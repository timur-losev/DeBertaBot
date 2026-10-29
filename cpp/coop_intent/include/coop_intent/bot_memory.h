// The bot's long-term memory, one file per player: what the player taught it (teach.h), kept in a Wick store
// (github.com/timur-losev/Wick, the owner's C++20 port of Wax, Apache 2.0) -- structured facts with revisions, in an
// append-only file with a write-ahead log. No embeddings: every key is the player's own words, and a kept line matches
// a heard one by NearLine only (2026-10-29, memory_sim.py on the owner's 916 lines: looser matching harmed lines).
//
//   line    a heard line -> the English order lines it means. Entity "line|<lang>|<heard, normalized>", attribute
//           "means", the value the order lines one per row; metadata intent (the first line's, as the bot read it when it
//           was taught), source ("voice", "cmd"), doubts (the player cancelled what it gave right after).
//   name    a thing's name. Entity "name|<map>|<entity id>", attribute the language, the value the name, normalized.
//   colour  a thing's colour. Entity "colour|<map>|<entity id>", attribute "colour", the value a colour id (teach.h).
//
// The header is C++17 (coop_cli includes it); the store and Wick build as C++20 behind it. Every write is flushed to
// the file before the call returns.
#pragma once

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace coop {

struct MemoryLine {
    std::string lang, heard;          // heard: normalized (MemoryNorm)
    std::vector<std::string> lines;   // the English order lines it means
    std::string intent, source;
    int doubts = 0;
    int64_t at_ms = 0;                // when it was kept (the wall clock)
};

struct MemoryName {
    std::string map, entity, lang, name;   // name: normalized
    int64_t at_ms = 0;
};

struct MemoryColour {
    std::string map, entity, colour;
    int64_t at_ms = 0;
};

class BotMemory {
public:
    BotMemory();
    ~BotMemory();
    BotMemory(const BotMemory&) = delete;
    BotMemory& operator=(const BotMemory&) = delete;

    // opens the file, or makes it (and its folder) when there is none
    bool Open(const std::string& path, std::string* err);
    void Close();
    bool IsOpen() const;
    const std::string& Path() const;

    // a new pair, or a new meaning of a heard line kept before (the old one stays in the file's history)
    bool KeepLine(const MemoryLine& line, std::string* err);
    // the kept line a heard line (normalized) means: the same words first, then NearLine; nullptr: none
    const MemoryLine* LineFor(const std::string& lang, const std::string& heard) const;
    // one more doubt about a kept line; the second removes it (*removed)
    bool DoubtLine(const std::string& lang, const std::string& heard, bool* removed, std::string* err);
    // false with an empty *err: no such line
    bool ForgetLine(const std::string& lang, const std::string& heard, std::string* err);

    bool KeepName(const MemoryName& name, std::string* err);   // one name a language: a new one replaces it
    bool KeepColour(const MemoryColour& colour, std::string* err);
    // a thing's names and colour; *any: there was something to forget
    bool ForgetThing(const std::string& map, const std::string& entity, bool* any, std::string* err);

    const std::vector<MemoryLine>& Lines() const;
    const std::vector<MemoryName>& Names() const;
    const std::vector<MemoryColour>& Colours() const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace coop
