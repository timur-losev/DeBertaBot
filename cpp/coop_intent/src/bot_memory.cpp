// The bot's long-term memory on Wick's structured facts (bot_memory.h). Built as C++20 with Wick's core.
#include "coop_intent/bot_memory.h"

#include <filesystem>
#include <stdexcept>

#include "coop_intent/teach.h"
#include "waxcpp/memory_orchestrator.hpp"

namespace coop {

namespace {

constexpr char kSep = '|';

std::string LineEntity(const std::string& lang, const std::string& heard) { return "line|" + lang + kSep + heard; }
std::string NameEntity(const std::string& map, const std::string& entity) { return "name|" + map + kSep + entity; }
std::string ColourEntity(const std::string& map, const std::string& entity) { return "colour|" + map + kSep + entity; }

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
    std::vector<MemoryLine> lines;
    std::vector<MemoryName> names;
    std::vector<MemoryColour> colours;

    // the facts in force, read back after every write: a few hundred at most
    void Reload() {
        lines.clear();
        names.clear();
        colours.clear();
        for (const waxcpp::StructuredMemoryEntry& e : wax->RecallFactsByEntityPrefix("", -1)) {
            std::string a, b;
            if (Split(e.entity, "line", &a, &b) && e.attribute == "means") {
                MemoryLine l;
                l.lang = a;
                l.heard = b;
                l.lines = Rows(e.value);
                l.intent = Meta(e.metadata, "intent");
                l.source = Meta(e.metadata, "source");
                const std::string d = Meta(e.metadata, "doubts");
                l.doubts = d.empty() ? 0 : std::atoi(d.c_str());
                l.at_ms = e.timestamp_ms;
                lines.push_back(std::move(l));
            } else if (Split(e.entity, "name", &a, &b)) {
                names.push_back({a, b, e.attribute, e.value, e.timestamp_ms});
            } else if (Split(e.entity, "colour", &a, &b) && e.attribute == "colour") {
                colours.push_back({a, b, e.value, e.timestamp_ms});
            }
        }
    }

    template <class F>
    bool Write(std::string* err, F&& f) {
        if (!wax) return *err = "the memory is not open", false;
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

bool BotMemory::Open(const std::string& path, std::string* err) {
    Close();
    try {
        const std::filesystem::path p(std::u8string(path.begin(), path.end()));
        if (p.has_parent_path()) std::filesystem::create_directories(p.parent_path());
        waxcpp::OrchestratorConfig cfg;
        cfg.enable_vector_search = false;   // no embedder: the keys are words
        cfg.enable_text_search = true;
        cfg.enable_structured_memory = true;
        cfg.query_embedding_policy = waxcpp::QueryEmbeddingPolicy::kNever;
        cfg.rag.search_mode = {waxcpp::SearchModeKind::kTextOnly, 0.0f};
        cfg.require_on_device_providers = false;
        impl_->wax = std::make_unique<waxcpp::MemoryOrchestrator>(p, cfg);
        impl_->path = path;
        impl_->Reload();
        return true;
    } catch (const std::exception& e) {
        impl_->wax.reset();
        return *err = "memory " + path + ": " + e.what(), false;
    }
}

void BotMemory::Close() {
    if (!impl_->wax) return;
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

bool BotMemory::KeepLine(const MemoryLine& line, std::string* err) {
    if (line.heard.empty() || line.lines.empty()) return *err = "memory: a line to keep needs the heard words and a meaning", false;
    std::string value;
    for (const std::string& l : line.lines) value += (value.empty() ? "" : "\n") + l;
    return impl_->Write(err, [&] {
        impl_->wax->RememberFact(LineEntity(line.lang, line.heard), "means", value,
                                 {{"intent", line.intent}, {"source", line.source}, {"doubts", std::to_string(line.doubts)}});
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
    return impl_->Write(err, [&] { impl_->wax->RememberFact(NameEntity(name.map, name.entity), name.lang, name.name, {{"kind", "name"}}); });
}

bool BotMemory::KeepColour(const MemoryColour& colour, std::string* err) {
    if (colour.entity.empty() || colour.colour.empty()) return *err = "memory: a colour needs the thing and the colour", false;
    return impl_->Write(err, [&] {
        impl_->wax->RememberFact(ColourEntity(colour.map, colour.entity), "colour", colour.colour, {{"kind", "colour"}});
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

const std::vector<MemoryLine>& BotMemory::Lines() const { return impl_->lines; }
const std::vector<MemoryName>& BotMemory::Names() const { return impl_->names; }
const std::vector<MemoryColour>& BotMemory::Colours() const { return impl_->colours; }

}  // namespace coop
