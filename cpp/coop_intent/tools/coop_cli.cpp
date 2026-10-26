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
//          --tts-speed X (> 1 faster), --tts-threads N (default 1)
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
//   --decider DIR                 a second reader of every line beside the ensemble (decider.h: decider-2b with the
//                                 bot's LoRA, GGUF; DIR is scripts/coop/decider/export_game.py's output). Off without it.
//                                 --decider-mode avg (default: the two readers' probabilities averaged) | only (the
//                                 decider's alone), --decider-threads N (default 8), --decider-gpu-layers N (default 0)
//   coop_cli --decider DIR --decider-tests FILE   the line's tokens against upstream's tokenizer and the probabilities
//                                 against decider_eval's (export_game.py writes FILE)
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
#include <memory>
#include <mutex>
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
#include "coop_intent/decider.h"
#include "coop_intent/intent_model.h"
#include "coop_intent/bro.h"
#include "coop_intent/localize.h"
#include "coop_intent/rewriter.h"
#include "coop_intent/speech.h"
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
            for (const auto& list : c.locations.words)
                c.locations.has_pointers = c.locations.has_pointers || coop::LocationVocab::PointerList(list.first);
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
    return sc;
}

bool ParseWorld(const json& j, coop::WorldState* w, std::string* err) {
    *w = coop::WorldState();
    try {
        for (const json& e : j.value("entities", json::array())) {
            coop::WorldEntity x;
            x.id = e.at("id").get<std::string>();
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
           (o.has_item ? "/item:" + (o.item.empty() ? std::string("-") : o.item) + "/" + (o.item_id.empty() ? std::string("-") : o.item_id) : std::string());
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
           (o.contains("item") ? "/item:" + LabelStr(o["item"]) + "/" + LabelStr(o["item_id"]) : std::string());
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
};

// "what do you see?" as a Russian or Spanish player says it (lower case, Cyrillic and accents included)
bool SeenInOwnWords(const std::string& line) {
    std::u32string u = coop::DecodeUtf8(line);
    for (char32_t& c : u) {
        if (c >= U'A' && c <= U'Z') c = c - U'A' + U'a';
        else if (c >= U'А' && c <= U'Я') c = c - U'А' + U'а';
        else if (c == U'Ё') c = U'ё';
    }
    std::u32string t;
    for (char32_t c : u) t += (c == U'?' || c == U'¿' || c == U'!' || c == U'¡' || c == U',' || c == U'.') ? U' ' : c;
    const std::string s = " " + coop::EncodeUtf8(t) + " ";
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

// --language en|ru|es: the player's language. English goes as it always went (the router sends a line to the decoder only
// when it gives several orders or leans on the talk). Russian and Spanish lines all go to the decoder (a chain whose decoder
// was trained on three languages, chain v62: scripts/coop/stt/chains6_v62.py), which writes them as English orders; the
// classifier, the place matcher and the planner then read English as before. The router is English and is not asked.
std::string g_language = "en";

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

const std::vector<std::string> kBroOff = {"Okay, I won't anymore.", "Got it, no more.", "Fine, I'll stop."};
const std::string kBroRelapse = "Sorry, habit.";

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
    std::vector<std::string> held;     // order lines of a rewritten line that wait for the answer to the bot's question
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
    };

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
    template <class Each>
    bool Hear(const std::string& heard, const std::string& text, Heard* h, std::string* err, Each&& each) {
        *h = Heard();
        const auto now = Clock::now();
        Chain* c = chain_on ? g_chain : nullptr;
        const bool answering = planner.Mem().has_question;
        const int asked = answering ? planner.Mem().question.intent : -1;   // the order the open question is about
        struct Line {
            std::string heard, text;
        };
        std::vector<Line> todo;
        std::string second;   // while the question is open: the one order the decoder read in an answer
        // the decoder on this line with the talk before it; false when it fails (a line too long for its context)
        auto decode = [&](std::vector<std::string>* pieces) {
            while (!said.empty() && Ms(now - said.front().at) > 1000 * c->memory_seconds) said.pop_front();
            std::vector<std::string> before;
            for (const Said& s : said) before.push_back(s.text);
            const bool bot = !bot_said.text.empty() && Ms(now - bot_said.at) <= 1000 * c->memory_seconds;
            const auto t1 = Clock::now();
            const bool ok = c->Rewrite(before, bot ? bot_said.text : std::string(), planner.World().scene, text, pieces, &h->note);
            h->rewrite_ms += Ms(Clock::now() - t1);
            if (ok) h->decoded = true;
            return ok;
        };
        // a Russian or Spanish line: always to the decoder, which writes it in English (--language)
        const bool foreign = g_language != "en";
        if (c) {
            const auto t0 = Clock::now();
            if (foreign) h->route = 1.0;
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
            if (foreign || !c->router || h->route >= c->cut || scene_look) {
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
                for (std::string piece : pieces) {
                    // bot v62: the classifier reads an English "hi" / "hi there" as the owner's misheard "hide (there)"
                    // (v57). The decoder's English for «привет», «hola» is no mishearing: it is a greeting
                    if (foreign) {
                        const std::string low = coop::SpeechTextForClassifier(piece);
                        if (low == "hi" || low.rfind("hi ", 0) == 0) piece = "hello" + piece.substr(2);
                    }
                    todo.push_back({piece, coop::SpeechTextForClassifier(piece)});
                }
                h->rewritten = !todo.empty();
            }
        }
        const bool one = todo.size() <= 1;   // the line gives one order line: it may be what settles the open question
        if (!(answering && one)) held.clear();
        // the line as the next ones will be shown it: the orders the bot read in it, when it was rewritten
        std::string kept;
        for (const Line& l : todo) kept += (kept.empty() ? "" : " ") + l.heard + (std::string(".!?").find(l.heard.back()) == std::string::npos ? "." : "");
        if (todo.empty()) todo.push_back({heard, text});
        for (size_t k = 0; k < todo.size(); ++k) {
            Turn t;
            t.line = todo[k].heard;
            if (!Think(todo[k].heard, todo[k].text, &t, err, k > 0)) return false;
            if (k == 0 && !second.empty() && t.r.action == "say_again" && planner.Mem().has_question) {
                // "say again" changed nothing in the bot or the planner: the decoder's reading of the answer goes instead
                t = Turn();
                t.line = second;
                if (!Think(second, coop::SpeechTextForClassifier(second), &t, err)) return false;
                h->rewritten = true;
                kept = second;
            } else if (k == 0 && c && !h->decoded && todo.size() == 1 && t.r.action == "say_again") {
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
        }
        h->held = held;
        if (g_chain) {
            // a line the bot asked to hear again was not dealt with: the talk so far stays as it was
            bool again = true;
            for (const Turn& t : h->turns) again = again && t.r.action == "say_again";
            if (!again) {
                // a Russian or Spanish line is remembered as the player said it: the decoder learned its earlier lines in
                // the player's language (chains6_v62.py), the bot's own lines in English
                said.push_back({foreign || kept.empty() ? text : kept, now});
                while (said.size() > g_chain->memory_lines) said.pop_front();
                const std::string& own = h->turns.back().r.say;
                bot_said = own.empty() ? Said() : Said{own, now};
            }
        }
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
    bool Think(const std::string& heard, const std::string& text, Turn* turn, std::string* err, bool continued = false) {
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
    std::printf("voice: %s, %d Hz, loaded in %.0f ms\n", voice.Describe().c_str(), voice.SampleRate(), Ms(Clock::now() - t0));
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
        if (!voice.Speak(text, &x, &err, s)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        const double ms = Ms(Clock::now() - t1), seconds = static_cast<double>(x.size()) / voice.SampleRate();
        total_ms += ms;
        total_s += seconds;
        const std::string path = out_dir + "/" + s + ".wav";
        if (!WriteWav(path, x, voice.SampleRate(), &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        std::printf("%-6s %.2f s of audio in %.0f ms\n", s.c_str(), seconds, ms);
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
//   {"cmd":"ptt_down"}                                           the talk key went down: the clip starts (with
//                                                                its 0.2 s pre-roll), the bot's voice stops
//   {"cmd":"ptt_up","id":8,"world":{...}}                        the key came up: recognize, classify, plan
//   {"cmd":"ptt_cancel"}                                         drop the clip
//   {"cmd":"wav","id":9,"path":"clip.wav","world":{...}}         a 16-bit PCM file instead of the microphone
//   {"cmd":"world","world":{...}}                                the world alone
//   {"cmd":"say","text":"Contact left!"}                         the bot's voice (--tts); {"cmd":"hush"} stops it
//   {"cmd":"say","id":12,"text":"Contact left!","speaker":"p311","speed":1.0}   with --tts-piper: the line as audio,
//                                                                answered by "speech" (speaker and speed optional:
//                                                                the ones the service was started with); "hush" and
//                                                                "ptt_down" drop the lines not made yet
//        "terms":{"thing":{"a spike trap":{"ru":{"text":"ловушка с шипами","acc":"ловушку с шипами"},"es":{"text":
//        "una trampa de pinchos"}}}}: the words of the level's labelled things the line names, in the languages the
//        label has; the reply table takes the player's (localize.h Terms)
//   {"cmd":"reset"} {"cmd":"threshold","value":0.7} {"cmd":"ping"} {"cmd":"quit"}
//
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
//        "ammo" (StateQuestion; a v64 bot's STATUS_REPORT and BODY_STATE always carry one).
//        With --replies-bro: "bro" "on" / "off" when the line switched the habit (bro.h; "off" comes with the bot's
//        agreement as its words and SMALL_TALK, nothing else read), "bro_active" whether this reply was written with it
//   {"event":"nothing","id":8,...}    the clip had no words;  {"event":"too_short","id":8}
//   {"event":"speech","id":12,"text":"Contact left!","rate":22050,"audio_s":0.9,"ms":61,"pcm16":"<base64>"}
//        the line as 16-bit little-endian mono samples (--tts-piper); the game plays it from the bot.
//        {"event":"hushed","id":12}: the line was dropped before it was made ("hush", "ptt_down", a queue of three)
//        "ready" says which voice: "tts_kind" "piper" (the lines come back as audio) or "system" (the process speaks)
//   {"event":"error","id":7,"cmd":"text","message":"..."}        the request was refused; the service goes on
// The service ends when stdin closes (the game is gone) or on "quit".
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
    if (g_replies && !t.reply.empty()) {
        std::string local;
        if (Localize(t.reply, &local)) j["say"] = local, j["say_en"] = t.reply;
        else j["say_untranslated"] = true;
    }
    j["ms"] = t.ms;
    j["on_signal"] = d.on_signal;
    j["other"] = d.other;
    j["negated"] = d.negated;
    j["adjusted"] = r.adjusted;
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
    if (!chat.Init(&err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    bool stt_ready = false, mic_ready = false, tts_ready = false;
    std::string stt_note, mic_note, tts_note, tts_kind;
    // the bot's voice as audio for the game (Piper): made on a thread of its own, so that a line being made never
    // holds up the talk key; one line at a time, three waiting at most
    bool piper_ready = false, local_ready = false;
    std::string local_note;
#ifdef COOP_WITH_STT
    coop::PiperVoice voice, voice_local;
    if (piper) {
        piper_ready = voice.Load(*piper, &err);
        tts_ready = piper_ready;
        tts_note = piper_ready ? voice.Describe() : err;
        if (piper_ready) tts_kind = "piper";
    }
    // the player's language's voice (--voice-local): the lines written in it are said with it
    if (piper_ready && local_voice) {
        local_ready = voice_local.Load(*local_voice, &err);
        local_note = local_ready ? voice_local.Describe() : err;
    }
#else
    if (piper) tts_note = "this coop_cli was built without sherpa-onnx: no Piper voice";
#endif
    (void)local_voice;
    struct SpeechJob {
        json id;
        std::string text, speaker;
        float speed = 0;
        bool local = false;   // in the player's language, with voice_local
    };
    std::mutex out_mutex, jobs_mutex;
    std::condition_variable jobs_cv;
    std::deque<SpeechJob> jobs;
    bool jobs_done = false;
    std::thread speaker;
#ifdef COOP_WITH_STT
    coop::SpeechRecognizer stt;
    if (want_stt) {
        stt_ready = LoadSpeech(stt, speech, &err);
        if (!stt_ready) stt_note = err;
    } else {
        stt_note = "switched off (--no-stt)";
    }
#ifdef _WIN32
    MicCapture mic;
    if (stt_ready) {
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
                    jobs_cv.wait(lock, [&] { return jobs_done || !jobs.empty(); });
                    if (jobs.empty()) return;   // done, and nothing left to say
                    job = std::move(jobs.front());
                    jobs.pop_front();
                }
                const auto t0 = Clock::now();
                std::vector<float> x;
                std::string speak_err;
                const coop::PiperVoice& v = job.local ? voice_local : voice;
                if (!v.Speak(job.text, &x, &speak_err, job.speaker, job.speed)) {
                    send({{"event", "error"}, {"id", job.id}, {"cmd", "say"}, {"message", speak_err}});
                    continue;
                }
                const int rate = v.SampleRate();
                send({{"event", "speech"}, {"id", job.id}, {"text", job.text}, {"lang", job.local && g_replies ? g_replies->Language() : std::string("en")},
                      {"rate", rate},
                      {"audio_s", rate > 0 ? static_cast<double>(x.size()) / rate : 0.0}, {"ms", Ms(Clock::now() - t0)}, {"pcm16", Base64(Pcm16(x))}});
            }
        });
    }
#endif
    // the lines not made yet are dropped, and whoever asked for them is told
    auto drop_lines = [&]() {
        std::lock_guard<std::mutex> lock(jobs_mutex);
        for (const SpeechJob& j : jobs) send({{"event", "hushed"}, {"id", j.id}});
        jobs.clear();
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
    send({{"event", "ready"}, {"bot", m.dir}, {"labels", m.cfg.labels}, {"gate", m.cfg.gate}, {"threshold", chat.brain.threshold},
          {"threads", threads}, {"runtime", coop::OrtBackend::RuntimeVersion()}, {"stt", stt_ready}, {"stt_note", stt_note},
          {"mic", mic_ready}, {"mic_note", mic_note}, {"tts", tts_ready}, {"tts_note", tts_note},
          {"tts_kind", tts_kind.empty() ? json(nullptr) : json(tts_kind)},
          {"replies", g_replies ? json({{"language", g_replies->Language()}, {"templates", g_replies->Templates()}}) : json(nullptr)},
          {"bro", g_bro_replies ? json({{"active", g_replies == g_bro_replies}, {"relapse_s", g_bro.RelapseSeconds()},
                                        {"templates", g_bro_replies->Templates()}}) : json(nullptr)},
          {"place_objects", chat.brain.Places().ObjectIds()},   // what the game may send as a place's object (bot v62: teleport)
          {"place_qualifiers", chat.brain.Places().QualifierIds()},   // ... and as its qualifier (bot v64: big, small, cardboard)
          {"voice_local", local_ready}, {"voice_local_note", local_note},
          {"chain", g_chain ? json({{"dir", g_chain->dir}, {"router", g_chain->router != nullptr}, {"cut", g_chain->cut},
                                    {"decoder", Chain::Backend()}, {"gpu", g_chain->decoder_options.gpu_layers != 0},
                                    {"memory_lines", g_chain->memory_lines}, {"memory_seconds", g_chain->memory_seconds}})
                            : json(nullptr)},
          {"language", g_language},
          {"decider", g_decider ? json({{"dir", g_decider->dir}, {"mode", g_decider->mode}, {"source", g_decider->source},
                                        {"threads", g_decider->options.threads}, {"gpu", g_decider->options.gpu_layers != 0}})
                                : json(nullptr)}});
    bool listening = false;
    Clock::time_point down = Clock::now();
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
            // a heard or typed line through the classifier and the planner
            auto respond = [&](const std::string& raw, bool spoken, double audio_s, double stt_ms) {
                const std::string heard = StripPy(raw);
                if (heard.empty()) {
                    send({{"event", "nothing"}, {"id", id}, {"audio_s", audio_s}, {"stt_ms", stt_ms}});
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
                json turns = json::array();
                if (!chat.Hear(heard, spoken ? coop::SpeechTextForClassifier(heard) : heard, &h, &err, [&](const Chat::Heard&, const Chat::Turn& t) {
                        json turn = ReplyJson(chat, t);
                        turn.erase("event");
                        turn["line"] = t.line;
                        turns.push_back(std::move(turn));
                    })) {
                    fail(err);
                    return;
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
                send(j);
            };
            if (cmd == "text") {
                respond(q.at("text").get<std::string>(), false, 0, 0);
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
                send({{"event", "listening"}, {"id", id}});
#else
                fail("no microphone in this build");
#endif
            } else if (cmd == "ptt_up" || cmd == "ptt_cancel") {
#if defined(COOP_WITH_STT) && defined(_WIN32)
                if (!listening) {
                    fail("the talk key was not down");
                    continue;
                }
                listening = false;
                const double held = Ms(Clock::now() - down);
                const std::vector<float> clip = mic.End();
                if (cmd == "ptt_cancel") {
                    send({{"event", "cancelled"}, {"id", id}});
                } else if (held < 200) {
                    send({{"event", "too_short"}, {"id", id}, {"held_ms", held}});
                } else {
                    const auto t0 = Clock::now();
                    std::string heard;
                    if (!stt.Transcribe(clip.data(), clip.size(), MicCapture::kSampleRate, &heard, &err)) {
                        fail(err);
                        continue;
                    }
                    respond(heard, true, static_cast<double>(clip.size()) / MicCapture::kSampleRate, Ms(Clock::now() - t0));
                }
#else
                fail("no microphone in this build");
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
                if (!stt.Transcribe(x.data(), x.size(), rate, &heard, &err)) {
                    fail(err);
                    continue;
                }
                respond(heard, true, static_cast<double>(x.size()) / rate, Ms(Clock::now() - t0));
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
                        if (local_ready && g_replies) {
                            if (q.value("localized", false) || IsLocalized(text)) in_local = true;
                            else if (LocalizeMixed(text, &local, &terms)) text = local, in_local = true;
                        } else if (g_replies && g_replies->Language() == "en") {
                            // English with the habit: the game's line in the persona's words, said by the English voice
                            if (!q.value("localized", false) && !IsLocalized(text) && LocalizeMixed(text, &local, &terms)) text = local;
                        }
                        jobs.push_back({id, text, in_local ? std::string() : q.value("speaker", std::string()), q.value("speed", 0.0f), in_local});
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
                send({{"event", "reset"}, {"id", id}});
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
    coop::VoiceOptions piper, voice_local;
    std::string replies_file, bro_file, bro_check;
    bool bro_on = false;
    double bro_relapse = 0;
    std::string tts_demo_dir, tts_text = "Contact left! Moving to the ping. Which door? The one ahead, 8 m?";
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (a == "--model-dir" && i + 1 < argc) m.dir = argv[++i];
        else if (a == "--tts-piper" && i + 1 < argc) piper.model_dir = argv[++i];
        else if (a == "--tts-speaker" && i + 1 < argc) piper.speaker = argv[++i];
        else if (a == "--tts-speed" && i + 1 < argc) piper.speed = static_cast<float>(std::atof(argv[++i]));
        else if (a == "--tts-threads" && i + 1 < argc) piper.threads = std::atoi(argv[++i]);
        else if (a == "--tts-demo" && i + 1 < argc) mode = "tts-demo", tts_demo_dir = argv[++i];
        else if (a == "--tts-text" && i + 1 < argc) tts_text = argv[++i];
        else if (a == "--chain" && i + 1 < argc) chain.dir = argv[++i];
        else if (a == "--decoder-cpu") decoder_cpu = true;
        else if (a == "--decoder-threads" && i + 1 < argc) decoder_threads = std::atoi(argv[++i]);
        else if (a == "--chain-tests") mode = "chain-tests";
        else if (a == "--language" && i + 1 < argc) g_language = argv[++i];
        else if (a == "--replies-bro" && i + 1 < argc) bro_file = argv[++i];
        else if (a == "--bro" && i + 1 < argc) bro_on = std::string(argv[++i]) == "on";
        else if (a == "--bro-relapse" && i + 1 < argc) bro_relapse = std::atof(argv[++i]);
        else if (a == "--bro-check" && i + 1 < argc) mode = "bro-check", bro_check = argv[++i];
        else if (a == "--replies" && i + 1 < argc) replies_file = argv[++i];
        else if (a == "--replies-check" && i + 1 < argc) mode = "replies-check", replies_file = argv[++i];
        else if (a == "--voice-local" && i + 1 < argc) voice_local.model_dir = argv[++i];
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
        else if (a == "--stt-model" && i + 1 < argc) speech.model_dir = argv[++i];
        else if (a == "--stt-threads" && i + 1 < argc) speech.threads = std::atoi(argv[++i]);
        else if (a == "--voice") mode = "voice";
        else if (a == "--mic-test" && i + 1 < argc) mode = "mic-test", mic_seconds = std::atof(argv[++i]);
        else if (a == "--stt-wav" && i + 1 < argc) mode = "stt-wav", wavs.push_back(argv[++i]);
        else if (a == "--stt-tests" && i + 3 < argc) mode = "stt-tests", stt_test = {argv[i + 1], argv[i + 2], argv[i + 3]}, i += 3;
        else {
            std::fprintf(stderr, "usage: coop_cli [--golden | --tokenizer-tests | --dialogue | --gate-tests | --decide-tests |\n"
                                 "                 --location-tests | --world-tests | --item-tests | --bench | --tokenize TEXT | --speech-text-tests FILE |\n"
                                 "                 --voice | --mic-test SECONDS | --stt-wav FILE ... | --stt-tests LIST WAVDIR EXPECTED |\n"
                                 "                 --serve [--no-stt] [--tts | --tts-piper DIR] | --tts-piper DIR --tts-demo OUTDIR [--tts-text TEXT]]\n"
                                 "                [--model-dir DIR] [--threads N] [--no-spin] [--sequential] [--world FILE]\n"
                                 "                [--stt-model DIR] [--stt-threads N]\n"
                                 "                [--tts-speaker NAME[,NAME...]] [--tts-speed X] [--tts-threads N]\n"
                                 "                [--chain DIR [--chain-tests] [--decoder-cpu] [--decoder-threads N]]\n"
                                 "                [--language en|ru|es]\n"
                                 "                [--decider DIR [--decider-tests FILE] [--decider-mode avg|only] [--decider-threads N]\n"
                                 "                 [--decider-gpu-layers N]]\n");
            return 2;
        }
    }
    std::string err;
    if (mode == "speech-text-tests") return RunSpeechTextTests(speech_text_file);
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
        if (!LoadChain(chain, opt, decoder_cpu, decoder_threads, &err)) return std::fprintf(stderr, "%s: %s\n", chain.dir.c_str(), err.c_str()), 1;
        std::printf("chain: %s (%s, decoder on the %s, %d threads, loaded in %.0f ms)\n", chain.dir.c_str(),
                    chain.router ? "router and decoder" : "decoder, no router: every line goes to it", decoder_cpu ? "CPU" : "GPU",
                    decoder_threads, chain.load_ms);
        g_chain = &chain;
    }
    if (g_language != "en" && g_language != "ru" && g_language != "es")
        return std::fprintf(stderr, "--language is en, ru or es, not %s\n", g_language.c_str()), 2;
    if (g_language != "en")
        std::printf("language: %s (every line to the decoder, written in English%s)\n", g_language.c_str(),
                    g_chain ? "" : "; NO decoder is loaded (--chain DIR): the classifier gets the lines as they are and reads little");
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
    voice_local.threads = std::max(piper.threads, 4);   // a Kokoro voice needs them: about 3 s a line on one thread, 0.5 s on four
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
