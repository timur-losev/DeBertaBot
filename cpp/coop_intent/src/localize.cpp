// Localizer: English sentence templates -> the player's language (localize.h).
#include "coop_intent/localize.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <map>

#include "coop_intent/unicode.h"
#include "nlohmann/json.hpp"

namespace coop {

namespace {

// slots whose English value may be any words: the item a player named, a weapon the game calls by its asset's name, a
// thing the level designer labelled ("spike trap": its words in the player's language come with the line, Terms)
bool OpenSlot(const std::string& slot) { return slot == "item" || slot == "weapon" || slot == "thing"; }

struct Token {
    enum Kind { Lit, Slot, Num } kind = Lit;
    std::string text;                 // Lit
    std::string slot, form;           // Slot: name (lowercase) and form (empty: "text")
    bool cap = false;                 // Slot: first letter capital
    std::vector<std::string> plural;  // Num in a translation: the words for one / few / many (or one / other)
};

struct Template {
    std::string en;
    std::vector<Token> match, out;
    int slots = 0;
    size_t literal = 0;
};

struct SlotTable {
    std::vector<std::string> values;   // the English values, longest first
    std::map<std::string, std::map<std::string, std::string>> forms;
    std::map<std::string, std::string> other;
};

std::string Lower(std::string s) {
    for (char& c : s)
        if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
    return s;
}

// the first letter capital: ASCII, Latin-1 (á -> Á) and Cyrillic (а -> А, ё -> Ё)
std::string Capital(const std::string& s) {
    std::u32string u = DecodeUtf8(s);
    if (u.empty()) return s;
    char32_t& c = u[0];
    if (c >= U'a' && c <= U'z') c -= 32;
    else if (c >= 0xE0 && c <= 0xFE && c != 0xF7) c -= 32;
    else if (c >= 0x430 && c <= 0x44F) c -= 32;
    else if (c >= 0x450 && c <= 0x45F) c -= 80;
    return EncodeUtf8(u);
}

bool Parse(const std::string& s, bool target, std::vector<Token>* out, std::string* error) {
    out->clear();
    std::string lit;
    for (size_t i = 0; i < s.size();) {
        if (s[i] != '{') {
            lit += s[i++];
            continue;
        }
        const size_t end = s.find('}', i);
        if (end == std::string::npos) return *error = "an unclosed { in \"" + s + "\"", false;
        if (!lit.empty()) out->push_back({Token::Lit, lit}), lit.clear();
        std::string inside = s.substr(i + 1, end - i - 1);
        i = end + 1;
        Token t;
        if (inside == "n" || inside.rfind("n:", 0) == 0) {
            t.kind = Token::Num;
            if (inside.size() > 2) {
                if (!target) return *error = "a plural in an English template: \"" + s + "\"", false;
                std::string alts = inside.substr(2);
                for (size_t a = 0;;) {
                    const size_t bar = alts.find('|', a);
                    t.plural.push_back(alts.substr(a, bar == std::string::npos ? std::string::npos : bar - a));
                    if (bar == std::string::npos) break;
                    a = bar + 1;
                }
            }
        } else {
            t.kind = Token::Slot;
            const size_t dot = inside.find('.');
            std::string name = inside.substr(0, dot);
            if (dot != std::string::npos) {
                if (!target) return *error = "a form in an English template: \"" + s + "\"", false;
                t.form = inside.substr(dot + 1);
            }
            if (name.empty() || !std::isalpha(static_cast<unsigned char>(name[0]))) return *error = "a bad slot {" + inside + "} in \"" + s + "\"", false;
            t.cap = name[0] >= 'A' && name[0] <= 'Z';
            t.slot = Lower(name);
        }
        out->push_back(std::move(t));
    }
    if (!lit.empty()) out->push_back({Token::Lit, lit});
    return true;
}

bool EqualAt(const std::string& s, size_t pos, const std::string& v) {
    if (pos + v.size() > s.size()) return false;
    for (size_t k = 0; k < v.size(); ++k) {
        char a = s[pos + k], b = v[k];
        if (a >= 'A' && a <= 'Z') a = static_cast<char>(a - 'A' + 'a');
        if (b >= 'A' && b <= 'Z') b = static_cast<char>(b - 'A' + 'a');
        if (a != b) return false;
    }
    return true;
}

}  // namespace

std::vector<std::string> SplitSentences(const std::string& line) {
    std::vector<std::string> out;
    std::string cur;
    for (size_t i = 0; i < line.size(); ++i) {
        cur += line[i];
        const char c = line[i];
        if ((c == '.' || c == '!' || c == '?') && i + 1 < line.size() && std::isspace(static_cast<unsigned char>(line[i + 1]))) {
            out.push_back(cur);
            cur.clear();
            while (i + 1 < line.size() && std::isspace(static_cast<unsigned char>(line[i + 1]))) ++i;
        }
    }
    size_t b = cur.find_first_not_of(" \t\r\n"), e = cur.find_last_not_of(" \t\r\n");
    if (b != std::string::npos) out.push_back(cur.substr(b, e - b + 1));
    return out;
}

struct Localizer::Impl {
    std::string language;
    std::vector<Template> templates;   // the ones with fewer slots and more literal text first
    std::map<std::string, SlotTable> slots;

