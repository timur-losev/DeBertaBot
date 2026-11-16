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
//   coop_cli --item-tests         item_tests.jsonl: what the farmer's and the builder's orders act on, per line and
//                                 intent (a v60 bot's config has "items"; no model)
//   coop_cli --bench              latency on the golden lines, load time, memory
//   coop_cli --tokenize "text"    the words, pieces and ids of one line
//   coop_cli --serve              the bot as a service for a game: JSON lines on stdin and stdout (see RunServe);
//                                 with --no-stt without the recognizer and the microphone (typed lines only),
//                                 with --tts the bot speaks the lines the game hands it (Windows, the system's voice),
//                                 with --tts-piper DIR it hands the game each line as audio instead (Piper, voice.h);
//                                 with both, the system's voice is there for a Piper voice that does not load
//   coop_cli --speech-text-tests FILE   SpeechTextForClassifier against the Python `norm` (no model)
//   coop_cli --time-tests FILE    FindTimePhrase against scripts/coop/time_phrase.py (time_phrase_tests.jsonl; no model)
// with speech-to-text (a build that found sherpa-onnx under third_party/):
//   coop_cli --voice              the chat with a microphone: hold SPACE and talk, release to send; a typed
//                                 line still works (Windows, macOS)
//   coop_cli --stt-wav FILE       one clip (16-bit PCM WAV) through the recognizer and the bot; may be repeated
//   coop_cli --mic-test SECONDS   the default microphone for that long: the level it heard and the transcript
//                                 (Windows, macOS; no bot is loaded)
//   coop_cli --stt-tests LIST WAVDIR EXPECTED   the C++ transcripts against the Python package's: LIST is a
//                                 list of {id, wav} (scripts/coop/stt/lines.json), EXPECTED a run_stt.py output
//   coop_cli --tts-piper DIR --tts-demo OUTDIR [--tts-text TEXT] [--tts-speaker A,B,...]   one WAV per speaker of a
//                                 Piper voice saying TEXT (no bot is loaded): to choose the bot's voice by ear
// the bot's voice (voice.h): --tts-piper DIR (a sherpa-onnx Piper export), --tts-speaker NAME ("p311" or a number),
//          --tts-speed X (> 1 faster), --tts-threads N (default 1; given, the player's language's voice gets as many, else
//          at least 4), --tts-provider cpu|cuda|auto (default cpu: the voices on the GPU with sherpa-onnx's CUDA build next
//          to the exe and CUDA 12 + cuDNN 9 on the machine, else on the CPU; auto: a Kokoro voice on the GPU, Piper on the CPU)
// with the decoder (a build that found llama.cpp under third_party/, tools/setup_llama.ps1):
//   --chain DIR                   in the chat, --voice, --stt-wav and --serve: a line that gives several orders, or
//                                 leans on what was said before it, is rewritten as orders that stand by themselves
//                                 (rewriter.h; DIR is export_chain_cpp.py's output); /chain switches it off and on.
//                                 --decoder-cpu keeps the decoder off the GPU, --decoder-threads N (default 4)
//   coop_cli --chain DIR --chain-tests   chain_tests.jsonl: the decoder's turn text, the router's probability against
//                                 PyTorch's, the decoder's answers against llama.cpp's own server (with --decoder-cpu:
//                                 the file's answers are the CPU's)
//   --language en|ru|es           the player's language (default en). ru and es: every line goes to the decoder of --chain
//                                 (chain v62 or later: trained on three languages), which writes English orders; the
//                                 router is not asked. Speech: --stt-model with Parakeet TDT 0.6B v3 (25 languages)
//   --decoder-every-line          English lines go to the decoder too, every one (the router is not asked), as ru and es
//   --decider DIR                 a second reader of every line beside the ensemble (decider.h: decider-2b with the
//                                 bot's LoRA, GGUF; DIR is scripts/coop/decider/export_game.py's output). Off without it.
//                                 --decider-mode avg (default: the two readers' probabilities averaged) | only (the
//                                 decider's alone), --decider-threads N (default 8), --decider-gpu-layers N (default 0)
//   coop_cli --decider DIR --decider-tests FILE   the line's tokens against upstream's tokenizer and the probabilities
//                                 against decider_eval's (export_game.py writes FILE)
// the long-term memory (bot_memory.h, teach.h; a build that found Wick, CMakeLists.txt):
//   --memory FILE                 in --serve: what the player taught the bot, kept in FILE (made when missing; one file per
//                                 player): "I meant ...", "not that", names and colours of things, "forget ..."; the
//                                 serve commands teach, forget and recall. The bot's name and the player's too
//   --name-chance P               how often the bot says the player's name, in percent of the short lines it may go into
//                                 (default 25, never on two of three lines in a row; 100: every one, for tests; 0: never)
//   coop_cli --memory-dump FILE   everything FILE keeps, as JSON (no model): the lines it holds are rows for a training round
//   coop_cli --teach-tests FILE   the teaching lines' rules and the memory's text rules (tools/teach_tests.json; no model)
//   coop_cli --memory-store-tests DIR   the memory's store in a folder of its own, made anew (no model): keeping, reading
//                                 back in a new store, the matching rule, doubts, a file held twice, compaction, a cut-short
//                                 compaction, an unreadable file, a folder named in Cyrillic
// every mode first prints the bot it runs on (directory, labels, gate, threshold)
// options: --model-dir DIR (export_cpp.py output: intent_config.json, vocab.tsv and the model files
//          it lists under "members"), --threads N (per model, default 4),
//          --stt-model DIR (a sherpa-onnx export of Parakeet TDT), --stt-threads N (default 2),
//          --no-spin (ONNX Runtime worker threads sleep between calls), --sequential (an ensemble's
//          members one after another instead of one thread each)
#include <algorithm>
#include <cctype>
#include <array>
#include <atomic>
#include <chrono>
#include <clocale>
#include <cmath>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <filesystem>
#include <functional>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <memory>
#include <mutex>
#include <numeric>
#include <random>
#include <set>
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
#include "coop_intent/bot_memory.h"
#include "coop_intent/decider.h"
#include "coop_intent/intent_model.h"
#include "coop_intent/bro.h"
#include "coop_intent/localize.h"
#include "coop_intent/rewriter.h"
#include "coop_intent/speech.h"
#include "coop_intent/talker.h"
#include "coop_intent/teach.h"
#include "coop_intent/time_phrase.h"
#include "coop_intent/tokenizer.h"
#include "coop_intent/unicode.h"
#include "coop_intent/voice.h"
#include "coop_intent/world.h"
#include "nlohmann/json.hpp"
// the microphone modes (--voice, --mic-test) exist where tools/ has a MicCapture
#if defined(COOP_WITH_STT) && (defined(_WIN32) || defined(__APPLE__))
#define COOP_WITH_MIC
#include "mic_capture.h"
#endif
#ifdef _WIN32
#include "tts.h"
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
            for (const auto& list : c.locations.words) {
                c.locations.has_pointers = c.locations.has_pointers || coop::LocationVocab::PointerList(list.first);
                c.locations.has_it = c.locations.has_it || coop::LocationVocab::ItList(list.first);   // rule set v8
                c.locations.has_means = c.locations.has_means || coop::LocationVocab::MeansList(list.first);   // rule set v9
            }
        }
        if (j.contains("items")) {   // what the farmer's and the builder's orders act on (scripts/coop/items_v60.json): v60 bots
            const json& I = j.at("items");
            c.has_items = true;
            c.items.version = I.at("version").get<int>();
            c.items.intents = I.at("intents").get<std::vector<std::string>>();
            c.items.verbs = I.at("verbs").get<std::unordered_map<std::string, std::vector<std::string>>>();
            c.items.keeps_object = I.at("item_keeps_object").get<std::vector<std::string>>();
            c.items.crop_intents = I.at("crop_intents").get<std::vector<std::string>>();
            c.items.max_words = I.at("max_words").get<int>();
            for (auto& [key, value] : I.items())   // every other list is a word list the rules read by its name
                if (value.is_array() && key != "intents" && key != "item_keeps_object" && key != "crop_intents")
                    c.items.lists[key] = value.get<std::vector<std::string>>();
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

// ---- the world state (world.h) as JSON: what the game hands over, and what the tests carry ----

std::string StrOrEmpty(const json& j, const char* key) {
    const auto it = j.find(key);
    return it == j.end() || it->is_null() ? std::string() : it->get<std::string>();
}

bool ParsePin(const json& j, coop::WorldPin* p, std::string* err) {
    try {
        p->id = j.at("id").get<std::string>();
        p->entity = StrOrEmpty(j, "entity");
        p->bearing = j.value("bearing", 0.0);
        p->distance = j.value("distance", 0.0);
        p->elevation = j.value("elevation", 0.0);
    } catch (const std::exception& e) {
        return *err = std::string("pin: ") + e.what(), false;
    }
    return true;
}

// what the bot deals with, as the game sends it (decoder v65): {"holding", "standing_on", "car_m" (null or left out: no
// car), "last": {"thing", "m"}}
coop::Scene SceneFromJson(const json& s) {
    coop::Scene sc;
    sc.holding = StrOrEmpty(s, "holding");
    sc.standing_on = StrOrEmpty(s, "standing_on");
    if (s.contains("car_m") && !s["car_m"].is_null()) sc.has_car = true, sc.car_m = s["car_m"].get<double>();
    if (s.contains("last") && s["last"].is_object()) sc.last = StrOrEmpty(s["last"], "thing"), sc.last_m = s["last"].value("m", 0.0);
    sc.failed = StrOrEmpty(s, "failed");   // decoder v67: "<order>, <why>" of an order the bot could not carry out lately
    return sc;
}

bool ParseWorld(const json& j, coop::WorldState* w, std::string* err) {
    *w = coop::WorldState();
    try {
        for (const json& e : j.value("entities", json::array())) {
            coop::WorldEntity x;
            x.id = e.at("id").get<std::string>();
            x.key = StrOrEmpty(e, "key");   // the long-term memory's name for the thing (world.h)
            x.object = StrOrEmpty(e, "object");
            x.qualifier = StrOrEmpty(e, "qualifier");
            x.zone = StrOrEmpty(e, "zone");
            x.bearing = e.value("bearing", 0.0);
            x.distance = e.value("distance", 0.0);
            x.elevation = e.value("elevation", 0.0);
            x.tags = e.value("tags", std::vector<std::string>{});
            w->entities.push_back(std::move(x));
        }
        if (j.contains("player_pin") && !j["player_pin"].is_null()) {
            w->has_player_pin = true;
            if (!ParsePin(j["player_pin"], &w->player_pin, err)) return false;
        }
        if (j.contains("bot_pin") && !j["bot_pin"].is_null()) {
            w->has_bot_pin = true;
            if (!ParsePin(j["bot_pin"], &w->bot_pin, err)) return false;
        }
        w->player_gaze = StrOrEmpty(j, "player_gaze");
        if (j.contains("player")) w->player_downed = j["player"].value("downed", false);
        if (j.contains("bot")) {
            w->bot_stance = j["bot"].value("stance", std::string("stand"));
            w->bot_items = j["bot"].value("items", std::vector<std::string>{});
            w->bot_busy = j["bot"].value("busy", false);
            w->bot_name = StrOrEmpty(j["bot"], "name");   // the game's name of the bot (2026-10-31)
        }
        // where the crosshair was while the talk key was down: [{"t": seconds since the key went down, "gaze": an entity id or null}]
        if (j.contains("talk_trail") && j["talk_trail"].is_array()) {
            for (const json& s : j["talk_trail"]) {
                const std::string g = StrOrEmpty(s, "gaze");
                bool known = g.empty();
                for (const coop::WorldEntity& e : w->entities) known = known || e.id == g;
                if (known) w->talk_trail.emplace_back(s.value("t", 0.0), g);
            }
            std::sort(w->talk_trail.begin(), w->talk_trail.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
        }
        if (j.contains("scene") && j["scene"].is_object()) {
            const coop::Scene sc = SceneFromJson(j["scene"]);
            w->scene = coop::SceneLine(sc);
            w->scene_standing = !sc.standing_on.empty();
            w->scene_car_near = sc.has_car && sc.car_m <= coop::kSceneCarNear;
        }
        if (j.contains("time") && !j["time"].is_null()) {   // the game's clock: without it the planner keeps no context
            w->has_time = true;
            w->time = j["time"].get<double>();
        }
        w->map = StrOrEmpty(j, "map");   // the long-term memory keeps names and colours per map
        if (j.contains("catalog") && !j["catalog"].is_null()) {   // per intent with an item, what the game has (the v60 bots)
            for (auto& [intent, entries] : j["catalog"].items()) {
                std::vector<coop::CatalogEntry> list;
                for (const json& e : entries) list.push_back({e.at("id").get<std::string>(), e.at("words").get<std::vector<std::string>>()});
                w->catalog.emplace_back(intent, std::move(list));
            }
        }
    } catch (const std::exception& e) {
        return *err = std::string("world state: ") + e.what(), false;
    }
    return true;
}

// a grounding, an order, a question as one comparable string each
std::string GroundStr(const std::vector<coop::Grounding>& g) {
    std::string s;
    for (const coop::Grounding& x : g) {
        s += x.status + "/" + (x.entity.empty() ? "-" : x.entity) + "/" + (x.via.empty() ? "-" : x.via) + "/[";
        for (size_t i = 0; i < x.candidates.size(); ++i) s += (i ? "," : "") + x.candidates[i];
        s += "];";
    }
    return s;
}
std::string GroundStr(const json& g) {
    std::string s;
    for (const json& x : g) {
        s += x["status"].get<std::string>() + "/" + LabelStr(x["entity"]) + "/" + LabelStr(x["via"]) + "/[";
        const auto c = x["candidates"].get<std::vector<std::string>>();
        for (size_t i = 0; i < c.size(); ++i) s += (i ? "," : "") + c[i];
        s += "];";
    }
    return s;
}
// with_object: the test row has the order's "object" (bot v56); an older row is compared without it. An order with an
// item (the v60 bots) adds it and its catalogue entry
std::string OrderStr(const coop::PlannerResult& r, const Model& m, const coop::LocationMatcher& places, bool with_object) {
    if (!r.has_order) return "-";
    const coop::Order& o = r.order;
    std::string s = m.cfg.labels[static_cast<size_t>(o.intent)] + "/" + (o.entity.empty() ? "-" : o.entity) + "/[";
    for (size_t i = 0; i < o.candidates.size(); ++i) s += (i ? "," : "") + o.candidates[i];
    const char* dir = coop::PlaceDirectionName(o.direction);
    const char* ptr = coop::PlacePointerName(o.pointer);
    return s + "]/" + (*dir ? dir : "-") + "/" + (o.zone >= 0 ? places.ZoneId(o.zone) : "-") + "/" + (*ptr ? ptr : "-") + "/" + (o.other ? "1" : "0") +
           "/" + (o.via.empty() ? "-" : o.via) + "/" + (o.nearby ? "1" : "0") +
           (with_object ? "/" + (o.object >= 0 ? places.ObjectId(o.object) : std::string("-")) : std::string()) +
           (o.has_item ? "/item:" + (o.item.empty() ? std::string("-") : o.item) + "/" + (o.item_id.empty() ? std::string("-") : o.item_id) : std::string()) +
           (o.has_means ? "/means:" + (o.means.empty() ? std::string("-") : o.means) + "/" + (o.means_object >= 0 ? places.ObjectId(o.means_object) : std::string("-"))
                        : std::string());
}
std::string OrderStr(const json& o) {
    if (o.is_null()) return "-";
    std::string s = o["intent"].get<std::string>() + "/" + LabelStr(o["entity"]) + "/[";
    const auto c = o["candidates"].get<std::vector<std::string>>();
    for (size_t i = 0; i < c.size(); ++i) s += (i ? "," : "") + c[i];
    // a file written before the markerless rules has neither key: it is stale, and says so instead of crashing
    return s + "]/" + LabelStr(o["direction"]) + "/" + LabelStr(o["zone"]) + "/" + LabelStr(o["pointer"]) + "/" + FlagStr(o["other"]) +
           "/" + (o.contains("via") ? LabelStr(o["via"]) : std::string("(no via: regenerate world_tests.jsonl)")) + "/" +
           (o.contains("near") ? FlagStr(o["near"]) : std::string("?")) + (o.contains("object") ? "/" + LabelStr(o["object"]) : std::string()) +
           (o.contains("item") ? "/item:" + LabelStr(o["item"]) + "/" + LabelStr(o["item_id"]) : std::string()) +
           (o.contains("means") ? "/means:" + LabelStr(o["means"]) + "/" + LabelStr(o["means_object"]) : std::string());
}
// the frame of the previous order: intent / it had a place / the place's entity / how it was found / when / it keeps
// what the order's own line called the place
std::string FrameStr(const coop::Memory& mem, const Model& m) {
    const coop::Memory::Frame& f = mem.frame;
    if (!f.has) return "-";
    char when[32];
    std::snprintf(when, sizeof(when), "%.3f", f.time);
    return m.cfg.labels[static_cast<size_t>(f.intent)] + "/" + (f.has_target ? "1" : "0") + "/" +
           (f.has_target && !f.ground.entity.empty() ? f.ground.entity : "-") + "/" + (f.has_target && !f.ground.via.empty() ? f.ground.via : "-") + "/" +
           (f.has_time ? when : "-") + "/" + (f.has_said ? "1" : "0");
}
std::string FrameStr(const json& f) {
    if (f.is_null()) return "-";
    char when[32];
    if (!f["time"].is_null()) std::snprintf(when, sizeof(when), "%.3f", f["time"].get<double>());
    return f["intent"].get<std::string>() + "/" + FlagStr(f["has_target"]) + "/" + LabelStr(f["entity"]) + "/" + LabelStr(f["via"]) + "/" +
           (f["time"].is_null() ? "-" : when) + "/" + (f.contains("said") ? FlagStr(f["said"]) : std::string("(no said: regenerate world_tests.jsonl)"));
}
std::string QuestionStr(const coop::Memory& mem, const Model& m) {
    if (!mem.has_question) return "-";
    const coop::Memory::Question& q = mem.question;
    std::string s = q.kind + "/" + m.cfg.labels[static_cast<size_t>(q.intent)] + "/" + std::to_string(q.k) + "/" + (q.other ? "1" : "0") + "/" +
                    (q.queued ? "1" : "0") + "/[";
    for (size_t i = 0; i < q.candidates.size(); ++i) s += (i ? "," : "") + q.candidates[i];
    return s + "]/" + std::to_string(q.offered);
}
std::string QuestionStr(const json& q) {
    if (q.is_null()) return "-";
    std::string s = q["kind"].get<std::string>() + "/" + q["intent"].get<std::string>() + "/" + std::to_string(q["k"].get<int>()) + "/" +
                    FlagStr(q["other"]) + "/" + FlagStr(q["queued"]) + "/[";
    const auto c = q["candidates"].get<std::vector<std::string>>();
    for (size_t i = 0; i < c.size(); ++i) s += (i ? "," : "") + c[i];
    return s + "]/" + std::to_string(q["offered"].get<int>());
}

// ---- checks ----------------------------------------------------------------------------------

// world_tests.jsonl (gen_world_tests.py): the planner on scripted worlds and conversations, no model
int RunWorldTests(Model& m) {
    const auto rows = ReadJsonl(m.dir + "/world_tests.jsonl");
    std::string err;
    size_t n = 0, ok = 0, scenarios = 0, refusals = 0;
    for (const json& sc : rows) {
        if (sc.contains("refused")) {   // a world the rules must refuse (or the example they must accept)
            coop::BotBrain brain;
            coop::Planner planner;
            if (!brain.Init(m.cfg, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
            planner.Init(&brain);
            coop::WorldState w;
            const bool accepted = ParseWorld(sc["world"], &w, &err) && planner.SetWorld(w, &err);
            ++n;
            ++refusals;
            ok += accepted == sc["accepted"].get<bool>();
            if (accepted != sc["accepted"].get<bool>())
                std::printf("  world \"%s\": python %s, c++ %s%s\n", sc["refused"].get<std::string>().c_str(),
                            sc["accepted"].get<bool>() ? "accepted" : "refused", accepted ? "accepted" : "refused",
                            accepted ? "" : (" (" + err + ")").c_str());
            continue;
        }
        ++scenarios;
        coop::IntentConfig cfg = m.cfg;
        cfg.gate = sc["gate"].get<std::string>();
        coop::BotBrain brain;
        coop::Planner planner;
        if (!brain.Init(cfg, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        brain.threshold = sc["threshold"].get<double>();
        planner.Init(&brain);
        coop::WorldState w;
        if (!ParseWorld(sc["world"], &w, &err) || !planner.SetWorld(w, &err))
            return std::fprintf(stderr, "scenario %zu: %s\n", scenarios, err.c_str()), 1;
        for (const json& s : sc["steps"]) {
            std::vector<float> p;
            for (double x : s["probs"].get<std::vector<double>>()) p.push_back(static_cast<float>(x));
            const std::string text = s["text"];
            if (s.contains("world")) {   // the world as the game sends it before this line: time passed, the pin moved
                coop::WorldState ws;
                if (!ParseWorld(s["world"], &ws, &err) || !planner.SetWorld(ws, &err))
                    return std::fprintf(stderr, "scenario %zu, %s: %s\n", scenarios, Escaped(text).c_str(), err.c_str()), 1;
            }
            const coop::PlannerResult r = planner.Step(text, p, s.value("continued", false));   // a further order of one line
            const std::string intent = r.intent >= 0 ? cfg.labels[static_cast<size_t>(r.intent)] : "?";
            const std::string pending = brain.Pending() >= 0 ? cfg.labels[static_cast<size_t>(brain.Pending())] : "-";
            const coop::WorldState& world = planner.World();
            std::string why;
            auto same = [&](const char* what, const std::string& got, const std::string& want) {
                if (got != want) why += std::string(why.empty() ? "" : "; ") + what + ": python " + want + ", c++ " + got;
            };
            same("action", r.action, s["action"].get<std::string>());
            same("intent", intent, s["intent"].get<std::string>());
            if (std::fabs(r.prob - s["prob"].get<double>()) > 1e-5) why += "; prob";
            if (!s["say"].is_null()) same("say", r.say, s["say"].get<std::string>());
            same("adjusted", r.adjusted ? "1" : "0", FlagStr(s["adjusted"]));
            same("ground", GroundStr(r.ground), GroundStr(s["ground"]));
            same("order", OrderStr(r, m, brain.Places(), !s["order"].is_null() && s["order"].contains("object")), OrderStr(s["order"]));
            same("question", QuestionStr(planner.Mem(), m), QuestionStr(s["question"]));
            same("pending", pending, LabelStr(s["pending"]));
            same("pending_entity", planner.PendingEntity().empty() ? "-" : planner.PendingEntity(), LabelStr(s["pending_entity"]));
            same("pending_here", planner.PendingHere() ? "1" : "0", s.contains("pending_here") ? FlagStr(s["pending_here"]) : std::string("?"));
            same("pending_near", planner.PendingNear() ? "1" : "0", s.contains("pending_near") ? FlagStr(s["pending_near"]) : std::string("?"));
            same("last_entity", planner.Mem().last_entity.empty() ? "-" : planner.Mem().last_entity, LabelStr(s["last_entity"]));
            if (s.contains("frame")) same("frame", FrameStr(planner.Mem(), m), FrameStr(s["frame"]));
            same("bot_pin", world.has_bot_pin ? world.bot_pin.entity : "-", LabelStr(s["bot_pin"]));
            ++n;
            ok += why.empty();
            if (!why.empty()) std::printf("  scenario %zu, %s: %s\n", scenarios, Escaped(text).c_str(), why.c_str());
        }
    }
    std::printf("world tests, %zu scenarios, %zu steps and %zu worlds to accept or refuse: C++ planned what the Python planner "
                "planned on %zu/%zu\n", scenarios, n - refusals, refusals, ok, n);
    return ok == n ? 0 : 1;
}

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
// item_tests.jsonl (gen_tests.py, a bot with "items"): items.find per line and intent against the Python rules
int RunItemTests(Model& m) {
    const auto rows = ReadJsonl(m.dir + "/item_tests.jsonl");
    std::string err;
    coop::LocationMatcher places;
    coop::ItemMatcher items;
    if (!m.cfg.has_locations || !m.cfg.has_items) return std::fprintf(stderr, "intent_config.json has no \"locations\" or no \"items\"\n"), 1;
    if (!places.Init(m.cfg.locations, &err) || !items.Init(m.cfg.items, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    size_t ok = 0, with_item = 0;
    int shown = 0;
    for (const json& r : rows) {
        const std::string text = r["text"], intent = r["intent"];
        const coop::ItemFound f = items.Find(text, intent, places);
        const std::string got = (f.has_item ? f.item : "-") + "/" + std::to_string(f.first) + "/" + std::to_string(f.last) + "/" + std::to_string(f.verb);
        const std::string want = LabelStr(r["item"]) + "/" + std::to_string(r["first"].get<int>()) + "/" + std::to_string(r["last"].get<int>()) + "/" +
                                 std::to_string(r["verb"].get<int>());
        with_item += f.has_item;
        if (got == want)
            ++ok;
        else if (shown++ < 12)
            std::printf("  %s (%s)\n    python %s\n    c++    %s\n", Escaped(text).c_str(), intent.c_str(), want.c_str(), got.c_str());
    }
    std::printf("item tests: %zu lines and intents, %zu with an item: C++ found what Python found on %zu/%zu\n", rows.size(), with_item, ok, rows.size());
    return ok == rows.size() && !rows.empty() ? 0 : 1;
}

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
    {"REVIVE_ME", {"Coming to get you!", "Hold on, reviving.", "On my way, stay down."}},   // bots v4 ... v55
    {"HELP_INTERACTION", {"Coming to help.", "On my way to you.", "Hold on, coming."}},     // bot v56
    {"GO_BACK", {"Going back.", "Heading back.", "Back to where I was."}},                  // bot v56
    {"SWITCH_WEAPON", {"Switching weapons.", "Swapping.", "Changing guns."}},             // bot v57
    {"RELOAD", {"Reloading.", "Changing mags.", "Reloading, cover me."}},
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
    {"GET_IN", {"Getting in.", "Hopping in.", "In the car."}},
    {"GET_OUT", {"Getting out.", "Hopping out.", "Out of the car."}},
    {"REPEAT", {"Again.", "Trying again.", "One more time."}},
    // the v60 bots: the farmer and the builder
    {"PLANT_CROP", {"Planting.", "Getting it in the ground.", "Sowing."}},
    {"WATER", {"Watering.", "On the watering.", "Giving them water."}},
    {"HARVEST", {"Harvesting.", "Bringing it in.", "Picking it."}},
    {"TILL", {"Working the ground.", "On the soil.", "Getting the ground ready."}},
    {"FEED", {"Feeding them.", "On the feeding.", "Getting them fed."}},
    {"COLLECT", {"Collecting.", "Gathering it up.", "On it, collecting."}},
    {"DELIVER", {"Bringing it.", "On the way with it.", "Carrying it over."}},
    {"BUILD", {"Building.", "Putting it up.", "On the build."}},
    {"REPAIR", {"Repairing.", "Fixing it.", "Patching it up."}},
    {"DEMOLISH", {"Tearing it down.", "Taking it apart.", "Demolishing."}},
    // the v62 bots: the bot that talks. Whether it sees a thing or the player is the game's answer (its line of sight):
    // the brain says nothing for those. Small talk is answered by what the line asks (kTalk)
    {"SEE_THING", {""}},
    {"SEE_ME", {""}},
    {"PRAISE", {"Thanks!", "Appreciate it.", "Just doing my job.", "Couldn't have done it without you.", "Thanks, you too."}},
    {"KILL_YOURSELF", {"Respawn timer's too long for that.", "Nice try. Who'd cover you then?", "Request denied. I like being alive.",
                       "Not today. You'd miss me.", "I'll pass. Somebody has to watch your back."}},
    // the v64 bots (spec v63 + v64): what it sees and how it is are the game's answer (the reply carries "state")
    {"MELEE", {"Going hands-on.", "He's getting a beating.", "On him."}},
    {"HOLSTER", {"Putting it away.", "Hands free.", "Weapon away."}},
    {"STATUS_REPORT", {""}},
    {"BODY_STATE", {""}},
    {"PUSH", {"Pushing it.", "Shoving it over.", "Moving it."}},
    {"ROLL", {"Rolling it.", "Rolling it over.", "On it, rolling."}},
    {"DROP", {"Putting it down.", "Setting it down.", "Dropping it."}},
    // the v66 bots: out of the player's way; what the thing looked at is, is the game's answer (the reply carries "state")
    {"GIVE_WAY", {"Out of your way.", "Making room.", "Stepping aside."}},
    {"WHAT_IS_IT", {""}},
    // round v70: the game says what it does with the car and the body (OVCoopBotDriving.cpp, UOVBodyStateComponent): no word here
    {"DRIVE", {""}},
    {"BODY_MOVE", {""}},
    {"BODY_COMBO", {""}},
};
// SMALL_TALK (bot v62): the answer by what the line asks, the first kind whose words it has; none: kTalk "other"
const std::vector<std::pair<std::string, std::vector<std::string>>> kTalkWords = {
    {"thanks", {"thank", "thanks", "thx", "cheers", "appreciate"}},
    {"sorry", {"sorry", "my bad", "apologize", "apologies", "oops"}},
    {"bye", {"bye", "goodbye", "see you", "see ya", "later", "good night", "peace", "i'm out", "gotta go"}},
    {"how", {"how are", "how's it", "how is it", "how you doing", "how are things", "how do you feel", "how was", "how's your",
             "what's up", "whats up", "sup", "what's new", "you okay", "you ok", "are you okay", "are you alright", "you alright",
             "alive"}},
    {"there", {"you there", "are you there", "still there", "you with me", "can you hear me", "you hear me", "talking to me"}},
    {"who", {"who are you", "your name", "what are you", "are you a bot", "are you human", "are you real", "how old", "where are you from"}},
    {"joke", {"joke", "funny", "make me laugh"}},
    {"bored", {"bored", "boring", "talk to me", "say something", "tell me something"}},
    {"hello", {"hello", "hey", "hi", "yo", "good morning", "good evening", "morning", "greetings", "howdy"}},
};
const std::unordered_map<std::string, std::vector<std::string>> kTalk = {
    {"thanks", {"Anytime.", "No problem.", "That's what I'm here for."}},
    {"sorry", {"No worries.", "It happens.", "All good."}},
    {"bye", {"See you.", "Later.", "Take care out there."}},
    {"how", {"Doing fine. Ready to work.", "All good here.", "Still in one piece."}},
    {"there", {"Right here.", "Still here.", "I hear you."}},
    {"who", {"Just your teammate. A bot, and proud of it.", "Your squad mate. I follow orders and watch your back."}},
    {"joke", {"Why did the grenade get promoted? It really blew them away.", "I'd tell you a sniper joke, but you wouldn't see it coming."}},
    {"bored", {"Let's go find some trouble then.", "Say the word and we move."}},
    {"hello", {"Hey.", "Hey, good to see you.", "Hi. Ready when you are."}},
    {"other", {"Ha. Good one.", "Sure thing.", "Noted."}},
};

// a phrase of the list in the line, as whole words (lower case)
bool PhraseIn(const std::string& text, const std::vector<std::string>& phrases) {
    std::string t;
    for (char c : text) t += static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
    const std::string padded = " " + t + " ";
    for (const std::string& w : phrases)
        for (size_t at = padded.find(w); at != std::string::npos; at = padded.find(w, at + 1)) {
            const char before = padded[at - 1], after = at + w.size() < padded.size() ? padded[at + w.size()] : ' ';
            if (!std::isalnum(static_cast<unsigned char>(before)) && !std::isalnum(static_cast<unsigned char>(after))) return true;
        }
    return false;
}

const std::vector<std::string>& TalkLines(const std::string& text) {
    for (const auto& kind : kTalkWords)
        if (PhraseIn(text, kind.second)) return kTalk.at(kind.first);
    return kTalk.at("other");
}

// Questions about the bot itself that only the game can answer (2026-10-24, the owner): what it sees and senses now (the
// labelled things and the enemy), and how its body is (health, heat, cold, gas, ammo). The brain says nothing for them:
// the reply carries "state" and the game's server answers from the bot. A question about one thing ("are you hurt?",
// "тебе не жарко?" -> "are you hot") is that thing; "how is it going?" and the like, everything at once
const std::vector<std::pair<std::string, std::vector<std::string>>> kStateWords = {
    {"seen", {"what do you see", "what can you see", "what are you looking at", "what are you seeing", "what's around", "what is around",
              "anything around", "what's there", "what is there", "what's out there", "see anything", "anything there",
              "what do you notice", "anything interesting", "what's ahead", "what is ahead"}},
    {"hurt", {"hurt", "wounded", "injured", "health", "are you hit", "you hit", "bleeding", "hp", "damaged", "in pain"}},
    {"heat", {"hot", "heat", "burning", "on fire", "too warm", "warm", "sweating", "overheating"}},
    {"cold", {"cold", "freezing", "frozen", "chilly", "chilled"}},
    {"gas", {"gas", "poison", "poisoned", "toxic", "breathe", "breathing", "smell", "smells", "choking", "fumes"}},
    {"ammo", {"ammo", "ammunition", "bullets", "rounds left", "magazine", "how many rounds", "rounds", "cartridges"}},
    // what it is doing and where it is going (2026-11-01, the owner: «Ты куда пошёл?» was "Got it."; "he should answer where
    // he is going and so on"): the game says its order, its place, its plan step
    {"doing", {"where are you going", "where you going", "where're you going", "where are you headed", "where are you heading",
               "where you headed", "where are you off to", "where did you go", "where'd you go", "where are you", "what are you doing",
               "what you doing", "whatcha doing", "what are you up to", "what are you busy with", "what are you working on",
               "what's your task", "what is your task", "what's your order", "what is your order"}},
};

// a Russian or Spanish line as the own-words checks read it: lower case (Cyrillic and accents included), ё as е, the stops
// and commas spaces, a space at each end
std::string OwnWords(const std::string& line) {
    std::u32string u = coop::DecodeUtf8(line);
    for (char32_t& c : u) {
        if (c >= U'A' && c <= U'Z') c = c - U'A' + U'a';
        else if (c >= U'А' && c <= U'Я') c = c - U'А' + U'а';
        else if (c == U'Ё' || c == U'ё') c = U'е';
    }
    std::u32string t;
    for (char32_t c : u) {
        const char32_t x = (c == U'?' || c == U'¿' || c == U'!' || c == U'¡' || c == U',' || c == U'.' || c == U':' || c == U';') ? U' ' : c;
        if (!(x == U' ' && !t.empty() && t.back() == U' ')) t += x;
    }
    while (!t.empty() && t.back() == U' ') t.pop_back();
    while (!t.empty() && t.front() == U' ') t.erase(t.begin());
    return " " + coop::EncodeUtf8(t) + " ";
}
size_t OwnWordCount(const std::string& padded) {
    size_t n = 0;
    for (size_t i = 1; i < padded.size(); ++i) n += padded[i] != ' ' && padded[i - 1] == ' ';
    return n;
}
bool AnyIn(const std::string& padded, std::initializer_list<const char*> parts) {
    for (const char* part : parts)
        if (padded.find(part) != std::string::npos) return true;
    return false;
}

// "where are you going?", "what are you doing?" as a Russian or Spanish player asks it, in a short line: the decoder writes
// «ты куда пошёл?» as "Where did you go?" (small talk to the classifier) and a misheard «пош<unk>л» as anything
bool DoingInOwnWords(const std::string& line) {
    const std::string s = OwnWords(line);
    if (OwnWordCount(s) > 6) return false;
    // «где ты живёшь?», «где ты работаешь?»: about one's life (StateQuestion's kLifeAsked), not where it is going now
    if (AnyIn(s, {" живешь ", " живете ", " живет ", " работаешь ", " работаете ", " работает ", " родился ", " родилась ", " родились ",
                  " учишься ", " учитесь ", " vives ", " vive ", " trabajas ", " trabaja ", " naciste "}))
        return false;
    return AnyIn(s, {" куда идешь ", " куда ты идешь ", " ты куда ", " куда ты ", " куда пошел ", " куда собрался ", " куда направляешься ",
                     " что делаешь ", " что ты делаешь ", " чем занят ", " чем ты занят ", " где ты ", " ты где ", " зачем ты туда ",
                     " зачем туда ", " зачем идешь ", " зачем ты идешь ", " куда ты направляешься ",
                     " adonde vas ", " adónde vas ", " a donde vas ", " a dónde vas ", " que haces ", " qué haces ", " que estas haciendo ",
                     " qué estás haciendo ", " donde estas ", " dónde estás "});
}

// "close the door" in the player's own words: the decoder writes «закрывай дверь» as "Cover the door." (decoder v68), and the
// classifier has no order to close (2026-11-01, the owner: «Закрой дверь» was HOLD_ANGLE, «Закрывай дверь» OPEN_FIRE).
// «прикрой» only with a door: «прикрой меня» covers the player
bool CloseInOwnWords(const std::string& line) {
    const std::string s = OwnWords(line);
    const bool shut = AnyIn(s, {" закрой ", " закрывай ", " закройте ", " закрывайте ", " закрыть ", " захлопни ", " cierra ", " cierre ",
                                " cerrad ", " ciérrala ", " cierrala ", " ciérralo ", " cierralo "});
    const bool door = AnyIn(s, {" двер", " окн", " окош", " ворот", " люк", " ее ", " его ", " puerta", " ventana", " portón", " porton"});
    return (shut && door) || AnyIn(s, {" прикрой дверь ", " прикрой двери ", " прикрой окно "});
}

// a flank said in the player's own words: the decoder writes «зайди через главную дверь», «пройди через проход» as "Flank
// through the main door." (decoder v68; the owner, 2026-11-01). With no word of a flank, and a door, a passage or a room said,
// it is a way in
// "sit (down) on the bench", "take a seat on this bench", "have a seat at the bench" (2026-11-14, the owner: the benches labelled
// «чтобы на них можно было сидеть»; E2E people_adventure_look: «сядь на эту лавочку» -> "sit down on this bench" -> GET_IN 0.64,
// "Ещё раз?"; «баба Валя, сядьте на лавочку» GET_IN 0.42, read as talk). The classifier knows "sit down" as CROUCH, but a sitting
// ON a thing as getting into a car (GET_IN 0.6; "take a seat on this bench" 0.98, "In the car."; "sit down on the chair" GET_IN
// 0.35), and "crouch on / at <it>" as CROUCH at that place (1.00), the order the game sits a body down on a seat with (a chair:
// a crouch where it stands, as ever). The piece is written so, for a bench. In or into a thing ("sit in the car"), or a car named,
// stays as it is
bool SitOnPiece(std::string* piece) {
    std::string low = coop::SpeechTextForClassifier(*piece);
    for (const char* lead : {"please ", "now ", "okay ", "ok "})
        if (low.rfind(lead, 0) == 0) low = low.substr(std::string(lead).size());
    for (const char* sit : {"sit down ", "sit yourself down ", "sit ", "take a seat ", "have a seat ", "be seated ", "seat yourself "}) {
        if (low.rfind(sit, 0) != 0) continue;
        const std::string rest = low.substr(std::string(sit).size());
        bool on = false;
        for (const char* prep : {"on ", "onto ", "upon ", "at ", "by ", "on top of "})
            if (rest.rfind(prep, 0) == 0) on = true;
        if (!on) return false;
        // only a bench for now, the seat the game sits a body down on (OVCoopBotController.cpp, IsSeatKind): a chair or a sofa
        // stays as it was read («Сядь на стул» "Ещё раз?"), the owner's to teach or to decide
        bool bench = false;
        std::string word;
        for (const char c : rest + " ") {
            if (c != ' ' && c != ',' && c != '\'') {
                word += c;
                continue;
            }
            for (const char* v : {"car", "cars", "truck", "vehicle", "taxi", "cab", "bus", "van", "jeep", "seat", "wheel"})
                if (word == v) return false;
            bench = bench || word == "bench" || word == "benches";
            word.clear();
        }
        if (!bench) return false;
        *piece = "crouch " + rest;
        return true;
    }
    return false;
}

bool FlankInOwnWords(const std::string& line) {
    const std::string s = OwnWords(line);
    return AnyIn(s, {"фланг", " обойди", " обходи", " обход", " тыл", " сзади", " сбоку", " справа", " слева", " с боку", "flanco", " rodea",
                     " por detrás", " por detras", " por el lado"});
}
bool WayInInOwnWords(const std::string& line) {
    const std::string s = OwnWords(line);
    return AnyIn(s, {" двер", " проход", " вход", " комнат", " внутрь", " дом", " здани", " puerta", " entrada", " cuarto", " habitación",
                     " habitacion", " dentro"});
}

// "close the door" / "shut it" in an English line (the player's, or the decoder's): the word made "open" for the classifier,
// which knows OPEN and no CLOSE; true when it was. "shut up", "close the distance" close nothing
bool CloseToOpen(std::string* line) {
    std::string low;
    for (char c : *line) low += static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
    static const std::vector<std::string> kWhat = {"door", "doors", "window", "windows", "gate", "hatch", "it", "that", "this", "them"};
    for (const std::string verb : {"close", "shut"}) {
        for (size_t at = low.find(verb); at != std::string::npos; at = low.find(verb, at + 1)) {
            const bool starts = at == 0 || !std::isalnum(static_cast<unsigned char>(low[at - 1]));
            const size_t end = at + verb.size();
            if (!starts || (end < low.size() && std::isalnum(static_cast<unsigned char>(low[end])))) continue;
            // the next three words: a thing that opens and shuts
            std::istringstream rest(low.substr(end));
            std::string w;
            bool thing = false;
            for (int k = 0; k < 3 && !thing && (rest >> w); ++k) {
                while (!w.empty() && std::string(".,!?").find(w.back()) != std::string::npos) w.pop_back();
                thing = std::find(kWhat.begin(), kWhat.end(), w) != kWhat.end();
            }
            if (!thing) continue;
            const bool capital = (*line)[at] >= 'A' && (*line)[at] <= 'Z';
            line->replace(at, verb.size(), capital ? "Open" : "open");
            return true;
        }
    }
    return false;
}

// «не надо было запоминать» and the like: the last lesson undone (2026-11-01, the owner). recent: the lesson was a moment ago,
// and «забудь это», "forget it", «olvídalo» alone mean it too (else they are "never mind")
bool UndoInOwnWords(const std::string& line, bool recent) {
    const std::string s = OwnWords(line);
    if (AnyIn(s, {" не надо было запоминать", " не нужно было запоминать", " не надо было это запоминать", " не нужно было это запоминать",
                  " зря запомнил", " зря ты запомнил", " не запоминай это", " не запоминай такое", " отмени это", " отмени запоминание",
                  " отмени последнее", " забудь последнее", " забудь что запомнил", " забудь что ты запомнил", " забудь то что запомнил",
                  " забудь что только что запомнил", " забудь что выучил", " shouldn't have remembered", " should not have remembered",
                  " don't remember that", " do not remember that", " undo that", " forget the last", " forget what you just", " unlearn that",
                  " no lo recuerdes", " no hacía falta recordar", " no hacia falta recordar", " no tenías que recordar", " no tenias que recordar",
                  " olvida lo último", " olvida lo ultimo", " deshaz eso"}))
        return true;
    if (!recent) return false;
    std::string t = s;
    for (const char* lead : {" нет ", " no ", " ну "})
        if (t.rfind(lead, 0) == 0) t = t.substr(std::string(lead).size() - 1);
    for (const char* whole : {" забудь это ", " забудь ", " забудь об этом ", " забудь про это ", " forget it ", " forget that ",
                              " forget about it ", " olvídalo ", " olvidalo ", " olvida eso "})
        if (t == whole) return true;
    return false;
}

// «не расслышал», «что ты сказал?», «ещё раз?», "say again?": the player did not hear the bot (2026-11-01, the owner: the bot says
// its line again, «Я сказал: ...»). «ещё раз», "again" with no question mark stay REPEAT, the order again
bool RepeatAskedInOwnWords(const std::string& line) {
    const std::string s = OwnWords(line);
    if (OwnWordCount(s) > 7) return false;
    if (AnyIn(s, {" не расслышал", " не услышал", " не понял что ты сказал", " что ты сказал", " что ты говоришь", " что-что ",
                  " что что ", " повтори что ", " повтори что ты сказал", " скажи еще раз ", " повтори еще раз ", " say again ",
                  " say that again ", " come again ", " what did you say ", " didn't catch ", " didnt catch ", " didn't hear you ",
                  " didnt hear you ", " what was that ", " repeat that ", " qué dijiste ", " que dijiste ", " no te oí ", " no te oi ",
                  " no te escuché ", " no te escuche ", " repite eso ", " repítelo ", " repitelo "}))
        return true;
    const bool question = line.find('?') != std::string::npos;
    return question && (s == " еще раз " || s == " а еще раз " || s == " again " || s == " otra vez " || s == " повтори " ||
                        s == " что " || s == " чего " || s == " what " || s == " sorry " || s == " pardon " || s == " cómo " || s == " como ");
}

// "go up the blue stairs to the roof" (the decoder's English for «поднимись по ней на крышу»): two orders, up the stairs and
// then to the place after "to" (2026-11-01, the owner: the place parser takes the stairs as the place and drops the roof, and
// the bot walked to the stairs' foot). A line with no up or down, or no place after the stairs, is left as it is
std::vector<std::string> SplitWayTo(const std::string& line) {
    std::string low;
    for (char c : line) low += static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
    const std::string padded = " " + low + " ";
    const bool updown = padded.find(" up ") != std::string::npos || padded.find(" down ") != std::string::npos ||
                        low.rfind("climb", 0) == 0 || low.rfind("ascend", 0) == 0 || low.rfind("descend", 0) == 0;
    if (!updown) return {line};
    for (const char* way : {"stairs", "staircase", "steps", "ladder"}) {
        for (const char* to : {" up to ", " down to ", " to ", " onto ", " into "}) {
            const std::string pattern = std::string(way) + to;
            const size_t at = low.find(pattern);
            if (at == std::string::npos || (at > 0 && std::isalnum(static_cast<unsigned char>(low[at - 1])))) continue;
            std::string first = line.substr(0, at + std::string(way).size());
            std::string rest = line.substr(at + pattern.size());
            while (!rest.empty() && std::string(".!? ").find(rest.back()) != std::string::npos) rest.pop_back();
            if (rest.empty()) continue;
            return {first, "go to " + rest};
        }
    }
    return {line};
}

// to the player in the player's own words: «ко мне», «сюда», «aquí», «conmigo» (padded: OwnWords)
bool ToMeInOwnWords(const std::string& padded) {
    return AnyIn(padded, {" ко мне ", " сюда ", " к нам ", " поближе ", " ближе ко мне ", " aquí ", " aqui ", " acá ", " aca ", " conmigo ",
                          " a mí ", " a mi lado ", " hacia mí ", " hacia mi ", " junto a mí ", " junto a mi ", " to me ", " here "});
}
// a part of a line that only says to whom: «ко мне», «сюда, пожалуйста» («вернись, пожалуйста, ко мне» is cut at its commas)
bool OnlyToMeInOwnWords(const std::string& part) {
    std::string s = OwnWords(part);
    for (const char* filler : {" пожалуйста ", " давай ", " быстро ", " скорее ", " ну ", " por favor ", " rápido ", " rapido "})
        for (size_t at; (at = s.find(filler)) != std::string::npos;) s.replace(at, std::string(filler).size(), " ");
    return s == " ко мне " || s == " сюда " || s == " сюда ко мне " || s == " ко мне сюда " || s == " к нам " || s == " aquí " ||
           s == " aqui " || s == " acá " || s == " aca " || s == " conmigo " || s == " a mi lado ";
}
// «вернись», «вернись обратно», «возвращайся», «назад» in the player's own words: "back" (to where the bot stood: GO_BACK), "me" (to
// the player: «вернись ко мне», «возвращайся сюда»: COME_BACK), or empty when no going back is said. The decoder writes most of
// them "come back", which is to the player (2026-11-03, the owner: «иногда нужно вернуться ко мне, но чаще нужно вернуться в
// предыдущую позицию»; his log of 2026-11-02: «Вернись обратно.» was COME_BACK once and GO_BACK the next time)
std::string BackInOwnWords(const std::string& line) {
    const std::string s = OwnWords(line);
    if (!AnyIn(s, {" вернись ", " вернитесь ", " возвращайся ", " возвращайтесь ", " вертайся ", " обратно ", " назад ", " vuelve ",
                   " volved ", " vuelva ", " regresa ", " regresad ", " regrese ", " atrás ", " atras ", " go back "}))
        return {};
    return ToMeInOwnWords(s) ? "me" : "back";
}
// the decoder's English for a going back with no other place: "come back", "Come back to me.", "go back to where you were", "get back
// here", "return". A place of its own ("come back to the rock") is no bare one
bool BareBackPiece(const std::string& piece) {
    std::string low;
    for (char c : piece) low += static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
    while (!low.empty() && std::string(".,!? ").find(low.back()) != std::string::npos) low.pop_back();
    std::string rest;
    bool verb = false;
    for (const char* v : {"come on back", "come back", "go back", "get back", "head back", "return"}) {
        const std::string vs(v);
        if (low.rfind(vs, 0) == 0 && (low.size() == vs.size() || low[vs.size()] == ' ')) {
            rest = low.substr(vs.size());
            verb = true;
            break;
        }
    }
    if (!verb) return false;
    for (const char* filler : {" right now", " now", " please", " quickly", " immediately", " bro", " buddy"})
        for (size_t at; (at = rest.find(filler)) != std::string::npos;) rest.erase(at, std::string(filler).size());
    while (!rest.empty() && rest.front() == ' ') rest.erase(rest.begin());
    while (!rest.empty() && rest.back() == ' ') rest.pop_back();
    static const std::unordered_set<std::string> kNoPlace = {
        "", "to me", "here", "over here", "back here", "right here", "there", "over there", "back there", "again", "back",
        "to where you were", "where you were", "to where you stood", "where you stood", "to where you came from", "the way you came",
        "to your place", "to your spot", "to your position", "to your post", "to the place", "to the spot", "to the same place",
        "to your previous position", "to the previous position", "to the previous place", "to your old place", "to the old place",
        "to the old spot", "to where you started", "to the start"};
    return kNoPlace.count(rest) > 0;
}
// the decoder's leaving of the thing carried with no place of its own: "Leave the box behind." (v69s3 for «…, перелезь на белый
// стол и оставь там коробку», 2026-11-04, the owner's log), "Leave the box where it is." («Оставь там коробку.»), "leave it here".
// The classifier read them as DELIVER with the box for its place, and the bot carried it back to the crate marker it came from.
// It is the thing put down where the bot is: "put the box down" (DROP), returned. "Leave it there" stays: there may be a spot
std::string LeaveItemPiece(const std::string& piece) {
    std::string low;
    for (char c : piece) low += static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
    while (!low.empty() && std::string(".,!? ").find(low.back()) != std::string::npos) low.pop_back();
    if (low.rfind("leave ", 0) != 0) return {};
    const std::string rest = low.substr(6);
    for (const char* item : {"the box", "this box", "that box", "the crate", "this crate", "that crate", "the spool", "it"}) {
        const std::string is(item);
        if (rest.rfind(is, 0) != 0 || (rest.size() > is.size() && rest[is.size()] != ' ')) continue;
        std::string tail = rest.substr(is.size());
        while (!tail.empty() && tail.front() == ' ') tail.erase(tail.begin());
        for (const char* filler : {" bro", " buddy", " please", " now"})
            if (tail.size() >= std::string(filler).size() && tail.compare(tail.size() - std::string(filler).size(), std::string::npos, filler) == 0)
                tail.erase(tail.size() - std::string(filler).size());
        static const std::unordered_set<std::string> kNoPlace = {"", "behind", "where it is", "here", "right here", "down", "down here"};
        if (!kNoPlace.count(tail)) return {};
        return "put " + is + " down";
    }
    return {};
}
// the decoder's going back to a place of its own, "go back to the rock" (decoder v69s3 for «вернись к камню»; v68s2 wrote "come
// back to the rock"): the place, after "to", in *place. GO_BACK is the bot's history of places and takes no place, so the line is
// read as "come back to the rock" (COME_BACK at it), as it always was
bool GoBackToPlace(const std::string& piece, std::string* place) {
    if (BareBackPiece(piece)) return false;
    std::string low;
    for (char c : piece) low += static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
    while (!low.empty() && std::string(".,!? ").find(low.back()) != std::string::npos) low.pop_back();
    for (const char* v : {"go back to ", "get back to ", "head back to ", "go back over to ", "go back up to ", "go back down to "}) {
        const std::string vs(v);
        if (low.rfind(vs, 0) == 0 && low.size() > vs.size()) {
            *place = low.substr(vs.size());
            return *place != "me" && place->rfind("me ", 0) != 0;   // "to me ..." is no place of its own
        }
    }
    return false;
}

// "what do you see?" as a Russian or Spanish player says it (lower case, Cyrillic and accents included)
bool SeenInOwnWords(const std::string& line) {
    const std::string s = OwnWords(line);
    static const char* const kSeen[] = {" что видишь ", " что ты видишь ", " что там видишь ", " что видно ", " что там видно ",
                                        " что вокруг ", " что там впереди ", " видишь что-нибудь ", " видишь что нибудь ",
                                        " qué ves ", " que ves ", " qué estás viendo ", " que estas viendo ", " qué hay ", " que hay ",
                                        " qué se ve ", " que se ve ", " ves algo "};
    for (const char* p : kSeen)
        if (s.find(p) != std::string::npos) return true;
    return false;
}

// the question's kind: "seen", "hurt", ..., "how" (SMALL_TALK's how-are-you), or empty. talk: the classifier took the
// line for small talk or for no order at all ("патроны есть?" -> "got any ammo?" is no order)
std::string StateQuestion(const std::string& text, bool talk, bool walk = false) {
    // a question about its ammo, which the classifier reads as a walk to the ammo (an ammo box is a MOVE_TO place, bot v55);
    // a walk is only ever this question, "go over there and see what's there" stays a walk
    static const std::vector<std::string> kAmmoAsked = {"got any ammo", "have any ammo", "you have ammo", "you got ammo", "how much ammo",
                                                         "how's your ammo", "how is your ammo", "ammo check", "ammo count", "how many bullets",
                                                         "any ammo left", "ammo left", "low on ammo"};
    if (PhraseIn(text, kAmmoAsked)) return "ammo";
    if (walk) return std::string();
    if (PhraseIn(text, kStateWords[0].second)) return "seen";   // the classifier reads it as SEE_THING, or as nothing
    if (!talk) return std::string();
    // where one lives, comes from, works (2026-11-15: «где вы живёте?», «вы откуда?» said to the granny came back "where are you
    // living", "where are you from", and "where are you" made them a question of what she is doing: the game answered from her
    // body). Talk about their life, not about the order
    static const std::vector<std::string> kLifeAsked = {"where are you from", "where are you living", "where do you live", "where are you staying",
                                                        "where do you stay", "where do you come from", "where are you working", "where do you work",
                                                        "where were you born", "where are you based", "where is your home", "where's your home"};
    if (PhraseIn(text, kLifeAsked)) return std::string();
    for (size_t k = 1; k < kStateWords.size(); ++k)
        if (PhraseIn(text, kStateWords[k].second)) return kStateWords[k].first;
    for (const auto& kind : kTalkWords)
        if (kind.first == "how" && PhraseIn(text, kind.second)) return "how";
    return std::string();
}
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

// ---- lines with several orders or with a context (rewriter.h): the router and the decoder of --chain DIR
// (scripts/coop/stt/export_chain_cpp.py: chain_config.json, router.onnx, decoder.gguf, chain_tests.jsonl)
struct Chain {
    std::string dir;
    std::unique_ptr<coop::OrtBackend> router;   // none in the folder: every line goes to the decoder
    double cut = 0.5;                           // the router's probability from which a line goes to the decoder
    size_t memory_lines = 2;                    // earlier lines the decoder is shown
    double memory_seconds = 30;                 // and for how long a line counts as earlier
    coop::RewriterOptions decoder_options;
#ifdef COOP_WITH_LLM
    coop::Rewriter decoder;
#endif
    double load_ms = 0;

    // the router's probability that the line is for the decoder; -1 without a router
    bool Route(const std::vector<int64_t>& ids, double* p, std::string* err) {
        *p = -1;
        if (!router) return true;
        std::vector<float> logits;
        if (!router->Run(ids, &logits, err)) return false;
        if (logits.size() != 2) return *err = "the router gives " + std::to_string(logits.size()) + " outputs, not 2", false;
        *p = coop::RouteProbability(logits);
        return true;
    }

    bool Rewrite(const std::vector<std::string>& before, const std::string& bot, const std::string& scene, const std::string& line,
                 std::vector<std::string>* pieces, std::string* err) {
#ifdef COOP_WITH_LLM
        return decoder.Rewrite(before, bot, scene, line, pieces, err);
#else
        (void)before, (void)bot, (void)scene, (void)line, (void)pieces;
        return *err = "this coop_cli was built without the decoder", false;
#endif
    }

    static std::string Backend() {
#ifdef COOP_WITH_LLM
        return coop::Rewriter::Backend();
#else
        return std::string();
#endif
    }
};

Chain* g_chain = nullptr;   // set by --chain DIR; every Chat uses it

// ---- the talk in a role (talker.h): --talk DIR, or the brain's own talk/ beside its bot/ (the game's brain folder, so that
// a brain deployed with it talks without the game passing anything). DIR/talk_config.json:
//   {"model": "talk.gguf", "context": 2048, "max_new": 72, "temperature": 0.7, "top_p": 0.8, "top_k": 20, "seed": null,
//    "memory_turns": 4, "memory_seconds": 120,
//    "roles": {"bot": {"file": "roles/bot.txt", "names": {"en": "Buddy", "ru": "Бади", "es": "Buddy"}},
//              "seller": {"file": "roles/seller.txt", "names": {...}}}}
// A role's file is its character, in English; the brain adds what the speaker is called (the bot: the name the player gave it,
// else the game's), what is around (the bot's), the habit of «брат», and the language to answer in. The game may give a role
// a text of its own ("role"). Each role keeps its own talk: the last memory_turns exchanges of the last memory_seconds
struct Talk {
    std::string dir, found;   // found: "--talk" or "beside the bot"
    coop::TalkerOptions options;
    bool seed_set = false;    // --talk-seed: the config's seed is not taken
    size_t memory_turns = 4;
    double memory_seconds = 120;
    struct Role {
        std::string text;                          // its character, as said to the model
        std::string file, file_text;               // the brain's file for it (talk_config.json) and its text; none: the game's alone
        std::string source;                        // where the text in use came from: the file, or "game"
        std::map<std::string, std::string> names;  // what the speaker is called, per language
        bool orders = false;                       // a body of theirs in the game takes orders (the game's "role" says so)
        std::string gender;                        // "woman", "man" (the game's "role"); empty: not said
        bool bro = false;                          // they call the player «брат» / "bro" / "hermano" (the game's "role")
        std::string lang;                          // the language they speak: "en", "ru", "es" (the game's "role"); empty: the player's
    };
    std::map<std::string, Role> roles;
    struct Exchange {
        std::string user, assistant;
        Clock::time_point at;
    };
    std::map<std::string, std::deque<Exchange>> talks;   // per role, oldest first
    double load_ms = 0;
#ifdef COOP_WITH_LLM
    coop::Talker model;
#endif

    bool Ready() const {
#ifdef COOP_WITH_LLM
        return model.Ready();
#else
        return false;
#endif
    }
    // the role's talk so far, as the model is shown it
    std::vector<coop::TalkTurn> Before(const std::string& role) {
        std::deque<Exchange>& d = talks[role];
        const auto now = Clock::now();
        while (!d.empty() && Ms(now - d.front().at) > memory_seconds * 1000.0) d.pop_front();
        while (d.size() > memory_turns) d.pop_front();
        std::vector<coop::TalkTurn> out;
        for (const Exchange& e : d) out.push_back({e.user, e.assistant});
        return out;
    }
    void Keep(const std::string& role, const std::string& user, const std::string& assistant) {
        std::deque<Exchange>& d = talks[role];
        d.push_back({user, assistant, Clock::now()});
        while (d.size() > memory_turns) d.pop_front();
    }
    json RoleNames() const {
        json out = json::array();
        for (const auto& r : roles) out.push_back(r.first);
        return out;
    }
    // the role answered in the last `seconds`: a talk is going on
    bool TalkingNow(const std::string& role, double seconds = 60) const {
        const auto it = talks.find(role);
        return it != talks.end() && !it->second.empty() && Ms(Clock::now() - it->second.back().at) <= seconds * 1000.0;
    }
};

Talk* g_talk = nullptr;      // set by --talk DIR (or found beside the bot); every Chat uses it
std::string g_talk_note;     // why there is none

// --voice-local-extra NAME=DIR (2026-11-12, the owner: the people of a level speak in voices of their own): more voices of the
// player's language beside --voice-local; a "say" with "local_voice": NAME is said with that one, and "local_speaker" picks one
// of its speakers (the Kazakh model's six for Russian, Kokoro's for Spanish)
std::vector<std::pair<std::string, coop::VoiceOptions>> g_voice_local_extra;

// a role's file as the model is shown it: no byte-order mark, LF line ends, no blank lines at either end
std::string RoleText(std::string text) {
    if (text.rfind("\xEF\xBB\xBF", 0) == 0) text.erase(0, 3);
    std::string out;
    for (char c : text)
        if (c != '\r') out += c;
    while (!out.empty() && (out.back() == '\n' || out.back() == ' ' || out.back() == '\t')) out.pop_back();
    size_t b = 0;
    while (b < out.size() && (out[b] == '\n' || out[b] == ' ' || out[b] == '\t')) ++b;
    return out.substr(b);
}

bool LoadTalk(Talk& t, bool cpu, int threads, std::string* err) {
    const auto t0 = Clock::now();
    std::string text;
    if (!ReadFile(t.dir + "/talk_config.json", &text)) return *err = "cannot read talk_config.json", false;
    try {
        const json j = json::parse(text);
        t.options.model_path = t.dir + "/" + j.at("model").get<std::string>();
        t.options.context = j.value("context", 2048);
        t.options.max_new = j.value("max_new", 72);
        t.options.temperature = j.value("temperature", 0.7f);
        t.options.top_p = j.value("top_p", 0.8f);
        t.options.top_k = j.value("top_k", 20);
        if (!t.seed_set && j.contains("seed") && j["seed"].is_number_unsigned()) t.options.seed = j["seed"].get<uint32_t>();
        t.memory_turns = j.value("memory_turns", size_t{4});
        t.memory_seconds = j.value("memory_seconds", 120.0);
        for (const auto& [name, r] : j.at("roles").items()) {
            Talk::Role role;
            role.file = role.source = r.at("file").get<std::string>();
            std::string body;
            if (!ReadFile(t.dir + "/" + role.file, &body)) return *err = "cannot read the role " + name + ": " + role.file, false;
            role.file_text = role.text = RoleText(body);
            if (r.contains("names") && r["names"].is_object())
                for (const auto& [lang, n] : r["names"].items())
                    if (n.is_string()) role.names[lang] = n.get<std::string>();
            t.roles[name] = std::move(role);
        }
    } catch (const std::exception& e) {
        return *err = std::string("talk_config.json: ") + e.what(), false;
    }
    if (!t.roles.count("bot")) return *err = "talk_config.json has no role \"bot\"", false;
    t.options.gpu_layers = cpu ? 0 : 99;
    t.options.threads = threads;
#ifdef COOP_WITH_LLM
    if (!t.model.Load(t.options, err)) return false;
#else
    return *err = "this coop_cli was built without llama.cpp (tools/setup_llama.ps1): no talking model", false;
#endif
    t.load_ms = Ms(Clock::now() - t0);
    return true;
}

// --serve: the game shows the bot's brain starting (2026-10-28, the owner: "прогресс стартовой инициализации моделей бота").
// Before each part loads, one line {"event":"loading","part":"...","at":0.41,"until":0.6,"expect_ms":2900,"ms":6179}: "at" and
// "until" are the shares of the whole start done when the part begins and when it should end, "expect_ms" how long it should
// take (the game moves its bar on within the part by the clock), "ms" the time since the start. The shares come from the parts
// this start will load and their times on the work machine (2026-10-28, i9 + RTX: kLoadMs); "ready" is the end. Other modes
// print nothing of it.
bool g_load_events = false;
Clock::time_point g_load_t0;
std::vector<std::pair<std::string, double>> g_load_plan;   // the parts this start loads, in order, with their expected ms

double ExpectedLoadMs(const std::string& part) {
    static const std::pair<const char*, double> kLoadMs[] = {
        {"the intent classifier", 6200}, {"the language model", 2900}, {"the talking model", 1500}, {"the planner", 60}, {"the voice", 1600},
        {"the voice in the player's language", 1650}, {"more voices in the player's language", 2500}, {"speech recognition", 2550},
        {"the microphone", 60}};
    for (const auto& p : kLoadMs)
        if (part == p.first) return p.second;
    return 500;
}

void PlanLoading(const std::vector<std::string>& parts) {
    g_load_plan.clear();
    for (const std::string& p : parts) g_load_plan.emplace_back(p, ExpectedLoadMs(p));
}

void Loading(const char* part) {
    if (!g_load_events) return;
    double total = 0, before = 0, expect = ExpectedLoadMs(part);
    bool found = false;
    for (const auto& p : g_load_plan) {
        total += p.second;
        if (p.first == part) found = true;
        else if (!found) before += p.second;
    }
    const double at = found && total > 0 ? before / total : 0.0;
    const double until = found && total > 0 ? (before + expect) / total : at;
    const json j = {{"event", "loading"}, {"part", part}, {"at", at}, {"until", until}, {"expect_ms", static_cast<int>(expect)},
                    {"ms", static_cast<int>(Ms(Clock::now() - g_load_t0))}};
    std::fflush(stdout);   // the log lines printed so far first: they are the game's log
    std::fputs(j.dump().c_str(), stdout);
    std::fputc('\n', stdout);
    std::fflush(stdout);
}

// --language en|ru|es: the player's language. English goes as it always went (the router sends a line to the decoder only
// when it gives several orders or leans on the talk). Russian and Spanish lines all go to the decoder (a chain whose decoder
// was trained on three languages, chain v62: scripts/coop/stt/chains6_v62.py), which writes them as English orders; the
// classifier, the place matcher and the planner then read English as before. The router is English and is not asked.
std::string g_language = "en";

// --decoder-every-line: English lines go to the decoder too, every one, as Russian and Spanish do; the router is not asked
// (2026-11-06, the owner: «пусть LLM работает даже в английской версии на каждой фразе», after his English game where
// "grabbed this box and delivered it uh on top of the white table" stayed with the classifier (router 0.03) and the place
// matcher took the box for the place). A line the decoder writes back as it is still goes to the classifier as the player's
// own; an answer to the bot's question is read as the player's line first, as before
bool g_decode_every_line = false;

// --replies FILE (localize.h): the bot's lines in the player's language. Each reply's "say" is written in it ("say_en" keeps
// the English); a line the game hands to "say" in English is written in it too, and said with --voice-local DIR, the
// player's language's voice. A sentence the table has no template for keeps the whole line English (and its English voice),
// and is logged on stderr. The lines this brain wrote in the player's language are kept for a while: the game hands them
// back to "say" as they are.
coop::Localizer* g_replies = nullptr;
std::deque<std::string> g_localized;

bool Localize(const std::string& english, std::string* local, const coop::Localizer::Terms* terms = nullptr) {
    if (!g_replies || english.empty()) return false;
    std::string missing;
    if (!g_replies->Translate(english, local, &missing, terms)) {
        std::fprintf(stderr, "replies: no %s template for \"%s\" (in \"%s\")\n", g_replies->Language().c_str(), missing.c_str(), english.c_str());
        return false;
    }
    g_localized.push_back(*local);
    if (g_localized.size() > 64) g_localized.pop_front();
    return true;
}

bool IsLocalized(const std::string& line) { return std::find(g_localized.begin(), g_localized.end(), line) != g_localized.end(); }

// a line this brain wrote in the player's language by other means than the tables (the talk in a role, talker.h): the game
// hands it back to "say" as it is, and it is said with the player's language's voice
void KeepLocalized(const std::string& line) {
    if (!g_replies || line.empty()) return;
    g_localized.push_back(line);
    if (g_localized.size() > 64) g_localized.pop_front();
}

// --replies-bro FILE, --bro on|off, --bro-relapse SECONDS (bro.h): the habit of calling the player «брат» / "bro" /
// "hermano". While it is on the lines are written from the persona's table (English too: an English table of the same
// sentences with "bro"); off, from the plain one (--replies; none in English). The player's words switch it
coop::BroHabit g_bro;
coop::Localizer* g_plain_replies = nullptr;
coop::Localizer* g_bro_replies = nullptr;
const auto g_started = std::chrono::steady_clock::now();

double SinceStart() { return std::chrono::duration<double>(std::chrono::steady_clock::now() - g_started).count(); }

// the table for the next line: the habit's, or the plain one
void ChooseReplies() {
    g_replies = g_bro_replies && g_bro.Active(SinceStart()) ? g_bro_replies : g_plain_replies;
}

// The tables of a person's own language (2026-11-14, the owner: «у персоны можно было выбрать её язык общения, даже если язык
// сейчас пользователя английский, то персона может говорить на русском»): a person of the level who speaks another language
// than the player's is answered from that language's tables (replies_<lang>.json, replies_<lang>_brat.json with the habit),
// read from --replies-dir (else the folder of --replies / --replies-bro) when first wanted and kept. English without the habit
// is no table: the brain's own words. Null: English, or a table that is not there (the line stays English)
std::string g_replies_dir;
std::map<std::string, std::unique_ptr<coop::Localizer>> g_lang_replies;
coop::Localizer* RepliesIn(const std::string& lang, bool bro) {
    if (lang.empty() || lang == g_language) return bro && g_bro_replies ? g_bro_replies : g_plain_replies;
    if (lang == "en" && !bro) return nullptr;
    const std::string key = bro ? lang + "_brat" : lang;
    auto it = g_lang_replies.find(key);
    if (it == g_lang_replies.end()) {
        std::unique_ptr<coop::Localizer> table;
        std::string err;
        const std::string file = g_replies_dir + "/replies_" + key + ".json";
        if (!g_replies_dir.empty()) {
            table = std::make_unique<coop::Localizer>();
            if (!table->Load(file, &err)) table.reset();
        }
        std::fprintf(stderr, "replies of a person's own language: %s %s\n", file.c_str(), table ? "read" : ("not read: " + err).c_str());
        it = g_lang_replies.emplace(key, std::move(table)).first;
    }
    if (!it->second && bro) return RepliesIn(lang, false);   // no table with the habit: the plain one
    return it->second.get();
}

const std::vector<std::string> kBroOff = {"Okay, I won't anymore.", "Got it, no more.", "Fine, I'll stop."};
const std::string kBroRelapse = "Sorry, habit.";

// The long-term memory (--memory FILE, bot_memory.h): what the player taught the bot, one file per player. Its words
// (the reply tables have them: scripts/coop/replies/make_catalogue.py, "the long-term memory")
coop::BotMemory* g_memory = nullptr;
std::string g_memory_note;   // why there is none ("ready" says)
const std::string kAskMeaning = "What did you mean?";       // after "not that": the next line is the meaning
const std::string kRemembered = "Got it, I'll remember.";   // a name, a colour, a meaning kept (before the order's own words)
const std::string kForgotten = "Forgotten.";
const std::string kCannotUndo = "I can't undo that one.";   // «не надо было запоминать» after a setting or a phrase (2026-11-01)

// «Я сказал: иду к дивану.»: the bot's last line again, in its language and persona (2026-11-01)
std::string RepeatLine(const std::string& line);
const std::string kNotKept = "I don't remember that.";
const std::string kPointAtIt = "Point at it.";              // a name or a colour with no thing under the crosshair
const std::string kAskWhat = "Then what is it?";            // "no" right after "what is that?": the next line says it
const std::string kNotRemembered = "All right, I won't remember it.";   // "no" to "Shall I remember it as X?"
const std::string kNoColour = "I don't know what colour it is.";       // "what colour is it?" at a thing of no known colour
const std::string kGotIt = "Got it.";                       // "no, it's a table" about the table: nothing to keep
const std::string kYesOrNo = "Yes or no?";                  // a sound for the answer to "Shall I remember ...?" ("B.")
// a door whose inside the level marks (the game's tag "inside"): «это гараж» at it names the room behind it (2026-10-30, the
// owner: the bot knows walls and doors, not rooms; the door is where a room starts)
const std::string kOfferRoomA = "Shall I remember that ", kOfferRoomB = " is behind this door?";
const std::string kDoorToA = "That's the door to ";
// the bot's name and the player's (2026-10-31, the owner: the player names their bot and tells it their own name; the bot
// answers to its name and says the player's now and then). {name} is an open slot of the reply tables: the name as said
const std::string kNamedA = "I'm ", kNamedB = " now.";                  // «тебя зовут Рекс»
const std::string kMyNameA = "My name is ";                             // «как тебя зовут?»
const std::string kMeetA = "Nice to meet you, ";                        // «меня зовут Тимур»
const std::string kYourNameA = "Your name is ";                         // «как меня зовут?»
const std::string kNoPlayerName = "I don't know your name yet.";
const std::vector<std::string> kCalled = {"Yes?", "Right here.", "I hear you."};   // the name alone: «Рекс!»
// how often the bot says the player's name (--name-chance, percent of the lines it may go into): "now and then"
int g_name_chance = 25;
// the open microphone's voice detector (--vad FILE: silero_vad.onnx; 2026-11-01): without it "open_mic" is refused
std::string g_vad_model;
int g_name_since = 1000;   // the bot's lines since it last said the player's name

// a line the game put together from a reply this brain wrote in the player's language and its own English words ("No
// flashbangs, only frags." + "Зачищаю комнату."): each sentence that is a sentence of a line written here stays, each
// other one is translated. False when one of them can be neither: the line stays English
bool LocalizeMixed(const std::string& line, std::string* local, const coop::Localizer::Terms* terms = nullptr) {
    if (!g_replies) return false;
    std::string out;
    for (const std::string& sentence : coop::SplitSentences(line)) {
        std::string piece;
        bool ours = false;
        for (const std::string& l : g_localized)
            for (const std::string& s : coop::SplitSentences(l))
                if (s == sentence) ours = true;
        if (ours) piece = sentence;
        else if (!Localize(sentence, &piece, terms)) return false;
        if (!out.empty()) out += ' ';
        out += piece;
    }
    *local = out;
    return !out.empty();
}

// ---- the second reader of a line (decider.h): --decider DIR (decider.json and the GGUF it names), off by default
struct DeciderReader {
    std::string dir;
    std::string mode = "avg";        // avg: the ensemble's and the decider's probabilities averaged; only: the decider's
    std::string source;              // decider.json "source": which model, trained on what
    coop::DeciderOptions options;
#ifdef COOP_WITH_LLM
    coop::Decider model;
#endif
    double last_ms = 0;              // the last line's time in the decider (it runs beside the ensemble)
    size_t failures = 0;

    bool Probs(const std::string& text, std::vector<float>* p, std::string* err, std::vector<int32_t>* ids = nullptr) {
#ifdef COOP_WITH_LLM
        const auto t0 = Clock::now();
        const bool ok = model.Probs(text, p, err, ids);
        last_ms = Ms(Clock::now() - t0);
        return ok;
#else
        (void)text, (void)p, (void)ids;
        return *err = "this coop_cli was built without llama.cpp: no decider", false;
#endif
    }
};

DeciderReader* g_decider = nullptr;   // set by --decider DIR; every Chat uses it

bool LoadDecider(DeciderReader& d, const std::vector<std::string>& labels, std::string* err) {
    std::string text;
    if (!ReadFile(d.dir + "/decider.json", &text)) return *err = "cannot read decider.json", false;
    try {
        const json j = json::parse(text);
        if (j.at("labels").get<std::vector<std::string>>() != labels)
            return *err = "the decider's labels are not the bot's (another label set or order)", false;
        d.options.model_path = d.dir + "/" + j.at("model").get<std::string>();
        d.options.prefix = j.at("prefix").get<std::vector<int32_t>>();
        d.options.label_ids = j.at("label_ids").get<std::vector<int32_t>>();
        d.options.context_ids = j.at("context_ids").get<std::vector<int32_t>>();
        d.options.answer_ids = j.at("answer_ids").get<std::vector<int32_t>>();
        d.options.max_line_tokens = j.value("max_line_tokens", 1536);
        d.options.temperature = j.value("temperature", 1.0);
        d.source = j.value("source", std::string());
    } catch (const std::exception& e) {
        return *err = std::string("decider.json: ") + e.what(), false;
    }
    if (d.options.label_ids.size() != labels.size()) return *err = "decider.json: one label token per label expected", false;
    if (d.mode != "avg" && d.mode != "only") return *err = "--decider-mode is avg or only, not " + d.mode, false;
#ifdef COOP_WITH_LLM
    if (!d.model.Load(d.options, err)) return false;
    std::vector<float> p;
    return d.Probs("warm up", &p, err);
#else
    return *err = "this coop_cli was built without llama.cpp: no decider", false;
#endif
}

// --decider-tests FILE (export_game.py): per line the text, upstream's tokens of the line alone and decider_eval's label
// logits on the same GGUF. The line's tokens must be the same; the probabilities the same up to llama.cpp's own noise.
int RunDeciderTests(DeciderReader& d, const std::string& path) {
    std::string raw, err;
    if (!ReadFile(path, &raw)) return std::fprintf(stderr, "cannot read %s\n", path.c_str()), 1;
    const json rows = json::parse(raw).at("rows");
    size_t n = 0, same_ids = 0, same_top = 0, shown = 0;
    double worst = 0, total_ms = 0;
    std::vector<float> p;
    std::vector<int32_t> ids;
    for (const json& r : rows) {
        const std::string text = r.at("text").get<std::string>();
        if (!d.Probs(text, &p, &err, &ids)) return std::fprintf(stderr, "%s: %s\n", text.c_str(), err.c_str()), 1;
        total_ms += d.last_ms;
        ++n;
        const bool ids_ok = ids == r.at("line_ids").get<std::vector<int32_t>>();
        same_ids += ids_ok;
        const std::vector<float> lg = r.at("logits").get<std::vector<float>>();
        std::vector<double> ref(lg.size());
        const double top = *std::max_element(lg.begin(), lg.end());
        double sum = 0;
        for (size_t j = 0; j < lg.size(); ++j) sum += ref[j] = std::exp((lg[j] - top) / d.options.temperature);
        double dp = 0;
        size_t a = 0, b = 0;
        for (size_t j = 0; j < lg.size(); ++j) {
            dp = std::max(dp, std::abs(p[j] - ref[j] / sum));
            if (p[j] > p[a]) a = j;
            if (ref[j] > ref[b]) b = j;
        }
        worst = std::max(worst, dp);
        same_top += a == b;
        if ((!ids_ok || a != b) && shown++ < 10)
            std::printf("  %s %s: tokens %s, top %zu vs %zu, max |dp| %.4f\n", r.at("id").get<std::string>().c_str(),
                        Escaped(text).c_str(), ids_ok ? "equal" : "DIFFER", a, b, dp);
    }
    std::printf("decider tests, %zu lines: the line's tokens equal upstream's on %zu/%zu, the top label equal on %zu/%zu, "
                "max |d probability| %.4f; %.1f ms per line (%d threads)\n", n, same_ids, n, same_top, n, worst, total_ms / std::max<size_t>(1, n),
                d.options.threads);
    return (same_ids == n && same_top == n) ? 0 : 1;
}

// the decider's reading folded into the ensemble's probabilities `p` (avg or only); a line the decider could not read
// keeps the ensemble's alone
void SecondReading(DeciderReader& d, bool ok, const std::vector<float>& pd, const std::string& derr, std::vector<float>* p) {
    if (!ok || pd.size() != p->size()) {
        ++d.failures;
        std::fprintf(stderr, "decider: %s (the ensemble alone reads this line)\n", ok ? "the label count differs" : derr.c_str());
        return;
    }
    if (d.mode == "only") {
        *p = pd;
        return;
    }
    for (size_t i = 0; i < p->size(); ++i) (*p)[i] = 0.5f * ((*p)[i] + pd[i]);
}

bool LoadChain(Chain& c, const coop::OrtBackend::Options& opt, bool decoder_cpu, int decoder_threads, std::string* err) {
    const auto t0 = Clock::now();
    std::string text;
    if (!ReadFile(c.dir + "/chain_config.json", &text)) return *err = "cannot read chain_config.json", false;
    try {
        const json j = json::parse(text);
        c.cut = j.value("cut", 0.5);
        c.memory_lines = j.value("memory_lines", size_t{2});
        c.memory_seconds = j.value("memory_seconds", 30.0);
        if (j.contains("router")) {
            c.router = std::make_unique<coop::OrtBackend>();
            if (!c.router->Load(c.dir + "/" + j.at("router").get<std::string>(), opt, err)) return *err = "router: " + *err, false;
        }
        c.decoder_options.model_path = c.dir + "/" + j.at("decoder").get<std::string>();
        c.decoder_options.system = j.at("system").get<std::string>();
        c.decoder_options.max_new = j.value("max_new", 96);
        c.decoder_options.context = j.value("context", 1024);
    } catch (const std::exception& e) {
        return *err = std::string("chain_config.json: ") + e.what(), false;
    }
    c.decoder_options.gpu_layers = decoder_cpu ? 0 : 99;
    c.decoder_options.threads = decoder_threads;
#ifdef COOP_WITH_LLM
    if (!c.decoder.Load(c.decoder_options, err)) return false;
    std::string answer;   // the system turn goes into the context here, not on the player's first line
    if (!c.decoder.Answer(coop::RewriterTurn({}, {}, "warm up"), &answer, nullptr, err)) return false;
#else
    return *err = "this coop_cli was built without the decoder: llama.cpp was not under third_party/ (tools/setup_llama.ps1)", false;
#endif
    c.load_ms = Ms(Clock::now() - t0);
    return true;
}

// one bot in a conversation: the demo's replies and the debug line
// the first letter of a line a capital (defined below)
std::string CapitalFirst(std::string s);

struct Chat {
    Model& m;
    coop::BotBrain brain;
    std::mt19937 rng{static_cast<unsigned>(Clock::now().time_since_epoch().count())};
    bool why = true;
    std::vector<float> p;

    coop::Planner planner;   // the world (world.h): grounding, memory, questions, priors; empty until /world FILE

    // the talk so far, as the decoder of --chain is shown it (chains2/spec_context.json: "before", "bot")
    struct Said {
        std::string text;
        Clock::time_point at;
    };
    std::deque<Said> said;             // the player's earlier lines, oldest first: as the classifier read them, or, for
                                       // a line the decoder rewrote, the orders it wrote
    Said bot_said;                     // the planner's own words after them (a question, a settled order); empty: none
    int what_said_lines = -1;          // bot_said is the answer to "what is that?": the lines said since (-1: it is not)
    std::vector<std::string> held;     // order lines of a rewritten line that wait for the answer to the bot's question
    std::vector<std::string> after_go; // order lines after one queued for the player's "go" («когда я скажу давай, возьми
                                       // коробку, потом отнеси её на камень»): they wait for the go too, then follow it
    bool chain_on = true;              // /chain
    std::string read_text;             // Read(): the text `p` is for
    bool has_read = false;
    double read_ms = 0;                // ... what the classifier took for it; 0 once a turn has been charged with it

    explicit Chat(Model& model) : m(model) {}
    bool Init(std::string* err) {
        if (!brain.Init(m.cfg, err)) return false;
        planner.Init(&brain);
        return Classify(m, m.tok.Encode("warm up"), &p, err);
    }
    const std::string& Pick(const std::vector<std::string>& v) { return v[rng() % v.size()]; }

    // a world state file (world.py WORLD_EXAMPLE's shape) as the game would hand it over
    bool LoadWorld(const std::string& path, std::string* err) {
        std::string text;
        if (!ReadFile(path, &text)) return *err = "cannot read " + path, false;
        coop::WorldState w;
        try {
            if (!ParseWorld(json::parse(text), &w, err)) return false;
        } catch (const std::exception& e) {
            return *err = std::string("world file: ") + e.what(), false;
        }
        if (!planner.SetWorld(w, err)) return false;
        std::printf("  world: %zu entities%s%s, bot %s\n", w.entities.size(), w.has_player_pin ? ", a pin" : "",
                    w.player_gaze.empty() ? "" : (", looking at " + w.player_gaze).c_str(), w.bot_stance.c_str());
        return true;
    }

    // /q /why /t /world /chain: 0 not a command, 1 handled, 2 quit
    int Command(const std::string& line) {
        if (line == "/q" || line == "/quit") return 2;
        if (line == "/why") return why = !why, 1;
        if (line == "/chain") {
            if (!g_chain) return std::printf("  no router and decoder are loaded (--chain DIR)\n"), 1;
            chain_on = !chain_on;
            Forget();
            std::printf("  %s\n", chain_on ? "the router and the decoder are on" : "every line goes to the classifier as it is");
            return 1;
        }
        if (line.rfind("/t ", 0) == 0) {
            brain.threshold = std::atof(line.c_str() + 3);
            std::printf("  threshold %.2f\n", brain.threshold);
            return 1;
        }
        if (line.rfind("/world ", 0) == 0) {
            std::string err;
            if (!LoadWorld(StripPy(line.substr(7)), &err)) std::printf("  %s\n", err.c_str());
            return 1;
        }
        return 0;
    }

    // what one line led to: the planner's result, the words the bot answers with, the classifier's time
    struct Turn {
        std::string line;       // the order line it is about: the player's line, or one the decoder wrote from it
        coop::PlannerResult r;
        std::string reply;
        std::string state;      // a question only the game can answer (StateQuestion): "seen", "how", "hurt", "heat", ...
        std::vector<float> p;   // the classifier's probabilities
        double ms = 0;
        double at = -1;         // when its pointer word was said, seconds since the talk key went down; -1: not known
        coop::TimePhrase time;  // the time said with it (round v68): "wait 5 seconds", "in 10 seconds go to the door"
        coop::Localizer::Terms terms;   // the words of its reply the tables do not have (a thing's name or colour, WhichCallout)
        bool close = false;     // "close the door": read as OPEN, and the game shuts it (2026-11-01)
    };

    // A time said with an order outlives the line it was said in (round v68): the order the bot asked about ("hold the
    // door for 20 seconds" -> "Which door?" -> "the north one"), the one queued for "go", the last one for "again"
    coop::TimePhrase asked_time, queued_time, last_time;

    // the bot's words for the time ("10 seconds.", "In 10 seconds.", "A few seconds."), one sentence the reply tables
    // translate (one {n} a sentence, whole numbers: the game keeps the exact time)
    static std::string TimeWords(const coop::TimePhrase& t) {
        if (!t.found) return {};
        if (t.range) {
            const bool few = t.min == 3.0 && t.max == 7.0;
            if (few) return t.after ? "In a few seconds." : "A few seconds.";
            return "About " + std::to_string(static_cast<int>(std::lround((t.min + t.max) / 2.0))) + " seconds.";
        }
        const int n = std::max(1, static_cast<int>(std::lround(t.seconds)));
        const std::string unit = n == 1 ? " second." : " seconds.";
        if (t.after) return "In " + std::to_string(n) + unit;
        if (t.more) return std::to_string(n) + (n == 1 ? " more second." : " more seconds.");
        return std::to_string(n) + unit;
    }

    // The words of the spoken line being heard and where their clock starts (respond sets them for one Hear): each order
    // line with a pointer ("this", "here", «эту», «сюда», "aquí") is read with the crosshair where it was when that word
    // was said, from the game's talk_trail ("take this box", run, "put it here", let go of the key)
    std::vector<coop::SpeechWord> words;
    double clip_start = 0;

    // lower case for the pointer words: ASCII and Cyrillic, the punctuation the recognizer prints dropped
    static std::string LowerWord(const std::string& w) {
        std::u32string u = coop::DecodeUtf8(w), out;
        for (char32_t c : u) {
            if (c >= U'A' && c <= U'Z') c += 32;
            else if (c >= U'А' && c <= U'Я') c += 32;
            else if (c == U'Ё') c = U'ё';
            if ((c >= U'a' && c <= U'z') || (c >= U'а' && c <= U'я') || c == U'ё' || c >= 0xC0) out += c;
        }
        return coop::EncodeUtf8(out);
    }
    static bool IsPointer(const std::string& lower) {
        static const std::unordered_set<std::string> kPointers = {
            "this", "that", "these", "those", "here", "there",
            "\xD1\x8D\xD1\x82\xD0\xBE", "\xD1\x8D\xD1\x82\xD1\x83", "\xD1\x8D\xD1\x82\xD0\xBE\xD1\x82", "\xD1\x8D\xD1\x82\xD0\xB0",   // это эту этот эта
            "\xD1\x8D\xD1\x82\xD0\xB8", "\xD1\x8D\xD1\x82\xD0\xBE\xD0\xB9", "\xD1\x8D\xD1\x82\xD0\xBE\xD0\xB3\xD0\xBE",                 // эти этой этого
            "\xD1\x82\xD0\xBE\xD1\x82", "\xD1\x82\xD1\x83", "\xD1\x82\xD0\xB0", "\xD1\x82\xD0\xB5",                                    // тот ту та те
            "\xD1\x81\xD1\x8E\xD0\xB4\xD0\xB0", "\xD1\x82\xD1\x83\xD0\xB4\xD0\xB0", "\xD0\xB7\xD0\xB4\xD0\xB5\xD1\x81\xD1\x8C",       // сюда туда здесь
            "\xD1\x82\xD0\xB0\xD0\xBC", "\xD0\xB2\xD0\xBE\xD0\xBD",                                                                     // там вон
            "esto", "esta", "este", "eso", "esa", "ese", "estos", "estas", "aqu\xC3\xAD", "all\xC3\xAD", "ah\xC3\xAD", "ac\xC3\xA1",
            "all\xC3\xA1"};
        return kPointers.count(lower) > 0;
    }
    // when each pointer of the line was said, seconds since the key went down; a run of them ("вон туда", "right there")
    // is one, at its first word
    std::vector<double> PointerMoments() const {
        std::vector<double> out;
        bool last = false;
        for (const coop::SpeechWord& w : words) {
            const bool pointer = IsPointer(LowerWord(w.text));
            if (pointer && !last) out.push_back(w.start + clip_start);
            last = pointer;
        }
        return out;
    }
    static bool LinePoints(const std::string& line) {
        std::string word;
        for (size_t i = 0; i <= line.size(); ++i) {
            const char c = i < line.size() ? line[i] : ' ';
            if (c == ' ' || c == ',' || c == '.' || c == '!' || c == '?' || c == ';') {
                if (!word.empty() && IsPointer(LowerWord(word))) return true;
                word.clear();
            } else {
                word += c;
            }
        }
        return false;
    }
    // the entity under the crosshair at a moment of the talk_trail; empty: none known then (the line's own gaze stays)
    std::string TrailGaze(double at) const {
        std::string g;
        for (const auto& [t, id] : planner.World().talk_trail) {
            if (t > at) break;
            g = id;
        }
        return g;
    }

    // what one line of the player led to: a turn per order line gone through, and how the line got there
    struct Heard {
        double route = -1;                // the router's probability that the line is for the decoder; -1: not asked
        bool decoded = false;             // the decoder was asked
        bool rewritten = false;           // ... and its order lines were taken in place of the line
        size_t resumed = 0;               // order lines that had waited for this answer and went through after it
        std::vector<Turn> turns;
        std::vector<std::string> held;    // order lines still waiting: the bot asked a question first
        std::string note;                 // why the router and the decoder were passed by
        double route_ms = 0, rewrite_ms = 0;
    };

    void Forget() {
        said.clear();
        bot_said = Said();
        held.clear();
        after_go.clear();
    }

    // One line. `heard` is what the regex slots and the place matcher read; `text` is what the classifier
    // reads: the same string for a typed line, SpeechTextForClassifier(heard) for a spoken one
    bool Respond(const std::string& heard, const std::string& text, std::string* err) {
        Heard h;
        if (!Hear(heard, text, &h, err, [&](const Heard& now, const Turn& t) {
                if (why && now.turns.size() == 1) PrintRoute(now);
                if (why && (now.rewritten || now.turns.size() > 1)) std::printf("  %zu> %s\n", now.turns.size(), t.line.c_str());
                Print(t);
            }))
            return false;
        if (why && !h.held.empty()) {
            std::string rest;
            for (const std::string& s : h.held) rest += (rest.empty() ? "" : " | ") + s;
            std::printf("     waiting for your answer: %s\n", rest.c_str());
        }
        return true;
    }

    // The line through the router, the decoder if the router sends it on, and then each order line through the
    // classifier and the planner as a line of its own (rewriter.h). `each(heard so far, turn)` is called right after an
    // order line was planned, while the bot's state is that turn's. Without --chain: one turn, the line as it is.
    //   - the decoder is shown the player's last lines and the planner's own last words, for memory_seconds. A line it
    //     rewrote is kept as the orders it wrote (the earlier lines in a clean form are worth 6 to 8 points on heard
    //     lines with a context: chains2_54_score.log, "the earlier lines as the player said them");
    //   - while the planner's question is open, a line its rules for answers are made for (AnswerLike) goes to the
    //     planner as it is: the planner knows the candidates it offered. If the planner cannot read it (say again, the
    //     question still open) and the decoder read one order in it ("the north one" -> "open the north door"), that
    //     order goes to the planner instead. Every other line takes the usual road;
    //   - an order line that makes the planner ask stops the rest: they wait in `held`. They go through after a line
    //     that settles that order and gives no other; a line with several orders replaces them (the decoder wrote it
    //     with the earlier line in view), and so does a line about something else.
    // forced: the order lines the long-term memory keeps for this line (bot_memory.h): they go to the classifier as the
    // decoder's would, and the router and the decoder are not asked
    template <class Each>
    bool Hear(const std::string& heard, const std::string& text, Heard* h, std::string* err, Each&& each,
              const std::vector<std::string>* forced = nullptr) {
        *h = Heard();
        if (brain.Pending() < 0) after_go.clear();   // nothing waits for the player's go any more (cancelled, reset)
        bool go_waits = false;                       // this line queued an order with more after it
        const auto now = Clock::now();
        Chain* c = chain_on && !forced ? g_chain : nullptr;
        const bool answering = planner.Mem().has_question;
        const int asked = answering ? planner.Mem().question.intent : -1;   // the order the open question is about
        struct Line {
            std::string heard, text;
            bool close = false;   // "close the door" read as "open the door" (CloseToOpen)
        };
        std::vector<Line> todo;
        std::string second;   // while the question is open: the one order the decoder read in an answer
        // the decoder on this line with the talk before it; false when it fails (a line too long for its context)
        auto decode = [&](std::vector<std::string>* pieces) {
            while (!said.empty() && Ms(now - said.front().at) > 1000 * c->memory_seconds) said.pop_front();
            std::vector<std::string> before;
            if (!taught_alone)
                for (const Said& s : said) before.push_back(s.text);
            const bool bot = !taught_alone && !bot_said.text.empty() && Ms(now - bot_said.at) <= 1000 * c->memory_seconds;
            const auto t1 = Clock::now();
            const bool ok = c->Rewrite(before, bot ? bot_said.text : std::string(), planner.World().scene, text, pieces, &h->note);
            h->rewrite_ms += Ms(Clock::now() - t1);
            if (ok) h->decoded = true;
            return ok;
        };
        // a Russian or Spanish line: always to the decoder, which writes it in English (--language); a taught meaning too
        const bool foreign = g_language != "en";
        if (c) {
            const auto t0 = Clock::now();
            if (foreign || taught_alone || g_decode_every_line) h->route = 1.0;
            else if (!c->Route(m.tok.Encode(text), &h->route, err)) return false;
            h->route_ms = Ms(Clock::now() - t0);
            // an English line of one order the scene may change (decoder v65: chains9_v65.py): "get down" standing on a
            // box is climbing down, "jump in" with no car near is jumping up on the thing. The classifier's own reading
            // says which lines: one the scene could make another order goes to the decoder with the scene
            bool scene_look = false;
            if (!foreign && c->router && h->route < c->cut && !planner.World().scene.empty()) {
                if (!Read(text, err)) return false;
                const std::string& top = m.cfg.labels[std::max_element(p.begin(), p.end()) - p.begin()];
                const coop::WorldState& w = planner.World();
                scene_look = (w.scene_standing && (top == "TAKE_COVER" || top == "MOVE_TO" || top == "NONE" || top == "GET_OUT" ||
                                                   top == "CROUCH" || top == "FOLLOW_ME")) ||
                             (!w.scene_car_near && top == "GET_IN");
                if (scene_look) h->note = "the scene may change what the line orders: the decoder reads it in the scene";
            }
            if (foreign || taught_alone || !c->router || h->route >= c->cut || scene_look) {
                std::vector<std::string> pieces;
                // a decoder that fails leaves the line to the classifier
                decode(&pieces);
                // a line written back as it is stays the player's own line
                if (pieces.size() == 1 && coop::SpeechTextForClassifier(pieces[0]) == coop::SpeechTextForClassifier(text)) pieces.clear();
                // an answer to the bot's question: in English the player's own line is read first (the decoder's reading
                // only if the planner cannot read it); a Russian or Spanish line cannot be read, its English is
                if (!foreign && answering && pieces.size() == 1) {
                    bool answer = false;
                    if (!AnswerLike(text, &answer, err)) return false;
                    if (answer) {
                        second = pieces[0];
                        pieces.clear();
                        h->note = "the bot's question is open, the line is its answer";
                    }
                }
                // «закрывай дверь»: one order, to close, whatever the decoder wrote ("Cover the door.")
                const bool close_said = foreign && pieces.size() == 1 && CloseInOwnWords(heard);
                // «вернись (обратно)» with no «ко мне»: back to where the bot stood ("go back", GO_BACK), whatever the decoder
                // wrote ("come back" is to the player); «вернись ко мне»: to the player. One kind per going back said, in order
                std::vector<std::string> back_said;
                if (foreign && pieces.size() == 1) {
                    if (std::string k = BackInOwnWords(heard); !k.empty()) back_said.push_back(k);
                } else if (foreign) {
                    for (const std::string& part : LineParts(heard)) {
                        if (std::string k = BackInOwnWords(part); !k.empty()) back_said.push_back(k);
                        else if (!back_said.empty() && back_said.back() == "back" && OnlyToMeInOwnWords(part)) back_said.back() = "me";
                    }
                }
                size_t next_back = 0;
                for (std::string piece : pieces) {
                    // bot v62: the classifier reads an English "hi" / "hi there" as the owner's misheard "hide (there)"
                    // (v57). The decoder's English for «привет», «hola» is no mishearing: it is a greeting
                    if (foreign) {
                        const std::string low = coop::SpeechTextForClassifier(piece);
                        if (low == "hi" || low.rfind("hi ", 0) == 0) piece = "hello" + piece.substr(2);
                        // «зайди через главную дверь» -> "Flank through the main door." (decoder v68): with no flank said and a
                        // door, a passage or a room, it is the way in
                        if ((low == "flank" || low.rfind("flank ", 0) == 0) && !FlankInOwnWords(heard) && WayInInOwnWords(heard)) {
                            std::string rest = low.size() > 6 ? low.substr(6) : std::string();
                            for (const char* by : {"through ", "using ", "via ", "by ", "from ", "around ", "at "})
                                if (rest.rfind(by, 0) == 0) rest = rest.substr(std::string(by).size());
                            const std::string was = piece;
                            piece = rest.empty() ? std::string("go inside") : "go inside through " + rest;
                            h->note = "a flank with no flank said: \"" + was + "\" read as \"" + piece + "\"";
                        }
                        if (close_said && !CloseToOpen(&piece)) {
                            // the decoder's verb is not "close" ("Cover the door.", "Close down."): the thing said, opened
                            std::string what = "the door";
                            const std::string own = OwnWords(heard);
                            if (AnyIn(own, {" окн", " окош", " ventana"})) what = "the window";
                            else if (AnyIn(own, {" ворот", " portón", " porton"})) what = "the gate";
                            else if (!AnyIn(own, {" двер", " puerta"})) what = "it";
                            for (const char* q : {"main", "north", "south", "west", "east"})
                                if (what != "it" && piece.find(q) != std::string::npos) what = "the " + std::string(q) + what.substr(3);
                            piece = "open " + what;
                        }
                        if (std::string put = LeaveItemPiece(piece); !put.empty()) {
                            h->note = "a leaving of the thing with no place: \"" + piece + "\" read as \"" + put + "\"";
                            piece = put;
                        }
                        if (std::string place; !back_said.empty() && GoBackToPlace(piece, &place)) {
                            const std::string was = piece;
                            piece = "come back to " + place;
                            ++next_back;
                            h->note = "a going back to a place of its own: \"" + was + "\" read as \"" + piece + "\"";
                        } else if (!back_said.empty() && BareBackPiece(piece)) {
                            const std::string& kind = back_said[std::min(next_back++, back_said.size() - 1)];
                            const std::string written = coop::SpeechTextForClassifier(piece);
                            const bool go = written.rfind("go back", 0) == 0;
                            const bool come = written.rfind("come back", 0) == 0 && written.find("to me") != std::string::npos;
                            if ((kind == "back" && !go) || (kind == "me" && !come)) {
                                const std::string was = piece;
                                piece = kind == "back" ? "go back" : "come back to me";
                                h->note = std::string(kind == "back" ? "a going back with no «ко мне» said" : "a going back to the player") + ": \"" +
                                          was + "\" read as \"" + piece + "\"";
                            }
                        }
                    }
                    if (std::string sat = piece; SitOnPiece(&sat)) {
                        h->note = "a sitting on a thing: \"" + piece + "\" read as \"" + sat + "\"";
                        piece = sat;
                    }
                    std::string read = piece;
                    const bool close = close_said || CloseToOpen(&read);
                    // "go up the blue stairs to the roof": up the stairs, then to the roof
                    for (const std::string& part : SplitWayTo(read)) todo.push_back({part, coop::SpeechTextForClassifier(part), close});
                }
                h->rewritten = !todo.empty();
            }
        }
        if (forced) {
            for (const std::string& piece : *forced) todo.push_back({piece, coop::SpeechTextForClassifier(piece)});
            h->rewritten = !todo.empty();
            h->note = "the long-term memory: the player taught the bot this line";
        }
        const bool one = todo.size() <= 1;   // the line gives one order line: it may be what settles the open question
        if (!(answering && one)) held.clear();
        // the line as the next ones will be shown it: the orders the bot read in it, when it was rewritten
        std::string kept;
        for (const Line& l : todo) kept += (kept.empty() ? "" : " ") + l.heard + (std::string(".!?").find(l.heard.back()) == std::string::npos ? "." : "");
        if (todo.empty()) {
            std::string read = heard;
            const bool close = CloseToOpen(&read);   // English words only: a Russian or Spanish line is left as it is
            const bool sat = !foreign && SitOnPiece(&read);   // "sit down on this bench": crouch on it
            if (sat) h->note = "a sitting on a thing: \"" + heard + "\" read as \"" + read + "\"";
            const std::vector<std::string> parts = foreign ? std::vector<std::string>{read} : SplitWayTo(read);
            if (parts.size() > 1) {
                for (const std::string& part : parts) todo.push_back({part, coop::SpeechTextForClassifier(part), close});
            } else {
                todo.push_back(close || sat ? Line{read, coop::SpeechTextForClassifier(read), close} : Line{heard, text, false});
            }
        }
        // each order line with a pointer is read with the crosshair as it was at its own pointer word, in the order said
        const std::vector<double> moments = PointerMoments();
        const std::string line_gaze = planner.World().player_gaze;
        size_t next_moment = 0;
        for (size_t k = 0; k < todo.size(); ++k) {
            Turn t;
            t.line = todo[k].heard;
            if (next_moment < moments.size() && LinePoints(todo[k].heard)) {
                t.at = moments[next_moment++];
                const std::string g = TrailGaze(t.at);
                if (!g.empty()) planner.SetGaze(g);
            }
            const bool ok = Think(todo[k].heard, todo[k].text, &t, err, k > 0);
            planner.SetGaze(line_gaze);
            if (!ok) return false;
            if (todo[k].close && t.r.has_order && t.r.order.intent >= 0 && m.cfg.labels[static_cast<size_t>(t.r.order.intent)] == "OPEN") {
                t.close = true;
                if (t.r.action == "act") t.reply = "Closing it.";
            }
            if (k == 0 && !second.empty() && t.r.action == "say_again" && planner.Mem().has_question) {
                // "say again" changed nothing in the bot or the planner: the decoder's reading of the answer goes instead
                t = Turn();
                t.line = second;
                if (!Think(second, coop::SpeechTextForClassifier(second), &t, err)) return false;
                h->rewritten = true;
                kept = second;
            } else if (k == 0 && c && !forced && !h->decoded && todo.size() == 1 && t.r.action == "say_again") {
                // a second look (bot v55): the router kept the line from the decoder and the bot cannot read it alone. With
                // talk to lean on -- the bot's open question, or earlier lines still in memory -- the decoder reads it in
                // that talk: "on my pin." after "Which window?", "To this wall." after "start shooting"
                bool talk = answering;
                for (const Said& s : said) talk = talk || Ms(now - s.at) <= 1000 * c->memory_seconds;
                std::vector<std::string> pieces;
                if (talk && decode(&pieces) && !pieces.empty() &&
                    !(pieces.size() == 1 && coop::SpeechTextForClassifier(pieces[0]) == coop::SpeechTextForClassifier(text))) {
                    t = Turn();
                    t.line = pieces[0];
                    if (!Think(pieces[0], coop::SpeechTextForClassifier(pieces[0]), &t, err)) return false;
                    h->rewritten = true;
                    h->note = "a second look: the bot could not read the line alone";
                    kept.clear();
                    for (const std::string& piece : pieces)
                        kept += (kept.empty() ? "" : " ") + piece + (std::string(".!?").find(piece.back()) == std::string::npos ? "." : "");
                    for (size_t j = 1; j < pieces.size(); ++j) todo.push_back({pieces[j], coop::SpeechTextForClassifier(pieces[j])});
                }
            }
            h->turns.push_back(std::move(t));
            each(*h, h->turns.back());
            if (k == 0 && answering && one) {
                const coop::PlannerResult& r = h->turns.back().r;
                const bool open = planner.Mem().has_question;
                if (open && planner.Mem().question.intent == asked) break;   // that order is still being settled: what waits goes on waiting
                if (!open && r.has_order && r.order.intent == asked) {       // settled: what waited goes through now
                    h->resumed = held.size();
                    for (const std::string& piece : held) todo.push_back({piece, coop::SpeechTextForClassifier(piece)});
                }
                held.clear();
            } else if (planner.Mem().has_question) {
                held.clear();
                for (size_t r = k + 1; r < todo.size(); ++r) held.push_back(todo[r].heard);
                break;
            }
            const std::string& did = h->turns.back().r.action;
            if (did == "execute" && !after_go.empty()) {
                // the go for an order queued with more after it: the rest of its line follows it now
                h->resumed += after_go.size();
                for (const std::string& piece : after_go) todo.push_back({piece, coop::SpeechTextForClassifier(piece)});
                after_go.clear();
            } else if (did == "queued") {
                // «когда я скажу давай, возьми коробку, потом отнеси её на камень» (2026-11-02, the owner): the orders after
                // the queued one wait for the go too (the planner alone would carry them out at once)
                after_go.clear();
                for (size_t r = k + 1; r < todo.size(); ++r) after_go.push_back(todo[r].heard);
                go_waits = !after_go.empty();
                if (go_waits) break;
            }
        }
        h->held = held;
        if (go_waits) h->held.insert(h->held.end(), after_go.begin(), after_go.end());
        if (g_chain) {
            // a line the bot asked to hear again was not dealt with: the talk so far stays as it was
            bool again = true;
            for (const Turn& t : h->turns) again = again && t.r.action == "say_again";
            if (!again) {
                // a Russian or Spanish line is remembered as the player said it: the decoder learned its earlier lines in
                // the player's language (chains6_v62.py), the bot's own lines in English
                said.push_back({foreign || kept.empty() ? text : kept, now});
                while (said.size() > g_chain->memory_lines) said.pop_front();
                std::string own = h->turns.back().r.say;
                // "what is that?": the game says the answer, and the decoder hears it as the bot's line ("That's the white
                // table."), so «Запрыгни на него» next is onto that table (2026-10-30, the owner's log: onto the rock before)
                // In the game's own words (its object and qualifier), not a taught name or colour: the planner reads the
                // decoder's English by them («зелёный» taught to the white table made it "the green table": "Which table?")
                what_said_lines = -1;
                if (own.empty() && h->turns.back().state == "what")
                    if (const coop::WorldEntity* e = PointedEntity()) {
                        what_said_lines = 0;   // for the next line only (Listen): a later «Это стол.» read with it was "repair"
                        std::string kind_words = (e->qualifier.empty() ? std::string() : e->qualifier + " ") + e->object;
                        std::replace(kind_words.begin(), kind_words.end(), '_', ' ');
                        own = "That's the " + kind_words + ".";
                    }
                bot_said = own.empty() ? Said() : Said{own, now};
            }
        }
        return true;
    }

    // ---- the long-term memory (--memory FILE, bot_memory.h): what the player taught the bot (teach.h) -------------------
    //
    // A line goes through it before the router and the decoder see it:
    //   - a teaching line (teach.h) is dealt with here: "I meant X" carries out X and keeps "the line before means X";
    //     "not that" asks "What did you mean?" and the next line is the meaning; a name or a colour of the thing under
    //     the crosshair is kept; "forget ..." forgets a name or a line. None of them while the bot's question is open:
    //     a line then is its answer;
    //   - a line the memory keeps (NearLine) goes as the order lines kept for it: no router, no decoder;
    //   - any other line has the names the player taught written as the thing's kind ("иди к верстаку" -> "иди к table":
    //     the decoder writes it in English as it is), and the things its names and colours name go to the planner
    //     (WorldState::named), which takes that one among the things the place fits.
    // A "no" right after a line the memory read is a doubt about the kept line; the second doubt forgets it.

    // A taught meaning («запрыгнуть на {x} и присесть», "jumping on the chair and crouching") is read as a line of its own:
    // the decoder without the talk before it, English too (2026-10-31: read after «сядь на диван», «сядь на кровать» it was
    // "crouch using the chair", one order of two). The place's "it" is the planner's (kItSeconds), not the decoder's
    bool taught_alone = false;
    struct Alone {
        bool& flag;
        explicit Alone(bool& f) : flag(f) { flag = true; }
        ~Alone() { flag = false; }
        Alone(const Alone&) = delete;
        Alone& operator=(const Alone&) = delete;
    };
    // a meaning as said, as a line the recognizer would write: a capital first and a stop at the end («Запрыгнуть на стул и
    // присесть.»). The decoder learned such lines: «запрыгнуть на стул и присесть.» was one order, "crouch using the chair"
    static std::string AsLine(const std::string& text) {
        size_t end = text.size();
        while (end > 0 && text[end - 1] == ' ') --end;
        std::string line = CapitalFirst(text.substr(0, end));
        if (!line.empty() && std::string(".!?").find(line.back()) == std::string::npos) line += ".";
        return line;
    }

    struct Recent {                    // a line of the player that was not a teaching one
        std::string norm;              // as heard (MemoryNorm)
        Clock::time_point at;
        bool failed = false;           // the bot asked to hear it again
        int intent = -1;               // the order the bot read in it (its first); -1: none
        std::string kept;              // the kept line the memory read it by (its heard words); empty: none
    };
    std::deque<Recent> recent;         // the last few, kRecentMs at most: what "I meant ..." and "not that" are about
    bool asked_meaning = false;        // the bot asked "What did you mean?": the next line is the meaning
    Clock::time_point asked_at;
    std::vector<std::string> asked_keys;   // ... of these heard lines
    bool asked_failed = false;             // ... the last of which the bot could not read
    int asked_intent = -1;                 // ... or read as this order
    // the bot just said what a thing is ("what is that?", "what colour is it?"): what the player says it is next corrects it
    // (2026-10-30, the owner: «Что это?» "the white table", «Нет, это жёлтый стол»)
    std::string what_key;                  // the thing (its key); empty: none
    Clock::time_point what_at;
    bool asked_what = false;               // the bot asked "Then what is it?": the next line says it
    Clock::time_point asked_what_at;
    // the pattern of a meaning taught with a place both lines name (teach.h MakePattern): the said words with the place as {x},
    // and what they mean: the meaning's English order lines with the place as {x} ("pattern": "jump on {x}", "crouch"), else
    // the meaning as said ("pattern_said": «запрыгнуть на {x} и присесть»). Empty key: none
    struct PatternOffer {
        std::string key, source;
        std::vector<std::string> lines;
    };
    // the last thing the long-term memory kept ("kept_line", "kept_colour", ... and what the reply said of it), for «не надо было
    // запоминать» (2026-11-01, the owner)
    struct Kept {
        std::string did, map;
        json info;
        Clock::time_point at;
        int lines_since = 0;   // the player's lines since (the lesson's own is 0): «забудь это» undoes it only as the next one
    };
    Kept last_kept;
    void NoteKept(const json& info) {
        const std::string did = info.contains("did") && info["did"].is_string() ? info["did"].get<std::string>() : std::string();
        if (did.rfind("kept_", 0) != 0) return;
        last_kept = {did, planner.World().map, info, Clock::now()};
    }
    // the bot's last line as it was said, in the player's language: «не расслышал» says it again
    std::string last_line, repeat_said;
    Clock::time_point last_line_at;
    struct Offer {                         // the bot asked "Shall I remember it as X?"; "yes" keeps the name
        bool open = false;
        std::string key, name;             // key: the thing's, or the room's behind a door (RoomKey)
        Clock::time_point at;
        // ... or "Shall I remember that "X" means "Y"?" (OfferMeaning): "yes" keeps the heard lines `keys` as the order lines
        bool meaning = false;
        std::vector<std::string> keys, lines;
        std::string intent;
        // ... or "Like this: "за́мок"?" (a pronunciation): "yes" keeps how the voice says `word`
        bool pronounce = false;
        std::string word, say;
        // ... or "Shall I say "пошёл" instead of "выдвигаюсь"?" (the bot's own line): `word` its sentence (normalized), `say`
        // the new words (empty: nothing)
        bool phrase = false;
        bool phrase_word = false;          // ... `word` is words inside the bot's sentences, not a whole one
        // ... or "Shall I keep 3 m from you?" (a setting): `word` its name, `value`
        bool setting = false;
        double value = 0;
        // a meaning with a place both lines name: "yes" keeps the patterns too, one for each heard line in `keys`
        std::vector<PatternOffer> patterns;
    } offer;
    std::deque<std::string> lines_said;      // the bot's last sentences in the player's language, as the tables wrote them (HeardFromBot)

    // what the memory did with a line: the reply's "memory"
    struct Memo {
        bool answered = false;         // the memory answered the line itself with `say` (English); no order went out
        std::string say;
        bool remembered = false;       // a meaning was kept: kRemembered goes before the order's own words
        std::string ask;               // a question after the order's own words (English; OfferMeaning)
        json info = json::object();
        coop::Localizer::Terms terms;  // the words of `say` the reply tables do not have: a name the player gave a thing
    };

    static constexpr double kRecentMs = 60000;    // "I meant ..." is about a line said this long ago at most
    static constexpr double kMeaningMs = 30000;   // the answer to "What did you mean?" comes this soon
    static constexpr double kDoubtMs = 10000;     // a "no" this soon after a line the memory read doubts the kept line
    static constexpr double kWhatMs = 20000;      // "no, it's X" is about the bot's answer to "what is that?" this soon
    static constexpr double kOfferMs = 30000;     // "yes" to "Shall I remember it as X?" comes this soon
    static constexpr size_t kOfferWords = 6;      // a line heard wrong of more words is not offered as a way of saying another
    static constexpr double kNearM = 3.0;         // "no, it's the lantern": a lantern this near the thing asked about is it

    void ForgetTalk() {
        recent.clear();
        asked_meaning = false;
        asked_keys.clear();
        what_key.clear();
        asked_what = false;
        offer.open = false;
    }

    // what the line points at: the thing under the crosshair at its first pointer word ("this", «это»), else when the
    // line was said
    std::string PointedThing() const {
        const std::vector<double> moments = PointerMoments();
        if (!moments.empty()) {
            const std::string g = TrailGaze(moments[0]);
            if (!g.empty()) return g;
        }
        return planner.World().player_gaze;
    }
    const coop::WorldEntity* EntityById(const std::string& id) const {
        for (const coop::WorldEntity& e : planner.World().entities)
            if (e.id == id) return &e;
        return nullptr;
    }
    // the memory keeps a thing by its key (the actor in the level, world.h), the game's ids change from line to line
    static const std::string& KeyOf(const coop::WorldEntity& e) { return e.key.empty() ? e.id : e.key; }
    const coop::WorldEntity* EntityByKey(const std::string& key) const {
        for (const coop::WorldEntity& e : planner.World().entities)
            if (KeyOf(e) == key) return &e;
        return nullptr;
    }
    // the name the player gave the thing kept by this key in their language on this map; nullptr: none
    const coop::MemoryName* NameByKey(const std::string& key) const {
        if (!g_memory || !g_memory->IsOpen()) return nullptr;   // a brain with no memory (WhichCallout asks it too)
        for (const coop::MemoryName& n : g_memory->Names())
            if (n.map == planner.World().map && n.lang == g_language && n.entity == key) return &n;
        return nullptr;
    }
    const coop::MemoryName* NameOf(const coop::WorldEntity& e) const { return NameByKey(KeyOf(e)); }
    // the bot's name: the one the player gave it, else the game's (the world's "bot": {"name"}); empty: none
    std::string BotName() const {
        if (g_memory && g_memory->IsOpen())
            if (const coop::MemoryPerson* person = g_memory->PersonFor("bot")) return person->name;
        return planner.World().bot_name;
    }
    // the player's name as they told it; empty: not told
    static std::string PlayerName() {
        if (!g_memory || !g_memory->IsOpen()) return {};
        const coop::MemoryPerson* person = g_memory->PersonFor("player");
        return person ? person->name : std::string();
    }

    // ---- the talk in a role (talker.h, Talk) ----
    static const char* LanguageName(const std::string& lang) { return lang == "ru" ? "Russian" : lang == "es" ? "Spanish" : "English"; }
    static std::string ThingWords(const coop::WorldEntity& e) {
        std::string s = e.qualifier.empty() ? e.object : e.qualifier + " " + e.object;
        for (char& c : s) c = c == '_' ? ' ' : c;
        return s;
    }
    // The system turn for a role: its character, what the speaker is called, for the bot what it holds and what is near the
    // player (the world of this line), the habit of «брат», and the language to answer in
    // the language a role answers in: its own (a person of the level who speaks one: the game's "role" "lang"), else the player's
    static std::string RoleLanguage(const std::string& role) {
        if (role == "bot" || !g_talk) return g_language;
        const auto it = g_talk->roles.find(role);
        return it == g_talk->roles.end() || it->second.lang.empty() ? g_language : it->second.lang;
    }
    std::string TalkSystem(const std::string& role) const {
        const Talk::Role& r = g_talk->roles.at(role);
        const std::string lang = RoleLanguage(role);
        std::string name = role == "bot" ? BotName() : std::string();
        if (name.empty()) {
            auto it = r.names.find(lang);
            if (it == r.names.end()) it = r.names.find("en");
            if (it != r.names.end()) name = it->second;
        }
        std::string s = r.text;
        for (size_t at = s.find("{name}"); at != std::string::npos && !name.empty(); at = s.find("{name}", at + name.size())) s.replace(at, 6, name);
        s += "\n";
        if (!name.empty()) s += "\nYour name is " + name + ".";
        // a woman or a man (2026-11-12: Anna, a teller of the role both tellers share, said «Я бы ... хотел»): the forms of the words
        // she says of herself in Russian and Spanish; nothing about who she is besides (the robot stays a robot)
        if (!r.gender.empty() && lang != "en")
            s += std::string("\nWhen you speak ") + LanguageName(lang) + ", use the " + (r.gender == "woman" ? "feminine" : "masculine") +
                 " forms for yourself.";
        if (role == "bot") {
            const std::string player = PlayerName();
            if (!player.empty()) s += "\nThe player's name is " + player + ".";
            // what it holds and stands on, the car; and the thing the player looks at ("what do you think of this car?"). Not the
            // things around: shown a list, the model works them into every answer («могу поднять красный автомобиль»)
            const coop::WorldState& w = planner.World();
            if (!w.scene.empty()) s += "\nYou now: " + w.scene + ".";
            for (const coop::WorldEntity& e : w.entities)
                if (!w.player_gaze.empty() && e.id == w.player_gaze && !e.object.empty()) s += "\nThe player is looking at the " + ThingWords(e) + ".";
            if (g_replies != nullptr && g_replies == g_bro_replies)
                s += std::string("\nYou call the player \"") + (g_language == "ru" ? "брат" : g_language == "es" ? "hermano" : "bro") + "\" now and then.";
        } else if (r.bro) {
            // a person of the level with the habit (the game's "role" "bro": true; 2026-11-14, the owner: «Mike, Tony, Nick должны
            // получить роли RU+BRAT»): always on, the player's words do not switch it off (that is the bot's own habit, bro.h)
            s += std::string("\nYou call the player \"") + (lang == "ru" ? "брат" : lang == "es" ? "hermano" : "bro") + "\" now and then.";
        }
        // a person who speaks a language of their own answers in it whatever the player's is (the player may not understand)
        s += std::string("\nAnswer in ") + LanguageName(lang) + " only, in one or two short sentences.";
        return s;
    }
    // The role's answer to the line, in the role's talk so far; one more draw when the answer is empty or not in the player's
    // language. False (and *err): no answer to say, the caller keeps its own words. *info: how it went, for the reply
    bool TalkReply(const std::string& role, const std::string& line, std::string* say, json* info, std::string* err) {
        const auto t0 = Clock::now();
        const std::string system = TalkSystem(role);
        const std::vector<coop::TalkTurn> before = g_talk->Before(role);
        std::string raw, answer;
        coop::Talker::Stats st;
        int tries = 0;
        bool ok = false;
        for (; tries < 2 && !ok; ++tries) {
#ifdef COOP_WITH_LLM
            if (!g_talk->model.Reply(system, before, line, &raw, &st, err, tries > 0)) return false;
#else
            return *err = "this coop_cli was built without llama.cpp", false;
#endif
            answer = coop::TalkAnswer(raw, st.cut_off);
            ok = !answer.empty() && coop::TalkInLanguage(answer, RoleLanguage(role));
        }
        *info = {{"role", role}, {"ms", std::round(Ms(Clock::now() - t0))}, {"tokens", st.generated}, {"cached", st.cached},
                 {"evaluated", st.evaluated}, {"dropped", st.dropped}, {"tries", tries}, {"cut_off", st.cut_off},
                 {"before", before.size()}};
        if (raw != answer) (*info)["raw"] = raw;
        if (!ok) return *err = "the talking model gave nothing to say in " + std::string(LanguageName(RoleLanguage(role))) + ": \"" + raw + "\"", false;
        g_talk->Keep(role, line, answer);
        *say = answer;
        return true;
    }
    // a name said in a reply: the tables' open slot {name} gets it as said (their match lowers ASCII letters only)
    static void NameTerm(Memo* memo, const std::string& name) {
        std::string key = name;
        for (char& c : key) c = static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
        memo->terms["name"][key] = {{"text", name}};
    }
    // Rooms (2026-10-30). The bot sees no rooms, only doors: a door whose inside the level marks (AOVCoopPlaceMarker's
    // InsidePoint, the game's tag "inside"; a barn's gate too) leads into one, and a name for the room is kept by the door's
    // key + "/room". "go to the garage" is read as the door named so, and the order goes in (or out) through it (RoomOrder)
    static bool HasInside(const coop::WorldEntity& e) {
        return !e.object.empty() && std::find(e.tags.begin(), e.tags.end(), "inside") != e.tags.end();
    }
    static std::string RoomKey(const coop::WorldEntity& e) { return KeyOf(e) + "/room"; }
    static bool IsRoomKey(const std::string& key) { return key.size() > 5 && key.compare(key.size() - 5, 5, "/room") == 0; }
    // the thing a kept name or colour is about: the thing of that key, or the door of a room
    const coop::WorldEntity* EntityOfKey(const std::string& key) const {
        if (!IsRoomKey(key)) return EntityByKey(key);
        const coop::WorldEntity* door = EntityByKey(key.substr(0, key.size() - 5));
        return door && HasInside(*door) ? door : nullptr;
    }
    // the words name the room behind the door `e`, not the door: a door with an inside, and words of another kind than the
    // door's («гараж», "the storage"); «дверь в гараж» leaves the room's own words in *room
    bool RoomName(const coop::WorldEntity& e, const std::vector<std::string>& spoken_words, std::vector<std::string>* room) const {
        if (!HasInside(e) || spoken_words.empty()) return false;
        static const std::set<std::string> kInto = {"в", "во", "to", "into", "of", "a", "al", "del", "de"};
        if (spoken_words.size() >= 3 && KindOf({spoken_words[0]}) == e.object && kInto.count(spoken_words[1])) {
            size_t b = 2;
            while (b < spoken_words.size() && (spoken_words[b] == "the" || spoken_words[b] == "la" || spoken_words[b] == "el")) ++b;
            if (b < spoken_words.size()) {
                room->assign(spoken_words.begin() + static_cast<std::ptrdiff_t>(b), spoken_words.end());
                return true;
            }
        }
        if (KindOf(spoken_words) == e.object) return false;
        *room = spoken_words;
        return true;
    }
    // the thing under the crosshair, if it is a thing of a kind (not a point on the floor, "gaze_17")
    const coop::WorldEntity* PointedEntity() const {
        const std::string thing = PointedThing();
        const coop::WorldEntity* e = thing.empty() ? nullptr : EntityById(thing);
        return e && !e->object.empty() ? e : nullptr;
    }
    // the colour the player taught this thing on this map; nullptr: none
    const coop::MemoryColour* TaughtColour(const coop::WorldEntity& e) const {
        if (!g_memory || !g_memory->IsOpen()) return nullptr;
        for (const coop::MemoryColour& c : g_memory->Colours())
            if (c.map == planner.World().map && c.entity == KeyOf(e)) return &c;
        return nullptr;
    }
    // its colour: the one the player taught, else the game's (a qualifier that is a colour: the "white" table); empty: none
    std::string ColourOfThing(const coop::WorldEntity& e) const {
        if (const coop::MemoryColour* c = TaughtColour(e)) return c->colour;
        const std::vector<std::string>& ids = coop::ColourIds();
        return std::find(ids.begin(), ids.end(), e.qualifier) != ids.end() ? e.qualifier : std::string();
    }
    // a thing the words name by a name the player taught, on this map; nullptr: none
    const coop::WorldEntity* NamedIn(const std::vector<std::string>& spoken_words) const {
        for (const coop::MemoryName& n : g_memory->Names()) {
            size_t b = 0, en = 0;
            if (n.map != planner.World().map || n.lang != g_language || IsRoomKey(n.entity) ||   // a room has no colour
                !coop::FindWords(spoken_words, coop::MemoryWords(n.name), 0, &b, &en))
                continue;
            if (const coop::WorldEntity* e = EntityByKey(n.entity)) return e;
        }
        return nullptr;
    }
    static bool EndsWith(const std::string& s, const std::string& end) {
        return s.size() >= end.size() && s.compare(s.size() - end.size(), end.size(), end) == 0;
    }
    // "the yellow table" (a kind, with a colour or none) as the bot says it, and its words in the player's language in
    // memo->terms («жёлтый стол», «la mesa amarilla»): the reply tables' "{thing}" takes them
    std::string ThingWordsFor(const std::string& kind, const std::string& colour, Memo* memo) const {
        std::string k = kind;
        std::replace(k.begin(), k.end(), '_', ' ');
        const std::string adj_en = colour.empty() ? std::string() : coop::ColourAdjective(colour, "en", 'm', false);
        const std::string en = "the " + (adj_en.empty() ? k : adj_en + " " + k);
        std::map<std::string, std::string> forms = {{"text", en}, {"acc", en}};
        const std::string lang = g_replies ? g_replies->Language() : std::string("en");
        const std::map<std::string, std::string>* f = g_replies ? g_replies->Forms("object", k) : nullptr;
        if (f && f->count("text") && lang == "ru") {
            const std::string noun = f->at("text"), which = f->count("which") ? f->at("which") : std::string();
            const char g = which == "какая" ? 'f' : which == "какое" ? 'n' : which == "какие" ? 'p' : 'm';
            std::string acc = noun;   // a feminine noun in -а / -я is -у / -ю
            if (g == 'f' && EndsWith(acc, "а")) acc = acc.substr(0, acc.size() - std::string("а").size()) + "у";
            else if (g == 'f' && EndsWith(acc, "я")) acc = acc.substr(0, acc.size() - std::string("я").size()) + "ю";
            const std::string adj = colour.empty() ? std::string() : coop::ColourAdjective(colour, "ru", g, false),
                              adj_acc = colour.empty() ? std::string() : coop::ColourAdjective(colour, "ru", g, true);
            forms = {{"text", adj.empty() ? noun : adj + " " + noun}, {"acc", adj_acc.empty() ? acc : adj_acc + " " + acc}};
        } else if (f && f->count("text") && lang == "es") {
            const std::string noun = f->at("text"), none = f->count("none") ? f->at("none") : std::string();
            const bool fem = none.rfind("ninguna", 0) == 0 ||
                             (none.rfind("ningún", 0) != 0 && (EndsWith(noun, "a") || EndsWith(noun, "ión")));
            const std::string adj = colour.empty() ? std::string() : coop::ColourAdjective(colour, "es", fem ? 'f' : 'm', false);
            const std::string text = std::string(fem ? "la " : "el ") + noun + (adj.empty() ? "" : " " + adj);
            forms = {{"text", text}, {"acc", text}};
        }
        memo->terms["thing"][en] = forms;
        return en;
    }
    // The planner's "Which chair? The one ahead, 8 m?" as a callout (2026-10-30, the owner: a distance tells the player nothing;
    // say its colour, its name): the thing offered by the name the player taught it, else by its colour when no other thing
    // asked about has that colour, else by its qualifier ("the north door") when no other has that one and the reply tables
    // know the words. Empty: none sets it apart, and the planner's words stay
    std::string WhichCallout(coop::Localizer::Terms* terms) const {
        const coop::Memory& mem = planner.Mem();
        if (!mem.has_question || mem.question.kind != "which") return {};
        const coop::Memory::Question& q = mem.question;
        if (q.offered < 0 || q.offered >= static_cast<int>(q.candidates.size())) return {};
        const coop::WorldEntity* e = EntityById(q.candidates[static_cast<size_t>(q.offered)]);
        if (!e || e->object.empty()) return {};
        std::vector<const coop::WorldEntity*> others;
        for (const std::string& id : q.candidates)
            if (id != e->id)
                if (const coop::WorldEntity* o = EntityById(id)) others.push_back(o);
        Memo memo;
        std::string called;
        if (NameOf(*e)) {
            called = Called(*e, &memo);
        } else if (const std::string colour = ColourOfThing(*e); !colour.empty() &&
                   std::none_of(others.begin(), others.end(), [&](const coop::WorldEntity* o) { return ColourOfThing(*o) == colour; })) {
            called = ThingWordsFor(e->object, colour, &memo);
        } else if (!e->qualifier.empty() &&
                   std::none_of(others.begin(), others.end(), [&](const coop::WorldEntity* o) { return o->qualifier == e->qualifier; })) {
            std::string qualified = "the " + e->qualifier + " " + e->object;
            std::replace(qualified.begin(), qualified.end(), '_', ' ');
            if (!g_replies || g_replies->Language() == "en" || g_replies->Forms("thing", qualified)) called = qualified;
        }
        std::string obj = e->object;
        std::replace(obj.begin(), obj.end(), '_', ' ');
        if (called.empty()) {
            // nothing of its own sets it apart: where it is, without the metres, when no other one is that way ("Which door?
            // The one ahead?"); else the planner's words, metres and all, the one thing that tells them apart
            auto sector = [](const coop::WorldEntity& x) {
                const std::string d = coop::Describe(x);
                return d.substr(0, d.find(", "));
            };
            const std::string where = sector(*e);
            if (std::any_of(others.begin(), others.end(), [&](const coop::WorldEntity* o) { return sector(*o) == where; })) return {};
            return "Which " + obj + "? The one " + where + "?";
        }
        *terms = memo.terms;
        return "Which " + obj + "? You mean " + called + "?";
    }
    // how the bot names this thing: the name the player gave it, else its kind with its colour (ThingWordsFor)
    std::string Called(const coop::WorldEntity& e, Memo* memo) const {
        if (const coop::MemoryName* n = NameOf(e)) {
            const std::string called = (g_language == "en" ? "the " : "") + n->name;
            memo->terms["thing"][called] = {{"text", called}, {"acc", called}};
            return called;
        }
        return ThingWordsFor(e.object, ColourOfThing(e), memo);
    }
    // the kind of thing (the vocabulary's object id) the words name: the vocabulary's English words ("box": crate), the
    // reply table's word for each kind («стол», «ящик», «mesa») and for its things («коробка»: "a box"); empty: none
    std::string KindOf(const std::vector<std::string>& spoken_words) const {
        const coop::LocationMatcher& places = brain.Places();
        if (!places.Ready() || spoken_words.empty()) return {};
        auto english = [&](const std::vector<std::string>& w) -> std::string {
            for (size_t n = std::min<size_t>(3, w.size()); n >= 1; --n)
                for (size_t b = 0; b + n <= w.size(); ++b) {
                    std::string joined;
                    for (size_t i = b; i < b + n; ++i) joined += (joined.empty() ? "" : " ") + w[i];
                    int idx = -1;
                    const char* kind = places.PhraseKind(joined, &idx);
                    if (kind && std::string(kind) == "object" && idx >= 0) return places.ObjectId(idx);
                }
            return {};
        };
        const std::string en = english(spoken_words);
        if (!en.empty() || !g_replies || g_replies->Language() == "en") return en;
        size_t b = 0, e = 0;
        for (const std::string& v : g_replies->Values("object")) {
            const auto* f = g_replies->Forms("object", v);
            if (!f || !f->count("text")) continue;
            std::string id = v;
            std::replace(id.begin(), id.end(), ' ', '_');
            if (places.ObjectIndex(id) >= 0 && coop::FindWords(spoken_words, coop::MemoryWords(coop::MemoryNorm(f->at("text"))), 0, &b, &e)) return id;
        }
        for (const std::string& v : g_replies->Values("thing")) {
            const auto* f = g_replies->Forms("thing", v);
            if (!f || !f->count("text")) continue;
            const std::string id = english(coop::MemoryWords(coop::MemoryNorm(v)));
            if (!id.empty() && coop::FindWords(spoken_words, coop::MemoryWords(coop::MemoryNorm(f->at("text"))), 0, &b, &e)) return id;
        }
        return {};
    }
    // a thing of `kind` (and `colour`, if one is said) within kNearM of `e`, not `e`; nullptr: none
    const coop::WorldEntity* NearThing(const coop::WorldEntity& e, const std::string& kind, const std::string& colour) const {
        auto at = [](const coop::WorldEntity& x) {
            const double r = x.bearing * 3.14159265358979323846 / 180.0;
            return std::array<double, 3>{x.distance * std::cos(r), x.distance * std::sin(r), x.elevation};
        };
        const auto pe = at(e);
        const coop::WorldEntity* best = nullptr;
        double best_d = kNearM;
        for (const coop::WorldEntity& x : planner.World().entities) {
            if (&x == &e || x.object != kind || (!colour.empty() && ColourOfThing(x) != colour)) continue;
            const auto px = at(x);
            const double d = std::sqrt((px[0] - pe[0]) * (px[0] - pe[0]) + (px[1] - pe[1]) * (px[1] - pe[1]) +
                                       (px[2] - pe[2]) * (px[2] - pe[2]));
            if (d <= best_d) best = &x, best_d = d;
        }
        return best;
    }
    // «нет, это камень» about a rock the player named otherwise (2026-10-30, the owner: «фонарь», then «нет, это камень» was "Got
    // it." and the name stayed): its name in this language goes, and the bot calls it by its kind again. False: none to forget
    bool ForgetOwnName(const coop::WorldEntity& e, Memo* memo) const {
        const coop::MemoryName* n = NameOf(e);
        if (!n) return false;
        const std::string name = n->name;
        bool any = false;
        std::string problem;
        if (!g_memory->ForgetName(planner.World().map, KeyOf(e), g_language, &any, &problem)) MemoryError(memo, problem);
        memo->info["forgot_name"] = {{"entity", e.id}, {"key", KeyOf(e)}, {"name", name}};
        return any;
    }
    static bool Answer(Memo* memo, const std::string& say, const char* did) {
        memo->answered = true;
        memo->say = say;
        memo->info["did"] = did;
        return true;
    }
    // the bot asks "Shall I remember it as X?" with the words as the player said them; "yes" keeps the name (Listen). At a
    // door with an inside, words of another kind name the room behind it: "Shall I remember that X is behind this door?"
    bool OfferName(const coop::WorldEntity& e, const std::vector<std::string>& spoken_words, Clock::time_point now, Memo* memo) {
        std::vector<std::string> room;
        const bool is_room = RoomName(e, spoken_words, &room);
        std::string name;
        for (const std::string& w : is_room ? room : spoken_words) name += (name.empty() ? "" : " ") + w;
        // a new question: nothing of the one before it stays (2026-10-30: an unanswered "Shall I remember that ... means ...?"
        // left its kind behind, and "yes" to "Shall I remember it as X?" kept that line instead of the name)
        offer = Offer();
        offer.open = true;
        offer.key = is_room ? RoomKey(e) : KeyOf(e);
        offer.name = name;
        offer.at = now;
        const std::string called = (g_language == "en" ? "the " : "") + name;
        memo->terms["thing"][called] = {{"text", called}, {"acc", called}};
        memo->info["offered_name"] = {{"entity", e.id}, {"key", offer.key}, {"name", name}};
        if (is_room) {
            memo->info["offered_name"]["room"] = true;
            return Answer(memo, kOfferRoomA + called + kOfferRoomB, "offered_name");
        }
        return Answer(memo, "Shall I remember it as " + called + "?", "offered_name");
    }
    // the bot's sentences it said last, as the reply tables wrote them (in the player's language): what «так не говори» and
    // «вместо «выдвигаюсь» говори …» are about
    void HeardFromBot(const std::string& text) {
        if (!text.empty() && text != repeat_said) {
            last_line = text;
            last_line_at = Clock::now();
        }
        for (const std::string& sentence : coop::SplitSentences(text)) {
            if (coop::MemoryWords(coop::MemoryNorm(sentence)).empty()) continue;
            lines_said.push_back(sentence);
            while (lines_said.size() > 12) lines_said.pop_front();
        }
    }
    // a sentence as the phrases are kept: normalized, without the habit's «брат» (the same line with and without it)
    static std::string PhraseKey(const std::string& sentence) {
        static const std::unordered_set<std::string> kFiller = {"брат", "братан", "братишка", "bro", "brother", "hermano"};
        std::string out;
        for (const std::string& w : coop::MemoryWords(coop::MemoryNorm(sentence)))
            if (!kFiller.count(w)) out += (out.empty() ? "" : " ") + w;
        return out;
    }
    // «вместо «выдвигаюсь» говори «пошёл»», «так не говори»: the bot's own line, said otherwise (2026-10-30, the owner: the player
    // teaches the bot everything). The line must be one the bot says: one of its last sentences, or a fixed one of the reply table
    bool OfferPhrase(const coop::TeachLine& t, Clock::time_point now, Memo* memo) {
        std::string key, shown;
        bool word = false;
        if (t.said.empty()) {   // «так не говори»: the bot's last line (its first sentence)
            if (lines_said.empty()) return Answer(memo, kPointAtIt, "no_line");
            shown = lines_said.back();
            key = PhraseKey(shown);
        } else {
            key = PhraseKey(t.said);
            for (auto it = lines_said.rbegin(); it != lines_said.rend() && shown.empty(); ++it)
                if (PhraseKey(*it) == key) shown = *it;
            if (shown.empty() && g_replies)
                for (const std::string& f : g_replies->FixedSentences())
                    if (PhraseKey(f) == key) {
                        shown = f;
                        break;
                    }
            // words inside the bot's sentences («не говори брат», «вместо «метров» говори «шагов»»): every sentence with them
            if (shown.empty()) {
                const std::vector<std::string> said_words = coop::MemoryWords(coop::MemoryNorm(t.said));
                auto inside = [&](const std::string& sentence) {
                    const std::vector<std::string> sw = coop::MemoryWords(coop::MemoryNorm(sentence));
                    for (size_t i = 0; i + said_words.size() <= sw.size(); ++i) {
                        bool same = true;
                        for (size_t k = 0; k < said_words.size() && same; ++k) same = sw[i + k] == said_words[k];
                        if (same) return true;
                    }
                    return false;
                };
                for (auto it = lines_said.rbegin(); it != lines_said.rend() && shown.empty(); ++it)
                    if (inside(*it)) shown = *it;
                if (shown.empty() && g_replies)
                    for (const std::string& f : g_replies->FixedSentences())
                        if (inside(f)) {
                            shown = f;
                            break;
                        }
                if (!shown.empty() && !said_words.empty()) {
                    key.clear();
                    for (const std::string& w : said_words) key += (key.empty() ? "" : " ") + w;
                    word = true;
                }
            }
            if (shown.empty()) {
                memo->terms["said"][t.said] = {{"text", t.said}};
                return Answer(memo, "I don't say \"" + t.said + "\".", "not_a_line");
            }
        }
        if (key.empty()) return Answer(memo, kPointAtIt, "no_line");
        std::string to = t.rest;
        while (!to.empty() && std::string(" .!?,«»\"'").find(to.back()) != std::string::npos) to.pop_back();
        offer = Offer();
        offer.open = true;
        offer.phrase = true;
        offer.phrase_word = word;
        offer.word = key;
        offer.say = to;
        offer.at = now;
        memo->info["offered_phrase"] = {{"from", key}, {"to", to}, {"line", shown}, {"word", word}};
        memo->terms["said"][key] = {{"text", key}};
        if (to.empty()) return Answer(memo, "Shall I stop saying \"" + key + "\"?", "offered_phrase");
        const std::string meant = coop::MemoryNorm(to);
        memo->terms["meant"][meant] = {{"text", to}};
        return Answer(memo, "Shall I say \"" + meant + "\" instead of \"" + key + "\"?", "offered_phrase");
    }
    // the bot's settings the game lets the player change by voice, with the game's own values (OVCoopBotDefinition: FollowDistance
    // 450, EngageRange 3500, VoiceSpeed 1; fire at will) for "nearer" and "faster" when none is kept
    static double SettingNow(const std::string& name) {
        if (g_memory && g_memory->IsOpen())
            for (const coop::MemorySetting& x : g_memory->Settings())
                if (x.name == name) return x.value;
        return name == "follow_m" ? 4.5 : name == "engage_m" ? 35.0 : name == "voice_speed" ? 1.0 : 0.0;
    }
    static json SettingsJson() {
        json out = json::object();
        if (g_memory && g_memory->IsOpen())
            for (const coop::MemorySetting& x : g_memory->Settings()) out[x.name] = x.value;
        return out;
    }
    // «держись в трёх метрах»: the bot says the setting back and asks before it keeps it
    bool OfferSetting(const coop::TeachLine& t, Clock::time_point now, Memo* memo) {
        double v = t.scale > 0 ? SettingNow(t.setting) * t.scale : t.value;
        std::string ask;
        if (t.setting == "follow_m") {
            v = std::clamp(std::round(v), 1.0, 20.0);
            ask = "Shall I keep " + std::to_string(static_cast<int>(v)) + " m from you?";
        } else if (t.setting == "engage_m") {
            v = std::clamp(std::round(v), 3.0, 60.0);
            ask = "Shall I open fire within " + std::to_string(static_cast<int>(v)) + " m?";
        } else if (t.setting == "fire_on_command") {
            ask = v > 0.5 ? "Shall I shoot only on your command?" : "Shall I shoot on my own?";
        } else if (t.setting == "voice_speed") {
            v = std::clamp(std::round(v * 20.0) / 20.0, 0.6, 1.6);
            ask = t.scale > 1 ? "Shall I speak faster?" : t.scale > 0 ? "Shall I speak slower?" : "Shall I speak at the usual speed?";
        } else {
            return false;
        }
        offer = Offer();
        offer.open = true;
        offer.setting = true;
        offer.word = t.setting;
        offer.value = v;
        offer.at = now;
        memo->info["offered_setting"] = {{"name", t.setting}, {"value", v}};
        return Answer(memo, ask, "offered_setting");
    }
    // how the voice says a word, said back the new way: "Like this: "за́мок"?" (the reply is spoken, so the player hears it);
    // "yes" keeps it (Listen)
    bool OfferSaying(const coop::TeachLine& t, Clock::time_point now, Memo* memo) {
        const std::string say = t.rest.empty() ? coop::StressedWord(t.said, t.stress, t.vowel) : t.rest;
        offer = Offer();
        offer.open = true;
        offer.pronounce = true;
        offer.word = t.said;
        offer.say = say;
        offer.at = now;
        memo->info["offered_saying"] = {{"word", t.said}, {"say", say}};
        memo->terms["said"][say] = {{"text", say}};
        return Answer(memo, "Like this: \"" + say + "\"?", "offered_saying");
    }
    // "no, it's the yellow table" with a yellow table next to the one asked about: the bot names that one, and the next
    // correction is about it
    bool PointedAt(const coop::WorldEntity& f, Clock::time_point now, Memo* memo) {
        what_key = KeyOf(f);
        what_at = now;
        memo->info["pointed_at"] = {{"entity", f.id}, {"key", KeyOf(f)}};
        return Answer(memo, "That's " + Called(f, memo) + ".", "pointed_at");
    }
    // what the player says the thing `e` is right after the bot named it (ThingWords' words): its colour («нет, это жёлтый
    // стол», «нет, он жёлтый»: kept), the thing beside it they meant (a yellow table next to it: the bot names that one), or
    // a name of its own («красный фонарь», «гараж»: the bot asks before it keeps it); «нет, это стол» about the table: nothing
    bool CorrectThing(const coop::WorldEntity& e, const std::vector<std::string>& spoken_words, Clock::time_point now, Memo* memo) {
        what_key.clear();
        const std::vector<std::string> colours = coop::ColoursIn(spoken_words);
        std::vector<std::string> noun;
        for (const std::string& w : spoken_words)
            if (coop::ColoursIn({w}).empty() && !coop::GenericThingWord(w)) noun.push_back(w);
        const std::string colour = colours.size() == 1 ? colours[0] : std::string();
        const std::string kind = noun.empty() ? e.object : KindOf(noun);
        memo->info["correction"] = {{"entity", e.id}, {"words", spoken_words}, {"kind", kind}, {"colour", colour}};
        if (colours.size() > 1) return OfferName(e, spoken_words, now, memo);
        if (kind == e.object) {
            std::vector<std::string> room;   // «нет, это дверь в гараж»: the room behind it
            if (colours.empty() && RoomName(e, spoken_words, &room)) return OfferName(e, spoken_words, now, memo);
            if (colour.empty() || colour == ColourOfThing(e))
                return ForgetOwnName(e, memo) ? Answer(memo, kRemembered, "forgot_name") : Answer(memo, kGotIt, "same_thing");
            if (!noun.empty())
                if (const coop::WorldEntity* f = NearThing(e, kind, colour)) return PointedAt(*f, now, memo);
            std::string problem;
            if (!g_memory->KeepColour({planner.World().map, KeyOf(e), colour, 0}, &problem)) MemoryError(memo, problem);
            memo->info["kept_colour"] = {{"entity", e.id}, {"key", KeyOf(e)}, {"colour", colour}};
            return Answer(memo, kRemembered, "kept_colour");
        }
        if (!kind.empty())
            if (const coop::WorldEntity* f = NearThing(e, kind, colour)) return PointedAt(*f, now, memo);
        return OfferName(e, spoken_words, now, memo);
    }
    const std::string& LabelOf(const Turn& t) const {
        static const std::string kNone = "NONE";
        const int i = t.r.decision.intent;
        return i >= 0 ? m.cfg.labels[static_cast<size_t>(i)] : kNone;
    }

    // the heard lines a meaning is for: the last line, and the ones just before it the bot could not read that sound like
    // it (the recognizer heard "on my go" twice, two ways)
    std::vector<std::string> MeaningKeys() const {
        std::vector<std::string> keys;
        if (recent.empty()) return keys;
        const Recent& last = recent.back();
        keys.push_back(last.norm);
        for (size_t i = 0; i + 1 < recent.size(); ++i) {
            const Recent& r = recent[i];
            if (!r.failed || r.norm == last.norm || Ms(last.at - r.at) > kRecentMs) continue;
            if (std::find(keys.begin(), keys.end(), r.norm) != keys.end()) continue;
            if (coop::NearLine(r.norm, last.norm) || coop::TrigramJaccard(r.norm, last.norm) >= 0.6) keys.push_back(r.norm);
        }
        return keys;
    }
    // a meaning the bot read as orders: no "say again", no "no", no cancel ("I said open fire, but no, don't fire")
    bool Understood(const Heard& h) const {
        if (h.turns.empty()) return false;
        for (const Turn& t : h.turns) {
            const std::string& label = LabelOf(t);
            if (t.r.action == "say_again" || t.r.action == "ignore" || t.r.action == "negated" || label == "NO" || label == "NONE") return false;
        }
        return true;
    }
    // the meaning is what the line before meant, not a new place for the order it gave: "go to the door", then "I meant
    // the window" is the same order at another place (the planner's short context), and "go to the door" must not mean
    // "the window" from then on (2026-10-29, teach_corpus_check.py: «я сказал на кухню», "dije sur, no norte"). So a line
    // the bot could not read, or read as another order than the meaning's
    static bool Misread(bool failed, int intent, const Heard& meaning) {
        return failed || meaning.turns.empty() || meaning.turns[0].r.decision.intent != intent;
    }
    // a plain «это X» / "this is X" is a name when the bot reads no order in it ("this is the workbench": say again)
    bool NoOrder(const Heard& h) const {
        for (const Turn& t : h.turns)
            if (!(t.r.action == "say_again" || t.r.action == "ignore" || LabelOf(t) == "NONE")) return false;
        return true;
    }
    // an order the bot would carry out or ask about: not talk, a question about a thing or an answer ("this box is green" may
    // read as small talk and is still a colour lesson; «вот на жёлтую кровать залезь» is a jump)
    bool ReadsOrder(const Heard& h) const {
        static const std::unordered_set<std::string> kNotOrders = {"NONE", "SMALL_TALK", "WHAT_IS_IT", "SEE_THING", "YES", "NO", "MAYBE",
                                                              "DONT_KNOW"};
        for (const Turn& t : h.turns) {
            const std::string& a = t.r.action;
            const bool acts = a == "act" || a == "execute" || a == "queued" || a == "go" || a == "wait" || a == "resolved" || a == "ask";
            if (acts && !kNotOrders.count(LabelOf(t))) return true;
        }
        return !h.held.empty();
    }
    bool Cancelled(const Heard& h) const {
        return !h.turns.empty() && (h.turns[0].r.action == "negated" || LabelOf(h.turns[0]) == "NO");
    }
    // two lines are about the same thing: a word of four letters or more in both, or two words with the same start (five
    // letters, or the whole of the shorter one: «диван» and «дивану», «стол» and «столу»), and not a word every line has
    static bool SharesWord(const std::string& a, const std::string& b) {
        static const std::unordered_set<std::string> kCommon = {
            "иди", "идти", "давай", "пожалуйста", "брат", "братан", "сюда", "туда", "этот", "эту", "этого", "этой", "тот", "ту",
            "того", "вон", "там", "тут", "здесь", "сейчас", "теперь", "быстро", "просто", "come", "please", "there", "here", "this",
            "that", "with", "what", "now", "quickly", "just", "bro", "brother", "the", "aquí", "allí", "ahora", "hermano", "por",
            "favor", "este", "esta", "ese", "esa"};
        auto letters = [](const std::string& w) {
            std::vector<std::string> out;
            for (size_t i = 0; i < w.size();) {
                const unsigned char c = static_cast<unsigned char>(w[i]);
                const size_t n = c < 0x80 ? 1 : (c >> 5) == 0x6 ? 2 : (c >> 4) == 0xE ? 3 : 4;
                out.push_back(w.substr(i, n));
                i += n;
            }
            return out;
        };
        for (const std::string& x : coop::MemoryWords(a)) {
            if (kCommon.count(x)) continue;
            const std::vector<std::string> lx = letters(x);
            if (lx.size() < 4) continue;
            for (const std::string& y : coop::MemoryWords(b)) {
                if (kCommon.count(y)) continue;
                const std::vector<std::string> ly = letters(y);
                if (ly.size() < 4) continue;
                const size_t shorter = std::min(lx.size(), ly.size());
                size_t same = 0;
                while (same < shorter && lx[same] == ly[same]) ++same;
                if (same >= std::min<size_t>(5, shorter)) return true;
            }
        }
        return false;
    }
    // the line read after a miss says the same order at another place, not what the miss meant (2026-10-31: «сядь на диван»
    // missed, then «сядь на кровать» was offered as its meaning): the same start and another end («диван», «кровать»: no
    // letters in common, unlike "on my goal" / "on my go"), or only words added («сядь на стул», «сядь на красный стул»)
    static bool AnotherPlace(const std::string& missed, const std::string& read) {
        const std::vector<std::string> a = coop::MemoryWords(missed), b = coop::MemoryWords(read);
        size_t p = 0;
        while (p < a.size() && p < b.size() && a[p] == b[p]) ++p;
        size_t q = 0;
        while (q < a.size() - p && q < b.size() - p && a[a.size() - 1 - q] == b[b.size() - 1 - q]) ++q;
        if (a.size() - p - q == 0) return true;
        if (p == 0 || q != 0 || b.size() - p - q == 0) return false;
        std::string da, db;
        for (size_t i = p; i < a.size(); ++i) da += (da.empty() ? "" : " ") + a[i];
        for (size_t i = p; i < b.size(); ++i) db += (db.empty() ? "" : " ") + b[i];
        return coop::TrigramJaccard(da, db) < 0.3;
    }
    // a line of one word of one or two letters that is no answer: a sound ("B.", «Э»), not a line
    static bool Mumble(const std::string& heard) {
        const std::vector<std::string> w = coop::MemoryWords(coop::MemoryNorm(heard));
        return w.size() == 1 && coop::DecodeUtf8(w[0]).size() <= 2;
    }
    static bool IsPattern(const coop::MemoryLine& l) { return l.heard.find("{x}") != std::string::npos; }
    static json PatternJson(const PatternOffer& po) { return {{"heard", po.key}, {"lines", po.lines}, {"source", po.source}}; }
    // keeps a pattern the player taught with a meaning (PatternOf): «сесть на {x}» -> "jump on {x}", "crouch"
    void KeepPattern(const PatternOffer& po, const std::string& intent, Memo* memo) {
        if (po.key.empty() || po.lines.empty()) return;
        coop::MemoryLine l;
        l.lang = g_language;
        l.heard = po.key;
        l.lines = po.lines;
        l.intent = intent;
        l.source = po.source;
        std::string e;
        if (!g_memory->KeepLine(l, &e)) return MemoryError(memo, e);
        if (!memo->info.contains("kept_pattern")) memo->info["kept_pattern"] = PatternJson(po);   // the first; all of them below
        memo->info["kept_patterns"].push_back(PatternJson(po));
    }
    // the place an English order line names: the words after its first preposition, to a conjunction or a comma ("Sit on the
    // sofa." -> "the sofa", "jump on it and squat" -> "it", "crouch using the chair" -> "the chair"); empty: none
    static std::string EnglishPlace(const std::string& line) {
        static const std::unordered_set<std::string> kPrep = {"on", "onto", "to", "at", "in", "into", "near", "behind", "under",
                                                              "over", "by", "beside", "toward", "towards", "inside", "using",
                                                              "across", "through", "upon"};
        static const std::unordered_set<std::string> kEnd = {"and", "then", "or", "but", ","};
        std::string t;
        for (char ch : line) {
            if (ch == ',' || ch == ';') t += " , ";
            else if (ch == '.' || ch == '!' || ch == '?') t += ' ';
            else t += static_cast<char>(ch >= 'A' && ch <= 'Z' ? ch - 'A' + 'a' : ch);
        }
        const std::vector<std::string> w = coop::MemoryWords(t);
        for (size_t i = 0; i + 1 < w.size(); ++i) {
            if (!kPrep.count(w[i])) continue;
            size_t e = i + 1;
            while (e < w.size() && !kEnd.count(w[e])) ++e;
            if (e == i + 1 || e - i - 1 > 6) return {};
            std::string place;
            for (size_t k = i + 1; k < e; ++k) place += (place.empty() ? "" : " ") + w[k];
            return place;
        }
        return {};
    }
    // the meaning's English order lines with the place they name as {x} ("jump on the chair", "crouch" -> "jump on {x}",
    // "crouch"): the first line's place (EnglishPlace), wherever a line names it as a whole word; false: none
    static bool EnglishPattern(const Heard& h, std::vector<std::string>* out) {
        std::vector<std::string> lines;
        for (const Turn& t : h.turns) lines.push_back(t.line);
        for (const std::string& l : h.held) lines.push_back(l);
        std::string place;
        for (const std::string& l : lines)
            if (place.empty()) place = EnglishPlace(l);
        if (place.empty()) return false;
        out->clear();
        bool any = false;
        for (const std::string& l : lines) {
            std::string low;
            for (char ch : l) low += static_cast<char>(ch >= 'A' && ch <= 'Z' ? ch - 'A' + 'a' : ch);
            std::string o;
            size_t at = 0;
            for (size_t f; (f = low.find(place, at)) != std::string::npos; at = f + place.size()) {
                const bool left = f == 0 || !std::isalnum(static_cast<unsigned char>(low[f - 1]));
                const size_t end = f + place.size();
                const bool right = end == low.size() || !std::isalnum(static_cast<unsigned char>(low[end]));
                o += l.substr(at, f - at) + (left && right ? std::string("{x}") : l.substr(f, place.size()));
                any = any || (left && right);
            }
            out->push_back(o + l.substr(at));
        }
        return any;
    }
    PatternOffer PatternOf(const std::string& said_words, const std::string& meant_text, const Heard& h) const {
        PatternOffer po;
        const coop::TaughtPattern t = coop::MakePattern(said_words, meant_text);
        if (!t.slot) return po;
        po.key = t.key;
        if (EnglishPattern(h, &po.lines)) {
            po.source = "pattern";
        } else {
            po.source = "pattern_said";
            po.lines = {t.meaning};
        }
        return po;
    }
    // the pattern a heard line is said as (*slot: its place as said); nullptr: none. The one with the most words of its own,
    // then the last kept
    const coop::MemoryLine* PatternFor(const std::string& heard, std::string* slot) const {
        const coop::MemoryLine* best = nullptr;
        size_t best_fixed = 0;
        for (const coop::MemoryLine& l : g_memory->Lines()) {
            if (l.lang != g_language || !IsPattern(l) || l.lines.empty()) continue;
            std::string x;
            size_t fixed = 0;
            if (!coop::MatchPattern(l.heard, heard, &x, &fixed)) continue;
            if (!best || fixed > best_fixed || (fixed == best_fixed && l.at_ms >= best->at_ms)) best = &l, best_fixed = fixed, *slot = x;
        }
        return best;
    }
    // the place a line names in English: the line itself in English, else the decoder's English of it in the talk so far («Сядь
    // на диван.» -> "Sit on the sofa." -> "the sofa"; «Сядь на него.» -> "it", or the thing the talk named); empty: none
    std::string HeardPlace(const std::string& line, bool spoken) {
        const std::string text = spoken ? coop::SpeechTextForClassifier(line) : line;
        if (g_language == "en") return EnglishPlace(text);
        if (!chain_on || !g_chain) return {};
        const auto now = Clock::now();
        std::vector<std::string> before;
        for (const Said& x : said)
            if (Ms(now - x.at) <= 1000 * g_chain->memory_seconds) before.push_back(x.text);
        const bool bot = !bot_said.text.empty() && Ms(now - bot_said.at) <= 1000 * g_chain->memory_seconds;
        std::vector<std::string> pieces;
        std::string note;
        if (!g_chain->Rewrite(before, bot ? bot_said.text : std::string(), planner.World().scene, text, &pieces, &note)) return {};
        for (const std::string& piece : pieces)
            if (const std::string place = EnglishPlace(piece); !place.empty()) return place;
        return {};
    }
    // a line's parts: cut at «и», "and", «y», «потом», "then" and at commas and stops, as said («Встань с дивана и сядь на
    // стул.» -> «Встань с дивана», «сядь на стул»)
    static std::vector<std::string> LineParts(const std::string& text) {
        static const std::unordered_set<std::string> kJoin = {"и", "потом", "затем", "and", "then", "y", "luego"};
        const std::vector<coop::SpanWord> sw = coop::SpanWords(text);
        std::vector<std::string> parts;
        size_t from = 0;
        for (size_t i = 0; i < sw.size(); ++i) {
            const std::string gap = i > 0 ? text.substr(sw[i - 1].end, sw[i].begin - sw[i - 1].end) : std::string();
            const bool comma = gap.find_first_of(",.;!?") != std::string::npos;
            if (comma && i > from) parts.push_back(text.substr(sw[from].begin, sw[i - 1].end - sw[from].begin)), from = i;
            if (kJoin.count(sw[i].norm)) {
                if (i > from) parts.push_back(text.substr(sw[from].begin, sw[i - 1].end - sw[from].begin));
                from = i + 1;
            }
        }
        if (from < sw.size()) parts.push_back(text.substr(sw[from].begin, sw.back().end - sw[from].begin));
        return parts;
    }
    // a taught meaning read as orders, not carried out (Means): the line as the recognizer would write it, read alone; when it
    // gives fewer orders than its parts («Запрыгнуть на диван и присесть.» was one, "crouch using the sofa"), each part alone
    // («Запрыгнуть на диван.», «Присесть.»), if that reads more. *read: every line an order
    bool ReadMeaning(const std::string& text, bool spoken, Heard* h, Memo* memo, std::string* err, bool* read) {
        auto quiet = [](const Heard&, const Turn&) {};   // read, not said: the bot's would-be replies are no lines of its
        auto as_orders = [&](const Heard& x) {
            bool ok = Understood(x);
            for (const Turn& t : x.turns) ok = ok && (t.r.action == "act" || t.r.action == "resolved");
            return ok;
        };
        const Alone alone(taught_alone);
        if (!HearNamed(AsLine(text), spoken, h, memo, err, quiet)) return false;
        planner.DropQuestion();   // only read: no question of it stays open
        *read = as_orders(*h);
        const std::vector<std::string> parts = LineParts(text);
        if (parts.size() < 2 || h->turns.size() + h->held.size() >= parts.size()) return true;
        Heard all;
        bool all_read = true;
        for (const std::string& part : parts) {
            Heard one;
            if (!HearNamed(AsLine(part), spoken, &one, memo, err, quiet)) return false;
            planner.DropQuestion();
            all_read = all_read && as_orders(one);
            for (Turn& t : one.turns) all.turns.push_back(std::move(t));
            for (std::string& l : one.held) all.held.push_back(std::move(l));
        }
        if (all_read && all.turns.size() + all.held.size() > h->turns.size() + h->held.size()) {
            memo->info["read_in_parts"] = parts;
            *h = std::move(all);
            *read = true;
        }
        return true;
    }
    // A line the bot read after lines just before it it could not read about the same thing (the owner, 2026-10-30: «Иди
    // садись на диван» twice "say again", then «Иди на диван»): the bot carries out the order and asks "Shall I remember that
    // "иди садись на диван" means "иди на диван"?"; "yes" keeps those lines as this one's orders (Listen). Never kept unasked:
    // the player may have said something else entirely
    void OfferMeaning(const std::string& norm, const std::string& heard, const Heard& h, Clock::time_point now, Memo* memo) {
        if (memo->answered || memo->remembered || planner.Mem().has_question || !Understood(h)) return;
        for (const Turn& t : h.turns)
            if (!(t.r.action == "act" || t.r.action == "resolved")) return;
        std::vector<std::string> keys;
        Clock::time_point after = now;
        for (auto it = recent.rbegin(); it != recent.rend(); ++it) {
            if (!it->failed || Ms(after - it->at) > kMeaningMs) break;   // only the run of misses right before it
            after = it->at;
            // a long line heard wrong is never heard the same way again: no use keeping it, and the question quoting it ran
            // 9 s (2026-11-01, the owner's log: «запомню что ляж ях это пляж на пол»)
            if (coop::MemoryWords(it->norm).size() > kOfferWords) continue;
            if (it->norm != norm && SharesWord(it->norm, norm) && !AnotherPlace(it->norm, norm) &&
                std::find(keys.begin(), keys.end(), it->norm) == keys.end())
                keys.push_back(it->norm);
        }
        if (keys.empty()) return;
        std::reverse(keys.begin(), keys.end());   // the first way it was said first
        offer = Offer();
        offer.open = true;
        offer.meaning = true;
        offer.keys = keys;
        offer.at = now;
        for (const Turn& t : h.turns) offer.lines.push_back(t.line);
        for (const std::string& line : h.held) offer.lines.push_back(line);
        offer.intent = LabelOf(h.turns[0]);
        // «сядь на него» / «запрыгни на него»: any thing, said in each of the ways it was heard
        for (const std::string& key : keys)
            if (PatternOffer po = PatternOf(key, heard, h); !po.key.empty()) offer.patterns.push_back(std::move(po));
        memo->info["did"] = "offered_meaning";
        memo->info["offered_meaning"] = {{"heard", keys}, {"meant", norm}, {"lines", offer.lines}, {"intent", offer.intent}};
        if (!offer.patterns.empty()) memo->info["offered_meaning"]["pattern"] = PatternJson(offer.patterns[0]);
        memo->ask = "Shall I remember that \"" + keys[0] + "\" means \"" + norm + "\"?";
        memo->terms["said"][keys[0]] = {{"text", keys[0]}};
        memo->terms["meant"][norm] = {{"text", norm}};
    }
    void RememberLine(const std::string& norm, const Heard& h, const std::string& kept) {
        Recent r;
        r.norm = norm;
        r.at = Clock::now();
        r.failed = !h.turns.empty() &&
                   std::all_of(h.turns.begin(), h.turns.end(), [](const Turn& t) { return t.r.action == "say_again"; });
        r.intent = h.turns.empty() || r.failed ? -1 : h.turns[0].r.decision.intent;
        r.kept = kept;
        recent.push_back(std::move(r));
        while (recent.size() > 8) recent.pop_front();
    }
    static void MemoryError(Memo* memo, const std::string& e) {
        std::fprintf(stderr, "memory: %s\n", e.c_str());
        memo->info["error"] = e;
    }

    // keeps what the heard lines `keys` meant: the order lines `h` gave (and the ones held for the bot's question)
    void KeepMeaning(const std::vector<std::string>& keys, const Heard& h, Memo* memo, const std::string& meant_text) {
        coop::MemoryLine l;
        l.lang = g_language;
        for (const Turn& t : h.turns) l.lines.push_back(t.line);
        for (const std::string& s : h.held) l.lines.push_back(s);
        l.intent = h.turns.empty() ? std::string() : LabelOf(h.turns[0]);
        l.source = "voice";
        json kept = json::array();
        for (const std::string& key : keys) {
            l.heard = key;
            std::string e;
            if (!g_memory->KeepLine(l, &e)) return MemoryError(memo, e);
            kept.push_back(key);
        }
        memo->remembered = true;
        memo->info["did"] = "kept_line";
        memo->info["kept_line"] = {{"heard", kept}, {"lines", l.lines}, {"intent", l.intent}};
        // a place both name: for any thing
        if (!meant_text.empty())
            for (const std::string& key : keys) KeepPattern(PatternOf(key, meant_text, h), l.intent, memo);
    }

    // the line with the names the player taught written as the thing's kind ("иди к верстаку" -> "иди к table"), and the
    // things its names and colours name, in *named; a room's name is its door's ("иди в гараж" -> "иди в door"), and the
    // door goes in *rooms too
    std::string WithNames(const std::string& line, std::vector<std::string>* named, std::vector<std::string>* rooms) const {
        const coop::WorldState& w = planner.World();
        const std::vector<coop::SpanWord> spans = coop::SpanWords(line);
        std::vector<std::string> norms;
        for (const coop::SpanWord& x : spans) norms.push_back(x.norm);
        auto add = [&](const std::string& id) {
            if (std::find(named->begin(), named->end(), id) == named->end()) named->push_back(id);
        };
        struct Cut {
            size_t begin, end;
            std::string with;
        };
        std::vector<Cut> cuts;
        std::vector<bool> used(spans.size(), false);
        std::vector<const coop::MemoryName*> names;   // longer names first: "red workbench" before "workbench"
        for (const coop::MemoryName& n : g_memory->Names())
            if (n.map == w.map && n.lang == g_language) names.push_back(&n);
        std::stable_sort(names.begin(), names.end(), [](const coop::MemoryName* a, const coop::MemoryName* b) {
            return coop::MemoryWords(a->name).size() > coop::MemoryWords(b->name).size();
        });
        for (const coop::MemoryName* n : names) {
            const coop::WorldEntity* e = EntityOfKey(n->entity);
            if (!e || e->object.empty()) continue;   // not in this world, or of no kind the words can name
            std::string kind = e->object;            // world.py object_word: "garden_bed" is "garden bed"
            std::replace(kind.begin(), kind.end(), '_', ' ');
            const std::vector<std::string> nw = coop::MemoryWords(n->name);
            size_t from = 0, b = 0, en = 0;
            while (coop::FindWords(norms, nw, from, &b, &en)) {
                bool free = true;
                for (size_t i = b; i < en; ++i) free = free && !used[i];
                if (free) {
                    for (size_t i = b; i < en; ++i) used[i] = true;
                    cuts.push_back({spans[b].begin, spans[en - 1].end, kind});
                    add(e->id);
                    if (IsRoomKey(n->entity) && std::find(rooms->begin(), rooms->end(), e->id) == rooms->end()) rooms->push_back(e->id);
                }
                from = en;
            }
        }
        for (const std::string& c : coop::ColoursIn(norms))
            for (const coop::MemoryColour& mc : g_memory->Colours())
                if (mc.map == w.map && mc.colour == c)
                    if (const coop::WorldEntity* e = EntityByKey(mc.entity)) add(e->id);
        std::sort(cuts.begin(), cuts.end(), [](const Cut& a, const Cut& b) { return a.begin > b.begin; });
        std::string out = line;
        for (const Cut& c : cuts) out.replace(c.begin, c.end - c.begin, c.with);
        return out;
    }

    // A kept line's English order lines with the things the player named in the heard line (2026-10-31, the owner named the rock
    // «диван», then «сядь на диван», a line taught while «диван» was the sofa, went to the sofa; the owner: the name wins over
    // the kind word). Where the lines name the kind the name's own words mean ("sofa", "couch": «диван»), they name the named
    // thing's kind instead ("rock"); the planner takes that thing (*named, as WithNames, with *rooms)
    std::vector<std::string> LinesWithNames(std::vector<std::string> lines, const std::string& heard, std::vector<std::string>* named,
                                            std::vector<std::string>* rooms) const {
        WithNames(heard, named, rooms);
        const coop::LocationMatcher& places = brain.Places();
        if (named->empty() || !places.Ready()) return lines;
        std::vector<std::string> hw;
        for (const coop::SpanWord& x : coop::SpanWords(heard)) hw.push_back(x.norm);
        for (const std::string& id : *named) {
            const coop::WorldEntity* e = EntityById(id);
            const coop::MemoryName* n = e ? NameOf(*e) : nullptr;
            size_t b = 0, en = 0;
            if (!n || e->object.empty() || !coop::FindWords(hw, coop::MemoryWords(n->name), 0, &b, &en)) continue;
            const std::string said_kind = KindOf(coop::MemoryWords(n->name));
            if (said_kind.empty() || said_kind == e->object) continue;
            std::string kind = e->object;
            std::replace(kind.begin(), kind.end(), '_', ' ');
            for (std::string& l : lines) {
                // the words of the line that name that kind (1 to 3 of them), the last first: the bytes stay where they are
                const std::vector<coop::SpanWord> ws = coop::SpanWords(l);
                std::vector<std::pair<size_t, size_t>> cuts;
                for (size_t i = 0; i < ws.size();) {
                    size_t took = 0;
                    for (size_t len = std::min<size_t>(3, ws.size() - i); len >= 1 && !took; --len) {
                        std::string joined;
                        for (size_t k = i; k < i + len; ++k) joined += (joined.empty() ? "" : " ") + ws[k].norm;
                        int idx = -1;
                        const char* what = places.PhraseKind(joined, &idx);
                        if (what && std::string(what) == "object" && idx >= 0 && places.ObjectId(idx) == said_kind) took = len;
                    }
                    if (took) cuts.push_back({ws[i].begin, ws[i + took - 1].end}), i += took;
                    else ++i;
                }
                for (auto c = cuts.rbegin(); c != cuts.rend(); ++c) l.replace(c->first, c->second - c->first, kind);
            }
        }
        return lines;
    }

    // Hear with the names and colours the player taught (WithNames)
    template <class Each>
    bool HearNamed(const std::string& line, bool spoken, Heard* h, Memo* memo, std::string* err, Each&& each) {
        std::vector<std::string> named, rooms;
        const std::string read_as = g_memory && g_memory->IsOpen() ? WithNames(line, &named, &rooms) : line;
        if (named.empty()) return Hear(line, spoken ? coop::SpeechTextForClassifier(line) : line, h, err, each);
        memo->info["named"] = named;
        if (!rooms.empty()) memo->info["rooms"] = rooms;   // RoomOrder
        if (read_as != line) memo->info["read_as"] = read_as;
        planner.SetNamed(named);
        const bool ok = Hear(read_as, spoken ? coop::SpeechTextForClassifier(read_as) : read_as, h, err, each);
        planner.SetNamed({});
        return ok;
    }

    // an order through a room's door: its "room" says whether the bot goes in or out through the door ("in", "out"), by the
    // order's English. A line that named a room (memo "rooms", WithNames): "exit through the door" is out, "go in through the
    // door" and "wait at the door" in; "go outside" with no place gets the room's door as its "door". A door with an inside
    // (HasInside) the order says in or out of: «зайди внутрь» with the crosshair on it is "go inside" at the door. The game
    // takes the door's inside or outside
    void RoomOrder(const Memo& memo, const Turn& t, json* turn) const {
        const std::vector<std::string> rooms =
            memo.info.contains("rooms") ? memo.info["rooms"].get<std::vector<std::string>>() : std::vector<std::string>();
        // «выйди из гаража» read as "get out of the door": GET_OUT is out of a car, and out of a room the line named is out through
        // its door, however sure the classifier was (2026-10-30, the game's run: say_again GET_OUT 0.62 with the decoder on the GPU)
        if (!rooms.empty() && !turn->contains("state") && turn->value("intent", json(nullptr)) == json("GET_OUT")) {
            const std::string en = "Moving.";
            std::string local;
            (*turn)["intent"] = "MOVE_TO";
            (*turn)["action"] = "act";
            (*turn)["say"] = g_replies && Localize(en, &local) ? local : en;
            (*turn)["say_en"] = en;
            (*turn)["order"] = {{"intent", "MOVE_TO"}, {"entity", nullptr}, {"candidates", json::array()}, {"direction", nullptr},
                                {"zone", "outside"}, {"pointer", nullptr}, {"other", false}, {"via", "outside"}, {"near", false},
                                {"object", nullptr}, {"door", rooms[0]}, {"room", "out"}};
            (*turn)["room_exit"] = true;
            return;
        }
        if (!turn->contains("order") || !(*turn)["order"].is_object()) return;
        json& order = (*turn)["order"];
        const std::string entity = order.value("entity", json(nullptr)).is_string() ? order["entity"].get<std::string>() : std::string();
        const std::string via = order.value("via", json(nullptr)).is_string() ? order["via"].get<std::string>() : std::string();
        static const std::unordered_set<std::string> kOut = {"exit", "out", "outside", "outdoors", "leave", "outta"};
        static const std::unordered_set<std::string> kIn = {"in", "inside", "into", "indoors", "enter"};
        // "in" of a time is not into a room: "in 5 seconds go to the main door", "go to the door in a moment" (2026-11-04, the timer
        // E2E: the bot went in through the main door and its switch)
        static const std::unordered_set<std::string> kTimeUnit = {"second", "seconds", "sec", "secs", "minute", "minutes", "min", "mins",
                                                                  "moment", "bit", "jiffy", "while", "hour", "hours"};
        static const std::unordered_set<std::string> kTimeFill = {"a", "an", "the", "few", "couple", "of", "half", "more", "next", "another",
                                                                  "some", "one", "two", "three", "four", "five", "six", "seven", "eight",
                                                                  "nine", "ten", "fifteen", "twenty", "thirty", "forty", "fifty", "sixty"};
        auto of_time = [&](const std::vector<std::string>& ws, size_t i) {   // ws[i] == "in": "in 5 seconds", "in a few seconds"
            for (size_t j = i + 1; j < ws.size() && j <= i + 4; ++j) {
                if (kTimeUnit.count(ws[j])) return true;
                const bool number = !ws[j].empty() && std::all_of(ws[j].begin(), ws[j].end(), [](unsigned char c) { return std::isdigit(c) != 0; });
                if (!number && !kTimeFill.count(ws[j])) return false;
            }
            return false;
        };
        bool out = false, in = false;
        const std::vector<std::string> line_words = coop::MemoryWords(coop::MemoryNorm(t.line));
        for (size_t i = 0; i < line_words.size(); ++i) {
            out = out || kOut.count(line_words[i]) > 0;
            in = in || (kIn.count(line_words[i]) > 0 && !(line_words[i] == "in" && of_time(line_words, i)));
        }
        if (!entity.empty() && std::find(rooms.begin(), rooms.end(), entity) != rooms.end()) {
            order["room"] = out ? "out" : "in";
        } else if (entity.empty() && !rooms.empty() && (via == "inside" || via == "outside")) {
            order["door"] = rooms[0];
            order["room"] = via == "outside" ? "out" : "in";
        } else if (const coop::WorldEntity* e = entity.empty() || !(in || out) ? nullptr : EntityById(entity)) {
            if (HasInside(*e)) order["room"] = out ? "out" : "in";
        }
    }

    // A line of the player through the long-term memory and then Hear (see above). memo->answered: the memory answered
    // the line itself (its words in memo->say), and the turns `each` saw are not the reply
    template <class Each>
    bool Listen(const std::string& heard, bool spoken, Heard* h, Memo* memo, std::string* err, Each&& each) {
        *memo = Memo();
        // the bot called by its name (2026-10-31, the owner: it answers to its name): «Рекс!» is answered, «Рекс, иди сюда» and
        // «иди сюда, Рекс» are read without it. Not a line about the names themselves («тебя зовут Рекс»)
        {
            const std::string name = BotName();
            std::string rest;
            const coop::TeachKind tk = name.empty() ? coop::TeachKind::None : coop::ReadTeach(heard, g_language).kind;
            if (!name.empty() && tk != coop::TeachKind::BotName && tk != coop::TeachKind::PlayerName && coop::CalledBy(heard, name, &rest)) {
                if (rest.empty()) {
                    memo->answered = true;
                    memo->say = Pick(kCalled);
                    memo->info["did"] = "called";
                    memo->info["called"] = name;
                    return true;
                }
                const bool ok = Listen(rest, spoken, h, memo, err, each);
                memo->info["called"] = name;
                return ok;
            }
        }
        if (!last_kept.did.empty()) ++last_kept.lines_since;
        // «не расслышал», «ещё раз?»: the bot's last line again (2026-11-01, the owner: «Я сказал: ...»)
        if (!last_line.empty() && Ms(Clock::now() - last_line_at) <= 60000 && RepeatAskedInOwnWords(heard)) {
            memo->answered = true;
            memo->say = RepeatLine(last_line);
            memo->info["did"] = "repeated";
            memo->info["repeated"] = last_line;
            repeat_said = memo->say;
            return true;
        }
        // the answer to "what is that?" is the decoder's context for the line right after it only
        if (what_said_lines >= 0 && ++what_said_lines > 1) {
            bot_said = Said();
            what_said_lines = -1;
        }
        if (!g_memory || !g_memory->IsOpen()) return Hear(heard, spoken ? coop::SpeechTextForClassifier(heard) : heard, h, err, each);
        const auto now = Clock::now();
        while (!recent.empty() && Ms(now - recent.front().at) > kRecentMs) recent.pop_front();
        const std::string norm = coop::MemoryNorm(heard);
        const std::string map = planner.World().map;
        // a line while the bot's question is open is its answer ("not that" is "not that one"), except "I meant <another
        // order>": the bot asked "Which crate?" about a line it read wrong
        const bool open = planner.Mem().has_question;
        const int asked = open ? planner.Mem().question.intent : -1;
        coop::TeachLine tl = coop::ReadTeach(heard, g_language);
        if (open && tl.kind != coop::TeachKind::Meant) tl = coop::TeachLine();
        memo->info["teach"] = coop::TeachKindName(tl.kind);
        auto answer = [&](const std::string& say, const char* did) {
            memo->answered = true;
            memo->say = say;
            memo->info["did"] = did;
            return true;
        };

        // the thing the bot just named is open to a correction on the next line alone: any line closes it, and the answers
        // that name a thing open it again below
        const std::string what_was = what_key;
        what_key.clear();

        // «не надо было запоминать», «забудь это» a moment after a lesson (2026-11-01, the owner): the last thing kept is
        // forgotten. An open "Shall I remember ...?" takes the line as its answer instead ("no")
        // («не надо было запоминать» with nothing kept since: "I don't remember that.")
        if (!offer.open && !open && last_kept.did.empty() && UndoInOwnWords(heard, false)) return answer(kNotKept, "nothing_to_undo");
        if (!offer.open && !open && !last_kept.did.empty() &&
            UndoInOwnWords(heard, last_kept.lines_since <= 1 && Ms(now - last_kept.at) <= 60000)) {
            const Kept k = last_kept;
            last_kept = Kept();
            std::string problem;
            bool any = false;
            auto key_of = [&](const char* field) {
                const json& o = k.info.contains(k.did) ? k.info[k.did] : json();
                return o.is_object() && o.contains(field) && o[field].is_string() ? o[field].get<std::string>() : std::string();
            };
            if (k.did == "kept_line" || k.did == "kept_pattern" || k.did == "kept_patterns") {
                // the heard lines (and the patterns kept with a meaning)
                std::vector<std::string> heards;
                for (const char* field : {"kept_line", "kept_pattern", "kept_patterns"}) {
                    if (!k.info.contains(field)) continue;
                    const json& o = k.info[field];
                    auto take = [&](const json& x) {
                        if (x.is_string()) heards.push_back(x.get<std::string>());
                        else if (x.is_object() && x.contains("heard")) {
                            if (x["heard"].is_string()) heards.push_back(x["heard"].get<std::string>());
                            else if (x["heard"].is_array())
                                for (const json& hh : x["heard"]) if (hh.is_string()) heards.push_back(hh.get<std::string>());
                        }
                    };
                    if (o.is_array()) for (const json& x : o) take(x);
                    else take(o);
                }
                for (const std::string& hh : heards) {
                    std::string e;
                    if (g_memory->ForgetLine(g_language, hh, &e)) any = true;
                    else if (!e.empty()) MemoryError(memo, e);
                }
            } else if (k.did == "kept_name") {
                if (!g_memory->ForgetName(k.map, key_of("key"), g_language, &any, &problem)) MemoryError(memo, problem);
            } else if (k.did == "kept_colour") {
                if (!g_memory->ForgetColour(k.map, key_of("key"), &any, &problem)) MemoryError(memo, problem);
            } else if (k.did == "kept_bot_name" || k.did == "kept_player_name") {
                const bool bot = k.did == "kept_bot_name";
                if (!g_memory->ForgetPerson(bot ? "bot" : "player", &any, &problem)) MemoryError(memo, problem);
                if (bot) memo->info["bot_name"] = nullptr;
            } else if (k.did == "kept_saying") {
                if (!g_memory->ForgetSaying(g_language, key_of("word"), &any, &problem)) MemoryError(memo, problem);
            } else {
                // a setting, a phrase of the bot's: no way back to the one before it
                memo->info["undo"] = k.did;
                return answer(kCannotUndo, "cannot_undo");
            }
            memo->info["undone"] = k.did;
            if (k.info.contains(k.did)) memo->info["undone_what"] = k.info[k.did];
            return answer(any ? kForgotten : kNotKept, any ? "forgot_last" : "not_kept");
        }

        // the answer to "Shall I remember it as X?": "yes" keeps the name, "no" does not, anything else drops the question
        if (offer.open) {
            const Offer o = offer;
            offer.open = false;
            if (o.pronounce && Ms(now - o.at) <= kOfferMs && !open) {
                // «нет, на второй слог», «на о»: the stress again, of the same word (before "no": it starts with one)
                std::vector<std::string> w = coop::MemoryWords(norm);
                while (!w.empty() && (w[0] == "нет" || w[0] == "не" || w[0] == "а")) w.erase(w.begin());
                std::string again = "в слове " + o.word + " ударение";
                for (const std::string& x : w) again += " " + x;
                const coop::TeachLine t = !w.empty() && w[0] == "на" ? coop::ReadTeach(again, g_language) : coop::TeachLine();
                if (t.kind == coop::TeachKind::Pronounce && !t.forget) return OfferSaying(t, now, memo);
            }
            const int yn = Ms(now - o.at) <= kOfferMs && !open ? coop::YesNo(heard) : 0;
            // a sound the recognizer made of the answer (2026-10-30, the owner's «да» heard as "B.", read as an order): the
            // question stays and is asked again
            if (yn == 0 && Ms(now - o.at) <= kOfferMs && !open && Mumble(heard)) {
                offer = o;
                offer.open = true;
                offer.at = now;
                return answer(kYesOrNo, "asked_yes_no");
            }
            if (yn > 0 && o.meaning) {
                coop::MemoryLine l;
                l.lang = g_language;
                l.lines = o.lines;
                l.intent = o.intent;
                l.source = "voice";
                std::string problem;
                for (const std::string& key : o.keys) {
                    l.heard = key;
                    if (!g_memory->KeepLine(l, &problem)) MemoryError(memo, problem);
                }
                memo->info["kept_line"] = {{"heard", o.keys}, {"lines", o.lines}, {"intent", o.intent}};
                for (const PatternOffer& po : o.patterns) KeepPattern(po, o.intent, memo);
                return answer(kRemembered, "kept_line");
            }
            if (yn < 0 && o.meaning) return answer(kNotRemembered, "not_kept_line");
            if (yn > 0 && o.pronounce) {
                std::string problem;
                if (!g_memory->KeepSaying({g_language, o.word, o.say, 0}, &problem)) MemoryError(memo, problem);
                memo->info["kept_saying"] = {{"word", o.word}, {"say", o.say}};
                return answer(kRemembered, "kept_saying");
            }
            if (yn < 0 && o.pronounce) return answer(kNotRemembered, "not_kept_saying");
            if (yn > 0 && o.phrase) {
                std::string problem;
                if (!g_memory->KeepPhrase({g_language, o.word, o.say, 0, o.phrase_word}, &problem)) MemoryError(memo, problem);
                memo->info["kept_phrase"] = {{"from", o.word}, {"to", o.say}, {"word", o.phrase_word}};
                return answer(kRemembered, "kept_phrase");
            }
            if (yn < 0 && o.phrase) return answer(kNotRemembered, "not_kept_phrase");
            if (yn > 0 && o.setting) {
                std::string problem;
                if (!g_memory->KeepSetting({o.word, o.value, 0}, &problem)) MemoryError(memo, problem);
                memo->info["kept_setting"] = {{"name", o.word}, {"value", o.value}};
                memo->info["behaviour"] = SettingsJson();
                return answer(kRemembered, "kept_setting");
            }
            if (yn < 0 && o.setting) return answer(kNotRemembered, "not_kept_setting");
            if (yn > 0) {
                std::string problem;
                if (!g_memory->KeepName({map, o.key, g_language, o.name, 0}, &problem)) MemoryError(memo, problem);
                const coop::WorldEntity* e = EntityOfKey(o.key);
                memo->info["kept_name"] = {{"entity", e ? e->id : o.key}, {"key", o.key}, {"name", o.name}};
                if (IsRoomKey(o.key)) memo->info["kept_name"]["room"] = true;
                return answer(kRemembered, "kept_name");
            }
            if (yn < 0) return answer(kNotRemembered, "not_kept_name");
        }

        // «как тебя зовут?», «как меня зовут?» (2026-10-31): the bot's name (the player's, else the game's) and the player's.
        // A bot with no name at all leaves "who are you?" to the small talk
        if (!open) {
            const int q = coop::NameQuestion(heard);
            const std::string name = q == 1 ? BotName() : q == 2 ? PlayerName() : std::string();
            if (q == 1 && !name.empty()) {
                NameTerm(memo, name);
                memo->info["bot_name_said"] = name;
                return answer(kMyNameA + name + ".", "said_bot_name");
            }
            if (q == 2) {
                if (name.empty()) return answer(kNoPlayerName, "no_player_name");
                NameTerm(memo, name);
                g_name_since = 0;
                return answer(kYourNameA + name + ".", "said_player_name");
            }
        }

        // "what colour is it?" (the owner, 2026-10-30: «какого цвета этот стул?»): the colour the player taught, else the
        // game's; a thing named by a taught name first, else the one under the crosshair
        std::vector<std::string> asked_words;
        if (!open && coop::ColourQuestion(heard, &asked_words)) {
            const coop::WorldEntity* e = NamedIn(asked_words);
            if (!e) e = PointedEntity();
            if (!e) return answer(kPointAtIt, "no_thing");
            what_key = KeyOf(*e);
            what_at = now;
            const std::string colour = ColourOfThing(*e);
            memo->info["colour_of"] = {{"entity", e->id}, {"colour", colour}};
            if (colour.empty()) return answer(kNoColour, "no_colour");
            return answer("That's " + ThingWordsFor(e->object, colour, memo) + ".", "colour_of");
        }

        // what the thing the bot just named is (the owner, 2026-10-30: «Что это?» "the white table", «Нет, это жёлтый
        // стол» was read as "no"): «нет, это красный фонарь», «это жёлтый стол», «это не стол, а верстак»; a bare «нет»
        // asks "Then what is it?" and the next line says it (the words alone too: «фонарь», unless it is an order)
        {
            const bool answering = asked_what && Ms(now - asked_what_at) <= kMeaningMs && !open;
            asked_what = false;
            const bool after = !open && !what_was.empty() && Ms(now - what_at) <= kWhatMs;
            const coop::WorldEntity* e = answering || after ? EntityByKey(what_was) : nullptr;
            // the crosshair on another thing now: the line is about that one («это гараж» at the door), not the answer
            if (const coop::WorldEntity* now_at = e ? PointedEntity() : nullptr)
                if (KeyOf(*now_at) != what_was) e = nullptr;
            if (e && !answering && coop::BareDenial(heard)) {
                what_key = what_was;   // the next line says what it is
                asked_what = true;
                asked_what_at = now;
                what_at = now;
                return answer(kAskWhat, "asked_what");
            }
            coop::ThingWords tw = e ? coop::ReadThingWords(heard, false) : coop::ThingWords();
            bool bare = false;
            if (e && !tw.ok && answering) {
                tw = coop::ReadThingWords(heard, true);
                bare = tw.ok;
            }
            if (tw.ok) {
                if (bare) {   // «стой» is an order, not what the thing is
                    if (!HearNamed(heard, spoken, h, memo, err, each)) return false;
                    if (!NoOrder(*h)) {
                        what_key.clear();
                        RememberLine(norm, *h, {});
                        return true;
                    }
                }
                memo->info["teach"] = "correction";
                return CorrectThing(*e, tw.words, now, memo);
            }
        }

        // the answer to "What did you mean?"
        const bool meaning = asked_meaning && Ms(now - asked_at) <= kMeaningMs && tl.kind == coop::TeachKind::None && !open;
        const std::vector<std::string> meaning_keys = asked_keys;
        asked_meaning = false;
        if (meaning) {
            if (!HearNamed(heard, spoken, h, memo, err, each)) return false;
            if (!Understood(*h)) memo->info["did"] = "meaning_not_read";
            else if (!Misread(asked_failed, asked_intent, *h)) memo->info["did"] = "same_order";   // "not that" -- "the window"
            else KeepMeaning(meaning_keys, *h, memo, heard);
            return true;
        }

        switch (tl.kind) {
            case coop::TeachKind::Meant: {
                if (recent.empty()) break;   // nothing said before it: a line like any other
                const std::vector<std::string> keys = MeaningKeys();
                const std::string old = recent.back().kept;   // the kept line that read it wrong goes
                const bool failed = recent.back().failed;
                const int intent = recent.back().intent;
                if (!HearNamed(tl.rest, spoken, h, memo, err, each)) return false;
                if (!Understood(*h)) {
                    memo->info["did"] = "meaning_not_read";
                    return true;
                }
                // "I meant the red table": the answer to the question, settled by the planner (or the order asked about)
                if (open && (h->turns[0].r.decision.intent == asked || h->turns[0].r.action == "resolved" || h->turns[0].r.action == "ask")) {
                    memo->info["did"] = "answered_question";
                    return true;
                }
                if (!Misread(failed && !open, open ? asked : intent, *h)) {   // "I meant the window": the same order, another place
                    memo->info["did"] = "same_order";
                    return true;
                }
                std::string e;
                if (!old.empty() && std::find(keys.begin(), keys.end(), old) == keys.end() && !g_memory->ForgetLine(g_language, old, &e) && !e.empty())
                    MemoryError(memo, e);
                KeepMeaning(keys, *h, memo, tl.rest);
                recent.back().kept.clear();
                return true;
            }
            case coop::TeachKind::NotThat: {
                if (recent.empty()) break;
                std::string e;
                if (!recent.back().kept.empty()) {
                    if (g_memory->ForgetLine(g_language, recent.back().kept, &e)) memo->info["forgot_line"] = recent.back().kept;
                    else if (!e.empty()) MemoryError(memo, e);
                    recent.back().kept.clear();
                }
                asked_keys = MeaningKeys();
                asked_failed = recent.back().failed;
                asked_intent = recent.back().intent;
                asked_meaning = true;
                asked_at = now;
                return answer(kAskMeaning, "asked_meaning");
            }
            case coop::TeachKind::Name:
            case coop::TeachKind::Colour: {
                const std::string thing = PointedThing();
                const coop::WorldEntity* e = thing.empty() ? nullptr : EntityById(thing);
                if (e && e->object.empty()) e = nullptr;   // a point on the floor or a wall ("gaze_17"): no thing to name
                if (!e) {
                    if (tl.plain || tl.kind == coop::TeachKind::Colour) break;   // «это X» at nothing: a line like any other
                    return answer(kPointAtIt, "no_thing");
                }
                // «это красный фонарь»: a colour said as part of a thing of another kind than this one's is a name
                const bool other = tl.kind == coop::TeachKind::Colour && tl.attributive && KindOf(tl.noun) != e->object;
                if (tl.plain || other) {
                    // «это гараж» is a name only when the bot reads no order in it, and it asks before it keeps it: «это
                    // ловушка» is a warning (2026-10-30, the owner: "the player may mean something else entirely")
                    if (!HearNamed(heard, spoken, h, memo, err, each)) return false;
                    if (!NoOrder(*h)) {
                        RememberLine(norm, *h, {});
                        return true;
                    }
                    const std::vector<std::string> name_words = coop::MemoryWords(tl.rest);
                    std::vector<std::string> room;   // «это дверь в гараж»: a name, of the room behind it
                    if (!other && KindOf(name_words) == e->object && !RoomName(*e, name_words, &room))   // «это стол» at a table
                        return ForgetOwnName(*e, memo) ? answer(kRemembered, "forgot_name") : answer(kGotIt, "same_thing");
                    return OfferName(*e, name_words, now, memo);
                }
                // «вот жёлтую возьми»: an order is no colour lesson, whatever its words (2026-11-01, the owner's «Вот на желтую
                // кровать залез.» was "the same colour", and the order was dropped)
                if (tl.kind == coop::TeachKind::Colour) {
                    if (!HearNamed(heard, spoken, h, memo, err, each)) return false;
                    if (ReadsOrder(*h)) {
                        memo->info["teach"] = "none";
                        RememberLine(norm, *h, {});
                        return true;
                    }
                }
                if (tl.kind == coop::TeachKind::Colour && tl.colour == ColourOfThing(*e)) return answer(kGotIt, "same_thing");
                std::string problem;
                const bool name = tl.kind == coop::TeachKind::Name;
                // «назови это гаражом» at a door with an inside: the room behind it
                std::vector<std::string> room;
                const bool is_room = name && RoomName(*e, coop::MemoryWords(tl.rest), &room);
                std::string room_name;
                for (const std::string& w : room) room_name += (room_name.empty() ? "" : " ") + w;
                const std::string key = is_room ? RoomKey(*e) : KeyOf(*e), kept = is_room ? room_name : tl.rest;
                const bool ok = name ? g_memory->KeepName({map, key, g_language, kept, 0}, &problem)
                                     : g_memory->KeepColour({map, KeyOf(*e), tl.colour, 0}, &problem);
                if (!ok) MemoryError(memo, problem);
                if (name) memo->info["kept_name"] = {{"entity", e->id}, {"key", key}, {"name", kept}};
                if (is_room) memo->info["kept_name"]["room"] = true;
                if (!name) memo->info["kept_colour"] = {{"entity", e->id}, {"key", KeyOf(*e)}, {"colour", tl.colour}};
                return answer(kRemembered, name ? "kept_name" : "kept_colour");
            }
            case coop::TeachKind::Means: {
                // «когда я говорю бабах, это значит кидай гранату» (2026-10-30, the owner: the player teaches the bot everything):
                // the meaning is read now and not carried out (the reply is the memory's), and the bot asks before it keeps it.
                // «A — это то же самое, что B» (2026-10-31, the owner: «Смотри, запрыгнуть на стул и присесть. Это то же самое,
                // что сесть на стул. Научись.»): the side the bot reads as orders is the meaning, the other the player's own
                // words; both read, the one of more orders, then of more words
                std::string said_words = tl.said, meant_text = tl.rest;
                bool read = false;
                if (tl.same) {
                    Heard a, b;
                    bool ra = false, rb = false;
                    if (!ReadMeaning(tl.said_text, spoken, &a, memo, err, &ra)) return false;
                    if (!ReadMeaning(tl.rest, spoken, &b, memo, err, &rb)) return false;
                    const size_t na = a.turns.size() + a.held.size(), nb = b.turns.size() + b.held.size();
                    const size_t wa = coop::MemoryWords(tl.said).size(), wb = coop::MemoryWords(coop::MemoryNorm(tl.rest)).size();
                    const bool first = ra && (!rb || na > nb || (na == nb && wa > wb));
                    memo->info["same"] = {{"first", tl.said_text}, {"second", tl.rest}, {"first_read", ra}, {"second_read", rb},
                                          {"meaning", first ? "first" : "second"}};
                    if (first) {
                        said_words = coop::MemoryNorm(tl.rest);
                        meant_text = tl.said_text;
                        *h = std::move(a);
                    } else {
                        *h = std::move(b);
                    }
                    read = first || rb;
                } else {
                    if (!ReadMeaning(tl.rest, spoken, h, memo, err, &read)) return false;
                }
                const std::string meant = coop::MemoryNorm(meant_text);
                memo->terms["said"][said_words] = {{"text", said_words}};
                memo->terms["meant"][meant] = {{"text", meant}};
                if (!read) {
                    memo->info["means"] = {{"said", said_words}, {"meant", meant_text}};
                    return answer("I don't understand \"" + meant + "\".", "means_not_read");
                }
                offer = Offer();
                offer.open = true;
                offer.meaning = true;
                offer.keys = {said_words};
                offer.at = now;
                for (const Turn& t : h->turns) offer.lines.push_back(t.line);
                for (const std::string& line : h->held) offer.lines.push_back(line);
                offer.intent = LabelOf(h->turns[0]);
                // a place both name: for any thing («сесть на {x}»)
                if (PatternOffer po = PatternOf(said_words, meant_text, *h); !po.key.empty()) offer.patterns.push_back(std::move(po));
                memo->info["offered_meaning"] = {{"heard", offer.keys}, {"meant", meant}, {"lines", offer.lines}, {"intent", offer.intent}};
                if (!offer.patterns.empty()) memo->info["offered_meaning"]["pattern"] = PatternJson(offer.patterns[0]);
                return answer("Shall I remember that \"" + said_words + "\" means \"" + meant + "\"?", "offered_meaning");
            }
            case coop::TeachKind::BotName:
            case coop::TeachKind::PlayerName: {
                // «тебя зовут Рекс», «меня зовут Тимур» (2026-10-31): kept at once, as «назови это X» is. The reply's memory
                // carries "bot_name" for the game (its name over the bot); null: the game's own name again
                const bool bot = tl.kind == coop::TeachKind::BotName;
                const std::string who = bot ? "bot" : "player";
                std::string problem;
                if (tl.forget) {
                    bool any = false;
                    if (!g_memory->ForgetPerson(who, &any, &problem)) MemoryError(memo, problem);
                    if (bot) memo->info["bot_name"] = nullptr;
                    return answer(any ? kForgotten : kNotKept, any ? (bot ? "forgot_bot_name" : "forgot_player_name") : "not_kept");
                }
                if (!g_memory->KeepPerson({who, tl.said_text, 0}, &problem)) MemoryError(memo, problem);
                memo->info[bot ? "bot_name" : "player_name"] = tl.said_text;
                NameTerm(memo, tl.said_text);
                if (bot) return answer(kNamedA + tl.said_text + kNamedB, "kept_bot_name");
                g_name_since = 0;   // the bot says it now
                return answer(kMeetA + tl.said_text + ".", "kept_player_name");
            }
            case coop::TeachKind::Pronounce: {
                // «в слове замок ударение на первый слог», «говори Buddy как Бадди»: how the voice says a word
                if (tl.forget) {
                    bool any = false;
                    std::string problem;
                    if (!g_memory->ForgetSaying(g_language, tl.said, &any, &problem)) MemoryError(memo, problem);
                    memo->info["forgot_saying"] = tl.said;
                    return answer(any ? kForgotten : kNotKept, any ? "forgot_saying" : "not_kept");
                }
                return OfferSaying(tl, now, memo);
            }
            case coop::TeachKind::Speech: {
                if (tl.forget) {   // «говори как раньше»
                    bool any = false;
                    std::string problem;
                    if (!g_memory->ForgetPhrases(g_language, &any, &problem)) MemoryError(memo, problem);
                    return answer(any ? kForgotten : kNotKept, any ? "forgot_phrases" : "not_kept");
                }
                return OfferPhrase(tl, now, memo);
            }
            case coop::TeachKind::Behaviour: {
                if (tl.forget) {   // «веди себя как раньше»
                    bool any = false;
                    std::string problem;
                    if (!g_memory->ForgetSettings(&any, &problem)) MemoryError(memo, problem);
                    memo->info["behaviour"] = SettingsJson();
                    return answer(any ? kForgotten : kNotKept, any ? "forgot_settings" : "not_kept");
                }
                if (OfferSetting(tl, now, memo)) return true;
                break;
            }
            case coop::TeachKind::Forget: {
                std::string problem;
                bool any = false;
                if (tl.rest.empty()) {   // the thing under the crosshair
                    const std::string thing = PointedThing();
                    if (thing.empty()) return answer(kPointAtIt, "no_thing");
                    const coop::WorldEntity* ge = EntityById(thing);
                    const std::string key = ge ? KeyOf(*ge) : thing;
                    if (!g_memory->ForgetThing(map, key, &any, &problem)) MemoryError(memo, problem);
                    if (ge && HasInside(*ge)) {   // at a door: the room behind it too
                        bool room_any = false;
                        if (!g_memory->ForgetThing(map, RoomKey(*ge), &room_any, &problem)) MemoryError(memo, problem);
                        any = any || room_any;
                    }
                    memo->info["forgot_thing"] = key;
                    return answer(any ? kForgotten : kNotKept, any ? "forgot" : "not_kept");
                }
                bool forgot_line = g_memory->ForgetLine(g_language, tl.rest, &problem);   // a kept line said so
                if (!forgot_line && !problem.empty()) MemoryError(memo, problem);
                // ... said in another form of its verbs, and the patterns it is said as («забудь сесть на стул»: «сесть на {x}»)
                std::vector<std::string> also;
                for (const coop::MemoryLine& l : g_memory->Lines())
                    if (l.lang == g_language && (IsPattern(l) ? coop::MatchPattern(l.heard, tl.rest, nullptr, nullptr) : coop::SameLine(l.heard, tl.rest)))
                        also.push_back(l.heard);
                for (const std::string& k : also) {
                    std::string e;
                    if (g_memory->ForgetLine(g_language, k, &e)) forgot_line = true;
                    else if (!e.empty()) MemoryError(memo, e);
                }
                if (forgot_line) {
                    memo->info["forgot_line"] = tl.rest;
                    if (!also.empty()) memo->info["forgot_also"] = also;
                    return answer(kForgotten, "forgot");
                }
                const std::vector<std::string> what = coop::MemoryWords(tl.rest);
                const std::vector<coop::MemoryName> names = g_memory->Names();   // a copy: forgetting changes the list
                for (const coop::MemoryName& n : names) {
                    size_t b = 0, en = 0;
                    if (n.map != map || n.lang != g_language || !coop::FindWords(what, coop::MemoryWords(n.name), 0, &b, &en) ||
                        b != 0 || en != what.size())
                        continue;
                    if (!g_memory->ForgetThing(map, n.entity, &any, &problem)) MemoryError(memo, problem);
                    memo->info["forgot_thing"] = n.entity;
                    return answer(kForgotten, "forgot");
                }
                break;   // nothing kept by these words: «забудь про дверь» is a line like any other
            }
            default:
                break;
        }

        // "forget sit down on the chair", «забудь сядь на стул»: a line the memory keeps, of any length, after a word of forgetting
        // (ReadTeach's Forget takes a name or a short line only: "forget the pistol just start shooting" is a change of plan). A
        // line said with "forget" is never the kept line itself (2026-11-05, the owner's log: NearLine took "Forget sit down on the
        // chair." for the kept line, one word more, and the bot did what it had been taught)
        const std::string forget_what = coop::ForgetWhat(heard);
        if (!forget_what.empty()) {
            std::vector<std::string> gone;
            for (const coop::MemoryLine& l : g_memory->Lines())
                if (l.lang == g_language && (IsPattern(l) ? coop::MatchPattern(l.heard, forget_what, nullptr, nullptr)
                                                          : l.heard == forget_what || coop::NearLine(l.heard, forget_what) ||
                                                                coop::SameLine(l.heard, forget_what)))
                    gone.push_back(l.heard);
            bool forgot_line = false;
            for (const std::string& k : gone) {
                std::string e;
                if (g_memory->ForgetLine(g_language, k, &e)) forgot_line = true;
                else if (!e.empty()) MemoryError(memo, e);
            }
            if (forgot_line) {
                memo->info["forgot_line"] = forget_what;
                memo->info["forgot_also"] = gone;
                return answer(kForgotten, "forgot");
            }
        }
        // a line the memory keeps: the order lines kept for it, with the things the player named in it (LinesWithNames)
        if (const coop::MemoryLine* kept = forget_what.empty() ? g_memory->LineFor(g_language, norm) : nullptr) {
            const coop::MemoryLine line = *kept;
            std::vector<std::string> named, rooms;
            const std::vector<std::string> lines = LinesWithNames(line.lines, heard, &named, &rooms);
            memo->info["did"] = "used_line";
            memo->info["used_line"] = {{"heard", line.heard}, {"lines", lines}};
            if (lines != line.lines) memo->info["used_line"]["kept_lines"] = line.lines;
            if (!named.empty()) memo->info["named"] = named;
            if (!rooms.empty()) memo->info["rooms"] = rooms;   // RoomOrder
            planner.SetNamed(named);
            const bool ok = Hear(heard, spoken ? coop::SpeechTextForClassifier(heard) : heard, h, err, each, &lines);
            planner.SetNamed({});
            if (!ok) return false;
            RememberLine(norm, *h, line.heard);
            return true;
        }
        // a pattern the player taught (2026-10-31: «сесть на {x}» means «запрыгнуть на {x} и присесть»): its meaning with this
        // line's place, read as the player's own line («сядь на диван» -> «запрыгнуть на диван и присесть», «сядь на него»)
        if (forget_what.empty()) {
            std::string slot;
            if (const coop::MemoryLine* found = PatternFor(heard, &slot)) {
                const coop::MemoryLine pat = *found;
                if (pat.source == "pattern") {
                    // its English order lines with the place this line names in English: the meaning is not read again
                    std::vector<std::string> named, rooms;
                    const std::string read_as = WithNames(heard, &named, &rooms);
                    const std::string place = HeardPlace(read_as, spoken);
                    if (!place.empty()) {
                        std::vector<std::string> lines;
                        for (const std::string& l : pat.lines) lines.push_back(coop::FillPattern(l, place));
                        memo->info["did"] = "used_pattern";
                        memo->info["used_pattern"] = {{"heard", pat.heard}, {"place", place}, {"lines", lines}};
                        if (!named.empty()) memo->info["named"] = named;
                        planner.SetNamed(named);
                        const bool ok = Hear(heard, spoken ? coop::SpeechTextForClassifier(heard) : heard, h, err, each, &lines);
                        planner.SetNamed({});
                        if (!ok) return false;
                        RememberLine(norm, *h, pat.heard);
                        return true;
                    }
                } else {
                    // the meaning as said with this line's place, read as a line of its own
                    const std::string taught = coop::FillPattern(pat.lines[0], slot);
                    memo->info["did"] = "used_pattern";
                    memo->info["used_pattern"] = {{"heard", pat.heard}, {"meaning", taught}};
                    const Alone alone(taught_alone);
                    if (!HearNamed(AsLine(taught), spoken, h, memo, err, each)) return false;
                    RememberLine(norm, *h, pat.heard);
                    return true;
                }
            }
        }
        // a line of several parts, one of them a line or a pattern the player taught (2026-11-02, the owner: «сядь на стул» said
        // alone was its lesson, «встань с дивана и сядь на стул» was not): the taught part by its lesson, each other part read
        // alone (as a taught meaning is), all in the order said
        if (g_memory && g_memory->IsOpen()) {
            const std::vector<std::string> parts = LineParts(heard);
            std::vector<std::vector<std::string>> part_lines(parts.size());
            std::vector<std::string> used;
            for (size_t i = 0; parts.size() > 1 && i < parts.size(); ++i) {
                // the words round a part that are no part of what was taught («ну сядь на стул», «а потом ...»)
                std::string part = parts[i];
                static const std::initializer_list<const char*> kLead = {"ну ", "а ", "давай ", "теперь ", "так ", "now ", "ok ", "okay ",
                                                                         "so ", "bueno ", "ahora ", "pues "};
                for (bool cut = true; cut;) {
                    cut = false;
                    const std::string low = coop::MemoryNorm(part);
                    for (const char* lead : kLead)
                        if (low.rfind(lead, 0) == 0 && low.size() > std::strlen(lead)) {
                            const std::vector<coop::SpanWord> pw = coop::SpanWords(part);
                            if (pw.size() > 1) part = part.substr(pw[1].begin), cut = true;
                            break;
                        }
                }
                if (const coop::MemoryLine* kept = g_memory->LineFor(g_language, coop::MemoryNorm(part))) {
                    part_lines[i] = kept->lines;
                    used.push_back(kept->heard);
                    continue;
                }
                std::string slot;
                if (const coop::MemoryLine* found = PatternFor(part, &slot)) {
                    const coop::MemoryLine pat = *found;
                    if (pat.source == "pattern") {
                        const std::string place = HeardPlace(part, spoken);
                        if (place.empty()) continue;
                        for (const std::string& l : pat.lines) part_lines[i].push_back(coop::FillPattern(l, place));
                    } else {
                        Heard x;
                        bool read = false;
                        if (!ReadMeaning(coop::FillPattern(pat.lines[0], slot), spoken, &x, memo, err, &read)) return false;
                        if (!read) continue;
                        for (const Turn& t : x.turns) part_lines[i].push_back(t.line);
                        for (const std::string& l : x.held) part_lines[i].push_back(l);
                    }
                    used.push_back(pat.heard);
                }
            }
            if (!used.empty()) {
                for (size_t i = 0; i < parts.size(); ++i) {
                    if (!part_lines[i].empty()) continue;
                    Heard x;
                    bool read = false;
                    if (!ReadMeaning(parts[i], spoken, &x, memo, err, &read)) return false;
                    for (const Turn& t : x.turns) part_lines[i].push_back(t.line);
                    for (const std::string& l : x.held) part_lines[i].push_back(l);
                }
                std::vector<std::string> lines;
                for (const std::vector<std::string>& pl : part_lines) lines.insert(lines.end(), pl.begin(), pl.end());
                std::vector<std::string> named, rooms;
                lines = LinesWithNames(lines, heard, &named, &rooms);
                memo->info["did"] = "used_line_part";
                memo->info["used_line_part"] = {{"heard", used}, {"parts", parts}, {"lines", lines}};
                if (!named.empty()) memo->info["named"] = named;
                if (!rooms.empty()) memo->info["rooms"] = rooms;   // RoomOrder
                planner.SetNamed(named);
                const bool ok = Hear(heard, spoken ? coop::SpeechTextForClassifier(heard) : heard, h, err, each, &lines);
                planner.SetNamed({});
                if (!ok) return false;
                RememberLine(norm, *h, used[0]);
                return true;
            }
        }
        if (!HearNamed(heard, spoken, h, memo, err, each)) return false;
        // "what is that?" at a thing the player named: the bot says the name (the game would say the thing's kind). The
        // reply tables' "That's {thing}." takes the name as it is (memo->terms)
        if (h->turns.size() == 1 && h->turns[0].state == "what") {
            const coop::WorldEntity* e = PointedEntity();
            if (e) what_key = KeyOf(*e), what_at = now;   // «нет, это ...» next corrects the answer
            if (const coop::MemoryName* n = e ? NameOf(*e) : nullptr) {
                const std::string called = (g_language == "en" ? "the " : "") + n->name;
                memo->terms["thing"][called] = {{"text", called}, {"acc", called}};
                memo->info["name_of"] = {{"entity", e->id}, {"name", n->name}};
                RememberLine(norm, *h, {});
                return answer("That's " + called + ".", "named_thing");
            }
            // a door into a room the player named: "That's the door to the garage."
            if (const coop::MemoryName* n = e && HasInside(*e) ? NameByKey(RoomKey(*e)) : nullptr) {
                const std::string called = (g_language == "en" ? "the " : "") + n->name;
                memo->terms["thing"][called] = {{"text", called}, {"acc", called}};
                memo->info["name_of"] = {{"entity", e->id}, {"name", n->name}, {"room", true}};
                RememberLine(norm, *h, {});
                return answer(kDoorToA + called + ".", "room_door");
            }
            // a colour the player taught: "That's the yellow table." (the game knows its own, "the white table")
            if (const coop::MemoryColour* c = e ? TaughtColour(*e) : nullptr) {
                memo->info["colour_of"] = {{"entity", e->id}, {"colour", c->colour}};
                RememberLine(norm, *h, {});
                return answer("That's " + ThingWordsFor(e->object, c->colour, memo) + ".", "coloured_thing");
            }
        }
        // a line read right after misses about the same thing: "Shall I remember that "X" means "Y"?"
        OfferMeaning(norm, heard, *h, now, memo);
        // "no" right after a line the memory read: a doubt about the kept line
        if (!recent.empty() && !recent.back().kept.empty() && Ms(now - recent.back().at) <= kDoubtMs && Cancelled(*h)) {
            bool removed = false;
            std::string problem;
            if (g_memory->DoubtLine(g_language, recent.back().kept, &removed, &problem))
                memo->info[removed ? "forgot_line" : "doubted_line"] = recent.back().kept;
            else if (!problem.empty())
                MemoryError(memo, problem);
            recent.back().kept.clear();
        }
        RememberLine(norm, *h, {});
        return true;
    }

    // the classifier's probabilities for a text, in `p`; kept for the text read last
    bool Read(const std::string& text, std::string* err) {
        if (has_read && read_text == text) return true;
        has_read = false;
        const auto t0 = Clock::now();
        // with --decider the second reader runs on a thread of its own while the ensemble reads the line
        std::vector<float> pd;
        std::string derr;
        bool dok = false;
        std::thread second;
        if (g_decider) second = std::thread([&] { dok = g_decider->Probs(text, &pd, &derr); });
        const bool ok = Classify(m, m.tok.Encode(text), &p, err);
        if (second.joinable()) second.join();
        if (!ok) return false;
        if (g_decider) SecondReading(*g_decider, dok, pd, derr, &p);
        read_ms = Ms(Clock::now() - t0);
        read_text = text;
        return has_read = true;
    }

    // While the planner's question is open: is this a line its rules for answers are made for? Yes when the classifier
    // takes it for an answer (yes, no, maybe, don't know) or for no order, or cannot read it: "yes", "the left one",
    // "over there". A line it reads as an order is a line like any other. (On the classifier's own probabilities: the
    // world's priors, which the planner applies, are not in them.)
    bool AnswerLike(const std::string& text, bool* answer, std::string* err) {
        if (!Read(text, err)) return false;
        int intent = -1;
        double conf = 0;
        *answer = true;
        if (!brain.Pick(p, &intent, &conf) || !(conf >= brain.threshold)) return true;
        const std::string& label = m.cfg.labels[static_cast<size_t>(intent)];
        *answer = label == "NONE" || std::find(m.cfg.answer_intents.begin(), m.cfg.answer_intents.end(), label) != m.cfg.answer_intents.end();
        return true;
    }

    // the line through the classifier and the planner, and the reply chosen for it; nothing is printed. continued: a
    // further order line of the line the player just said (world.h, "a line of several orders")
    bool Think(const std::string& heard_line, const std::string& text_line, Turn* turn, std::string* err, bool continued = false) {
        // the time said with the order (round v68, time_phrase.h): it never changes what the order is, so the classifier,
        // the slots and the places read the line without it ("run forward for 10 seconds" was MOVE_TO 0.69, "run forward"
        // is not in doubt); the time goes with the turn
        std::string heard = heard_line, text = text_line;
        turn->time = coop::FindTimePhrase(heard_line, &heard);
        if (turn->time.found) coop::FindTimePhrase(text_line, &text);
        if (!Read(text, err)) return false;
        turn->p = p;
        turn->ms = read_ms;   // the classifier's time for this text, whichever step asked for it first
        read_ms = 0;
        const int pending_before = brain.Pending();
        turn->r = planner.Step(heard, p, continued);
        const coop::PlannerResult& r = turn->r;
        const coop::Decision& d = r.decision;
        if (d.intent < 0) return *err = "the model does not fit intent_config.json", false;
        const std::string& intent = m.cfg.labels[d.intent];
        std::string& reply = turn->reply;
        // the planner's own words: a question, a settled order, "Copy, stopping.", the place it assumed ("Open fire, on
        // your pin."); otherwise the chat picks a line
        if (r.action == "ask" || r.action == "resolved" || !r.say.empty()) reply = r.say;
        else switch (d.action) {
            case coop::Action::Negated: reply = "Copy, standing down."; break;
            case coop::Action::SayAgain: reply = Pick(kAgain); break;
            case coop::Action::Ignore: reply = Pick(kAck); break;
            case coop::Action::Execute: reply = "Now! " + Pick(LinesFor(m.cfg.labels[pending_before])); break;
            case coop::Action::Go: reply = "Going!"; break;
            case coop::Action::Wait: reply = Pick(kLines.at("WAIT")); break;
            case coop::Action::Queued: reply = "Ready to " + m.cfg.phrases[intent] + ". On your go."; break;
            case coop::Action::Act: reply = intent == "SMALL_TALK" ? Pick(TalkLines(text)) : Pick(LinesFor(intent)); break;
            case coop::Action::Answer: reply = Pick(LinesFor(intent)); break;   // the answer said back: nothing is done
        }
        // "Which chair? You mean the red chair?" instead of "The one ahead, 8 m?" (2026-10-30, the owner: callouts, not distances)
        if (r.action == "ask") {
            const std::string callout = WhichCallout(&turn->terms);
            if (!callout.empty()) reply = callout;
        }
        // "hold fire until I say": the bot holds now and has queued OPEN_FIRE for the signal
        if (intent == "HOLD_FIRE" && d.action == coop::Action::Act && d.on_signal && brain.LabelIndex("OPEN_FIRE") >= 0)
            reply += " On your go.";
        if (d.other && (d.action == coop::Action::Act || d.action == coop::Action::Queued) && intent != "HOLD_OTHER_ANGLE" &&
            intent != "HOLD_FIRE" && r.action != "ask")
            reply += " Taking the other one.";
        // what it sees, how it is: the game answers (the order, if any, is dropped in ReplyJson)
        if (intent == "STATUS_REPORT" || intent == "BODY_STATE") {
            // a v64 bot reads the question itself: the words only say which part ("what do you see" the things, "are you hot"
            // the heat); a report with no part is everything, a body question with none the whole body
            const std::string part = StateQuestion(text, true);
            turn->state = intent == "STATUS_REPORT" ? (part == "seen" ? "seen" : "how")
                                                    : (part.empty() || part == "seen" || part == "how" ? "body" : part);
            reply.clear();
        } else if (intent == "WHAT_IS_IT") {
            // "what is that" (bot v66): the game names the thing under the crosshair, and that thing is the one talked about
            // now: «Что это?» "the white table", «Запрыгни на него» is onto it, not onto the rock of an order 27 s before (the
            // owner's log, 2026-10-30; "it" is the thing named last, rule set v8)
            turn->state = "what";
            reply.clear();
            // a spot of no kind ("That's a wall."): the talk is about what was pointed at all the same, not about the thing of an
            // order before it (2026-11-01, the owner's log: «А это что?» at the far wall, «Перепрыгни её» jumped the near wall it
            // had jumped 8 s before). The spot's id is not kept by the next world: "it" is then where the player looks
            if (const coop::WorldEntity* e = PointedEntity()) planner.Named(e->id);
            else planner.Named(PointedThing());
        } else if (intent == "MOVE_TO") {
            // "got any ammo?": the planner may have asked where the ammo is; the question is the bot's, not the walk's
            turn->state = StateQuestion(text, false, true);
            if (!turn->state.empty()) {
                reply.clear();
                if (r.action == "ask") planner.DropQuestion();
            }
        } else if (r.action != "ask" && (intent == "SMALL_TALK" || intent == "SEE_THING" || intent == "NONE" || d.action == coop::Action::Ignore)) {
            turn->state = StateQuestion(text, intent == "SMALL_TALK" || intent == "NONE" || d.action == coop::Action::Ignore);
            if (!turn->state.empty()) reply.clear();
        }
        // the time of an order made later from an earlier line: the answer to the bot's question, "go" for a queued order,
        // "again"; a time said now wins
        if (!turn->time.found) {
            if (r.action == "resolved" && asked_time.found) turn->time = asked_time;
            else if (d.action == coop::Action::Execute && queued_time.found) turn->time = queued_time;
            else if (intent == "REPEAT" && last_time.found) turn->time = last_time;
        }
        if (r.action == "ask") asked_time = turn->time;
        else if (r.action != "resolved" && !planner.Mem().has_question) asked_time = coop::TimePhrase{};
        if (d.action == coop::Action::Queued) queued_time = turn->time;
        else if (d.action == coop::Action::Execute || d.action == coop::Action::Wait || d.action == coop::Action::Negated) queued_time = coop::TimePhrase{};
        const bool orders = r.action == "resolved" || d.action == coop::Action::Act || d.action == coop::Action::Execute ||
                            d.action == coop::Action::Wait || d.action == coop::Action::Go;
        if (orders) last_time = turn->time;
        // ... and the bot says it ("Holding up. 10 seconds."), with an order it takes now; a question waits for its answer
        if (turn->time.found && orders && r.action != "ask" && !reply.empty()) reply += " " + TimeWords(turn->time);
        return true;
    }

    // under /why, where the line went before the classifier
    void PrintRoute(const Heard& h) {
        if (!g_chain || !chain_on) return;
        char route[48] = "no router";
        if (h.route >= 0) std::snprintf(route, sizeof route, "router %.2f (%.0f ms)", h.route, h.route_ms);
        if (h.decoded)
            std::printf("     chain: %s, decoder %.0f ms: %s\n", route, h.rewrite_ms,
                        h.rewritten ? "rewritten" : h.note.empty() ? "written back as it is" : h.note.c_str());
        else if (!h.note.empty())
            std::printf("     chain: %s, the line as it is: %s\n", route, h.note.c_str());
        else
            std::printf("     chain: %s, the line as it is\n", route);
    }

    // the chat's two lines for a turn: the reply, and under /why the debug line
    void Print(const Turn& turn) {
        const coop::PlannerResult& r = turn.r;
        const coop::Decision& d = r.decision;
        const std::string& intent = m.cfg.labels[d.intent];
        const double ms = turn.ms;
        const std::vector<float>& probs = turn.p;
        std::printf("bot> %s\n", turn.reply.c_str());
        if (why) {
            const auto top = coop::TopK(probs, 3);
            std::string slots;
            if (d.on_signal) slots += "on my signal";
            if (d.other) slots += std::string(slots.empty() ? "" : ", ") + "other";
            if (d.executed_other) slots += std::string(slots.empty() ? "" : ", ") + "other (the queued order's)";
            const std::string& first = m.cfg.labels[top[0]];
            char mass[64] = "";
            if (m.cfg.gate == "family")
                std::snprintf(mass, sizeof mass, " | %s mass %.2f", m.cfg.families[intent].c_str(), d.prob);
            std::printf("     %s (%s) %.2f | %s %.2f | %s %.2f%s | %s%s%s | %.0f ms\n", first.c_str(),
                        m.cfg.families[first].c_str(), probs[top[0]], m.cfg.labels[top[1]].c_str(), probs[top[1]],
                        m.cfg.labels[top[2]].c_str(), probs[top[2]], mass, coop::ActionName(d.action),
                        slots.empty() ? "" : (" | slots: " + slots).c_str(),
                        brain.Pending() >= 0 ? (" | queued: " + m.cfg.labels[brain.Pending()]).c_str() : "", ms);
            if (!d.places.targets.empty())
                std::printf("     place: %s\n", PlacesText(d.places, brain.Places()).c_str());
            if (!d.executed_places.targets.empty())
                std::printf("     executes at: %s\n", PlacesText(d.executed_places, brain.Places()).c_str());
            // the world: how each target was grounded, the order the game gets, the question pending
            if (!r.ground.empty() || r.has_order || r.adjusted) {
                std::string line;
                for (const coop::Grounding& g : r.ground)
                    line += (line.empty() ? "" : "; ") + g.status + (g.entity.empty() ? "" : " " + g.entity) + (g.via.empty() ? "" : " (" + g.via + ")");
                if (r.has_order)
                    line += std::string(line.empty() ? "" : " | ") + "order: " + m.cfg.labels[static_cast<size_t>(r.order.intent)] +
                            (r.order.entity.empty() ? "" : " @ " + r.order.entity);
                if (planner.Mem().has_question) line += std::string(line.empty() ? "" : " | ") + "asking";
                if (r.adjusted) line += std::string(line.empty() ? "" : " | ") + "priors applied";
                std::printf("     world: %s\n", line.c_str());
            }
        }
    }
};

int RunChat(Model& m, int threads, const std::string& world_file) {
    Chat chat(m);
    std::string err;
    if (!chat.Init(&err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    if (!world_file.empty() && !chat.LoadWorld(world_file, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    std::printf("ready (C++, ONNX Runtime %s CPU, %d threads). threshold %.2f. Talk to your teammate in English; /why /t <x> /world FILE%s /q\n\n",
                coop::OrtBackend::RuntimeVersion().c_str(), threads, chat.brain.threshold, g_chain ? " /chain" : "");
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

// chain_tests.jsonl (export_chain_cpp.py): the turn's text, the line's token ids, the router's probability against
// PyTorch's, the decoder's answer against the one llama.cpp's own server gave on the CPU, in file order
int RunChainTests(Model& m, Chain& c) {
#ifdef COOP_WITH_LLM
    const auto rows = ReadJsonl(c.dir + "/chain_tests.jsonl");
    size_t turn_ok = 0, ids_ok = 0, routed = 0, route_close = 0, route_side = 0, answer_ok = 0, pieces_ok = 0, shown = 0, scenes = 0, scene_ok = 0;
    double worst = 0;
    std::vector<double> ms;
    std::string err;
    for (const json& r : rows) {
        const auto before = r.at("before").get<std::vector<std::string>>();
        const std::string bot = r.at("bot").is_null() ? std::string() : r.at("bot").get<std::string>();
        const std::string line = r.at("line").get<std::string>();
        const std::string scene = r.contains("scene") && !r.at("scene").is_null() ? r.at("scene").get<std::string>() : std::string();
        const std::string turn = coop::RewriterTurn(before, bot, line, scene);
        turn_ok += turn == r.at("turn").get<std::string>();
        if (r.contains("scene_parts")) {   // the scene line from the parts the game sends, against chains9_v65.scene_text
            ++scenes;
            const std::string got = coop::SceneLine(SceneFromJson(r.at("scene_parts")));
            scene_ok += got == scene;
            if (got != scene && shown++ < 5) std::printf("  scene: C++ %s\n         Python %s\n", got.c_str(), scene.c_str());
        }
        const auto ids = m.tok.Encode(line);
        ids_ok += ids == r.at("ids").get<std::vector<int64_t>>();
        if (c.router && r.contains("route")) {
            double p = 0;
            if (!c.Route(ids, &p, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
            const double want = r.at("route").get<double>();
            ++routed;
            worst = std::max(worst, std::fabs(p - want));
            route_close += std::fabs(p - want) <= 1e-4;
            route_side += (p >= c.cut) == (want >= c.cut);
        }
        std::string answer;
        const auto t0 = Clock::now();
        if (!c.decoder.Answer(turn, &answer, nullptr, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        ms.push_back(Ms(Clock::now() - t0));
        const std::string want = r.at("answer").get<std::string>();
        answer_ok += answer == want;
        const bool same = coop::RewriterPieces(answer) == coop::RewriterPieces(want);
        pieces_ok += same;
        if (!same && shown++ < 5)
            std::printf("  %s\n    C++    %s\n    server %s\n", Escaped(turn).c_str(), Escaped(answer).c_str(), Escaped(want).c_str());
    }
    const size_t n = rows.size();
    std::printf("chain tests, %zu lines: turn text %zu/%zu, token ids %zu/%zu\n", n, turn_ok, n, ids_ok, n);
    if (scenes) std::printf("  scene line from the game's parts equal to Python's on %zu/%zu\n", scene_ok, scenes);
    if (routed)
        std::printf("  router: probability within 1e-4 of PyTorch on %zu/%zu (largest difference %.2g), same side of the cut %.2f on %zu/%zu\n",
                    route_close, routed, worst, c.cut, route_side, routed);
    else
        std::printf("  router: none in this folder\n");
    // the file's answers are the CPU's: a GPU rounds another way and a close call falls the other way, so there the
    // count is reported and not required
    const bool exact = c.decoder_options.gpu_layers == 0;
    std::printf("  decoder (%s, %s): answer equal to llama.cpp's server on the CPU on %zu/%zu, the same order lines on %zu/%zu%s; "
                "%.0f ms a line (median %.0f, p95 %.0f)\n",
                coop::Rewriter::Backend().c_str(), exact ? "CPU" : "GPU", answer_ok, n, pieces_ok, n,
                exact ? "" : " (not required on a GPU: --decoder-cpu is the exact check)",
                std::accumulate(ms.begin(), ms.end(), 0.0) / std::max<size_t>(n, 1), Percentile(ms, 0.5), Percentile(ms, 0.95));
    return turn_ok == n && ids_ok == n && scene_ok == scenes && route_close == routed && (!exact || pieces_ok == n) ? 0 : 1;
#else
    (void)m;
    (void)c;
    return std::fprintf(stderr, "this coop_cli was built without the decoder\n"), 2;
#endif
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

// --time-tests FILE: the C++ time phrases against the Python's (scripts/coop/time_phrase.py --write)
int RunTimeTests(const std::string& path) {
    std::string raw;
    if (!ReadFile(path, &raw)) return std::fprintf(stderr, "cannot read %s\n", path.c_str()), 1;
    size_t n = 0, same = 0;
    std::istringstream in(raw);
    for (std::string line; std::getline(in, line);) {
        if (line.empty() || line[0] != '{') continue;
        const json r = json::parse(line);
        ++n;
        std::string rest;
        const coop::TimePhrase t = coop::FindTimePhrase(r.at("line").get<std::string>(), &rest);
        json got = nullptr;
        if (t.found) {
            got = {{"kind", t.after ? "after" : "for"}, {"more", t.more}, {"capped", t.capped}, {"said", t.said}};
            if (t.range) got["min"] = t.min, got["max"] = t.max;
            else got["seconds"] = t.seconds;
        }
        const bool ok = got == r.at("time") && rest == r.at("rest").get<std::string>();
        if (ok) ++same;
        else std::printf("  %s: C++ %s %s, Python %s %s\n", Escaped(r.at("line")).c_str(), got.dump().c_str(), Escaped(rest).c_str(),
                         r.at("time").dump().c_str(), Escaped(r.at("rest")).c_str());
    }
    std::printf("time tests, %zu lines: the C++ equals the Python on %zu/%zu\n", n, same, n);
    return n > 0 && same == n ? 0 : 1;
}

// samples in -1..1 as 16-bit little-endian PCM
std::string Pcm16(const std::vector<float>& samples) {
    std::string bytes(samples.size() * 2, '\0');
    for (size_t i = 0; i < samples.size(); ++i) {
        const float x = std::clamp(samples[i], -1.0f, 1.0f);
        const int v = static_cast<int>(std::lround(x * 32767.0f));
        bytes[2 * i] = static_cast<char>(v & 0xff);
        bytes[2 * i + 1] = static_cast<char>((v >> 8) & 0xff);
    }
    return bytes;
}

std::string Base64(const std::string& bytes) {
    static const char* kAlphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string out;
    out.reserve((bytes.size() + 2) / 3 * 4);
    for (size_t i = 0; i < bytes.size(); i += 3) {
        const uint32_t b0 = static_cast<uint8_t>(bytes[i]);
        const uint32_t b1 = i + 1 < bytes.size() ? static_cast<uint8_t>(bytes[i + 1]) : 0;
        const uint32_t b2 = i + 2 < bytes.size() ? static_cast<uint8_t>(bytes[i + 2]) : 0;
        const uint32_t n = (b0 << 16) | (b1 << 8) | b2;
        out += kAlphabet[(n >> 18) & 63];
        out += kAlphabet[(n >> 12) & 63];
        out += i + 1 < bytes.size() ? kAlphabet[(n >> 6) & 63] : '=';
        out += i + 2 < bytes.size() ? kAlphabet[n & 63] : '=';
    }
    return out;
}

// a 16-bit mono PCM WAV file
bool WriteWav(const std::string& path, const std::vector<float>& samples, int sample_rate, std::string* err) {
    std::ofstream out(std::filesystem::u8path(path), std::ios::binary);
    if (!out) return *err = "cannot write " + path, false;
    const std::string data = Pcm16(samples);
    auto u32 = [&](uint32_t v) { for (int k = 0; k < 4; ++k) out.put(static_cast<char>((v >> (8 * k)) & 0xff)); };
    auto u16 = [&](uint16_t v) { out.put(static_cast<char>(v & 0xff)); out.put(static_cast<char>(v >> 8)); };
    out.write("RIFF", 4);
    u32(static_cast<uint32_t>(36 + data.size()));
    out.write("WAVEfmt ", 8);
    u32(16);
    u16(1);   // PCM
    u16(1);   // mono
    u32(static_cast<uint32_t>(sample_rate));
    u32(static_cast<uint32_t>(sample_rate * 2));
    u16(2);
    u16(16);
    out.write("data", 4);
    u32(static_cast<uint32_t>(data.size()));
    out.write(data.data(), static_cast<std::streamsize>(data.size()));
    return out ? true : (*err = "cannot write " + path, false);
}

#ifdef COOP_WITH_STT
// one WAV per speaker of a Piper voice saying the same line, to choose the bot's voice by ear
int RunTtsDemo(const coop::VoiceOptions& options, const std::string& out_dir, const std::string& text, const std::string& only) {
    coop::PiperVoice voice;
    std::string err;
    const auto t0 = Clock::now();
    if (!voice.Load(options, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    std::printf("voice: %s, %d Hz, on the %s, loaded in %.0f ms\n", voice.Describe().c_str(), voice.SampleRate(),
                voice.Provider() == "cuda" ? "GPU (CUDA)" : "CPU", Ms(Clock::now() - t0));
    std::vector<std::string> speakers;
    if (!only.empty()) {
        std::stringstream list(only);
        for (std::string s; std::getline(list, s, ',');)
            if (!s.empty()) speakers.push_back(s);
    } else {
        speakers = voice.Speakers();
        if (speakers.empty()) speakers.push_back("0");
    }
    std::filesystem::create_directories(std::filesystem::u8path(out_dir));
    double total_ms = 0, total_s = 0;
    for (const std::string& s : speakers) {
        std::vector<float> x;
        const auto t1 = Clock::now();
        // sentence by sentence, as "say" with "stream" sends them: when the first was ready, and whether they add up to the line
        std::vector<float> joined;
        std::vector<double> sentence_ms;
        const auto on_sentence = [&](const float* p, size_t n, bool) {
            sentence_ms.push_back(Ms(Clock::now() - t1));
            joined.insert(joined.end(), p, p + n);
            return true;
        };
        if (!voice.Speak(text, &x, &err, s, 0.0f, on_sentence)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        const double ms = Ms(Clock::now() - t1), seconds = static_cast<double>(x.size()) / voice.SampleRate();
        total_ms += ms;
        total_s += seconds;
        const std::string path = out_dir + "/" + s + ".wav";
        if (!WriteWav(path, x, voice.SampleRate(), &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        std::string sentences;
        if (sentence_ms.size() > 1) {
            sentences = ", " + std::to_string(sentence_ms.size()) + " sentences, the first in " + std::to_string(static_cast<int>(sentence_ms[0] + 0.5)) + " ms";
            sentences += joined == x ? " (they add up to the line)" : " (THEY DIFFER from the line: " + std::to_string(joined.size()) + " vs " + std::to_string(x.size()) + " samples)";
        }
        std::printf("%-6s %.2f s of audio in %.0f ms%s\n", s.c_str(), seconds, ms, sentences.c_str());
    }
    std::printf("%zu speakers: %.2f s of audio a line on average, made in %.0f ms (%.3f of real time)\n", speakers.size(),
                total_s / speakers.size(), total_ms / speakers.size(), total_s > 0 ? total_ms / 1000.0 / total_s : 0.0);
    return 0;
}

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
    std::vector<coop::SpeechWord> words;
    if (!stt.Transcribe(clip.data(), clip.size(), rate, &heard, err, &words)) return false;
    heard = StripPy(heard);
    std::printf("%s%s   [%.1f s of audio, recognized in %.0f ms]\n", prefix, heard.empty() ? "(nothing recognized)" : heard.c_str(),
                static_cast<double>(clip.size()) / rate, Ms(Clock::now() - t0));
    if (!words.empty()) {   // when each word began, as the game is told it
        std::string w;
        for (const coop::SpeechWord& x : words) w += (w.empty() ? "" : " ") + x.text + "@" + std::to_string(x.start).substr(0, 4);
        std::printf("%s  words: %s\n", prefix, w.c_str());
    }
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
int RunVoice(Model& m, const coop::SpeechOptions& opt, int threads, const std::string& world_file) {
    const HANDLE in = GetStdHandle(STD_INPUT_HANDLE);
    DWORD mode = 0;
    if (!GetConsoleMode(in, &mode)) return std::fprintf(stderr, "--voice reads the key from a console: run it in a terminal, not through a pipe\n"), 1;
    coop::SpeechRecognizer stt;
    Chat chat(m);
    MicCapture mic;
    std::string err;
    if (!LoadSpeech(stt, opt, &err) || !chat.Init(&err) || !mic.Start(&err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    if (!world_file.empty() && !chat.LoadWorld(world_file, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    std::printf("ready (C++, ONNX Runtime %s CPU, %d threads). threshold %.2f.\n"
                "Hold SPACE and talk, release to send. Or type a line and press Enter; /why /t <x> /world FILE%s /q. Esc quits.\n\n",
                coop::OrtBackend::RuntimeVersion().c_str(), threads, chat.brain.threshold, g_chain ? " /chain" : "");
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
int RunVoice(Model& m, const coop::SpeechOptions& opt, int threads, const std::string& world_file) {
    if (!isatty(STDIN_FILENO)) return std::fprintf(stderr, "--voice reads the key from a terminal: run it in one, not through a pipe\n"), 1;
    coop::SpeechRecognizer stt;
    Chat chat(m);
    MicCapture mic;
    KeyTerminal keys;
    std::string err;
    if (!LoadSpeech(stt, opt, &err) || !chat.Init(&err) || !mic.Start(&err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    if (!world_file.empty() && !chat.LoadWorld(world_file, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    if (!keys.Open()) return std::fprintf(stderr, "this terminal does not give single keys\n"), 1;
    std::printf("ready (C++, ONNX Runtime %s CPU, %d threads). threshold %.2f.\n"
                "Hold SPACE and talk, release to send. Or type a line and press Enter; /why /t <x> /world FILE%s /q. Esc quits.\n\n",
                coop::OrtBackend::RuntimeVersion().c_str(), threads, chat.brain.threshold, g_chain ? " /chain" : "");
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

// ---- the bot as a service for a game: JSON lines on stdin, JSON lines on stdout -----------------
//
// The game (the CLIENT side of it: speech and command recognition belong to the player's machine) starts
// `coop_cli --serve` and talks to it through the two pipes. One request per line, one answer per line;
// a line of stdout that does not start with '{' is a log line and the game skips it.
//
//   {"cmd":"text","id":7,"text":"hold the door","world":{...}}    a typed line; "world" (world.h, the shape of
//                                                                scripts/coop/world_example.json) is the state
//                                                                the planner grounds it in; without it the last
//                                                                world stays
//   "callees" (text, ptt_up, vad_up, wav; 2026-11-12): who may be called by name, nearest first: [{"to":"bot","key":"bot",
//        "names":["Buddy"]}, {"to":"sweeper","key":"OV_Sweeper","names":["Fred","Фёдор","Federico"],"far":false}, ...];
//        "to_key": the key of the one the game says the line to ("to" names their role). A line that calls another
//        (CalledCallee: the name at its start or end) is answered at once by {"event":"readdress","id":8,"heard":"Фёдор,
//        иди за мной","to":"sweeper","key":"OV_Sweeper","name":"Фёдор","text":"Иди за мной","far":false,"spoken":true,
//        "words":[...],"clip_start_s":0.2} and goes no further: the game says "text" again to them ("to", "to_key", their
//        world, "spoken" and "words" as given), or tells the player they are too far to hear ("far")
//   {"cmd":"ptt_down"}                                           the talk key went down: the clip starts (with
//                                                                its 0.2 s pre-roll), the bot's voice stops
//   {"cmd":"ptt_up","id":8,"world":{...}}                        the key came up: recognize, classify, plan
//                                                                ("tail_s": 0.2, how long the game kept the clip going after
//                                                                the key came up: the clip's own 0.15 s tail waits only the rest)
//   {"cmd":"ptt_cancel"}                                         drop the clip
//   {"cmd":"open_mic","on":true,"silence_s":0.6,"source":"mic"}  the open microphone (--vad, 2026-11-01): the voice detector
//                                                                cuts phrases out of what the microphone hears ("source":
//                                                                "script": out of the clips "mic_wav" gives it, silence
//                                                                between them), each ended by a pause of silence_s; the talk
//                                                                key's clip is its own (nothing is cut while it is down).
//                                                                Answered by "open_mic"; each phrase by
//        {"event":"speech_end","seg":3,"audio_s":1.4,"start_ago_s":2.1,"end_ago_s":0.7}   (when it began and ended, seconds
//        before this line was written); the game sends it back with its world:
//   {"cmd":"vad_up","id":8,"seg":3,"window":false,"world":{...}} recognize it; a line that does not call the bot by its name
//                                                                (CalledBy, the name the player gave it or the game's) and
//                                                                is not said in the game's window after the bot's words
//                                                                ("window": true) is {"event":"not_called","id":8,"heard":
//                                                                "...","name":"Рекс"} and goes no further; else as ptt_up
//   {"cmd":"mic_wav","path":"clip.wav"}                          the open microphone hears the clip (with "source":"script")
//   {"cmd":"wav","id":9,"path":"clip.wav","world":{...}}         a 16-bit PCM file instead of the microphone
//   {"cmd":"world","world":{...}}                                the world alone
//   {"cmd":"say","text":"Contact left!"}                         the bot's voice (--tts); {"cmd":"hush"} stops it
//   {"cmd":"say","id":12,"text":"Contact left!","speaker":"p311","speed":1.0}   with --tts-piper: the line as audio,
//                                                                answered by "speech" (speaker and speed optional:
//                                                                the ones the service was started with); "hush" and
//                                                                "ptt_down" drop the lines not made yet, and stop the
//                                                                one being made after its sentence ("hushed")
//                                                                "stream":true: a line of several sentences comes as one
//                                                                "speech_part" per sentence but the last, as each is made
//        "terms":{"thing":{"a spike trap":{"ru":{"text":"ловушка с шипами","acc":"ловушку с шипами"},"es":{"text":
//        "una trampa de pinchos"}}}}: the words of the level's labelled things the line names, in the languages the
//        label has; the reply table takes the player's (localize.h Terms)
//   {"cmd":"reset"} {"cmd":"threshold","value":0.7} {"cmd":"ping"} {"cmd":"quit"}
//   with --memory FILE (bot_memory.h): {"cmd":"teach","heard":"on my goal","lines":["go"]}, {"cmd":"teach","entity":
//        "Place_Door_03","name":"оружейка"}, {"cmd":"teach","entity":...,"colour":"green"}, {"cmd":"forget","heard":...},
//        {"cmd":"forget","entity":...}, {"cmd":"recall"}: answered by "taught", "forgot" ("none": nothing was kept) and
//        "memory", each with everything kept. The world's "map" scopes names and colours
//
//   {"event":"loading","part":"the language model","at":0.41,"until":0.61,"expect_ms":2900,"ms":6090}   before each part
//        of the start loads (Loading): the game shows the brain waking up; "ready" ends it
//   {"event":"ready","labels":[...],"gate":"family","threshold":0.68,"stt":true,"mic":true,"tts":true,...}
//   {"event":"reply","id":7,"heard":"hold the door","spoken":false,"intent":"HOLD_ANGLE","prob":1.0,
//    "action":"ask","say":"Which door? The one ahead, 8 m?","order":null,"question":{...},...}
//        action: the bot's (act, queued, execute, go, wait, negated, answer, say_again, ignore) or the
//        planner's (ask, resolved). "order" is what the game carries out NOW: {"intent","entity" (an id of
//        the world the game sent, or null),"candidates","direction","zone","pointer","other","via" (how the
//        place was found: "gaze", "pin", "here" = where the speaker is, "direction", "inside" = indoors where
//        the speaker looks, ...),"near" (the line pointed with "this" / "here" and no far word),"object" (the
//        object the line named, bot v56: "go up by the stairs" has no entity and the way is a staircase)}; null: nothing
//        With --chain DIR (rewriter.h) a line can give several orders. The reply's own fields stay the FIRST order's,
//        and it gains "turns": one object per order line gone through, in the order to carry them out, each with the
//        reply's fields and "line" (the order line: the player's, or one the decoder wrote from it); and "chain":
//        {"route" (the router's probability, null when it was not asked),"decoded","rewritten","held" (order lines
//        that wait for the answer to the question a turn asked; they come as turns of the reply to that answer,
//        "resumed" of them),"note","route_ms","rewrite_ms"}
//        "state" (a turn's, 2026-10-24): a question about the bot that only the game can answer, with no order and no
//        words: "seen" (what it sees and senses), "how" (everything), "body" (all of its body), "hurt", "heat", "cold", "gas",
//        "ammo" (StateQuestion; a v64 bot's STATUS_REPORT and BODY_STATE always carry one); "what" (bot v66's WHAT_IS_IT:
//        the game names the thing under the crosshair).
//        "time" (a turn's, round v68, time_phrase.h): the time said with the order, null when none: {"kind": "for" (it
//        lasts that long) | "after" (it starts after it), "seconds": 10 | "min": 3, "max": 7 (a random time, the game
//        draws), "more" (added to a timed order still running), "capped" (longer than 60 s, cut), "said"}. WAIT carries it
//        too (its order is null). The classifier, the slots and the places read the line without it; the bot's words get
//        one sentence for it ("10 seconds.", "In 10 seconds.", "A few seconds."). Kept for the order the bot asked about,
//        the one queued for "go" and "again".
//        With --memory: "memory", what the long-term memory did with the line: "teach" (the teaching rule it read:
//        none, meant, not_that, name, colour, forget), "did" (kept_line, used_line, asked_meaning, kept_name,
//        kept_colour, forgot, not_kept, no_thing, meaning_not_read, answered_question), "named" (the things its names
//        and colours named), "read_as" (the line with the names written as the things' kinds), "kept_line",
//        "used_line", "kept_name", "kept_colour", "forgot_line", "forgot_thing", "doubted_line", "error". A line the
//        memory answers itself ("What did you mean?", "Got it, I'll remember.") comes as SMALL_TALK with no order
//        With --replies-bro: "bro" "on" / "off" when the line switched the habit (bro.h; "off" comes with the bot's
//        agreement as its words and SMALL_TALK, nothing else read), "bro_active" whether this reply was written with it
//   {"event":"nothing","id":8,...}    the clip had no words;  {"event":"too_short","id":8}
//   {"event":"speech","id":12,"text":"Contact left!","rate":22050,"audio_s":0.9,"ms":61,"pcm16":"<base64>"}
//        the line as 16-bit little-endian mono samples (--tts-piper); the game plays it from the bot.
//        Streamed ("say" with "stream":true) and of several sentences: first {"event":"speech_part","id":12,"part":0,
//        "text":...,"rate":22050,"audio_s":1.1,"ms":150,"pcm16":...} for each sentence but the last (audio_s: that sentence's,
//        ms: since the line was begun), then "speech" with the last sentence's samples alone and "part" (its number),
//        "parts", "first_ms"; its "audio_s" and "ms" are the whole line's. The game plays the parts one after another
//        {"event":"hushed","id":12}: the line was dropped before it was made, or stopped while it was ("hush", "ptt_down",
//        a queue of three)
//        "ready" says which voice: "tts_kind" "piper" (the lines come back as audio) or "system" (the process speaks)
//   {"event":"error","id":7,"cmd":"text","message":"..."}        the request was refused; the service goes on
// The service ends when stdin closes (the game is gone) or on "quit".
std::string RepeatLine(const std::string& line) {
    const bool bro = g_replies != nullptr && g_replies == g_bro_replies;
    std::string lead = g_language == "ru" ? (bro ? "Брат, я сказал: " : "Я сказал: ")
                     : g_language == "es" ? (bro ? "Hermano, dije: " : "Dije: ")
                                          : (bro ? "Bro, I said: " : "I said: ");
    // the line's first letter small after the colon, unless the second is a capital too (a name, "OK")
    std::u32string u = coop::DecodeUtf8(line);
    if (u.size() > 1) {
        const char32_t a = u[0], b = u[1];
        const bool capital = (a >= U'A' && a <= U'Z') || (a >= U'А' && a <= U'Я') || a == U'Ё' || a == U'Á' || a == U'É' || a == U'Ó';
        const bool second_small = !((b >= U'A' && b <= U'Z') || (b >= U'А' && b <= U'Я'));
        if (capital && second_small) {
            if (a >= U'A' && a <= U'Z') u[0] = a - U'A' + U'a';
            else if (a >= U'А' && a <= U'Я') u[0] = a - U'А' + U'а';
            else if (a == U'Ё') u[0] = U'ё';
            else if (a == U'Á') u[0] = U'á';
            else if (a == U'É') u[0] = U'é';
            else if (a == U'Ó') u[0] = U'ó';
        }
    }
    return lead + coop::EncodeUtf8(u);
}

// Whether the talking model answers a line of one turn in the bot's role (2026-11-11, the owner: the lines that give no order,
// and the questions about the bot the game answers now with its body's state, «ты живой?», «хочешь пива?», "do you eat?"):
// small talk the planner does not answer itself (also when the classifier was not sure of it), a question about the bot that
// names no part of it (BODY_STATE "body"), and a question the classifier finds no order in (NONE, the line ends with "?").
// Questions the game answers from the bot's facts stay its: what it sees, its health, heat, ammo, what it is doing, how it is
// talking: the bot answered in its role a moment ago (Talk::TalkingNow): a question the classifier is not sure of is the talk
// going on («почему ты так думаешь?» after its answer was HOLD_ANGLE 0.4, "say again?")
bool TalkFor(const json& turn, const std::string& heard, bool talking) {
    const std::string intent = turn.value("intent", std::string()), action = turn.value("action", std::string());
    const std::string state = turn.contains("state") && turn["state"].is_string() ? turn["state"].get<std::string>() : std::string();
    if (action != "act" && action != "say_again" && action != "ignore" && action != "answer") return false;
    size_t e = heard.size();
    while (e > 0 && (heard[e - 1] == ' ' || heard[e - 1] == '\t')) --e;
    const bool question = e > 0 && heard[e - 1] == '?';
    if (intent == "SMALL_TALK") return state.empty();
    if (intent == "BODY_STATE") return state == "body";
    if (intent == "NONE" && state.empty()) return question;
    // an unsure question right after the talk: the talk's, unless it reads as an order the classifier could not quite pin down
    // -- its top label fairly likely and almost no talk in it: that asks again as before (2026-11-12: "maybe go to the bank?"
    // after small talk, MOVE_TO 0.65, got "The bank's about fourteen meters off" and no walk; «хочешь пива?» after small talk is
    // MOVE_TO 0.48 and is talk). talk_p: SMALL_TALK + NONE + BODY_STATE (set in respond)
    constexpr double kTalkShare = 0.15, kOrderSure = 0.6;
    const bool order_like = turn.value("talk_p", 0.0) < kTalkShare && turn.value("prob", 0.0) >= kOrderSure;
    return action == "say_again" && state.empty() && question && talking && !order_like;
}

// ---- names heard in the other alphabet (2026-11-15, the owner: «когда я одному персонажу NPC говорю ... по имени, то есть Майк, иди
// к Нику, то системе кажется, что я обращаюсь к Нику, хотя я говорю Майк, иди к Нику. Вот такие вещи должны быть распознаны
// хорошо»). A person of the level has a name in every language (Mike, Михалыч, Miguel) and the player says the one shown over them
// in his own speech: the Russian recognizer writes "Mike" as «Майк» and "Nick" as «Ник», an English one «Коля» as "Kolya". A name
// in Latin letters is read the English way into Cyrillic (Mike -> майк, Nick -> ник, Tony -> тони, Sergei -> сергей, Buddy ->
// бадди, бади), one in Cyrillic into Latin as names are written (Коля -> kolya, kolia; Михалыч -> mikhalych). A few forms, lower
// case (MemoryNorm: ё as е), the word itself not among them; a word of other letters or of both alphabets: none
std::vector<std::string> NameInOtherAlphabet(const std::string& word) {
    std::u32string w;
    bool latin = true, cyrillic = true;
    for (char32_t c : coop::DecodeUtf8(coop::MemoryNorm(word))) {
        switch (c) {   // Spanish letters as plain ones
        case U'á': c = U'a'; break;
        case U'é': c = U'e'; break;
        case U'í': c = U'i'; break;
        case U'ó': c = U'o'; break;
        case U'ú': case U'ü': c = U'u'; break;
        default: break;
        }
        latin = latin && ((c >= U'a' && c <= U'z') || c == U'ñ');
        cyrillic = cyrillic && ((c >= U'а' && c <= U'я') || c == U'ё');
        w += c;
    }
    if (w.size() < 2 || latin == cyrillic) return {};
    // the word as pieces, each with its forms (the first the usual one)
    using Forms = std::vector<std::u32string>;
    std::vector<Forms> pieces;
    const size_t n = w.size();
    auto at = [&](size_t i) { return i < n ? w[i] : char32_t(0); };
    size_t i = 0;
    auto put = [&](Forms forms, size_t len) {
        pieces.push_back(std::move(forms));
        i += len;
    };
    if (latin) {
        auto vowel = [](char32_t c) { return c == U'a' || c == U'e' || c == U'i' || c == U'o' || c == U'u' || c == U'y'; };
        auto letter = [&](size_t k) -> std::u32string {   // one letter as it is usually said
            const char32_t c = w[k], d = at(k + 1);
            switch (c) {
            case U'a': return U"а";
            case U'b': return U"б";
            case U'c': return d == U'e' || d == U'i' || d == U'y' ? U"с" : U"к";
            case U'd': return U"д";
            case U'e': return k == 0 ? U"э" : U"е";
            case U'f': return U"ф";
            case U'g': return U"г";
            case U'h': return U"х";
            case U'i': return U"и";
            case U'j': return U"дж";
            case U'k': return U"к";
            case U'l': return U"л";
            case U'm': return U"м";
            case U'n': return U"н";
            case U'ñ': return U"нь";
            case U'o': return U"о";
            case U'p': return U"п";
            case U'q': return U"к";
            case U'r': return U"р";
            case U's': return U"с";
            case U't': return U"т";
            case U'u': return U"у";
            case U'v': return U"в";
            case U'w': return vowel(d) ? U"у" : U"в";
            case U'x': return U"кс";
            case U'y': return U"и";
            case U'z': return U"з";
            default: return U"";
            }
        };
        // a final e that makes the vowel before it long (Mike, Jake, Steve, Luke, Kyle) is not said
        const bool silent_e = n >= 3 && w[n - 1] == U'e' && !vowel(w[n - 2]) && vowel(w[n - 3]) && (n == 3 || !vowel(w[n - 4]));
        while (i < n) {
            const char32_t c = w[i], d = at(i + 1), e = at(i + 2);
            const bool pair_ends = i + 2 == n;
            auto two = [&](const char32_t* s) { return c == s[0] && d == s[1]; };
            if (silent_e && i == n - 1) break;
            if (silent_e && i == n - 3) {
                put(c == U'a' ? Forms{U"ей"} : c == U'e' ? Forms{U"и"} : c == U'i' || c == U'y' ? Forms{U"ай"} : c == U'o' ? Forms{U"оу", U"о"} : Forms{U"ю", U"у"}, 1);
            } else if (c == U's' && d == U'c' && e == U'h') {
                put({U"ш"}, 3);
            } else if (c == U't' && d == U'c' && e == U'h') {
                put({U"ч"}, 3);
            } else if (two(U"sh")) {
                put({U"ш"}, 2);
            } else if (two(U"ch")) {
                put({U"ч", U"к"}, 2);
            } else if (two(U"zh")) {
                put({U"ж"}, 2);
            } else if (two(U"kh")) {
                put({U"х"}, 2);
            } else if (two(U"th")) {
                put({U"т"}, 2);
            } else if (two(U"ph")) {
                put({U"ф"}, 2);
            } else if (two(U"ck")) {
                put({U"к"}, 2);
            } else if (two(U"qu")) {
                put({U"кв"}, 2);
            } else if (two(U"gh")) {
                put({U"г"}, 2);
            } else if (two(U"wh")) {
                put({U"у"}, 2);
            } else if (c == U'g' && d == U'u' && (e == U'e' || e == U'i')) {
                put({U"г"}, 2);   // Miguel
            } else if (two(U"ee") || two(U"ea")) {
                put({U"и"}, 2);
            } else if (two(U"oo")) {
                put({U"у"}, 2);
            } else if (two(U"ai") || two(U"ay") || two(U"ei")) {
                put({U"ей"}, 2);
            } else if (two(U"ey")) {
                put(pair_ends ? Forms{U"и", U"ей"} : Forms{U"ей"}, 2);   // Mickey; Sergey
            } else if (two(U"ie")) {
                put({U"и"}, 2);
            } else if (two(U"ou")) {
                put({U"у"}, 2);
            } else if (two(U"au") || two(U"aw")) {
                put({U"о"}, 2);
            } else if (two(U"ow")) {
                put({pair_ends ? U"оу" : U"ау"}, 2);
            } else if (two(U"oy")) {
                put({U"ой"}, 2);
            } else if (c == U'y' && (d == U'a' || d == U'u' || d == U'o' || d == U'e') && (i == 0 || !vowel(at(i - 1)))) {
                // Kolya, Yuri, Fyodor, Yelena
                put(d == U'a' ? Forms{U"я"} : d == U'u' ? Forms{U"ю"} : d == U'o' ? Forms{U"ё", U"йо"} : Forms{U"е", U"йе"}, 2);
            } else if (c == U'ñ' && vowel(d)) {
                put(d == U'a' ? Forms{U"нья"} : d == U'o' ? Forms{U"ньо"} : d == U'u' ? Forms{U"нью"} : d == U'e' ? Forms{U"нье"} : Forms{U"ньи"}, 2);
            } else if (c == d && !vowel(c)) {
                const std::u32string one = letter(i + 1);   // Buddy: бадди, бади; Otto: отто, ото
                put({one + one, one}, 2);
            } else if (c == U'u' && d && !vowel(d) && (!e || !vowel(e))) {
                put({U"а", U"у"}, 1);   // u in a closed syllable: Buddy, Duncan
            } else if (c == U'y') {
                const bool first = i == 0, last = i + 1 == n, after_vowel = i > 0 && vowel(at(i - 1));
                put(first && vowel(d) ? Forms{U"й"} : last ? Forms{U"и"} : after_vowel ? Forms{U"й"} : Forms{U"и", U"ы"}, 1);   // Tony; Mikhalych
            } else {
                const std::u32string one = letter(i);
                put({one}, 1);
            }
        }
    } else {
        while (i < n) {
            const char32_t c = w[i], d = at(i + 1);
            switch (c) {
            case U'а': put({U"a"}, 1); break;
            case U'б': put({U"b"}, 1); break;
            case U'в': put({U"v"}, 1); break;
            case U'г': put({U"g"}, 1); break;
            case U'д': put({U"d"}, 1); break;
            case U'е': put(i == 0 ? Forms{U"e", U"ye"} : Forms{U"e"}, 1); break;
            case U'ё': put({U"yo", U"e"}, 1); break;
            case U'ж': put({U"zh"}, 1); break;
            case U'з': put({U"z"}, 1); break;
            case U'и': put({U"i"}, 1); break;
            case U'й': put({U"y", U"i"}, 1); break;
            case U'к': d == U'с' ? put({U"ks", U"x"}, 2) : put({U"k"}, 1); break;
            case U'л': put({U"l"}, 1); break;
            case U'м': put({U"m"}, 1); break;
            case U'н': put({U"n"}, 1); break;
            case U'о': put({U"o"}, 1); break;
            case U'п': put({U"p"}, 1); break;
            case U'р': put({U"r"}, 1); break;
            case U'с': put({U"s"}, 1); break;
            case U'т': put({U"t"}, 1); break;
            case U'у': put({U"u"}, 1); break;
            case U'ф': put({U"f"}, 1); break;
            case U'х': put({U"kh", U"h"}, 1); break;
            case U'ц': put({U"ts"}, 1); break;
            case U'ч': put({U"ch"}, 1); break;
            case U'ш': put({U"sh"}, 1); break;
            case U'щ': put({U"shch"}, 1); break;
            case U'ы': put({U"y"}, 1); break;
            case U'э': put({U"e"}, 1); break;
            case U'ю': put({U"yu"}, 1); break;
            case U'я': put({U"ya", U"ia"}, 1); break;
            default: put({U""}, 1); break;   // ъ, ь
            }
        }
    }
    // the usual reading, then that reading with one piece in another of its forms, then every piece in its second form
    std::vector<std::string> out;
    const std::string self = coop::MemoryNorm(word);
    auto add = [&](const std::u32string& s) {
        const std::string x = coop::MemoryNorm(coop::EncodeUtf8(s));
        if (!x.empty() && x != self && std::find(out.begin(), out.end(), x) == out.end()) out.push_back(x);
    };
    std::u32string usual, second;
    for (const Forms& p : pieces) usual += p[0], second += p.size() > 1 ? p[1] : p[0];
    add(usual);
    for (size_t k = 0; k < pieces.size() && out.size() < 6; ++k)
        for (size_t f = 1; f < pieces[k].size(); ++f) {
            std::u32string s;
            for (size_t j = 0; j < pieces.size(); ++j) s += j == k ? pieces[j][f] : pieces[j][0];
            add(s);
        }
    add(second);
    return out;
}

// whether a word of a line (MemoryNorm'd) is a word of a name (MemoryNorm'd) as said in any case: the same, one letter off (4+
// letters: a recognizer's slip), or (Cyrillic) its stem with a case's ending («Колю», «Коле», «Колей» for «Коля»; «Майку»,
// «Майком» for «Майк»; «Михалыча» for «Михалыч»; «Сергею» for «Сергей»; «Лео», «Тони» do not decline); (Latin) "Nick's"
bool NameWordIn(const std::string& said, const std::string& name) {
    if (said == name) return true;
    const std::u32string a = coop::DecodeUtf8(said), b = coop::DecodeUtf8(name);
    if (b.size() < 3 || a.empty()) return false;
    if (a.size() == b.size() && b.size() >= 4) {
        size_t diff = 0;
        for (size_t k = 0; k < a.size(); ++k) diff += a[k] != b[k];
        if (diff <= 1) return true;
    }
    const char32_t last = b.back();
    if (!(last >= U'а' && last <= U'я')) return a == b + U"s" || a == b + U"'s";
    std::u32string stem = b;
    if (last == U'а' || last == U'я' || last == U'й' || last == U'ь') stem.pop_back();
    else if (last == U'о' || last == U'е' || last == U'и' || last == U'у' || last == U'ю' || last == U'э' || last == U'ы') return false;
    if (a.size() < stem.size() || a.compare(0, stem.size(), stem) != 0) return false;
    static const std::set<std::u32string> kEnding = {U"",   U"а",  U"я",  U"у",  U"ю",  U"е",  U"и",  U"ы",
                                                     U"ой", U"ей", U"ою", U"ею", U"ом", U"ем", U"й",  U"ь"};
    return kEnding.count(a.substr(stem.size())) > 0;
}

// a Russian name in a case: 'd' dative («Иду к Коле», «к Майку», «к Михалычу»), 'i' instrumental («Иду за Колей», «за Михалычем»);
// a name of several words word by word («баба Валя» -> «бабе Вале»); one that does not decline (Лео, Отто, Тони, Бади) or is in
// Latin letters as it is
std::string RussianNameIn(const std::string& name, char kase) {
    std::string out;
    size_t from = 0;
    while (from <= name.size()) {
        size_t to = name.find(' ', from);
        if (to == std::string::npos) to = name.size();
        std::u32string w = coop::DecodeUtf8(name.substr(from, to - from));
        if (!w.empty()) {
            const auto low = [](char32_t c) { return c >= U'А' && c <= U'Я' ? char32_t(c + 0x20) : c == U'Ё' ? U'ё' : c; };
            const char32_t last = low(w.back()), before = w.size() >= 2 ? low(w[w.size() - 2]) : 0;
            const auto hush = [](char32_t c) { return c == U'ж' || c == U'ш' || c == U'ч' || c == U'щ' || c == U'ц'; };
            const bool consonant = last >= U'а' && last <= U'я' && std::u32string(U"аеиоуыэюяйь").find(last) == std::u32string::npos;
            std::u32string stem = w.substr(0, w.size() - 1);
            if (last == U'а') w = stem + (kase == 'd' ? U"е" : hush(before) ? U"ей" : U"ой");
            else if (last == U'я') w = stem + (kase == 'd' ? (before == U'и' ? U"и" : U"е") : U"ей");
            else if (last == U'й' || last == U'ь') w = stem + (kase == 'd' ? U"ю" : U"ем");
            else if (consonant) w += kase == 'd' ? U"у" : hush(last) ? U"ем" : U"ом";
            out += (out.empty() ? "" : " ") + coop::EncodeUtf8(w);
        }
        from = to + 1;
    }
    return out;
}

// The one a line calls by name (2026-11-12, the owner: «если он стоит рядом, просто я обращаюсь по имени, то нужно, чтобы система
// поняла, к какому из персонажей я обращаюсь, в том числе и мой бот»). callees: the game's, nearest first: [{"to": "bot" or a
// role, "key": the game's id of them, "names": [...], "far": true when they are out of earshot}]. A name is called as
// CalledBy reads it (at the line's start or its end: «Фёдор, иди за мной», «Эй, Анна, ...», «иди сюда, Рекс»); a name of
// several words by its last word too («баба Валя»: «Валя, ...»); each heard in the other alphabet too (NameInOtherAlphabet:
// «Майк» for Mike). The bot answers to the name the player gave it (bot_name), the game's and its role's in every language.
// A name at the line's start calls, whoever of the callees it is, before any at its end (2026-11-15: «Майк, иди к Нику» is Mike's
// line; the other names in it are whom the order is about); *rest: the line without the name
struct ActOn;
bool ActVerb(const std::string& x, const std::string& next, ActOn* out);
enum class Going { None, Go, Follow, Stay, Reach };
Going GoVerb(const std::string& x);
struct Callee {
    std::string to, key, name;
    bool distant = false;   // "far": out of earshot ("far" and "near" are macros of windows.h)
};
// every name a callee answers to: the game's, the bot's own, the last word of a name of several, each in the other alphabet
std::vector<std::string> CalleeNames(const json& c, const std::string& bot_name) {
    std::vector<std::string> names;
    const std::string to = c.value("to", std::string());
    if (c.contains("names") && c["names"].is_array())
        for (const json& n : c["names"])
            if (n.is_string() && !n.get<std::string>().empty()) names.push_back(n.get<std::string>());
    if (to == "bot") {
        if (!bot_name.empty()) names.push_back(bot_name);
        if (g_talk && g_talk->roles.count("bot"))
            for (const auto& [lang, n] : g_talk->roles.at("bot").names) names.push_back(n);
    }
    const size_t given = names.size();
    for (size_t k = 0; k < given; ++k) {
        const std::vector<std::string> w = coop::MemoryWords(coop::MemoryNorm(names[k]));
        if (w.size() > 1 && coop::DecodeUtf8(w.back()).size() >= 3) names.push_back(w.back());
    }
    const size_t own = names.size();
    for (size_t k = 0; k < own; ++k) {
        const std::vector<std::string> w = coop::MemoryWords(coop::MemoryNorm(names[k]));
        if (w.size() == 1) {
            for (const std::string& v : NameInOtherAlphabet(w[0])) names.push_back(v);
        } else if (!w.empty()) {
            std::string all;   // a name of several words: their usual forms together («doña Valentina» -> «донья валентина»)
            for (const std::string& x : w) {
                const std::vector<std::string> v = NameInOtherAlphabet(x);
                if (v.empty()) {
                    all.clear();
                    break;
                }
                all += (all.empty() ? "" : " ") + v[0];
            }
            if (!all.empty()) names.push_back(all);
        }
    }
    // the familiar form a Russian first name has in the street (2026-11-15, the owner's log: «втащи коляну» named nobody): Коля ->
    // Колян, Толик / Толя -> Толян, Валя -> Валян; its cases are read as any name's (NameWordIn)
    const size_t with_alphabets = names.size();
    for (size_t k = 0; k < with_alphabets; ++k) {
        const std::vector<std::string> w = coop::MemoryWords(coop::MemoryNorm(names[k]));
        if (w.size() != 1) continue;
        const std::u32string u = coop::DecodeUtf8(w[0]);
        std::u32string stem;
        if (u.size() >= 4 && u.back() == U'я') stem = u.substr(0, u.size() - 1);
        else if (u.size() >= 5 && u.compare(u.size() - 2, 2, U"ик") == 0) stem = u.substr(0, u.size() - 2);
        if (stem.size() >= 3) names.push_back(coop::EncodeUtf8(stem + U"ян"));
    }
    // a patronymic as the street says it (Михалыч, Иваныч, Палыч, Сергеич) is heard as the full one too, and the one of six letters or
    // more as the first name it comes from (2026-11-15, the owner's log: «Михаилович, встань возле этой стенки», «застрели Михайловича»,
    // «Михаил, иди сюда» were said to Михалыч and called nobody): the stem and «ович» (after a vowel «евич»), with a й, и or в before
    // the stem's last л as the full name has it (Михал- -> Михайл-, Михаил-; Пал- -> Павл-). Кузьмич, Ильич (no vowel before «ич»)
    // are names of their own
    const size_t with_street = names.size();
    for (size_t k = 0; k < with_street; ++k) {
        const std::vector<std::string> w = coop::MemoryWords(coop::MemoryNorm(names[k]));
        if (w.size() != 1) continue;
        const std::u32string u = coop::DecodeUtf8(w[0]);
        if (u.size() < 5) continue;
        const bool yc = u.compare(u.size() - 2, 2, U"ыч") == 0, ic = u.compare(u.size() - 2, 2, U"ич") == 0;
        if (!yc && !ic) continue;
        const std::u32string stem = u.substr(0, u.size() - 2);
        const bool vowel = std::u32string(U"аеиоуэюяы").find(stem.back()) != std::u32string::npos;
        if (ic && !vowel) continue;
        const std::u32string suffix = vowel ? U"евич" : U"ович";
        std::vector<std::u32string> stems = {stem};
        if (stem.back() == U'л')
            for (const char32_t ins : {U'й', U'и', U'в'}) stems.push_back(stem.substr(0, stem.size() - 1) + ins + U"л");
        for (const std::u32string& x : stems) {
            names.push_back(coop::EncodeUtf8(x + suffix));
            if (x != stem && x.size() >= 6) names.push_back(coop::EncodeUtf8(x));   // Михаил
        }
    }
    std::vector<std::string> out;
    std::unordered_set<std::string> seen;
    for (const std::string& n : names)
        if (const std::string k = coop::MemoryNorm(n); !k.empty() && seen.insert(k).second) out.push_back(n);
    return out;
}
bool CalledCallee(const std::string& heard, const json& callees, const std::string& bot_name, Callee* out, std::string* rest) {
    if (!callees.is_array()) return false;
    const std::vector<coop::SpanWord> sw = coop::SpanWords(heard);
    std::vector<std::string> hw;
    for (const coop::SpanWord& s : sw) hw.push_back(s.norm);
    for (int pass = 0; pass < 2; ++pass)   // the start first, of every callee; then the end
        for (const json& c : callees) {
            if (!c.is_object()) continue;
            const std::string to = c.value("to", std::string());
            if (to.empty()) continue;
            for (const std::string& n : CalleeNames(c, bot_name)) {
                std::string r;
                bool at_start = false;
                if (!coop::CalledBy(heard, n, &r, &at_start) || at_start != (pass == 0)) continue;
                const std::vector<std::string> nw = coop::MemoryWords(coop::MemoryNorm(n));
                if (nw.empty() || hw.empty()) continue;
                static const std::unordered_set<std::string> kHey = {"эй", "ей", "слушай", "ну", "так", "а", "ладно", "окей", "hey", "yo", "oi",
                                                                     "so", "now", "listen", "ok", "okay", "alright", "oye", "mira", "bueno", "vale"};
                const size_t first = kHey.count(hw[0]) && hw.size() > 1 ? 1 : 0;
                if (at_start) {
                    // «ударь Колю», "make fun of him" ~ "Mike": a verb of acting on someone at the start is the verb, not a name
                    if (ActVerb(hw[first], first + 1 < hw.size() ? hw[first + 1] : std::string(), nullptr)) continue;
                } else {
                    // the name at the end after a word that asks about them is a question about them, not a call: «где Фёдор?»,
                    // "where's Anna?", «¿dónde está Ana?», «кто такой Лео» (CalledBy already leaves out «к Фёдору», «это Анна»)
                    static const std::unordered_set<std::string> kAbout = {
                        "где", "кто", "куда", "откуда", "чей", "чья", "чье", "чьи", "такой", "такая", "вот", "where", "wheres", "who",
                        "whos", "is", "was", "about", "donde", "dónde", "quien", "quién", "esta", "está", "es"};
                    if (hw.size() > nw.size() && kAbout.count(hw[hw.size() - nw.size() - 1])) continue;
                    // ... and a name at the end in another case than the one it is called in is whom the line is about: «ударь Колю»,
                    // «стреляй в Михалыча» (2026-11-14); a call says the name as it is («иди сюда, Коля»)
                    if (hw.back() != nw.back()) {
                        const std::u32string said = coop::DecodeUtf8(hw.back()), own = coop::DecodeUtf8(nw.back());
                        if (said.size() >= 3 && own.size() >= 3 && said.substr(0, own.size() - 1) == own.substr(0, own.size() - 1)) continue;
                    }
                    // "shoot Nick", «пристрели Колю», "follow Mike", "approach Tony" (2026-11-14, 11-15): the name after a verb of
                    // acting on someone (anywhere in the line) or of going (just before it) is whom it is done to, unless a comma
                    // sets it apart ("Shoot him, Nick.": Nick is called)
                    const size_t from = sw.size() - nw.size();
                    bool comma = false;
                    for (size_t b = from > 0 ? sw[from - 1].end : 0; from > 0 && b < sw[from].begin && !comma; ++b) comma = heard[b] == ',';
                    if (!comma) {
                        bool object = false;
                        for (size_t k = 0; k < from && !object; ++k)
                            object = ActVerb(hw[k], k + 1 < hw.size() ? hw[k + 1] : std::string(), nullptr) ||
                                     (k + 3 >= from && GoVerb(hw[k]) != Going::None);
                        if (object) continue;
                    }
                }
                out->to = to;
                out->key = c.value("key", to);
                out->name = n;
                out->distant = c.value("far", false);
                *rest = r;
                return true;
            }
        }
    return false;
}

// ---- acting on someone (2026-11-14, the owner: «чтобы мой бот мог дамажить. Вообще все могли дамажить друг друга, если я это
// приказываю ... Бить руками, стрелять, издеваться, направлять»; his choices: the player as a target too, «издеваться» = taunt with
// words and gestures, «направлять» = aim at without firing). The classifier reads some of these lines well («ударь его» MELEE,
// «стреляй в него» OPEN_FIRE) and some not at all («ударь меня» HELP, «пристрели Колю» "take out cole" SWITCH_WEAPON, «целься в
// него» OPEN_FIRE, «подразни его» DEFUSE), and none says WHOM to the game. The player's own words say both: a verb of one of four
// kinds and whom: me (the speaker), him / her (the one named before it in the line, else the one under the crosshair), the bot,
// a person of the level by name in any case. The order then carries "target": {"kind": "speaker" | "pointed" | "bot" | "person",
// "key": the game's key of them, "name": as they are called}; hit = MELEE, shoot = OPEN_FIRE, aim = AIM_AT, taunt = TAUNT (the
// last two are the game's, not the classifier's). Going to someone and following them (2026-11-15, ReadGoTo) are read alike
struct ActOn {
    std::string kind;     // "hit", "shoot", "aim", "taunt"; "go", "follow"
    std::string intent;   // MELEE, OPEN_FIRE, AIM_AT, TAUNT; MOVE_TO, FOLLOW_ME
    std::string english;  // the words for it (the reply tables have them)
    bool once = false;    // «ударь», "punch": one strike; «избей», «бей», "beat up": until they are down
    json target;
    size_t clause = 0, clauses = 1;   // the line's part it is in, of how many (split at «и», «потом», "and", "then")
    size_t verb_at = 0;   // its verb's word in the line (the turns made of the words go in their order: RebuildTurns)
};
// «по щам», «по морде», «в морду», «в табло»: a strike said by where it lands (2026-11-15, the owner: «вот он ... дай ему по щам»;
// the recognizer heard «да тайму по щам»): w[i] is the place it lands with «по» / «в» before it
bool StrikeByFace(const std::vector<std::string>& w, size_t i) {
    static const std::unordered_set<std::string> kFace = {"щам", "щщам", "щи", "морде", "морду", "роже", "рожу", "харе", "харю", "табло",
                                                          "рылу", "рыло", "башке", "башку", "лицу", "зубам", "сопатке", "сусалам", "мордасам"};
    return i > 0 && kFace.count(w[i]) && (w[i - 1] == "по" || w[i - 1] == "в");
}
// whether a word (MemoryNorm'd; next: the word after it) is a verb of acting on someone, and which (into *out, when given)
bool ActVerb(const std::string& x, const std::string& next, ActOn* out) {
    auto starts = [&x](std::initializer_list<const char*> stems) {
        for (const char* st : stems)
            if (x.rfind(st, 0) == 0) return true;
        return false;
    };
    const char *kind = nullptr, *intent = nullptr, *english = nullptr;
    if (starts({"дразн", "подразн", "издева", "поиздева", "высме", "оскорб", "обзов", "посмейся", "tease", "mock", "taunt", "insult", "burla",
                "insulta"}) || (x == "make" && next == "fun"))
        kind = "taunt", intent = "TAUNT", english = "Copy.";
    else if (x == "целься" || x == "прицелься" || x == "целись" || starts({"навед", "наведи", "направь", "aim", "apunta"}) ||
             (x == "point" && (next == "at" || next == "your" || next == "the" || next == "a" || next == "gun")))
        kind = "aim", intent = "AIM_AT", english = "Eyes on it.";
    // turning to look at someone (2026-11-15, the owner's log: «развернись к бабе Вале»): with «к» / «на» after it
    else if ((starts({"развернись", "повернись", "обернись", "посмотри", "глянь", "взгляни", "уставься"}) &&
              (next == "к" || next == "ко" || next == "на")) ||
             (x == "look" && next == "at") || (x == "turn" && (next == "to" || next == "towards")) || x == "face" ||
             ((x == "mira" || x == "gírate" || x == "girate") && (next == "a" || next == "al" || next == "hacia")))
        kind = "look", intent = "LOOK_AT", english = "Eyes on it.";
    // (2026-11-15, the owner's log: «расстреляй бабу Валю», «втащи Толику», «замочи», «дай ему по щам» were not read: the
    // decoder wrote "Smack Toli." and the classifier SMOKE)
    else if (starts({"стреля", "стрельни", "пристрел", "застрел", "подстрел", "выстрел", "расстрел", "постреля", "обстреля", "пальни",
                     "шмальни", "шмаляй", "убей", "убейте", "убить", "замочи", "мочи", "грохни", "прикончи", "добей", "ликвидируй",
                     "устрани", "уничтожь", "пришей", "shoot", "kill", "dispara", "mata"}) ||
             // «открыть огонь в Михайловиче», «огонь по Михалычу», "fire at Nick" (2026-11-15, the owner's log)
             (x == "огонь" && (next == "по" || next == "в" || next == "на")) || (x == "fire" && (next == "at" || next == "on")))
        kind = "shoot", intent = "OPEN_FIRE", english = "Opening fire!";
    else if (x == "удар" || starts({"ударь", "ударить", "бей", "побей", "избей", "избить", "врежь", "вмажь", "вдарь", "стукни", "тресни", "пни",
                                    "отпинай", "отлупи", "двинь", "втащи", "втащите", "вломи", "влепи", "залепи", "засвети", "накостыляй",
                                    "наваляй", "отметель", "отмудохай", "отпизди", "въеби", "уеби", "ебни", "ёбни", "hit", "punch", "beat",
                                    "kick", "smack", "slap", "whack", "bash", "deck", "golpea", "pega", "patea"}))
        kind = "hit", intent = "MELEE", english = "Going hands-on.";
    else
        return false;
    if (out) {
        out->kind = kind, out->intent = intent, out->english = english;
        out->once = out->kind == "hit" && !starts({"бей", "побей", "избей", "избить", "отлупи", "отпинай", "beat", "golpea"});
    }
    return true;
}

// whether a word says going somewhere (Go: «иди», "go", «ve»), following (Follow: «следуй», "follow", «sigue»), staying by
// (Stay: «встань», "stand", «quédate») or coming up to whom it names (Reach: «догони», "approach")
Going GoVerb(const std::string& x) {
    static const std::unordered_set<std::string> kGo = {
        "иди", "идите", "пойди", "пойдите", "подойди", "подойдите", "подходи", "подходите", "сходи", "сходите", "ступай", "ступайте", "беги",
        "бегите", "побеги", "подбеги", "подбегите", "сбегай", "двигай", "двигайся", "двигайтесь", "направляйся", "направляйтесь", "шагай",
        "топай", "дуй", "вали", "чеши", "отправляйся", "ползи", "подползи", "приблизься", "приблизьтесь", "пройди", "пройдите", "вернись",
        "вернитесь", "возвращайся", "идти", "пойти", "подойти", "сходить", "подбежать", "двигаться", "езжай", "поезжай", "подъедь",
        "подъезжай", "go", "walk", "run", "head", "move", "come", "get", "proceed", "sprint", "crawl", "hurry", "rush", "return", "drive",
        "step", "ve", "vaya", "vayan", "id", "anda", "camina", "corre", "acércate", "acercate", "ven", "dirígete", "dirigete", "vuelve",
        "regresa", "muévete", "muevete"};
    static const std::unordered_set<std::string> kFollow = {
        "следуй", "следуйте", "проследуй", "ходи", "ходите", "сопровождай", "сопроводи", "проводи", "преследуй", "следовать", "сопровождать",
        "follow", "escort", "tail", "shadow", "chase", "accompany", "sigue", "siga", "acompaña", "acompana", "escolta", "persigue"};
    static const std::unordered_set<std::string> kStay = {
        "встань", "встаньте", "стань", "стой", "стойте", "постой", "жди", "ждите", "подожди", "подождите", "будь", "оставайся", "останься",
        "держись", "stand", "stay", "wait", "keep", "remain", "quédate", "quedate", "espera"};
    static const std::unordered_set<std::string> kReach = {"догони", "догоните", "approach", "reach", "catch"};
    if (kGo.count(x)) return Going::Go;
    if (kFollow.count(x)) return Going::Follow;
    if (kStay.count(x)) return Going::Stay;
    if (kReach.count(x)) return Going::Reach;
    return Going::None;
}

// a word that is no thing and nobody: a preposition, a conjunction, a particle, "there", "now", "fast" («втащи тому по морде», «убей
// этого быстро», «застрели, давай»)
bool SmallWord(const std::string& x) {
    static const std::unordered_set<std::string> kSmall = {
        "по", "в", "во", "на", "с", "со", "за", "из", "у", "к", "ко", "от", "до", "и", "а", "но", "или", "потом", "затем", "кто", "что",
        "который", "которая", "которое", "которые", "там", "тут", "здесь", "вон", "вот", "сейчас", "быстро", "скорее", "живо", "уже",
        "тоже", "еще", "ещё", "пожалуйста", "нахрен", "нафиг", "нахер", "наконец", "сразу", "давай", "давайте", "ну", "же", "ж", "бы",
        "ли", "блин", "брат", "братан", "then", "and", "now", "too", "please", "right", "there", "here", "again", "quick", "quickly",
        "fast", "already", "y", "ahora", "también", "tambien", "ya", "por", "favor", "rápido", "rapido", "ahí", "ahi", "allí", "alli"};
    return kSmall.count(x) > 0;
}
// The ones a line names, each where it is in its words (MemoryNorm'd): a person of the level or the bot by any of their names in
// any case («Колю», «Майку», "Nick's"), «бота», me, him / her
struct Mention {
    size_t at = 0;
    json target;
    bool pronoun = false;   // him, her, them: the one named before it in the line (Resolved), else the one under the crosshair
};
std::vector<Mention> Mentions(const std::vector<std::string>& w, const json& callees, const std::string& bot_name) {
    std::vector<std::pair<const json*, std::vector<std::pair<std::string, std::string>>>> named;   // a callee: (name's word, name)
    // ... and their names of several words, whole: (the words, name)
    std::vector<std::pair<const json*, std::vector<std::pair<std::vector<std::string>, std::string>>>> named_whole;
    if (callees.is_array())
        for (const json& c : callees) {
            if (!c.is_object() || c.value("to", std::string()).empty()) continue;
            // a name the line said in the other alphabet («Майк») is theirs as the game gives it (Mike)
            std::vector<std::string> given;
            if (c.contains("names") && c["names"].is_array())
                for (const json& g : c["names"])
                    if (g.is_string() && !g.get<std::string>().empty()) given.push_back(g.get<std::string>());
            std::vector<std::pair<std::string, std::string>> words;
            std::vector<std::pair<std::vector<std::string>, std::string>> whole;
            for (const std::string& n : CalleeNames(c, bot_name)) {
                const std::vector<std::string> nw = coop::MemoryWords(coop::MemoryNorm(n));
                const bool own = given.empty() || std::find(given.begin(), given.end(), n) != given.end() || n == bot_name;
                if (!nw.empty() && coop::DecodeUtf8(nw.back()).size() >= 3) words.push_back({nw.back(), own ? n : given[0]});
                if (nw.size() > 1) whole.push_back({nw, own ? n : given[0]});
            }
            named.push_back({&c, std::move(words)});
            named_whole.push_back({&c, std::move(whole)});
        }
    static const std::unordered_set<std::string> kBot = {"бот", "бота", "боту", "ботом", "боте", "робот", "робота", "роботу", "роботом",
                                                         "роботе", "bot", "robot", "bot's", "robot's"};
    static const std::unordered_set<std::string> kMe = {"меня", "мне", "мной", "мною", "me", "mí", "mi", "myself", "conmigo"};
    // (2026-11-15: «вот он, ... дай ему по щам»: he as said; «втащи там парню», «втащи тому деду»: a man, an old man, that one, as
    // the one under the crosshair)
    static const std::unordered_set<std::string> kHim = {"его", "него", "её", "неё", "ее", "нее", "ему", "нему", "ей", "ней", "им", "ним",
                                                         "ими", "ними", "их", "них", "этого", "этому", "этим", "эту", "этот", "этих",
                                                         "он", "она", "они", "того", "тому", "той", "ту", "парню", "парня", "парнем",
                                                         "мужику", "мужика", "мужиком", "чуваку", "чувака", "пацану", "пацана", "деду",
                                                         "деда", "дедом", "старику", "старика", "бабке", "бабку", "тётке", "тётку",
                                                         "тетке", "тетку", "человеку", "человека", "урода", "уроду",
                                                         "гада", "гаду", "козла", "козлу", "придурка", "придурку", "дядьку",
                                                         "дядьке", "дядю", "дяде", "мужчину", "мужчине", "женщину", "женщине",
                                                         "девушку", "девушке", "бабулю", "бабуле", "старушку", "старушке",
                                                         "рабочего", "рабочему", "охранника", "охраннику", "продавца", "продавцу",
                                                         "guy", "man", "woman", "dude", "lady", "fellow", "him",
                                                         "her", "them", "that", "this", "lo", "la", "le", "les", "ese", "este", "esa", "esta",
                                                         "él", "ella"};
    // «встань возле той стенки», «повернись к той стене», "go to that wall" (2026-11-15, the owner's log: the bot turned to Михалыч,
    // not to the wall): a demonstrative before a word that is no person, no verb and no small word is that thing's, not him / her
    static const std::unordered_set<std::string> kDemo = {"этого", "этому", "этим", "эту", "этот", "этих", "этой", "того", "тому", "той", "ту",
                                                          "тот", "that", "this", "ese", "este", "esa", "esta"};
    auto of_a_thing = [&](size_t i) {
        if (!kDemo.count(w[i]) || i + 1 >= w.size()) return false;
        const std::string& x = w[i + 1];
        return !kHim.count(x) && !kMe.count(x) && !kBot.count(x) && !SmallWord(x) && GoVerb(x) == Going::None &&
               !ActVerb(x, i + 2 < w.size() ? w[i + 2] : std::string(), nullptr);
    };
    std::vector<Mention> out;
    auto person = [](const json* c, const std::string& n) {
        const std::string to = c->value("to", std::string());
        return to == "bot" ? json{{"kind", "bot"}, {"name", n}} : json{{"kind", "person"}, {"key", c->value("key", to)}, {"to", to}, {"name", n}};
    };
    for (size_t i = 0; i < w.size(); ++i) {
        // a name of several words said whole, in any case («бабе Вале»), misheard («баби Вале») or run together by the recognizer
        // («бабували»): theirs before a word of it is read as another's (2026-11-15, the owner's log: «развернись к баби Вале» went
        // to nobody, «баби» being a letter off «Бади», the bot's name). Where it is: its last word, as for a name said in part
        size_t whole_end = 0;
        for (const auto& [c, names] : named_whole) {
            for (const auto& [nw, n] : names) {
                bool all = i + nw.size() <= w.size();
                for (size_t j = 0; j < nw.size() && all; ++j) all = NameWordIn(w[i + j], nw[j]);
                if (all) whole_end = i + nw.size();
                if (!all && nw.size() == 2) {
                    const std::u32string u = coop::DecodeUtf8(w[i]);
                    for (size_t cut = 3; cut + 3 <= u.size() && !whole_end; ++cut)
                        if (NameWordIn(coop::EncodeUtf8(u.substr(0, cut)), nw[0]) && NameWordIn(coop::EncodeUtf8(u.substr(cut)), nw[1])) whole_end = i + 1;
                }
                if (whole_end) {
                    out.push_back({whole_end - 1, person(c, n)});
                    break;
                }
            }
            if (whole_end) break;
        }
        if (whole_end) {
            i = whole_end - 1;
            continue;
        }
        bool found = false;
        for (const auto& [c, words] : named) {
            for (const auto& [word, n] : words)
                if (NameWordIn(w[i], word)) {
                    out.push_back({i, person(c, n)});
                    found = true;
                    break;
                }
            if (found) break;
        }
        if (found) continue;
        if (kBot.count(w[i])) out.push_back({i, {{"kind", "bot"}}});
        else if (kMe.count(w[i])) out.push_back({i, {{"kind", "speaker"}}});
        else if (kHim.count(w[i]) && !of_a_thing(i)) out.push_back({i, {{"kind", "pointed"}}, true});
    }
    return out;
}
// whom a mention stands for: him is the one named last before him in the line («иди к Коле и ударь его»: Коля), else as it is
json Resolved(const std::vector<Mention>& ms, size_t k) {
    if (!ms[k].pronoun) return ms[k].target;
    for (size_t j = k; j-- > 0;) {
        const std::string kind = ms[j].target.value("kind", std::string());
        if (!ms[j].pronoun && (kind == "person" || kind == "bot")) return ms[j].target;
    }
    return ms[k].target;
}
// the line's parts, a part a word (at «и», «а», «потом», «затем», "and", "then", «y», «luego»: they begin the next), and how many
std::vector<size_t> Clauses(const std::vector<std::string>& w, size_t* count) {
    static const std::unordered_set<std::string> kAnd = {"и", "а", "потом", "затем", "and", "then", "y", "luego", "después", "despues"};
    std::vector<size_t> clause(w.size(), 0);
    size_t k = 0;
    bool words = false;   // the part has a word of its own yet
    for (size_t i = 0; i < w.size(); ++i) {
        const bool conj = kAnd.count(w[i]) > 0;
        if (conj && words) ++k, words = false;
        clause[i] = k;
        words = words || !conj;
    }
    *count = words || k == 0 ? k + 1 : k;
    return clause;
}
// «не бей его», "don't shoot him", «хватит дразнить», «не ходи за Колей»: the words before a verb in its part say not to
bool Negated(const std::vector<std::string>& w, const std::vector<size_t>& clause, size_t verb) {
    static const std::unordered_set<std::string> kNot = {"не", "нельзя", "хватит", "перестань", "прекрати", "don't", "dont", "do", "stop",
                                                          "never", "no"};
    // within three words of it (2026-11-15: «вот он, не видишь, вот стоит, да дай ему по щам»: the «не» is of «видишь»)
    for (size_t i = verb > 3 ? verb - 3 : 0; i < verb; ++i)
        if (clause[i] == clause[verb] && kNot.count(w[i]) && (w[i] != "do" || (i + 1 < w.size() && w[i + 1] == "not"))) return true;
    return false;
}
// whether a target is the one the line is said to (self: a person's role, or "bot"): nobody does it to themselves
bool IsSelf(const json& target, const std::string& self) {
    if (self.empty()) return false;
    return self == "bot" ? target.value("kind", std::string()) == "bot" : target.value("to", std::string()) == self;
}

// self: whom the line is said to (a role, or "bot"); line: without their name
bool ReadActOn(const std::string& line, const json& callees, const std::string& bot_name, const std::string& self, ActOn* out) {
    const std::vector<std::string> w = coop::MemoryWords(coop::MemoryNorm(line));
    if (w.empty()) return false;
    size_t parts = 1;
    const std::vector<size_t> clause = Clauses(w, &parts);
    const std::vector<Mention> ms = Mentions(w, callees, bot_name);
    // every verb of acting on someone in turn (the first not said not to, with whom it is done to)
    for (size_t verb = 0; verb < w.size(); ++verb) {
        ActOn act;
        const bool face = StrikeByFace(w, verb);   // «дай ему по щам»: a strike by where it lands
        if ((!face && !ActVerb(w[verb], verb + 1 < w.size() ? w[verb + 1] : std::string(), &act)) || Negated(w, clause, verb)) continue;
        if (face) act.kind = "hit", act.intent = "MELEE", act.english = "Going hands-on.", act.once = true;
        // whom: the first one named after the verb in its part (before the next such verb), else the last one before it in its part
        size_t end = w.size();
        for (size_t i = verb + 1; i < w.size() && end == w.size(); ++i)
            if (clause[i] != clause[verb] || ActVerb(w[i], i + 1 < w.size() ? w[i + 1] : std::string(), nullptr) || GoVerb(w[i]) != Going::None) end = i;
        size_t k = ms.size();
        for (size_t m = 0; m < ms.size() && k == ms.size(); ++m)
            if (ms[m].at > verb && ms[m].at < end) k = m;
        for (size_t m = ms.size(); m-- > 0 && k == ms.size();)
            if (ms[m].at < verb && clause[ms[m].at] == clause[verb]) k = m;
        if (k == ms.size()) {
            // «стреляй!», «бей!»: no one said, the line as the classifier reads it. A verb that wants whom said with nobody and
            // nothing more («застрели!», «втащи!», «дай по щам!») is about the one pointed at (2026-11-15, the owner's log:
            // «застрели Михайловича» with the name unheard was "Open fire" at nobody); a word after it that may be whom («застрели
            // Петю»: nobody known) leaves the line as it is
            static const std::unordered_set<std::string> kWantsWhom = {
                "застрели", "пристрели", "подстрели", "расстреляй", "убей", "убейте", "замочи", "грохни", "прикончи", "добей",
                "ликвидируй", "устрани", "уничтожь", "пришей", "втащи", "втащите", "вломи", "врежь", "вмажь", "вдарь", "наваляй",
                "накостыляй", "ударь", "стукни", "тресни", "пни", "отпинай", "отлупи", "избей", "побей", "kill", "punch", "smack", "slap"};
            if (!face && !kWantsWhom.count(w[verb])) continue;
            bool more = false;
            for (size_t i = verb + 1; i < w.size() && clause[i] == clause[verb] && !more; ++i)
                more = !SmallWord(w[i]) && !(face && i <= verb + 1);
            if (more) continue;
            act.target = json{{"kind", "pointed"}};
        } else {
            act.target = Resolved(ms, k);
            if (IsSelf(act.target, self)) continue;
        }
        act.clause = clause[verb];
        act.clauses = parts;
        act.verb_at = verb;
        *out = act;
        return true;
    }
    return false;
}

// ---- going to someone, following them (2026-11-15, the owner: «Майк, иди к Нику»): «иди к Нику», «подойди к Толику», «иди за
// Колей», «следуй за Толиком», «встань рядом с Колей», «иди к нему», "go to Nick", "follow Mike", "walk up to Tony", «ve con Nico».
// People are no places of the planner and their names no words of the decoder's (2026-11-15: «иди к Коле» came back "Go to the
// garage", «иди за Колей» "follow me", «подойди к Толику» as talk): the player's own words say who, and the order carries
// "target" as an act on someone does. MOVE_TO walks up to them, FOLLOW_ME follows them instead of the player (the game: a target
// that is nobody's body, a thing under the crosshair, leaves the order as it was). Me («иди ко мне», «иди за мной») is the
// classifier's as ever. lang: the language of the words said back (the name in it: «Иду к Коле.», "Going over to Nick.")
std::string CalledIn(const json& target, const std::string& lang, char kase, const std::string& bot_name);
bool ReadGoTo(const std::string& line, const json& callees, const std::string& bot_name, const std::string& self, const std::string& lang,
              ActOn* out) {
    const std::vector<std::string> w = coop::MemoryWords(coop::MemoryNorm(line));
    if (w.empty()) return false;
    size_t parts = 1;
    const std::vector<size_t> clause = Clauses(w, &parts);
    const std::vector<Mention> ms = Mentions(w, callees, bot_name);
    if (ms.empty()) return false;
    // the word before whom: to them (Go), by them (Near), after them (After), with them (With)
    enum class Rel { None, To, Near, After, With };
    auto rel = [](const std::string& x) {
        static const std::unordered_set<std::string> kTo = {"к", "ко", "до", "навстречу", "to", "towards", "toward", "a", "al", "hacia", "hasta",
                                                            "donde"};
        static const std::unordered_set<std::string> kNear = {"рядом", "возле", "около", "у", "близко", "near", "next", "beside", "by",
                                                              "behind", "junto", "cerca"};
        static const std::unordered_set<std::string> kAfter = {"за", "after", "tras", "detrás", "detras"};
        static const std::unordered_set<std::string> kWith = {"с", "со", "with", "con"};
        return kTo.count(x) ? Rel::To : kNear.count(x) ? Rel::Near : kAfter.count(x) ? Rel::After : kWith.count(x) ? Rel::With : Rel::None;
    };
    for (size_t verb = 0; verb < w.size(); ++verb) {
        const Going going = GoVerb(w[verb]);
        if (going == Going::None || Negated(w, clause, verb)) continue;
        // whom: named within three words after the verb in its part (no other verb between), else within three words before it
        size_t k = ms.size();
        for (size_t m = 0; m < ms.size() && k == ms.size(); ++m)
            if (ms[m].at > verb && ms[m].at <= verb + 4 && clause[ms[m].at] == clause[verb]) k = m;
        if (k < ms.size()) {
            const size_t at = ms[k].at;
            for (size_t i = verb + 1; i < at && k < ms.size(); ++i)
                if (GoVerb(w[i]) != Going::None || ActVerb(w[i], w[i + 1], nullptr)) k = ms.size();
        }
        size_t from = verb + 1, to = k < ms.size() ? ms[k].at : verb + 1;   // the words between the verb and whom
        bool shared = false;   // whom is the one the act after the walk is done to
        if (k == ms.size()) {
            for (size_t m = ms.size(); m-- > 0 && k == ms.size();)
                if (ms[m].at < verb && ms[m].at + 4 >= verb && clause[ms[m].at] == clause[verb]) k = m;
            if (k == ms.size()) {
                // «догони и убей бабу Валю», «беги, втащи ему» (2026-11-15, the owner's log): a walk with nobody of its own goes to
                // whom the act right after it is done to
                size_t act = w.size();
                for (size_t v = verb + 1; v < w.size() && v <= verb + 2 && act == w.size(); ++v)
                    if (ActVerb(w[v], v + 1 < w.size() ? w[v + 1] : std::string(), nullptr) || StrikeByFace(w, v)) act = v;
                for (size_t m = 0; m < ms.size() && k == ms.size() && act < w.size(); ++m)
                    if (ms[m].at > act && ms[m].at <= act + 4) k = m, shared = true;
                if (k == ms.size()) continue;
            } else {
                from = ms[k].at >= 2 ? ms[k].at - 2 : 0, to = ms[k].at;   // «к Коле иди», «за Колей иди»: the word or two before whom
            }
        }
        Rel r = shared ? Rel::To : Rel::None;
        for (size_t i = from; i < to && !shared; ++i)
            if (const Rel x = rel(w[i]); x != Rel::None) r = x;   // the last one before whom
        std::string kind;
        switch (going) {
        case Going::Go: kind = r == Rel::To || r == Rel::Near ? "go" : r == Rel::After || r == Rel::With ? "follow" : ""; break;
        case Going::Follow: kind = "follow"; break;
        case Going::Stay: kind = r != Rel::None ? "go" : ""; break;
        case Going::Reach: kind = "go"; break;
        default: break;
        }
        if (kind.empty()) continue;
        const json target = Resolved(ms, k);
        const std::string whom = target.value("kind", std::string());
        if (whom == "speaker" || IsSelf(target, self)) continue;   // «иди ко мне»: the classifier's; nobody goes to themselves
        out->kind = kind;
        out->intent = kind == "go" ? "MOVE_TO" : "FOLLOW_ME";
        out->once = false;
        out->target = target;
        out->clause = clause[verb];
        out->clauses = parts;
        out->verb_at = verb;
        const std::string name = whom == "pointed" ? std::string() : CalledIn(target, lang, kind == "go" ? 'd' : 'i', bot_name);
        out->english = name.empty() ? (kind == "go" ? "On my way there." : "Moving.") : (kind == "go" ? "Going over to " : "Following ") + name + ".";
        return true;
    }
    return false;
}

// what the one who goes calls the one gone to, in the language of its words: their name in it (their role's, else English, else
// as the line said it), in Russian in the case the sentence wants ('d' «Иду к Коле», 'i' «Иду за Колей», 'n' as it is)
std::string CalledIn(const json& target, const std::string& lang, char kase, const std::string& bot_name) {
    const bool bot = target.value("kind", std::string()) == "bot";
    const std::string role = bot ? std::string("bot") : target.value("to", std::string());
    std::string name;
    if (g_talk && g_talk->roles.count(role)) {
        const auto& names = g_talk->roles.at(role).names;
        for (const std::string& l : {lang, std::string("en")})
            if (const auto it = names.find(l); name.empty() && it != names.end() && !it->second.empty()) name = it->second;
    }
    if (name.empty() && bot) name = bot_name;
    if (name.empty()) name = target.value("name", std::string());
    if (name.empty()) return {};
    return lang == "ru" && kase != 'n' ? RussianNameIn(name, kase) : name;
}

// The line's turns with the act: the turn of its part (a turn a part), or the only turn, becomes that order with its target and its
// words (from the table in use, `table`); a line read otherwise gives the target to its turns of the same kind. A turn that is that
// order already keeps its words and what it says, the target added; going to someone named never keeps a place (the decoder's
// reading of their name: "Go to the garage" for «иди к Коле»). True: changed
bool ApplyActOn(const ActOn& act, json* turns, coop::Localizer* table) {
    if (!turns->is_array() || turns->empty()) return false;
    static const std::map<std::string, std::vector<std::string>> kSame = {
        {"MELEE", {"MELEE", "PUSH"}},
        {"OPEN_FIRE", {"OPEN_FIRE", "ATTACK", "SUPPRESS"}},
        {"AIM_AT", {"LOOK_AT", "HOLD_ANGLE"}},
        {"LOOK_AT", {"LOOK_AT", "LOOK_AT_ME", "HOLD_ANGLE", "AIM_AT"}},
        {"TAUNT", {}},
        {"MOVE_TO", {"MOVE_TO", "COME_BACK", "REGROUP", "HOLD_POSITION"}},
        {"FOLLOW_ME", {"FOLLOW_ME", "COVER_ME", "COME_BACK"}}};
    const bool going = act.intent == "MOVE_TO" || act.intent == "FOLLOW_ME";
    const bool named = act.target.value("kind", std::string()) != "pointed";
    // a place the planner gave an act on someone (the pin left on the map: "via": "pin_default") is not where it is done, the one it is
    // done to is (2026-11-15: «Бади, застрели Михалыча» with a pin set was "Opening fire, on your pin." and an order at the pin)
    auto placed = [](const json& t) {
        return t.contains("order") && t["order"].is_object() && t["order"].contains("entity") && !t["order"]["entity"].is_null();
    };
    auto rewrite = [&](json& t) {
        const json was = {{"intent", t.value("intent", json(nullptr))}, {"action", t.value("action", json(nullptr))}, {"prob", t.value("prob", json(nullptr))}};
        const std::string intent = t.value("intent", std::string());
        // read right: its order and its own words, the target added. A walk to someone named keeps neither (the place was their
        // name misread, the words name it: «Иду к метке»); one to him under the crosshair keeps the place (a thing there: the
        // walk as before) and says its own words (the planner's are about the place, not about him)
        const bool kept = intent == act.intent && t.value("action", std::string()) == "act" && !(going && named) && (going || !placed(t));
        const bool kept_words = kept && !going && t.contains("say");
        t["intent"] = act.intent;
        t["action"] = "act";
        t["prob"] = 1.0;
        t["talk_p"] = 0.0;
        t["question"] = nullptr;
        t.erase("state");
        json order = t.contains("order") && t["order"].is_object() && kept ? t["order"] : json::object();
        order["intent"] = act.intent;
        order["target"] = act.target;
        if (act.once) order["strikes"] = 1;   // one strike, not until they are down
        t["order"] = order;
        t["target"] = act.target;
        t["act_on"] = {{"kind", act.kind}, {"was", was}};
        if (!kept_words) {
            std::string local;
            coop::Localizer* const were = g_replies;
            g_replies = table;
            if (table && Localize(act.english, &local)) t["say"] = local, t["say_en"] = act.english;
            else t["say"] = act.english, t.erase("say_en");
            g_replies = were;
        }
    };
    if (turns->size() == 1) {
        rewrite(turns->at(0));
        return true;
    }
    if (act.clauses == turns->size() && act.clause < turns->size()) {
        rewrite(turns->at(act.clause));   // a turn a part: this part's
        return true;
    }
    const auto& same = kSame.at(act.intent);
    bool any = false;
    for (json& t : *turns) {
        const std::string intent = t.value("intent", std::string());
        if (!t.contains("order") || !t["order"].is_object() || (intent != act.intent && std::find(same.begin(), same.end(), intent) == same.end()))
            continue;
        if ((going && named) || (!going && placed(t))) {
            rewrite(t);   // its place was their name misread; an act's place is the one it is done to
        } else {
            t["order"]["target"] = act.target;
            t["target"] = act.target;
        }
        any = true;
    }
    return any;
}

// The turns made again from the player's own words (2026-11-15, the owner's log: «Бади, догони убей, бабу, валю» came back FOLLOW_ME,
// FRAG, BREACH, and the act on Valya fit none of them): a turn a verb, in their order. Only for a line of one part (no «и», «потом»):
// every verb in it is one of these, and whatever else the decoder made of it was its misreading
void RebuildTurns(std::vector<ActOn> orders, json* turns, coop::Localizer* table) {
    std::sort(orders.begin(), orders.end(), [](const ActOn& a, const ActOn& b) { return a.verb_at < b.verb_at; });
    json made = json::array();
    for (const ActOn& o : orders) {
        json one = json::array({json{{"line", o.english}, {"intent", o.intent}, {"action", "act"}, {"prob", 1.0}, {"talk_p", 0.0},
                                     {"question", nullptr}, {"order", json::object()}}});
        ApplyActOn(o, &one, table);
        made.push_back(one.at(0));
    }
    *turns = std::move(made);
}
// Who the talk is about (2026-11-15, the owner: «чтобы он понял контекст, про кого шла речь»; «Бади, убей её» after «убей бабу Валю»
// went to nobody: the crosshair was a hand off her): the one named last in the player's lines, a person or the bot, for 30 s (as "it"
// is for things, rule set v8). Him / her with nobody named before it in the line is the one under the crosshair (the game's), else them:
// the target carries "else"
struct NamedLast {
    json target;
    Clock::time_point at{};
} g_named_last;
constexpr double kNamedLastSeconds = 30.0;
json WithElse(json target, const std::string& self) {
    // (not the one the line is said to: «втащи Коле» to the bot, then «Коля, а ну-ка втащи там парню» -- Коля does not hit himself)
    if (target.is_object() && target.value("kind", std::string()) == "pointed" && g_named_last.target.is_object() &&
        std::chrono::duration<double>(Clock::now() - g_named_last.at).count() <= kNamedLastSeconds && !IsSelf(g_named_last.target, self))
        target["else"] = g_named_last.target;
    return target;
}
void NoteNamed(const std::string& line, const json& callees, const std::string& bot_name, const std::string& self) {
    const std::vector<std::string> w = coop::MemoryWords(coop::MemoryNorm(line));
    for (const Mention& m : Mentions(w, callees, bot_name)) {
        const std::string kind = m.target.value("kind", std::string());
        if (!m.pronoun && (kind == "person" || kind == "bot") && !IsSelf(m.target, self)) g_named_last = {m.target, Clock::now()};
    }
}

// The player's own words on someone (an act, a walk to them) over the turns: each to the turn of its part, its kind's turn, or the
// only one (ApplyActOn); a line of one part whose turns fit neither made again from the words (RebuildTurns). note: what was done
struct WordOrders {
    bool acted = false, went = false, rebuilt = false;
    ActOn act, go;
};
WordOrders ApplyWordOrders(const std::string& line, const json& callees, const std::string& bot_name, const std::string& self,
                           const std::string& lang, json* turns, coop::Localizer* table) {
    WordOrders r;
    const bool has_act = ReadActOn(line, callees, bot_name, self, &r.act);
    const bool has_go = ReadGoTo(line, callees, bot_name, self, lang, &r.go);
    r.act.target = WithElse(r.act.target, self);
    r.go.target = WithElse(r.go.target, self);
    NoteNamed(line, callees, bot_name, self);   // for the lines after it
    r.acted = has_act && ApplyActOn(r.act, turns, table);
    // a line read as one turn that strikes them already leaves the walk to that (a strike walks up to them first); a shot, a look,
    // an aim do not walk: «Бади, догони убей, бабу, валю» (2026-11-15, the owner's log) came back one turn, OPEN_FIRE at her from
    // where it stood. The walk is a turn of its own then, before or after the act as said
    const bool walk_left = r.acted && turns->size() == 1 && r.act.kind == "hit";
    if (has_go && !walk_left) {
        if (r.acted && turns->size() == 1) {
            json one = json::array({json{{"line", r.go.english}, {"intent", r.go.intent}, {"action", "act"}, {"prob", 1.0}, {"talk_p", 0.0},
                                         {"question", nullptr}, {"order", json::object()}}});
            ApplyActOn(r.go, &one, table);
            turns->insert(r.go.verb_at < r.act.verb_at ? turns->begin() : turns->end(), one.at(0));
            r.went = true;
        } else {
            r.went = ApplyActOn(r.go, turns, table);
        }
    }
    const size_t parts = has_act ? r.act.clauses : has_go ? r.go.clauses : 1;
    if (parts == 1 && ((has_act && !r.acted) || (has_go && !walk_left && !r.went))) {
        std::vector<ActOn> orders;
        if (has_go) orders.push_back(r.go);
        if (has_act) orders.push_back(r.act);
        RebuildTurns(orders, turns, table);
        r.acted = has_act, r.went = has_go, r.rebuilt = true;
    }
    // the same act on the same one twice in a row is said for weight, not done twice (2026-11-15, the owner's log: «убей, бабу Валю,
    // убей её» came back ATTACK on her twice: she would come back at her post and be killed again)
    if (r.acted || r.went)
        for (size_t k = 1; k < turns->size();) {
            const json &a = turns->at(k - 1), &b = turns->at(k);
            const bool same = a.contains("target") && b.contains("target") && a["target"] == b["target"] &&
                              a.value("intent", std::string()) == b.value("intent", std::string());
            if (same) turns->erase(turns->begin() + static_cast<std::ptrdiff_t>(k));
            else ++k;
        }
    return r;
}

// «встань сюда», «встань туда», «встань возле забора», «встань на мою метку», "stand over there", «ponte allí» (2026-11-15, the owner:
// «когда я говорю встань сюда, встань туда, они не двигаются ... Я же показываю, куда встать. Я хочу, чтобы чётенько вставали, куда я
// прям показываю»): HOLD_POSITION is "stay where you are" to the game (a spot named "near", or one within 2.5 m, is never walked to),
// unless the order says "stand": to that place, or where the crosshair is, and held there. «встань» with no place after it in its
// part is getting up; "stand by" alone is waiting
bool StandThere(const std::string& line) {
    const std::vector<std::string> w = coop::MemoryWords(coop::MemoryNorm(line));
    static const std::unordered_set<std::string> kStand = {"встань", "встаньте", "стань", "станьте", "становись", "становитесь", "stand", "ponte",
                                                           "póngase", "pongase", "colócate", "colocate", "sitúate", "situate", "párate", "parate"};
    static const std::unordered_set<std::string> kWhere = {
        "сюда", "туда", "здесь", "тут", "там", "вон", "вот", "возле", "около", "рядом", "у", "на", "к", "перед", "за", "под", "напротив",
        "посреди", "между", "here", "there", "by", "near", "next", "on", "at", "beside", "behind", "aquí", "aqui", "allí", "alli", "ahí",
        "ahi", "allá", "alla", "junto", "cerca", "en", "al", "delante", "detrás", "detras"};
    size_t parts = 1;
    const std::vector<size_t> clause = Clauses(w, &parts);
    for (size_t i = 0; i < w.size(); ++i) {
        if (!kStand.count(w[i])) continue;
        for (size_t j = i + 1; j < w.size() && clause[j] == clause[i]; ++j) {
            if (w[i] == "stand" && w[j] == "by" && j == i + 1 && j + 1 == w.size()) break;
            if (kWhere.count(w[j])) return true;
        }
    }
    return false;
}
// ... and its words are of going there ("On my way there." from the table in use, `table`), not "Staying put."
void MarkStand(const std::string& line, json* turns, coop::Localizer* table) {
    if (!turns->is_array() || !StandThere(line)) return;
    for (json& t : *turns) {
        // read as getting up ("Stand up there.", STAND_UP 0.72 in the game's run of 2026-11-15): with a place after «встань» it is
        // standing there (a chair or a bed is up onto it, as HOLD_POSITION has it)
        if (t.value("intent", std::string()) == "STAND_UP" && t.value("action", std::string()) == "act") {
            t["intent"] = "HOLD_POSITION";
            if (!t.contains("order") || !t["order"].is_object()) t["order"] = json::object();
            t["order"]["intent"] = "HOLD_POSITION";
        }
        if (t.value("intent", std::string()) != "HOLD_POSITION" || !t.contains("order") || !t["order"].is_object()) continue;
        t["order"]["stand"] = true;
        if (t.value("action", std::string()) != "act") continue;
        const std::string en = "On my way there.";
        std::string local;
        coop::Localizer* const were = g_replies;
        g_replies = table;
        if (table && Localize(en, &local)) t["say"] = local, t["say_en"] = en;
        else t["say"] = en, t.erase("say_en");
        g_replies = were;
    }
}

// An order the bot would carry out (2026-11-15): a line said while looking at a person, nobody called by name, is the bot's when it
// gives one: a turn the classifier is sure of that is no talk and asks nothing of them, even one the planner would ask about
// («открыть огонь на мою метку» with no pin yet: "Where?" is the bot's question then, not the granny's talk)
bool SureOrder(const json& turns, const std::string& heard, bool talking) {
    constexpr double kTalkShare = 0.15, kOrderSure = 0.6;
    for (const json& t : turns) {
        const std::string action = t.value("action", std::string()), intent = t.value("intent", std::string());
        if ((action != "act" && action != "ask") || intent.empty() || intent == "SMALL_TALK" || intent == "NONE" || intent == "TALK") continue;
        if (TalkFor(t, heard, talking) || (t.contains("state") && t["state"].is_string() && !t["state"].get<std::string>().empty())) continue;
        if (t.value("prob", 0.0) >= kOrderSure && t.value("talk_p", 0.0) < kTalkShare) return true;
    }
    return false;
}

// Whether a person of the level whose body takes orders (2026-11-12, the owner: «чтобы любому NPC можно было отдать именно приказ
// и поговорить») answers a line in their role rather than carry it out. Talk is what they are there for: every turn of the line
// must be talk for it to be, and a turn is talk when the bot would talk too (TalkFor), when it asks how they are (the game's
// "how", "hurt" and "body" answers are a soldier's: health, heat, ammo), when it gives nothing to carry out or the planner would
// ask back about it ("Which door?": their role answers in its own words instead), and when the classifier is not sure of the
// order (its top label under 0.6, or 0.15 of talk in it: «откройте мне счёт» read as OPEN at 0.5 is the teller's business, not a
// door). What they see, what that is, what they do: the game answers from their body, as it does for the bot.
bool PersonTalks(const json& turns, const std::string& heard, bool talking) {
    if (turns.empty()) return true;
    for (const json& t : turns) {
        const std::string state = t.contains("state") && t["state"].is_string() ? t["state"].get<std::string>() : std::string();
        const std::string action = t.value("action", std::string());
        if (TalkFor(t, heard, talking) || state == "how" || state == "hurt" || state == "body") continue;
        if (!state.empty()) return false;
        if (!t.contains("order") || t["order"].is_null() || action == "ask" || action == "say_again" || action == "ignore") continue;
        if (t["order"].is_object() && t["order"].contains("intent") && t["order"]["intent"].is_string() &&
            t["order"]["intent"].get<std::string>() == "SMALL_TALK")
            continue;
        constexpr double kTalkShare = 0.15, kOrderSure = 0.6;
        if (t.value("prob", 0.0) < kOrderSure || t.value("talk_p", 0.0) >= kTalkShare) continue;
        return false;   // an order it is sure of
    }
    return true;
}

json ReplyJson(Chat& chat, const Chat::Turn& t) {
    const Model& m = chat.m;
    const coop::PlannerResult& r = t.r;
    const coop::Decision& d = r.decision;
    const coop::LocationMatcher& places = chat.brain.Places();
    auto label = [&](int i) { return i >= 0 ? json(m.cfg.labels[static_cast<size_t>(i)]) : json(nullptr); };
    auto or_null = [](const std::string& s) { return s.empty() ? json(nullptr) : json(s); };
    json j;
    j["event"] = "reply";
    j["intent"] = label(d.intent);
    j["prob"] = d.prob;
    j["action"] = r.action;
    j["say"] = t.reply;
    if (t.at >= 0) j["at_s"] = std::round(t.at * 1000) / 1000;   // the moment of its pointer word: the game grounds it then
    if (g_replies && !t.reply.empty()) {
        std::string local;
        if (Localize(t.reply, &local, t.terms.empty() ? nullptr : &t.terms)) j["say"] = local, j["say_en"] = t.reply;
        else j["say_untranslated"] = true;
    }
    j["ms"] = t.ms;
    j["on_signal"] = d.on_signal;
    j["other"] = d.other;
    j["negated"] = d.negated;
    j["adjusted"] = r.adjusted;
    // round v68: the time said with the order, on the turn (WAIT has no order object): {"kind": "for" | "after", "seconds":
    // 10} or {"kind", "min": 3, "max": 7} (the game draws), "more" (add to a timed order still running), "capped" (said
    // longer than 60 s), "said"; null when none
    if (t.time.found) {
        json time = {{"kind", t.time.after ? "after" : "for"}, {"more", t.time.more}, {"capped", t.time.capped}, {"said", t.time.said}};
        if (t.time.range) time["min"] = t.time.min, time["max"] = t.time.max;
        else time["seconds"] = t.time.seconds;
        j["time"] = time;
    } else {
        j["time"] = nullptr;
    }
    json top = json::array();
    for (int i : coop::TopK(t.p, 3)) top.push_back({m.cfg.labels[static_cast<size_t>(i)], t.p[static_cast<size_t>(i)]});
    j["top"] = top;
    j["places"] = d.places.targets.empty() ? std::string() : PlacesText(d.places, places);
    json ground = json::array();
    for (const coop::Grounding& g : r.ground)
        ground.push_back({{"status", g.status}, {"entity", or_null(g.entity)}, {"via", or_null(g.via)}, {"candidates", g.candidates}});
    j["ground"] = ground;
    if (r.has_order) {
        const coop::Order& o = r.order;
        const char* dir = coop::PlaceDirectionName(o.direction);
        const char* ptr = coop::PlacePointerName(o.pointer);
        j["order"] = {{"intent", label(o.intent)}, {"entity", or_null(o.entity)}, {"candidates", o.candidates},
                      {"direction", or_null(dir)}, {"zone", o.zone >= 0 ? json(places.ZoneId(o.zone)) : json(nullptr)},
                      {"pointer", or_null(ptr)}, {"other", o.other}, {"via", or_null(o.via)}, {"near", o.nearby},
                      {"object", o.object >= 0 ? json(places.ObjectId(o.object)) : json(nullptr)}};
        if (o.has_item) {   // the farmer's and the builder's orders: what it acts on, as said, and the game's catalogue entry
            j["order"]["item"] = or_null(o.item);
            j["order"]["item_id"] = or_null(o.item_id);
        }
        if (t.close) j["order"]["close"] = true;   // "close the door": OPEN, the other way (2026-11-01)
        if (o.has_means) {  // rule set v9 (bot v67): the thing it is done with ("using the crate"), and its object
            j["order"]["means"] = or_null(o.means);
            j["order"]["means_object"] = o.means_object >= 0 ? json(places.ObjectId(o.means_object)) : json(nullptr);
        }
    } else {
        j["order"] = nullptr;
    }
    if (!t.state.empty()) {
        // a question the game answers from the bot: no order goes with it ("what do you see?" is no SEE_THING at the crosshair)
        j["state"] = t.state;
        j["order"] = nullptr;
    }
    const coop::Memory& mem = chat.planner.Mem();
    if (mem.has_question)
        j["question"] = {{"kind", mem.question.kind}, {"intent", label(mem.question.intent)}, {"candidates", mem.question.candidates},
                         {"offered", mem.question.offered}, {"queued", mem.question.queued}};
    else
        j["question"] = nullptr;
    j["pending"] = label(chat.brain.Pending());
    j["pending_entity"] = or_null(chat.planner.PendingEntity());
    j["last_entity"] = or_null(mem.last_entity);
    return j;
}

// everything the long-term memory keeps (serve "recall", --memory-dump): the lines and what they mean, the names, the colours
// the bot's line with the sentences the player asked it to say otherwise («вместо «выдвигаюсь» говори «пошёл»»), in the line's
// language; a sentence they asked it not to say is left out (2026-10-30)
// the first letter of a line a capital (ASCII, Cyrillic а-я and ё, Latin-1 á..ñ): a sentence that lost its first word
std::string CapitalFirst(std::string s) {
    if (s.empty()) return s;
    const unsigned char c0 = static_cast<unsigned char>(s[0]);
    if (c0 >= 'a' && c0 <= 'z') {
        s[0] = static_cast<char>(c0 - 'a' + 'A');
    } else if (s.size() >= 2) {
        const unsigned cp = ((c0 & 0x1Fu) << 6) | (static_cast<unsigned char>(s[1]) & 0x3Fu);
        unsigned up = cp;
        if (c0 >= 0xC0 && c0 < 0xE0) {
            if (cp >= 0x430 && cp <= 0x44F) up = cp - 0x20;
            else if (cp == 0x451) up = 0x401;
            else if (cp >= 0xE0 && cp <= 0xFE && cp != 0xF7) up = cp - 0x20;
        }
        if (up != cp) {
            s[0] = static_cast<char>(0xC0 | (up >> 6));
            s[1] = static_cast<char>(0x80 | (up & 0x3F));
        }
    }
    return s;
}

// the sentence with the words the player asked to say otherwise («брат» -> nothing, «метров» -> «шагов»), as said (the spans of
// SpanWords); a word left out takes the comma before it along («Понял, брат, запомню.» -> «Понял, запомню.»)
std::string Reworded(const std::string& sentence, const coop::MemoryPhrase& p, bool* changed) {
    const std::vector<std::string> words = coop::MemoryWords(p.from);
    const std::vector<coop::SpanWord> sw = coop::SpanWords(sentence);
    if (words.empty()) return sentence;
    std::string out;
    size_t at = 0;
    for (size_t i = 0; i + words.size() <= sw.size();) {
        bool same = true;
        for (size_t k = 0; k < words.size() && same; ++k) same = sw[i + k].norm == words[k];
        if (!same) {
            ++i;
            continue;
        }
        size_t from = sw[i].begin, to = sw[i + words.size() - 1].end;
        if (p.to.empty()) {
            size_t b = from;
            while (b > at && sentence[b - 1] == ' ') --b;
            if (b > at && sentence[b - 1] == ',') from = b - 1;   // «Понял, брат»: the comma before it goes
            else {                                               // «Брат, не вижу»: the comma and space after it
                while (to < sentence.size() && (sentence[to] == ',' || sentence[to] == ' ')) ++to;
            }
        }
        out += sentence.substr(at, from - at) + p.to;
        at = to;
        i += words.size();
        *changed = true;
    }
    out += sentence.substr(at);
    return out == sentence ? sentence : CapitalFirst(out);
}

std::string Rephrased(const std::string& text, const std::string& lang) {
    if (!g_memory || !g_memory->IsOpen() || g_memory->Phrases().empty() || text.empty()) return text;
    std::string out;
    bool changed = false;
    for (const std::string& line_sentence : coop::SplitSentences(text)) {
        std::string sentence = line_sentence;
        for (const coop::MemoryPhrase& x : g_memory->Phrases())   // words inside it first
            if (x.lang == lang && x.word) sentence = Reworded(sentence, x, &changed);
        const std::string key = Chat::PhraseKey(sentence);
        const coop::MemoryPhrase* p = nullptr;
        for (const coop::MemoryPhrase& x : g_memory->Phrases())
            if (x.lang == lang && !x.word && x.from == key) p = &x;
        std::string piece = sentence;
        if (p) {
            changed = true;
            piece = p->to;
            if (!piece.empty() && std::string(".!?").find(piece.back()) == std::string::npos) {
                const char end = sentence.empty() ? '.' : sentence.back();
                piece += std::string(".!?").find(end) != std::string::npos ? std::string(1, end) : std::string(".");
            }
            piece = CapitalFirst(piece);
        }
        if (piece.empty()) continue;
        out += (out.empty() ? "" : " ") + piece;
    }
    return changed ? out : text;
}

// the line as the voice is to say it: the words the player taught a pronunciation of, in the voice's language, the way they
// taught it («за́мок», «бадди»); the text shown stays as it is (2026-10-30)
std::string Pronounced(const std::string& text, const std::string& lang) {
    if (!g_memory || !g_memory->IsOpen() || g_memory->Sayings().empty()) return text;
    const std::vector<coop::SpanWord> sw = coop::SpanWords(text);
    std::string out;
    size_t at = 0;
    for (size_t i = 0; i < sw.size();) {
        size_t taken = 0;
        for (const coop::MemorySaying& x : g_memory->Sayings()) {
            if (x.lang != lang) continue;
            const std::vector<std::string> words = coop::MemoryWords(x.word);
            if (words.empty() || i + words.size() > sw.size()) continue;
            bool same = true;
            for (size_t k = 0; k < words.size() && same; ++k) same = sw[i + k].norm == words[k];
            if (!same) continue;
            out += text.substr(at, sw[i].begin - at) + x.say;
            at = sw[i + words.size() - 1].end;
            taken = words.size();
            break;
        }
        i += taken ? taken : 1;
    }
    return out + text.substr(at);
}

// The player's name said to them now and then (2026-10-31, the owner): «Понял, Тимур.» At the end of the line's first sentence,
// when that is a short one (5 words at most, no question), in a line that has no name and no «брат» in it already, and on
// about one line in four of those (--name-chance), never on two of the bot's next three lines
std::string WithPlayerName(const std::string& text, std::mt19937& rng) {
    ++g_name_since;
    const std::string name = Chat::PlayerName();
    if (name.empty() || text.empty() || g_name_chance <= 0) return text;
    const std::vector<std::string> words = coop::MemoryWords(coop::MemoryNorm(text));
    size_t b = 0, e = 0;
    if (coop::FindWords(words, coop::MemoryWords(coop::MemoryNorm(name)), 0, &b, &e)) {
        g_name_since = 0;   // the line says it already
        return text;
    }
    for (const std::string& w : words)
        if (w == "брат" || w == "братан" || w == "bro" || w == "brother" || w == "hermano") return text;
    const std::vector<std::string> sentences = coop::SplitSentences(text);
    const std::string first = sentences.empty() ? text : sentences[0];
    if (first.find('?') != std::string::npos || coop::MemoryWords(coop::MemoryNorm(first)).size() > 5) return text;
    if (g_name_chance < 100 && (g_name_since <= 3 || static_cast<int>(rng() % 100) >= g_name_chance)) return text;
    g_name_since = 0;
    return coop::WithAddress(text, name);
}

json MemoryJson(const coop::BotMemory& mem) {
    json lines = json::array(), names = json::array(), colours = json::array(), sayings = json::array(), phrases = json::array(),
         settings = json::object(), people = json::object();
    for (const coop::MemoryPerson& x : mem.People()) people[x.who] = {{"name", x.name}, {"at_ms", x.at_ms}};
    for (const coop::MemoryPhrase& x : mem.Phrases()) phrases.push_back({{"lang", x.lang}, {"from", x.from}, {"to", x.to}, {"at_ms", x.at_ms}});
    for (const coop::MemorySetting& x : mem.Settings()) settings[x.name] = x.value;
    for (const coop::MemorySaying& x : mem.Sayings())
        sayings.push_back({{"lang", x.lang}, {"word", x.word}, {"say", x.say}, {"at_ms", x.at_ms}});
    for (const coop::MemoryLine& l : mem.Lines())
        lines.push_back({{"lang", l.lang}, {"heard", l.heard}, {"lines", l.lines}, {"intent", l.intent}, {"source", l.source},
                         {"doubts", l.doubts}, {"at_ms", l.at_ms}});
    for (const coop::MemoryName& n : mem.Names())
        names.push_back({{"map", n.map}, {"entity", n.entity}, {"lang", n.lang}, {"name", n.name}, {"at_ms", n.at_ms}});
    for (const coop::MemoryColour& c : mem.Colours())
        colours.push_back({{"map", c.map}, {"entity", c.entity}, {"colour", c.colour}, {"at_ms", c.at_ms}});
    return {{"path", mem.Path()}, {"lines", lines}, {"names", names}, {"colours", colours}, {"sayings", sayings}, {"phrases", phrases},
            {"settings", settings}, {"people", people}};
}

// --teach-tests FILE (tools/teach_tests.json): the teaching lines' rules and the memory's text rules (teach.h), no model.
//   {"line": "...", "kind": "meant" | "not_that" | "name" | "colour" | "forget" | "none", "rest": "...", "colour": "...",
//    "plain": true}   ReadTeach (rest, colour and plain checked when given)
//    "attributive": true, "noun": ["..."]}          ... and a colour's attributive and noun
//   {"thing": "line", "bare": false, "expect": ["word", ...] | null, "denied": true}   ReadThingWords (null: not ok)
//   {"denial": "line", "expect": true}               BareDenial
//   {"colour_question": "line", "expect": true, "rest": ["..."]}   ColourQuestion
//   {"yes_no": "line", "expect": 1 | -1 | 0}         YesNo
//   {"adjective": ["yellow", "ru", "f", true], "expect": "жёлтую"}   ColourAdjective (id, lang, gender, accusative)
//   {"stressed": ["замок", 1, ""], "expect": "за́мок"}   StressedWord (word, syllable, vowel)
//   line cases also check "said", "stress", "vowel", "forget" (means, pronounce)
//   {"near": ["kept", "line"], "expect": true}      NearLine
//   {"form": ["said", "taught"], "expect": true}    WordForm
//   {"colours": "line", "expect": ["green"]}        ColoursIn
//   {"spans": "line", "expect": ["word", ...]}      SpanWords' words, normalized, and each span's own text normalized alike
//   line cases also check "same" and "said_text" (means said as «A — это то же самое, что B»)
//   {"verb": ["said", "taught"], "expect": true}    VerbForm
//   {"same_line": ["kept", "line"], "expect": true} SameLine
//   {"pattern": ["said", "meant as said"], "key": "...", "meaning": "...", "slot": true}   MakePattern (said normalized here)
//   {"match": ["key", "heard"], "expect": true, "slot": "..."}   MatchPattern (and the place as said)
//   {"name_question": "line", "expect": 0 | 1 | 2}   NameQuestion (1 the bot's name, 2 the player's)
//   {"called": ["line", "name"], "expect": true, "rest": "..."}   CalledBy (and the line without the name)
//   {"address": ["line", "name"], "expect": "..."}  WithAddress
//   line cases of kind bot_name / player_name check "rest" (normalized), "said_text" (as said) and "forget"
// Every case that reads otherwise is printed; exit 1 on any
int RunTeachTests(const std::string& path) {
    std::ifstream f(path);
    if (!f) return std::fprintf(stderr, "cannot read %s\n", path.c_str()), 2;
    json cases;
    try {
        f >> cases;
    } catch (const std::exception& e) {
        return std::fprintf(stderr, "%s: %s\n", path.c_str(), e.what()), 2;
    }
    size_t bad = 0, n = 0;
    auto wrong = [&](const json& c, const std::string& got) {
        ++bad;
        std::printf("  %s\n      got %s\n", c.dump(-1, ' ', false, json::error_handler_t::replace).c_str(), got.c_str());
    };
    for (const json& c : cases) {
        ++n;
        if (c.contains("line")) {
            const coop::TeachLine t = coop::ReadTeach(c.at("line").get<std::string>(), c.value("lang", std::string("en")));
            const std::string kind = coop::TeachKindName(t.kind);
            bool ok = kind == c.at("kind").get<std::string>();
            if (c.contains("rest")) ok = ok && t.rest == c["rest"].get<std::string>();
            if (c.contains("colour")) ok = ok && t.colour == c["colour"].get<std::string>();
            if (c.contains("plain")) ok = ok && t.plain == c["plain"].get<bool>();
            if (c.contains("attributive")) ok = ok && t.attributive == c["attributive"].get<bool>();
            if (c.contains("said")) ok = ok && t.said == c["said"].get<std::string>();
            if (c.contains("stress")) ok = ok && t.stress == c["stress"].get<int>();
            if (c.contains("vowel")) ok = ok && t.vowel == c["vowel"].get<std::string>();
            if (c.contains("forget")) ok = ok && t.forget == c["forget"].get<bool>();
            if (c.contains("setting")) ok = ok && t.setting == c["setting"].get<std::string>();
            if (c.contains("value")) ok = ok && std::abs(t.value - c["value"].get<double>()) < 1e-6;
            if (c.contains("scale")) ok = ok && std::abs(t.scale - c["scale"].get<double>()) < 1e-6;
            if (c.contains("noun")) ok = ok && t.noun == c["noun"].get<std::vector<std::string>>();
            if (c.contains("same")) ok = ok && t.same == c["same"].get<bool>();
            if (c.contains("said_text")) ok = ok && t.said_text == c["said_text"].get<std::string>();
            if (!ok)
                wrong(c, kind + " rest \"" + t.rest + "\" said \"" + t.said + "\" setting " + t.setting + " " + std::to_string(t.value) + " x" +
                             std::to_string(t.scale) + (t.forget ? " forget" : "") + " stress " + std::to_string(t.stress) + " vowel \"" + t.vowel +
                             "\" colour \"" + t.colour + "\" plain " + (t.plain ? "true" : "false") +
                             " attributive " + (t.attributive ? "true" : "false") + " noun " + json(t.noun).dump() +
                             (t.same ? " same, said_text \"" + t.said_text + "\"" : ""));
        } else if (c.contains("thing")) {
            const coop::ThingWords t = coop::ReadThingWords(c["thing"].get<std::string>(), c.value("bare", false));
            const json want = c.at("expect");
            bool ok = want.is_null() ? !t.ok : (t.ok && t.words == want.get<std::vector<std::string>>());
            if (c.contains("denied")) ok = ok && t.denied == c["denied"].get<bool>();
            if (!ok) wrong(c, std::string(t.ok ? "ok " : "not ok ") + json(t.words).dump() + (t.denied ? " denied" : ""));
        } else if (c.contains("denial")) {
            const bool got = coop::BareDenial(c["denial"].get<std::string>());
            if (got != c.at("expect").get<bool>()) wrong(c, got ? "true" : "false");
        } else if (c.contains("colour_question")) {
            std::vector<std::string> rest;
            const bool got = coop::ColourQuestion(c["colour_question"].get<std::string>(), &rest);
            bool ok = got == c.at("expect").get<bool>();
            if (c.contains("rest")) ok = ok && rest == c["rest"].get<std::vector<std::string>>();
            if (!ok) wrong(c, std::string(got ? "true " : "false ") + json(rest).dump());
        } else if (c.contains("yes_no")) {
            const int got = coop::YesNo(c["yes_no"].get<std::string>());
            if (got != c.at("expect").get<int>()) wrong(c, std::to_string(got));
        } else if (c.contains("stressed")) {
            const json& a = c["stressed"];
            const std::string got = coop::StressedWord(a[0].get<std::string>(), a[1].get<int>(), a[2].get<std::string>());
            if (got != c.at("expect").get<std::string>()) wrong(c, got);
        } else if (c.contains("adjective")) {
            const json& a = c["adjective"];
            const std::string got = coop::ColourAdjective(a[0].get<std::string>(), a[1].get<std::string>(), a[2].get<std::string>()[0], a[3].get<bool>());
            if (got != c.at("expect").get<std::string>()) wrong(c, got);
        } else if (c.contains("near")) {
            const bool got = coop::NearLine(coop::MemoryNorm(c["near"][0].get<std::string>()), coop::MemoryNorm(c["near"][1].get<std::string>()));
            if (got != c.at("expect").get<bool>()) wrong(c, got ? "true" : "false");
        } else if (c.contains("form")) {
            const bool got = coop::WordForm(coop::MemoryNorm(c["form"][0].get<std::string>()), coop::MemoryNorm(c["form"][1].get<std::string>()));
            if (got != c.at("expect").get<bool>()) wrong(c, got ? "true" : "false");
        } else if (c.contains("verb")) {
            const bool got = coop::VerbForm(coop::MemoryNorm(c["verb"][0].get<std::string>()), coop::MemoryNorm(c["verb"][1].get<std::string>()));
            if (got != c.at("expect").get<bool>()) wrong(c, got ? "true" : "false");
        } else if (c.contains("same_line")) {
            const bool got = coop::SameLine(coop::MemoryNorm(c["same_line"][0].get<std::string>()), coop::MemoryNorm(c["same_line"][1].get<std::string>()));
            if (got != c.at("expect").get<bool>()) wrong(c, got ? "true" : "false");
        } else if (c.contains("forget_what")) {
            const std::string got = coop::ForgetWhat(c["forget_what"].get<std::string>());
            if (got != c.at("rest").get<std::string>()) wrong(c, "\"" + got + "\"");
        } else if (c.contains("pattern")) {
            const coop::TaughtPattern t = coop::MakePattern(coop::MemoryNorm(c["pattern"][0].get<std::string>()), c["pattern"][1].get<std::string>());
            bool ok = t.slot == c.value("slot", true);
            if (c.contains("key")) ok = ok && t.key == c["key"].get<std::string>();
            if (c.contains("meaning")) ok = ok && t.meaning == c["meaning"].get<std::string>();
            if (!ok) wrong(c, std::string(t.slot ? "slot" : "no slot") + " key \"" + t.key + "\" meaning \"" + t.meaning + "\"");
        } else if (c.contains("match")) {
            std::string slot;
            const bool got = coop::MatchPattern(c["match"][0].get<std::string>(), c["match"][1].get<std::string>(), &slot, nullptr);
            bool ok = got == c.at("expect").get<bool>();
            if (got && c.contains("slot")) ok = ok && slot == c["slot"].get<std::string>();
            if (!ok) wrong(c, std::string(got ? "true" : "false") + " slot \"" + slot + "\"");
        } else if (c.contains("name_question")) {
            const int got = coop::NameQuestion(c["name_question"].get<std::string>());
            if (got != c.at("expect").get<int>()) wrong(c, std::to_string(got));
        } else if (c.contains("called")) {
            // {"called": ["line", "name"], "expect": true, "rest": "..."}
            std::string rest;
            const bool got = coop::CalledBy(c["called"][0].get<std::string>(), c["called"][1].get<std::string>(), &rest);
            bool ok = got == c.at("expect").get<bool>();
            if (got && c.contains("rest")) ok = ok && rest == c["rest"].get<std::string>();
            if (!ok) wrong(c, std::string(got ? "true" : "false") + " rest \"" + rest + "\"");
        } else if (c.contains("address")) {
            const std::string got = coop::WithAddress(c["address"][0].get<std::string>(), c["address"][1].get<std::string>());
            if (got != c.at("expect").get<std::string>()) wrong(c, got);
        } else if (c.contains("colours")) {
            const std::vector<std::string> got = coop::ColoursIn(coop::MemoryWords(coop::MemoryNorm(c["colours"].get<std::string>())));
            if (got != c.at("expect").get<std::vector<std::string>>()) wrong(c, json(got).dump());
        } else if (c.contains("spans")) {
            const std::string line = c["spans"].get<std::string>();
            std::vector<std::string> got;
            bool spans_ok = true;
            for (const coop::SpanWord& w : coop::SpanWords(line)) {
                got.push_back(w.norm);
                spans_ok = spans_ok && coop::MemoryNorm(line.substr(w.begin, w.end - w.begin)) == w.norm;
            }
            if (got != c.at("expect").get<std::vector<std::string>>() || !spans_ok) wrong(c, json(got).dump() + (spans_ok ? "" : " (a span's text differs)"));
        } else {
            wrong(c, "an unknown case");
        }
    }
    std::printf("teach tests: %zu cases, %zu wrong\n", n, bad);
    return bad ? 1 : 0;
}

// --memory-store-tests DIR: the long-term memory's store (bot_memory.h) on its own, in DIR (made anew, removed after). Each
// check prints ok or FAIL with what it got; exit 1 on any FAIL, 2 when this coop_cli has no memory (built without Wick)
int RunMemoryStoreTests(const std::string& dir_utf8) {
    namespace fs = std::filesystem;
    auto u8 = [](const std::string& s) { return fs::u8path(s); };   // C++17: a UTF-8 path
    const fs::path dir = u8(dir_utf8);
    std::error_code ec;
    fs::remove_all(dir, ec);
    fs::create_directories(dir, ec);
    // the player's folder named in Cyrillic: the path goes from UTF-8 to the file system as it is
    const std::string sub = dir_utf8 + "/\xD0\xBF\xD0\xB0\xD0\xBC\xD1\x8F\xD1\x82\xD1\x8C";   // память
    const std::string file = sub + "/player.mv2s";
    size_t bad = 0, n = 0;
    auto check = [&](const char* what, bool ok, const std::string& got = {}) {
        ++n;
        if (!ok) ++bad;
        std::printf("  %s %s%s\n", ok ? "ok  " : "FAIL", what, ok || got.empty() ? "" : ("  -- got " + got).c_str());
    };
    // everything kept, "path" aside
    auto state = [](const coop::BotMemory& m) {
        json j = MemoryJson(m);
        j.erase("path");
        return j.dump();
    };
    std::string err;
    {
        coop::BotMemory probe;
        if (!probe.Open(file, &err) && err.find("without Wick") != std::string::npos)
            return std::printf("memory store tests: %s\n", err.c_str()), 2;
    }
    fs::remove_all(u8(sub), ec);

    coop::BotMemory a;
    check("a new file in a folder named in Cyrillic", a.Open(file, &err) && a.IsOpen() && fs::exists(u8(file)), err);
    check("a new file is small (the write-ahead log 1 MiB, not 256)", fs::file_size(u8(file), ec) < 2u * 1024 * 1024,
          std::to_string(fs::file_size(u8(file), ec)));
    const coop::MemoryLine l1{"en", "banana", {"follow me"}, "FOLLOW_ME", "voice", 0, 0};
    const coop::MemoryLine l2{"en", "mango smoothie now", {"hold position"}, "HOLD_POSITION", "voice", 0, 0};
    const coop::MemoryLine l3{"ru", "\xD0\xB1\xD0\xB0\xD0\xBD\xD0\xB0\xD0\xBD", {"Follow me."}, "FOLLOW_ME", "voice", 0, 0};   // банан
    const coop::MemoryLine chain{"en", "storm it", {"throw a flashbang in the room", "go in"}, "FLASH", "cmd", 0, 0};
    const bool kept = a.KeepLine(l1, &err) && a.KeepLine(l2, &err) && a.KeepLine(l3, &err) && a.KeepLine(chain, &err) &&
                      a.KeepName({"/Game/Maps/L_Test", "Marker_4", "en", "workbench", 0}, &err) &&
                      a.KeepName({"/Game/Maps/L_Test", "Marker_4", "ru", "\xD0\xB2\xD0\xB5\xD1\x80\xD1\x81\xD1\x82\xD0\xB0\xD0\xBA", 0}, &err) &&
                      a.KeepColour({"/Game/Maps/L_Test", "Crate_2/crate", "green", 0}, &err);
    check("lines, names in two languages, a colour kept", kept && a.Lines().size() == 4 && a.Names().size() == 2 && a.Colours().size() == 1, err);
    const coop::MemoryLine* got = a.LineFor("en", "banana");
    check("the same words", got && got->lines == std::vector<std::string>{"follow me"} && got->intent == "FOLLOW_ME");
    got = a.LineFor("en", "mango smoothie now please");
    check("one word more (3+ words)", got && got->heard == "mango smoothie now");
    got = a.LineFor("en", "mango now");
    check("one word less, 2 words left: no", got == nullptr);
    check("two words more: no", a.LineFor("en", "mango smoothie now right now please") == nullptr);
    check("a short line: the same words only", a.LineFor("en", "banana please") == nullptr);
    check("another language: no", a.LineFor("es", "banana") == nullptr && a.LineFor("ru", "banana") == nullptr);
    check("a Russian line in Russian", a.LineFor("ru", "\xD0\xB1\xD0\xB0\xD0\xBD\xD0\xB0\xD0\xBD") != nullptr);
    got = a.LineFor("en", "storm it");
    check("a line of two orders keeps both, in order", got && got->lines.size() == 2 && got->lines[1] == "go in");
    coop::MemoryLine l1b = l1;
    l1b.lines = {"come here"};
    l1b.intent = "MOVE_TO";
    check("a new meaning replaces the old one", a.KeepLine(l1b, &err) && a.Lines().size() == 4 && a.LineFor("en", "banana")->lines[0] == "come here", err);
    bool removed = true;
    check("the first doubt keeps the line", a.DoubtLine("en", "banana", &removed, &err) && !removed && a.LineFor("en", "banana")->doubts == 1, err);
    check("the second doubt forgets it", a.DoubtLine("en", "banana", &removed, &err) && removed && a.LineFor("en", "banana") == nullptr, err);
    err = "x";
    check("forgetting a line never kept: false, no error", !a.ForgetLine("en", "kiwi", &err) && err.empty(), err);
    bool any = false;
    check("forgetting a thing: its names in every language and its colour stays",
          a.ForgetThing("/Game/Maps/L_Test", "Marker_4", &any, &err) && any && a.Names().empty() && a.Colours().size() == 1, err);
    check("a thing never named: nothing to forget", a.ForgetThing("/Game/Maps/L_Test", "Marker_9", &any, &err) && !any, err);
    check("a name is per map", a.KeepName({"/Game/Maps/L_Other", "Marker_4", "en", "shed", 0}, &err) &&
                                   a.ForgetThing("/Game/Maps/L_Test", "Marker_4", &any, &err) && !any && a.Names().size() == 1, err);
    a.KeepName({"/Game/Maps/L_Test", "Marker_4", "en", "workbench", 0}, &err);
    a.KeepName({"/Game/Maps/L_Test", "Marker_4", "en", "bench", 0}, &err);
    check("one name a thing and language: the new one replaces it", a.Names().size() == 2, std::to_string(a.Names().size()));
    // the bot's name and the player's (2026-10-31): one each, a new one replaces the old, forgetting one leaves the other
    const bool people = a.KeepPerson({"bot", "Rex", 0}, &err) && a.KeepPerson({"bot", "\xD0\xA0\xD0\xB5\xD0\xBA\xD1\x81", 0}, &err) &&   // Рекс
                        a.KeepPerson({"player", "Tim", 0}, &err) && a.KeepPerson({"player", "Joe", 0}, &err);
    check("the bot's name and the player's, a new one replacing the old",
          people && a.People().size() == 2 && a.PersonFor("bot") && a.PersonFor("bot")->name == "\xD0\xA0\xD0\xB5\xD0\xBA\xD1\x81" &&
              a.PersonFor("player") && a.PersonFor("player")->name == "Joe" && a.Names().size() == 2, err);
    check("forgetting the player's name leaves the bot's", a.ForgetPerson("player", &any, &err) && any && !a.PersonFor("player") &&
                                                                a.PersonFor("bot") != nullptr, err);
    check("a name never given: nothing to forget", a.ForgetPerson("player", &any, &err) && !any, err);
    a.KeepPerson({"player", "Tim", 0}, &err);
    const std::string kept_state = state(a);
    const int64_t at = a.Lines().front().at_ms;

    coop::BotMemory b;
    check("the file held by an open store: another store is refused", !b.Open(file, &err) && err.find("lease already held") != std::string::npos, err);
    a.Close();
    check("after it closes, it opens", b.Open(file, &err), err);
    check("everything read back by a new store", state(b) == kept_state);
    if (state(b) != kept_state) std::printf("       kept: %s\n       read: %s\n", kept_state.c_str(), state(b).c_str());
    check("a line's time read back", !b.Lines().empty() && b.Lines().front().at_ms == at);

    // compaction: every commit leaves the old table of contents behind; a file over 4 MiB is written anew at open
    for (int i = 0; i < 450; ++i) b.KeepLine({"en", "word number " + std::to_string(i), {"follow me"}, "FOLLOW_ME", "cmd", 0, 0}, &err);
    const auto big = fs::file_size(u8(file), ec);
    const std::string many = state(b);
    const size_t lines_before = b.Lines().size();
    b.Close();
    check("450 writes grow the file past 4 MiB", big > 4u * 1024 * 1024, std::to_string(big));
    coop::BotMemory c;
    check("opened again: compacted under 2 MiB", c.Open(file, &err) && fs::file_size(u8(file), ec) < 2u * 1024 * 1024,
          err + " " + std::to_string(fs::file_size(u8(file), ec)));
    check("compaction keeps every fact and its time", c.Lines().size() == lines_before && state(c) == many,
          std::to_string(c.Lines().size()) + " lines");
    c.Close();

    // a compaction cut short between its two renames: the old file is .bak, the new one not yet in its place
    fs::rename(u8(file), u8(file + ".bak"), ec);
    coop::BotMemory d;
    check("a cut-short compaction: the .bak is taken back", d.Open(file, &err) && d.Lines().size() == lines_before && !fs::exists(u8(file + ".bak")), err);
    d.Close();

    // files the store cannot read: put aside, not lost, and a new memory starts
    auto unreadable = [&](const char* what, const std::string& name, const std::string& bytes) {
        const std::string f = sub + "/" + name;
        {
            std::ofstream o(u8(f), std::ios::binary);
            o << bytes;
        }
        coop::BotMemory m;
        const bool opened = m.Open(f, &err);
        const bool aside = !m.PutAside().empty() && fs::exists(u8(m.PutAside()));
        check(what, opened && m.Lines().empty() && aside, err + " aside: " + m.PutAside());
        const bool keeps = opened && m.KeepLine(l1, &err);
        m.Close();
        coop::BotMemory again;
        check("... and the new memory keeps what it is taught", keeps && again.Open(f, &err) && again.Lines().size() == 1, err);
    };
    unreadable("an empty file: put aside, a new memory", "empty.mv2s", "");
    unreadable("a file of garbage: put aside, a new memory", "garbage.mv2s", std::string(4096, '\x5A'));
    {
        // a real file cut in half (a crash while it was written)
        std::ifstream in(u8(file), std::ios::binary);
        std::string bytes((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
        bytes.resize(bytes.size() / 2);
        const std::string f = sub + "/cut.mv2s";
        {
            std::ofstream o(u8(f), std::ios::binary);
            o << bytes;
        }
        coop::BotMemory m;
        const bool opened = m.Open(f, &err);
        check("a file cut in half: it opens (repaired or put aside), no crash", opened, err);
        std::printf("       (cut in half: %s, %zu lines)\n", m.PutAside().empty() ? "repaired" : "put aside", m.Lines().size());
    }
    fs::remove_all(dir, ec);
    std::printf("memory store tests: %zu checks, %zu failed\n", n, bad);
    return bad ? 1 : 0;
}

// --bro-check FILE (tools/bro_tests.json): [{"line": "...", "expect": "on" | "off" | "none"}, ...], what the habit reads in
// each line (bro.h); every line that reads otherwise is printed. Exit 1 on any
int RunBroCheck(const std::string& path) {
    std::ifstream f(path);
    if (!f) return std::fprintf(stderr, "cannot read %s\n", path.c_str()), 2;
    json cases;
    try {
        f >> cases;
    } catch (const std::exception& e) {
        return std::fprintf(stderr, "%s: %s\n", path.c_str(), e.what()), 2;
    }
    size_t bad = 0;
    for (const json& c : cases) {
        const std::string line = c.at("line").get<std::string>(), expect = c.at("expect").get<std::string>();
        const coop::BroHabit::Heard h = coop::BroHabit::Read(line);
        const std::string got = h == coop::BroHabit::Heard::On ? "on" : h == coop::BroHabit::Heard::Off ? "off" : "none";
        if (got != expect) {
            ++bad;
            std::printf("  %-48s expected %-4s got %s\n", line.c_str(), expect.c_str(), got.c_str());
        }
    }
    // the habit over time: the brat persona comes back 30 s after it is stopped, the plain bot does not
    coop::BroHabit persona, plain;
    persona.Configure(true, 30);
    plain.Configure(false, 0);
    persona.Hear("не называй меня брат", 10);
    plain.Hear("bro", 10);
    plain.Hear("stop calling me bro", 11);
    const bool timing = !persona.Active(20) && persona.Active(41) && persona.TakeRelapse() && !plain.Active(100);
    std::printf("bro check: %zu lines, %zu wrong; the 30 s relapse %s\n", cases.size(), bad, timing ? "ok" : "WRONG");
    return bad || !timing ? 1 : 0;
}

// --replies-check FILE: every template of the table, with every value of each of its slots, translated back: a template or
// a slot form the table lacks shows here, not in a player's game. Prints each failure and a few samples.
int RunRepliesCheck(const coop::Localizer& replies) {
    const std::vector<std::string> ex = replies.Examples();
    size_t bad = 0;
    for (size_t i = 0; i < ex.size(); ++i) {
        std::string out, missing;
        if (!replies.Translate(ex[i], &out, &missing)) {
            if (++bad <= 40) std::printf("  NO  \"%s\" (sentence \"%s\")\n", ex[i].c_str(), missing.c_str());
        } else if (i % 97 == 0) {
            std::printf("  ok  \"%s\" -> \"%s\"\n", ex[i].c_str(), out.c_str());
        }
    }
    std::printf("replies check (%s): %zu of %zu example lines translated\n", replies.Language().c_str(), ex.size() - bad, ex.size());
    return bad ? 1 : 0;
}

int RunServe(Model& m, const coop::SpeechOptions& speech, int threads, bool want_stt, bool want_tts, const coop::VoiceOptions* piper,
             const coop::VoiceOptions* local_voice) {
    Chat chat(m);
    chat.why = false;
    std::string err;
    Loading("the planner");
    if (!chat.Init(&err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    bool stt_ready = false, mic_ready = false, tts_ready = false;
    std::string stt_note, mic_note, tts_note, tts_kind;
    // the bot's voice as audio for the game (Piper): made on a thread of its own, so that a line being made never
    // holds up the talk key; one line at a time, three waiting at most
    bool piper_ready = false, local_ready = false;
    std::string local_note, tts_provider, local_provider;   // where the voices run: "cpu" or "cuda" (--tts-provider)
#ifdef COOP_WITH_STT
    coop::PiperVoice voice, voice_local;
    if (piper) {
        Loading("the voice");
        piper_ready = voice.Load(*piper, &err);
        tts_ready = piper_ready;
        tts_note = piper_ready ? voice.Describe() : err;
        if (piper_ready) tts_provider = voice.Provider();
        if (piper_ready) tts_kind = "piper";
    }
    // the player's language's voice (--voice-local): the lines written in it are said with it
    if (piper_ready && local_voice) {
        Loading("the voice in the player's language");
        local_ready = voice_local.Load(*local_voice, &err);
        local_note = local_ready ? voice_local.Describe() : err;
        if (local_ready) local_provider = voice_local.Provider();
    }
#else
    if (piper) tts_note = "this coop_cli was built without sherpa-onnx: no Piper voice";
#endif
    (void)local_voice;
    // more voices of the player's language (--voice-local-extra): loaded when its own voice is
    json extra_info = json::object();
#ifdef COOP_WITH_STT
    std::map<std::string, std::unique_ptr<coop::PiperVoice>> voices_extra;
    if (local_ready && !g_voice_local_extra.empty()) {
        Loading("more voices in the player's language");
        for (const auto& [name, options] : g_voice_local_extra) {
            auto v = std::make_unique<coop::PiperVoice>();
            std::string verr;
            if (v->Load(options, &verr)) {
                extra_info[name] = {{"voice", v->Describe()}, {"speakers", v->NumSpeakers()}, {"provider", v->Provider()}};
                voices_extra[name] = std::move(v);
            } else {
                extra_info[name] = {{"error", verr}};
            }
        }
    }
#endif
    struct SpeechJob {
        json id;
        std::string text, speaker;   // speaker: of the voice the line is said with (a local voice's own, for a local line)
        float speed = 0;
        bool local = false;   // in the player's language, with voice_local
        std::string voiced;   // the text as the voice says it (Pronounced); empty: text
        bool stream = false;  // "say"'s "stream": each sentence but the last goes out as soon as it is made ("speech_part")
        std::string local_name;   // a local line: one of the --voice-local-extra voices ("local_voice"); empty: voice_local
        std::string lang;         // the line's language (its "lang" event field)
    };
    std::mutex out_mutex, jobs_mutex;
    std::condition_variable jobs_cv;
    std::deque<SpeechJob> jobs;
    bool jobs_done = false;
    bool making = false;                    // the speaker thread is making a line (under jobs_mutex)
    std::atomic<bool> stop_making{false};   // a hush came while it was: the rest of that line is not made
    std::thread speaker;
#ifdef COOP_WITH_STT
    coop::SpeechRecognizer stt;
    if (want_stt) {
        Loading("speech recognition");
        stt_ready = LoadSpeech(stt, speech, &err);
        if (!stt_ready) stt_note = err;
    } else {
        stt_note = "switched off (--no-stt)";
    }
#ifdef _WIN32
    MicCapture mic;
    if (stt_ready) {
        Loading("the microphone");
        mic_ready = mic.Start(&err);
        if (!mic_ready) mic_note = err;
    }
#else
    mic_note = "the microphone is read only on Windows so far";
#endif
#else
    (void)speech;
    (void)want_stt;
    stt_note = "this coop_cli was built without speech-to-text";
#endif
#ifdef _WIN32
    Tts tts;
    // the system's voice (--tts): when no Piper voice was asked for, or the one asked for did not load
    const bool system_voice = want_tts && !piper_ready;
    if (system_voice) {
        const std::string piper_failed = piper ? tts_note : std::string();
        tts_ready = tts.Start(&err);
        tts_note = (tts_ready ? tts.Voice() : err) + (piper_failed.empty() ? "" : " (the Piper voice did not load: " + piper_failed + ")");
        if (tts_ready) tts_kind = "system";
    }
#else
    const bool system_voice = false;
    (void)want_tts;
#endif
    // the speaker thread writes too: one line at a time on stdout
    auto send = [&out_mutex](const json& j) {
        const std::string s = j.dump(-1, ' ', false, json::error_handler_t::replace);
        std::lock_guard<std::mutex> lock(out_mutex);
        std::fputs(s.c_str(), stdout);
        std::fputc('\n', stdout);
        std::fflush(stdout);
    };
#ifdef COOP_WITH_STT
    if (piper_ready) {
        speaker = std::thread([&] {
            {   // the first line a fresh model makes takes four times as long as the next ones: not the player's
                std::vector<float> x;
                std::string warm_err;
                voice.Speak("Ready.", &x, &warm_err);
                std::string ready;
                if (local_ready && g_replies && g_replies->Translate("Ready.", &ready)) voice_local.Speak(ready, &x, &warm_err);
            }
            for (;;) {
                SpeechJob job;
                {
                    std::unique_lock<std::mutex> lock(jobs_mutex);
                    making = false;
                    jobs_cv.wait(lock, [&] { return jobs_done || !jobs.empty(); });
                    if (jobs.empty()) return;   // done, and nothing left to say
                    job = std::move(jobs.front());
                    jobs.pop_front();
                    making = true;
                    stop_making = false;
                }
                const auto t0 = Clock::now();
                std::vector<float> x;
                std::string speak_err;
                const coop::PiperVoice* chosen = job.local ? &voice_local : &voice;
                if (job.local && !job.local_name.empty()) {
                    auto extra = voices_extra.find(job.local_name);
                    // a voice of another language than the player's (a person who speaks their own, 2026-11-14): its folder beside
                    // the bot's voice, loaded once, the first time a line wants it (a second or so)
                    if (extra == voices_extra.end() && piper && job.local_name.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789_") == std::string::npos) {
                        coop::VoiceOptions o = local_voice ? *local_voice : *piper;
                        o.model_dir = (std::filesystem::u8path(piper->model_dir).parent_path() / job.local_name).u8string();
                        o.speaker.clear();
                        o.lang.clear();
                        if (!local_voice) o.threads = std::max(piper->threads, 4);
                        auto v = std::make_unique<coop::PiperVoice>();
                        std::string verr;
                        const auto l0 = Clock::now();
                        if (v->Load(o, &verr)) {
                            std::fprintf(stderr, "voice %s loaded for a line in %s (%.0f ms)\n", job.local_name.c_str(), job.lang.c_str(), Ms(Clock::now() - l0));
                            extra = voices_extra.emplace(job.local_name, std::move(v)).first;
                        } else {
                            std::fprintf(stderr, "voice %s: %s\n", job.local_name.c_str(), verr.c_str());
                            voices_extra.emplace(job.local_name, nullptr);
                        }
                        extra = voices_extra.find(job.local_name);
                    }
                    if (extra != voices_extra.end() && extra->second) chosen = extra->second.get();
                    else if (!local_ready || job.lang != (g_replies ? g_replies->Language() : std::string("en"))) {
                        // no voice for that language here: the line is not said (the player's language's voice would garble it)
                        send({{"event", "hushed"}, {"id", job.id}});
                        continue;
                    }
                }
                const coop::PiperVoice& v = *chosen;
                const int rate = v.SampleRate();
                auto line_event = [&](const char* name) {   // the fields every event of the line has
                    return json{{"event", name}, {"id", job.id}, {"text", job.text}, {"voiced", job.voiced.empty() ? json(nullptr) : json(job.voiced)},
                                {"lang", !job.lang.empty() ? job.lang : job.local && g_replies ? g_replies->Language() : std::string("en")}, {"rate", rate}};
                };
                // streamed (2026-11-04): each sentence but the last goes out as it is made, so the game plays the first while the
                // next is made; the last goes with "speech", which ends the line. A line of one sentence is one "speech", as before
                int parts = 0;
                double first_ms = -1;
                std::vector<float> last;
                const auto on_sentence = [&](const float* s, size_t n, bool is_last) {
                    if (stop_making) return false;   // hushed: the rest is not made
                    if (!job.stream) return true;
                    if (is_last) {
                        last.assign(s, s + n);
                        return true;
                    }
                    const double ms = Ms(Clock::now() - t0);
                    if (parts == 0) first_ms = ms;
                    json part = line_event("speech_part");
                    part["part"] = parts++;
                    part["audio_s"] = rate > 0 ? static_cast<double>(n) / rate : 0.0;
                    part["ms"] = ms;
                    part["pcm16"] = Base64(Pcm16(std::vector<float>(s, s + n)));
                    send(part);
                    return true;
                };
                bool stopped = false;
                if (!v.Speak(job.voiced.empty() ? job.text : job.voiced, &x, &speak_err, job.speaker, job.speed, on_sentence, &stopped)) {
                    send({{"event", "error"}, {"id", job.id}, {"cmd", "say"}, {"message", speak_err}});
                    continue;
                }
                if (stopped) {
                    send({{"event", "hushed"}, {"id", job.id}});
                    continue;
                }
                json done = line_event("speech");
                done["audio_s"] = rate > 0 ? static_cast<double>(x.size()) / rate : 0.0;   // the whole line
                done["ms"] = Ms(Clock::now() - t0);
                if (parts > 0) {   // the sentences before it went as "speech_part": this one carries the last
                    done["part"] = parts;
                    done["parts"] = parts + 1;
                    done["first_ms"] = first_ms;
                    done["pcm16"] = Base64(Pcm16(last));
                } else {
                    done["pcm16"] = Base64(Pcm16(x));
                }
                send(done);
            }
        });
    }
#endif
    // the lines not made yet are dropped, and whoever asked for them is told; the one being made stops after its sentence
    auto drop_lines = [&]() {
        std::lock_guard<std::mutex> lock(jobs_mutex);
        for (const SpeechJob& j : jobs) send({{"event", "hushed"}, {"id", j.id}});
        jobs.clear();
        if (making) stop_making = true;
    };
    struct JoinSpeaker {   // every way out of the loop below ends the speaker thread
        std::function<void()> f;
        ~JoinSpeaker() { f(); }
    } join_speaker{[&] {
        {
            std::lock_guard<std::mutex> lock(jobs_mutex);
            jobs_done = true;
        }
        jobs_cv.notify_all();
        if (speaker.joinable()) speaker.join();
    }};
    // the open microphone (2026-11-01, the owner: no talk key, the bot hears a line when it is called by its name): Silero VAD
    // cuts phrases out of what the microphone hears (or a script's clips, "mic_wav"), on a thread of its own; the game is told
    // of each ("speech_end") and sends it back with its world ("vad_up"), which recognizes it here, on the main thread
    bool vad_ready = false;
    std::string vad_note = g_vad_model.empty() ? "no --vad" : "";
#ifdef COOP_WITH_STT
    coop::VoiceActivity vad;
    struct OpenMic {
        std::mutex lock;
        bool on = false, script = false, key = false, reload = false, quit = false;
        coop::VadOptions options;
        std::deque<float> clip;                        // "mic_wav": heard at the pace of the clock
        std::map<long long, coop::VadPhrase> phrases;  // cut, until the game's "vad_up"
        long long next = 1;
    } open;
    if (stt_ready && !g_vad_model.empty()) {
        open.options.model = g_vad_model;
        vad_ready = vad.Load(open.options, &err);
        if (!vad_ready) vad_note = err;
    } else if (!stt_ready && !g_vad_model.empty()) {
        vad_note = "no speech-to-text";
    }
    std::thread open_thread;
    if (vad_ready) {
        open_thread = std::thread([&] {
            auto last = Clock::now();
            bool tapping = false;
            std::vector<float> heard;
            // what the detector was given, the last 30 s: a phrase goes with a little before and after it (the detector's cut
            // takes the first consonant off: «Стой здесь» was heard as «то есть здесь»), as the talk key's pre-roll and tail
            std::deque<float> given;
            long long given_from = 0;   // the index of given.front() in the detector's count
            constexpr double kBefore = 0.30, kAfter = 0.15;
            for (;;) {
                std::this_thread::sleep_for(std::chrono::milliseconds(30));
                const auto now = Clock::now();
                const size_t due = static_cast<size_t>(Ms(now - last) * coop::VoiceActivity::kSampleRate / 1000.0);
                last = now;
                bool on = false, script = false, key = false, reload = false;
                coop::VadOptions options;
                heard.clear();
                {
                    std::lock_guard<std::mutex> g(open.lock);
                    if (open.quit) break;
                    on = open.on, script = open.script, key = open.key, reload = open.reload, options = open.options;
                    open.reload = false;
                    if (on && script) {   // the script's clip as the time goes by, silence after it
                        const size_t n = std::min(due, open.clip.size());
                        heard.assign(open.clip.begin(), open.clip.begin() + static_cast<std::ptrdiff_t>(n));
                        open.clip.erase(open.clip.begin(), open.clip.begin() + static_cast<std::ptrdiff_t>(n));
                        heard.resize(due, 0.0f);
                    }
                }
#ifdef _WIN32
                const bool tap = on && !script && mic_ready;
                if (tap != tapping) mic.Tap(tap), tapping = tap;
                if (tap) mic.Drain(&heard);
#endif
                if (reload) {
                    std::string reload_err;
                    if (!vad.Load(options, &reload_err)) send({{"event", "error"}, {"id", nullptr}, {"cmd", "open_mic"}, {"message", reload_err}});
                }
                if (!on || key) {   // off, or the talk key's clip: nothing is cut
                    if (vad.Fed() > 0 || !given.empty()) vad.Reset(), given.clear(), given_from = 0;
                    continue;
                }
                vad.Accept(heard.data(), heard.size());
                given.insert(given.end(), heard.begin(), heard.end());
                const size_t keep = 30 * coop::VoiceActivity::kSampleRate;
                if (given.size() > keep) {
                    given_from += static_cast<long long>(given.size() - keep);
                    given.erase(given.begin(), given.begin() + static_cast<std::ptrdiff_t>(given.size() - keep));
                }
                coop::VadPhrase phrase;
                while (vad.Pop(&phrase)) {
                    const double rate = coop::VoiceActivity::kSampleRate;
                    const long long given_to = given_from + static_cast<long long>(given.size());
                    const long long from = std::max(given_from, phrase.start - static_cast<long long>(kBefore * rate));
                    const long long to = std::min(given_to, phrase.start + static_cast<long long>(phrase.samples.size()) + static_cast<long long>(kAfter * rate));
                    if (from < to) phrase.samples.assign(given.begin() + static_cast<std::ptrdiff_t>(from - given_from), given.begin() + static_cast<std::ptrdiff_t>(to - given_from));
                    const double audio_s = static_cast<double>(phrase.samples.size()) / rate;
                    const double start_ago = static_cast<double>(given_to - (from < to ? from : phrase.start)) / rate;
                    long long seg = 0;
                    {
                        std::lock_guard<std::mutex> g(open.lock);
                        seg = open.next++;
                        open.phrases[seg] = std::move(phrase);
                        while (open.phrases.size() > 8) open.phrases.erase(open.phrases.begin());   // the game never asked
                    }
                    auto r3 = [](double x) { return std::round(x * 1000) / 1000; };
                    send({{"event", "speech_end"}, {"seg", seg}, {"audio_s", r3(audio_s)}, {"start_ago_s", r3(start_ago)},
                          {"end_ago_s", r3(std::max(0.0, start_ago - audio_s))}});
                    phrase = coop::VadPhrase();
                }
            }
#ifdef _WIN32
            if (tapping) mic.Tap(false);
#endif
        });
    }
    struct JoinOpen {   // every way out of the loop below ends the open microphone's thread
        std::function<void()> f;
        ~JoinOpen() { f(); }
    } join_open{[&] {
        {
            std::lock_guard<std::mutex> g(open.lock);
            open.quit = true;
        }
        if (open_thread.joinable()) open_thread.join();
    }};
#endif
    send({{"event", "ready"}, {"bot", m.dir}, {"labels", m.cfg.labels}, {"gate", m.cfg.gate}, {"threshold", chat.brain.threshold},
          {"threads", threads}, {"runtime", coop::OrtBackend::RuntimeVersion()}, {"stt", stt_ready}, {"stt_note", stt_note},
          {"mic", mic_ready}, {"mic_note", mic_note}, {"tts", tts_ready}, {"tts_note", tts_note},
          {"vad", vad_ready}, {"vad_note", vad_note},
          {"tts_kind", tts_kind.empty() ? json(nullptr) : json(tts_kind)},
          {"replies", g_replies ? json({{"language", g_replies->Language()}, {"templates", g_replies->Templates()}}) : json(nullptr)},
          {"bro", g_bro_replies ? json({{"active", g_replies == g_bro_replies}, {"relapse_s", g_bro.RelapseSeconds()},
                                        {"templates", g_bro_replies->Templates()}}) : json(nullptr)},
          {"place_objects", chat.brain.Places().ObjectIds()},   // what the game may send as a place's object (bot v62: teleport)
          {"place_qualifiers", chat.brain.Places().QualifierIds()},   // ... and as its qualifier (bot v64: big, small, cardboard)
          {"voice_local", local_ready}, {"voice_local_note", local_note},
          {"voice_local_extra", extra_info},   // --voice-local-extra: name -> voice, speakers, provider (or error)
          {"tts_provider", tts_provider.empty() ? json(nullptr) : json(tts_provider)},
          {"voice_local_provider", local_provider.empty() ? json(nullptr) : json(local_provider)},
          {"tts_threads", tts_provider.empty() ? json(nullptr) : json(piper->threads)},   // the voices' CPU threads
          {"voice_local_threads", local_provider.empty() ? json(nullptr) : json(local_voice->threads)},
          {"chain", g_chain ? json({{"dir", g_chain->dir}, {"router", g_chain->router != nullptr}, {"cut", g_chain->cut},
                                    {"decoder", Chain::Backend()}, {"gpu", g_chain->decoder_options.gpu_layers != 0},
                                    {"memory_lines", g_chain->memory_lines}, {"memory_seconds", g_chain->memory_seconds}})
                            : json(nullptr)},
          {"language", g_language},
          {"memory", g_memory && g_memory->IsOpen() ? json({{"path", g_memory->Path()}, {"lines", g_memory->Lines().size()},
                                                            {"names", g_memory->Names().size()}, {"colours", g_memory->Colours().size()},
                                                            {"put_aside", g_memory->PutAside().empty() ? json(nullptr) : json(g_memory->PutAside())}})
                                                     : json(nullptr)},
          {"memory_note", g_memory_note},
          // the bot's settings the player set by voice (follow_m, engage_m, fire_on_command, voice_speed): the game applies them
          {"behaviour", Chat::SettingsJson()},
          // the names the player gave (2026-10-31): the game shows the bot's over it; null: none kept
          {"names", {{"bot", g_memory && g_memory->IsOpen() && g_memory->PersonFor("bot") ? json(g_memory->PersonFor("bot")->name) : json(nullptr)},
                     {"player", Chat::PlayerName().empty() ? json(nullptr) : json(Chat::PlayerName())}}},
          {"decider", g_decider ? json({{"dir", g_decider->dir}, {"mode", g_decider->mode}, {"source", g_decider->source},
                                        {"threads", g_decider->options.threads}, {"gpu", g_decider->options.gpu_layers != 0}})
                                : json(nullptr)},
          // the talk in a role (talker.h): where it was found, the model, where it runs, the roles
          {"talk", g_talk ? json({{"dir", g_talk->dir}, {"found", g_talk->found}, {"model", g_talk->options.model_path},
                                  {"gpu", g_talk->options.gpu_layers != 0}, {"threads", g_talk->options.threads},
                                  {"roles", g_talk->RoleNames()}, {"load_ms", std::round(g_talk->load_ms)}})
                          : json(nullptr)},
          {"talk_note", g_talk_note}});
    bool listening = false;
    Clock::time_point down = Clock::now();
    std::string last_to = "bot";   // whom the line before was said to (the game's "to"; the bot when none)
    for (std::string line; std::getline(std::cin, line);) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty()) continue;
        json q;
        try {
            q = json::parse(line);
        } catch (const std::exception& e) {
            send({{"event", "error"}, {"id", nullptr}, {"cmd", ""}, {"message", std::string("not a JSON line: ") + e.what()}});
            continue;
        }
        const std::string cmd = q.is_object() ? q.value("cmd", std::string()) : std::string();
        const json id = q.is_object() && q.contains("id") ? q["id"] : json(nullptr);
        auto fail = [&](const std::string& message) { send({{"event", "error"}, {"id", id}, {"cmd", cmd}, {"message", message}}); };
        try {
            if (q.contains("world") && !q["world"].is_null()) {   // the world the line is said in
                coop::WorldState w;
                if (!ParseWorld(q["world"], &w, &err) || !chat.planner.SetWorld(w, &err)) {
                    fail(err);
                    continue;
                }
            }
            // whom the line is said to (the game's "to", talker.h): the bot when none
            const std::string to = q.is_object() ? q.value("to", std::string()) : std::string();
            // who may be called by name, and the key of the one the line is said to (2026-11-12; see "callees" above)
            const json callees = q.is_object() && q.contains("callees") ? q["callees"] : json(nullptr);
            const std::string to_key = q.is_object() ? q.value("to_key", std::string()) : std::string();
            // why the line is said to them (2026-11-15): "look", the person under the crosshair, not called by name: an order there is
            // the bot's (readdress), talk is theirs; "question", their question is open; none: called by name, or the game's own
            const std::string to_by = q.is_object() ? q.value("to_by", std::string()) : std::string();
            // a heard or typed line through the classifier and the planner
            // words: the transcript's words with their start times (SpeechWord); clip_start: where the clip's second 0 is from
            // the talk key going down (the microphone's pre-roll comes before it)
            auto respond = [&](const std::string& raw, bool spoken, double audio_s, double stt_ms,
                               const std::vector<coop::SpeechWord>* words = nullptr, double clip_start = 0) {
                const std::string heard = StripPy(raw);
                if (heard.empty()) {
                    send({{"event", "nothing"}, {"id", id}, {"audio_s", audio_s}, {"stt_ms", stt_ms}});
                    return;
                }
                // a line that calls another by name than the one the game said it to (its "callees" and "to_key", 2026-11-12): the
                // game says it again to them, with the world as theirs ("readdress"; "far": they are out of earshot). A line that
                // calls the one it is said to: theirs, a person's without the name (the bot's Listen reads its own name)
                std::string line = heard;
                bool named_here = false;   // the person it is said to was called by name in it
                if (callees.is_array()) {
                    Callee callee;
                    std::string rest;
                    if (CalledCallee(heard, callees, chat.BotName(), &callee, &rest)) {
                        const std::string whom = to.empty() ? std::string("bot") : to;
                        if (to_key.empty() ? callee.to != whom : callee.key != to_key) {
                            json j = {{"event", "readdress"}, {"id", id}, {"heard", heard}, {"to", callee.to}, {"key", callee.key},
                                      {"name", callee.name}, {"text", rest.empty() ? heard : rest}, {"far", callee.distant},
                                      {"spoken", spoken}, {"audio_s", audio_s}, {"stt_ms", stt_ms}};
                            if (words && !words->empty()) {
                                json w = json::array();
                                for (const coop::SpeechWord& x : *words) w.push_back({{"w", x.text}, {"t", std::round(x.start * 1000) / 1000}});
                                j["words"] = std::move(w);
                                j["clip_start_s"] = clip_start;
                            }
                            send(j);
                            return;
                        }
                        if (callee.to != "bot" && !rest.empty()) line = rest;
                        named_here = callee.to != "bot";
                    }
                }
                // a line to another than the line before it (the bot, a person of the level): what the planner asked the one before
                // is not asked of this one, and the decoder's short context (the lines said to the one before, and their words back)
                // is not this talk's (2026-11-12). A line said to the one under the crosshair, not by name ("look"), may yet be the bot's
                // (an order: readdress below): the talk so far is kept as it was until it is theirs
                const bool look_only = !to.empty() && to != "bot" && to_by == "look" && !named_here;
                const std::deque<Chat::Said> said_before = chat.said;
                const Chat::Said bot_said_before = chat.bot_said;
                const int what_said_before = chat.what_said_lines;
                const std::vector<std::string> held_before = chat.held, after_go_before = chat.after_go;
                const coop::Planner::Saved planner_before = chat.planner.Save();
                auto switch_to = [&]() {
                    const std::string whom = to.empty() ? std::string("bot") : to;
                    if (whom != last_to) {
                        if (chat.planner.Mem().has_question) chat.planner.DropQuestion();
                        chat.said.clear();
                        chat.bot_said = Chat::Said();
                        last_to = whom;
                    }
                };
                if (!look_only) switch_to();
                // a line to someone else the game has (its "to": the seller at the counter, 2026-11-11): their role answers it
                // (talker.h), and the bot hears nothing of it -- no habit, no lesson, no name of the bot's
                if (!to.empty() && to != "bot") {
                    if (!g_talk || !g_talk->Ready()) {
                        fail("no talking model: " + g_talk_note);
                        return;
                    }
                    if (!g_talk->roles.count(to)) {
                        fail("no role \"" + to + "\" (talk_config.json's roles, or the game's \"role\")");
                        return;
                    }
                    // the language they speak (their own, else the player's)
                    const std::string person_lang = g_talk->roles[to].lang.empty() ? g_language : g_talk->roles[to].lang;
                    // the answer in their role; was: what the classifier made of the line, when it was asked
                    auto talk_in_role = [&](const json& was) {
                        std::string said, talk_err;
                        json info;
                        if (!chat.TalkReply(to, heard, &said, &info, &talk_err)) {
                            fail(talk_err);
                            return;
                        }
                        if (!was.is_null()) info["was"] = was;
                        said = Rephrased(said, person_lang);
                        KeepLocalized(said);
                        json turn = {{"intent", "TALK"}, {"prob", 1.0}, {"action", "talk"}, {"say", said}, {"line", heard}, {"order", nullptr},
                                     {"question", nullptr}, {"to", to}, {"talk", info}};
                        json j = turn;
                        j.erase("line");
                        j["event"] = "reply";
                        j["turns"] = json::array({turn});
                        j["id"] = id;
                        j["heard"] = heard;
                        j["spoken"] = spoken;
                        j["audio_s"] = audio_s;
                        j["stt_ms"] = stt_ms;
                        send(j);
                    };
                    if (!g_talk->roles[to].orders) {
                        switch_to();
                        talk_in_role(nullptr);   // nobody of theirs in the game takes orders: every line is talk
                        return;
                    }
                    // a body of theirs takes orders (2026-11-12, the owner: «чтобы любому NPC можно было отдать именно приказ и
                    // поговорить»): the line through the classifier, the planner and the decoder as the bot's lines go, without the
                    // bot's long-term memory, its habit or its name; their words for an order from the plain table (no «брат»),
                    // or from the «брат» one when their role has the habit (2026-11-14, "bro")
                    coop::Localizer* const replies_were = g_replies;
                    g_replies = RepliesIn(person_lang, g_talk->roles[to].bro);   // their own language's tables (none: English)
                    Chat::Heard h;
                    json turns = json::array();
                    chat.words = words ? *words : std::vector<coop::SpeechWord>();
                    chat.clip_start = clip_start;
                    const bool heard_ok = chat.Hear(line, spoken ? coop::SpeechTextForClassifier(line) : line, &h, &err,
                        [&](const Chat::Heard&, const Chat::Turn& t) {
                            json turn = ReplyJson(chat, t);
                            turn.erase("event");
                            turn["line"] = t.line;
                            double talk_p = 0;
                            for (const char* label : {"SMALL_TALK", "NONE", "BODY_STATE"}) {
                                const auto it = std::find(chat.m.cfg.labels.begin(), chat.m.cfg.labels.end(), label);
                                if (it != chat.m.cfg.labels.end() && static_cast<size_t>(it - chat.m.cfg.labels.begin()) < t.p.size())
                                    talk_p += t.p[static_cast<size_t>(it - chat.m.cfg.labels.begin())];
                            }
                            turn["talk_p"] = std::round(talk_p * 1000) / 1000;
                            if (turn.contains("say") && turn["say"].is_string())
                                turn["say"] = Rephrased(turn["say"].get<std::string>(), g_replies ? g_replies->Language() : std::string("en"));
                            turns.push_back(std::move(turn));
                        });
                    chat.words.clear();
                    g_replies = replies_were;
                    if (!heard_ok) {
                        fail(err);
                        return;
                    }
                    // hit, shoot, aim at, taunt someone (2026-11-14): whom from the player's own words (the line without their name); a
                    // taunt's words are theirs, from their role
                    // going to someone, following them (2026-11-15, «Майк, иди к Нику»): whom from the player's own words; the turns made
                    // again from them when they fit none (ApplyWordOrders)
                    const WordOrders words_said = ApplyWordOrders(line, callees, chat.BotName(), to, person_lang, &turns,
                                                                  RepliesIn(person_lang, g_talk->roles[to].bro));
                    if (words_said.rebuilt) h.note = "the turns made from the words";
                    if (words_said.went)
                        h.note += std::string(h.note.empty() ? "" : "; ") + "going to someone: " + words_said.go.kind + " " + words_said.go.target.dump();
                    MarkStand(line, &turns, RepliesIn(person_lang, g_talk->roles[to].bro));   // «встань туда»: there, not where they stand
                    bool acted = false;
                    {
                        const ActOn& act = words_said.act;
                        if (words_said.acted) {
                            acted = true;
                            h.note += std::string(h.note.empty() ? "" : "; ") + "acting on someone: " + act.kind + " " + act.target.dump();
                            if (act.intent == "TAUNT" && turns.size() == 1) {
                                std::string said, talk_err;
                                json info;
                                const std::string kind = act.target.value("kind", std::string());
                                std::string whom = kind == "speaker" ? "the player" : kind == "pointed" ? "him" : CalledIn(act.target, person_lang, 'n', chat.BotName());
                                if (whom.empty()) whom = "him";
                                if (chat.TalkReply(to, "(The player tells you to mock " + whom + " to " + (whom == "the player" ? "his" : "their") +
                                                           " face. Say one short mocking sentence to " + whom + ".)", &said, &info, &talk_err)) {
                                    said = Rephrased(said, person_lang);
                                    KeepLocalized(said);
                                    turns.at(0)["say"] = said;
                                    turns.at(0).erase("say_en");
                                    turns.at(0)["talk"] = info;
                                }
                            }
                        }
                    }
                    // "what do you see?", "where are you going?" in the player's own words: the game answers from their body
                    if (g_language != "en" && turns.size() == 1 && !turns.at(0).contains("state") && SeenInOwnWords(line)) {
                        json& only = turns.at(0);
                        only["state"] = "seen";
                        only["order"] = nullptr;
                        only["say"] = "";
                        only.erase("say_en");
                    }
                    if (g_language != "en" && turns.size() == 1 && DoingInOwnWords(line) &&
                        (!turns.at(0).contains("state") || turns.at(0).value("state", std::string()) == "how")) {
                        json& only = turns.at(0);
                        only["state"] = "doing";
                        only["order"] = nullptr;
                        only["say"] = "";
                        only.erase("say_en");
                    }
                    const bool talks = PersonTalks(turns, line, g_talk->TalkingNow(to));
                    bool asks = false;   // what they see, what they do: a question to them, answered from their body
                    for (const json& t : turns) asks = asks || (t.contains("state") && t["state"].is_string() && !t["state"].get<std::string>().empty());
                    if (look_only && !asks && (!talks || SureOrder(turns, line, g_talk->TalkingNow(to)))) {
                        // an order said while looking at them, nobody called by name (2026-11-15, the owner: «Оно не понимает, что делать
                        // именно мой бот»; «втащи ему», «встань сюда», «открыть огонь на мою метку» said at a person went to that person):
                        // the bot's, and the one under the crosshair is what it is about. The talk so far as it was; the game says the line
                        // again to the bot, with the world as the bot's (HandleReaddress)
                        chat.said = said_before;
                        chat.bot_said = bot_said_before;
                        chat.what_said_lines = what_said_before;
                        chat.held = held_before;
                        chat.after_go = after_go_before;
                        chat.planner.Restore(planner_before);
                        std::string bot_called = chat.BotName();   // (the world's "bot" is theirs now: the bot's name from the callees)
                        if (callees.is_array())
                            for (const json& c : callees)
                                if (c.is_object() && c.value("to", std::string()) == "bot" && c.contains("names") && c["names"].is_array() &&
                                    !c["names"].empty() && c["names"][0].is_string()) {
                                    bot_called = c["names"][0].get<std::string>();
                                    break;
                                }
                        json j = {{"event", "readdress"}, {"id", id}, {"heard", heard}, {"to", "bot"}, {"key", "bot"}, {"name", bot_called},
                                  {"text", heard}, {"far", false}, {"spoken", spoken}, {"audio_s", audio_s}, {"stt_ms", stt_ms},
                                  {"why", "an order with nobody called by name: the bot's"}};
                        if (words && !words->empty()) {
                            json w = json::array();
                            for (const coop::SpeechWord& x : *words) w.push_back({{"w", x.text}, {"t", std::round(x.start * 1000) / 1000}});
                            j["words"] = std::move(w);
                            j["clip_start_s"] = clip_start;
                        }
                        send(j);
                        return;
                    }
                    switch_to();   // the line is theirs: the talk is with them now
                    if (talks) {
                        // talk: what the planner asked or queued about the line is not theirs to ask (their role answers instead)
                        if (chat.planner.Mem().has_question) chat.planner.DropQuestion();
                        json was = json::array();
                        for (const json& t : turns)
                            was.push_back({{"intent", t.value("intent", json(nullptr))}, {"prob", t.value("prob", json(nullptr))},
                                           {"action", t.value("action", json(nullptr))}, {"talk_p", t.value("talk_p", json(nullptr))}});
                        talk_in_role(was);
                        return;
                    }
                    for (const json& t : turns)
                        if (t.contains("say") && t["say"].is_string() && !t["say"].get<std::string>().empty())
                            chat.HeardFromBot(t["say"].get<std::string>());   // their words, the decoder's context of this talk
                    json j = turns.at(0);   // the reply as it was before --chain: the first order's
                    j.erase("line");
                    j["event"] = "reply";
                    j["to"] = to;          // the order is theirs: the game gives it to their body
                    j["person"] = true;
                    if (g_chain) {
                        j["turns"] = std::move(turns);
                        j["chain"] = {{"route", h.route >= 0 ? json(h.route) : json(nullptr)}, {"decoded", h.decoded}, {"rewritten", h.rewritten},
                                      {"resumed", h.resumed}, {"held", h.held}, {"note", h.note}, {"route_ms", h.route_ms}, {"rewrite_ms", h.rewrite_ms}};
                    }
                    j["id"] = id;
                    j["heard"] = heard;
                    j["spoken"] = spoken;
                    j["audio_s"] = audio_s;
                    j["stt_ms"] = stt_ms;
                    if (words && !words->empty()) {
                        json w = json::array();
                        for (const coop::SpeechWord& x : *words) w.push_back({{"w", x.text}, {"t", std::round(x.start * 1000) / 1000}});
                        j["words"] = std::move(w);
                        j["clip_start_s"] = clip_start;
                    }
                    send(j);
                    return;
                }
                // the habit first, by the words as said: "stop calling me bro" is about the habit and nothing else (the
                // classifier would read it as an order: "хватит говорить брат" -> HOLD_FIRE)
                const coop::BroHabit::Heard bro = g_bro_replies ? g_bro.Hear(heard, SinceStart()) : coop::BroHabit::Heard::None;
                const char* bro_name = bro == coop::BroHabit::Heard::On ? "on" : bro == coop::BroHabit::Heard::Off ? "off" : nullptr;
                ChooseReplies();
                const bool relapsed = g_bro.TakeRelapse();
                if (bro == coop::BroHabit::Heard::Off) {
                    const std::string en = chat.Pick(kBroOff);
                    json turn = {{"intent", "SMALL_TALK"}, {"prob", 1.0}, {"action", "act"}, {"say", en}, {"line", heard},
                                 {"order", {{"intent", "SMALL_TALK"}}}, {"question", nullptr}, {"bro", "off"}};
                    std::string local;
                    if (g_replies && Localize(en, &local)) turn["say"] = local, turn["say_en"] = en;
                    json j = turn;
                    j.erase("line");
                    j["event"] = "reply";
                    j["turns"] = json::array({turn});
                    j["id"] = id;
                    j["heard"] = heard;
                    j["spoken"] = spoken;
                    j["audio_s"] = audio_s;
                    j["stt_ms"] = stt_ms;
                    j["bro_active"] = false;
                    j["bro_back_in"] = g_bro.RelapseSeconds() > 0 ? json(g_bro.RelapseSeconds()) : json(nullptr);
                    send(j);
                    return;
                }
                Chat::Heard h;
                Chat::Memo memo;
                json turns = json::array();
                chat.words = words ? *words : std::vector<coop::SpeechWord>();
                chat.clip_start = clip_start;
                const bool heard_ok = chat.Listen(heard, spoken, &h, &memo, &err, [&](const Chat::Heard&, const Chat::Turn& t) {
                        json turn = ReplyJson(chat, t);
                        turn.erase("event");
                        turn["line"] = t.line;
                        // how much the classifier sees talk in the line (SMALL_TALK + NONE + BODY_STATE, the questions about the
                        // bot itself: «хочешь пива?» wavers between it, SMALL_TALK and MOVE_TO): TalkFor gives an unsure line to the
                        // talk only when it is not an order the classifier merely could not pin down
                        if (g_talk) {
                            double talk_p = 0;
                            for (const char* label : {"SMALL_TALK", "NONE", "BODY_STATE"}) {
                                const auto it = std::find(chat.m.cfg.labels.begin(), chat.m.cfg.labels.end(), label);
                                if (it != chat.m.cfg.labels.end() && static_cast<size_t>(it - chat.m.cfg.labels.begin()) < t.p.size())
                                    talk_p += t.p[static_cast<size_t>(it - chat.m.cfg.labels.begin())];
                            }
                            turn["talk_p"] = std::round(talk_p * 1000) / 1000;
                        }
                        chat.RoomOrder(memo, t, &turn);   // in or out through a room's door
                        if (turn.contains("say") && turn["say"].is_string()) {
                            const std::string said = turn["say"].get<std::string>();
                            chat.HeardFromBot(said);
                            turn["say"] = Rephrased(said, g_replies ? g_replies->Language() : std::string("en"));
                        }
                        turns.push_back(std::move(turn));
                    });
                chat.words.clear();
                if (!heard_ok) {
                    fail(err);
                    return;
                }
                chat.NoteKept(memo.info);   // the last lesson, for «не надо было запоминать»
                // the player's own words without the bot's name («Бади, иди к Майку»: Майк is whom, Бади who is told)
                std::string own = heard;
                {
                    Callee called;
                    std::string r;
                    if (callees.is_array() && CalledCallee(heard, callees, chat.BotName(), &called, &r) && called.to == "bot" && !r.empty()) own = r;
                    else if (!chat.BotName().empty() && coop::CalledBy(heard, chat.BotName(), &r) && !r.empty()) own = r;
                }
                // hit, shoot, aim at, taunt someone (2026-11-14): whom from the player's own words; a taunt's words are the bot's own,
                // from its talking model
                bool acted = false;
                if (!memo.answered) {
                    // ... and going to someone, following them (2026-11-15, «Бади, иди к Майку», «иди за Колей»); the turns made again
                    // from the words when they fit none (ApplyWordOrders)
                    const WordOrders words_said = ApplyWordOrders(own, callees, chat.BotName(), "bot",
                                                                  g_replies ? g_replies->Language() : std::string("en"), &turns, g_replies);
                    if (words_said.rebuilt) h.note = "the turns made from the words";
                    if (words_said.went)
                        h.note += std::string(h.note.empty() ? "" : "; ") + "going to someone: " + words_said.go.kind + " " + words_said.go.target.dump();
                    MarkStand(own, &turns, g_replies);   // «встань туда»: there, not where it stands
                    const ActOn& act = words_said.act;
                    if (words_said.acted) {
                        acted = true;
                        h.note += std::string(h.note.empty() ? "" : "; ") + "acting on someone: " + act.kind + " " + act.target.dump();
                        if (act.intent == "TAUNT" && turns.size() == 1 && g_talk && g_talk->Ready()) {
                            std::string said, talk_err;
                            json info;
                            const std::string kind = act.target.value("kind", std::string());
                            std::string whom = kind == "speaker" ? "the player" : kind == "pointed" ? "him" : CalledIn(act.target, g_language, 'n', chat.BotName());
                            if (whom.empty()) whom = "him";
                            if (chat.TalkReply("bot", "(The player tells you to mock " + whom + " to " + (whom == "the player" ? "his" : "their") +
                                                          " face. Say one short mocking sentence to " + whom + ".)", &said, &info, &talk_err)) {
                                said = Rephrased(said, g_language);
                                KeepLocalized(said);
                                turns.at(0)["say"] = said;
                                turns.at(0).erase("say_en");
                                turns.at(0)["talk"] = info;
                            }
                        }
                    }
                }
                if (memo.answered) {
                    // the long-term memory answered the line itself ("What did you mean?", "Got it, I'll remember."): its
                    // words and no order, as SMALL_TALK is
                    json turn = {{"intent", "SMALL_TALK"}, {"prob", 1.0}, {"action", "act"}, {"say", memo.say}, {"line", heard},
                                 {"order", {{"intent", "SMALL_TALK"}}}, {"question", nullptr}, {"time", nullptr}};
                    std::string local;
                    if (g_replies && Localize(memo.say, &local, memo.terms.empty() ? nullptr : &memo.terms)) turn["say"] = local, turn["say_en"] = memo.say;
                    chat.HeardFromBot(turn["say"].get<std::string>());
                    turn["say"] = Rephrased(turn["say"].get<std::string>(), g_replies ? g_replies->Language() : std::string("en"));
                    json j = turn;
                    j.erase("line");
                    j["event"] = "reply";
                    j["turns"] = json::array({turn});
                    j["id"] = id;
                    j["heard"] = heard;
                    j["spoken"] = spoken;
                    j["audio_s"] = audio_s;
                    j["stt_ms"] = stt_ms;
                    j["bro_active"] = g_replies != nullptr && g_replies == g_bro_replies;
                    j["memory"] = memo.info;
                    send(j);
                    return;
                }
                if (!memo.ask.empty() && !turns.empty()) {
                    // the bot's question after the order's own words ("Moving. Shall I remember that ...?")
                    json& first = turns.at(0);
                    std::string q = memo.ask, local;
                    if (g_replies && Localize(memo.ask, &local, &memo.terms)) q = local;
                    const std::string said = first.value("say", std::string());
                    first["say"] = said.empty() ? q : said + " " + q;
                    if (first.contains("say_en")) first["say_en"] = first["say_en"].get<std::string>() + " " + memo.ask;
                }
                if (memo.remembered && !turns.empty()) {
                    // a meaning was kept: the bot says so before the order's own words
                    json& first = turns.at(0);
                    std::string got = kRemembered, local;
                    if (g_replies && Localize(kRemembered, &local)) got = local;
                    const std::string said = first.value("say", std::string());
                    first["say"] = said.empty() ? got : got + " " + said;
                    if (first.contains("say_en")) first["say_en"] = kRemembered + " " + first["say_en"].get<std::string>();
                }
                if (bro == coop::BroHabit::Heard::On && !turns.empty()) {
                    // the line that switched the habit on gets an answer with the word in it: the player hears it took
                    json& first = turns.at(0);
                    const std::string said = first.value("say", std::string()), english = first.value("say_en", said);
                    const auto variants = kLines.find(first.value("intent", std::string()));
                    if (coop::BroHabit::Read(said) == coop::BroHabit::Heard::None && variants != kLines.end() &&
                        std::find(variants->second.begin(), variants->second.end(), english) != variants->second.end())
                        for (const std::string& v : variants->second) {
                            std::string local;
                            if (g_replies && Localize(v, &local) && coop::BroHabit::Read(local) == coop::BroHabit::Heard::On) {
                                first["say"] = local;
                                first["say_en"] = v;
                                break;
                            }
                        }
                }
                if (relapsed && !turns.empty()) {
                    // the brat persona, 30 s after it was told to stop: it slips, and owns up to it
                    json& first = turns.at(0);
                    std::string sorry = kBroRelapse, local;
                    if (g_replies && Localize(kBroRelapse, &local)) sorry = local;
                    const std::string said = first.value("say", std::string());
                    first["say"] = said.empty() ? sorry : sorry + " " + said;
                    if (first.contains("say_en")) first["say_en"] = kBroRelapse + " " + first["say_en"].get<std::string>();
                    first["bro_relapse"] = true;
                }
                // "what do you see?" in the player's own words: the decoder writes «qué ves?» as an order to watch an angle
                // (chain v63), so a Russian or Spanish line that asks it is the question whatever the decoder made of it
                if (g_language != "en" && turns.size() == 1 && !turns.at(0).contains("state") && SeenInOwnWords(heard)) {
                    json& only = turns.at(0);
                    only["state"] = "seen";
                    only["order"] = nullptr;
                    only["say"] = "";
                    only.erase("say_en");
                }
                // "where are you going?" in the player's own words (2026-11-01, «Ты куда пош<unk>л?» was HOLSTER): the game answers.
                // Over a "how" too (2026-11-03, the owner: «Чем занят?» was "what's up", «Доложи, что делаешь» a status report: the
                // health and the ammo, not what it does)
                if (g_language != "en" && turns.size() == 1 && DoingInOwnWords(heard) &&
                    (!turns.at(0).contains("state") || turns.at(0).value("state", std::string()) == "how")) {
                    json& only = turns.at(0);
                    only["state"] = "doing";
                    only["order"] = nullptr;
                    only["say"] = "";
                    only.erase("say_en");
                }
                // the talk in the bot's role (talker.h, 2026-11-11): a line of one turn that gives no order is answered by the
                // talking model instead of the fixed lines (TalkFor); not while the bot waits for the answer to its question.
                // The words it had stay under "talk"."was"; a model with nothing to say leaves them as they were
                if (g_talk && g_talk->Ready() && turns.size() == 1 && !chat.planner.Mem().has_question &&
                    TalkFor(turns.at(0), heard, g_talk->TalkingNow("bot"))) {
                    json& only = turns.at(0);
                    std::string said, talk_err;
                    json info;
                    if (chat.TalkReply("bot", heard, &said, &info, &talk_err)) {
                        info["was"] = {{"intent", only.value("intent", json(nullptr))}, {"action", only.value("action", json(nullptr))},
                                       {"state", only.contains("state") ? only["state"] : json(nullptr)}, {"say", only.value("say", json(nullptr))}};
                        said = Rephrased(said, g_language);
                        only["intent"] = "SMALL_TALK";
                        only["action"] = "act";
                        only["order"] = {{"intent", "SMALL_TALK"}};
                        only.erase("state");
                        only.erase("say_en");
                        only["say"] = said;
                        only["talk"] = info;
                        KeepLocalized(said);
                        chat.HeardFromBot(said);
                    } else {
                        only["talk_error"] = talk_err;
                    }
                }
                json j = turns.at(0);   // the reply as it was before --chain: the first order's
                j.erase("line");
                j["event"] = "reply";
                if (bro_name) j["bro"] = bro_name;
                j["bro_active"] = g_replies != nullptr && g_replies == g_bro_replies;
                if (g_chain) {
                    j["turns"] = std::move(turns);
                    j["chain"] = {{"route", h.route >= 0 ? json(h.route) : json(nullptr)}, {"decoded", h.decoded}, {"rewritten", h.rewritten},
                                  {"resumed", h.resumed}, {"held", h.held}, {"note", h.note}, {"route_ms", h.route_ms}, {"rewrite_ms", h.rewrite_ms}};
                }
                j["id"] = id;
                j["heard"] = heard;
                j["spoken"] = spoken;
                j["audio_s"] = audio_s;
                j["stt_ms"] = stt_ms;
                if (g_memory && g_memory->IsOpen()) j["memory"] = memo.info;   // what the long-term memory did with the line
                if (words && !words->empty()) {   // when each word was said: the game grounds each order at its own moment
                    json w = json::array();
                    for (const coop::SpeechWord& x : *words) w.push_back({{"w", x.text}, {"t", std::round(x.start * 1000) / 1000}});
                    j["words"] = std::move(w);
                    j["clip_start_s"] = clip_start;
                }
                send(j);
            };
            if (cmd == "text") {
                // a typed line; or a heard one the game says again to the one it called ("readdress"): "spoken" and its words
                // with their times come with it
                std::vector<coop::SpeechWord> said_words;
                if (q.contains("words") && q["words"].is_array())
                    for (const json& w : q["words"])
                        if (w.is_object()) said_words.push_back({w.value("w", std::string()), w.value("t", 0.0)});
                respond(q.at("text").get<std::string>(), q.value("spoken", false), q.value("audio_s", 0.0), q.value("stt_ms", 0.0),
                        said_words.empty() ? nullptr : &said_words, q.value("clip_start_s", 0.0));
            } else if (cmd == "rephrase") {
                // {"cmd":"rephrase","text":"Понял, брат, запомню.","lang":"ru"}: the line with the player's phrases and pronunciations
                const std::string lang = q.value("lang", g_replies ? g_replies->Language() : std::string("en"));
                const std::string text = Rephrased(q.at("text").get<std::string>(), lang);
                send({{"event", "rephrased"}, {"id", id}, {"text", text}, {"voiced", Pronounced(text, lang)}});
            } else if (cmd == "world") {
                send({{"event", "world"}, {"id", id}, {"entities", chat.planner.World().entities.size()}});
            } else if (cmd == "ptt_down") {
#ifdef _WIN32
                if (system_voice && tts_ready) tts.Stop();   // the microphone must not hear the bot
#endif
                if (piper_ready) drop_lines();   // the game stops what it is playing itself
#if defined(COOP_WITH_STT) && defined(_WIN32)
                if (!mic_ready) {
                    fail(stt_ready ? "no microphone: " + mic_note : "no speech-to-text: " + stt_note);
                    continue;
                }
                mic.Begin();
                listening = true;
                down = Clock::now();
                {
                    std::lock_guard<std::mutex> g(open.lock);
                    open.key = true;   // the open microphone cuts nothing while the key is down
                }
                send({{"event", "listening"}, {"id", id}});
#else
                fail("no microphone in this build");
#endif
            } else if (cmd == "ptt_up" || cmd == "ptt_cancel") {
#if defined(COOP_WITH_STT) && defined(_WIN32)
                {
                    std::lock_guard<std::mutex> g(open.lock);
                    open.key = false;
                }
                if (!listening) {
                    fail("the talk key was not down");
                    continue;
                }
                listening = false;
                const double held = Ms(Clock::now() - down);
                // the game kept the microphone on after the key came up ("tail_s", its TalkTailSeconds): no second wait for the
                // last syllable (2026-11-04: it was 150 ms more on every line)
                const double waited = q.contains("tail_s") && q["tail_s"].is_number() ? q["tail_s"].get<double>() : 0.0;
                const std::vector<float> clip = mic.End(std::clamp(waited, 0.0, 10.0));
                if (cmd == "ptt_cancel") {
                    send({{"event", "cancelled"}, {"id", id}});
                } else if (held < 200) {
                    send({{"event", "too_short"}, {"id", id}, {"held_ms", held}});
                } else {
                    const auto t0 = Clock::now();
                    std::string heard;
                    std::vector<coop::SpeechWord> words;
                    if (!stt.Transcribe(clip.data(), clip.size(), MicCapture::kSampleRate, &heard, &err, &words)) {
                        fail(err);
                        continue;
                    }
                    respond(heard, true, static_cast<double>(clip.size()) / MicCapture::kSampleRate, Ms(Clock::now() - t0), &words,
                            -MicCapture::kPreRollSeconds);
                }
#else
                fail("no microphone in this build");
#endif
            } else if (cmd == "open_mic") {
#ifdef COOP_WITH_STT
                if (!vad_ready) {
                    fail("no voice detector: " + vad_note);
                    continue;
                }
                const bool on = q.value("on", true);
                const std::string source = q.value("source", std::string("mic"));
                if (on && source == "mic" && !mic_ready) {
                    fail("no microphone: " + mic_note);
                    continue;
                }
                const float silence = std::clamp(q.value("silence_s", 0.6f), 0.2f, 3.0f);
                {
                    std::lock_guard<std::mutex> g(open.lock);
                    open.on = on;
                    open.script = source == "script";
                    if (std::abs(silence - open.options.min_silence) > 1e-3f) open.options.min_silence = silence, open.reload = true;
                    if (!on) open.phrases.clear(), open.clip.clear();
                }
                send({{"event", "open_mic"}, {"id", id}, {"on", on}, {"source", source}, {"silence_s", silence}});
#else
                fail("this coop_cli was built without speech-to-text");
#endif
            } else if (cmd == "mic_wav") {
#ifdef COOP_WITH_STT
                std::vector<float> x;
                int rate = 0;
                if (!ReadWav(q.at("path").get<std::string>(), &x, &rate, &err)) {
                    fail(err);
                    continue;
                }
                if (rate != coop::VoiceActivity::kSampleRate && rate > 0 && !x.empty()) {   // to the detector's rate, linearly
                    std::vector<float> y(static_cast<size_t>(static_cast<double>(x.size()) * coop::VoiceActivity::kSampleRate / rate));
                    for (size_t i = 0; i < y.size(); ++i) {
                        const double at = static_cast<double>(i) * rate / coop::VoiceActivity::kSampleRate;
                        const size_t k = std::min(static_cast<size_t>(at), x.size() - 1), k1 = std::min(k + 1, x.size() - 1);
                        y[i] = static_cast<float>(x[k] + (x[k1] - x[k]) * (at - static_cast<double>(k)));
                    }
                    x.swap(y);
                }
                {
                    std::lock_guard<std::mutex> g(open.lock);
                    open.clip.insert(open.clip.end(), x.begin(), x.end());
                }
                send({{"event", "mic_wav"}, {"id", id}, {"audio_s", static_cast<double>(x.size()) / coop::VoiceActivity::kSampleRate}});
#else
                fail("this coop_cli was built without speech-to-text");
#endif
            } else if (cmd == "vad_up") {
#ifdef COOP_WITH_STT
                coop::VadPhrase phrase;
                bool found = false;
                {
                    std::lock_guard<std::mutex> g(open.lock);
                    const auto it = open.phrases.find(q.value("seg", 0LL));
                    if (it != open.phrases.end()) phrase = std::move(it->second), open.phrases.erase(it), found = true;
                }
                if (!found) {
                    fail("no such phrase (dropped, or the open microphone went off)");
                    continue;
                }
                const auto t0 = Clock::now();
                std::string heard;
                std::vector<coop::SpeechWord> words;
                if (!stt.Transcribe(phrase.samples.data(), phrase.samples.size(), coop::VoiceActivity::kSampleRate, &heard, &err, &words)) {
                    fail(err);
                    continue;
                }
                const double audio_s = static_cast<double>(phrase.samples.size()) / coop::VoiceActivity::kSampleRate, stt_ms = Ms(Clock::now() - t0);
                // the bot hears it when it is called by its name, or in the game's window after its words (the owner: 8 s); a
                // person near when the line calls them (the game's "callees", 2026-11-12: respond readdresses it to them)
                const std::string said = StripPy(heard), name = chat.BotName();
                std::string rest;
                Callee callee;
                const bool called = (!name.empty() && coop::CalledBy(said, name, &rest)) ||
                                    (q.contains("callees") && CalledCallee(said, q["callees"], name, &callee, &rest));
                if (!said.empty() && !q.value("window", false) && !called) {
                    send({{"event", "not_called"}, {"id", id}, {"heard", said}, {"name", name}, {"audio_s", audio_s}, {"stt_ms", stt_ms}});
                    continue;
                }
                respond(heard, true, audio_s, stt_ms, &words, 0);
#else
                fail("this coop_cli was built without speech-to-text");
#endif
            } else if (cmd == "wav") {
#ifdef COOP_WITH_STT
                if (!stt_ready) {
                    fail("no speech-to-text: " + stt_note);
                    continue;
                }
                std::vector<float> x;
                int rate = 0;
                if (!ReadWav(q.at("path").get<std::string>(), &x, &rate, &err)) {
                    fail(err);
                    continue;
                }
                const auto t0 = Clock::now();
                std::string heard;
                std::vector<coop::SpeechWord> words;
                if (!stt.Transcribe(x.data(), x.size(), rate, &heard, &err, &words)) {
                    fail(err);
                    continue;
                }
                respond(heard, true, static_cast<double>(x.size()) / rate, Ms(Clock::now() - t0), &words, 0);
#else
                fail("this coop_cli was built without speech-to-text");
#endif
            } else if (cmd == "say" || cmd == "hush") {
                if (piper_ready) {
                    if (cmd == "hush") {
                        drop_lines();
                    } else {
                        std::lock_guard<std::mutex> lock(jobs_mutex);
                        if (jobs.size() >= 3) {   // a burst of callouts: the oldest that is not being made yet goes
                            send({{"event", "hushed"}, {"id", jobs.front().id}});
                            jobs.pop_front();
                        }
                        // a line in English from the game is written in the player's language here; one this brain wrote in it
                        // already (a reply's "say") is said as it is
                        std::string text = q.at("text").get<std::string>(), local;
                        bool in_local = false;
                        ChooseReplies();
                        // a person who speaks another language than the player's ("lang", 2026-11-14): written and said in theirs, with
                        // its tables (the habit's with "bro") and a voice of it ("local_voice", loaded when first wanted)
                        const std::string say_lang = q.contains("lang") && q["lang"].is_string() ? q["lang"].get<std::string>() : std::string();
                        const bool own_lang = (say_lang == "en" || say_lang == "ru" || say_lang == "es") && say_lang != g_language;
                        coop::Localizer* const replies_were = g_replies;
                        if (own_lang) g_replies = RepliesIn(say_lang, q.value("bro", false));
                        // "terms": the words of labelled things in the player's language, {"thing": {"spike trap": {"ru":
                        // {"text": ..., "acc": ...}, "es": {...}}}}: this language's forms go to the table
                        coop::Localizer::Terms terms;
                        if (g_replies && q.contains("terms") && q["terms"].is_object())
                            for (auto s = q["terms"].begin(); s != q["terms"].end(); ++s)
                                for (auto v = s.value().begin(); v != s.value().end(); ++v) {
                                    const json& forms = v.value().contains(g_replies->Language()) ? v.value()[g_replies->Language()] : v.value();
                                    std::string key = v.key();
                                    for (char& c : key) c = static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
                                    for (auto f = forms.begin(); f != forms.end(); ++f)
                                        if (f.value().is_string()) terms[s.key()][key][f.key()] = f.value().get<std::string>();
                                }
                        if (own_lang) {
                            // English: the brain's own words (with the habit: its English table); another: its table, or as it is
                            if (say_lang != "en") in_local = true;
                            if (g_replies && !q.value("localized", false) && !IsLocalized(text) && LocalizeMixed(text, &local, &terms)) text = local;
                        } else if (local_ready && g_replies) {
                            if (q.value("localized", false) || IsLocalized(text)) in_local = true;
                            else if (LocalizeMixed(text, &local, &terms)) text = local, in_local = true;
                        } else if (g_replies && g_replies->Language() == "en") {
                            // English with the habit: the game's line in the persona's words, said by the English voice
                            if (!q.value("localized", false) && !IsLocalized(text) && LocalizeMixed(text, &local, &terms)) text = local;
                        }
                        const std::string line_lang = own_lang ? say_lang : in_local && g_replies ? g_replies->Language() : std::string("en");
                        g_replies = replies_were;
                        chat.HeardFromBot(text);
                        text = Rephrased(text, line_lang);
                        if (text.empty()) {   // a line the player asked the bot not to say
                            send({{"event", "hushed"}, {"id", id}});
                            continue;
                        }
                        if (!own_lang) text = WithPlayerName(text, chat.rng);   // «Понял, Тимур.» now and then
                        const std::string voiced = Pronounced(text, line_lang);
                        float speed = q.value("speed", 0.0f);
                        const double tuned = Chat::SettingNow("voice_speed");   // «говори медленнее»
                        if (std::abs(tuned - 1.0) > 1e-3) speed = static_cast<float>((speed > 0 ? speed : 1.0f) * tuned);
                        // a local line: the player's language's voice, or one of the more ("local_voice") and a speaker of it
                        // ("local_speaker"); an English line: the bot's voice and "speaker"
                        jobs.push_back({id, text, in_local ? q.value("local_speaker", std::string()) : q.value("speaker", std::string()), speed, in_local,
                                        voiced == text ? std::string() : voiced, q.value("stream", false)});
                        if (in_local) jobs.back().local_name = q.value("local_voice", std::string());
                        // another language's line with no voice named: that language's own folder (voice_ru, voice_es)
                        if (own_lang && in_local && jobs.back().local_name.empty()) jobs.back().local_name = "voice_" + say_lang;
                        jobs.back().lang = line_lang;
                        jobs_cv.notify_one();
                    }
                } else if (cmd == "say" && !id.is_null()) {
                    send({{"event", "hushed"}, {"id", id}});   // asked for audio, and there is no voice to make it
                }
#ifdef _WIN32
                if (system_voice && tts_ready) {
                    if (cmd == "say") tts.Say(q.at("text").get<std::string>());
                    else tts.Stop();
                }
#endif
            } else if (cmd == "reset") {
                chat.planner.Reset();
                chat.Forget();
                chat.ForgetTalk();
                if (g_talk) g_talk->talks.clear();
                send({{"event", "reset"}, {"id", id}});
            } else if (cmd == "role") {
                // the game's own text for a role (talker.h): the bot's definition, a person placed in the level. {"cmd":"role",
                // "name":"seller","text":"...","names":{"ru":"Макс","en":"Max"}}; no text: the brain's file's again. A new text
                // starts the role's talk over
                if (!g_talk) {
                    fail("no talking model: " + g_talk_note);
                    continue;
                }
                const std::string name = q.at("name").get<std::string>();
                const std::string text = RoleText(q.value("text", std::string()));
                Talk::Role& r = g_talk->roles[name];
                const std::string before = r.text;
                if (!text.empty()) {
                    r.text = text;
                    r.source = "game";
                } else if (!r.file_text.empty()) {
                    r.text = r.file_text;
                    r.source = r.file;
                } else {
                    g_talk->roles.erase(name);
                    fail("the role " + name + " has no text, and the brain has no file for it");
                    continue;
                }
                if (q.contains("names") && q["names"].is_object())
                    for (const auto& [lang, n] : q["names"].items())
                        if (n.is_string()) r.names[lang] = n.get<std::string>();
                // "orders": a body of theirs in the game takes orders (2026-11-12): a line to them may be an order for it
                r.orders = q.contains("orders") && q["orders"].is_boolean() && q["orders"].get<bool>();
                // "gender": "woman" | "man": the forms of the words they say of themselves (TalkSystem)
                {
                    const std::string g = q.contains("gender") && q["gender"].is_string() ? q["gender"].get<std::string>() : std::string();
                    const std::string was = r.gender;
                    r.gender = g == "woman" || g == "man" ? g : std::string();
                    if (r.gender != was) g_talk->talks.erase(name);   // their talk so far was in the other forms
                }
                // "bro": true: they call the player «брат» / "bro" / "hermano" (2026-11-14): in their talk (TalkSystem) and in their
                // words for an order (the --replies-bro table); their voice is the game's choice apart from it
                {
                    const bool was = r.bro;
                    r.bro = q.contains("bro") && q["bro"].is_boolean() && q["bro"].get<bool>();
                    if (r.bro != was) g_talk->talks.erase(name);
                }
                // "lang": "en" | "ru" | "es": the language they speak whatever the player's (2026-11-14); none: the player's
                {
                    const std::string was = r.lang;
                    const std::string l = q.contains("lang") && q["lang"].is_string() ? q["lang"].get<std::string>() : std::string();
                    r.lang = l == "en" || l == "ru" || l == "es" ? l : std::string();
                    if (r.lang != was) g_talk->talks.erase(name);   // their talk so far was in another language
                }
                if (r.text != before) g_talk->talks.erase(name);   // another character: its talk starts over (the game sends it before each line)
                send({{"event", "role"}, {"id", id}, {"name", name}, {"source", r.source}, {"chars", r.text.size()}, {"names", r.names},
                      {"orders", r.orders}, {"gender", r.gender.empty() ? json(nullptr) : json(r.gender)}, {"bro", r.bro},
                      {"lang", r.lang.empty() ? json(nullptr) : json(r.lang)}, {"roles", g_talk->RoleNames()}});
            } else if (cmd == "react") {
                // a person of the level's words of their own on what just happened to them (2026-11-14, the owner: a person hurt by
                // someone complains and steps away): their role answers "line", the game's account of it, in their language.
                // {"cmd":"react","to":"granny","line":"(The player just hurt you. ...)"} -> {"event":"react","to":"granny","say":...}
                if (!g_talk || !g_talk->Ready()) {
                    fail("no talking model: " + g_talk_note);
                    continue;
                }
                const std::string role = q.value("to", std::string());
                if (!g_talk->roles.count(role)) {
                    fail("no role \"" + role + "\" (the game's \"role\" first)");
                    continue;
                }
                std::string said, talk_err;
                json info;
                if (!chat.TalkReply(role, q.value("line", std::string()), &said, &info, &talk_err)) {
                    fail(talk_err);
                    continue;
                }
                const std::string lang = g_talk->roles[role].lang.empty() ? g_language : g_talk->roles[role].lang;
                said = Rephrased(said, lang);
                KeepLocalized(said);
                send({{"event", "react"}, {"id", id}, {"to", role}, {"say", said}, {"talk", info}});
            } else if (cmd == "teach" || cmd == "forget" || cmd == "recall") {
                // the long-term memory by hand (a HUD, a test): {"cmd":"teach","heard":"on my goal","lines":["go"]},
                // {"cmd":"teach","entity":"Place_Door_03","name":"оружейка"}, {"cmd":"teach","entity":...,"colour":"green"},
                // {"cmd":"forget","heard":...} or {"cmd":"forget","entity":...}, {"cmd":"recall"}. "lang" and "map" default
                // to the player's language and the world's map; the answer carries everything kept
                if (!g_memory || !g_memory->IsOpen()) {
                    fail("no long-term memory (--memory FILE): " + g_memory_note);
                    continue;
                }
                const std::string lang = q.value("lang", g_language), map = q.value("map", chat.planner.World().map);
                json out = {{"event", cmd == "teach" ? "taught" : cmd == "forget" ? "forgot" : "memory"}, {"id", id}};
                bool ok = true;
                if (cmd == "teach" && q.contains("heard")) {
                    coop::MemoryLine l;
                    l.lang = lang;
                    l.heard = coop::MemoryNorm(q.at("heard").get<std::string>());
                    l.lines = q.at("lines").get<std::vector<std::string>>();
                    l.intent = q.value("intent", std::string());
                    l.source = q.value("source", std::string("cmd"));
                    ok = g_memory->KeepLine(l, &err);
                } else if (cmd == "teach" && q.contains("name")) {
                    ok = g_memory->KeepName({map, q.at("entity").get<std::string>(), lang, coop::MemoryNorm(q["name"].get<std::string>()), 0}, &err);
                } else if (cmd == "teach" && q.contains("colour")) {
                    ok = g_memory->KeepColour({map, q.at("entity").get<std::string>(), q["colour"].get<std::string>(), 0}, &err);
                } else if (cmd == "teach") {
                    fail("teach: \"heard\" and \"lines\", or \"entity\" and \"name\", or \"entity\" and \"colour\"");
                    continue;
                } else if (cmd == "forget" && q.contains("heard")) {
                    err.clear();
                    ok = g_memory->ForgetLine(lang, coop::MemoryNorm(q["heard"].get<std::string>()), &err);
                    if (!ok && err.empty()) ok = true, out["none"] = true;
                } else if (cmd == "forget" && q.contains("entity")) {
                    bool any = false;
                    ok = g_memory->ForgetThing(map, q["entity"].get<std::string>(), &any, &err);
                    out["none"] = !any;
                } else if (cmd == "forget") {
                    fail("forget: \"heard\" or \"entity\"");
                    continue;
                }
                if (!ok) {
                    fail(err);
                    continue;
                }
                out["memory"] = MemoryJson(*g_memory);
                send(out);
            } else if (cmd == "threshold") {
                chat.brain.threshold = q.at("value").get<double>();
                send({{"event", "threshold"}, {"id", id}, {"value", chat.brain.threshold}});
            } else if (cmd == "ping") {
                send({{"event", "pong"}, {"id", id}});
            } else if (cmd == "quit") {
                break;
            } else {
                fail("unknown cmd");
            }
        } catch (const std::exception& e) {   // a missing key, a wrong type
            fail(e.what());
        }
    }
    (void)listening;
    (void)down;
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
#endif
    Model m;
    m.dir = COOP_DEFAULT_MODEL_DIR;
    std::string mode = "chat", tokenize_text, speech_text_file, world_file;
    bool serve_stt = true, serve_tts = false;
    coop::OrtBackend::Options opt;
    bool parallel = true;
    coop::SpeechOptions speech;
#ifdef COOP_DEFAULT_STT_DIR
    speech.model_dir = COOP_DEFAULT_STT_DIR;
#endif
    std::vector<std::string> wavs, stt_test;
    double mic_seconds = 0;
    Chain chain;
    DeciderReader decider;
    std::string decider_tests;
    bool decoder_cpu = false;
    int decoder_threads = 4;
    bool tts_threads_set = false;   // --tts-threads given: both voices get that many
    coop::VoiceOptions piper, voice_local;
    std::string replies_file, bro_file, bro_check;
    bool bro_on = false;
    double bro_relapse = 0;
    std::string tts_demo_dir, tts_text = "Contact left! Moving to the ping. Which door? The one ahead, 8 m?";
    std::string memory_file;
    Talk talk;
    bool no_talk = false, talk_cpu = false;
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (a == "--model-dir" && i + 1 < argc) m.dir = argv[++i];
        else if (a == "--talk" && i + 1 < argc) talk.dir = argv[++i], talk.found = "--talk";
        else if (a == "--no-talk") no_talk = true;
        else if (a == "--talk-cpu") talk_cpu = true;
        else if (a == "--talk-seed" && i + 1 < argc) talk.options.seed = static_cast<uint32_t>(std::strtoul(argv[++i], nullptr, 10)), talk.seed_set = true;
        else if (a == "--tts-piper" && i + 1 < argc) piper.model_dir = argv[++i];
        else if (a == "--tts-speaker" && i + 1 < argc) piper.speaker = argv[++i];
        else if (a == "--tts-speed" && i + 1 < argc) piper.speed = static_cast<float>(std::atof(argv[++i]));
        else if (a == "--tts-threads" && i + 1 < argc) piper.threads = std::max(1, std::atoi(argv[++i])), tts_threads_set = true;
        else if (a == "--tts-provider" && i + 1 < argc) piper.provider = argv[++i];
        else if (a == "--tts-demo" && i + 1 < argc) mode = "tts-demo", tts_demo_dir = argv[++i];
        else if (a == "--tts-text" && i + 1 < argc) tts_text = argv[++i];
        else if (a == "--chain" && i + 1 < argc) chain.dir = argv[++i];
        else if (a == "--decoder-cpu") decoder_cpu = true;
        else if (a == "--decoder-threads" && i + 1 < argc) decoder_threads = std::atoi(argv[++i]);
        else if (a == "--chain-tests") mode = "chain-tests";
        else if (a == "--language" && i + 1 < argc) g_language = argv[++i];
        else if (a == "--decoder-every-line") g_decode_every_line = true;
        else if (a == "--replies-bro" && i + 1 < argc) bro_file = argv[++i];
        else if (a == "--bro" && i + 1 < argc) bro_on = std::string(argv[++i]) == "on";
        else if (a == "--bro-relapse" && i + 1 < argc) bro_relapse = std::atof(argv[++i]);
        else if (a == "--bro-check" && i + 1 < argc) mode = "bro-check", bro_check = argv[++i];
        else if (a == "--replies" && i + 1 < argc) replies_file = argv[++i];
        else if (a == "--replies-dir" && i + 1 < argc) g_replies_dir = argv[++i];
        else if (a == "--replies-check" && i + 1 < argc) mode = "replies-check", replies_file = argv[++i];
        else if (a == "--voice-local" && i + 1 < argc) voice_local.model_dir = argv[++i];
        else if (a == "--voice-local-extra" && i + 1 < argc) {
            const std::string s = argv[++i];
            const size_t eq = s.find('=');
            if (eq == std::string::npos || eq == 0 || eq + 1 == s.size())
                return std::fprintf(stderr, "--voice-local-extra is NAME=DIR, not %s\n", s.c_str()), 2;
            coop::VoiceOptions o;
            o.model_dir = s.substr(eq + 1);
            g_voice_local_extra.emplace_back(s.substr(0, eq), o);
        }
        else if (a == "--decider" && i + 1 < argc) decider.dir = argv[++i];
        else if (a == "--decider-mode" && i + 1 < argc) decider.mode = argv[++i];
        else if (a == "--decider-threads" && i + 1 < argc) decider.options.threads = std::atoi(argv[++i]);
        else if (a == "--decider-gpu-layers" && i + 1 < argc) decider.options.gpu_layers = std::atoi(argv[++i]);
        else if (a == "--decider-tests" && i + 1 < argc) mode = "decider-tests", decider_tests = argv[++i];
        else if (a == "--threads" && i + 1 < argc) opt.threads = std::atoi(argv[++i]);
        else if (a == "--no-spin") opt.allow_spinning = false;
        else if (a == "--sequential") parallel = false;
        else if (a == "--golden" || a == "--tokenizer-tests" || a == "--dialogue" || a == "--bench" || a == "--gate-tests" ||
                 a == "--decide-tests" || a == "--location-tests" || a == "--world-tests" || a == "--item-tests")
            mode = a.substr(2);
        else if (a == "--world" && i + 1 < argc) world_file = argv[++i];
        else if (a == "--serve") mode = "serve";
        else if (a == "--no-stt") serve_stt = false;
        else if (a == "--tts") serve_tts = true;
        else if (a == "--tokenize" && i + 1 < argc) mode = "tokenize", tokenize_text = argv[++i];
        else if (a == "--speech-text-tests" && i + 1 < argc) mode = "speech-text-tests", speech_text_file = argv[++i];
        else if (a == "--time-tests" && i + 1 < argc) mode = "time-tests", speech_text_file = argv[++i];
        else if (a == "--stt-model" && i + 1 < argc) speech.model_dir = argv[++i];
        else if (a == "--stt-threads" && i + 1 < argc) speech.threads = std::atoi(argv[++i]);
        else if (a == "--voice") mode = "voice";
        else if (a == "--mic-test" && i + 1 < argc) mode = "mic-test", mic_seconds = std::atof(argv[++i]);
        else if (a == "--stt-wav" && i + 1 < argc) mode = "stt-wav", wavs.push_back(argv[++i]);
        else if (a == "--stt-tests" && i + 3 < argc) mode = "stt-tests", stt_test = {argv[i + 1], argv[i + 2], argv[i + 3]}, i += 3;
        else if (a == "--memory" && i + 1 < argc) memory_file = argv[++i];
        else if (a == "--name-chance" && i + 1 < argc) g_name_chance = std::clamp(std::atoi(argv[++i]), 0, 100);
        else if (a == "--vad" && i + 1 < argc) g_vad_model = argv[++i];
        else if (a == "--memory-dump" && i + 1 < argc) mode = "memory-dump", memory_file = argv[++i];
        else if (a == "--teach-tests" && i + 1 < argc) mode = "teach-tests", speech_text_file = argv[++i];
        else if (a == "--memory-store-tests" && i + 1 < argc) mode = "memory-store-tests", speech_text_file = argv[++i];
        else {
            std::fprintf(stderr, "usage: coop_cli [--golden | --tokenizer-tests | --dialogue | --gate-tests | --decide-tests |\n"
                                 "                 --location-tests | --world-tests | --item-tests | --bench | --tokenize TEXT | --speech-text-tests FILE |\n"
                                 "                 --voice | --mic-test SECONDS | --stt-wav FILE ... | --stt-tests LIST WAVDIR EXPECTED |\n"
                                 "                 --serve [--no-stt] [--tts | --tts-piper DIR] | --tts-piper DIR --tts-demo OUTDIR [--tts-text TEXT]]\n"
                                 "                [--model-dir DIR] [--threads N] [--no-spin] [--sequential] [--world FILE]\n"
                                 "                [--stt-model DIR] [--stt-threads N] [--vad silero_vad.onnx]\n"
                                 "                [--tts-speaker NAME[,NAME...]] [--tts-speed X] [--tts-threads N] [--tts-provider cpu|cuda|auto]\n"
                                 "                [--chain DIR [--chain-tests] [--decoder-cpu] [--decoder-threads N]]\n"
                                 "                [--language en|ru|es] [--memory FILE [--name-chance P]] | --memory-dump FILE | --teach-tests FILE\n"
                                 "                [--decider DIR [--decider-tests FILE] [--decider-mode avg|only] [--decider-threads N]\n"
                                 "                 [--decider-gpu-layers N]]\n"
                                 "                [--talk DIR | --no-talk] [--talk-cpu] [--talk-seed N] [--voice-local-extra NAME=DIR ...]\n");
            return 2;
        }
    }
    std::string err;
    if (piper.provider != "cpu" && piper.provider != "cuda" && piper.provider != "auto")
        return std::fprintf(stderr, "--tts-provider is cpu, cuda or auto, not %s\n", piper.provider.c_str()), 2;
    if (mode == "speech-text-tests") return RunSpeechTextTests(speech_text_file);
    if (mode == "time-tests") return RunTimeTests(speech_text_file);
    if (mode == "teach-tests") return RunTeachTests(speech_text_file);
    if (mode == "memory-store-tests") return RunMemoryStoreTests(speech_text_file);
    coop::BotMemory memory;
    if (!memory_file.empty()) {
        // a brain the game is still stopping holds the file a moment longer (its lease goes with its process: 2026-10-29, a
        // brain started at once after a language switch found it held)
        bool opened = memory.Open(memory_file, &err);
        for (const auto until = Clock::now() + std::chrono::seconds(5);
             !opened && err.find("lease already held") != std::string::npos && Clock::now() < until;) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            opened = memory.Open(memory_file, &err);
        }
        if (opened) {
            g_memory = &memory;
            if (!memory.PutAside().empty()) g_memory_note = "the file could not be read: put aside as " + memory.PutAside() + ", a new memory starts";
        } else {
            // the memory is optional: a bot without it hears as before (the reason goes to "ready")
            g_memory_note = err;
            std::fprintf(stderr, "%s\n", err.c_str());
            if (mode == "memory-dump") return 1;
        }
    }
    if (mode == "memory-dump") {
        std::printf("%s\n", MemoryJson(memory).dump(1, ' ', false, json::error_handler_t::replace).c_str());
        return 0;
    }
    if (mode == "tts-demo") {
#ifdef COOP_WITH_STT
        if (piper.model_dir.empty()) return std::fprintf(stderr, "--tts-demo needs --tts-piper DIR\n"), 2;
        const std::string only = piper.speaker;   // a list here: the demo's speakers, not one to load
        piper.speaker.clear();
        return RunTtsDemo(piper, tts_demo_dir, tts_text, only);
#else
        return std::fprintf(stderr, "this coop_cli was built without sherpa-onnx: no Piper voice\n"), 2;
#endif
    }
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
    if (mode == "world-tests") return RunWorldTests(m);
    if (mode == "item-tests") return RunItemTests(m);
    if (mode == "tokenize") {
        for (const auto& w : m.tok.Words(tokenize_text)) std::printf("word %s\n", Escaped(w).c_str());
        const auto ids = m.tok.Encode(tokenize_text);
        for (int64_t id : ids) std::printf("  %6lld %s\n", static_cast<long long>(id), Escaped(m.tok.Piece(id)).c_str());
        return 0;
    }
    const double mem0 = WorkingSetMb();
    const auto t0 = Clock::now();
    // the talk in a role (talker.h): --talk DIR, else the brain's own talk/ beside its bot/ (the game's brain folder holds bot/,
    // chain/, talk/: a brain deployed with talk/ talks, whatever the game passes); --no-talk: none. Only --serve talks
    if (no_talk) {
        talk.dir.clear();
        g_talk_note = "switched off (--no-talk)";
    } else if (talk.dir.empty() && mode == "serve") {
        std::filesystem::path bot = U8Path(m.dir);
        if (!bot.has_filename()) bot = bot.parent_path();
        const std::filesystem::path beside = bot.parent_path() / "talk";
        std::error_code ec;
        if (std::filesystem::exists(beside / "talk_config.json", ec)) talk.dir = beside.u8string(), talk.found = "beside the bot";
        else g_talk_note = "no --talk DIR, and no talk/talk_config.json beside the bot";
    }
    g_load_events = mode == "serve";
    g_load_t0 = t0;
    if (g_load_events) {
        std::vector<std::string> parts = {"the intent classifier"};
        if (!chain.dir.empty()) parts.push_back("the language model");
        if (!talk.dir.empty()) parts.push_back("the talking model");
        parts.push_back("the planner");
        if (!piper.model_dir.empty()) parts.push_back("the voice");
        if (!piper.model_dir.empty() && !voice_local.model_dir.empty()) parts.push_back("the voice in the player's language");
        if (!piper.model_dir.empty() && !voice_local.model_dir.empty() && !g_voice_local_extra.empty())
            parts.push_back("more voices in the player's language");
        if (serve_stt) {
            parts.push_back("speech recognition");
            parts.push_back("the microphone");
        }
        PlanLoading(parts);
    }
    Loading("the intent classifier");
    if (!LoadModels(m, opt, parallel, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    const double load_ms = Ms(Clock::now() - t0);
    {   // a model that does not fit the config (another label set) is refused here, not mid-game
        std::vector<float> logits;
        if (!m.backend->Run(m.tok.Encode("warm up"), &logits, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        if (logits.size() != m.cfg.labels.size())
            return std::fprintf(stderr, "the model gives %zu outputs, intent_config.json has %zu labels\n",
                                logits.size(), m.cfg.labels.size()), 1;
    }
    if (mode == "chain-tests" && chain.dir.empty()) return std::fprintf(stderr, "--chain-tests needs --chain DIR\n"), 2;
    if (!chain.dir.empty()) {
        Loading("the language model");
        if (!LoadChain(chain, opt, decoder_cpu, decoder_threads, &err)) return std::fprintf(stderr, "%s: %s\n", chain.dir.c_str(), err.c_str()), 1;
        std::printf("chain: %s (%s, decoder on the %s, %d threads, loaded in %.0f ms)\n", chain.dir.c_str(),
                    chain.router ? "router and decoder" : "decoder, no router: every line goes to it", decoder_cpu ? "CPU" : "GPU",
                    decoder_threads, chain.load_ms);
        g_chain = &chain;
    }
    if (!talk.dir.empty()) {
        // optional: a brain whose talking model does not load answers small talk with its fixed lines, as before
        Loading("the talking model");
        if (LoadTalk(talk, decoder_cpu || talk_cpu, decoder_threads, &err)) {
            g_talk = &talk;
            std::string roles;
            for (const auto& r : talk.roles) roles += (roles.empty() ? "" : ", ") + r.first;
            std::printf("talk: %s (%s; %s, %d threads, roles %s; loaded in %.0f ms)\n", talk.dir.c_str(), talk.found.c_str(),
                        talk.options.gpu_layers ? "GPU" : "CPU", talk.options.threads, roles.c_str(), talk.load_ms);
        } else {
            g_talk_note = talk.dir + ": " + err;
            std::fprintf(stderr, "talk: %s; small talk gets the fixed lines\n", g_talk_note.c_str());
        }
    }
    if (g_language != "en" && g_language != "ru" && g_language != "es")
        return std::fprintf(stderr, "--language is en, ru or es, not %s\n", g_language.c_str()), 2;
    if (g_language != "en")
        std::printf("language: %s (every line to the decoder, written in English%s)\n", g_language.c_str(),
                    g_chain ? "" : "; NO decoder is loaded (--chain DIR): the classifier gets the lines as they are and reads little");
    else if (g_decode_every_line)
        std::printf("language: en, every line to the decoder (--decoder-every-line)%s\n",
                    g_chain ? "" : "; NO decoder is loaded (--chain DIR): the flag does nothing");
    // the people's own languages' tables (RepliesIn): --replies-dir, else beside the player's language's tables
    if (g_replies_dir.empty() && (!replies_file.empty() || !bro_file.empty()))
        g_replies_dir = std::filesystem::u8path(!replies_file.empty() ? replies_file : bro_file).parent_path().u8string();
    coop::Localizer replies;
    if (!replies_file.empty()) {
        if (!replies.Load(replies_file, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 2;
        std::printf("replies: %s, %zu templates (%s)\n", replies.Language().c_str(), replies.Templates(), replies_file.c_str());
        g_replies = &replies;
        g_plain_replies = &replies;
    }
    if (mode == "bro-check") return RunBroCheck(bro_check);
    coop::Localizer bro_replies;
    if (!bro_file.empty()) {
        if (!bro_replies.Load(bro_file, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 2;
        if (bro_replies.Language() != g_language)
            return std::fprintf(stderr, "%s is a %s table, and the player's language is %s\n", bro_file.c_str(), bro_replies.Language().c_str(),
                                g_language.c_str()), 2;
        g_bro_replies = &bro_replies;
        g_bro.Configure(bro_on, bro_relapse);
        ChooseReplies();
        std::printf("bro: %s, %zu templates (%s), starts %s%s\n", bro_replies.Language().c_str(), bro_replies.Templates(), bro_file.c_str(),
                    bro_on ? "on" : "off", bro_relapse > 0 ? (", comes back " + std::to_string(static_cast<int>(bro_relapse)) + " s after it is stopped").c_str() : "");
    }
    if (mode == "replies-check") return RunRepliesCheck(replies);
    // the player's language's voice: --tts-threads when given (the game's setting, 2026-11-02), else at least four (a Kokoro
    // voice needs them: about 1.6 s a line on one thread, 0.6 s on four)
    voice_local.threads = tts_threads_set ? piper.threads : std::max(piper.threads, 4);
    voice_local.provider = piper.provider;                 // both voices where --tts-provider says ("auto": each by its kind)
    for (auto& extra : g_voice_local_extra) {             // the more voices of the player's language as its own
        extra.second.threads = voice_local.threads;
        extra.second.provider = voice_local.provider;
    }
    if (mode == "decider-tests" && decider.dir.empty()) return std::fprintf(stderr, "--decider-tests needs --decider DIR\n"), 2;
    if (!decider.dir.empty() && !LoadDecider(decider, m.cfg.labels, &err)) {
        // the second reader is optional: a brain whose decider does not load (another label set, a missing file) goes on
        // with the ensemble alone; only its own tests need it
        if (mode == "decider-tests") return std::fprintf(stderr, "%s: %s\n", decider.dir.c_str(), err.c_str()), 1;
        std::fprintf(stderr, "decider: %s: %s; the ensemble alone reads the lines\n", decider.dir.c_str(), err.c_str());
        decider.dir.clear();
    }
    if (!decider.dir.empty()) {
#ifdef COOP_WITH_LLM
        std::printf("decider: %s (%s; %s, %d threads, %s; loaded in %.0f ms, prefix of %zu tokens in %.0f ms)\n", decider.dir.c_str(),
                    decider.mode == "avg" ? "averaged with the ensemble" : "alone, the ensemble's reading set aside",
                    decider.options.gpu_layers ? "GPU" : "CPU", decider.options.threads, decider.source.c_str(), decider.model.load_ms(),
                    decider.model.prefix_tokens(), decider.model.prefix_ms());
#endif
        g_decider = &decider;
    }
    if (mode == "decider-tests") return RunDeciderTests(decider, decider_tests);
    if (mode == "chain-tests") return RunChainTests(m, chain);
    if (mode == "serve")
        return RunServe(m, speech, opt.threads, serve_stt, serve_tts, piper.model_dir.empty() ? nullptr : &piper,
                        voice_local.model_dir.empty() ? nullptr : &voice_local);
    if (mode == "golden") return RunGolden(m);
    if (mode == "dialogue") return RunDialogue(m);
    if (mode == "bench") return RunBench(m, load_ms, mem0);
#ifdef COOP_WITH_STT
    if (mode == "stt-wav") return RunSttWav(m, speech, wavs);
    if (mode == "stt-tests") return RunSttTests(m, speech, stt_test[0], stt_test[1], stt_test[2]);
#ifdef COOP_WITH_MIC
    if (mode == "voice") return RunVoice(m, speech, opt.threads, world_file);
#else
    if (mode == "voice" || mode == "mic-test")
        return std::fprintf(stderr, "the microphone is read only on Windows and macOS so far; --stt-wav reads a file\n"), 2;
#endif
#endif
    return RunChat(m, opt.threads, world_file);
}
