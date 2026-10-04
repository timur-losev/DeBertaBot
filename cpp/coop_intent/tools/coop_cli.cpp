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
//   coop_cli --location-tests     location_tests.jsonl: the map places found in each line (no model)
//   coop_cli --bench              latency on the golden lines, load time, memory
//   coop_cli --tokenize "text"    the words, pieces and ids of one line
// every mode first prints the bot it runs on (directory, labels, gate, threshold)
// options: --model-dir DIR (export_cpp.py output: intent_config.json, vocab.tsv and the model files
//          it lists under "members"), --threads N (per model, default 4),
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
#include <memory>
#include <numeric>
#include <random>
#include <sstream>
#include <string>
#include <vector>

#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#include <psapi.h>
#endif

#include "coop_intent/bot_brain.h"
#include "coop_intent/intent_model.h"
#include "coop_intent/tokenizer.h"
#include "coop_intent/unicode.h"
#include "nlohmann/json.hpp"

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
    const json j = json::parse(cfg_text);
    coop::IntentConfig& c = m.cfg;
    c.labels = j["labels"].get<std::vector<std::string>>();
    c.families = j["families"].get<std::unordered_map<std::string, std::string>>();
    c.phrases = j["phrases"].get<std::unordered_map<std::string, std::string>>();
    c.threshold = j["threshold"].get<double>();
    c.gate = j.value("gate", std::string("top"));
    m.members = j.value("members", std::vector<std::string>{"model.onnx"});
    c.safe_intents = j["safe_intents"].get<std::vector<std::string>>();
    c.on_signal = j["regex"]["on_signal"].get<std::string>();
    c.other = j["regex"]["other"].get<std::string>();
    c.negation = j["regex"]["negation"].get<std::string>();
    if (j.contains("locations")) {   // the map's named places (scripts/coop/locations.json)
        const json& L = j["locations"];
        c.has_locations = true;
        for (const json& o : L["objects"])
            c.locations.objects.push_back({o["id"], o["words"].get<std::vector<std::string>>(),
                                           o["qualifiers"].get<std::vector<std::string>>()});
        for (const json& q : L["qualifiers"])
            c.locations.qualifiers.push_back({q["id"], q["words"].get<std::vector<std::string>>(),
                                              q["lone"].is_null() ? std::string() : q["lone"].get<std::string>()});
        for (const json& t : L["named"]) c.locations.named.push_back({t["phrase"], t["object"], t["qualifier"]});
        for (const json& z : L["zones"]) c.locations.zones.push_back({z["id"], z["words"].get<std::vector<std::string>>()});
        c.locations.ignore = L["ignore"].get<std::vector<std::string>>();
        c.locations.words = L["words"].get<std::unordered_map<std::string, std::vector<std::string>>>();
    }
    coop::DebertaTokenizer::Options o;
    o.cls_id = j["cls_id"].get<int32_t>();
    o.sep_id = j["sep_id"].get<int32_t>();
    o.unk_id = j["unk_id"].get<int32_t>();
    o.max_len = j["max_len"].get<int>();
    for (auto& [text, id] : j["added_tokens"].items()) o.added.push_back({text, id.get<int32_t>()});
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

// a place record as one comparable string: "<primary>: object/qualifier/zone/role/flag/inferred; ..."
std::string PlacesStr(const coop::PlaceRecord& r, const coop::LocationMatcher& m) {
    std::string s = std::to_string(r.primary) + ":";
    for (const coop::PlaceTarget& t : r.targets) {
        auto dash = [](const std::string& x) { return x.empty() ? std::string("-") : x; };
        s += " " + (t.object >= 0 ? m.ObjectId(t.object) : "-") + "/" + (t.qualifier >= 0 ? m.QualifierId(t.qualifier) : "-") +
             "/" + (t.zone >= 0 ? m.ZoneId(t.zone) : "-") + "/" + dash(coop::PlaceRoleName(t.role)) + "/" +
             dash(coop::PlaceFlagName(t.flag)) + "/" + (t.inferred ? "1" : "0") + ";";
    }
    return s;
}