    using Bindings = std::map<std::string, std::string>;

    bool Match(const std::vector<Token>& toks, size_t ti, const std::string& s, size_t pos, Bindings* b) const {
        if (ti == toks.size()) return pos == s.size();
        const Token& t = toks[ti];
        if (t.kind == Token::Lit) return s.compare(pos, t.text.size(), t.text) == 0 && Match(toks, ti + 1, s, pos + t.text.size(), b);
        if (t.kind == Token::Num) {
            size_t end = pos;
            while (end < s.size() && std::isdigit(static_cast<unsigned char>(s[end]))) ++end;
            if (end == pos) return false;
            (*b)["n"] = s.substr(pos, end - pos);
            return Match(toks, ti + 1, s, end, b);
        }
        const auto it = slots.find(t.slot);
        if (it == slots.end()) return false;
        for (const std::string& v : it->second.values) {
            if (!EqualAt(s, pos, v)) continue;
            (*b)[t.slot] = v;
            if (Match(toks, ti + 1, s, pos + v.size(), b)) return true;
        }
        if (OpenSlot(t.slot)) {
            for (size_t end = pos + 1; end <= s.size(); ++end) {
                const std::string v = Lower(s.substr(pos, end - pos));
                if (v.find_first_not_of(' ') == std::string::npos || v.front() == ' ' || v.back() == ' ') continue;
                (*b)[t.slot] = v;
                if (Match(toks, ti + 1, s, end, b)) return true;
            }
        }
        b->erase(t.slot);
        return false;
    }

