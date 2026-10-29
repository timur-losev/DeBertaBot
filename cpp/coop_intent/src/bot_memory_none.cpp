// The long-term memory of a coop_cli built without Wick (bot_memory.h): it never opens, and the bot keeps nothing.
#include "coop_intent/bot_memory.h"

namespace coop {

struct BotMemory::Impl {
    std::string path;
    std::vector<MemoryLine> lines;
    std::vector<MemoryName> names;
    std::vector<MemoryColour> colours;
};

BotMemory::BotMemory() : impl_(std::make_unique<Impl>()) {}
BotMemory::~BotMemory() = default;

bool BotMemory::Open(const std::string& path, std::string* err) {
    return *err = "memory " + path + ": this coop_cli was built without Wick (cpp/coop_intent/README.md, \"The long-term memory\")", false;
}
void BotMemory::Close() {}
bool BotMemory::IsOpen() const { return false; }
const std::string& BotMemory::Path() const { return impl_->path; }
bool BotMemory::KeepLine(const MemoryLine&, std::string* err) { return *err = "no memory", false; }
const MemoryLine* BotMemory::LineFor(const std::string&, const std::string&) const { return nullptr; }
bool BotMemory::DoubtLine(const std::string&, const std::string&, bool* removed, std::string* err) {
    *removed = false;
    return *err = "no memory", false;
}
bool BotMemory::ForgetLine(const std::string&, const std::string&, std::string* err) { return *err = "no memory", false; }
bool BotMemory::KeepName(const MemoryName&, std::string* err) { return *err = "no memory", false; }
bool BotMemory::KeepColour(const MemoryColour&, std::string* err) { return *err = "no memory", false; }
bool BotMemory::ForgetThing(const std::string&, const std::string&, bool* any, std::string* err) {
    *any = false;
    return *err = "no memory", false;
}
const std::vector<MemoryLine>& BotMemory::Lines() const { return impl_->lines; }
const std::vector<MemoryName>& BotMemory::Names() const { return impl_->names; }
const std::vector<MemoryColour>& BotMemory::Colours() const { return impl_->colours; }

}  // namespace coop
