// The twin of scripts/coop/time_phrase.py: the same steps in the same order (see the header).
#include "coop_intent/time_phrase.h"

#include <charconv>
#include <cmath>
#include <optional>
#include <vector>

namespace coop {
namespace {

struct Tok {
    std::string t;
    size_t a = 0, b = 0;   // where it is in the line
};

bool IsAlnum(char c) { return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9'); }
bool IsDigit(char c) { return c >= '0' && c <= '9'; }
bool IsSpace(char c) { return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\f' || c == '\v'; }
char Lower(char c) { return c >= 'A' && c <= 'Z' ? static_cast<char>(c - 'A' + 'a') : c; }

// [a-z0-9]+ (?:[.,][0-9]+)? over the lowercased line
std::vector<Tok> Tokens(std::string_view line) {
    std::vector<Tok> out;
    size_t i = 0;
    while (i < line.size()) {
        if (!IsAlnum(Lower(line[i]))) {
            ++i;
            continue;
        }
        Tok t;
        t.a = i;
        while (i < line.size() && IsAlnum(Lower(line[i]))) t.t += Lower(line[i++]);
        if (i + 1 < line.size() && (line[i] == '.' || line[i] == ',') && IsDigit(line[i + 1])) {
            t.t += line[i++];
            while (i < line.size() && IsDigit(line[i])) t.t += line[i++];
        }
        t.b = i;
        out.push_back(std::move(t));
    }
    return out;
}

bool AllDigitsNumber(const std::string& t) {   // [0-9]+([.,][0-9]+)?
    size_t i = 0;
    while (i < t.size() && IsDigit(t[i])) ++i;
    if (i == 0) return false;
    if (i == t.size()) return true;
    if (t[i] != '.' && t[i] != ',') return false;
    size_t j = ++i;
    while (i < t.size() && IsDigit(t[i])) ++i;
    return i > j && i == t.size();
}

double ParseNumber(std::string t) {
    for (char& c : t)
        if (c == ',') c = '.';
    double v = 0;
    std::from_chars(t.data(), t.data() + t.size(), v);
    return v;
}

int Ones(const std::string& t) {
    static const char* kOnes[] = {"zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                                  "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
                                  "nineteen"};
    for (int i = 0; i < 20; ++i)
        if (t == kOnes[i]) return i;
    return -1;
}

int Tens(const std::string& t) {
    static const char* kTens[] = {"twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"};
    for (int i = 0; i < 8; ++i)
        if (t == kTens[i]) return 20 + 10 * i;
    return -1;
}

double UnitSeconds(const std::string& t) {
    if (t == "second" || t == "seconds" || t == "sec" || t == "secs" || t == "s") return 1.0;
    if (t == "minute" || t == "minutes" || t == "min" || t == "mins") return 60.0;
    if (t == "hour" || t == "hours") return 3600.0;
    return 0.0;
}

bool IsAbout(const std::string& t) {
    for (const char* w : {"about", "around", "roughly", "approximately", "some", "maybe", "like", "almost", "nearly", "just", "only"})
        if (t == w) return true;
    return false;
}

struct Num {
    double v;
    size_t next;
};
struct Unit {
    double per;
    size_t next;
};

bool Is(const std::vector<Tok>& k, size_t i, std::initializer_list<const char*> words) {
    for (const char* w : words) {
        if (i >= k.size() || k[i].t != w) return false;
        ++i;
    }
    return true;
}

std::optional<Num> Number(const std::vector<Tok>& k, size_t i) {
    if (i >= k.size()) return std::nullopt;
    const std::string& t = k[i].t;
    double v;
    size_t j;
    if (AllDigitsNumber(t)) {
        v = ParseNumber(t), j = i + 1;
    } else if (Tens(t) >= 0) {
        v = Tens(t), j = i + 1;
        if (j < k.size() && Ones(k[j].t) > 0 && Ones(k[j].t) < 10) v += Ones(k[j].t), ++j;
    } else if (Ones(t) >= 0) {
        v = Ones(t), j = i + 1;
    } else {
        return std::nullopt;
    }
    if (j + 2 < k.size() && Is(k, j, {"and", "a", "half"})) v += 0.5, j += 3;
    return Num{v, j};
}

std::optional<Unit> UnitAt(const std::vector<Tok>& k, size_t i) {
    if (i < k.size() && UnitSeconds(k[i].t) > 0) return Unit{UnitSeconds(k[i].t), i + 1};
    return std::nullopt;
}

struct Amount {
    bool range = false;
    double seconds = 0, min = 0, max = 0;
    size_t end = 0;
    bool more = false;
};

std::optional<Amount> AmountAt(const std::vector<Tok>& k, size_t i) {
    size_t j = i;
    bool more = false;
    if (j < k.size() && k[j].t == "another") more = true, ++j;
    while (j < k.size() && IsAbout(k[j].t)) ++j;
    auto fixed = [&](double s, size_t end) { Amount a; a.seconds = s, a.end = end, a.more = more; return a; };
    // between 5 and 10 seconds
    if (j < k.size() && k[j].t == "between") {
        auto lo = Number(k, j + 1);
        if (lo && lo->next < k.size() && k[lo->next].t == "and") {
            auto hi = Number(k, lo->next + 1);
            auto u = hi ? UnitAt(k, hi->next) : std::nullopt;
            if (hi && u && hi->v > lo->v) {
                Amount a;
                a.range = true, a.min = lo->v * u->per, a.max = hi->v * u->per, a.end = u->next, a.more = more;
                return a;
            }
        }
    }
    // half a minute, a half minute, half of a minute, half minute
    if (Is(k, j, {"half", "a", "minute"})) return fixed(30.0, j + 3);
    if (Is(k, j, {"a", "half", "minute"})) return fixed(30.0, j + 3);
    if (Is(k, j, {"half", "of", "a", "minute"})) return fixed(30.0, j + 4);
    if (Is(k, j, {"half", "minute"})) return fixed(30.0, j + 2);
    // a minute and a half, a second and a half
    if (j + 1 < k.size() && (k[j].t == "a" || k[j].t == "one") && Is(k, j + 2, {"and", "a", "half"})) {
        const std::string& w = k[j + 1].t;
        if (w == "minute") return fixed(90.0, j + 5);
        if (w == "second" || w == "sec") return fixed(1.5, j + 5);
    }
    const size_t after_a = j + (Is(k, j, {"a"}) ? 1 : 0);
    // a couple of seconds, couple seconds, a couple more seconds
    if (after_a < k.size() && k[after_a].t == "couple") {
        size_t u_at = after_a + 1 + (after_a + 1 < k.size() && k[after_a + 1].t == "of" ? 1 : 0);
        if (u_at < k.size() && (k[u_at].t == "more" || k[u_at].t == "extra")) more = true, ++u_at;
        if (auto u = UnitAt(k, u_at)) return fixed(2.0 * u->per, u->next);
    }
    // a few seconds, several seconds, a few more seconds
    if (after_a < k.size() && (k[after_a].t == "few" || k[after_a].t == "several")) {
        size_t u_at = after_a + 1;
        if (u_at < k.size() && (k[u_at].t == "more" || k[u_at].t == "extra")) more = true, ++u_at;
        auto u = UnitAt(k, u_at);
        if (u && u->per == 1.0) {
            Amount a;
            a.range = true, a.min = 3.0, a.max = 7.0, a.end = u->next, a.more = more;
            return a;
        }
    }
    // a second, a minute (for a minute)
    if (j < k.size() && (k[j].t == "a" || k[j].t == "an")) {
        auto u = UnitAt(k, j + 1);
        if (u) {
            const std::string& w = k[j + 1].t;
            if (w == "second" || w == "sec" || w == "minute" || w == "min" || w == "hour") return fixed(u->per, u->next);
        }
    }
    // 5s, 10sec
    if (j < k.size()) {
        const std::string& t = k[j].t;
        size_t d = 0;
        while (d < t.size() && IsDigit(t[d])) ++d;
        const std::string tail = t.substr(d);
        if (d > 0 && (tail == "s" || tail == "sec" || tail == "secs")) return fixed(ParseNumber(t.substr(0, d)), j + 1);
    }
    auto n = Number(k, j);
    if (!n) return std::nullopt;
    const double v = n->v;
    size_t at = n->next;
    // a range: 10 to 15, 10 or 15, 10-15 (two numbers in a row)
    std::optional<Num> hi;
    if (at < k.size() && (k[at].t == "to" || k[at].t == "or")) {
        hi = Number(k, at + 1);
    } else if (at < k.size()) {
        hi = Number(k, at);
        if (hi && hi->v <= v) hi.reset();
    }
    if (hi && hi->v > v) {
        if (auto u = UnitAt(k, hi->next)) {
            Amount a;
            a.range = true, a.min = v * u->per, a.max = hi->v * u->per, a.end = u->next, a.more = more;
            return a;
        }
    }
    if (at < k.size() && (k[at].t == "more" || k[at].t == "extra")) more = true, ++at;
    auto u = UnitAt(k, at);
    if (!u) return std::nullopt;
    double seconds = v * u->per;
    size_t end = u->next;
    // 1 minute 30 seconds, a minute and 20 seconds
    if (u->per > 1.0) {
        const size_t m = end + (end < k.size() && k[end].t == "and" ? 1 : 0);
        if (auto n2 = Number(k, m)) {
            auto u2 = UnitAt(k, n2->next);
            if (u2 && u2->per == 1.0) seconds += n2->v, end = u2->next;
        }
    }
    return fixed(seconds, end);
}

double Tenths(double v) { return std::floor(v * 10.0 + 0.5) / 10.0; }

bool HasLetter(const std::string& s) {
    for (char c : s)
        if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')) return true;
    return false;
}

std::string Trim(const std::string& s) {
    size_t a = 0, b = s.size();
    while (a < b && IsSpace(s[a])) ++a;
    while (b > a && IsSpace(s[b - 1])) --b;
    return s.substr(a, b - a);
}

// the line without the time, tidied as the Python's re.sub steps do
std::string Rest(std::string_view line, size_t a, size_t b, const char* instead, const char* if_empty) {
    std::string r = Trim(std::string(line.substr(0, a)) + " " + std::string(line.substr(b)));
    std::string s;   // \s+ -> " "
    for (size_t i = 0; i < r.size();) {
        if (IsSpace(r[i])) {
            s += ' ';
            while (i < r.size() && IsSpace(r[i])) ++i;
        } else {
            s += r[i++];
        }
    }
    std::string t;   // \s+([,.!?;:]) -> \1
    for (size_t i = 0; i < s.size(); ++i) {
        if (s[i] == ' ' && i + 1 < s.size() && std::string_view(",.!?;:").find(s[i + 1]) != std::string_view::npos) continue;
        t += s[i];
    }
    size_t lead = 0;   // ^[,.;:\s]+
    while (lead < t.size() && (std::string_view(",.;:").find(t[lead]) != std::string_view::npos || IsSpace(t[lead]))) ++lead;
    t = t.substr(lead);
    // ,\s*([.!?]?)$ -> \1
    {
        size_t end = t.size();
        std::string keep;
        if (end > 0 && std::string_view(".!?").find(t[end - 1]) != std::string_view::npos) keep = t[end - 1], --end;
        size_t c = end;
        while (c > 0 && IsSpace(t[c - 1])) --c;
        if (c > 0 && t[c - 1] == ',') t = t.substr(0, c - 1) + keep;
    }
    t = Trim(t);
    if (instead) t = Trim(std::string(instead) + " " + t);
    if (!HasLetter(t)) t = if_empty;
    return t;
}

TimePhrase Finish(std::string_view line, const std::vector<Tok>& k, size_t start, size_t end, bool after, const Amount& am,
                  std::string* rest, const char* instead = nullptr) {
    TimePhrase out;
    out.after = after;
    out.more = am.more;
    auto cut = [&](double v) {
        v = Tenths(v);
        if (v > kMaxOrderSeconds) v = kMaxOrderSeconds, out.capped = true;
        return v;
    };
    if (am.range) {
        out.range = true, out.min = cut(am.min), out.max = cut(am.max);
        if (out.min >= out.max) out.range = false, out.seconds = out.max, out.min = out.max = 0;
    } else {
        out.seconds = cut(am.seconds);
    }
    if (!out.range && out.seconds <= 0.0) {
        *rest = std::string(line);
        return TimePhrase{};
    }
    const size_t a = k[start].a, b = k[end - 1].b;
    out.said = std::string(line.substr(a, b - a));
    out.found = true;
    *rest = Rest(line, a, b, instead, "wait");
    return out;
}

}  // namespace

TimePhrase FindTimePhrase(std::string_view line, std::string* rest) {
    const std::vector<Tok> k = Tokens(line);
    for (size_t i = 0; i < k.size(); ++i) {
        const std::string& t = k[i].t;
        // count to ten
        if (t == "count" && i + 1 < k.size()) {
            const size_t j = i + 1 + (k[i + 1].t == "to" ? 1 : 0);
            if (auto n = Number(k, j)) {
                Amount a;
                a.seconds = n->v;
                return Finish(line, k, i, n->next, true, a, rest);
            }
        }
        const bool lead = t == "for" || t == "in" || t == "after" || t == "within";
        const size_t start = i;
        // "give me 5 seconds", "gimme a minute": a wait
        size_t give = 0;
        if (!lead && (t == "give" || t == "gimme")) {
            give = t == "give" && i + 1 < k.size() && k[i + 1].t == "me" ? 2 : 1;
            if (t == "give" && give == 1) continue;
        }
        size_t j = i + (lead ? 1 : give);
        if (lead && Is(k, j, {"the", "next"})) j += 2;
        auto a = AmountAt(k, j);
        if (!a) continue;
        Amount am = *a;
        size_t end = am.end;
        // "a second" / "a minute" without "for": the idiom, no time ("just a sec" too)
        size_t k0 = j;
        while (k0 < k.size() && (k[k0].t == "just" || k[k0].t == "only")) ++k0;
        if (k0 < k.size() && k[k0].t == "a" && end - k0 == 2 && t != "for" && t != "within") continue;
        // "for 10 seconds more", "for half a minute more"
        if (!am.more && end < k.size() && (k[end].t == "more" || k[end].t == "extra")) am.more = true, ++end;
        if (give) return Finish(line, k, start, end, false, am, rest, "wait");
        bool after = t == "in" || t == "after";
        if (Is(k, end, {"from", "now"})) after = true, end += 2;
        else if (Is(k, end, {"later"})) after = true, end += 1;
        if (Is(k, end, {"or", "so"})) end += 2;
        return Finish(line, k, start, end, after, am, rest);
    }
    *rest = std::string(line);
    return TimePhrase{};
}

}  // namespace coop
