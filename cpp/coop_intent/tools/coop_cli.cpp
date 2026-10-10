// coop_cli: the co-op bot in C++ -- a terminal chat like scripts/coop/coop_bot.py, and the checks
// that the port is exact (everything is compared with what the Python bot produced).
//
//   coop_cli                      chat; /why /t <x> /q as in coop_bot.py
//   coop_cli --golden             golden.jsonl: token ids equal, probabilities within 1e-4, same argmax
//   coop_cli --tokenizer-tests    tokenizer_tests.jsonl: normalizer output, token ids, regex slots (no model);
//                                 the token ids again with the vocabulary reloaded under a decimal-comma locale
//   coop_cli --dialogue           dialogue.jsonl: a scripted conversation, the bot's action, confidence,
//                                 queued order, places and executed order on every line
//   coop_cli --gate-tests         gate_tests.jsonl: both gates on the Python bot's probabilities and on
//                                 constructed rows (ties, family mass against top label; no model)
//   coop_cli --decide-tests       decide_tests.jsonl: every branch of the bot's decision, both gates (no model);
//                                 Reset() on every queued order
//   coop_cli --location-tests     location_tests.jsonl: the map places found in each line and, with a rule set v4
//                                 vocabulary, the directions; with a rule set v5 one, the pointers too (no model)
//   coop_cli --bench              latency on the golden lines, load time, memory
//   coop_cli --tokenize "text"    the words, pieces and ids of one line
//   coop_cli --speech-text-tests FILE   SpeechTextForClassifier against the Python `norm` (no model)
// with speech-to-text (a build that found sherpa-onnx under third_party/):
//   coop_cli --voice              the chat with a microphone: hold SPACE and talk, release to send; a typed
//                                 line still works (Windows, macOS)
//   coop_cli --stt-wav FILE       one clip (16-bit PCM WAV) through the recognizer and the bot; may be repeated
//   coop_cli --mic-test SECONDS   the default microphone for that long: the level it heard and the transcript
//                                 (Windows, macOS; no bot is loaded)
//   coop_cli --stt-tests LIST WAVDIR EXPECTED   the C++ transcripts against the Python package's: LIST is a
//                                 list of {id, wav} (scripts/coop/stt/lines.json), EXPECTED a run_stt.py output
// every mode first prints the bot it runs on (directory, labels, gate, threshold)
// options: --model-dir DIR (export_cpp.py output: intent_config.json, vocab.tsv and the model files
//          it lists under "members"), --threads N (per model, default 4),
//          --stt-model DIR (a sherpa-onnx export of Parakeet TDT), --stt-threads N (default 2),
//          --no-spin (ONNX Runtime worker threads sleep between calls), --sequential (an ensemble's
//          members one after another instead of one thread each)
#include <algorithm>
#include <chrono>
#include <clocale>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <memory>
#include <numeric>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_set>
#include <vector>

#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#include <psapi.h>
#include <conio.h>
#elif defined(__APPLE__)
#include <mach/mach.h>
#endif

#include "coop_intent/bot_brain.h"
#include "coop_intent/intent_model.h"
#include "coop_intent/speech.h"
#include "coop_intent/tokenizer.h"
#include "coop_intent/unicode.h"
#include "nlohmann/json.hpp"
// the microphone modes (--voice, --mic-test) exist where tools/ has a MicCapture
#if defined(COOP_WITH_STT) && (defined(_WIN32) || defined(__APPLE__))
#define COOP_WITH_MIC
#include "mic_capture.h"
#endif
#if defined(COOP_WITH_MIC) && defined(__APPLE__)
#include <CoreGraphics/CoreGraphics.h>
#include <poll.h>
#include <termios.h>
#include <unistd.h>
#include <cerrno>
#include <csignal>
#endif

using json = nlohmann::json;
using Clock = std::chrono::steady_clock;

namespace {

#ifndef COOP_DEFAULT_MODEL_DIR
#define COOP_DEFAULT_MODEL_DIR "."
#endif

std::filesystem::path U8Path(const std::string& s) { return std::filesystem::u8path(s); }

bool ReadFile(const std::string& path, std::string* out) {
    std::ifstream f(U8Path(path), std::ios::binary);
    if (!f) return false;
    std::ostringstream ss;
    ss << f.rdbuf();
    *out = ss.str();
    return true;
}

std::vector<json> ReadJsonl(const std::string& path) {
    std::vector<json> rows;
    std::string text;
    if (!ReadFile(path, &text)) {
        std::fprintf(stderr, "cannot read %s\n", path.c_str());
        std::exit(2);
    }
    std::istringstream in(text);
    for (std::string line; std::getline(in, line);)
        if (!line.empty()) rows.push_back(json::parse(line));
    return rows;
}

double Ms(Clock::duration d) { return std::chrono::duration<double, std::milli>(d).count(); }

double Percentile(std::vector<double> v, double q) {
    if (v.empty()) return 0;
    std::sort(v.begin(), v.end());
    return v[static_cast<size_t>(std::min<double>(static_cast<double>(v.size() - 1), std::floor(q * (v.size() - 1) + 0.5)))];
}

double WorkingSetMb() {
#ifdef _WIN32
    PROCESS_MEMORY_COUNTERS pmc{};
    if (GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof pmc)) return pmc.WorkingSetSize / 1048576.0;
#elif defined(__APPLE__)
    // the footprint, as Activity Monitor shows it: the resident size leaves out what macOS has compressed
    task_vm_info_data_t info{};
    mach_msg_type_number_t n = TASK_VM_INFO_COUNT;
    if (task_info(mach_task_self(), TASK_VM_INFO, reinterpret_cast<task_info_t>(&info), &n) == KERN_SUCCESS)
        return info.phys_footprint / 1048576.0;
#endif
    return 0;
}

// one line of UTF-8 from the terminal; the Windows console needs the wide API for non-ASCII input
bool ReadLine(std::string* line) {
#ifdef _WIN32
    HANDLE in = GetStdHandle(STD_INPUT_HANDLE);
    DWORD mode = 0;
    if (GetConsoleMode(in, &mode)) {
        std::u32string u;
        wchar_t buf[1024];
        for (;;) {
            DWORD n = 0;
            if (!ReadConsoleW(in, buf, 1024, &n, nullptr) || n == 0) return false;
            bool done = false;
            for (DWORD i = 0; i < n; ++i) {
                char32_t c = buf[i];
                if (c >= 0xD800 && c < 0xDC00 && i + 1 < n) c = 0x10000 + ((c - 0xD800) << 10) + (buf[++i] - 0xDC00);
                if (c == U'\n') done = true;
                else if (c != U'\r') u.push_back(c);
            }
            if (u.size() == 1 && u[0] == 0x1A) return false;   // Ctrl+Z
            if (done) break;
        }
        *line = coop::EncodeUtf8(u);
        return true;
    }
#endif
    return static_cast<bool>(std::getline(std::cin, *line));
}

struct Model {
    coop::DebertaTokenizer tok;
    coop::IntentConfig cfg;
    std::unique_ptr<coop::ILogitsBackend> backend;
    std::vector<std::string> members;   // ONNX files; several = an ensemble, probabilities averaged
    std::string dir;
};

// one OrtBackend per member file; several are wrapped in an EnsembleBackend
bool LoadModels(Model& m, const coop::OrtBackend::Options& opt, bool parallel, std::string* err) {
    std::vector<std::unique_ptr<coop::ILogitsBackend>> loaded;
    for (const std::string& f : m.members) {
        auto b = std::make_unique<coop::OrtBackend>();
        if (!b->Load(m.dir + "/" + f, opt, err)) return *err = f + ": " + *err, false;
        loaded.push_back(std::move(b));
    }
    if (loaded.size() == 1)
        m.backend = std::move(loaded[0]);
    else
        m.backend = std::make_unique<coop::EnsembleBackend>(std::move(loaded), parallel);
    return true;
}