// the same string from locations.record() as the Python bot wrote it (null: no record)
std::string PlacesStr(const json& r) {
    if (r.is_null()) return "-1:";
    std::string s = std::to_string(r["primary"].get<int>()) + ":";
    for (const json& t : r["targets"]) {
        auto f = [&](const char* k) { return t[k].is_null() ? std::string("-") : t[k].get<std::string>(); };
        s += " " + f("object") + "/" + f("qualifier") + "/" + f("zone") + "/" + f("role") + "/" + f("flag") + "/" +
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

// what the planner gets, for the chat's debug line: "* north door (basement) [mine]"
std::string PlacesText(const coop::PlaceRecord& r, const coop::LocationMatcher& m) {
    std::string s;
    for (size_t k = 0; k < r.targets.size(); ++k) {
        const coop::PlaceTarget& t = r.targets[k];
        if (k) s += "; ";
        if (static_cast<int>(k) == r.primary) s += "* ";
        std::string name;
        for (const std::string& part : {t.qualifier >= 0 ? m.QualifierId(t.qualifier) : std::string(),
                                        t.object >= 0 ? m.ObjectId(t.object) : std::string(),
                                        t.zone >= 0 ? m.ZoneId(t.zone) : std::string()})
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
    size_t ok = 0, with_place = 0;
    int shown = 0;
    for (const json& r : rows) {
        const std::string text = r["text"];
        const coop::PlaceRecord rec = matcher.Find(text);
        const std::string got = PlacesStr(rec, matcher), want = PlacesStr(r["places"]);
        with_place += !rec.targets.empty();
        if (got == want)
            ++ok;
        else if (shown++ < 12)
            std::printf("  %s\n    python %s\n    c++    %s\n", Escaped(text).c_str(), want.c_str(), got.c_str());
    }
    std::printf("location tests, %zu lines (%zu name a place): the C++ record equals the Python record on %zu/%zu\n",
                rows.size(), with_place, ok, rows.size());
    return ok == rows.size() ? 0 : 1;
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
    if (missing) std::printf("%s", kMissingKeys);
    std::printf("decide tests, %zu steps over both gates: C++ decided what the Python bot decided on %zu/%zu\n", n, ok, n);
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
};
const std::vector<std::string> kAck = {"Copy.", "Noted.", "Heard."};

// a label the demo has no lines for (a newer model) still gets an answer
const std::vector<std::string>& LinesFor(const std::string& label) {
    auto it = kLines.find(label);
    return it != kLines.end() ? it->second : kAck;
}
const std::vector<std::string> kAgain = {"Say again?", "Didn't catch that.", "Come again?"};

int RunChat(Model& m, int threads) {
    coop::BotBrain brain;
    std::string err;
    if (!brain.Init(m.cfg, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
    std::vector<float> p;
    Classify(m, m.tok.Encode("warm up"), &p, &err);
    std::mt19937 rng(static_cast<unsigned>(Clock::now().time_since_epoch().count()));
    auto pick = [&](const std::vector<std::string>& v) { return v[rng() % v.size()]; };
    bool why = true;
    std::printf("ready (C++, ONNX Runtime CPU, %d threads). threshold %.2f. Talk to your teammate in English; /why /t <x> /q\n\n",
                threads, brain.threshold);
    for (;;) {
        std::printf("you> ");
        std::fflush(stdout);
        std::string line;
        if (!ReadLine(&line)) return std::printf("\n"), 0;
        {   // coop_bot.py strips the line with str.strip(): the same Unicode whitespace here
            std::u32string u = coop::DecodeUtf8(line);
            size_t b = 0, e = u.size();
            while (b < e && coop::IsPySpace(u[b])) ++b;
            while (e > b && coop::IsPySpace(u[e - 1])) --e;
            line = coop::EncodeUtf8(std::u32string_view(u).substr(b, e - b));
        }
        if (line.empty()) continue;
        if (line == "/q" || line == "/quit") return 0;
        if (line == "/why") { why = !why; continue; }
        if (line.rfind("/t ", 0) == 0) {
            brain.threshold = std::atof(line.c_str() + 3);
            std::printf("  threshold %.2f\n", brain.threshold);
            continue;
        }
        const auto t0 = Clock::now();
        const auto ids = m.tok.Encode(line);
        if (!Classify(m, ids, &p, &err)) return std::fprintf(stderr, "%s\n", err.c_str()), 1;
        const double ms = Ms(Clock::now() - t0);
        const int pending_before = brain.Pending();
        const coop::Decision d = brain.Decide(line, p);
        if (d.intent < 0) return std::fprintf(stderr, "the model does not fit intent_config.json\n"), 1;
        const std::string& intent = m.cfg.labels[d.intent];
        std::string reply;
        switch (d.action) {
            case coop::Action::Negated: reply = "Copy, standing down."; break;
            case coop::Action::SayAgain: reply = pick(kAgain); break;
            case coop::Action::Ignore: reply = pick(kAck); break;
            case coop::Action::Execute: reply = "Now! " + pick(LinesFor(m.cfg.labels[pending_before])); break;
            case coop::Action::Go: reply = "Going!"; break;
            case coop::Action::Wait: reply = pick(kLines.at("WAIT")); break;
            case coop::Action::Queued: reply = "Ready to " + m.cfg.phrases[intent] + ". On your go."; break;
            case coop::Action::Act: reply = pick(LinesFor(intent)); break;
        }
        if (d.other && (d.action == coop::Action::Act || d.action == coop::Action::Queued) && intent != "HOLD_OTHER_ANGLE")
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
    }
}

}  // namespace

int main(int argc, char** argv) {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
#endif
    Model m;
    m.dir = COOP_DEFAULT_MODEL_DIR;
    std::string mode = "chat", tokenize_text;
    coop::OrtBackend::Options opt;
    bool parallel = true;
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
        else {
            std::fprintf(stderr, "usage: coop_cli [--golden | --tokenizer-tests | --dialogue | --gate-tests | --decide-tests |\n"
                                 "                 --bench |\n"
                                 "                 --tokenize TEXT]\n"
                                 "                [--model-dir DIR] [--threads N] [--no-spin] [--sequential]\n");
            return 2;
        }
    }
    std::string err;
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
    return RunChat(m, opt.threads);
}
