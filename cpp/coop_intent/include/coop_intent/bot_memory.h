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

// how the bot's voice says a word in a language (2026-10-30): word normalized, say as the voice is given it («за́мок», «бадди»)
struct MemorySaying {
    std::string lang, word, say;
    int64_t at_ms = 0;
};

// a line of the bot's own the player asked it to say otherwise (2026-10-30): from, the sentence as the bot said it
// (normalized, without «брат»), to as the player said it; empty to: say nothing for it
struct MemoryPhrase {
    std::string lang, from, to;
    int64_t at_ms = 0;
    bool word = false;   // from is words inside the bot's sentences («брат», «метров»), not a whole sentence
};

// one of the bot's settings the player set by voice (2026-10-30): follow_m, engage_m, fire_on_command (0 / 1), voice_speed
struct MemorySetting {
    std::string name;
    double value = 0;
    int64_t at_ms = 0;
};

class BotMemory {
public:
    BotMemory();
    ~BotMemory();
    BotMemory(const BotMemory&) = delete;
    BotMemory& operator=(const BotMemory&) = delete;

    // opens the file, or makes it (and its folder) when there is none. A file the store cannot read (cut short, overwritten,
    // empty) is put aside as <file>.broken-<ms> and a new memory starts (PutAside); a file another process holds is an error
    // ("lease already held": that process is still ending)
    bool Open(const std::string& path, std::string* err);
    void Close();
    bool IsOpen() const;
    const std::string& Path() const;
    const std::string& PutAside() const;   // where the last Open put an unreadable file; empty: it did not

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
    // its name in one language only (its colour stays): «нет, это камень» about a rock named otherwise
    bool ForgetName(const std::string& map, const std::string& entity, const std::string& lang, bool* any, std::string* err);
    // how the voice says a word: a new one replaces the old; forgetting it says the word as the voice would (*any: there was one)
    bool KeepSaying(const MemorySaying& saying, std::string* err);
    bool ForgetSaying(const std::string& lang, const std::string& word, bool* any, std::string* err);
    // the bot's own lines said otherwise: a new one replaces the old; ForgetPhrases forgets every one of a language
    bool KeepPhrase(const MemoryPhrase& phrase, std::string* err);
    bool ForgetPhrases(const std::string& lang, bool* any, std::string* err);
    // the bot's settings: a new value replaces the old; ForgetSettings forgets them all
    bool KeepSetting(const MemorySetting& setting, std::string* err);
    bool ForgetSettings(bool* any, std::string* err);

    const std::vector<MemoryLine>& Lines() const;
    const std::vector<MemoryName>& Names() const;
    const std::vector<MemoryColour>& Colours() const;
    const std::vector<MemorySaying>& Sayings() const;
    const std::vector<MemoryPhrase>& Phrases() const;
    const std::vector<MemorySetting>& Settings() const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace coop
