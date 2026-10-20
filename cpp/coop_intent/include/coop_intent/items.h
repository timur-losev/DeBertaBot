// What the order acts on: the item of the v60 bots' farmer's and builder's intents -- the C++ twin of
// scripts/coop/items.py (the rules and their reasons are documented there; this file follows it step by step and is
// checked against it line by line: coop_cli --item-tests).
//
// The classifier gives the intent (the verb); this gives the thing, as the player said it: "build a pillar" = "pillar",
// "carry the crate to the barn" = "crate", "give the cows some hay" = "cows". The planner (world.h) checks it against
// the catalogue the game sends and refuses what the game does not have. The word lists are data ("items" in
// intent_config.json, from scripts/coop/items_v60.json); a bot without them has no items.
#pragma once

#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "coop_intent/locations.h"

namespace coop {

// items_v60.json as data
struct ItemVocab {
    int version = 0;
    std::vector<std::string> intents;                                       // the intents that have an item
    std::unordered_map<std::string, std::vector<std::string>> verbs;        // intent -> the verb forms an order uses
    std::unordered_map<std::string, std::vector<std::string>> lists;        // every other word list, by its name
    std::vector<std::string> keeps_object;   // BUILD, COLLECT, DELIVER: a map object said is the item, not the place
    std::vector<std::string> crop_intents;   // PLANT_CROP, WATER, HARVEST
    int max_words = 3;
};

struct ItemFound {
    bool has_item = false;
    std::string item;   // the words as said, one space between them
    int first = -1, last = -1, verb = -1;   // word positions, after fillers and the recogniser's repeats are dropped
};

class ItemMatcher {
public:
    bool Init(const ItemVocab& vocab, std::string* error);   // refuses a malformed vocabulary
    bool Ready() const { return ready_; }
    ItemFound Find(std::string_view utf8, const std::string& intent, const LocationMatcher& places) const;
    bool HasItem(const std::string& intent) const;      // one of the intents with an item
    bool KeepsObject(const std::string& intent) const;  // BUILD, COLLECT, DELIVER
    const std::vector<std::string>& Intents() const { return vocab_.intents; }

private:
    struct Word {
        std::string w;
        int brk;   // the punctuation before the word: 0 none, 1 comma, 2 . ; : ! ?
    };
    struct Phrase {
        std::vector<std::string> kept;
        int first = -1, last = -1;
        bool obj = false;   // its last words are a map object
    };
    bool In(const char* list, const std::string& w) const;
    bool Verb(const std::string& w) const { return all_verbs_.count(w) != 0; }
    std::vector<Word> Words(std::string_view utf8, const LocationMatcher& places) const;
    // (kind, length) of the longest vocabulary phrase at word i; kind empty: none
    std::string PlaceAt(const std::vector<Word>& w, size_t i, const LocationMatcher& places, int* len) const;
    bool NounNext(const std::vector<Word>& w, size_t i) const;
    bool PhraseAt(const std::vector<Word>& w, size_t i, const LocationMatcher& places, const std::string& intent, Phrase* out) const;
    bool PhraseBody(const std::vector<Word>& w, size_t i, const LocationMatcher& places, const std::string& intent, Phrase* out) const;
    std::vector<std::string> Clean(const std::vector<std::string>& kept) const;
    int FindVerb(const std::vector<Word>& w, const std::string& intent) const;
    size_t AfterVerb(const std::vector<Word>& w, size_t v) const;
    bool ObjectItem(const Phrase& ph, const std::string& intent, const LocationMatcher& places, std::vector<std::string>* item) const;
    size_t ObjectLen(const std::vector<std::string>& kept, const LocationMatcher& places) const;
    bool NextPhraseAfter(const std::vector<Word>& w, size_t i, const char* links, const std::unordered_set<std::string>* extra,
                         const LocationMatcher& places, size_t limit, Phrase* out) const;
    bool Antecedent(const std::vector<Word>& w, size_t v, const LocationMatcher& places, Phrase* out) const;

    bool ready_ = false;
    ItemVocab vocab_;
    std::unordered_map<std::string, std::unordered_set<std::string>> verbs_, lists_;
    std::unordered_set<std::string> all_verbs_, keeps_, crop_;
};

}  // namespace coop
