#include "coop_intent/locations.h"

#include <algorithm>
#include <deque>

namespace coop {
namespace {

constexpr int kRoleWindow = 5, kRoleReach = 12, kAnaphorMax = 6, kGovernMax = 4;
constexpr size_t kAfterMax = 4, kZoneAfterMax = 3, kMaxPhraseTokens = 4, kMaxTokens = 128;
// locations.py WORD_LISTS: a vocabulary must have exactly these
const char* const kWordLists[] = {
    "before_fill", "after_fill", "tail", "zone_after_fill", "lone_follow", "lone_block", "lone_not_after",
    "unknown_modifier", "role_not", "role_from", "role_mine", "role_them", "number", "number_next", "status_next",
    "role_stop", "report_verb", "other", "determiner", "neutral_modifier", "role_them_soft", "soft_fill", "soft_lead",
    "number_fill", "motion_past", "role_from_of", "of_lead", "be", "not_ing", "role_from_after", "from_lead", "from_to",
    "ask", "number_lead", "status_not_next", "not_exempt", "not_unless_to", "govern", "aux", "order_verb",
    "from_particle", "filler", "anaphor", "let", "let_me", "negator", "fire", "no_words", "preposition", "post_prep",
    "post_modifier"};

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
    max_len_ = 1;
    for (const auto& o : v.objects) {
        if (IndexOf(objects_, o.id) >= 0) return fail("duplicate object id " + o.id);
        if (o.words.empty()) return fail("object " + o.id + " has no words");
        objects_.push_back(o.id);
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
    for (const char* name : kWordLists) {
        auto it = v.words.find(name);
        if (it == v.words.end()) return fail(std::string("missing word list ") + name);
        for (const auto& w : it->second)
            if (!PhraseOk(w) || w.find(' ') != std::string::npos)
                return fail(std::string("word list ") + name + ": \"" + w + "\" must be one lowercase ASCII token");
        lists_[name] = std::unordered_set<std::string>(it->second.begin(), it->second.end());
    }
    for (const auto& list : v.words)   // a list no rule reads: locations.py refuses the vocabulary too
        if (lists_.count(list.first) == 0) return fail("unknown word list " + list.first);
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
    for (Work* t : targets) {
        const int f = t->first;
        if (!t->is_twin && f > 0 && In("unknown_modifier", word(f - 1)) && !tbrk(f) && kind(f - 1) < 0)
            t->t.flag = PlaceFlag::UnknownModifier;
    }
    // 1d. "the spiral staircase": one unknown word between a determiner and an unqualified object
    for (Work* t : targets) {
        const int f = t->first;
        if (t->is_twin || t->t.flag != PlaceFlag::None || t->t.qualifier >= 0 || f < 2) continue;
        const std::string& w = word(f - 1);
        if (In("determiner", word(f - 2)) && !tbrk(f - 1) && !tbrk(f) && kind(f - 1) < 0 && !In("neutral_modifier", w) &&
            !In("determiner", w) && !In("preposition", w) && !In("number", w) && !In("order_verb", w))
            t->t.flag = PlaceFlag::UnknownModifier;
    }
    // 1e. "take the other door": the object right after an `other` word is the other one of its kind
    for (Work* t : targets) {
        const int f = t->first;
        if (!t->is_twin && t->t.flag == PlaceFlag::None && t->t.qualifier < 0 && f > 0 && !tbrk(f) && In("other", word(f - 1)))
            t->t.flag = PlaceFlag::Other;
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
        if (and_or(objects[i]->last, objects[i + 1]->first) && ta->t.flag == PlaceFlag::None) {
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
        if (e < n && !tbrk(e) && In("post_modifier", word(e)) && kind(e) < 0) t->t.flag = PlaceFlag::UnknownModifier;
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

    for (size_t ti = 0; ti < targets.size(); ++ti) {
        Work* t = targets[ti];
        // "they're on red and blue": a place joined to the one before it by and / or shares its role
        if (ti > 0) {
            const Work* u = targets[ti - 1];
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
                    continue;
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
    }

    // 5a. status: "north door is clear, hold the south window". Only when the line has another place to
    // act on (or asks for "the other one"): "east door's barricaded, blow it" names its own target
    auto status_follows = [&](const Work* t) {
        const int e = t->last + 1;
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

    for (const Work* t : targets) rec.targets.push_back(t->t);
    for (size_t k = 0; k < rec.targets.size() && rec.primary < 0; ++k)
        if (rec.targets[k].role == PlaceRole::None) rec.primary = static_cast<int>(k);
    if (rec.primary < 0 && !rec.targets.empty()) rec.primary = 0;
    return rec;
}

}  // namespace coop
