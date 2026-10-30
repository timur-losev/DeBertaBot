// The bot's long-term memory on Wick's structured facts (bot_memory.h). Built as C++20 with Wick's core.
#include "coop_intent/bot_memory.h"

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <streambuf>

#include "coop_intent/teach.h"
#include "waxcpp/memory_orchestrator.hpp"

namespace coop {

namespace {

// Wick traces every open and rebuild on std::cerr ("[STORE-TRACE] ...", a dozen lines a start), and the game logs the
// brain's stderr: quiet while the memory calls it. coop_cli's own messages go through fprintf and are not touched
struct QuietCerr {
    struct Null : std::streambuf {
        int overflow(int c) override { return c; }
    } null;
    std::streambuf* old;
    QuietCerr() : old(std::cerr.rdbuf(&null)) {}
    ~QuietCerr() { std::cerr.rdbuf(old); }
};

constexpr char kSep = '|';

std::string LineEntity(const std::string& lang, const std::string& heard) { return "line|" + lang + kSep + heard; }
std::string NameEntity(const std::string& map, const std::string& entity) { return "name|" + map + kSep + entity; }
std::string ColourEntity(const std::string& map, const std::string& entity) { return "colour|" + map + kSep + entity; }
std::string SayEntity(const std::string& lang, const std::string& word) { return "say|" + lang + kSep + word; }
std::string PhraseEntity(const std::string& lang, const std::string& from) { return "phrase|" + lang + kSep + from; }
std::string SettingEntity(const std::string& name) { return std::string("setting|player") + kSep + name; }

// "line|ru|heard" -> {"ru", "heard"}; false when it is not of that kind
bool Split(const std::string& entity, const std::string& kind, std::string* a, std::string* b) {
    const std::string head = kind + kSep;
    if (entity.rfind(head, 0) != 0) return false;
    const size_t at = entity.find(kSep, head.size());
    if (at == std::string::npos) return false;
    *a = entity.substr(head.size(), at - head.size());
    *b = entity.substr(at + 1);
    return true;
}

std::vector<std::string> Rows(const std::string& value) {
    std::vector<std::string> out;
    std::string cur;
    for (char c : value) {
        if (c == '\n') {
            if (!cur.empty()) out.push_back(cur);
            cur.clear();
        } else {
            cur += c;
        }
    }
    if (!cur.empty()) out.push_back(cur);
    return out;
}

std::string Meta(const waxcpp::Metadata& m, const char* key) {
    const auto it = m.find(key);
    return it == m.end() ? std::string() : it->second;
}

}  // namespace

struct BotMemory::Impl {
    std::unique_ptr<waxcpp::MemoryOrchestrator> wax;
    std::string path;
    std::string broken;   // where a file the store could not read was put aside at the last Open; empty: none
    std::vector<MemoryLine> lines;
    std::vector<MemoryName> names;
    std::vector<MemoryColour> colours;
    std::vector<MemorySaying> sayings;
    std::vector<MemoryPhrase> phrases;
    std::vector<MemorySetting> settings;

    // the facts in force, read back after every write: a few hundred at most
    void Reload() {
        lines.clear();
        names.clear();
        colours.clear();
        sayings.clear();
        phrases.clear();
        settings.clear();
        for (const waxcpp::StructuredMemoryEntry& e : wax->RecallFactsByEntityPrefix("", -1)) {
            std::string a, b;
            // when it was kept: a compacted file has the first time in "kept_ms"
            const std::string kept = Meta(e.metadata, "kept_ms");
            const int64_t at = kept.empty() ? e.timestamp_ms : std::atoll(kept.c_str());
            if (Split(e.entity, "line", &a, &b) && e.attribute == "means") {
                MemoryLine l;
                l.lang = a;
                l.heard = b;
                l.lines = Rows(e.value);
                l.intent = Meta(e.metadata, "intent");
                l.source = Meta(e.metadata, "source");
                const std::string d = Meta(e.metadata, "doubts");
                l.doubts = d.empty() ? 0 : std::atoi(d.c_str());
                l.at_ms = at;
                lines.push_back(std::move(l));
            } else if (Split(e.entity, "name", &a, &b)) {
                names.push_back({a, b, e.attribute, e.value, at});
            } else if (Split(e.entity, "colour", &a, &b) && e.attribute == "colour") {
                colours.push_back({a, b, e.value, at});
            } else if (Split(e.entity, "say", &a, &b) && e.attribute == "say") {
                sayings.push_back({a, b, e.value, at});
            } else if (Split(e.entity, "phrase", &a, &b) && e.attribute == "say") {
                phrases.push_back({a, b, Meta(e.metadata, "mute") == "1" ? std::string() : e.value, at, Meta(e.metadata, "word") == "1"});
            } else if (Split(e.entity, "setting", &a, &b) && e.attribute == "value") {
                settings.push_back({b, std::atof(e.value.c_str()), at});
            }
        }
    }

