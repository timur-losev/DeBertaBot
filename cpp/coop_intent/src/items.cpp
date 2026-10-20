#include "coop_intent/items.h"

#include <algorithm>

namespace coop {

namespace {

// items.load_items: every word list the rules read
const char* const kLists[] = {"particle", "particle_after_rid", "recipient", "recipient_verbs", "determiner", "amount",
                              "not_kind", "stop", "dem_determiner", "anaphor", "generic", "generic_crop", "generic_feed",
                              "feed_not", "damage", "damage_link", "with_link"};

bool TokenWord(const std::string& w) {
    if (w.empty()) return false;
    for (unsigned char c : w)
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9'))) return false;
    return true;
}

bool Digits(const std::string& w) {   // Python str.isdigit() on a token
    return !w.empty() && std::all_of(w.begin(), w.end(), [](char c) { return c >= '0' && c <= '9'; });
}

std::string Join(const std::vector<std::string>& w, size_t from, size_t to) {   // words [from, to) joined by one space
    std::string s;
    for (size_t i = from; i < to; ++i) {
        if (i > from) s += ' ';
        s += w[i];
    }
    return s;
}

}  // namespace

bool ItemMatcher::Init(const ItemVocab& v, std::string* error) {
    ready_ = false;
    auto fail = [&](const std::string& msg) {
        if (error) *error = "items vocabulary refused: " + msg;
        return false;
    };
    vocab_ = v;
    verbs_.clear();
    lists_.clear();
    all_verbs_.clear();
    if (v.intents.empty()) return fail("no intents");
    if (v.max_words < 1) return fail("max_words must be at least 1");
    for (const auto& [intent, forms] : v.verbs) {
        if (std::find(v.intents.begin(), v.intents.end(), intent) == v.intents.end()) return fail("verbs of an intent without items: " + intent);
        for (const std::string& f : forms) {
            if (!TokenWord(f)) return fail("verb \"" + f + "\" must be one lowercase ASCII token");
            verbs_[intent].insert(f);
            all_verbs_.insert(f);
        }
    }
    for (const char* name : kLists) {
        auto it = v.lists.find(name);
        if (it == v.lists.end()) return fail(std::string("no word list ") + name);
        for (const std::string& w : it->second)
            if (!TokenWord(w)) return fail(std::string(name) + ": \"" + w + "\" must be one lowercase ASCII token");
        lists_[name] = std::unordered_set<std::string>(it->second.begin(), it->second.end());
    }
    keeps_ = std::unordered_set<std::string>(v.keeps_object.begin(), v.keeps_object.end());
    crop_ = std::unordered_set<std::string>(v.crop_intents.begin(), v.crop_intents.end());
    ready_ = true;
    return true;
}

bool ItemMatcher::In(const char* list, const std::string& w) const {
    auto it = lists_.find(list);
    return it != lists_.end() && it->second.count(w) != 0;
}

bool ItemMatcher::HasItem(const std::string& intent) const {
    return ready_ && std::find(vocab_.intents.begin(), vocab_.intents.end(), intent) != vocab_.intents.end();
}

bool ItemMatcher::KeepsObject(const std::string& intent) const { return keeps_.count(intent) != 0; }

// items._words: the tokens without fillers and without the recogniser's repeats
std::vector<ItemMatcher::Word> ItemMatcher::Words(std::string_view utf8, const LocationMatcher& places) const {
    std::vector<Word> out;
    for (PlaceToken& t : PlaceTokens(utf8)) {
        if (places.InList("filler", t.word)) continue;
        out.push_back({std::move(t.word), t.brk});
    }
    size_t k = 1;
    while (k < out.size()) {
        if (out[k].w == out[k - 1].w && !out[k].brk) {   // "fix fix the fans"
            out.erase(out.begin() + static_cast<std::ptrdiff_t>(k));
            continue;
        }
        if (k >= 3 && out[k - 1].w == out[k - 3].w && out[k].w == out[k - 2].w && !out[k - 1].brk && !out[k].brk) {   // "in the in the"
            out.erase(out.begin() + static_cast<std::ptrdiff_t>(k - 1), out.begin() + static_cast<std::ptrdiff_t>(k + 1));
            continue;
        }
        ++k;
    }
    return out;
}

// items._place_at
std::string ItemMatcher::PlaceAt(const std::vector<Word>& w, size_t i, const LocationMatcher& places, int* len) const {
    const size_t top = std::min(places.MaxPhraseLen(), w.size() - i);
    for (size_t n = top; n >= 1; --n) {
        bool broken = false;
        for (size_t j = 1; j < n; ++j)
            if (w[i + j].brk) broken = true;
        if (broken) continue;
        std::string joined;
        for (size_t j = 0; j < n; ++j) {
            if (j) joined += ' ';
            joined += w[i + j].w;
        }
        const char* kind = places.PhraseKind(joined);
        if (kind) {
            *len = static_cast<int>(n);
            return kind;
        }
    }
    return {};
}

// items._noun_next
bool ItemMatcher::NounNext(const std::vector<Word>& w, size_t i) const {
    const size_t j = i + 1;
    return j < w.size() && !w[j].brk && !In("stop", w[j].w) && !In("anaphor", w[j].w);
}

// items._phrase
bool ItemMatcher::PhraseAt(const std::vector<Word>& w, size_t i, const LocationMatcher& places, const std::string& intent, Phrase* out) const {
    const size_t n = w.size();
    while (i < n && (In("determiner", w[i].w) || In("amount", w[i].w) || Digits(w[i].w) || (In("dem_determiner", w[i].w) && NounNext(w, i)))) {
        if (i > 0 && w[i].brk == 2) return false;
        ++i;
    }
    if (i >= n) return false;
    if (w[i].brk == 2) return false;
    return PhraseBody(w, i, places, intent, out);
}

// items._phrase_body
bool ItemMatcher::PhraseBody(const std::vector<Word>& w, size_t i, const LocationMatcher& places, const std::string& intent, Phrase* out) const {
    const size_t n = w.size();
    Phrase ph;
    ph.first = static_cast<int>(i);
    const size_t max_words = static_cast<size_t>(vocab_.max_words);
    for (size_t j = i; j < n && ph.kept.size() < max_words;) {
        if (j > i && w[j].brk) break;
        const std::string& word = w[j].w;
        int len = 0;
        const std::string kind = PlaceAt(w, j, places, &len);
        if (kind == "zone" && ph.kept.empty() && KeepsObject(intent)) {   // "put a roof on it": the roof is built
            for (int t = 0; t < len; ++t) ph.kept.push_back(w[j + static_cast<size_t>(t)].w);
            ph.last = static_cast<int>(j) + len - 1;
            ph.obj = true;
            break;
        }
        if (kind == "zone" || kind == "zone_end" || kind == "ignore") break;
        if (kind == "object" || kind == "named") {
            for (int t = 0; t < len; ++t) ph.kept.push_back(w[j + static_cast<size_t>(t)].w);
            ph.last = static_cast<int>(j) + len - 1;
            ph.obj = true;
            break;
        }
        if (In("stop", word) || (Verb(word) && !ph.kept.empty())) break;
        if (In("determiner", word) || Digits(word) || In("amount", word)) break;
        ph.kept.push_back(word);
        ph.last = static_cast<int>(j);
        ++j;
    }
    if (ph.kept.empty()) return false;
    *out = std::move(ph);
    return true;
}

std::vector<std::string> ItemMatcher::Clean(const std::vector<std::string>& kept) const {
    std::vector<std::string> out;
    for (const std::string& x : kept)
        if (!In("not_kind", x)) out.push_back(x);
    return out;
}

// items._find_verb: the intent's own verbs first, then any intent's
int ItemMatcher::FindVerb(const std::vector<Word>& w, const std::string& intent) const {
    static const std::unordered_set<std::string> kNone;
    auto own_it = verbs_.find(intent);
    const std::unordered_set<std::string>& own = own_it == verbs_.end() ? kNone : own_it->second;
    for (const std::unordered_set<std::string>* list : {&own, &all_verbs_}) {
        for (size_t i = 0; i < w.size(); ++i) {
            if (list->count(w[i].w) && !(i > 0 && !w[i].brk && In("determiner", w[i - 1].w))) return static_cast<int>(i);
        }
    }
    return -1;
}

// items._after_verb
size_t ItemMatcher::AfterVerb(const std::vector<Word>& w, size_t v) const {
    size_t i = v + 1;
    while (i < w.size() && !w[i].brk && In("particle", w[i].w)) {
        ++i;
        if (w[i - 1].w == "rid" && i < w.size() && In("particle_after_rid", w[i].w)) ++i;
    }
    return i;
}

// items._object_len
size_t ItemMatcher::ObjectLen(const std::vector<std::string>& kept, const LocationMatcher& places) const {
    for (size_t n = std::min(places.MaxPhraseLen(), kept.size()); n >= 1; --n) {
        const char* kind = places.PhraseKind(Join(kept, kept.size() - n, kept.size()));
        if (kind && (std::string(kind) == "object" || std::string(kind) == "named")) return n;
    }
    return 0;
}

// items._object_item
bool ItemMatcher::ObjectItem(const Phrase& ph, const std::string& intent, const LocationMatcher& places, std::vector<std::string>* item) const {
    if (ph.obj) {
        if (KeepsObject(intent)) {
            *item = Clean(ph.kept);
            return !item->empty();
        }
        if (crop_.count(intent)) {   // "reap the corn field": the crop words before the field or bed
            const size_t n_obj = ObjectLen(ph.kept, places);
            *item = Clean(std::vector<std::string>(ph.kept.begin(), ph.kept.end() - static_cast<std::ptrdiff_t>(n_obj)));
            return !item->empty();
        }
        return false;
    }
    std::vector<std::string> words = Clean(ph.kept);
    if (words.empty()) return false;
    const std::string& head = words.back();
    if (In("generic", head) || (crop_.count(intent) && In("generic_crop", head)) || (intent == "FEED" && In("generic_feed", head))) return false;
    *item = std::move(words);
    return true;
}

// items._next_phrase_after: links is a word list by name, or (extra) a set of its own
bool ItemMatcher::NextPhraseAfter(const std::vector<Word>& w, size_t i, const char* links, const std::unordered_set<std::string>* extra,
                                  const LocationMatcher& places, size_t limit, Phrase* out) const {
    for (size_t j = i; j < std::min(w.size(), i + limit); ++j) {
        if (j > i && w[j].brk == 2) return false;
        if (extra ? extra->count(w[j].w) != 0 : In(links, w[j].w)) return PhraseAt(w, j + 1, places, std::string(), out);
    }
    return false;
}

// items._antecedent
bool ItemMatcher::Antecedent(const std::vector<Word>& w, size_t v, const LocationMatcher& places, Phrase* out) const {
    for (size_t u = v; u-- > 0;) {
        if (Verb(w[u].w) && !(u > 0 && In("determiner", w[u - 1].w))) {
            Phrase ph;
            if (PhraseAt(w, AfterVerb(w, u), places, std::string(), &ph)) {
                const std::vector<std::string> c = Clean(ph.kept);
                if (!c.empty() && !In("anaphor", c.back())) {
                    *out = std::move(ph);
                    return true;
                }
            }
        }
    }
    if (!w.empty() && In("determiner", w[0].w)) {
        Phrase ph;
        if (PhraseAt(w, 0, places, std::string(), &ph) && ph.last < static_cast<int>(v) && !Clean(ph.kept).empty()) {
            *out = std::move(ph);
            return true;
        }
    }
    return false;
}

// items.find
ItemFound ItemMatcher::Find(std::string_view utf8, const std::string& intent, const LocationMatcher& places) const {
    ItemFound res;
    if (!HasItem(intent)) return res;
    const std::vector<Word> w = Words(utf8, places);
    const int v = FindVerb(w, intent);
    if (v < 0) return res;
    res.verb = v;
    size_t i = AfterVerb(w, static_cast<size_t>(v));
    const std::string& vw = w[static_cast<size_t>(v)].w;
    if (i < w.size() && In("recipient", w[i].w) && !w[i].brk && In("recipient_verbs", vw) && NounNext(w, i))
        ++i;   // "bring me the wood"; not "bring em to me", where "em" is the thing
    Phrase ph;
    if (!PhraseAt(w, i, places, intent, &ph)) return res;
    std::vector<std::string> kept = Clean(ph.kept);
    std::string head = kept.empty() ? std::string() : kept.back();
    const bool has_head = !kept.empty();
    bool with_head = has_head;
    if (intent == "PLANT_CROP" && (!has_head || In("generic", head) || In("generic_crop", head) || ph.obj)) {
        Phrase w2;
        if (NextPhraseAfter(w, static_cast<size_t>(ph.last) + 1, "with_link", nullptr, places, 4, &w2)) {   // "sow it with wheat"
            ph = std::move(w2);
            kept = Clean(ph.kept);
            with_head = !kept.empty();
            head = with_head ? kept.back() : std::string();
        }
    }
    if (with_head && In("anaphor", head) && kept.size() == 1) {
        if (!Antecedent(w, static_cast<size_t>(v), places, &ph)) return res;
    } else if (with_head && intent == "FEED" && In("feed_not", head)) {
        static const std::unordered_set<std::string> kToFor = {"to", "for"};
        Phrase p2;
        if (!NextPhraseAfter(w, static_cast<size_t>(ph.last) + 1, nullptr, &kToFor, places, 6, &p2)) return res;
        ph = std::move(p2);
    } else if (with_head && intent == "REPAIR" && In("damage", head)) {
        Phrase p2;
        if (!NextPhraseAfter(w, static_cast<size_t>(ph.last) + 1, "damage_link", nullptr, places, 3, &p2)) return res;
        ph = std::move(p2);
    }
    std::vector<std::string> item;
    if (!ObjectItem(ph, intent, places, &item)) return res;
    res.has_item = true;
    res.item = Join(item, 0, item.size());
    res.first = ph.first;
    res.last = ph.last;
    return res;
}

}  // namespace coop
