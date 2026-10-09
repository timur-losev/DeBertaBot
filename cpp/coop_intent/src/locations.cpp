#include "coop_intent/locations.h"

#include <algorithm>
#include <deque>
#include <iterator>

namespace coop {
namespace {

constexpr int kRoleWindow = 5, kRoleReach = 12, kAnaphorMax = 6, kGovernMax = 4;
constexpr size_t kAfterMax = 4, kZoneAfterMax = 3, kMaxPhraseTokens = 4, kMaxTokens = 128;
// locations.py WORD_LISTS: a vocabulary must have exactly these, and with "directions" (rule set v4)
// the dir_* lists below as well; a rule set v3 vocabulary has none of those
const char* const kWordLists[] = {
    "before_fill", "after_fill", "tail", "zone_after_fill", "lone_follow", "lone_block", "lone_not_after",
    "unknown_modifier", "role_not", "role_from", "role_mine", "role_them", "number", "number_next", "status_next",
    "role_stop", "report_verb", "other", "determiner", "neutral_modifier", "role_them_soft", "soft_fill", "soft_lead",
    "number_fill", "motion_past", "role_from_of", "of_lead", "be", "not_ing", "role_from_after", "from_lead", "from_to",
    "ask", "number_lead", "status_not_next", "not_exempt", "not_unless_to", "govern", "aux", "order_verb",
    "from_particle", "filler", "anaphor", "let", "let_me", "negator", "fire", "no_words", "preposition", "post_prep",
    "post_modifier"};
const char* const kDirWordLists[] = {
    "dir_adjective", "dir_adjective_tail", "dir_lead_lateral", "dir_prep", "dir_det", "dir_article", "dir_side",
    "dir_right_block", "dir_count", "dir_unit", "dir_always", "dir_relation", "dir_lead_vertical", "dir_vertical_block",
    "dir_up_block", "dir_stairs_prep", "dir_stairs_link", "dir_zone_prep", "dir_place_next", "dir_lead_forward",
    "dir_lead_ahead", "dir_front_lead", "dir_lead_back", "dir_back_block", "dir_back_next", "dir_back_prep", "dir_person",
    "dir_behind_lead", "dir_end_next", "dir_six_lead", "dir_six_verb", "dir_lead_climb", "dir_there_lead",
    "dir_right_soft", "dir_turn", "dir_split_object", "dir_split_verb", "dir_resource", "dir_have", "dir_amount",
    "dir_right_noun", "dir_lead_noun", "dir_throw", "dir_correction", "dir_straight_not", "dir_we"};
// locations.py DIRECTIONS, in the order of PlaceDirection after None: the rules name the six
const char* const kDirections[] = {"up", "down", "left", "right", "forward", "back"};

struct Tok {
    std::string word;
    int brk;   // punctuation between the previous token and this one: 0 none, 1 comma, 2 . ; : ! ?
};

bool TokenByte(unsigned char c) { return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9'); }
unsigned char Lower(unsigned char c) { return c >= 'A' && c <= 'Z' ? static_cast<unsigned char>(c + 32) : c; }

std::vector<Tok> Tokenize(std::string_view s) {
    std::vector<Tok> out;
    int brk = 0;
    for (size_t i = 0; i < s.size();) {
        const unsigned char c = Lower(static_cast<unsigned char>(s[i]));
        if (TokenByte(c)) {
            std::string w;
            size_t j = i;
            for (; j < s.size(); ++j) {
                const unsigned char d = Lower(static_cast<unsigned char>(s[j]));
                if (!TokenByte(d)) break;
                w.push_back(static_cast<char>(d));
            }
            out.push_back({std::move(w), out.empty() ? 0 : brk});
            i = j;
            brk = 0;
        } else {
            if (c == '.' || c == ';' || c == ':' || c == '!' || c == '?')
                brk = 2;
            else if (c == ',' && brk < 2)
                brk = 1;
            ++i;
        }
    }
    return out;
}

// 1 to kMaxPhraseTokens lowercase ASCII tokens separated by single spaces
bool PhraseOk(const std::string& p) {
    if (p.empty() || p.front() == ' ' || p.back() == ' ') return false;
    size_t tokens = 1;
    for (size_t i = 0; i < p.size(); ++i) {
        if (p[i] == ' ') {
            if (p[i - 1] == ' ') return false;
            ++tokens;
        } else if (!TokenByte(static_cast<unsigned char>(p[i]))) {
            return false;
        }
    }
    return tokens <= kMaxPhraseTokens;
}

// Python str.isdigit() on a token: every byte an ASCII digit
bool Digits(const std::string& w) {
    return std::all_of(w.begin(), w.end(), [](char c) { return c >= '0' && c <= '9'; });
}

template <class V>
int IndexOf(const V& ids, const std::string& id) {
    auto it = std::find(ids.begin(), ids.end(), id);
    return it == ids.end() ? -1 : static_cast<int>(it - ids.begin());
}

struct Mention {
    int kind;        // LocationMatcher::Kind as int
    int a, b;
    int first, last;
};

// a target while it is being built
struct Work {
    PlaceTarget t;
    int first = 0, last = 0;        // token positions (among the tokens the matcher read)
    const Mention* obj = nullptr;   // the object mention it came from
    Work* twin = nullptr;           // "north and south doors": the target that owns the object
    Work* shares = nullptr;         // "doors and windows on ...": the next coordinated object
    bool is_twin = false, after = false, zone_set = false, zone_after = false;
    // rule set v4. The noun phrase, where it is wider than first..last (-1: it is not): "the back
    // stairs", "the basement stairs" start at np, "the stairs in the basement" end at np_last
    int np = -1, np_last = -1;
    // a direction that is a target of its own; corrects: "go left, no, right"; joined: it became a
    // place's direction and is no target any more
    bool lone = false, corrects = false, joined = false;
};

}  // namespace

const char* PlaceRoleName(PlaceRole r) {
    switch (r) {
        case PlaceRole::Not: return "not";
        case PlaceRole::From: return "from";
        case PlaceRole::Mine: return "mine";
        case PlaceRole::Them: return "them";
        case PlaceRole::Status: return "status";
        case PlaceRole::None: break;
    }
    return "";
}

const char* PlaceFlagName(PlaceFlag f) {
    switch (f) {
        case PlaceFlag::UnknownModifier: return "unknown_modifier";
        case PlaceFlag::Unsure: return "unsure";
        case PlaceFlag::Other: return "other";
        case PlaceFlag::None: break;
    }
    return "";
}

const char* PlaceDirectionName(PlaceDirection d) {
    switch (d) {
        case PlaceDirection::Up: return "up";
        case PlaceDirection::Down: return "down";
        case PlaceDirection::Left: return "left";
        case PlaceDirection::Right: return "right";
        case PlaceDirection::Forward: return "forward";
        case PlaceDirection::Back: return "back";
        case PlaceDirection::None: break;
    }
    return "";
}

bool LocationMatcher::In(const char* list, const std::string& word) const {
    auto it = lists_.find(list);
    return it != lists_.end() && it->second.count(word) != 0;
}

bool LocationMatcher::Init(const LocationVocab& v, std::string* error) {
    ready_ = false;
    auto fail = [&](std::string msg) {
        if (error) *error = "locations vocabulary refused: " + std::move(msg);
        return false;
    };
    objects_.clear();
    qualifiers_.clear();
    zones_.clear();
    phrases_.clear();
    lists_.clear();
    vertical_.clear();
    dirs_.clear();
    clock_.clear();
    max_len_ = 1;
    directions_ = v.has_directions;
    for (const auto& o : v.objects) {
        if (IndexOf(objects_, o.id) >= 0) return fail("duplicate object id " + o.id);
        if (o.words.empty()) return fail("object " + o.id + " has no words");
        objects_.push_back(o.id);
        vertical_.push_back(directions_ && o.vertical);
    }
    for (const auto& q : v.qualifiers) {
        if (IndexOf(qualifiers_, q.id) >= 0) return fail("duplicate qualifier id " + q.id);
        qualifiers_.push_back(q.id);
    }
    for (const auto& z : v.zones) {
        if (IndexOf(zones_, z.id) >= 0) return fail("duplicate zone id " + z.id);
        if (z.words.empty()) return fail("zone " + z.id + " has no words");
        zones_.push_back(z.id);
    }
    auto claim = [&](const std::string& phrase, Phrase p, const std::string& who) {
        if (!PhraseOk(phrase))
            return fail(who + ": phrase \"" + phrase + "\" must be 1-4 lowercase ASCII tokens separated by single spaces");
        if (!phrases_.emplace(phrase, p).second) return fail("phrase \"" + phrase + "\" is listed twice (second: " + who + ")");
        max_len_ = std::max(max_len_, static_cast<size_t>(std::count(phrase.begin(), phrase.end(), ' ')) + 1);
        return true;
    };
    allowed_.assign(objects_.size(), std::vector<bool>(qualifiers_.size(), false));
    for (size_t i = 0; i < v.objects.size(); ++i) {
        for (const auto& w : v.objects[i].words)
            if (!claim(w, {Kind::Object, static_cast<int>(i), -1}, "object " + v.objects[i].id)) return false;
        for (const auto& q : v.objects[i].qualifiers) {
            const int k = IndexOf(qualifiers_, q);
            if (k < 0) return fail("object " + v.objects[i].id + " allows unknown qualifier " + q);
            allowed_[i][static_cast<size_t>(k)] = true;
        }
    }
    lone_.assign(qualifiers_.size(), -1);
    for (size_t k = 0; k < v.qualifiers.size(); ++k) {
        const auto& q = v.qualifiers[k];
        for (const auto& w : q.words)
            if (!claim(w, {Kind::Qualifier, static_cast<int>(k), -1}, "qualifier " + q.id)) return false;
        bool any = false;
        for (size_t i = 0; i < objects_.size(); ++i) any = any || allowed_[i][k];
        if (!any) return fail("qualifier " + q.id + " is allowed by no object");
        if (!q.lone.empty()) {
            const int o = IndexOf(objects_, q.lone);
            if (o < 0 || !allowed_[static_cast<size_t>(o)][k]) return fail("qualifier " + q.id + ": lone object " + q.lone + " does not allow it");
            lone_[k] = o;
        }
    }
    for (const auto& t : v.named) {
        const int o = IndexOf(objects_, t.object), q = IndexOf(qualifiers_, t.qualifier);
        if (o < 0 || q < 0 || !allowed_[static_cast<size_t>(o)][static_cast<size_t>(q)])
            return fail("named \"" + t.phrase + "\": " + t.object + " does not allow " + t.qualifier);
        if (!claim(t.phrase, {Kind::Named, o, q}, "named")) return false;
    }
    for (size_t i = 0; i < v.zones.size(); ++i) {
        for (const auto& w : v.zones[i].words)
            if (!claim(w, {Kind::Zone, static_cast<int>(i), -1}, "zone " + v.zones[i].id)) return false;
        for (const auto& w : v.zones[i].words_end)
            if (!claim(w, {Kind::ZoneEnd, static_cast<int>(i), -1}, "zone " + v.zones[i].id + " (words_end)")) return false;
    }
    for (const auto& p : v.ignore)
        if (!claim(p, {Kind::Ignore, -1, -1}, "ignore")) return false;
    auto one_token = [](const std::string& w) { return PhraseOk(w) && w.find(' ') == std::string::npos; };
    auto word_list = [&](const char* name) {
        auto it = v.words.find(name);
        if (it == v.words.end()) return fail(std::string("missing word list ") + name);
        for (const auto& w : it->second)
            if (!one_token(w)) return fail(std::string("word list ") + name + ": \"" + w + "\" must be one lowercase ASCII token");
        lists_[name] = std::unordered_set<std::string>(it->second.begin(), it->second.end());
        return true;
    };
    for (const char* name : kWordLists)
        if (!word_list(name)) return false;
    if (directions_)
        for (const char* name : kDirWordLists)
            if (!word_list(name)) return false;
    // a list no rule reads: locations.py refuses the vocabulary too (in a rule set v3 one, any dir_* list)
    for (const auto& list : v.words)
        if (lists_.count(list.first) == 0) return fail("unknown word list " + list.first);
    if (directions_) {
        // rule set v4: exactly the six directions the rules name, each with its words and the hours that
        // mean it ("clock" may be empty). A direction word is one token, not a phrase of the vocabulary
        // and not a filler word (it would never be read); no word or hour belongs to two directions
        bool have[std::size(kDirections)] = {};
        for (const auto& d : v.directions) {
            size_t k = 0;
            while (k < std::size(kDirections) && d.id != kDirections[k]) ++k;
            if (k == std::size(kDirections) || have[k])
                return fail("directions must be exactly up, down, left, right, forward, back: \"" + d.id + "\"");
            have[k] = true;
            if (d.words.empty()) return fail("direction " + d.id + " has no words");
            for (const bool hours : {false, true}) {
                auto& of = hours ? clock_ : dirs_;
                for (const auto& w : hours ? d.clock : d.words) {
                    if (!one_token(w)) return fail("direction " + d.id + ": \"" + w + "\" must be one lowercase ASCII token");
                    if (!hours && phrases_.count(w) != 0) return fail("direction word \"" + w + "\" is also a phrase of the vocabulary");
                    if (In("filler", w)) return fail("direction word \"" + w + "\" is a filler word: it would never be read");
                    if (!of.emplace(w, static_cast<PlaceDirection>(k + 1)).second)
                        return fail("direction word \"" + w + "\" is listed twice (second: " + d.id + ")");
                }
            }
        }
        if (v.directions.size() != std::size(kDirections))
            return fail("directions must be exactly up, down, left, right, forward, back");
        for (const auto& w : lists_["dir_adjective"])   // "the left window": the object's direction is the word's
            if (dirs_.count(w) == 0) return fail("dir_adjective word \"" + w + "\" is not a direction word");
    }
    ready_ = true;
    return true;
}

// locations.py find(), step by step; the rules and their reasons are documented there
PlaceRecord LocationMatcher::Find(std::string_view utf8) const {
    PlaceRecord rec;
    if (!ready_) return rec;
    std::vector<Tok> toks;
    {
        int carry = 0;   // "hold the north uh door": the recogniser's fillers are not words of the line
        for (Tok& t : Tokenize(utf8)) {
            if (In("filler", t.word)) {
                carry = std::max(carry, t.brk);
                continue;
            }
            t.brk = toks.empty() ? 0 : std::max(carry, t.brk);
            toks.push_back(std::move(t));
            carry = 0;
        }
        if (toks.size() > kMaxTokens) toks.erase(toks.begin(), toks.end() - static_cast<std::ptrdiff_t>(kMaxTokens));
        if (!toks.empty()) toks.front().brk = 0;   // the last ones: an order ends a ramble
    }
    const int n = static_cast<int>(toks.size());
    auto word = [&](int j) -> const std::string& { return toks[static_cast<size_t>(j)].word; };
    auto tbrk = [&](int j) { return toks[static_cast<size_t>(j)].brk; };
    auto ends_phrase = [&](int j) { return j >= n || tbrk(j) != 0 || In("lone_follow", word(j)); };

    // mentions: the longest vocabulary phrase at each token; a phrase does not run across punctuation
    std::vector<Mention> mentions;
    for (int i = 0; i < n;) {
        bool hit = false;
        for (int k = std::min(static_cast<int>(max_len_), n - i); k > 0 && !hit; --k) {
            std::string key = word(i);
            bool broken = false;
            for (int j = i + 1; j < i + k; ++j) {
                key += ' ';
                key += word(j);
                broken = broken || tbrk(j) != 0;
            }
            auto it = phrases_.find(key);
            if (it == phrases_.end() || broken) continue;
            Kind kind = it->second.kind;
            if (kind == Kind::ZoneEnd) {   // "on second": a floor only where it ends its phrase
                if (!ends_phrase(i + k)) continue;
                kind = Kind::Zone;
            }
            if (kind != Kind::Ignore) mentions.push_back({static_cast<int>(kind), it->second.a, it->second.b, i, i + k - 1});
            i += k;
            hit = true;
        }
        if (!hit) ++i;
    }
    const int kObject = static_cast<int>(Kind::Object), kQualifier = static_cast<int>(Kind::Qualifier),
              kNamed = static_cast<int>(Kind::Named), kZone = static_cast<int>(Kind::Zone);
    std::vector<int> kind_at(static_cast<size_t>(n), -1);
    for (const Mention& m : mentions)
        for (int j = m.first; j <= m.last; ++j) kind_at[static_cast<size_t>(j)] = m.kind;
    auto kind = [&](int j) { return kind_at[static_cast<size_t>(j)]; };

    auto brk = [&](int a, int b) {   // the strongest punctuation between token a and token b (a < b)
        int x = 0;
        for (int j = a + 1; j <= b; ++j) x = std::max(x, tbrk(j));
        return x;
    };
    // the tokens strictly between a and b (optionally without zone mentions): how many, and whether all are in a list
    auto gap = [&](int a, int b, bool skip_zones, const char* list, size_t* count) {
        bool all = true;
        *count = 0;
        for (int j = a + 1; j < b; ++j) {
            if (skip_zones && kind(j) == kZone) continue;
            ++*count;
            all = all && (list == nullptr || In(list, word(j)));
        }
        return all;
    };
    auto and_or = [&](int a, int b) { return b - a == 2 && (word(a + 1) == "and" || word(a + 1) == "or"); };

    std::vector<const Mention*> objects, quals, zones;
    for (const Mention& m : mentions) {
        if (m.kind == kObject || m.kind == kNamed) objects.push_back(&m);
        if (m.kind == kQualifier) quals.push_back(&m);
        if (m.kind == kZone) zones.push_back(&m);
    }
    std::deque<Work> store;
    std::vector<Work*> targets;
    auto add = [&](int object, int qualifier, int first, int last, const Mention* obj) {
        store.emplace_back();
        Work* w = &store.back();
        w->t.object = object;
        w->t.qualifier = qualifier;
        w->first = first;
        w->last = last;
        w->obj = obj;
        targets.push_back(w);
        return w;
    };
    std::vector<Work*> by_obj;
    for (const Mention* o : objects) by_obj.push_back(add(o->a, o->kind == kNamed ? o->b : -1, o->first, o->last, o));
    std::vector<char> free_q(quals.size(), 1);
    auto allows = [&](int object, int qualifier) { return allowed_[static_cast<size_t>(object)][static_cast<size_t>(qualifier)]; };
    size_t cnt = 0;

    // 1. the qualifier right before its object
    for (size_t oi = 0; oi < objects.size(); ++oi) {
        Work* t = by_obj[oi];
        const Mention* o = objects[oi];
        if (t->t.qualifier >= 0) continue;
        int best = -1;
        for (size_t k = 0; k < quals.size(); ++k) {
            const Mention* q = quals[k];
            if (!free_q[k] || q->last >= o->first) continue;
            if (gap(q->last, o->first, false, "before_fill", &cnt) && cnt <= 1 && !brk(q->last, o->first))
                if (best < 0 || q->last > quals[static_cast<size_t>(best)]->last) best = static_cast<int>(k);
        }
        if (best < 0) continue;
        const Mention* q = quals[static_cast<size_t>(best)];
        free_q[static_cast<size_t>(best)] = 0;
        if (!allows(t->t.object, q->a)) {   // "blue door": not a place on these maps
            t->t.flag = PlaceFlag::UnknownModifier;
            t->first = q->first;
            continue;
        }
        t->t.qualifier = q->a;
        t->first = q->first;
        // 1b. "north and south doors" (two targets) / "north west door" (not a place)
        for (size_t k2 = 0; k2 < quals.size(); ++k2) {
            const Mention* q1 = quals[k2];
            if (!free_q[k2] || q1->last >= q->first || !allows(t->t.object, q1->a)) continue;
            const bool empty = q->first - q1->last == 1;
            if (and_or(q1->last, q->first) || (empty && brk(q1->last, q->first) == 1)) {
                free_q[k2] = 0;
                Work* tw = add(t->t.object, q1->a, q1->first, q1->last, o);
                tw->twin = t;
                tw->is_twin = true;
            } else if (empty && !brk(q1->last, q->first)) {
                free_q[k2] = 0;
                t->t.flag = PlaceFlag::UnknownModifier;
                t->first = q1->first;
            }
        }
    }
    // 1c. a modifier word the vocabulary does not have, right before the object: "back door"
    // tokens already read as a direction or as an object's modifier (rule set v4)
    std::vector<char> dir_used(static_cast<size_t>(n), 0);
    auto dir_of = [&](int j) { return dirs_.find(word(j))->second; };   // of a dir_adjective word: Init checked it is one
    for (Work* t : targets) {
        const int f = t->first;
        if (t->is_twin || f == 0 || !In("unknown_modifier", word(f - 1)) || tbrk(f) || kind(f - 1) >= 0) continue;
        int a = f - 1;
        // "the left hand door", "the right side window"
        if (In("dir_adjective_tail", word(a)) && a > 0 && !tbrk(a) && In("dir_adjective", word(a - 1))) --a;
        if (In("dir_adjective", word(a))) {
            if (a >= 2 && !tbrk(a) && !tbrk(a - 1) && (word(a - 1) == "and" || word(a - 1) == "or") &&
                In("dir_adjective", word(a - 2)) && kind(a - 2) < 0)
                a -= 2;                       // "the left and right windows": the first one named
            t->t.direction = dir_of(a);       // "the left window": a direction, not an unknown name
            for (int j = a; j < f; ++j) dir_used[static_cast<size_t>(j)] = 1;
        } else {
            t->t.flag = PlaceFlag::UnknownModifier;
        }
        t->np = a;   // where the object's noun phrase starts (step 6)
    }
    // 1d. "the spiral staircase": one unknown word between a determiner and an unqualified object
    for (Work* t : targets) {
        const int f = t->first;
        if (t->is_twin || t->t.flag != PlaceFlag::None || t->t.direction != PlaceDirection::None || t->t.qualifier >= 0 || f < 2)
            continue;
        const std::string& w = word(f - 1);
        if (In("determiner", word(f - 2)) && !tbrk(f - 1) && !tbrk(f) && kind(f - 1) < 0 && !In("neutral_modifier", w) &&
            !In("determiner", w) && !In("preposition", w) && !In("number", w) && !In("order_verb", w)) {
            t->t.flag = PlaceFlag::UnknownModifier;
            t->np = f - 1;
        }
    }
    // 1e. "take the other door": the object right after an `other` word is the other one of its kind
    for (Work* t : targets) {
        const int f = t->first;
        if (!t->is_twin && t->t.flag == PlaceFlag::None && t->t.qualifier < 0 && f > 0 && !tbrk(f) && In("other", word(f - 1))) {
            t->t.flag = PlaceFlag::Other;
            t->np = f - 1;
        }
    }

    // 2. a free qualifier after an object
    for (size_t k = 0; k < quals.size(); ++k) {
        if (!free_q[k]) continue;
        const Mention* q = quals[k];
        int oi = -1;
        for (size_t i = 0; i < objects.size(); ++i)
            if (objects[i]->last < q->first) oi = static_cast<int>(i);
        if (oi < 0) continue;
        const Mention* o = objects[static_cast<size_t>(oi)];
        Work* t = by_obj[static_cast<size_t>(oi)];
        const int nxt = q->last + 1;
        // "the door to the main hall": the name belongs to that phrase
        if (nxt < n && !tbrk(nxt) && (In("lone_block", word(nxt)) || kind(nxt) == kZone)) continue;
        const bool tail = nxt < n && In("tail", word(nxt)) && !tbrk(nxt);
        const int b = brk(o->last, q->first);
        bool qual_between = false;
        for (int j = o->last + 1; j < q->first; ++j) qual_between = qual_between || kind(j) == kQualifier;
        if (allows(t->t.object, q->a) && gap(o->last, q->first, true, "after_fill", &cnt) && cnt <= kAfterMax &&
            (b == 0 || (b == 1 && tail)) && !qual_between) {
            free_q[k] = 0;
            const int last = q->last + (tail ? 1 : 0);
            if (t->t.qualifier < 0) {
                t->t.qualifier = q->a;
                t->last = last;
                t->after = true;
            } else {   // "not the north door, the south one": a second door
                add(t->t.object, q->a, q->first, last, o);
            }
        }
    }
    // 2b. "doors and windows on the north side": coordinated objects share the qualifier after them
    for (size_t i = 0; i + 1 < objects.size(); ++i) {
        Work *ta = by_obj[i], *tb = by_obj[i + 1];
        if (and_or(objects[i]->last, objects[i + 1]->first) && ta->t.flag == PlaceFlag::None &&
            ta->t.direction == PlaceDirection::None) {
            ta->shares = tb;
            if (ta->t.qualifier < 0 && tb->after && tb->t.qualifier >= 0 && allows(ta->t.object, tb->t.qualifier))
                ta->t.qualifier = tb->t.qualifier;
        }
    }
    // 2c. "the door on the left", "the stairs at the back": a modifier after an unqualified object
    for (size_t oi = 0; oi < objects.size(); ++oi) {
        Work* t = by_obj[oi];
        int e = objects[oi]->last + 1;
        if (t->t.flag != PlaceFlag::None || t->t.qualifier >= 0 || e >= n || tbrk(e) || !In("post_prep", word(e))) continue;
        ++e;
        if (e < n && !tbrk(e) && In("determiner", word(e))) ++e;
        if (e >= n || tbrk(e) || !In("post_modifier", word(e)) || kind(e) >= 0) continue;
        // "the door in front ...": step 6. Only under rule set v4: without directions step 6 never reads
        // the word, and the door keeps the flag rule set v3 gives it here
        if (directions_ && word(e) == "front" && word(e - 1) == "in") continue;
        if (In("dir_adjective", word(e)) && t->t.direction == PlaceDirection::None)
            t->t.direction = dir_of(e);   // "the door on the left"
        else
            t->t.flag = PlaceFlag::UnknownModifier;
        dir_used[static_cast<size_t>(e)] = 1;   // "the stairs at the back": the word is this object's, not a direction of its own
    }

    // 3. lone qualifiers: a place only where the word ends its phrase
    for (size_t k = 0; k < quals.size(); ++k) {
        if (!free_q[k]) continue;
        const Mention* q = quals[k];
        if (q->first > 0 && !tbrk(q->first) && In("lone_not_after", word(q->first - 1))) continue;   // "i'm red"
        const int nxt = q->last + 1;
        PlaceFlag flag = PlaceFlag::None;
        if (!ends_phrase(nxt)) {
            const std::string& x = word(nxt);
            if (In("lone_block", x) || kind(nxt) == kZone) continue;   // "yellow ping", "main hall"
            // a word that starts the next clause ends the phrase too: "take blue ill take red"
            if (!(In("role_mine", x) || In("role_not", x) || In("role_them", x) || In("govern", x) || In("determiner", x) ||
                  In("number", x) || In("order_verb", x)))
                flag = PlaceFlag::Unsure;
        }
        int obj = lone_[static_cast<size_t>(q->a)];
        // "you take the south one", "you watch the west": the kind of the object named before
        int pi = -1;
        for (size_t i = 0; i < objects.size(); ++i)
            if (objects[i]->last < q->first && allows(by_obj[i]->t.object, q->a)) pi = static_cast<int>(i);
        if (pi >= 0) {
            const Work* pt = by_obj[static_cast<size_t>(pi)];
            const bool one = nxt < n && !tbrk(nxt) && In("anaphor", word(nxt));
            const bool bare = obj < 0 && flag == PlaceFlag::None && ends_phrase(nxt) && q->first > 0 &&
                              In("determiner", word(q->first - 1)) && !tbrk(q->first) && pt->t.qualifier >= 0 &&
                              pt->t.qualifier != q->a && q->first - objects[static_cast<size_t>(pi)]->last <= kAnaphorMax;
            if (one || bare) obj = pt->t.object;
        }
        const int last = q->last + (nxt < n && In("tail", word(nxt)) && !tbrk(nxt) ? 1 : 0);
        Work* t = add(obj, q->a, q->first, last, nullptr);
        t->t.flag = flag;
        t->t.inferred = obj >= 0;
    }
    auto by_first = [](const Work* a, const Work* b) { return a->first < b->first; };
    std::stable_sort(targets.begin(), targets.end(), by_first);

    // 4. zones: a zone belongs to a target only inside its noun phrase; otherwise it is a target itself
    std::vector<char> placed(zones.size(), 0);
    for (size_t zi = 0; zi < zones.size(); ++zi) {
        const Mention* z = zones[zi];
        Work* best = nullptr;
        for (Work* t : targets) {
            if (t->zone_set) continue;
            if (z->last < t->first) {
                // "basement door"; across a comma only as shorthand: "first floor, north window"
                gap(z->last, t->first, false, nullptr, &cnt);
                const int b = brk(z->last, t->first);
                const bool item = b == 1 && tbrk(z->last + 1) == 1 && (z->first == 0 || tbrk(z->first) != 0) &&
                                  (cnt == 0 || (cnt == 1 && In("determiner", word(z->last + 1))));
                if (((cnt == 0 && b == 0) || item) && !best) best = t;
            } else if (z->first > t->last || (t->obj && t->obj->last < z->first && z->first <= t->last)) {
                const int a = t->obj && z->first <= t->last ? t->obj->last : t->last;
                bool other_between = false;
                for (const Work* u : targets) other_between = other_between || (u != t && a < u->first && u->first < z->first);
                const bool fill = gap(a, z->first, false, "zone_after_fill", &cnt);
                const int b = brk(a, z->first);
                // across a comma only as shorthand, the zone an item of its own: "red stairs, top floor, ..."
                const bool item = b == 1 && cnt == 0 && (z->last + 1 >= n || tbrk(z->last + 1) != 0);
                if (fill && cnt <= kZoneAfterMax && (b == 0 || item) && !other_between) {
                    best = t;
                    t->zone_after = true;
                }
            }
        }
        if (best) {
            best->t.zone = z->a;
            best->zone_set = true;
            if (z->last < best->first)
                best->np = std::min(best->np >= 0 ? best->np : best->first, z->first);   // "the basement stairs"
            else if (z->first > best->last)
                best->np_last = z->last;                                                 // "the stairs in the basement"
            placed[zi] = 1;
        }
    }
    for (Work* t : targets) {
        if (t->shares && t->t.zone < 0 && t->shares->zone_after) t->t.zone = t->shares->t.zone;
        if (t->twin && t->t.zone < 0) t->t.zone = t->twin->t.zone;
    }
    for (size_t zi = 0; zi < zones.size(); ++zi)
        if (!placed[zi]) add(-1, -1, zones[zi]->first, zones[zi]->last, nullptr)->t.zone = zones[zi]->a;
    std::stable_sort(targets.begin(), targets.end(), by_first);

    // 5. roles: whose place it is
    std::vector<char> owned_at(static_cast<size_t>(n) + 1, 0);
    for (const Work* t : targets)
        for (int j = t->first; j <= t->last; ++j) owned_at[static_cast<size_t>(j)] = 1;
    auto owned = [&](int j) { return owned_at[static_cast<size_t>(j)] != 0; };
    auto let_me = [&](int k) { return In("let_me", word(k)) && k > 0 && !tbrk(k) && In("let", word(k - 1)); };
    // the subject or negator right before the order verb at j (auxiliaries between), or -1
    auto governor = [&](int j) {
        int k = j - 1;
        for (int i = 0; i <= kGovernMax; ++i) {
            if (k < 0 || tbrk(k + 1)) return -1;
            if (In("role_not", word(k)) || In("role_mine", word(k)) || In("govern", word(k)) || let_me(k)) return k;
            if (!In("aux", word(k))) return -1;
            --k;
        }
        return -1;
    };
    auto ing = [&](int j) {   // "camping", "sitting": a progressive form, by its ending
        if (j >= n) return false;
        const std::string& w = word(j);
        return w.size() > 4 && w.compare(w.size() - 3, 3, "ing") == 0 && !In("not_ing", w);
    };
    auto after = [&](int j, const char* fill) {   // the token after j and at most two filler words
        int k = j + 1;
        for (int i = 0; i < 2; ++i)
            if (k < n && !tbrk(k) && In(fill, word(k))) ++k;
        return k;
    };
    auto acts = [&](int k) {   // what an enemy does there: "is", "sitting", "went"
        return k < n && !tbrk(k) && (In("be", word(k)) || ing(k) || In("motion_past", word(k)));
    };
    // token j starts a callout: line or clause start, after a lead word or after another place
    auto starts = [&](int j, bool soft) {
        return j == 0 || tbrk(j) != 0 || In("number_lead", word(j - 1)) || owned(j - 1) ||
               (soft && (In("soft_lead", word(j - 1)) || In("number", word(j - 1))));
    };
    auto leads_to = [&](const Work* t) {   // "from blue to red", "from the roof rappel down to the east window"
        int e = t->last + 1;
        for (const char* skip : {"order_verb", "from_particle"})
            if (e < n && !tbrk(e) && In(skip, word(e)) && kind(e) < 0) ++e;
        if (e >= n || tbrk(e) || !In("from_to", word(e))) return false;
        ++e;
        if (e < n && !tbrk(e) && In("determiner", word(e))) ++e;
        return e < n && !tbrk(e) && kind(e) >= 0;
    };
    auto negated = [&](int j) {   // a negator right before token j: "dont leave", "don't move from"
        const int k = j >= 2 && word(j - 1) == "t" ? j - 2 : j - 1;
        return k >= 0 && !tbrk(j) && In("negator", word(k));
    };
    auto next_to = [&](int j, const Work* t) {   // only determiners and neutral words between token j and the place
        for (int x = j + 1; x < t->first; ++x)
            if (!In("determiner", word(x)) && !In("neutral_modifier", word(x))) return false;
        return true;
    };

    // the role of group[ti]; the group is the targets in line order (in step 6: with the directions)
    auto assign_role = [&](size_t ti, Work* t, const std::vector<Work*>& group) {
        // "they're on red and blue": a place joined to the one before it by and / or shares its role
        if (ti > 0) {
            const Work* u = group[ti - 1];
            if (u->t.role == PlaceRole::Mine || u->t.role == PlaceRole::Them || u->t.role == PlaceRole::Not) {
                bool joined = false, only = true;
                int count = 0;
                for (int x = u->last + 1; x < t->first; ++x) {
                    const bool ao = word(x) == "and" || word(x) == "or";
                    ++count;
                    joined = joined || ao;
                    only = only && (ao || In("determiner", word(x)));
                }
                if (count > 0 && brk(u->last, t->first) < 2 && joined && only) {
                    t->t.role = u->t.role;
                    return;
                }
            }
        }
        int j = t->first - 1, steps = 0;
        while (j >= 0 && steps < kRoleWindow && t->first - j <= kRoleReach) {
            if (tbrk(j + 1) || In("role_stop", word(j)) || owned(j)) break;
            const std::string* w = &word(j);
            bool soft = false;
            if (In("role_them_soft", *w)) {   // "stack is sitting on ...", "guy on ..."; not "stack up on the north door"
                const int k = after(j, "soft_fill");
                soft = k < t->first && (acts(k) || (In("number_next", word(k)) && !In("order_verb", *w) && starts(j, true)));
            }
            // an order verb starts the bot's own order, unless it is a noun here ("a smoke", "the drone")
            if (In("order_verb", *w) && !soft && !(j > 0 && !tbrk(j) && In("determiner", word(j - 1)))) {
                j = governor(j);
                if (j < 0) break;   // "im planting watch the white stairs": the bot's own order starts here
                w = &word(j);       // "i'm going to breach the north door": straight to the subject
            }
            if (In("role_not", *w)) {
                const int k = word(j + 1) == "t" ? j + 2 : j + 1;   // "don't" is two tokens
                if ((In("not_unless_to", *w) && word(j + 1) == "to") || (k < n && In("not_exempt", word(k)))) break;
                t->t.role = PlaceRole::Not;
            } else if (In("role_from", *w)) {
                if (negated(j)) break;   // "dont leave the red stairs": stay there
                if (next_to(j, t)) t->t.role = PlaceRole::From;
            } else if (In("role_from_after", *w)) {
                const int lead = j >= 2 && !tbrk(j) && In("from_particle", word(j - 1)) ? j - 2 : j - 1;
                if (j > 0 && !tbrk(j) && In("fire", word(j - 1))) {
                    t->t.role = PlaceRole::Them;   // "taking fire from the roof"
                } else if (lead >= 0 && !tbrk(lead + 1) && In("from_lead", word(lead)) && next_to(j, t)) {
                    if (negated(lead)) break;      // "don't move from the north window"
                    t->t.role = PlaceRole::From;   // "fall back from", "come down from"; not "back off to the basement"
                } else if (leads_to(t)) {
                    t->t.role = PlaceRole::From;   // else the bot's own position: "cover me from the east window"
                }
            } else if (In("role_mine", *w) || let_me(j)) {
                int k = j + 1;
                while (k < t->first && In("aux", word(k))) ++k;
                // "I said the west door", "can i get smoke on the north door"
                if (In("report_verb", word(k)) || (j > 0 && !tbrk(j) && In("ask", word(j - 1)))) break;
                t->t.role = PlaceRole::Mine;
            } else if (In("role_from_of", *w)) {
                if (j > 0 && !tbrk(j) && In("of_lead", word(j - 1)) && next_to(j, t)) t->t.role = PlaceRole::From;
            } else if (In("role_them", *w) || soft) {
                if (j > 0 && !tbrk(j) && In("no_words", word(j - 1))) break;   // "no contact at the north door"
                t->t.role = PlaceRole::Them;
            } else if (In("number", *w)) {   // "two on red", "got one at main"; not "put one on the north door"
                const int k = after(j, "number_fill");
                if (k < t->first && (In("number_next", word(k)) || acts(k)) && starts(j, false)) t->t.role = PlaceRole::Them;
            } else if (ing(j) && (j == 0 || tbrk(j))) {
                t->t.role = PlaceRole::Mine;   // "pushing main": a report, not an order
            }
            if (t->t.role != PlaceRole::None) break;
            // auxiliaries, determiners and particles do not use up the window
            if (!(In("aux", *w) || In("determiner", *w) || In("from_particle", *w))) ++steps;
            --j;
        }
    };
    for (size_t ti = 0; ti < targets.size(); ++ti) assign_role(ti, targets[ti], targets);

    // 5a. status: "north door is clear, hold the south window". Only when the line has another place to
    // act on (or asks for "the other one"): "east door's barricaded, blow it" names its own target
    auto status_follows = [&](const Work* t) {
        int e = t->last + 1;
        if (t->t.direction != PlaceDirection::None && e < n && !tbrk(e) && In("post_prep", word(e)))
            while (e < n && !tbrk(e) && (dir_used[static_cast<size_t>(e)] || In("post_prep", word(e)) || In("determiner", word(e))))
                ++e;   // "the door on the right | is clear"
        if (e >= n || tbrk(e) || !In("status_next", word(e))) return false;
        return !(e + 1 < n && !tbrk(e + 1) && In("status_not_next", word(e + 1)));
    };
    auto other_after = [&](int a) {   // "... take the other one", "... you take the other"; not "on the other side"
        for (int j = a; j < n; ++j)
            if (In("other", word(j)) && (j + 1 >= n || tbrk(j + 1) || In("anaphor", word(j + 1)))) return true;
        return false;
    };
    {
        std::vector<Work*> cand;
        bool rest = false;   // a role-less place that is not a status candidate
        for (Work* t : targets) {
            if (t->t.role != PlaceRole::None) continue;
            if (status_follows(t))
                cand.push_back(t);
            else
                rest = true;
        }
        if (!cand.empty() && (rest || other_after(targets.back()->last + 1)))
            for (Work* t : cand) t->t.role = PlaceRole::Status;
    }
    // 5b. a correction reaches back: "smoke blue stairs, no wait, not blue, I meant white"
    for (size_t k = 0; k < targets.size(); ++k) {
        const Work* t = targets[k];
        if (t->t.role != PlaceRole::Not || t->t.qualifier < 0) continue;
        for (size_t u = 0; u < k; ++u) {
            Work* x = targets[u];
            if (x->t.role == PlaceRole::None && x->t.qualifier == t->t.qualifier && (x->t.object == t->t.object || x->t.object < 0))
                x->t.role = PlaceRole::Not;
        }
    }
    // 5c. "I've got the north door, you take the other one", "not the north door, the other one": no
    // named place is the bot's, and the line asks for the other one -> another object of that kind
    if (!targets.empty() && std::all_of(targets.begin(), targets.end(), [](const Work* t) { return t->t.role != PlaceRole::None; })) {
        const Work* t = targets.back();
        if (t->t.object >= 0 && other_after(t->last + 1)) add(t->t.object, -1, n, n, nullptr)->t.flag = PlaceFlag::Other;
    }

    // 6. directions (rule set v4): a direction word counts only in the contexts locations.py lists. A
    // vocabulary without "directions" is done here: rule set v3 ends with 5c
    if (directions_) {
        const PlaceDirection kNone = PlaceDirection::None, kUp = PlaceDirection::Up, kDown = PlaceDirection::Down,
                             kLeft = PlaceDirection::Left, kRight = PlaceDirection::Right,
                             kForward = PlaceDirection::Forward, kBack = PlaceDirection::Back;
        // the object's noun phrase: "the back stairs", "the basement stairs", "the stairs in the basement"
        auto np_first = [](const Work* t) { return t->np >= 0 ? t->np : t->first; };
        auto np_last = [](const Work* t) { return t->np_last >= 0 ? t->np_last : t->last; };
        // the target whose noun phrase starts / ends at a token (the later target, if two do); the "other"
        // target of 5c stands at no token
        std::vector<Work*> first_of(static_cast<size_t>(n), nullptr), last_of(static_cast<size_t>(n), nullptr);
        std::vector<char> np_tok(static_cast<size_t>(n), 0);
        for (Work* t : targets) {
            if (t->first < n) first_of[static_cast<size_t>(np_first(t))] = t;
            if (t->last < n) last_of[static_cast<size_t>(np_last(t))] = t;
            if (t->first < n)
                for (int j = np_first(t); j <= np_last(t); ++j) np_tok[static_cast<size_t>(j)] = 1;
        }
        auto starts_at = [&](int j) { return first_of[static_cast<size_t>(j)]; };
        auto ends_at = [&](int j) { return last_of[static_cast<size_t>(j)]; };
        auto used = [&](int j) { return dir_used[static_cast<size_t>(j)] != 0; };
        // token j exists and only spaces separate it from the token before
        auto nb = [&](int j) { return 0 < j && j < n && !tbrk(j); };
        // token j is a word of the line that belongs to no place and no direction
        auto plain = [&](int j) { return 0 <= j && j < n && kind(j) < 0 && !used(j); };
        auto place_at = [&](int j) {   // a place starts at token j, after an optional determiner: "above the east window"
            if (nb(j) && kind(j) < 0 && In("determiner", word(j))) ++j;
            return nb(j) && kind(j) >= 0;
        };
        auto is_floor = [](const Work* t) {   // a floor on its own: "the basement", "the roof"
            return t->t.object < 0 && t->t.qualifier < 0 && t->t.zone >= 0;
        };
        auto is_vertical = [&](const Work* t) { return t->t.object >= 0 && vertical_[static_cast<size_t>(t->t.object)]; };
        // the place that starts at j, after one optional word of the list `preps` (nullptr: none) and one determiner
        auto place_after = [&](int j, const char* preps) -> Work* {
            if (preps && nb(j) && !starts_at(j) && In(preps, word(j))) ++j;
            if (nb(j) && !starts_at(j) && In("determiner", word(j))) ++j;
            return nb(j) ? starts_at(j) : nullptr;
        };
        // the place that ends right before token j, or before a form of "be" there: "the stairs are | on your right"
        auto place_before = [&](int j) -> Work* {
            if (!nb(j)) return nullptr;
            Work* t = ends_at(j - 1);
            if (!t && nb(j - 1) && kind(j - 1) < 0 && In("be", word(j - 1))) t = ends_at(j - 2);
            return t;
        };
        // a neighbour of the direction word, or nullptr: no such word. No word is in no list and equals
        // no word, so a negated test holds for it (locations.py: `None not in W[...]`)
        auto in = [&](const char* list, const std::string* w) { return w && In(list, *w); };
        auto is = [](const std::string* w, const char* s) { return w && *w == s; };

        std::vector<Work*> lone;   // the directions that are targets of their own, in line order
        for (int i = 0; i < n; ++i) {
            const std::string& w = word(i);
            const auto dw = dirs_.find(w), cw = clock_.find(w);
            if ((dw == dirs_.end() && cw == clock_.end()) || !plain(i) || owned(i)) continue;
            // the words before, in the same phrase and not words of a place or of a direction, and after
            const std::string* prev = nb(i) && plain(i - 1) ? &word(i - 1) : nullptr;
            const std::string* prev2 = prev && nb(i - 1) && plain(i - 2) ? &word(i - 2) : nullptr;
            const std::string* prev3 = prev2 && nb(i - 2) && plain(i - 3) ? &word(i - 3) : nullptr;
            const std::string* nxt = nb(i + 1) ? &word(i + 1) : nullptr;
            const std::string* nxt2 = nxt && nb(i + 2) ? &word(i + 2) : nullptr;
            // "get your head down": a noun, not a verb (dir_lead_noun: "all the way left", "keep your eyes left")
            const std::string* lead = in("dir_det", prev2) && !in("dir_lead_noun", prev) ? nullptr : prev;
            const bool opens = i == 0 || tbrk(i) > 0;                                     // the word starts the line or a phrase
            const bool stop = i + 1 >= n || tbrk(i + 1) > 0 || in("dir_end_next", nxt);   // the phrase ends here: "go straight, then ..."
            PlaceDirection d = kNone;
            int last = i;
            Work* att = nullptr;   // the place whose direction it is
            bool corrects = false;
            if (cw != clock_.end()) {
                const PlaceDirection c = cw->second;
                if (is(nxt, "oclock")) {
                    d = c, last = i + 1;   // "three oclock"
                } else if (is(nxt, "o") && is(nxt2, "clock")) {
                    d = c, last = i + 2;   // "three o'clock"
                } else if (c == kBack || c == kForward) {
                    // "on your six", "check six", "one at twelve"; not "my six kills"
                    if ((in("dir_six_lead", prev) && ends_phrase(i + 1)) || (in("dir_six_verb", prev) && stop)) d = c;
                } else if (in("dir_six_lead", prev) && stop &&
                           (!prev2 || in("dir_prep", prev2) || in("dir_six_verb", prev2) || in("dir_lead_lateral", prev2)) &&
                           !(is(prev, "my") && is(prev2, "on") && !in("role_them", prev3) && !in("role_them_soft", prev3) &&
                             !in("number", prev3))) {
                    d = c;   // "check your nine", "contact on my three"; not "breach on my three" (a countdown), "i used my one"
                }
            }
            if (d == kNone && dw != dirs_.end()) {
                const PlaceDirection k = dw->second;
                if (In("dir_always", w)) {
                    d = k;   // "upwards", "backwards"
                } else if (In("dir_relation", w)) {
                    // "from above", "below you"; not "above the east window", "below half"
                    if (!place_at(i + 1) && !(nxt && (Digits(*nxt) || In("dir_amount", *nxt)))) {
                        d = k;
                        att = place_before(i);   // "the stairs below", "the window's above you"
                    }
                } else if (k == kUp || k == kDown) {
                    // "lock down the top floor", "set up on the roof"; "back me up here", "set it up there"
                    const bool blocked = in("dir_vertical_block", prev) || (in("dir_split_object", prev) && in("dir_split_verb", prev2));
                    const bool climb = in("dir_lead_vertical", lead) || in("dir_lead_climb", lead);
                    Work* t = blocked ? nullptr : place_after(i + 1, nullptr);
                    // "go down by stairs"; not "put it down by the stairs"
                    if (!t && !blocked && (opens || climb)) t = place_after(i + 1, "dir_stairs_prep");
                    if (t && is_vertical(t)) d = k, att = t;   // "up the blue stairs", "up blue", "up the back stairs"
                    if (d == kNone) {
                        t = nb(i) ? ends_at(i - 1) : nullptr;
                        if (!t && nb(i) && nb(i - 1) && kind(i - 1) < 0 && In("dir_stairs_link", word(i - 1))) t = ends_at(i - 2);
                        if (t && is_vertical(t)) {
                            int j = np_first(t) - 1;   // the verb before the stairs: "lock the stairs down", "hold blue down"
                            if (j >= 0 && !tbrk(j + 1) && kind(j) < 0 && In("determiner", word(j))) --j;
                            if (!(j >= 0 && !tbrk(j + 1) && kind(j) < 0 && In("dir_split_verb", word(j))))
                                d = k, att = t;        // "take the stairs down", "blue stairs going up"
                        }
                    }
                    if (d == kNone && !blocked && !(k == kUp && is(prev, "back") && !in("dir_lead_vertical", prev2))) {
                        t = place_after(i + 1, "dir_zone_prep");
                        // "down to the basement" always; "up on the roof" after a motion word or at the start of a phrase;
                        // "he's up on the roof" too, but "one down in the basement" is a kill; "back up to the basement" a retreat
                        if (t && is_floor(t) &&
                            (in("from_to", nxt) || is(nxt, "onto") || opens || climb ||
                             (k == kUp && in("dir_there_lead", prev) && !in("dir_split_object", prev))))
                            d = k, att = t;
                    }
                    if (d == kNone && !blocked && !(k == kUp && in("dir_up_block", nxt))) {
                        const std::string* there = in("determiner", nxt) && in("dir_place_next", nxt2) ? nxt2 : nxt;   // "up the ladder"
                        if (in("dir_place_next", there) && (opens || in("dir_there_lead", prev)))
                            d = k;   // "get up there", "he's down there", "up top"
                        else if (ends_phrase(i + 1) && (in("dir_lead_vertical", lead) || (is(prev, "back") && in("dir_lead_vertical", prev2))))
                            d = k;   // "go up", "go back up", "he went up there"; not "go down the hall", "go up to him"
                    }
                } else if (k == kLeft || k == kRight) {
                    const bool det = in("dir_det", prev), art = in("dir_article", prev);
                    const bool bare = opens && stop;   // a phrase of its own: "Left!"
                    // the other of left / right at token x
                    auto opposite = [&](int x) { return In("dir_adjective", word(x)) && word(x) != w; };
                    bool fix = false;   // a correction: "not left, right!", "right, not left", "go left, no, right"
                    if (bare && i >= 2 && opposite(i - 1) && In("negator", word(i - 2))) fix = true;
                    if (bare && i + 2 < n && In("negator", word(i + 1)) && opposite(i + 2)) fix = true;
                    if (bare && i >= 2 && In("dir_correction", word(i - 1)))
                        for (int x = 0; x < i - 1; ++x) fix = fix || opposite(x);
                    if (k == kRight &&
                        (in("dir_right_noun", nxt) ||
                         (!det && !art &&
                          (in("dir_right_block", nxt) ||
                           (in("dir_right_soft", nxt) &&
                            (!in("dir_turn", lead) || in("dir_back_block", nxt2) || in("dir_right_block", nxt2))))))) {
                        // "the right spot"; "right now", "looking right at you", "go right at them"; not "on your right now",
                        // "turn right at the stairs"
                    } else if (k == kLeft && !is(nxt, "of") && !(in("dir_side", nxt) && !in("anaphor", nxt)) &&
                               ((in("dir_count", prev2) && !in("dir_unit", prev) && !(in("dir_article", prev2) && in("dir_throw", prev3))) ||
                                (in("dir_resource", prev) && in("dir_have", prev2)))) {
                        // "one enemy left", "no smoke left", "i got smoke left"; not "two steps left", "throw a flash left"
                    } else if (k == kLeft && in("dir_det", nxt) && (in("role_them", prev) || in("role_them_soft", prev))) {
                        // "someone left the door open", "enemy left the site"
                    } else if (in("dir_lead_lateral", lead) || in("dir_prep", prev) || in("other", prev) ||
                               (in("dir_side", nxt) && !(k == kLeft && (in("role_mine", prev) || in("govern", prev) ||
                                                                         in("role_stop", prev) || in("dir_we", prev)))) ||
                               (det && (!prev2 || in("dir_prep", prev2) || in("dir_lead_lateral", prev2) || ends_phrase(i + 1))) ||
                               (art && in("dir_lead_lateral", prev2)) || (is(nxt, "of") && !in("dir_count", prev)) ||
                               (opens && in("status_next", nxt)) || (bare && k == kLeft) || fix ||
                               (k == kRight && in("number", prev) && !prev2 && stop)) {
                        // "go left", "on your right", "the other left", "left side", "take a left", "left of the stairs",
                        // "left clear", "Left!" (never a bare "right": "Right, hold the north door"), "not left, right!",
                        // "go left, no, right", "two right"
                        d = k, corrects = fix;
                        const int j = det ? i - 2 : i - 1;   // "the north door on the left": its preposition
                        if (j >= 1 && nb(j + 1) && nb(j) && kind(j) < 0 && In("post_prep", word(j)))
                            att = place_before(j);           // also "the stairs are on your right"
                    }
                } else if (k == kForward) {
                    if (w == "straight") {
                        // "go straight"; not "go straight to the north door", "shoot straight"
                        if (in("dir_lead_forward", lead) && !in("dir_straight_not", lead) && stop) d = k;
                    } else if (w == "ahead") {
                        // "straight ahead", "up ahead", "ahead of us"; not "go ahead", "go right ahead"
                        if ((in("dir_lead_ahead", lead) && !(is(prev, "right") && is(prev2, "go"))) ||
                            (is(nxt, "of") && in("dir_person", nxt2)))
                            d = k;
                    } else if (w == "front") {
                        Work* obj = is(prev, "in") && nb(i - 1) ? ends_at(i - 2) : nullptr;   // "the door in front ..."
                        if ((in("dir_front_lead", prev) ||
                             (in("dir_det", prev) && (in("dir_prep", prev2) || in("dir_six_verb", prev2)))) &&
                            !place_at(is(nxt, "of") ? i + 2 : i + 1) &&
                            (!in("dir_det", prev) || is(nxt, "of") || ends_phrase(i + 1)) &&
                            !(in("dir_front_lead", prev) && is(nxt, "of") && in("determiner", nxt2))) {
                            d = k, att = obj;   // "in front of you", "up front"; not "in front of the car", "the front room"
                        } else if (obj && obj->t.flag == PlaceFlag::None && obj->t.qualifier < 0) {
                            obj->t.flag = PlaceFlag::UnknownModifier;   // "the door in front of the stairs": one particular door (as rule set v3)
                        }
                    } else if (in("dir_lead_forward", lead) || opens) {
                        d = k;   // "move forward", "forward!"
                    }
                } else if (w == "behind") {
                    if (in("dir_person", nxt)) {
                        d = k, att = place_before(i);   // "behind you"; "the door behind you" is that door's
                    } else if (stop && (opens || (in("dir_behind_lead", prev) && !(is(prev, "re") && in("dir_we", prev2))))) {
                        d = k;   // "from behind", "Behind!"; not "behind the sofa", "stay behind", "we're behind"
                    }
                } else if (!place_at(is(nxt, "of") ? i + 2 : i + 1)) {   // "back", "rear"; not "the back door", "at the back of the stairs"
                    if (w == "rear") {
                        // "to the rear"; not "the rear hallway"
                        if (in("dir_prep", prev) || (in("dir_det", prev) && (is(nxt, "of") || ends_phrase(i + 1)))) d = k;
                    } else if (in("dir_back_next", nxt) || (in("dir_lead_back", lead) && !in("dir_back_block", nxt)) ||
                               (in("dir_det", prev) && (in("dir_prep", prev2) || in("dir_six_verb", prev2) || in("dir_back_prep", prev2)) &&
                                (is(nxt, "of") || ends_phrase(i + 1))) ||
                               (in("dir_back_prep", prev) && ends_phrase(i + 1))) {
                        d = k;   // "back there", "go back", "at the back", "out back"; not "the back room"
                    }
                }
            }
            if (d == kNone) continue;
            for (int j = i; j <= last; ++j) dir_used[static_cast<size_t>(j)] = 1;
            if (!att) {
                store.emplace_back();
                Work* t = &store.back();
                t->t.direction = d;
                t->first = i;
                t->last = last;
                t->lone = true;
                t->corrects = corrects;
                lone.push_back(t);
            } else if (att->t.direction == kNone) {
                att->t.direction = d;   // an object keeps its first direction: "up the stairs on the left" = left
            }
        }
        for (Work* t : targets) {   // "up the red or blue stairs": both
            Work* u = t->twin;
            if (u && (t->t.direction == kNone) != (u->t.direction == kNone))
                t->t.direction = u->t.direction = t->t.direction != kNone ? t->t.direction : u->t.direction;
        }
        // the roles of the directions, by the rules of the places ("they're on the stairs and the left": both
        // theirs), over places and directions in line order; a direction is never a place to leave ("come
        // from the left"). Only now are their tokens owned: the places got their roles without them
        for (const Work* t : lone)
            for (int j = t->first; j <= t->last; ++j) owned_at[static_cast<size_t>(j)] = 1;
        std::vector<Work*> merged = targets;
        merged.insert(merged.end(), lone.begin(), lone.end());
        std::stable_sort(merged.begin(), merged.end(), by_first);
        for (size_t k = 0; k < merged.size(); ++k) {
            Work* t = merged[k];
            if (!t->lone) continue;
            assign_role(k, t, merged);
            if (t->t.role == PlaceRole::From) t->t.role = PlaceRole::None;
        }
        for (size_t k = 0; k < lone.size(); ++k) {   // "go left, no, right": the correction reaches back
            const Work* t = lone[k];
            if (!t->corrects || t->t.role != PlaceRole::None) continue;
            for (size_t u = 0; u < k; ++u) {
                Work* x = lone[u];
                if (x->t.role == PlaceRole::None && (x->t.direction == kLeft || x->t.direction == kRight) &&
                    x->t.direction != t->t.direction)
                    x->t.role = PlaceRole::Not;
            }
        }
        // an order verb or a lateral lead stands before the direction in its phrase: "go left"
        auto ordered = [&](const Work* t) {
            int a = t->first;
            while (a > 0 && !tbrk(a)) --a;   // the first token of the phrase
            for (int j = a; j < t->first; ++j)
                if (In("order_verb", word(j)) || In("dir_lead_lateral", word(j))) return true;
            return false;
        };
        auto side = [&](int j) { return In("dir_side", word(j)) || In("dir_person", word(j)); };   // the direction's own "side" / "me"

        // 6a. a verbless direction that ends its sentence is a callout when an order with a place follows:
        // "Behind you! Get to the stairs!"
        for (Work* t : lone) {
            int e = t->last + 1;
            while (e < n && !tbrk(e) && side(e)) ++e;
            if (t->t.role == PlaceRole::None && e < n && tbrk(e) == 2 && !ordered(t) &&
                std::any_of(targets.begin(), targets.end(),
                            [&](const Work* u) { return u->t.role == PlaceRole::None && e <= u->first && u->first < n; }))
                t->t.role = PlaceRole::Status;
        }
        // 6b. a direction said on the way to a place is that place's: "go left to the north door", "look up at
        // the east window", "come up from the basement to the first floor". The place is the next one with
        // the same role; only prepositions, determiners, the direction's own "side" / "me" and other places
        // stand between, and no punctuation (a place with another role may stand between only when the
        // direction has no role). Across one comma only as a bare pointer: "on your right, the north door"
        for (Work* t : lone) {
            for (Work* u : targets) {
                if (!(t->last < u->first && u->first < n) || (u->t.role != t->t.role && t->t.role == PlaceRole::None)) continue;
                if (u->t.direction == kNone && u->t.role == t->t.role) {
                    int breaks = 0, commas = 0;
                    for (int j = t->last + 1; j <= u->first; ++j) {
                        if (tbrk(j) != 0) ++breaks;
                        if (tbrk(j) == 1) ++commas;
                    }
                    // "behind me at the north door", "the left side of the main door"
                    bool on_the_way = breaks == 0, pointer = breaks == 1 && commas == 1 && !ordered(t);
                    for (int j = t->last + 1; j < np_first(u); ++j) {
                        on_the_way = on_the_way && (np_tok[static_cast<size_t>(j)] || kind(j) >= 0 || In("preposition", word(j)) ||
                                                    In("determiner", word(j)) || In("post_modifier", word(j)) || side(j));
                        pointer = pointer && (In("determiner", word(j)) || side(j));
                    }
                    if (on_the_way || pointer) {
                        u->t.direction = t->t.direction;
                        t->joined = true;
                    }
                }
                break;
            }
        }
        // 6c. "north door, on the left", "he's on the stairs, left side": a direction that is a comma item of
        // its own right after a place is that place's
        for (Work* t : lone) {
            if (t->joined || t->t.role != PlaceRole::None) continue;
            int a = t->first, e = t->last + 1;
            for (int r = 0; r < 2; ++r)   // its own preposition and determiner: "on your left", "to the right"
                if (a > 0 && !tbrk(a) && kind(a - 1) < 0 && (In("dir_prep", word(a - 1)) || In("dir_det", word(a - 1)))) --a;
            if (e < n && !tbrk(e) && In("dir_side", word(e))) ++e;   // "left side"
            Work* u = a > 0 && tbrk(a) == 1 ? ends_at(a - 1) : nullptr;
            if (u && u->t.direction == kNone && (u->t.role == PlaceRole::None || u->t.role == PlaceRole::Them) && (e >= n || tbrk(e))) {
                u->t.direction = t->t.direction;
                t->joined = true;
            }
        }
        // 6d. status, with the directions: "left side is clear, push the main door", "north door is clear, go
        // left" -- what is reported clear is not the order's target when the line has another one, before it
        // or after punctuation
        auto dir_status = [&](const Work* t) {   // "left side | is clear", "behind us | is clear"
            int e = t->last + 1;
            if (e < n && !tbrk(e) && side(e)) ++e;
            return e < n && !tbrk(e) && In("status_next", word(e)) && !(e + 1 < n && !tbrk(e + 1) && In("status_not_next", word(e + 1)));
        };
        std::vector<Work*> cand, acts_on;
        for (Work* t : targets)
            if (t->t.role == PlaceRole::None && status_follows(t)) cand.push_back(t);
        for (Work* t : lone)
            if (!t->joined && t->t.role == PlaceRole::None && dir_status(t)) cand.push_back(t);
        auto reported = [&](const Work* t) { return std::find(cand.begin(), cand.end(), t) != cand.end(); };
        for (Work* t : lone)
            if (!t->joined && t->t.role == PlaceRole::None && !reported(t)) acts_on.push_back(t);
        for (Work* t : targets)
            if (t->t.role == PlaceRole::None && !reported(t)) acts_on.push_back(t);
        for (Work* c : cand) {
            bool another = false;
            // the "other" target of 5c stands after the last token (first == n). locations.py reads the
            // punctuation of that token here, which does not exist: IndexError, the line has no Python
            // record ("i've got the north door, you take the other one, left side is clear"). Until the
            // reference says what it means, the request for the other one counts as another target to act
            // on wherever it stands, as it does for a place reported clear in 5a
            for (const Work* o : acts_on) another = another || o->first < c->first || o->first >= n || brk(c->last, o->first) != 0;
            if (another) c->t.role = PlaceRole::Status;
        }
        for (Work* t : lone)
            if (!t->joined) targets.push_back(t);
        std::stable_sort(targets.begin(), targets.end(), by_first);
    }

    for (const Work* t : targets) rec.targets.push_back(t->t);
    for (size_t k = 0; k < rec.targets.size() && rec.primary < 0; ++k)
        if (rec.targets[k].role == PlaceRole::None) rec.primary = static_cast<int>(k);
    if (rec.primary < 0 && !rec.targets.empty()) rec.primary = 0;
    return rec;
}

}  // namespace coop