    bool Render(const Template& tp, const Bindings& b, std::string* out, const Localizer::Terms* terms) const {
        out->clear();
        for (const Token& t : tp.out) {
            if (t.kind == Token::Lit) {
                *out += t.text;
            } else if (t.kind == Token::Num) {
                const auto nb = b.find("n");
                if (nb == b.end()) return false;
                if (t.plural.empty()) {
                    *out += nb->second;
                    continue;
                }
                const long long n = std::stoll(nb->second);
                size_t k = 0;
                if (t.plural.size() >= 3) {
                    const long long d = n % 10, h = n % 100;
                    k = (d == 1 && h != 11) ? 0 : (d >= 2 && d <= 4 && (h < 12 || h > 14)) ? 1 : 2;
                } else if (t.plural.size() == 2) {
                    k = n == 1 ? 0 : 1;
                }
                *out += t.plural[k];
            } else {
                const auto sb = b.find(t.slot);
                const auto st = slots.find(t.slot);
                if (sb == b.end() || st == slots.end()) return false;
                // the words the line came with (a labelled thing's name in the player's language) before the table's
                const std::map<std::string, std::string>* given = nullptr;
                if (terms) {
                    const auto ts = terms->find(t.slot);
                    if (ts != terms->end()) {
                        const auto tv = ts->second.find(sb->second);
                        if (tv != ts->second.end()) given = &tv->second;
                    }
                }
                const auto fv = st->second.forms.find(sb->second);
                const std::map<std::string, std::string>& forms = given ? *given : fv != st->second.forms.end() ? fv->second : st->second.other;
                auto w = forms.find(t.form.empty() ? "text" : t.form);
                if (w == forms.end() && given) w = forms.find("text");   // a name given without that form: its plain one
                if (w == forms.end()) return false;
                // "*": the English words themselves (an English table: "bro" lines keep the item the player named)
                const std::string& word = w->second == "*" ? sb->second : w->second;
                *out += t.cap ? Capital(word) : word;
            }
        }
        return true;
    }
};

Localizer::Localizer() : impl_(new Impl) {}
Localizer::~Localizer() = default;
bool Localizer::Loaded() const { return !impl_->templates.empty(); }
const std::string& Localizer::Language() const { return impl_->language; }
size_t Localizer::Templates() const { return impl_->templates.size(); }

bool Localizer::Load(const std::string& path, std::string* error) {
    using nlohmann::json;
    std::ifstream in(path, std::ios::binary);
    if (!in) return *error = "cannot read " + path, false;
    json j;
    try {
        j = json::parse(in);
    } catch (const std::exception& e) {
        return *error = path + ": " + e.what(), false;
    }
    Impl fresh;
    fresh.language = j.value("language", std::string());
    if (!j.contains("sentences") || !j["sentences"].is_object() || !j.contains("slots") || !j["slots"].is_object())
        return *error = path + ": no \"sentences\" or \"slots\"", false;
    for (auto s = j["slots"].begin(); s != j["slots"].end(); ++s) {
        SlotTable t;
        for (auto v = s.value().begin(); v != s.value().end(); ++v) {
            std::map<std::string, std::string> forms;
            if (v.value().is_string()) forms["text"] = v.value().get<std::string>();
            else
                for (auto f = v.value().begin(); f != v.value().end(); ++f)
                    if (f.value().is_string()) forms[f.key()] = f.value().get<std::string>();
            if (v.key() == "_other") t.other = std::move(forms);
            else t.values.push_back(Lower(v.key())), t.forms[Lower(v.key())] = std::move(forms);
        }
        std::stable_sort(t.values.begin(), t.values.end(), [](const std::string& a, const std::string& b) { return a.size() > b.size(); });
        fresh.slots[s.key()] = std::move(t);
    }
    for (auto s = j["sentences"].begin(); s != j["sentences"].end(); ++s) {
        Template tp;
        tp.en = s.key();
        if (!s.value().is_string()) return *error = path + ": the translation of \"" + tp.en + "\" is not a string", false;
        if (!Parse(tp.en, false, &tp.match, error) || !Parse(s.value().get<std::string>(), true, &tp.out, error)) return false;
        for (const Token& t : tp.match) {
            if (t.kind == Token::Lit) tp.literal += t.text.size();
            else ++tp.slots;
            if (t.kind == Token::Slot && !fresh.slots.count(t.slot)) return *error = path + ": \"" + tp.en + "\" uses the slot " + t.slot + ", which has no table", false;
        }
        fresh.templates.push_back(std::move(tp));
    }
    std::stable_sort(fresh.templates.begin(), fresh.templates.end(), [](const Template& a, const Template& b) {
        return a.slots != b.slots ? a.slots < b.slots : a.literal > b.literal;
    });
    *impl_ = std::move(fresh);
    return true;
}

bool Localizer::Translate(const std::string& english, std::string* out, std::string* missing, const Terms* terms) const {
    out->clear();
    std::string result;
    for (const std::string& s : SplitSentences(english)) {
        bool done = false;
        for (const Template& tp : impl_->templates) {
            Impl::Bindings b;
            std::string piece;
            if (impl_->Match(tp.match, 0, s, 0, &b) && impl_->Render(tp, b, &piece, terms)) {
                if (!result.empty()) result += ' ';
                result += piece;
                done = true;
                break;
            }
        }
        if (!done) {
            if (missing) *missing = s;
            return false;
        }
    }
    *out = result;
    return true;
}

std::vector<std::string> Localizer::Examples() const {
    std::vector<std::string> out;
    for (const Template& tp : impl_->templates) {
        // every value of every slot once (the other slots at their first value), and an open slot's unknown word
        std::vector<std::pair<std::string, std::vector<std::string>>> slots;
        for (const Token& t : tp.match)
            if (t.kind == Token::Slot) {
                const SlotTable& st = impl_->slots.at(t.slot);
                std::vector<std::string> vals = st.values;
                if (OpenSlot(t.slot)) vals.push_back("gizmo");
                slots.push_back({t.slot, vals});
            }
        auto fill = [&](size_t which, const std::string& value) {
            std::string s;
            size_t k = 0;
            for (const Token& t : tp.match) {
                if (t.kind == Token::Lit) s += t.text;
                else if (t.kind == Token::Num) s += "23";
                else {
                    const std::string& v = k == which ? value : (slots[k].second.empty() ? std::string("x") : slots[k].second[0]);
                    s += t.cap ? Capital(v) : v;
                    ++k;
                }
            }
            return s;
        };
        if (slots.empty()) out.push_back(fill(0, {}));
        for (size_t k = 0; k < slots.size(); ++k)
            for (const std::string& v : slots[k].second) out.push_back(fill(k, v));
    }
    return out;
}

}  // namespace coop