    template <class F>
    bool Write(std::string* err, F&& f) {
        if (!wax) return *err = "the memory is not open", false;
        const QuietCerr quiet;
        try {
            f();
            wax->Flush();
            Reload();
            return true;
        } catch (const std::exception& e) {
            return *err = std::string("memory: ") + e.what(), false;
        }
    }
};

BotMemory::BotMemory() : impl_(std::make_unique<Impl>()) {}
BotMemory::~BotMemory() { Close(); }

namespace {

waxcpp::OrchestratorConfig MemoryConfig() {
    waxcpp::OrchestratorConfig cfg;
    cfg.enable_vector_search = false;   // no embedder: the keys are words
    cfg.enable_text_search = true;
    cfg.enable_structured_memory = true;
    cfg.query_embedding_policy = waxcpp::QueryEmbeddingPolicy::kNever;
    cfg.rag.search_mode = {waxcpp::SearchModeKind::kTextOnly, 0.0f};
    cfg.require_on_device_providers = false;
#ifdef WAXCPP_ORCHESTRATOR_WAL_SIZE
    // the store's write-ahead log is held by the file from the start: Wick's 256 MiB would make every player's file
    // 268 MB. Every write here is committed at once (Flush), so the log never holds more than one write: 1 MiB
    cfg.wal_size_bytes = 1024 * 1024;
#endif
    return cfg;
}

// Every commit appends the store's whole table of contents and leaves the old one behind: 600 writes made a 31 MB file
// (2026-10-29). A file over this is written anew at open, the facts in force and nothing else
constexpr std::uintmax_t kCompactAbove = 4ull * 1024 * 1024;

std::filesystem::path PathOf(const std::string& utf8) { return std::filesystem::path(std::u8string(utf8.begin(), utf8.end())); }
std::filesystem::path With(const std::filesystem::path& p, const char* suffix) {
    std::filesystem::path q = p;
    q += suffix;
    return q;
}
void RemoveStore(const std::filesystem::path& p) {
    std::error_code ec;
    std::filesystem::remove(p, ec);
    std::filesystem::remove(With(p, ".writer.lease"), ec);
}

}  // namespace

bool BotMemory::Open(const std::string& path, std::string* err) {
    Close();
    impl_->broken.clear();
    const QuietCerr quiet;
    try {
        const std::filesystem::path p = PathOf(path);
        if (p.has_parent_path()) std::filesystem::create_directories(p.parent_path());
        // a compaction cut short between its two renames left the old file as .bak
        const std::filesystem::path bak = With(p, ".bak");
        if (!std::filesystem::exists(p) && std::filesystem::exists(bak)) std::filesystem::rename(bak, p);
        try {
            impl_->wax = std::make_unique<waxcpp::MemoryOrchestrator>(p, MemoryConfig());
        } catch (const std::exception& e) {
            // a file the store cannot read (cut short, overwritten, empty) is put aside, not lost, and a new memory starts:
            // the player's game goes on with one. A file another brain holds is no broken file: the caller tries again
            const std::string why = e.what();
            if (why.find("lease already held") != std::string::npos || !std::filesystem::exists(p)) throw;
            const auto now = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
            const std::filesystem::path aside = With(p, (".broken-" + std::to_string(now)).c_str());
            std::filesystem::rename(p, aside);
            std::error_code ec;
            std::filesystem::remove(With(p, ".writer.lease"), ec);
            std::fprintf(stderr, "memory: %s could not be read (%s): put aside as %s, a new memory starts\n", path.c_str(), why.c_str(),
                         reinterpret_cast<const char*>(aside.u8string().c_str()));
            impl_->broken = reinterpret_cast<const char*>(aside.u8string().c_str());
            impl_->wax = std::make_unique<waxcpp::MemoryOrchestrator>(p, MemoryConfig());
        }
        impl_->path = path;
        if (std::filesystem::file_size(p) > kCompactAbove) {
            // the facts in force into a new file (their own times kept), then the new file in the old one's place
            const std::vector<waxcpp::StructuredMemoryEntry> facts = impl_->wax->RecallFactsByEntityPrefix("", -1);
            const std::filesystem::path fresh = With(p, ".compact");
            RemoveStore(fresh);
            {
                waxcpp::MemoryOrchestrator out(fresh, MemoryConfig());
                size_t n = 0;
                for (const waxcpp::StructuredMemoryEntry& e : facts) {
                    waxcpp::Metadata m = e.metadata;
                    if (!m.count("kept_ms")) m["kept_ms"] = std::to_string(e.timestamp_ms);
                    out.RememberFact(e.entity, e.attribute, e.value, m);
                    if (++n % 500 == 0) out.Flush();   // the log holds a few thousand at most
                }
                out.Flush();
                out.Close();
            }
            const auto before = std::filesystem::file_size(p);
            impl_->wax->Close();
            impl_->wax.reset();
            std::filesystem::rename(p, bak);
            std::filesystem::rename(fresh, p);
            RemoveStore(bak);
            std::fprintf(stderr, "memory: %s compacted, %llu -> %llu bytes, %zu facts\n", path.c_str(), static_cast<unsigned long long>(before),
                         static_cast<unsigned long long>(std::filesystem::file_size(p)), facts.size());
            impl_->wax = std::make_unique<waxcpp::MemoryOrchestrator>(p, MemoryConfig());
        }
        impl_->Reload();
        return true;
    } catch (const std::exception& e) {
        impl_->wax.reset();
        return *err = "memory " + path + ": " + e.what(), false;
    }
}

void BotMemory::Close() {
    if (!impl_->wax) return;
    const QuietCerr quiet;
    try {
        impl_->wax->Close();
    } catch (...) {
    }
    impl_->wax.reset();
    impl_->lines.clear();
    impl_->names.clear();
    impl_->colours.clear();
}

bool BotMemory::IsOpen() const { return impl_->wax != nullptr; }
const std::string& BotMemory::Path() const { return impl_->path; }
const std::string& BotMemory::PutAside() const { return impl_->broken; }

// when a fact was kept, as the memory reads it back: the caller's time (a doubt keeps the line's first time), else now. Kept in
// the fact itself: the store's own time of a fact read back is its frame's, a few ms off the time the fact had when written
static std::string KeptMs(int64_t at_ms) {
    if (at_ms > 0) return std::to_string(at_ms);
    return std::to_string(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count());
}

bool BotMemory::KeepLine(const MemoryLine& line, std::string* err) {
    if (line.heard.empty() || line.lines.empty()) return *err = "memory: a line to keep needs the heard words and a meaning", false;
    std::string value;
    for (const std::string& l : line.lines) value += (value.empty() ? "" : "\n") + l;
    return impl_->Write(err, [&] {
        impl_->wax->RememberFact(LineEntity(line.lang, line.heard), "means", value,
                                 {{"intent", line.intent}, {"source", line.source}, {"doubts", std::to_string(line.doubts)},
                                  {"kept_ms", KeptMs(line.at_ms)}});
    });
}

const MemoryLine* BotMemory::LineFor(const std::string& lang, const std::string& heard) const {
    if (heard.empty()) return nullptr;
    for (const MemoryLine& l : impl_->lines)
        if (l.lang == lang && l.heard == heard) return &l;
    for (const MemoryLine& l : impl_->lines)
        if (l.lang == lang && NearLine(l.heard, heard)) return &l;
    return nullptr;
}

bool BotMemory::DoubtLine(const std::string& lang, const std::string& heard, bool* removed, std::string* err) {
    *removed = false;
    const MemoryLine* l = nullptr;
    for (const MemoryLine& x : impl_->lines)
        if (x.lang == lang && x.heard == heard) l = &x;
    if (!l) return *err = "", false;
    if (l->doubts + 1 >= 2) {
        *removed = true;
        return ForgetLine(lang, heard, err);
    }
    MemoryLine doubted = *l;
    ++doubted.doubts;
    return KeepLine(doubted, err);
}

bool BotMemory::ForgetLine(const std::string& lang, const std::string& heard, std::string* err) {
    bool found = false;
    for (const MemoryLine& x : impl_->lines) found = found || (x.lang == lang && x.heard == heard);
    if (!found) return *err = "", false;
    return impl_->Write(err, [&] { impl_->wax->ForgetFact(LineEntity(lang, heard), "means"); });
}

bool BotMemory::KeepName(const MemoryName& name, std::string* err) {
    if (name.entity.empty() || name.name.empty()) return *err = "memory: a name needs the thing and the words", false;
    return impl_->Write(err, [&] { impl_->wax->RememberFact(NameEntity(name.map, name.entity), name.lang, name.name,
                                                           {{"kind", "name"}, {"kept_ms", KeptMs(name.at_ms)}}); });
}

bool BotMemory::KeepColour(const MemoryColour& colour, std::string* err) {
    if (colour.entity.empty() || colour.colour.empty()) return *err = "memory: a colour needs the thing and the colour", false;
    return impl_->Write(err, [&] {
        impl_->wax->RememberFact(ColourEntity(colour.map, colour.entity), "colour", colour.colour,
                                 {{"kind", "colour"}, {"kept_ms", KeptMs(colour.at_ms)}});
    });
}

bool BotMemory::ForgetThing(const std::string& map, const std::string& entity, bool* any, std::string* err) {
    std::vector<std::string> langs;
    for (const MemoryName& n : impl_->names)
        if (n.map == map && n.entity == entity) langs.push_back(n.lang);
    bool colour = false;
    for (const MemoryColour& c : impl_->colours) colour = colour || (c.map == map && c.entity == entity);
    *any = !langs.empty() || colour;
    if (!*any) return true;
    return impl_->Write(err, [&] {
        for (const std::string& lang : langs) impl_->wax->ForgetFact(NameEntity(map, entity), lang);
        if (colour) impl_->wax->ForgetFact(ColourEntity(map, entity), "colour");
    });
}

bool BotMemory::ForgetName(const std::string& map, const std::string& entity, const std::string& lang, bool* any, std::string* err) {
    *any = false;
    for (const MemoryName& n : impl_->names) *any = *any || (n.map == map && n.entity == entity && n.lang == lang);
    if (!*any) return true;
    return impl_->Write(err, [&] { impl_->wax->ForgetFact(NameEntity(map, entity), lang); });
}

const std::vector<MemoryLine>& BotMemory::Lines() const { return impl_->lines; }
const std::vector<MemoryName>& BotMemory::Names() const { return impl_->names; }
const std::vector<MemoryColour>& BotMemory::Colours() const { return impl_->colours; }
const std::vector<MemorySaying>& BotMemory::Sayings() const { return impl_->sayings; }
const std::vector<MemoryPhrase>& BotMemory::Phrases() const { return impl_->phrases; }
const std::vector<MemorySetting>& BotMemory::Settings() const { return impl_->settings; }

bool BotMemory::KeepPhrase(const MemoryPhrase& phrase, std::string* err) {
    if (phrase.from.empty()) return *err = "memory: a phrase needs the bot's line", false;
    const bool mute = phrase.to.empty();
    return impl_->Write(err, [&] {
        impl_->wax->RememberFact(PhraseEntity(phrase.lang, phrase.from), "say", mute ? std::string("-") : phrase.to,
                                 {{"kind", "phrase"}, {"mute", mute ? "1" : "0"}, {"word", phrase.word ? "1" : "0"},
                                  {"kept_ms", KeptMs(phrase.at_ms)}});
    });
}

bool BotMemory::ForgetPhrases(const std::string& lang, bool* any, std::string* err) {
    std::vector<std::string> from;
    for (const MemoryPhrase& p : impl_->phrases)
        if (p.lang == lang) from.push_back(p.from);
    *any = !from.empty();
    if (!*any) return true;
    return impl_->Write(err, [&] {
        for (const std::string& f : from) impl_->wax->ForgetFact(PhraseEntity(lang, f), "say");
    });
}

bool BotMemory::KeepSetting(const MemorySetting& setting, std::string* err) {
    if (setting.name.empty()) return *err = "memory: a setting needs its name", false;
    char value[32];
    std::snprintf(value, sizeof value, "%.3f", setting.value);
    return impl_->Write(err, [&] {
        impl_->wax->RememberFact(SettingEntity(setting.name), "value", value, {{"kind", "setting"}, {"kept_ms", KeptMs(setting.at_ms)}});
    });
}

bool BotMemory::ForgetSettings(bool* any, std::string* err) {
    std::vector<std::string> names;
    for (const MemorySetting& x : impl_->settings) names.push_back(x.name);
    *any = !names.empty();
    if (!*any) return true;
    return impl_->Write(err, [&] {
        for (const std::string& n : names) impl_->wax->ForgetFact(SettingEntity(n), "value");
    });
}

bool BotMemory::KeepSaying(const MemorySaying& saying, std::string* err) {
    if (saying.word.empty() || saying.say.empty()) return *err = "memory: a saying needs the word and how to say it", false;
    return impl_->Write(err, [&] {
        impl_->wax->RememberFact(SayEntity(saying.lang, saying.word), "say", saying.say, {{"kind", "say"}, {"kept_ms", KeptMs(saying.at_ms)}});
    });
}

bool BotMemory::ForgetSaying(const std::string& lang, const std::string& word, bool* any, std::string* err) {
    *any = false;
    for (const MemorySaying& s : impl_->sayings) *any = *any || (s.lang == lang && s.word == word);
    if (!*any) return true;
    return impl_->Write(err, [&] { impl_->wax->ForgetFact(SayEntity(lang, word), "say"); });
}

}  // namespace coop