bool LoadConfig(Model& m, std::string* err) {
    std::string cfg_text, vocab;
    if (!ReadFile(m.dir + "/intent_config.json", &cfg_text)) return *err = "cannot read intent_config.json", false;
    if (!ReadFile(m.dir + "/vocab.tsv", &vocab)) return *err = "cannot read vocab.tsv", false;
    coop::DebertaTokenizer::Options o;
    try {   // a missing key or a wrong type is a refusal with a message (json::at throws), not a crash
        // a key written twice is refused, as locations.py does: the later value would silently win
        std::vector<std::unordered_set<std::string>> seen;
        const json j = json::parse(cfg_text, [&seen](int, json::parse_event_t event, json& parsed) {
            if (event == json::parse_event_t::object_start) seen.emplace_back();
            if (event == json::parse_event_t::object_end) seen.pop_back();
            if (event == json::parse_event_t::key && !seen.back().insert(parsed.get<std::string>()).second)
                throw std::runtime_error("duplicate key \"" + parsed.get<std::string>() + "\"");
            return true;
        });
        coop::IntentConfig& c = m.cfg;
        c.labels = j.at("labels").get<std::vector<std::string>>();
        c.families = j.at("families").get<std::unordered_map<std::string, std::string>>();
        c.phrases = j.at("phrases").get<std::unordered_map<std::string, std::string>>();
        c.threshold = j.at("threshold").get<double>();
        c.gate = j.value("gate", std::string("top"));
        m.members = j.value("members", std::vector<std::string>{"model.onnx"});
        c.safe_intents = j.at("safe_intents").get<std::vector<std::string>>();
        // the answers to the planner's questions: only a bot that has such labels lists them (export_cpp.py)
        c.answer_intents = j.value("answer_intents", std::vector<std::string>{});
        c.on_signal = j.at("regex").at("on_signal").get<std::string>();
        c.other = j.at("regex").at("other").get<std::string>();
        c.negation = j.at("regex").at("negation").get<std::string>();
        if (j.contains("locations")) {   // the map's named places (scripts/coop/locations.json)
            const json& L = j.at("locations");
            c.has_locations = true;
            // the sections locations.py validate() requires, and no other. "directions" came with rule set
            // v4: a bot exported before it has none, and its places are matched by rule set v3 as before
            const char* const sections[] = {"version", "objects", "qualifiers", "named", "zones", "ignore", "words"};
            const bool directions = L.contains("directions");
            for (const char* s : sections)
                if (!L.contains(s)) throw std::runtime_error(std::string("locations: missing section \"") + s + "\"");
            for (auto& [key, value] : L.items()) {
                (void)value;
                if (key != "directions" &&
                    std::find_if(std::begin(sections), std::end(sections), [&](const char* s) { return key == s; }) == std::end(sections))
                    throw std::runtime_error("locations: unknown section \"" + key + "\"");
            }
            for (const json& ob : L.at("objects"))   // "vertical": true or false, where given (rule set v4)
                c.locations.objects.push_back({ob.at("id"), ob.at("words").get<std::vector<std::string>>(),
                                               ob.at("qualifiers").get<std::vector<std::string>>(),
                                               directions && ob.value("vertical", false)});
            for (const json& q : L.at("qualifiers")) {
                const json& lone = q.at("lone");   // explicit: an object id or null
                if (!lone.is_null() && lone.get<std::string>().empty())
                    throw std::runtime_error("locations: qualifier " + q.at("id").get<std::string>() + ": \"lone\" must be an object id or null");
                c.locations.qualifiers.push_back({q.at("id"), q.at("words").get<std::vector<std::string>>(),
                                                  lone.is_null() ? std::string() : lone.get<std::string>()});
            }
            for (const json& t : L.at("named")) c.locations.named.push_back({t.at("phrase"), t.at("object"), t.at("qualifier")});
            for (const json& z : L.at("zones"))
                c.locations.zones.push_back({z.at("id"), z.at("words").get<std::vector<std::string>>(),
                                             z.value("words_end", std::vector<std::string>{})});
            if (directions) {   // a list of {id, words, clock}; "clock" may be empty
                if (!L.at("directions").is_array()) throw std::runtime_error("locations: \"directions\" must be a list of {id, words, clock}");
                c.locations.has_directions = true;
                for (const json& d : L.at("directions"))
                    c.locations.directions.push_back({d.at("id"), d.at("words").get<std::vector<std::string>>(),
                                                      d.at("clock").get<std::vector<std::string>>()});
            }
            c.locations.ignore = L.at("ignore").get<std::vector<std::string>>();
            c.locations.words = L.at("words").get<std::unordered_map<std::string, std::vector<std::string>>>();
            // the pin_* and point_* word lists came with rule set v5: a bot exported before it has none, and
            // its places are matched by rule set v4 (or v3) as before. LocationMatcher::Init refuses a
            // vocabulary that has only some of them, or has them without "directions"
            for (const auto& list : c.locations.words)
                c.locations.has_pointers = c.locations.has_pointers || coop::LocationVocab::PointerList(list.first);
        }
        o.cls_id = j.at("cls_id").get<int32_t>();
        o.sep_id = j.at("sep_id").get<int32_t>();
        o.unk_id = j.at("unk_id").get<int32_t>();
        o.max_len = j.at("max_len").get<int>();
        for (auto& [text, id] : j.at("added_tokens").items()) o.added.push_back({text, id.get<int32_t>()});
    } catch (const std::exception& e) {
        return *err = std::string("intent_config.json refused: ") + e.what(), false;
    }
    return m.tok.Load(vocab, std::move(o), err);
}

bool Classify(Model& m, const std::vector<int64_t>& ids, std::vector<float>* probs, std::string* err) {
    std::vector<float> logits;
    if (!m.backend->Run(ids, &logits, err)) return false;
    *probs = coop::Softmax(logits);
    return true;
}

std::string IdsStr(const std::vector<int64_t>& ids) {
    std::string s;
    for (size_t i = 0; i < ids.size(); ++i) s += (i ? " " : "") + std::to_string(ids[i]);
    return s;
}

std::string Escaped(const std::string& s) { return json(s).dump(); }

// a place record as one comparable string:
// "<primary>: object/qualifier/zone/direction/pointer/role/flag/inferred; ..."
std::string PlacesStr(const coop::PlaceRecord& r, const coop::LocationMatcher& m) {
    std::string s = std::to_string(r.primary) + ":";
    for (const coop::PlaceTarget& t : r.targets) {
        auto dash = [](const std::string& x) { return x.empty() ? std::string("-") : x; };
        s += " " + (t.object >= 0 ? m.ObjectId(t.object) : "-") + "/" + (t.qualifier >= 0 ? m.QualifierId(t.qualifier) : "-") +
             "/" + (t.zone >= 0 ? m.ZoneId(t.zone) : "-") + "/" + dash(coop::PlaceDirectionName(t.direction)) + "/" +
             dash(coop::PlacePointerName(t.pointer)) + "/" + dash(coop::PlaceRoleName(t.role)) + "/" +
             dash(coop::PlaceFlagName(t.flag)) + "/" + (t.inferred ? "1" : "0") + ";";
    }
    return s;
}

// the same string from locations.record() as the Python bot wrote it (null: no record). A record
// written under rule set v3 has no "direction", and one written under rule set v3 or v4 no "pointer":
// none, which is what the engine gives such a bot
std::string PlacesStr(const json& r) {
    if (r.is_null()) return "-1:";
    std::string s = std::to_string(r["primary"].get<int>()) + ":";
    for (const json& t : r["targets"]) {
        auto f = [&](const char* k) { return t[k].is_null() ? std::string("-") : t[k].get<std::string>(); };
        s += " " + f("object") + "/" + f("qualifier") + "/" + f("zone") + "/" + (t.contains("direction") ? f("direction") : "-") +
             "/" + (t.contains("pointer") ? f("pointer") : "-") + "/" + f("role") + "/" + f("flag") + "/" +
             (t["inferred"].get<bool>() ? "1" : "0") + ";";
    }
    return s;
}

// a label or null, and a flag, as the Python bot wrote them
std::string LabelStr(const json& v) { return v.is_null() ? std::string("-") : v.get<std::string>(); }
std::string FlagStr(const json& v) { return v.get<bool>() ? "1" : "0"; }

// a key the test files have had only since the bot reports places (the place records, the order that
// fires and its "other" slot): compared whenever the row has it. A row without it passes only for a
// bot without "locations", whose stored files predate these keys (the v1 bot's); for a bot with
// places the key is missing, and that is a difference.
bool SameNewer(const json& row, const char* key, const std::string& got, std::string (*str)(const json&),
               const coop::IntentConfig& cfg, bool* missing) {
    const auto it = row.find(key);
    if (it != row.end()) return got == str(*it);
    if (cfg.has_locations) *missing = true;
    return !cfg.has_locations;
}

// the order a line executes with its "other" slot, for the messages: "SMOKE", "OPEN+other", "-"
std::string ExecStr(const std::string& label, bool other) { return label + (other ? "+other" : ""); }
std::string ExecStr(const json& row) {
    const auto it = row.find("executed");
    return it == row.end() ? "?" : ExecStr(LabelStr(*it), row.value("executed_other", false));
}

const char kMissingKeys[] = "  rows lack keys that a bot with places writes (places, executed, ...): "
                            "regenerate the test files with gen_tests.py\n";

// what the planner gets, for the chat's debug line: "* north door basement dir=left @this [mine]"
std::string PlacesText(const coop::PlaceRecord& r, const coop::LocationMatcher& m) {
    std::string s;
    for (size_t k = 0; k < r.targets.size(); ++k) {
        const coop::PlaceTarget& t = r.targets[k];
        if (k) s += "; ";
        if (static_cast<int>(k) == r.primary) s += "* ";
        std::string name;
        const char* direction = coop::PlaceDirectionName(t.direction);
        const char* pointer = coop::PlacePointerName(t.pointer);
        for (const std::string& part : {t.qualifier >= 0 ? m.QualifierId(t.qualifier) : std::string(),
                                        t.object >= 0 ? m.ObjectId(t.object) : std::string(),
                                        t.zone >= 0 ? m.ZoneId(t.zone) : std::string(),
                                        *direction ? std::string("dir=") + direction : std::string(),
                                        *pointer ? std::string("@") + pointer : std::string()})
            if (!part.empty()) name += (name.empty() ? "" : " ") + part;
        s += name;
        for (const char* tag : {coop::PlaceRoleName(t.role), coop::PlaceFlagName(t.flag)})
            if (*tag) s += std::string(" [") + tag + "]";
    }
    return s;
}

// ---- checks ----------------------------------------------------------------------------------

