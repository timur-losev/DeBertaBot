#include "coop_intent/locations.h"

#include <algorithm>
#include <deque>

namespace coop {
namespace {

constexpr int kRoleWindow = 5;
constexpr size_t kAfterMax = 4, kZoneAfterMax = 3, kMaxPhraseTokens = 4;
const char* const kWordLists[] = {"before_fill", "after_fill", "tail", "zone_before_fill", "zone_after_fill",
                                  "lone_follow", "lone_block", "lone_not_after", "unknown_modifier", "role_not",
                                  "role_from", "role_mine", "role_them", "number", "number_next", "status_next",
                                  "role_stop", "report_verb", "other", "determiner", "neutral_modifier"};

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
    for (size_t i = 0; i < v.zones.size(); ++i)
        for (const auto& w : v.zones[i].words)
            if (!claim(w, {Kind::Zone, static_cast<int>(i), -1}, "zone " + v.zones[i].id)) return false;
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

PlaceRecord LocationMatcher::Find(std::string_view utf8) const {
    PlaceRecord rec;
    if (!ready_) return rec;
    const std::vector<Tok> toks = Tokenize(utf8);
    const int n = static_cast<int>(toks.size());
    auto word = [&](int j) -> const std::string& { return toks[static_cast<size_t>(j)].word; };
    auto tbrk = [&](int j) { return toks[static_cast<size_t>(j)].brk; };

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
            if (it->second.kind != Kind::Ignore)
                mentions.push_back({static_cast<int>(it->second.kind), it->second.a, it->second.b, i, i + k - 1});
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
            if (skip_zones && kind_at[static_cast<size_t>(j)] == kZone) continue;
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
        w->t.first = first;
        w->t.last = last;
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
            t->t.first = q->first;
            continue;
        }
        t->t.qualifier = q->a;
        t->t.first = q->first;
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
                t->t.first = q1->first;
            }
        }
    }
    // 1c. a modifier word the vocabulary does not have, right before the object: "back door"
    for (Work* t : targets) {
        const int f = t->t.first;
        if (!t->is_twin && f > 0 && In("unknown_modifier", word(f - 1)) && !tbrk(f) && kind_at[static_cast<size_t>(f - 1)] < 0)
            t->t.flag = PlaceFlag::UnknownModifier;
    }
    // 1d. "the spiral staircase": one or two unknown words between a determiner and an unqualified object
    for (Work* t : targets) {
        if (t->is_twin || t->t.flag != PlaceFlag::None || t->t.qualifier >= 0) continue;
        const int f = t->t.first;
        for (int k = 1; k <= 2; ++k) {
            if (f - k - 1 < 0 || !In("determiner", word(f - k - 1))) continue;
            bool ok = true;
            for (int j = f - k; j <= f && ok; ++j) ok = tbrk(j) == 0;
            for (int j = f - k; j < f && ok; ++j)
                ok = kind_at[static_cast<size_t>(j)] < 0 && !In("neutral_modifier", word(j)) && !In("determiner", word(j));
            if (ok) {
                t->t.flag = PlaceFlag::UnknownModifier;
                break;
            }
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
        bool qual_between = false;
        for (int j = o->last + 1; j < q->first; ++j) qual_between = qual_between || kind_at[static_cast<size_t>(j)] == kQualifier;
        if (allows(t->t.object, q->a) && gap(o->last, q->first, true, "after_fill", &cnt) && cnt <= kAfterMax &&
            brk(o->last, q->first) < 2 && !qual_between) {
            free_q[k] = 0;
            const int nxt = q->last + 1;
            const int last = q->last + (nxt < n && In("tail", word(nxt)) && !tbrk(nxt) ? 1 : 0);
            if (t->t.qualifier < 0) {
                t->t.qualifier = q->a;
                t->t.last = last;
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

    // 3. lone qualifiers: a place only where the word ends its phrase
    for (size_t k = 0; k < quals.size(); ++k) {
        if (!free_q[k]) continue;
        const Mention* q = quals[k];
        if (q->first > 0 && !tbrk(q->first) && In("lone_not_after", word(q->first - 1))) continue;   // "i'm red"
        const int nxt = q->last + 1;
        PlaceFlag flag = PlaceFlag::None;
        if (nxt < n && !tbrk(nxt) && !In("lone_follow", word(nxt))) {
            if (In("lone_block", word(nxt)) || kind_at[static_cast<size_t>(nxt)] == kZone) continue;   // "yellow ping"
            flag = PlaceFlag::Unsure;
        }
        const int obj = lone_[static_cast<size_t>(q->a)];
        const int last = q->last + (nxt < n && In("tail", word(nxt)) && !tbrk(nxt) ? 1 : 0);
        Work* t = add(obj, q->a, q->first, last, nullptr);
        t->t.flag = flag;
        t->t.inferred = obj >= 0;
    }
    auto by_first = [](const Work* a, const Work* b) { return a->t.first < b->t.first; };
    std::stable_sort(targets.begin(), targets.end(), by_first);

    // 4. zones: a zone belongs to a target only inside its noun phrase; otherwise it is a target itself
    std::vector<char> placed(zones.size(), 0);
    for (size_t zi = 0; zi < zones.size(); ++zi) {
        const Mention* z = zones[zi];
        Work* best = nullptr;
        for (Work* t : targets) {
            if (t->zone_set) continue;
            if (z->last < t->t.first) {
                if (gap(z->last, t->t.first, false, "zone_before_fill", &cnt) && cnt <= 1 && brk(z->last, t->t.first) < 2)
                    if (!best) best = t;
            } else if (z->first > t->t.last || (t->obj && t->obj->last < z->first && z->first <= t->t.last)) {
                const int a = t->obj && z->first <= t->t.last ? t->obj->last : t->t.last;
                bool other_between = false;
                for (const Work* u : targets) other_between = other_between || (u != t && a < u->t.first && u->t.first < z->first);
                if (gap(a, z->first, false, "zone_after_fill", &cnt) && cnt <= kZoneAfterMax && brk(a, z->first) < 2 &&
                    !other_between) {
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
    std::vector<char> owned(static_cast<size_t>(n) + 1, 0);
    for (const Work* t : targets)
        for (int j = t->t.first; j <= t->t.last; ++j) owned[static_cast<size_t>(j)] = 1;
    for (Work* t : targets) {
        int j = t->t.first - 1;
        for (int steps = 0; j >= 0 && steps < kRoleWindow; --j, ++steps) {
            if (tbrk(j + 1) || In("role_stop", word(j)) || owned[static_cast<size_t>(j)]) break;
            const std::string& w = word(j);
            if (In("role_not", w)) {
                t->t.role = PlaceRole::Not;
            } else if (In("role_from", w)) {
                t->t.role = PlaceRole::From;
            } else if (In("role_mine", w)) {
                if (In("report_verb", word(j + 1))) break;   // "I said the west door": not the player's place
                t->t.role = PlaceRole::Mine;
            } else if (In("role_them", w) || (In("number", w) && In("number_next", word(j + 1)))) {
                t->t.role = PlaceRole::Them;
            }
            if (t->t.role != PlaceRole::None) break;
        }
        const int e = t->t.last + 1;
        if (t->t.role == PlaceRole::None && e < n && In("status_next", word(e)) && !tbrk(e)) t->t.role = PlaceRole::Status;
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
    // 5c. "I've got the north door, you take the other one": another object of that kind
    if (!targets.empty() && std::all_of(targets.begin(), targets.end(), [](const Work* t) {
            return t->t.role == PlaceRole::Mine || t->t.role == PlaceRole::Status;
        })) {
        const Work* t = targets.back();
        bool other = false;
        for (int j = t->t.last + 1; j < n; ++j) other = other || In("other", word(j));
        if (t->t.object >= 0 && other) add(t->t.object, -1, n, n, nullptr)->t.flag = PlaceFlag::Other;
    }

    for (const Work* t : targets) rec.targets.push_back(t->t);
    for (size_t k = 0; k < rec.targets.size() && rec.primary < 0; ++k)
        if (rec.targets[k].role == PlaceRole::None) rec.primary = static_cast<int>(k);
    if (rec.primary < 0 && !rec.targets.empty()) rec.primary = 0;
    return rec;
}

}  // namespace coop
