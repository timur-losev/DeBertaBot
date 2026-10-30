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
//   means     «когда я говорю бабах, это значит кидай гранату», "when I say boom, it means throw a grenade", «cuando digo
//             bum, significa lanza una granada»: a line of the player's own for what the bot already understands (2026-10-30,
//             the owner: the player teaches the bot everything; one kind of what is taught). The bot asks before it keeps it.
//   pronounce «в слове замок ударение на первый слог», «говори Buddy как Бадди», "pronounce Buddy as Baddy": how the bot's
//             voice says a word (the text on the screen stays as it is). The bot says it the new way and asks.
//   speech    «вместо «выдвигаюсь» говори «пошёл»», «не говори «брат»», «так не говори, говори «есть»», "say Y instead of X",
//             «no digas X, di Y»: the bot's own lines. The bot asks before it keeps it; «говори как раньше» forgets them all.
//   behaviour «держись в трёх метрах», «держись поближе», «открывай огонь с двадцати метров», «стреляй только по моей
//             команде» / «стреляй сам», «говори медленнее», "stay 3 meters from me", «mantente a 3 metros»: one of the bot's
//             settings the game lets the player change. The bot asks; «веди себя как раньше» forgets them all.
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

enum class TeachKind { None, Meant, NotThat, Name, Colour, Forget, Means, Pronounce, Speech, Behaviour };
// "none", "meant", "not_that", "name", "colour", "forget", "means", "pronounce", "speech", "behaviour"
const char* TeachKindName(TeachKind k);

struct TeachLine {
    TeachKind kind = TeachKind::None;
    // meant: the meaning as said (the line's own words after "I meant"); name: the name, normalized, articles and
    // possessives dropped; forget: what to forget, normalized, empty for the thing under the crosshair
    std::string rest;
    std::string colour;   // colour: the colour's id
    bool plain = false;   // name: a plain «это X» / "this is X": a name only when the bot reads no order in the line
    // colour: the colour is part of what the thing is said to be («это красный фонарь», "it's a red lantern", «es una
    // linterna roja»), not said of it («этот ящик зелёный», "this box is green", "it's green"); `noun` holds the other
    // words («фонарь»). coop_cli: a noun of another kind than the thing's makes the line a name, not a colour
    bool attributive = false;
    std::vector<std::string> noun;
    // means: the words the player will say (normalized), `rest` what they mean as said (its own words and stops). pronounce:
    // the word (normalized), `rest` how it sounds written (normalized) or empty with a stress: `stress` the syllable (1 the
    // first, -1 the last, -2 the one before it) or `vowel` the stressed vowel (its first time in the word); `forget`: as before
    std::string said;
    int stress = 0;
    std::string vowel;
    bool forget = false;
    // speech: `said` the bot's line as the player quotes it (normalized; empty: the line the bot said last), `rest` what to
    // say instead as said (empty: nothing), `forget`: every line as before. behaviour: `setting` (follow_m, engage_m,
    // fire_on_command, voice_speed; empty with `forget`: all as before) to `value`, or the current value times `scale`
    std::string setting;
    double value = 0, scale = 0;
};

// a number said in words or digits in ru / en / es («двух», «двадцать пять», "three", «tres», "2,5"), from words[i]; *next:
// the word after it. False: none there
bool ReadNumber(const std::vector<std::string>& words, size_t i, double* value, size_t* next);

// the word with its stress marked for the voice (U+0301 after the stressed vowel: «за́мок»), by syllable (1 first, -1 last,
// -2 the one before) or by the vowel's letter (its first time); empty: no such syllable or vowel (Russian vowels)
std::string StressedWord(const std::string& word, int syllable, const std::string& vowel);

// lang: "en", "ru" or "es" (coop_cli --language); a line the rules do not take is kind None
TeachLine ReadTeach(std::string_view heard, const std::string& lang);

// What a thing is, said right after the bot answered "what is that?" (coop_cli, 2026-10-30, the owner: «Нет, это красный
// фонарь» was read as "no" and the bot stopped): «нет, это красный фонарь», «это не стол, а верстак», «нет, он жёлтый»,
// "no, it's a lantern", "that's not a table, it's a workbench", «no, es una linterna roja». bare: the line may be the
// words alone («фонарь», "a lantern"), the answer to the bot's "Then what is it?"
struct ThingWords {
    bool ok = false;
    bool denied = false;              // it began with "no" / «нет»
    std::vector<std::string> words;   // what the thing is: normalized, articles and possessives dropped, 1 to 3 words
};
ThingWords ReadThingWords(std::string_view heard, bool bare);

// a line that only says the bot's answer was wrong: «нет», «не то», «неправильно», "no", "wrong", «no es eso»
bool BareDenial(std::string_view heard);

// a question about a thing's colour: «какого цвета этот стул?», «какой это цвет?», "what colour is it?", «¿de qué color
// es?». *rest: its other words, normalized (a name or a kind the question names: «верстак», "table")
bool ColourQuestion(std::string_view heard, std::vector<std::string>* rest);

// the answer to the bot's yes-or-no question: 1 yes («да», "sure", «claro»), -1 no («нет», "no", «не надо»), 0 neither
int YesNo(std::string_view heard);

// words that name no kind of thing: «штука», «вещь», "thing", "one", «cosa»
bool GenericThingWord(const std::string& word);

// a colour (ColourIds) as the bot says it of a thing. en: "yellow", "light blue"; ru: for a noun of gender 'm', 'f', 'n'
// or 'p' (plural), accusative or not («жёлтый», «жёлтую»); es: 'm' or 'f' («amarillo», «amarilla»). Empty: unknown
std::string ColourAdjective(const std::string& id, const std::string& lang, char gender, bool acc);

}  // namespace coop