int RunTokenizerTests(Model& m) {
    const auto rows = ReadJsonl(m.dir + "/tokenizer_tests.jsonl");
    coop::SlotPatterns slots;
    std::string err;
    if (!slots.Init(m.cfg, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    size_t bad_norm = 0, bad_ids = 0, bad_slots = 0, limit_rows = 0;
    int shown = 0;
    auto show = [&](const char* what, const std::string& text, const std::string& want, const std::string& got) {
        if (shown++ < 12) std::printf("  %s %s\n    python %s\n    c++    %s\n", what, Escaped(text).c_str(), want.c_str(), got.c_str());
    };
    for (const json& r : rows) {
        const std::string text = r["text"];
        const std::string norm = m.tok.Normalize(text);
        if (norm != r["norm"].get<std::string>()) ++bad_norm, show("normalizer", text, Escaped(r["norm"]), Escaped(norm));
        const auto ids = m.tok.Encode(text);
        const auto want = r["ids"].get<std::vector<int64_t>>();
        if (ids != want) ++bad_ids, show("ids", text, IdsStr(want), IdsStr(ids));
        coop::Decision d;
        const unsigned gave_up = slots.SearchErrors();
        slots.Match(text, &d);   // must not crash on any line
        const auto s = r["slots"].get<std::vector<bool>>();
        // a line built to pass std::regex's recursion limit, and it did (MSVC; libc++ has no such limit
        // and is compared): documented, not compared
        if (r.value("regex_limit", false) && slots.SearchErrors() != gave_up) {
            ++limit_rows;
            continue;
        }
        if (d.on_signal != s[0] || d.other != s[1] || d.negated != s[2]) {
            ++bad_slots;
            char a[64], b[64];
            std::snprintf(a, sizeof a, "on_signal %d other %d negation %d", (int)s[0], (int)s[1], (int)s[2]);
            std::snprintf(b, sizeof b, "on_signal %d other %d negation %d", d.on_signal, d.other, d.negated);
            show("slots", text, a, b);
        }
    }
    // the vocabulary must load whatever locale the host process has set: read with strtod, "0.0" is a
    // bad score under a decimal comma. Every line is encoded again with the vocabulary reloaded under
    // such a locale, if one is installed
    const char* comma = nullptr;
    for (const char* name : {"de_DE.UTF-8", "de_DE.utf8", "German_Germany.1252"})
        if (!comma && std::setlocale(LC_ALL, name)) comma = name;
    size_t bad_locale = 0;
    bool loads = true;
    if (comma) {
        Model again;
        again.dir = m.dir;
        loads = LoadConfig(again, &err);
        if (loads)
            for (const json& r : rows)
                bad_locale += again.tok.Encode(r["text"].get<std::string>()) != r["ids"].get<std::vector<int64_t>>();
        std::setlocale(LC_ALL, "C");
    }
    const size_t n = rows.size();
    std::printf("tokenizer tests, %zu lines: normalizer %zu/%zu equal, token ids %zu/%zu equal, regex slots %zu/%zu equal",
                n, n - bad_norm, n, n - bad_ids, n, n - limit_rows - bad_slots, n - limit_rows);
    if (limit_rows)
        std::printf(" (+%zu lines past std::regex's recursion limit, not compared; it gave up on %u slot searches)\n",
                    limit_rows, slots.SearchErrors());
    else
        std::printf(" (every line compared; std::regex gave up on %u slot searches)\n", slots.SearchErrors());
    if (!comma)
        std::printf("  vocabulary reload under a decimal comma skipped: no decimal-comma locale installed\n");
    else if (!loads)
        std::printf("  under %s the vocabulary does not load: %s\n", comma, err.c_str());
    else
        std::printf("  vocabulary reloaded under %s: token ids %zu/%zu equal\n", comma, n - bad_locale, n);
    return bad_norm || bad_ids || bad_slots || bad_locale || !loads ? 1 : 0;
}

int RunGolden(Model& m) {
    const auto rows = ReadJsonl(m.dir + "/golden.jsonl");
    size_t bad_ids = 0, argmax_ok = 0, within = 0;
    double max_diff = 0;
    std::string err, worst;
    for (const json& r : rows) {
        const std::string text = r["text"];
        const auto ids = m.tok.Encode(text);
        const auto want = r["ids"].get<std::vector<int64_t>>();
        if (ids != want) {
            if (bad_ids++ < 10) std::printf("  ids differ %s\n    python %s\n    c++    %s\n", Escaped(text).c_str(), IdsStr(want).c_str(), IdsStr(ids).c_str());
        }
        std::vector<float> p;
        if (!Classify(m, ids, &p, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        const auto ref = r["probs"].get<std::vector<double>>();
        if (p.size() != ref.size())
            return std::fprintf(stderr, "the model gives %zu probabilities, golden.jsonl has %zu\n", p.size(), ref.size()), 1;
        double d = 0;
        for (size_t i = 0; i < ref.size(); ++i) d = std::max(d, std::fabs(p[i] - ref[i]));
        if (d > max_diff) max_diff = d, worst = text;
        within += d <= 1e-4;
        argmax_ok += std::max_element(p.begin(), p.end()) - p.begin() == std::max_element(ref.begin(), ref.end()) - ref.begin();
    }
    const size_t n = rows.size();
    std::printf("golden, %zu lines: token ids %zu/%zu equal, same argmax %zu/%zu, probabilities within 1e-4 on %zu/%zu, "
                "max |dp| %.2e (%s)\n", n, n - bad_ids, n, argmax_ok, n, within, n, max_diff, Escaped(worst).c_str());
    return bad_ids || argmax_ok != n || within != n ? 1 : 0;
}

int RunDialogue(Model& m) {
    const auto rows = ReadJsonl(m.dir + "/dialogue.jsonl");
    coop::BotBrain brain;
    std::string err;
    if (!brain.Init(m.cfg, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    size_t ok = 0;
    bool missing = false;
    for (const json& r : rows) {
        const std::string text = r["text"];
        std::vector<float> p;
        if (!Classify(m, m.tok.Encode(text), &p, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        const coop::Decision d = brain.Decide(text, p);
        const std::string intent = d.intent >= 0 ? m.cfg.labels[d.intent] : "?";
        const std::string pending = brain.Pending() >= 0 ? m.cfg.labels[brain.Pending()] : "-";
        const std::string want_pending = r["pending"].is_null() ? "-" : r["pending"].get<std::string>();
        const std::string executed = d.executed >= 0 ? m.cfg.labels[d.executed] : "-";
        auto newer = [&](const char* key, const std::string& got, std::string (*str)(const json&)) {
            return SameNewer(r, key, got, str, m.cfg, &missing);
        };
        // the confidence too: under the family gate it is the family's mass, not the top probability
        const bool same = intent == r["intent"] && std::fabs(d.prob - r["prob"].get<double>()) <= 1e-4 &&
                          coop::ActionName(d.action) == r["action"].get<std::string>() &&
                          pending == want_pending && d.other == r["other"].get<bool>() &&
                          newer("places", PlacesStr(d.places, brain.Places()), PlacesStr) &&
                          newer("executed", executed, LabelStr) &&
                          newer("executed_places", PlacesStr(d.executed_places, brain.Places()), PlacesStr) &&
                          newer("executed_other", d.executed_other ? "1" : "0", FlagStr);
        ok += same;
        std::printf("%s %-44s %-16s %.2f %-9s queued %-14s%s\n", same ? "ok  " : "DIFF", Escaped(text).c_str(),
                    intent.c_str(), d.prob, coop::ActionName(d.action), pending.c_str(), d.other ? " other" : "");
        if (!same)
            std::printf("     python: %s %.2f %s queued %s executes %s; c++ executes %s\n", r["intent"].get<std::string>().c_str(),
                        r["prob"].get<double>(), r["action"].get<std::string>().c_str(), want_pending.c_str(),
                        ExecStr(r).c_str(), ExecStr(executed, d.executed_other).c_str());
    }
    if (missing) std::printf("%s", kMissingKeys);
    std::printf("dialogue, %zu lines: the C++ bot did what the Python bot did on %zu/%zu\n", rows.size(), ok, rows.size());
    return ok == rows.size() ? 0 : 1;
}

// the gates alone, without a model: coop_bot.Bot.pick's answers for both gates on the Python bot's own
// probabilities and on constructed rows (exact ties, the top label outside the top-mass family)
int RunGateTests(Model& m) {
    const auto rows = ReadJsonl(m.dir + "/gate_tests.jsonl");
    std::string err;
    size_t n = 0, ok = 0;
    for (const char* gate : {"top", "family"}) {
        coop::IntentConfig cfg = m.cfg;
        cfg.gate = gate;
        coop::BotBrain brain;
        if (!brain.Init(cfg, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        int shown = 0;
        for (const json& r : rows) {
            std::vector<float> p;
            for (double x : r["probs"].get<std::vector<double>>()) p.push_back(static_cast<float>(x));
            int intent = -1;
            double conf = 0;
            const bool fits = brain.Pick(p, &intent, &conf);
            const json& want = r[gate];
            const bool same = fits && cfg.labels[intent] == want["intent"].get<std::string>() &&
                              std::fabs(conf - want["prob"].get<double>()) <= 1e-12;
            ++n;
            ok += same;
            if (!same && shown++ < 8)
                std::printf("  %s gate, row %s: python %s %.17g, c++ %s %.17g\n", gate, r["name"].get<std::string>().c_str(),
                            want["intent"].get<std::string>().c_str(), want["prob"].get<double>(),
                            fits ? cfg.labels[intent].c_str() : "?", conf);
        }
    }
    std::printf("gate tests, %zu rows x 2 gates: C++ picked what the Python bot picked on %zu/%zu\n", rows.size(), ok, n);
    return ok == n ? 0 : 1;
}

// LocationMatcher::Find against locations.record() of the Python bot, line by line (no model)
int RunLocationTests(Model& m) {
    const auto rows = ReadJsonl(m.dir + "/location_tests.jsonl");
    coop::LocationMatcher matcher;
    std::string err;
    if (!m.cfg.has_locations) return std::fprintf(stderr, "intent_config.json has no \"locations\"\n"), 1;
    if (!matcher.Init(m.cfg.locations, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    size_t ok = 0, with_place = 0, with_direction = 0, with_pointer = 0, no_record = 0;
    int shown = 0;
    for (const json& r : rows) {
        const std::string text = r["text"];
        const coop::PlaceRecord rec = matcher.Find(text);   // must not crash on any line
        // a line locations.record() raises on (gen_tests.py: rule set v4, step 6d): there is no Python
        // record. Documented, not compared
        if (r.value("python_error", false)) {
            ++no_record;
            continue;
        }
        const std::string got = PlacesStr(rec, matcher), want = PlacesStr(r["places"]);
        with_place += !rec.targets.empty();
        with_direction += std::any_of(rec.targets.begin(), rec.targets.end(),
                                      [](const coop::PlaceTarget& t) { return t.direction != coop::PlaceDirection::None; });
        with_pointer += std::any_of(rec.targets.begin(), rec.targets.end(),
                                    [](const coop::PlaceTarget& t) { return t.pointer != coop::PlacePointer::None; });
        if (got == want)
            ++ok;
        else if (shown++ < 12)
            std::printf("  %s\n    python %s\n    c++    %s\n", Escaped(text).c_str(), want.c_str(), got.c_str());
    }
    const size_t n = rows.size() - no_record;
    if (m.cfg.locations.has_pointers)   // rule set v5: a target may be a pointer alone
        std::printf("location tests, %zu lines (%zu name a place, a direction or a pointer, %zu of them a direction, %zu a "
                    "pointer): the C++ record equals the Python record on %zu/%zu", n, with_place, with_direction, with_pointer,
                    ok, n);
    else if (m.cfg.locations.has_directions)   // rule set v4: a target may be a direction alone
        std::printf("location tests, %zu lines (%zu name a place or a direction, %zu of them a direction): the C++ record "
                    "equals the Python record on %zu/%zu", n, with_place, with_direction, ok, n);
    else
        std::printf("location tests, %zu lines (%zu name a place): the C++ record equals the Python record on %zu/%zu", n,
                    with_place, ok, n);
    if (no_record) std::printf(" (+%zu lines the Python matcher raises on, not compared)", no_record);
    std::printf("\n");
    return ok == n ? 0 : 1;
}

// BotBrain::Decide against coop_bot.Bot.decide on constructed probabilities: every branch, both gates
int RunDecideTests(Model& m) {
    const auto rows = ReadJsonl(m.dir + "/decide_tests.jsonl");
    std::string err;
    size_t n = 0, ok = 0;
    bool missing = false;
    for (const json& sc : rows) {
        coop::IntentConfig cfg = m.cfg;
        cfg.gate = sc["gate"].get<std::string>();
        coop::BotBrain brain, spare;   // spare: the one Reset() is tried on
        if (!brain.Init(cfg, &err) || !spare.Init(cfg, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        brain.threshold = spare.threshold = sc["threshold"].get<double>();
        for (const json& s : sc["steps"]) {
            std::vector<float> p;
            for (double x : s["probs"].get<std::vector<double>>()) p.push_back(static_cast<float>(x));
            const std::string text = s["text"];
            const coop::Decision d = brain.Decide(text, p);
            const std::string intent = d.intent >= 0 ? cfg.labels[d.intent] : "?";
            const std::string pending = brain.Pending() >= 0 ? cfg.labels[brain.Pending()] : "-";
            const std::string want_pending = s["pending"].is_null() ? "-" : s["pending"].get<std::string>();
            const std::string executed = d.executed >= 0 ? cfg.labels[d.executed] : "-";
            auto newer = [&](const char* key, const std::string& got, std::string (*str)(const json&)) {
                return SameNewer(s, key, got, str, cfg, &missing);
            };
            const bool same = intent == s["intent"] && std::fabs(d.prob - s["prob"].get<double>()) <= 1e-12 &&
                              coop::ActionName(d.action) == s["action"].get<std::string>() &&
                              pending == want_pending && d.other == s["other"].get<bool>() &&
                              newer("places", PlacesStr(d.places, brain.Places()), PlacesStr) &&
                              newer("executed", executed, LabelStr) &&
                              newer("executed_places", PlacesStr(d.executed_places, brain.Places()), PlacesStr) &&
                              newer("executed_other", d.executed_other ? "1" : "0", FlagStr) &&
                              newer("pending_places", PlacesStr(brain.PendingPlaces(), brain.Places()), PlacesStr) &&
                              newer("pending_other", brain.PendingOther() ? "1" : "0", FlagStr);
            // Reset() with an order queued: the conversation's brain only runs it in Init, with nothing
            // queued, so a second brain queues this step's order and must forget it, its places and its
            // "other" slot
            bool forgot = true;
            if (s["action"] == "queued") {
                spare.Decide(text, p);
                spare.Reset();
                forgot = spare.Pending() < 0 && spare.PendingPlaces().targets.empty() && !spare.PendingOther();
                if (!forgot)
                    std::printf("  %s gate, %s: Reset() left the queued order, its places or its \"other\" slot\n",
                                cfg.gate.c_str(), Escaped(text).c_str());
            }
            ++n;
            ok += same && forgot;
            if (!same)
                std::printf("  %s gate, %s: python %s %s queued %s executes %s, c++ %s %s queued %s executes %s\n",
                            cfg.gate.c_str(), Escaped(text).c_str(), s["intent"].get<std::string>().c_str(),
                            s["action"].get<std::string>().c_str(), want_pending.c_str(), ExecStr(s).c_str(),
                            intent.c_str(), coop::ActionName(d.action), pending.c_str(),
                            ExecStr(executed, d.executed_other).c_str());
        }
    }
    // the engine's own guard, which the test file cannot carry (JSON has no NaN): a model that returns NaN
    // is asked again under both gates, and nothing is queued
    for (const char* gate : {"top", "family"}) {
        coop::IntentConfig cfg = m.cfg;
        cfg.gate = gate;
        coop::BotBrain brain;
        if (!brain.Init(cfg, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        const std::vector<float> nan(cfg.labels.size(), std::numeric_limits<float>::quiet_NaN());
        const coop::Decision d = brain.Decide("smoke the north door on my go", nan);
        const bool good = d.action == coop::Action::SayAgain && brain.Pending() < 0;
        ++n;
        ok += good;
        if (!good) std::printf("  %s gate: NaN probabilities gave %s, not say_again\n", gate, coop::ActionName(d.action));
    }
    if (missing) std::printf("%s", kMissingKeys);
    std::printf("decide tests, %zu steps over both gates (2 of them built in: NaN probabilities): C++ decided what the "
                "Python bot decided on %zu/%zu\n", n, ok, n);
    return ok == n ? 0 : 1;
}

int RunBench(Model& m, double load_ms, double mem_before) {
    const auto rows = ReadJsonl(m.dir + "/golden.jsonl");
    std::vector<std::string> texts;
    for (const json& r : rows) texts.push_back(r["text"]);
    std::string err;
    std::vector<float> p;
    for (int i = 0; i < 5; ++i) Classify(m, m.tok.Encode(texts[i]), &p, &err);   // warm-up
    std::vector<double> tok_us, model_ms, len;
    for (int rep = 0; rep < 2; ++rep) {
        for (const std::string& t : texts) {
            auto t0 = Clock::now();
            const auto ids = m.tok.Encode(t);
            auto t1 = Clock::now();
            if (!Classify(m, ids, &p, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
            auto t2 = Clock::now();
            tok_us.push_back(Ms(t1 - t0) * 1000);
            model_ms.push_back(Ms(t2 - t1));
            len.push_back(static_cast<double>(ids.size()));
        }
    }
    std::printf("model load %.0f ms, working set +%.0f MB (%.0f MB total)\n", load_ms, WorkingSetMb() - mem_before, WorkingSetMb());
    std::printf("%zu lines x 2, %.1f tokens on average (max %.0f)\n", texts.size(),
                std::accumulate(len.begin(), len.end(), 0.0) / len.size(), *std::max_element(len.begin(), len.end()));
    std::printf("tokenizer: median %.1f us, p99 %.1f us\n", Percentile(tok_us, 0.5), Percentile(tok_us, 0.99));
    coop::LocationMatcher places;
    if (m.cfg.has_locations && places.Init(m.cfg.locations, &err)) {
        std::vector<double> loc_us;
        size_t with_place = 0;
        for (const std::string& t : texts) {
            const auto t0 = Clock::now();
            const coop::PlaceRecord r = places.Find(t);
            loc_us.push_back(Ms(Clock::now() - t0) * 1000);
            with_place += !r.targets.empty();
        }
        std::printf("places:    median %.1f us, p99 %.1f us (%zu of %zu lines name a place)\n", Percentile(loc_us, 0.5),
                    Percentile(loc_us, 0.99), with_place, texts.size());
    }
    std::printf("model:     median %.1f ms, p90 %.1f ms, p99 %.1f ms, max %.1f ms\n", Percentile(model_ms, 0.5),
                Percentile(model_ms, 0.9), Percentile(model_ms, 0.99), Percentile(model_ms, 1.0));
    return 0;
}

// ---- chat --------------------------------------------------------------------------------------

const std::unordered_map<std::string, std::vector<std::string>> kLines = {
    {"FOLLOW_ME", {"On you.", "Right behind you.", "Moving with you."}},
    {"MOVE_TO", {"Moving to the ping.", "On my way there.", "Relocating."}},
    {"HOLD_POSITION", {"Holding here.", "Staying put.", "Not moving."}},
    {"HOLD_ANGLE", {"Holding that angle.", "Eyes on it.", "Angle locked."}},
    {"HOLD_OTHER_ANGLE", {"I've got the other side.", "Taking the other angle.", "Watching the other one."}},
    {"FLANK", {"Going around.", "Flanking, keep them busy.", "Taking the long way."}},
    {"VAULT_WINDOW", {"Going through the window.", "Vaulting in.", "Window, going."}},
    {"RAPPEL", {"On the rope.", "Rappelling.", "Heading up top."}},
    {"BREACH", {"Charge set, breaching!", "Blowing it open.", "Breaching!"}},
    {"DRONE", {"Droning it out.", "Drone's in.", "Scouting first."}},
    {"FLASH", {"Flash out!", "Popping a flash.", "Stun going in."}},
    {"SMOKE", {"Smoke out.", "Popping smoke.", "Smoking it."}},
    {"FRAG", {"Frag out!", "Nade going in.", "Throwing a frag."}},
    {"COVER_ME", {"Covering you, go.", "I've got your back.", "Go, I'm on it."}},
    {"ENTRY", {"Pushing in!", "Taking the room.", "Entry, entry!"}},
    {"FALL_BACK", {"Falling back.", "Pulling out.", "Backing off."}},
    {"PLANT", {"Planting.", "Getting the plant down.", "Plant going down, cover me."}},
    {"DEFUSE", {"Defusing.", "On the defuser.", "Working on it."}},
    {"REVIVE_ME", {"Coming to get you!", "Hold on, reviving.", "On my way, stay down."}},
    {"WAIT", {"Holding up.", "Standing by.", "Copy, waiting."}},
    {"TAKE_COVER", {"Getting into cover.", "Finding cover.", "Hiding."}},
    {"OPEN", {"Opening it.", "Getting it open.", "Opening, not going in."}},
    {"ATTACK", {"Attacking!", "Engaging.", "Going on the offensive."}},
    {"OPEN_FIRE", {"Opening fire!", "Weapons free.", "Firing!"}},
    {"HOLD_FIRE", {"Holding fire.", "Weapons tight.", "Ceasing fire."}},
    {"LOOK_AT", {"Looking.", "I see it.", "Turning to look."}},
    {"LOOK_AT_ME", {"Looking at you.", "Yeah, I see you.", "Facing you."}},
    {"HELP", {"Coming to help.", "On my way to you.", "Hang on, I'm coming."}},
    {"CHECK", {"Checking it.", "I'll check.", "Going to take a look."}},
    {"SUPPRESS", {"Suppressing!", "Covering fire!", "Keeping their heads down."}},
    {"JUMP", {"Jumping.", "On it, jumping.", "Going over."}},
    {"COME_BACK", {"Coming back.", "On my way back.", "Returning."}},
    {"CROUCH", {"Crouching.", "Getting low.", "Down on a knee."}},
    {"PRONE", {"Going prone.", "Lying down.", "Flat on the ground."}},
    {"STAND_UP", {"Standing up.", "On my feet.", "Up."}},
    {"YES", {"Yes, got it.", "Understood: yes.", "Copy, that's a yes."}},
    {"NO", {"No, got it.", "Understood: no.", "Copy, that's a no."}},
    {"MAYBE", {"Maybe, got it.", "Understood: not certain.", "Copy, I'll use my judgement."}},
    {"DONT_KNOW", {"You don't know, got it.", "Understood: no answer.", "Copy, you're not sure."}},
};
const std::vector<std::string> kAck = {"Copy.", "Noted.", "Heard."};

// a label the demo has no lines for (a newer model) still gets an answer
const std::vector<std::string>& LinesFor(const std::string& label) {
    auto it = kLines.find(label);
    return it != kLines.end() ? it->second : kAck;
}
const std::vector<std::string> kAgain = {"Say again?", "Didn't catch that.", "Come again?"};

// coop_bot.py strips the line with str.strip(): the same Unicode whitespace here
std::string StripPy(const std::string& line) {
    std::u32string u = coop::DecodeUtf8(line);
    size_t b = 0, e = u.size();
    while (b < e && coop::IsPySpace(u[b])) ++b;
    while (e > b && coop::IsPySpace(u[e - 1])) --e;
    return coop::EncodeUtf8(std::u32string_view(u).substr(b, e - b));
}

// one bot in a conversation: the demo's replies and the debug line
struct Chat {
    Model& m;
    coop::BotBrain brain;
    std::mt19937 rng{static_cast<unsigned>(Clock::now().time_since_epoch().count())};
    bool why = true;
    std::vector<float> p;

    explicit Chat(Model& model) : m(model) {}
    bool Init(std::string* err) {
        if (!brain.Init(m.cfg, err)) return false;
        return Classify(m, m.tok.Encode("warm up"), &p, err);
    }
    const std::string& Pick(const std::vector<std::string>& v) { return v[rng() % v.size()]; }

    // /q /why /t: 0 not a command, 1 handled, 2 quit
    int Command(const std::string& line) {
        if (line == "/q" || line == "/quit") return 2;
        if (line == "/why") return why = !why, 1;
        if (line.rfind("/t ", 0) == 0) {
            brain.threshold = std::atof(line.c_str() + 3);
            std::printf("  threshold %.2f\n", brain.threshold);
            return 1;
        }
        return 0;
    }

    // One line. `heard` is what the regex slots and the place matcher read; `text` is what the classifier
    // reads: the same string for a typed line, SpeechTextForClassifier(heard) for a spoken one
    bool Respond(const std::string& heard, const std::string& text, std::string* err) {
        const auto t0 = Clock::now();
        const auto ids = m.tok.Encode(text);
        if (!Classify(m, ids, &p, err)) return false;
        const double ms = Ms(Clock::now() - t0);
        const int pending_before = brain.Pending();
        const coop::Decision d = brain.Decide(heard, p);
        if (d.intent < 0) return *err = "the model does not fit intent_config.json", false;
        const std::string& intent = m.cfg.labels[d.intent];
        std::string reply;
        switch (d.action) {
            case coop::Action::Negated: reply = "Copy, standing down."; break;
            case coop::Action::SayAgain: reply = Pick(kAgain); break;
            case coop::Action::Ignore: reply = Pick(kAck); break;
            case coop::Action::Execute: reply = "Now! " + Pick(LinesFor(m.cfg.labels[pending_before])); break;
            case coop::Action::Go: reply = "Going!"; break;
            case coop::Action::Wait: reply = Pick(kLines.at("WAIT")); break;
            case coop::Action::Queued: reply = "Ready to " + m.cfg.phrases[intent] + ". On your go."; break;
            case coop::Action::Act: reply = Pick(LinesFor(intent)); break;
            case coop::Action::Answer: reply = Pick(LinesFor(intent)); break;   // the answer said back: nothing is done
        }
        // "hold fire until I say": the bot holds now and has queued OPEN_FIRE for the signal
        if (intent == "HOLD_FIRE" && d.action == coop::Action::Act && d.on_signal && brain.LabelIndex("OPEN_FIRE") >= 0)
            reply += " On your go.";
        if (d.other && (d.action == coop::Action::Act || d.action == coop::Action::Queued) && intent != "HOLD_OTHER_ANGLE" &&
            intent != "HOLD_FIRE")
            reply += " Taking the other one.";
        std::printf("bot> %s\n", reply.c_str());
        if (why) {
            const auto top = coop::TopK(p, 3);
            std::string slots;
            if (d.on_signal) slots += "on my signal";
            if (d.other) slots += std::string(slots.empty() ? "" : ", ") + "other";
            if (d.executed_other) slots += std::string(slots.empty() ? "" : ", ") + "other (the queued order's)";
            const std::string& first = m.cfg.labels[top[0]];
            char mass[64] = "";
            if (m.cfg.gate == "family")
                std::snprintf(mass, sizeof mass, " | %s mass %.2f", m.cfg.families[intent].c_str(), d.prob);
            std::printf("     %s (%s) %.2f | %s %.2f | %s %.2f%s | %s%s%s | %.0f ms\n", first.c_str(),
                        m.cfg.families[first].c_str(), p[top[0]], m.cfg.labels[top[1]].c_str(), p[top[1]],
                        m.cfg.labels[top[2]].c_str(), p[top[2]], mass, coop::ActionName(d.action),
                        slots.empty() ? "" : (" | slots: " + slots).c_str(),
                        brain.Pending() >= 0 ? (" | queued: " + m.cfg.labels[brain.Pending()]).c_str() : "", ms);
            if (!d.places.targets.empty())
                std::printf("     place: %s\n", PlacesText(d.places, brain.Places()).c_str());
            if (!d.executed_places.targets.empty())
                std::printf("     executes at: %s\n", PlacesText(d.executed_places, brain.Places()).c_str());
        }
        return true;
    }
};

int RunChat(Model& m, int threads) {
    Chat chat(m);
    std::string err;
    if (!chat.Init(&err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    std::printf("ready (C++, ONNX Runtime %s CPU, %d threads). threshold %.2f. Talk to your teammate in English; /why /t <x> /q\n\n",
                coop::OrtBackend::RuntimeVersion().c_str(), threads, chat.brain.threshold);
    for (;;) {
        std::printf("you> ");
        std::fflush(stdout);
        std::string line;
        if (!ReadLine(&line)) return std::printf("\n"), 0;
        line = StripPy(line);
        if (line.empty()) continue;
        if (const int c = chat.Command(line)) {
            if (c == 2) return 0;
            continue;
        }
        if (!chat.Respond(line, line, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    }
}

// SpeechTextForClassifier against scripts/coop/stt `norm`: a list of {text, norm} written by Python
int RunSpeechTextTests(const std::string& path) {
    std::string raw;
    if (!ReadFile(path, &raw)) return std::fprintf(stderr, "cannot read %s\n", path.c_str()), 1;
    const json rows = json::parse(raw);
    size_t same = 0, shown = 0;
    for (const json& r : rows) {
        const std::string got = coop::SpeechTextForClassifier(r.at("text").get<std::string>());
        if (got == r.at("norm").get<std::string>()) ++same;
        else if (shown++ < 5)
            std::printf("  %s: C++ %s, Python %s\n", Escaped(r.at("text")).c_str(), Escaped(got).c_str(), Escaped(r.at("norm")).c_str());
    }
    std::printf("speech text tests, %zu lines: the classifier's text equals the Python one on %zu/%zu\n", rows.size(), same, rows.size());
    return same == rows.size() ? 0 : 1;
}

#ifdef COOP_WITH_STT
// a 16-bit PCM WAV file: its first channel as samples in -1..1
bool ReadWav(const std::string& path, std::vector<float>* samples, int* sample_rate, std::string* err) {
    std::string raw;
    if (!ReadFile(path, &raw)) return *err = "cannot read " + path, false;
    auto u16 = [&](size_t i) { return static_cast<unsigned>(static_cast<unsigned char>(raw[i])) | static_cast<unsigned>(static_cast<unsigned char>(raw[i + 1])) << 8; };
    auto u32 = [&](size_t i) { return u16(i) | u16(i + 2) << 16; };
    if (raw.size() < 12 || raw.compare(0, 4, "RIFF") != 0 || raw.compare(8, 4, "WAVE") != 0) return *err = path + " is not a WAV file", false;
    unsigned channels = 0, bits = 0, format = 0;
    for (size_t i = 12; i + 8 <= raw.size();) {
        const size_t n = u32(i + 4), body = i + 8;
        if (body + n > raw.size() && raw.compare(i, 4, "data") != 0) break;
        if (raw.compare(i, 4, "fmt ") == 0 && n >= 16) {
            format = u16(body), channels = u16(body + 2), *sample_rate = static_cast<int>(u32(body + 4)), bits = u16(body + 14);
        } else if (raw.compare(i, 4, "data") == 0) {
            if (format != 1 || bits != 16 || channels == 0) return *err = path + ": only 16-bit PCM is read", false;
            const size_t bytes = std::min(n, raw.size() - body), frame = 2 * channels;
            samples->resize(bytes / frame);
            for (size_t k = 0; k < samples->size(); ++k)
                (*samples)[k] = static_cast<short>(u16(body + k * frame)) / 32768.0f;
            return true;
        }
        i = body + n + (n & 1);
    }
    return *err = path + " has no audio data", false;
}

bool LoadSpeech(coop::SpeechRecognizer& stt, const coop::SpeechOptions& opt, std::string* err) {
    const auto t0 = Clock::now();
    const double mem0 = WorkingSetMb();
    if (!stt.Load(opt, err)) return false;
    std::vector<float> silence(16000, 0.0f);    // the first call pays for allocation
    std::string text;
    if (!stt.Transcribe(silence.data(), silence.size(), 16000, &text, err)) return false;
    std::printf("speech: %s on ONNX Runtime %s, %s (%d threads; loaded in %.1f s, %.0f MB)\n",
                coop::SpeechRecognizer::Backend().c_str(), coop::SpeechRecognizer::RuntimeVersion().c_str(), opt.model_dir.c_str(),
                opt.threads, Ms(Clock::now() - t0) / 1000, WorkingSetMb() - mem0);
    return true;
}

// The C++ transcripts against what the Python package printed for the same clips (scripts/coop/stt/run_stt.py),
// and what the difference does to the bot: its pick on the C++ transcript against its pick on the Python one
// (the intent, or "say again" under the threshold), and against the line's own label where the list has one
int RunSttTests(Model& m, const coop::SpeechOptions& opt, const std::string& list, const std::string& wav_dir,
                const std::string& expected) {
    coop::SpeechRecognizer stt;
    coop::BotBrain brain;
    std::string err, raw;
    if (!LoadSpeech(stt, opt, &err) || !brain.Init(m.cfg, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    if (!ReadFile(list, &raw)) return std::fprintf(stderr, "cannot read %s\n", list.c_str()), 1;
    const json rows = json::parse(raw);
    if (!ReadFile(expected, &raw)) return std::fprintf(stderr, "cannot read %s\n", expected.c_str()), 1;
    const json python = json::parse(raw);
    std::unordered_map<std::string, std::string> want;
    for (const json& r : python.at("rows")) want[r.at("id").get<std::string>()] = r.at("text").get<std::string>();
    std::vector<float> p;
    auto pick = [&](const std::string& transcript, std::string* label) {
        if (!Classify(m, m.tok.Encode(coop::SpeechTextForClassifier(transcript)), &p, &err)) return false;
        int intent = -1;
        double conf = 0;
        if (!brain.Pick(p, &intent, &conf)) return err = "the model does not fit intent_config.json", false;
        *label = conf >= brain.threshold ? m.cfg.labels[static_cast<size_t>(intent)] : std::string("(say again)");
        return true;
    };
    size_t n = 0, same = 0, same_pick = 0, labelled = 0, right_cpp = 0, right_python = 0, shown = 0;
    std::vector<double> ms;
    double audio = 0;
    for (const json& r : rows) {
        const auto w = want.find(r.at("id").get<std::string>());
        if (w == want.end()) continue;
        std::vector<float> x;
        int rate = 0;
        if (!ReadWav(wav_dir + "/" + r.at("wav").get<std::string>(), &x, &rate, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        const auto t0 = Clock::now();
        std::string text, a, b;
        if (!stt.Transcribe(x.data(), x.size(), rate, &text, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        ms.push_back(Ms(Clock::now() - t0));
        audio += static_cast<double>(x.size()) / rate;
        ++n;
        if (!pick(text, &a) || !pick(w->second, &b)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        if (text == w->second) ++same;
        else if (shown++ < 5)
            std::printf("  %s: C++ %s -> %s, Python %s -> %s\n", r.at("wav").get<std::string>().c_str(), Escaped(text).c_str(), a.c_str(),
                        Escaped(w->second).c_str(), b.c_str());
        if (a == b) ++same_pick;
        if (r.contains("maj") && r["maj"].is_string()) {
            ++labelled;
            right_cpp += a == r["maj"].get<std::string>();
            right_python += b == r["maj"].get<std::string>();
        }
    }
    if (n == 0) return std::fprintf(stderr, "no clip of %s is in %s\n", list.c_str(), expected.c_str()), 1;
    std::printf("stt tests, %zu clips of %s: the C++ transcript equals the Python transcript on %zu/%zu; the bot picks the same on %zu/%zu",
                n, wav_dir.c_str(), same, n, same_pick, n);
    if (labelled)
        std::printf(" (the line's own intent on %zu from the C++ transcript, %zu from the Python one, of %zu)", right_cpp, right_python, labelled);
    std::printf("; median %.0f ms, p95 %.0f ms per clip of %.1f s\n", Percentile(ms, 0.5), Percentile(ms, 0.95), audio / n);
    return same == n ? 0 : 1;
}

// one recorded or read clip through the recognizer and the bot
bool HearAndRespond(Chat& chat, const coop::SpeechRecognizer& stt, const std::vector<float>& clip, int rate, const char* prefix,
                    std::string* err) {
    const auto t0 = Clock::now();
    std::string heard;
    if (!stt.Transcribe(clip.data(), clip.size(), rate, &heard, err)) return false;
    heard = StripPy(heard);
    std::printf("%s%s   [%.1f s of audio, recognized in %.0f ms]\n", prefix, heard.empty() ? "(nothing recognized)" : heard.c_str(),
                static_cast<double>(clip.size()) / rate, Ms(Clock::now() - t0));
    if (heard.empty()) return true;
    return chat.Respond(heard, coop::SpeechTextForClassifier(heard), err);
}

int RunSttWav(Model& m, const coop::SpeechOptions& opt, const std::vector<std::string>& files) {
    coop::SpeechRecognizer stt;
    Chat chat(m);
    std::string err;
    if (!LoadSpeech(stt, opt, &err) || !chat.Init(&err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    for (const std::string& f : files) {
        std::vector<float> x;
        int rate = 0;
        if (!ReadWav(f, &x, &rate, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        std::printf("%s\n", f.c_str());
        if (!HearAndRespond(chat, stt, x, rate, "you> ", &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    }
    return 0;
}

#ifdef COOP_WITH_MIC
void SleepMs(double ms) {
#ifdef _WIN32
    Sleep(static_cast<DWORD>(ms));
#else
    std::this_thread::sleep_for(std::chrono::duration<double, std::milli>(ms));
#endif
}

// Is the microphone the one the player means, and is it loud enough: SECONDS of it, its level, its transcript
int RunMicTest(const coop::SpeechOptions& opt, double seconds) {
    coop::SpeechRecognizer stt;
    MicCapture mic;
    std::string err, text;
    if (!LoadSpeech(stt, opt, &err) || !mic.Start(&err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    std::printf("listening for %.1f s: say something\n", seconds);
    std::fflush(stdout);
    SleepMs(300);   // more than the pre-roll: the clip starts with real audio
    mic.Begin();
    SleepMs(seconds * 1000);
    const std::vector<float> clip = mic.End();
    double sum = 0, peak = 0;
    for (float x : clip) sum += static_cast<double>(x) * x, peak = std::max(peak, std::fabs(static_cast<double>(x)));
    const double rms = clip.empty() ? 0 : std::sqrt(sum / static_cast<double>(clip.size()));
    const auto t0 = Clock::now();
    if (!stt.Transcribe(clip.data(), clip.size(), MicCapture::kSampleRate, &text, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    std::printf("mic test: %.2f s captured at %d Hz (asked for %.2f s + %.2f s before and %.2f s after), level %.1f dBFS, peak %.1f dBFS%s\n",
                static_cast<double>(clip.size()) / MicCapture::kSampleRate, MicCapture::kSampleRate, seconds, MicCapture::kPreRollSeconds,
                MicCapture::kTailSeconds, 20 * std::log10(std::max(rms, 1e-9)), 20 * std::log10(std::max(peak, 1e-9)),
                peak == 0 ? " -- pure silence: the device gives no signal (muted, or the wrong default input)" : "");
    std::printf("heard: %s   [recognized in %.0f ms]\n", text.empty() ? "(nothing recognized)" : text.c_str(), Ms(Clock::now() - t0));
    return clip.empty() ? 1 : 0;
}

#ifdef _WIN32
// The chat with a microphone. The key is read from this console (so it does nothing while another window has
// the keyboard); its release is read from the keyboard state, which the console does not report
int RunVoice(Model& m, const coop::SpeechOptions& opt, int threads) {
    const HANDLE in = GetStdHandle(STD_INPUT_HANDLE);
    DWORD mode = 0;
    if (!GetConsoleMode(in, &mode)) return std::fprintf(stderr, "--voice reads the key from a console: run it in a terminal, not through a pipe\n"), 1;
    coop::SpeechRecognizer stt;
    Chat chat(m);
    MicCapture mic;
    std::string err;
    if (!LoadSpeech(stt, opt, &err) || !chat.Init(&err) || !mic.Start(&err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    std::printf("ready (C++, ONNX Runtime %s CPU, %d threads). threshold %.2f.\n"
                "Hold SPACE and talk, release to send. Or type a line and press Enter; /why /t <x> /q. Esc quits.\n\n",
                coop::OrtBackend::RuntimeVersion().c_str(), threads, chat.brain.threshold);
    for (;;) {
        std::printf("you> ");
        std::fflush(stdout);
        wint_t c = _getwch();
        if (c == 27 || c == WEOF) return std::printf("\n"), 0;
        if (c == 0 || c == 0xE0) {   // a function or arrow key: its second code
            _getwch();
            std::printf("\r");
            continue;
        }
        if (c == L' ') {
            mic.Begin();
            const auto t0 = Clock::now();
            std::printf("(listening)");
            std::fflush(stdout);
            while (GetAsyncKeyState(VK_SPACE) & 0x8000) Sleep(5);
            const double held = Ms(Clock::now() - t0);
            const std::vector<float> clip = mic.End();
            FlushConsoleInputBuffer(in);   // the spaces the held key typed
            std::printf("\r                \r");   // over "you> (listening)"
            if (held < 200) {
                std::printf("you> (hold SPACE while you talk)\n");
                continue;
            }
            if (!HearAndRespond(chat, stt, clip, MicCapture::kSampleRate, "you> ", &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
            continue;
        }
        std::u32string typed;   // a typed line: echoed and edited here, because the console's own line input is off
        for (;; c = _getwch()) {
            if (c == L'\r' || c == L'\n') break;
            if (c == 27) {
                typed.clear();
                break;
            }
            if (c == 0 || c == 0xE0) {
                _getwch();
            } else if (c == L'\b') {
                if (!typed.empty()) {
                    typed.pop_back();
                    std::printf("\b \b");
                }
            } else if (c >= 0x20) {
                typed.push_back(static_cast<char32_t>(c));
                _putwch(static_cast<wchar_t>(c));
            }
            std::fflush(stdout);
        }
        std::printf("\n");
        const std::string line = StripPy(coop::EncodeUtf8(typed));
        if (line.empty()) continue;
        if (const int k = chat.Command(line)) {
            if (k == 2) return 0;
            continue;
        }
        if (!chat.Respond(line, line, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    }
}
#else   // macOS
// The terminal of the voice chat: its keys one at a time and unechoed, as _getwch gives them on Windows. The
// terminal's own settings are put back on every way out, Ctrl-C included.
termios g_terminal;

void RestoreTerminal() { tcsetattr(STDIN_FILENO, TCSANOW, &g_terminal); }

void RestoreTerminalAndDie(int sig) {
    RestoreTerminal();
    std::signal(sig, SIG_DFL);
    std::raise(sig);
}

// A keyboard setting of macOS in milliseconds. "InitialKeyRepeat" (how long a key is held before it repeats) and
// "KeyRepeat" (the interval after that) are stored in sixtieths of a second, and only once the user has moved
// the slider: `unset` is what macOS uses until then
int KeySettingMs(CFStringRef key, double unset) {
    double ms = unset;
    if (CFPropertyListRef v = CFPreferencesCopyAppValue(key, kCFPreferencesCurrentApplication)) {
        int ticks = 0;
        if (CFGetTypeID(v) == CFNumberGetTypeID() && CFNumberGetValue(static_cast<CFNumberRef>(v), kCFNumberIntType, &ticks))
            ms = ticks * 1000.0 / 60;
        CFRelease(v);
    }
    return static_cast<int>(ms);
}

struct KeyTerminal {
    bool raw = false;

    ~KeyTerminal() {
        if (raw) RestoreTerminal();
    }
    bool Open() {
        if (tcgetattr(STDIN_FILENO, &g_terminal) != 0) return false;
        termios t = g_terminal;
        t.c_lflag &= ~static_cast<tcflag_t>(ICANON | ECHO);
        t.c_cc[VMIN] = 1;
        t.c_cc[VTIME] = 0;
        if (tcsetattr(STDIN_FILENO, TCSANOW, &t) != 0) return false;
        raw = true;
        for (int sig : {SIGINT, SIGTERM, SIGHUP}) std::signal(sig, RestoreTerminalAndDie);
        return true;
    }
    // one byte of what was typed; false at the end of input
    static bool Read(unsigned char* b) {
        ssize_t n;
        while ((n = read(STDIN_FILENO, b, 1)) < 0 && errno == EINTR) {}
        return n == 1;
    }
    static bool Waiting(int ms) {
        pollfd in{STDIN_FILENO, POLLIN, 0};
        return poll(&in, 1, ms) > 0;
    }
    // After the byte 27: Esc itself (false), or the start of an arrow or function key (ESC [ ... letter,
    // ESC O letter), which is skipped. A key's bytes arrive together, so the rest of one is already waiting
    static bool SkipSequence() {
        if (!Waiting(25)) return false;
        unsigned char b = 0;
        if (Read(&b) && b == '[') {
            while (Read(&b) && (b < 0x40 || b > 0x7E)) {}
        } else if (b == 'O') {
            Read(&b);
        }
        return true;
    }
    // Waits until SPACE is released. A terminal reports no key-up, so the release is read from the keyboard
    // state. Where macOS does not show that state to this process (a remote terminal, secure keyboard entry),
    // the spaces the held key goes on typing stand in for it and the wait ends when they stop coming: false
    // then, and how long the key was down is not known
    static bool WaitForSpaceUp() {
        const auto down = [] { return CGEventSourceKeyState(kCGEventSourceStateCombinedSessionState, 49 /* kVK_Space */); };
        unsigned char b = 0;
        if (down()) {
            while (down())
                if (Waiting(5)) Read(&b);   // the spaces the held key types
            return true;
        }
        static const int first = KeySettingMs(CFSTR("InitialKeyRepeat"), 500) + 300, next = KeySettingMs(CFSTR("KeyRepeat"), 83) + 200;
        for (int wait = first; Waiting(wait) && Read(&b); wait = next) {}
        return false;
    }
};

// The chat with a microphone. The key is read from this terminal (so it does nothing while another window has
// the keyboard); its release is read from the keyboard state, which the terminal does not report
int RunVoice(Model& m, const coop::SpeechOptions& opt, int threads) {
    if (!isatty(STDIN_FILENO)) return std::fprintf(stderr, "--voice reads the key from a terminal: run it in one, not through a pipe\n"), 1;
    coop::SpeechRecognizer stt;
    Chat chat(m);
    MicCapture mic;
    KeyTerminal keys;
    std::string err;
    if (!LoadSpeech(stt, opt, &err) || !chat.Init(&err) || !mic.Start(&err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    if (!keys.Open()) return std::fprintf(stderr, "this terminal does not give single keys\n"), 1;
    std::printf("ready (C++, ONNX Runtime %s CPU, %d threads). threshold %.2f.\n"
                "Hold SPACE and talk, release to send. Or type a line and press Enter; /why /t <x> /q. Esc quits.\n\n",
                coop::OrtBackend::RuntimeVersion().c_str(), threads, chat.brain.threshold);
    bool told = false;
    for (;;) {
        std::printf("you> ");
        std::fflush(stdout);
        unsigned char c = 0;
        if (!keys.Read(&c) || c == 4) return std::printf("\n"), 0;   // the end of input, Ctrl-D
        if (c == 27) {
            if (!keys.SkipSequence()) return std::printf("\n"), 0;
            std::printf("\r");
            continue;
        }
        if (c == ' ') {
            mic.Begin();
            const auto t0 = Clock::now();
            std::printf("(listening)");
            std::fflush(stdout);
            const bool timed = keys.WaitForSpaceUp();
            const double held = Ms(Clock::now() - t0);
            const std::vector<float> clip = mic.End();
            tcflush(STDIN_FILENO, TCIFLUSH);   // the spaces the held key typed
            std::printf("\r                \r");   // over "you> (listening)"
            if (timed && held < 200) {
                std::printf("you> (hold SPACE while you talk)\n");
                continue;
            }
            if (!timed && !told) {
                told = true;
                std::printf("(macOS does not show the keyboard to this terminal: the release of SPACE is taken from the key's "
                            "auto-repeat, a moment late)\n");
            }
            if (!HearAndRespond(chat, stt, clip, MicCapture::kSampleRate, "you> ", &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
            continue;
        }
        std::string typed;   // a typed line, UTF-8: echoed and edited here, because the terminal's own line input is off
        for (;;) {
            if (c == '\r' || c == '\n') break;
            if (c == 27) {
                if (!keys.SkipSequence()) {
                    typed.clear();
                    break;
                }
            } else if (c == 0x7F || c == '\b') {
                if (!typed.empty()) {
                    while (typed.size() > 1 && (static_cast<unsigned char>(typed.back()) & 0xC0) == 0x80) typed.pop_back();
                    typed.pop_back();
                    std::printf("\b \b");
                }
            } else if (c >= 0x20) {
                typed.push_back(static_cast<char>(c));
                std::putchar(c);
            }
            std::fflush(stdout);
            if (!keys.Read(&c)) return std::printf("\n"), 0;
        }
        std::printf("\n");
        const std::string line = StripPy(typed);
        if (line.empty()) continue;
        if (const int k = chat.Command(line)) {
            if (k == 2) return 0;
            continue;
        }
        if (!chat.Respond(line, line, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    }
}
#endif   // _WIN32
#endif   // COOP_WITH_MIC
#endif   // COOP_WITH_STT

}  // namespace

int main(int argc, char** argv) {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
#endif
    Model m;
    m.dir = COOP_DEFAULT_MODEL_DIR;
    std::string mode = "chat", tokenize_text, speech_text_file;
    coop::OrtBackend::Options opt;
    bool parallel = true;
    coop::SpeechOptions speech;
#ifdef COOP_DEFAULT_STT_DIR
    speech.model_dir = COOP_DEFAULT_STT_DIR;
#endif
    std::vector<std::string> wavs, stt_test;
    double mic_seconds = 0;
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (a == "--model-dir" && i + 1 < argc) m.dir = argv[++i];
        else if (a == "--threads" && i + 1 < argc) opt.threads = std::atoi(argv[++i]);
        else if (a == "--no-spin") opt.allow_spinning = false;
        else if (a == "--sequential") parallel = false;
        else if (a == "--golden" || a == "--tokenizer-tests" || a == "--dialogue" || a == "--bench" || a == "--gate-tests" ||
                 a == "--decide-tests" || a == "--location-tests")
            mode = a.substr(2);
        else if (a == "--tokenize" && i + 1 < argc) mode = "tokenize", tokenize_text = argv[++i];
        else if (a == "--speech-text-tests" && i + 1 < argc) mode = "speech-text-tests", speech_text_file = argv[++i];
        else if (a == "--stt-model" && i + 1 < argc) speech.model_dir = argv[++i];
        else if (a == "--stt-threads" && i + 1 < argc) speech.threads = std::atoi(argv[++i]);
        else if (a == "--voice") mode = "voice";
        else if (a == "--mic-test" && i + 1 < argc) mode = "mic-test", mic_seconds = std::atof(argv[++i]);
        else if (a == "--stt-wav" && i + 1 < argc) mode = "stt-wav", wavs.push_back(argv[++i]);
        else if (a == "--stt-tests" && i + 3 < argc) mode = "stt-tests", stt_test = {argv[i + 1], argv[i + 2], argv[i + 3]}, i += 3;
        else {
            std::fprintf(stderr, "usage: coop_cli [--golden | --tokenizer-tests | --dialogue | --gate-tests | --decide-tests |\n"
                                 "                 --location-tests | --bench | --tokenize TEXT | --speech-text-tests FILE |\n"
                                 "                 --voice | --mic-test SECONDS | --stt-wav FILE ... | --stt-tests LIST WAVDIR EXPECTED]\n"
                                 "                [--model-dir DIR] [--threads N] [--no-spin] [--sequential]\n"
                                 "                [--stt-model DIR] [--stt-threads N]\n");
            return 2;
        }
    }
    std::string err;
    if (mode == "speech-text-tests") return RunSpeechTextTests(speech_text_file);
#ifdef COOP_WITH_MIC
    if (mode == "mic-test") return RunMicTest(speech, mic_seconds);
#endif
#ifndef COOP_WITH_STT
    if (mode == "voice" || mode == "stt-wav" || mode == "stt-tests" || mode == "mic-test")
        return std::fprintf(stderr, "this coop_cli was built without speech-to-text: sherpa-onnx was not under third_party/ "
                                    "(cpp/coop_intent/README.md)\n"), 2;
#endif
    if (!LoadConfig(m, &err)) return std::fprintf(stderr, "%s: %s\n", m.dir.c_str(), err.c_str()), 1;
    // which bot this run is about: the default directory is compiled in (and stays in the CMake cache),
    // and the checks' own lines do not tell one bot from another
    std::printf("bot: %s (%zu labels, %s gate, threshold %g)\n", m.dir.c_str(), m.cfg.labels.size(), m.cfg.gate.c_str(),
                m.cfg.threshold);
    if (mode == "tokenizer-tests") return RunTokenizerTests(m);
    if (mode == "gate-tests") return RunGateTests(m);
    if (mode == "decide-tests") return RunDecideTests(m);
    if (mode == "location-tests") return RunLocationTests(m);
    if (mode == "tokenize") {
        for (const auto& w : m.tok.Words(tokenize_text)) std::printf("word %s\n", Escaped(w).c_str());
        const auto ids = m.tok.Encode(tokenize_text);
        for (int64_t id : ids) std::printf("  %6lld %s\n", static_cast<long long>(id), Escaped(m.tok.Piece(id)).c_str());
        return 0;
    }
    const double mem0 = WorkingSetMb();
    const auto t0 = Clock::now();
    if (!LoadModels(m, opt, parallel, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    const double load_ms = Ms(Clock::now() - t0);
    {   // a model that does not fit the config (another label set) is refused here, not mid-game
        std::vector<float> logits;
        if (!m.backend->Run(m.tok.Encode("warm up"), &logits, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        if (logits.size() != m.cfg.labels.size())
            return std::fprintf(stderr, "the model gives %zu outputs, intent_config.json has %zu labels\n",
                                logits.size(), m.cfg.labels.size()), 1;
    }
    if (mode == "golden") return RunGolden(m);
    if (mode == "dialogue") return RunDialogue(m);
    if (mode == "bench") return RunBench(m, load_ms, mem0);
#ifdef COOP_WITH_STT
    if (mode == "stt-wav") return RunSttWav(m, speech, wavs);
    if (mode == "stt-tests") return RunSttTests(m, speech, stt_test[0], stt_test[1], stt_test[2]);
#ifdef COOP_WITH_MIC
    if (mode == "voice") return RunVoice(m, speech, opt.threads);
#else
    if (mode == "voice" || mode == "mic-test")
        return std::fprintf(stderr, "the microphone is read only on Windows and macOS so far; --stt-wav reads a file\n"), 2;
#endif
#endif
    return RunChat(m, opt.threads);
}
