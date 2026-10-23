// The bot's lines in the player's language (2026-10-23). Every line the bot says is written in English, by the brain
// (the chat's lines, the planner's questions) and by the game (callouts, refusals). A Russian or Spanish player hears
// it in their language: the line is cut into sentences, each sentence is matched to one English template of a reply
// table, and the template's translation is written with the words the template's slots took.
//
//   "Which window? The one on the right, 23 m?"
//     -> "Which {object}?" (object = window)          -> "{object.which} {object}?"                 -> "Какое окно?"
//     -> "The one {sector}, {n} m?" (sector, n = 23)  -> "{Sector}, в {n} {n:метре|метрах|метрах}?" -> "Справа, в 23 метрах?"
//
// A reply table (scripts/coop/replies/replies_<lang>.json, made from catalogue_en.json by TRANSLATE.md):
//   {"language": "ru",
//    "sentences": {"<English template>": "<translation>", ...},
//    "slots": {"<slot>": {"<English value>": {"text": "...", "<form>": "...", ...}, "_other": {...}}, ...}}
// In an English template {slot} matches one of the slot's English values (any case: {Phrase} starts a sentence), or,
// for an open slot (item, weapon), any words, which then take the slot's "_other" forms; {n} matches a number. In a
// translation {slot} writes the value's "text", {slot.form} its named form, a capital first letter ({Sector},
// {Sector.form}) makes the written word's first letter capital, {n} writes the number and {n:one|few|many} (or
// {n:one|other}) the word for it (Russian or Spanish plural rules).
#pragma once

#include <memory>
#include <string>
#include <vector>

namespace coop {

// a line cut after every . ! ? that a space follows ("I see no door. Where?" -> two)
std::vector<std::string> SplitSentences(const std::string& line);

class Localizer {
public:
    Localizer();
    ~Localizer();
    Localizer(const Localizer&) = delete;
    Localizer& operator=(const Localizer&) = delete;

    bool Load(const std::string& path, std::string* error);
    bool Loaded() const;
    const std::string& Language() const;
    size_t Templates() const;

    // the English line in the table's language. False when a sentence of it matches no template: out is left empty
    // and missing (if given) gets that sentence.
    bool Translate(const std::string& english, std::string* out, std::string* missing = nullptr) const;
    // one English template with every slot filled with its first value (and {n} with 23): what the coverage check
    // translates back (coop_cli --replies-check)
    std::vector<std::string> Examples() const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace coop
