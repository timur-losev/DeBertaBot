// The words a player teaches the bot with, and the text rules of its long-term memory (bot_memory.h). No model reads
// these lines: they are found by rule in the transcript as said, in the player's language (ru, en, es), before the
// router, the decoder and the classifier see it.
//
//   meant     "no, I meant follow me", «нет, я имел в виду вперёд», «quise decir sígueme»: the line said before this one
//             means what follows. The bot carries out the meaning now and keeps the pair.
//   not that  "not that", «не то», «eso no»: the bot asks what was meant; the next line is the meaning.
//   name      "call this the workbench", «назови это верстак», «это оружейка» with the crosshair on a thing: the thing's
//             name for this player. A plain «это X» / "this is X" counts only when the bot reads no order in it.
//   colour    "this box is green", «этот ящик зелёный», «es verde»: the colour of the thing under the crosshair.
//   forget    "forget the name" (the thing under the crosshair), "forget the workbench", «забудь банан»: a name or a
//             line the memory keeps. A bare "forget it" / «забудь» is "never mind", not this.
//
// Every rule reads the whole line: a line that only starts like one of these ("this is where we go") is an order.
#pragma once

#include <string>
#include <string_view>
#include <vector>

namespace coop {

// a line as the memory keys it: lower case (ASCII, Cyrillic, Latin-1), ё as е, everything but letters, digits and the
// apostrophe a space, one space between words
std::string MemoryNorm(std::string_view s);
std::vector<std::string> MemoryWords(std::string_view norm);
// the words of a line as said, each with where it is (bytes [begin, end) of the line) and its MemoryNorm form: a taught
// name found among them is replaced in the line itself, its punctuation and capitals kept
struct SpanWord {
    size_t begin = 0, end = 0;
    std::string norm;
};
std::vector<SpanWord> SpanWords(std::string_view line);

// the correction rule measured on the owner's lines (2026-10-29, memory_sim.py: 18 fixed, none harmed): the same words,
// or, both of 3+ words, one's words all in the other's with at most one word more. Both normalized
bool NearLine(const std::string& kept, const std::string& line);
// character trigrams of the two lines, |A & B| / |A | B| (memory_sim.py tri)
double TrigramJaccard(const std::string& a, const std::string& b);

// a word said in one of its forms: the same word, or (4+ letters) the taught word's stem -- the word without its last
// vowels, ь or й, at most two letters, 3+ left -- followed by at most three letters: «верстак» is said «верстаку»,
// «оружейка» «оружейку», "table" "tables". Fleeting vowels («угол», «угла») are not caught
bool WordForm(const std::string& said, const std::string& taught);

// where a taught name (its words) is said in a line (its words), word by word in that order; false: nowhere.
// *begin, *end: the span in the line's words
bool FindWords(const std::vector<std::string>& line, const std::vector<std::string>& name, size_t from, size_t* begin, size_t* end);

// the colours a player names, by id (red, blue, yellow, white, brown: the vocabulary's; green, black, grey, orange,
// purple, pink, light_blue: the memory's own) and their words in the three languages
const std::vector<std::string>& ColourIds();
// the colour ids the words of a line name, in line order, each once
std::vector<std::string> ColoursIn(const std::vector<std::string>& words);

enum class TeachKind { None, Meant, NotThat, Name, Colour, Forget };
const char* TeachKindName(TeachKind k);   // "none", "meant", "not_that", "name", "colour", "forget"

struct TeachLine {
    TeachKind kind = TeachKind::None;
    // meant: the meaning as said (the line's own words after "I meant"); name: the name, normalized, articles and
    // possessives dropped; forget: what to forget, normalized, empty for the thing under the crosshair
    std::string rest;
    std::string colour;   // colour: the colour's id
    bool plain = false;   // name: a plain «это X» / "this is X": a name only when the bot reads no order in the line
};

// lang: "en", "ru" or "es" (coop_cli --language); a line the rules do not take is kind None
TeachLine ReadTeach(std::string_view heard, const std::string& lang);

}  // namespace coop
