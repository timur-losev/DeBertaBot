// The teaching lines and the memory's text rules (teach.h).
#include "coop_intent/teach.h"

#include <algorithm>
#include <initializer_list>
#include <unordered_set>

#include "coop_intent/unicode.h"

namespace coop {

namespace {

char32_t Lower(char32_t c) {
    if (c >= U'A' && c <= U'Z') return c + 32;
    if (c >= U'А' && c <= U'Я') return c + 32;   // А..Я
    if (c == U'Ё' || c == U'ё') return U'е';   // Ё ё -> е
    if (c >= U'À' && c <= U'Þ' && c != U'×') return c + 32;   // Latin-1 capitals (Ñ, É, ...)
    return c;
}

bool WordChar(char32_t c) {
    return (c >= U'a' && c <= U'z') || (c >= U'0' && c <= U'9') || (c >= U'а' && c <= U'я') ||
           (c >= U'ß' && c <= U'ÿ' && c != U'÷') || c == U'\'';
}

bool Vowelish(char32_t c) {   // what a stem drops at the end of a taught word
    static const std::u32string kSet = U"аеиоуыэюяьйaeiouy";
    return kSet.find(c) != std::u32string::npos;
}

std::string Join(const std::vector<std::string>& w, size_t from, size_t to) {
    std::string s;
    for (size_t i = from; i < to && i < w.size(); ++i) s += (s.empty() ? "" : " ") + w[i];
    return s;
}

// the words after `phrase` when the line starts with it at `at`; npos: it does not
size_t After(const std::vector<std::string>& w, size_t at, std::string_view phrase) {
    const std::vector<std::string> p = MemoryWords(phrase);
    if (at + p.size() > w.size()) return std::string::npos;
    for (size_t i = 0; i < p.size(); ++i)
        if (w[at + i] != p[i]) return std::string::npos;
    return at + p.size();
}

// the longest of `phrases` the line starts with at `at`; npos: none
size_t AfterAny(const std::vector<std::string>& w, size_t at, std::initializer_list<std::string_view> phrases) {
    size_t best = std::string::npos;
    for (std::string_view p : phrases) {
        const size_t k = After(w, at, p);
        if (k != std::string::npos && (best == std::string::npos || k > best)) best = k;
    }
    return best;
}

bool IsAny(const std::string& line, std::initializer_list<std::string_view> lines) {
    for (std::string_view l : lines)
        if (line == l) return true;
    return false;
}

// "no", «нет», "not that", «не то» before "I meant ...": the line is still the correction
size_t SkipLead(const std::vector<std::string>& w) {
    static const std::unordered_set<std::string> kOne = {"нет", "ну", "no", "nope", "um", "uh", "oh", "nah"};
    size_t i = 0;
    for (int step = 0; step < 4 && i < w.size(); ++step) {
        if (kOne.count(w[i])) {
            ++i;
            continue;
        }
        const size_t k = AfterAny(w, i, {"не то", "не так", "not that", "not that one", "eso no", "no eso"});
        if (k == std::string::npos) break;
        i = k;
    }
    return i;
}

// a name as kept: the articles and possessives in front of it dropped
std::vector<std::string> NameWords(const std::vector<std::string>& w, size_t from) {
    static const std::unordered_set<std::string> kFront = {
        "the", "a", "an", "our", "my", "your", "el", "la", "los", "las", "un", "una", "mi", "nuestro", "nuestra", "tu",
        "наш", "наша", "наше", "мой", "моя", "мое", "твой", "твоя", "твое"};
    // «называй это теперь камень», «называй теперь это камень просто» (2026-10-30, the owner): "now" and "just" round the name
    static const std::unordered_set<std::string> kRound = {"теперь", "просто", "now", "just", "ahora"};
    size_t i = from;
    while (i < w.size() && (kFront.count(w[i]) || kRound.count(w[i]))) ++i;
    size_t end = w.size();
    while (end > i && kRound.count(w[end - 1])) --end;
    return std::vector<std::string>(w.begin() + static_cast<std::ptrdiff_t>(std::min(i, w.size())),
                                    w.begin() + static_cast<std::ptrdiff_t>(std::max(i, end)));
}

// punctuation inside the line, not at its end: "Forget the roof, nothing's happening up there" and «Вот это клатч, жесть!»
// are no teaching lines (2026-10-29, teach_corpus_check.py on 16458 lines)
bool InnerPunct(std::string_view line) {
    size_t end = line.size();
    while (end > 0 && std::string_view(" \t.!?").find(line[end - 1]) != std::string_view::npos) --end;
    return line.substr(0, end).find_first_of(",;:!?.") != std::string_view::npos;
}

// words no plain «это X» names a thing with: «это круто», "that's right", «это сюда»
bool PlainStop(const std::string& word) {
    static const std::unordered_set<std::string> kStop = {
        // ru
        "не", "да", "нет", "то", "так", "все", "оно", "он", "она", "они", "мы", "вы", "ты", "я", "хорошо", "плохо", "круто",
        "отлично", "правда", "неправда", "здорово", "классно", "сюда", "туда", "здесь", "там", "вон", "мне", "тебе", "что",
        "кто", "где", "как", "зачем", "почему", "еще", "уже", "тоже", "для", "очень", "просто", "ерунда", "бред", "ок",
        "окей", "норм", "нормально", "супер", "смешно", "странно", "мое", "твое", "его", "ее", "их", "наше", "ваше", "был",
        "была", "было", "будет", "надо", "нужно", "можно", "нельзя", "конец", "всё", "неправильно", "правильно", "жесть",
        "верно", "неверно", "ошибка", "тот", "та", "та самая", "оно самое", "он самый",
        // en
        "it", "that", "this", "not", "right", "wrong", "good", "great", "fine", "ok", "okay", "enough", "correct", "true",
        "cool", "nice", "bad", "all", "me", "you", "mine", "yours", "here", "there", "what", "why", "how", "where", "who",
        "awesome", "funny", "weird", "strange", "crazy", "so", "too", "very", "just", "amazing", "perfect", "it's", "is",
        "are", "was", "were", "going", "gonna", "done", "over", "it", "him", "her", "them", "us", "fun", "insane", "nuts",
        "negative", "affirmative", "one", "ones", "true", "false", "fine", "enough", "clear", "mistake", "lie",
        // es
        "no", "sí", "si", "eso", "esto", "bueno", "malo", "verdad", "así", "asi", "aquí", "aqui", "allí", "alli", "qué",
        "que", "genial", "bien", "mal", "todo", "nada", "mío", "mio", "tuyo", "increíble", "increible", "perfecto"};
    return kStop.count(word) > 0;
}

struct Colour {
    const char* id;
    std::vector<std::string> words;   // said as they are
    std::vector<std::string> stems;   // said with at most three more letters
};

const std::vector<Colour>& Colours() {
    static const std::vector<Colour> kColours = {
        {"red", {"red"}, {"красн", "roj"}},
        {"blue", {"blue", "azul", "azules"}, {"син"}},
        {"yellow", {"yellow"}, {"желт", "amarill"}},
        {"white", {"white"}, {"бел", "blanc"}},
        {"brown", {"brown"}, {"коричнев", "marr"}},
        {"green", {"green", "verde", "verdes"}, {"зелен"}},
        {"black", {"black"}, {"черн", "negr"}},
        {"grey", {"grey", "gray", "gris", "grises"}, {"сер"}},
        {"orange", {"orange"}, {"оранжев", "naranj"}},
        {"purple", {"purple", "violet"}, {"фиолетов", "morad", "violet"}},
        {"pink", {"pink", "rosa", "rosas"}, {"розов", "rosad"}},
        {"light_blue", {}, {"голуб", "celest"}},
    };
    return kColours;
}

bool StemForm(const std::string& said, const std::string& stem) {
    const std::u32string s = DecodeUtf8(said), t = DecodeUtf8(stem);
    return s.size() >= t.size() && s.size() <= t.size() + 3 && s.compare(0, t.size(), t) == 0;
}

std::string ColourOf(const std::string& word) {
    for (const Colour& c : Colours()) {
        if (std::find(c.words.begin(), c.words.end(), word) != c.words.end()) return c.id;
        for (const std::string& s : c.stems)
            if (StemForm(word, s)) return c.id;
    }
    return {};
}

}  // namespace

std::string MemoryNorm(std::string_view s) {
    std::u32string out;
    bool space = false;
    for (char32_t c : DecodeUtf8(s)) {
        if (c == U'’' || c == U'`') c = U'\'';
        c = Lower(c);
        if (WordChar(c)) {
            if (space && !out.empty()) out += U' ';
            space = false;
            out += c;
        } else {
            space = true;
        }
    }
    // an apostrophe at a word's edge is a quote, not part of it
    std::u32string clean;
    for (size_t i = 0; i < out.size(); ++i) {
        const bool edge = (i == 0 || out[i - 1] == U' ') || (i + 1 == out.size() || out[i + 1] == U' ');
        if (out[i] == U'\'' && edge) continue;
        clean += out[i];
    }
    std::u32string squeezed;
    for (char32_t c : clean) {
        if (c == U' ' && (squeezed.empty() || squeezed.back() == U' ')) continue;
        squeezed += c;
    }
    while (!squeezed.empty() && squeezed.back() == U' ') squeezed.pop_back();
    return EncodeUtf8(squeezed);
}

std::vector<SpanWord> SpanWords(std::string_view line) {
    std::vector<SpanWord> out;
    size_t i = 0;
    while (i < line.size()) {
        // one code point at a time: its bytes, and whether it is part of a word
        size_t n = 1;
        const unsigned char b = static_cast<unsigned char>(line[i]);
        if (b >= 0xF0) n = 4;
        else if (b >= 0xE0) n = 3;
        else if (b >= 0xC0) n = 2;
        n = std::min(n, line.size() - i);
        const std::u32string cp = DecodeUtf8(line.substr(i, n));
        char32_t c = cp.empty() ? U' ' : cp[0];
        if (c == U'’' || c == U'`') c = U'\'';
        if (WordChar(Lower(c))) {
            if (out.empty() || out.back().end != i) out.push_back({i, i, std::string()});
            out.back().end = i + n;
        }
        i += n;
    }
    for (SpanWord& w : out) {
        w.norm = MemoryNorm(line.substr(w.begin, w.end - w.begin));
        // the quote marks MemoryNorm drops at a word's edges are not part of the span either
        while (w.begin < w.end && (line[w.begin] == '\'' || line[w.begin] == '`')) ++w.begin;
        while (w.end > w.begin && (line[w.end - 1] == '\'' || line[w.end - 1] == '`')) --w.end;
    }
    out.erase(std::remove_if(out.begin(), out.end(), [](const SpanWord& w) { return w.norm.empty(); }), out.end());
    return out;
}

std::vector<std::string> MemoryWords(std::string_view norm) {
    std::vector<std::string> w;
    std::string cur;
    for (char c : norm) {
        if (c == ' ') {
            if (!cur.empty()) w.push_back(cur), cur.clear();
        } else {
            cur += c;
        }
    }
    if (!cur.empty()) w.push_back(cur);
    return w;
}

bool NearLine(const std::string& kept, const std::string& line) {
    if (kept == line) return true;
    const std::vector<std::string> a = MemoryWords(kept), b = MemoryWords(line);
    if (a.size() < 3 || b.size() < 3) return false;
    const std::unordered_set<std::string> sa(a.begin(), a.end()), sb(b.begin(), b.end());
    auto within = [](const std::unordered_set<std::string>& x, const std::unordered_set<std::string>& y) {
        for (const std::string& s : x)
            if (!y.count(s)) return false;
        return y.size() - x.size() <= 1;
    };
    return within(sa, sb) || within(sb, sa);
}

double TrigramJaccard(const std::string& a, const std::string& b) {
    auto grams = [](const std::string& s) {
        const std::u32string t = U"  " + DecodeUtf8(s) + U" ";
        std::unordered_set<std::u32string> g;
        for (size_t i = 0; i + 3 <= t.size(); ++i) g.insert(t.substr(i, 3));
        return g;
    };
    const auto x = grams(a), y = grams(b);
    size_t both = 0;
    for (const auto& g : x) both += y.count(g);
    const size_t all = x.size() + y.size() - both;
    return all ? static_cast<double>(both) / static_cast<double>(all) : 0.0;
}

bool WordForm(const std::string& said, const std::string& taught) {
    if (said == taught) return true;
    std::u32string t = DecodeUtf8(taught);
    if (t.size() < 4) return false;
    for (int k = 0; k < 2 && t.size() > 3 && Vowelish(t.back()); ++k) t.pop_back();
    return StemForm(said, EncodeUtf8(t));
}

bool FindWords(const std::vector<std::string>& line, const std::vector<std::string>& name, size_t from, size_t* begin, size_t* end) {
    if (name.empty()) return false;
    for (size_t i = from; i + name.size() <= line.size(); ++i) {
        bool all = true;
        for (size_t k = 0; k < name.size() && all; ++k) all = WordForm(line[i + k], name[k]);
        if (all) {
            *begin = i;
            *end = i + name.size();
            return true;
        }
    }
    return false;
}

const std::vector<std::string>& ColourIds() {
    static const std::vector<std::string> kIds = [] {
        std::vector<std::string> v;
        for (const Colour& c : Colours()) v.push_back(c.id);
        return v;
    }();
    return kIds;
}

std::vector<std::string> ColoursIn(const std::vector<std::string>& words) {
    std::vector<std::string> out;
    for (const std::string& w : words) {
        const std::string c = ColourOf(w);
        if (!c.empty() && std::find(out.begin(), out.end(), c) == out.end()) out.push_back(c);
    }
    return out;
}

const char* TeachKindName(TeachKind k) {
    switch (k) {
        case TeachKind::Meant: return "meant";
        case TeachKind::NotThat: return "not_that";
        case TeachKind::Name: return "name";
        case TeachKind::Colour: return "colour";
        case TeachKind::Forget: return "forget";
        case TeachKind::Means: return "means";
        case TeachKind::Pronounce: return "pronounce";
        case TeachKind::Speech: return "speech";
        case TeachKind::Behaviour: return "behaviour";
        default: return "none";
    }
}

namespace {

const std::u32string kRuVowels = U"аеёиоуыэюя";

// «когда я говорю бабах, это значит кидай гранату», «когда я скажу бабах — кидай гранату», «бабах значит кидай гранату»,
// "when I say boom, it means throw a grenade", "when I say boom, throw a grenade", «cuando digo bum, significa lanza una
// granada»: X (1..6 words) and Y (the rest of the line as said, 1+ words)
bool ReadMeans(std::string_view heard, const std::vector<std::string>& w, TeachLine* out) {
    const std::vector<SpanWord> sw = SpanWords(heard);
    if (sw.size() != w.size() || w.size() < 3) return false;
    // every time I say it: a rule; «когда скажу «го», ныряй за грузовик», "when I say go, ..." is one order on the signal (the
    // planner's), a rule only with "it means" in it (the corpus of 2026-10-30: 27 such lines)
    static const std::initializer_list<std::string_view> kHabit = {
        "когда я говорю", "когда говорю", "если я говорю", "если говорю", "каждый раз когда я говорю", "whenever i say",
        "every time i say", "cuando digo", "cuando yo digo", "cuando te digo", "si digo", "si yo digo", "si te digo",
        "cada vez que digo"};
    static const std::initializer_list<std::string_view> kOnce = {
        "когда я скажу", "когда скажу", "если я скажу", "если скажу", "when i say", "if i say", "cuando diga", "si digo que"};
    static const std::initializer_list<std::string_view> kMiddle = {
        "это значит", "это означает", "то это значит", "то это", "значит", "означает", "то есть", "это", "то", "it means",
        "that means", "means", "i mean", "then", "significa", "quiere decir", "eso significa", "es"};
    static const std::initializer_list<std::string_view> kStrong = {"значит", "означает", "это значит", "это означает",
                                                                     "то это значит", "то это означает", "то значит", "means",
                                                                     "it means", "that means", "significa", "quiere decir"};
    // a comma, a dash or a colon between two words as said
    auto stop_before = [&](size_t j) {
        for (size_t b = sw[j - 1].end; b < sw[j].begin; ++b)
            if (heard[b] == ',' || heard[b] == ':' || heard[b] == ';' || heard[b] == '-') return true;
        // a dash written as a UTF-8 en or em dash
        const std::string_view gap = heard.substr(sw[j - 1].end, sw[j].begin - sw[j - 1].end);
        return gap.find("\xE2\x80\x94") != std::string_view::npos || gap.find("\xE2\x80\x93") != std::string_view::npos;
    };
    size_t x0 = AfterAny(w, 0, kHabit);
    const bool lead = x0 != std::string::npos;
    if (!lead) {
        x0 = AfterAny(w, 0, kOnce);
        if (x0 == std::string::npos) x0 = 0;
    }
    for (size_t j = x0 + 1; j < w.size() && j <= x0 + 6; ++j) {
        size_t k = std::string::npos;
        const size_t m = AfterAny(w, j, lead ? kMiddle : kStrong);
        if (m != std::string::npos) k = m;
        else if (lead && stop_before(j)) k = j;
        if (k == std::string::npos) continue;
        if (lead && k == j) {   // after the comma: a marker may still come («когда я говорю бабах, это значит ...»)
            const size_t m2 = AfterAny(w, k, kMiddle);
            if (m2 != std::string::npos && m2 < w.size()) k = m2;
        }
        if (k >= w.size()) return false;
        // «это значит, что ты прав»: X must be words of its own, not a pronoun
        static const std::unordered_set<std::string> kPronoun = {"это", "то", "оно", "that", "this", "it", "eso", "esto"};
        if (!lead && (kPronoun.count(w[x0]) || j - x0 > 3)) return false;
        out->kind = TeachKind::Means;
        out->said = Join(w, x0, j);
        size_t end = heard.size();
        while (end > sw[k].begin && std::string_view(" \t.!?").find(heard[end - 1]) != std::string_view::npos) --end;
        out->rest = std::string(heard.substr(sw[k].begin, end - sw[k].begin));
        return true;
    }
    return false;
}

// «первый слог», «на последний», «на вторую гласную»: the syllable; 0: not one
int Ordinal(const std::string& x) {
    static const std::pair<const char*, int> kWords[] = {
        {"первый", 1}, {"первую", 1}, {"первом", 1}, {"второй", 2}, {"вторую", 2}, {"втором", 2}, {"третий", 3},
        {"третью", 3}, {"третьем", 3}, {"четвертый", 4}, {"четвертую", 4}, {"пятый", 5}, {"пятую", 5}, {"последний", -1},
        {"последнюю", -1}, {"последнем", -1}, {"предпоследний", -2}, {"предпоследнюю", -2}};
    for (const auto& p : kWords)
        if (x == p.first) return p.second;
    return 0;
}

bool ReadPronounce(const std::vector<std::string>& w, TeachLine* out) {
    static const std::unordered_set<std::string> kGlue = {"в", "слове", "слова", "у", "говори", "произноси", "скажи",
                                                          "слово", "надо", "нужно", "правильно", "с", "ударение", "ударением"};
    // the stress: «(в слове) X ударение на первый слог», «ударение в слове X на а», «X с ударением на о», «говори X с
    // ударением на последний слог»
    for (size_t i = 0; i < w.size(); ++i) {
        if (w[i] != "ударение" && w[i] != "ударением") continue;
        size_t na = std::string::npos;
        for (size_t j = 0; j < w.size(); ++j)
            if (w[j] == "на" && j > i) {
                na = j;
                break;
            }
        if (na == std::string::npos || na + 1 >= w.size()) return false;
        std::string word;   // the one word of the line before «на» that is no glue
        for (size_t j = 0; j < na; ++j)
            if (!kGlue.count(w[j])) {
                if (!word.empty()) return false;
                word = w[j];
            }
        if (word.empty()) return false;
        size_t t = na + 1;
        if (t < w.size() && (w[t] == "букву" || w[t] == "гласную" || w[t] == "звук")) ++t;
        if (t >= w.size()) return false;
        int stress = Ordinal(w[t]);
        std::string vowel;
        if (!stress) {
            const std::u32string v = DecodeUtf8(w[t]);
            if (v.size() != 1 || kRuVowels.find(v[0]) == std::u32string::npos) return false;
            vowel = w[t];
        }
        size_t end = t + 1;
        if (end < w.size() && (w[end] == "слог" || w[end] == "гласную" || w[end] == "букву")) ++end;
        if (end != w.size()) return false;
        if (StressedWord(word, stress, vowel).empty()) return false;
        out->kind = TeachKind::Pronounce;
        out->said = word;
        out->stress = stress;
        out->vowel = vowel;
        return true;
    }
    // «говори X как раньше», "say X like before": as the voice said it
    {
        const size_t k = AfterAny(w, 0, {"говори", "произноси", "say", "pronounce", "di", "pronuncia"});
        if (k != std::string::npos && k + 1 < w.size()) {
            const size_t e = AfterAny(w, k + 1, {"как раньше", "как было", "по старому", "like before", "as before",
                                                 "como antes"});
            if (e == w.size()) {
                out->kind = TeachKind::Pronounce;
                out->said = w[k];
                out->forget = true;
                return true;
            }
        }
    }
    // how it sounds: «говори X как Y», «произноси X как Y», «X произноси как Y», «говори не X, а Y», "pronounce X as Y", "say X
    // like Y", «pronuncia X como Y»: X one or two words, Y one to three
    auto take = [&](size_t x0, size_t x1, size_t y0) {
        if (x1 <= x0 || x1 - x0 > 2 || y0 >= w.size() || w.size() - y0 > 3) return false;
        out->kind = TeachKind::Pronounce;
        out->said = Join(w, x0, x1);
        out->rest = Join(w, y0, w.size());
        return out->said != out->rest;
    };
    static const std::initializer_list<std::string_view> kSay = {"говори", "произноси", "pronounce", "say", "pronuncia", "di"};
    static const std::initializer_list<std::string_view> kAs = {"как", "as", "like", "como"};
    size_t k = AfterAny(w, 0, kSay);
    if (k != std::string::npos && k < w.size()) {
        if (k < w.size() && (w[k] == "слово" || w[k] == "the" || w[k] == "word")) ++k;
        if (k < w.size() && w[k] == "не") {   // «говори не X, а Y»
            for (size_t j = k + 2; j < w.size(); ++j)
                if (w[j] == "а" && j + 1 < w.size()) return take(k + 1, j, j + 1);
            return false;
        }
        for (size_t j = k + 1; j < w.size(); ++j)
            if (AfterAny(w, j, kAs) == j + 1) return take(k, j, j + 1);
        return false;
    }
    // «Бадди говори как Бадди»: X first
    for (size_t j = 1; j + 2 < w.size() && j <= 2; ++j)
        if (AfterAny(w, j, {"произноси как", "говори как", "pronounce as", "say as", "pronuncia como"}) == j + 2) return take(0, j, j + 2);
    return false;
}

// a comma, a semicolon, a colon or a dash between the words j-1 and j as said (quotes round them aside)
bool StopBetween(std::string_view heard, const std::vector<SpanWord>& sw, size_t j) {
    if (j == 0 || j >= sw.size()) return false;
    const std::string_view gap = heard.substr(sw[j - 1].end, sw[j].begin - sw[j - 1].end);
    return gap.find_first_of(",;:-") != std::string_view::npos || gap.find("â") != std::string_view::npos ||
           gap.find("â") != std::string_view::npos;
}

// the words [a, b) of the line as said, without the quotes and stops round them
std::string SaidPart(std::string_view heard, const std::vector<SpanWord>& sw, size_t a, size_t b) {
    if (a >= b || b > sw.size()) return {};
    return std::string(heard.substr(sw[a].begin, sw[b - 1].end - sw[a].begin));
}

// «вместо «выдвигаюсь» говори «пошёл»», «не говори «выдвигаюсь», говори «пошёл»», «не говори «брат»», «говори «есть» вместо
// «понял»», «так не говори», «так не говори, говори «есть»», «говори как раньше»; "say Y instead of X", "instead of X say Y",
// "don't say X, say Y", "don't say that"; «en vez de X di Y», «no digas X, di Y», «no digas eso»
bool ReadSpeech(std::string_view heard, const std::vector<std::string>& w, TeachLine* out) {
    const std::vector<SpanWord> sw = SpanWords(heard);
    if (sw.size() != w.size() || w.empty()) return false;
    if (IsAny(Join(w, 0, w.size()), {"говори как раньше", "говори как обычно", "говори по старому", "talk like before",
                                     "speak like before", "talk like you used to", "habla como antes"})) {
        out->kind = TeachKind::Speech;
        out->forget = true;
        return true;
    }
    static const std::initializer_list<std::string_view> kSay = {"говори", "скажи", "say", "di"};
    static const std::initializer_list<std::string_view> kDont = {"не говори", "don't say", "dont say", "do not say", "no digas"};
    static const std::initializer_list<std::string_view> kInstead = {"вместо", "instead of", "en vez de", "en lugar de"};
    static const std::initializer_list<std::string_view> kThat = {"так", "вот так", "это", "вот это", "that", "this", "eso",
                                                                   "that like that", "it like that", "así"};
    auto ok = [&](size_t a, size_t b, size_t most) { return a < b && b - a <= most; };
    auto set = [&](size_t xa, size_t xb, size_t ya, size_t yb) {
        out->kind = TeachKind::Speech;
        out->said = xa < xb ? Join(w, xa, xb) : std::string();
        out->rest = ya < yb ? SaidPart(heard, sw, ya, yb) : std::string();
        return true;
    };
    // «вместо X говори Y», "instead of X say Y"
    size_t k = AfterAny(w, 0, kInstead);
    if (k != std::string::npos) {
        for (size_t j = k + 1; j < w.size(); ++j) {
            const size_t m = AfterAny(w, j, kSay);
            if (m != std::string::npos && m < w.size() && ok(k, j, 8) && ok(m, w.size(), 10)) return set(k, j, m, w.size());
        }
        return false;
    }
    // «говори Y вместо X», «говори Y, а не X», "say Y instead of X"
    k = AfterAny(w, 0, kSay);
    if (k != std::string::npos && k < w.size()) {
        for (size_t j = k + 1; j < w.size(); ++j) {
            const size_t m = AfterAny(w, j, kInstead);
            if (m != std::string::npos && m < w.size() && ok(k, j, 10) && ok(m, w.size(), 8)) return set(m, w.size(), k, j);
            const size_t n = AfterAny(w, j, {"а не", "and not", "not"});
            if (n != std::string::npos && n < w.size() && ok(k, j, 10) && ok(n, w.size(), 8) && StopBetween(heard, sw, j))
                return set(n, w.size(), k, j);
        }
        return false;
    }
    // «так не говори», «так не говори, говори Y», «не говори так»
    size_t a = AfterAny(w, 0, kThat);
    if (a != std::string::npos) {
        const size_t d = AfterAny(w, a, kDont);
        if (d != std::string::npos) {
            if (d == w.size()) return set(0, 0, 0, 0);
            const size_t m = AfterAny(w, d, kSay);
            if (m != std::string::npos && ok(m, w.size(), 10)) return set(0, 0, m, w.size());
            const size_t m2 = AfterAny(w, d, {"а", "а говори", "лучше", "лучше говори"});
            if (m2 != std::string::npos && ok(m2, w.size(), 10)) return set(0, 0, m2, w.size());
        }
        return false;
    }
    // «не говори X», «не говори X, говори Y», «не говори X, а Y», «не говори так», "don't say X, say Y", «no digas eso»
    const size_t d = AfterAny(w, 0, kDont);
    if (d == std::string::npos || d >= w.size()) return false;
    if (AfterAny(w, d, kThat) == w.size()) return set(0, 0, 0, 0);
    for (size_t j = d + 1; j < w.size(); ++j) {
        const size_t m = AfterAny(w, j, {"говори", "а говори", "а", "say", "but say", "di", "sino", "sino di"});
        // the second part starts after a stop as said: «не говори выдвигаюсь, говори пошёл»
        if (m != std::string::npos && m < w.size() && StopBetween(heard, sw, j) && ok(d, j, 8) && ok(m, w.size(), 10))
            return set(d, j, m, w.size());
    }
    // «не говори брат»: say nothing for it; one to four words, never an order's («не говори ничего» is no rule)
    static const std::unordered_set<std::string> kNot = {"ничего", "ни", "слова", "anything", "a", "word", "nada"};
    if (w.size() - d > 4 || kNot.count(w[d])) return false;
    return set(d, w.size(), 0, 0);
}

}  // namespace

bool ReadNumber(const std::vector<std::string>& w, size_t i, double* value, size_t* next) {
    if (i >= w.size()) return false;
    static const std::pair<const char*, int> kWords[] = {
        {"один", 1}, {"одного", 1}, {"одном", 1}, {"одну", 1}, {"одна", 1}, {"два", 2}, {"две", 2}, {"двух", 2}, {"двум", 2},
        {"три", 3}, {"трех", 3}, {"трем", 3}, {"четыре", 4}, {"четырех", 4}, {"пять", 5}, {"пяти", 5}, {"шесть", 6}, {"шести", 6},
        {"семь", 7}, {"семи", 7}, {"восемь", 8}, {"восьми", 8}, {"девять", 9}, {"девяти", 9}, {"десять", 10}, {"десяти", 10},
        {"пятнадцать", 15}, {"пятнадцати", 15}, {"двадцать", 20}, {"двадцати", 20}, {"тридцать", 30}, {"тридцати", 30},
        {"сорок", 40}, {"сорока", 40}, {"пятьдесят", 50}, {"пятидесяти", 50}, {"сто", 100},
        {"one", 1}, {"two", 2}, {"three", 3}, {"four", 4}, {"five", 5}, {"six", 6}, {"seven", 7}, {"eight", 8}, {"nine", 9},
        {"ten", 10}, {"fifteen", 15}, {"twenty", 20}, {"thirty", 30}, {"forty", 40}, {"fifty", 50}, {"a", 1},
        {"uno", 1}, {"una", 1}, {"un", 1}, {"dos", 2}, {"tres", 3}, {"cuatro", 4}, {"cinco", 5}, {"seis", 6}, {"siete", 7},
        {"ocho", 8}, {"nueve", 9}, {"diez", 10}, {"quince", 15}, {"veinte", 20}, {"treinta", 30}, {"cuarenta", 40},
        {"cincuenta", 50}};
    auto word = [&](const std::string& x) {
        for (const auto& p : kWords)
            if (x == p.first) return p.second;
        return -1;
    };
    const std::string& t = w[i];
    if (t == "полтора" || t == "полутора") return *value = 1.5, *next = i + 1, true;
    if (!t.empty() && t[0] >= '0' && t[0] <= '9') {   // MemoryNorm keeps digits; "2,5" comes as two words
        double v = 0;
        size_t j = i + 1;
        for (char c : t) {
            if (c < '0' || c > '9') return false;
            v = v * 10 + (c - '0');
        }
        return *value = v, *next = j, true;
    }
    const int v = word(t);
    if (v < 0) return false;
    size_t j = i + 1;
    double total = v;
    if (v >= 20 && v % 10 == 0 && j < w.size()) {   // «двадцать пять», "twenty five", «veinte y cinco»
        size_t u = j;
        if (w[u] == "y" || w[u] == "and") ++u;
        const int ones = u < w.size() ? word(w[u]) : -1;
        if (ones > 0 && ones < 10) total += ones, j = u + 1;
    }
    *value = total;
    *next = j;
    return true;
}

namespace {

bool IsMetres(const std::string& x) {
    static const std::unordered_set<std::string> kM = {"метр", "метра", "метров", "метрах", "метре", "метрами", "м", "meter",
                                                       "meters", "metre", "metres", "m", "metro", "metros"};
    return kM.count(x) > 0;
}

// a number of metres anywhere in the line («в трёх метрах», "3 meters", «a tres metros»); 0: none
double MetresIn(const std::vector<std::string>& w) {
    for (size_t i = 0; i < w.size(); ++i) {
        double v = 0;
        size_t n = 0;
        if (ReadNumber(w, i, &v, &n) && n < w.size() && IsMetres(w[n]) && v > 0) return v;
    }
    return 0;
}

bool Has(const std::vector<std::string>& w, std::initializer_list<std::string_view> phrases) {
    for (size_t i = 0; i < w.size(); ++i)
        if (AfterAny(w, i, phrases) != std::string::npos) return true;
    return false;
}

bool ReadBehaviour(const std::vector<std::string>& w, TeachLine* out) {
    const std::string line = Join(w, 0, w.size());
    auto set = [&](const char* setting, double value, double scale) {
        out->kind = TeachKind::Behaviour;
        out->setting = setting;
        out->value = value;
        out->scale = scale;
        return true;
    };
    if (IsAny(line, {"веди себя как раньше", "веди себя как обычно", "act like before", "behave like before", "compórtate como antes",
                     "comportate como antes"})) {
        out->kind = TeachKind::Behaviour;
        out->forget = true;
        return true;
    }
    // the voice: faster, slower, as usual
    if (IsAny(line, {"говори быстрее", "говори побыстрее", "talk faster", "speak faster", "habla más rápido", "habla mas rapido"}))
        return set("voice_speed", 0, 1.25);
    if (IsAny(line, {"говори медленнее", "говори помедленнее", "talk slower", "speak slower", "talk more slowly", "speak more slowly",
                     "habla más despacio", "habla mas despacio", "habla más lento", "habla mas lento"}))
        return set("voice_speed", 0, 0.8);
    if (IsAny(line, {"говори с обычной скоростью", "talk at normal speed", "speak at normal speed", "habla a velocidad normal"}))
        return set("voice_speed", 1.0, 0);
    // shooting on the player's command only, or on its own
    if (Has(w, {"без команды не стреляй", "без моей команды не стреляй", "не стреляй без команды", "не стреляй без моей команды",
                "не стреляй без приказа", "стреляй только по команде", "стреляй только по моей команде", "стреляй только когда я скажу",
                "only shoot on my command", "only fire on my command", "only shoot when i say", "only fire when i say",
                "don't shoot without my command", "dont shoot without my command", "don't shoot unless i say", "dont shoot unless i say",
                "dispara solo a mi orden", "dispara solo cuando yo diga", "no dispares sin mi orden"}))
        return set("fire_on_command", 1, 0);
    if (Has(w, {"стреляй сам", "можешь стрелять сам", "стреляй по своему усмотрению", "стреляй когда хочешь", "стреляй без команды",
                "shoot on your own", "you can shoot on your own", "shoot whenever you want", "dispara por tu cuenta",
                "puedes disparar por tu cuenta"}))
        return set("fire_on_command", 0, 0);
    // opening fire within so many metres
    if (Has(w, {"открывай огонь с", "открывай огонь только с", "стреляй только с", "стреляй с", "стреляй только ближе", "стреляй ближе",
                "open fire within", "open fire at", "only open fire within", "shoot within", "only shoot within", "engage within",
                "abre fuego a", "dispara a menos de", "dispara solo a menos de"})) {
        const double m = MetresIn(w);
        return m > 0 && set("engage_m", m, 0);
    }
    // how near it keeps: so many metres, nearer, farther
    if (Has(w, {"держись ближе", "держись поближе", "будь поближе", "держись ко мне поближе", "держись ко мне ближе", "stay closer",
                "keep closer", "stay nearer", "quédate más cerca", "quedate mas cerca", "mantente más cerca", "mantente mas cerca"}) &&
        MetresIn(w) == 0)
        return set("follow_m", 0, 0.6);
    if (Has(w, {"держись дальше", "держись подальше", "держись от меня подальше", "держись от меня дальше", "не подходи так близко",
                "не лезь так близко", "keep your distance", "stay further away", "stay farther away", "keep further away",
                "mantén la distancia", "manten la distancia", "quédate más lejos", "quedate mas lejos"}) &&
        MetresIn(w) == 0)
        return set("follow_m", 0, 1.5);
    if (Has(w, {"держись в", "держись на", "держись от меня в", "держись от меня на", "будь в", "находись в", "не подходи ближе",
                "не подходи ко мне ближе", "stay", "keep", "don't come closer than", "dont come closer than", "mantente a", "quédate a",
                "quedate a", "no te acerques a menos de"}) &&
        Has(w, {"от меня", "метрах", "метров", "метра", "метре", "from me", "away", "meters", "metres", "metros", "de mí", "de mi"})) {
        const double m = MetresIn(w);
        if (m > 0 && (Has(w, {"держись", "будь", "находись", "не подходи", "from me", "away", "closer than", "mantente", "quédate",
                              "quedate", "no te acerques"})))
            return set("follow_m", m, 0);
    }
    return false;
}

}  // namespace

std::string StressedWord(const std::string& word, int syllable, const std::string& vowel) {
    const std::u32string u = DecodeUtf8(word);
    std::vector<size_t> at;   // where the vowels are
    for (size_t i = 0; i < u.size(); ++i)
        if (kRuVowels.find(u[i]) != std::u32string::npos) at.push_back(i);
    size_t pick = std::string::npos;
    if (!vowel.empty()) {
        const std::u32string v = DecodeUtf8(vowel);
        for (size_t i : at)
            if (v.size() == 1 && (u[i] == v[0] || (v[0] == U'е' && u[i] == U'ё'))) {
                pick = i;
                break;
            }
    } else if (syllable > 0 && static_cast<size_t>(syllable) <= at.size()) {
        pick = at[static_cast<size_t>(syllable) - 1];
    } else if (syllable < 0 && static_cast<size_t>(-syllable) <= at.size()) {
        pick = at[at.size() - static_cast<size_t>(-syllable)];
    }
    if (pick == std::string::npos) return {};
    std::u32string out = u.substr(0, pick + 1) + U"\u0301" + u.substr(pick + 1);
    return EncodeUtf8(out);
}

static TeachLine ReadTeachOne(std::string_view heard, const std::string& lang) {
    (void)lang;   // the rules of the three languages never meet in one line: all of them are read
    TeachLine out;
    const std::string norm = MemoryNorm(heard);
    const std::vector<std::string> w = MemoryWords(norm);
    if (w.empty()) return out;

    // "not that": the whole line
    if (IsAny(norm, {"не то", "нет не то", "это не то", "не так", "нет не так", "ты не понял", "ты меня не понял",
                     "ты не так понял", "ты неправильно понял", "ты меня неправильно понял", "не то сделал",
                     "ты не то сделал", "неправильно", "нет неправильно", "не то ты сделал", "я не это имел в виду",
                     "я не то имел в виду", "not that", "no not that", "wrong", "that's wrong", "thats wrong", "that is wrong",
                     "you got it wrong", "you got that wrong", "you misunderstood", "you misunderstood me", "you misheard",
                     "you misheard me", "that's not what i said", "thats not what i said", "that's not what i meant",
                     "thats not what i meant", "not what i said", "not what i meant", "no that's not it", "no thats not it",
                     "eso no", "no eso no", "no es eso", "eso no es", "te equivocaste", "no me entendiste",
                     "me entendiste mal", "no es lo que dije", "no es lo que quise decir", "eso no es lo que dije"})) {
        out.kind = TeachKind::NotThat;
        return out;
    }

    // «когда я говорю X, это значит Y»: a line of the player's own for one the bot understands (2026-10-30)
    if (ReadMeans(heard, w, &out)) return out;
    // «в слове замок ударение на первый слог», «говори Buddy как Бадди»: how the voice says a word
    if (ReadPronounce(w, &out)) return out;
    // «вместо «выдвигаюсь» говори «пошёл»»: the bot's own lines
    if (ReadSpeech(heard, w, &out)) return out;
    // «держись в трёх метрах», «стреляй только по моей команде»: the bot's settings
    if (ReadBehaviour(w, &out)) return out;

    // "I meant ...": what the line before meant
    {
        const size_t lead = SkipLead(w);
        const size_t k = AfterAny(w, lead, {
            "я имел в виду", "я имела в виду", "имел в виду", "имела в виду", "я сказал", "я сказала", "я говорю",
            "я говорил", "я говорила", "я хотел сказать", "я хотела сказать", "хотел сказать", "я просил", "я просила",
            "i meant", "i said", "what i meant was", "what i said was", "i wanted to say", "i told you to", "i asked you to",
            "quise decir", "quería decir", "queria decir", "dije", "te dije", "yo dije", "lo que dije fue",
            "lo que quise decir es", "lo que quise decir era"});
        if (k != std::string::npos && k < w.size()) {
            out.kind = TeachKind::Meant;
            out.rest = Join(w, k, w.size());
            return out;
        }
    }

    // "forget ...": a name or a line kept
    {
        const size_t gaze = AfterAny(w, 0, {
            "забудь это название", "забудь название", "забудь имя", "забудь это имя", "забудь как это называется",
            "забудь его название", "забудь ее название", "forget the name", "forget this name", "forget its name",
            "forget that name", "forget what this is called", "forget what it's called", "forget what its called",
            "olvida el nombre", "olvida este nombre", "olvida su nombre"});
        if (gaze != std::string::npos && gaze == w.size()) {
            out.kind = TeachKind::Forget;
            return out;
        }
        const size_t k = AfterAny(w, 0, {"забудь", "забудь про", "забудь что", "забудь слово", "forget", "forget about",
                                         "forget the word", "olvida", "olvídate de", "olvidate de", "olvida la palabra"});
        // a name or a short line, the whole line ("forget the workbench", «забудь банан»): "Forget the roof, get down to the
        // basement", «olvida eso, espera», "forget the pistol just start shooting" are a change of plan
        static const std::unordered_set<std::string> kNotAName = {"it", "that", "this", "what", "everything", "это", "что",
                                                                  "всё", "все", "об", "eso", "esto", "lo", "todo", "que"};
        if (k != std::string::npos && k < w.size() && !InnerPunct(heard)) {
            const std::vector<std::string> what = NameWords(w, k);
            const std::string rest = Join(what, 0, what.size());
            if (!rest.empty() && what.size() <= 3 && !kNotAName.count(what[0])) {
                out.kind = TeachKind::Forget;
                out.rest = rest;
                return out;
            }
        }
    }

    // a colour of the thing under the crosshair: «этот ящик зелёный», "this box is green", «es verde»
    {
        static const std::unordered_set<std::string> kFirst = {"это", "этот", "эта", "эти", "он", "она", "оно", "вот",
                                                               "this", "that", "it", "it's", "its", "that's", "thats",
                                                               "esto", "esta", "este", "eso", "esa", "ese", "es"};
        static const std::unordered_set<std::string> kNot = {"не", "нет", "not", "no", "isn't", "isnt", "nunca"};
        const bool negated = std::any_of(w.begin(), w.end(), [](const std::string& x) { return kNot.count(x) > 0; });
        if (w.size() <= 5 && kFirst.count(w[0]) && !negated) {
            const std::vector<std::string> c = ColoursIn(w);
            if (c.size() == 1) {
                out.kind = TeachKind::Colour;
                out.colour = c[0];
                // «это красный фонарь», "it's a red lantern": what the thing is; «этот ящик зелёный», "it's green": said of it
                const size_t frame = AfterAny(w, 0, {"это", "вот", "вот это", "it's", "its", "it is", "that's", "thats", "that is",
                                                     "this is", "es", "eso es", "esto es"});
                if (frame != std::string::npos) {
                    static const std::unordered_set<std::string> kGlue = {"a", "an", "the", "un", "una", "el", "la", "is", "es"};
                    for (size_t i = frame; i < w.size(); ++i)
                        if (!kGlue.count(w[i]) && ColourOf(w[i]).empty() && !GenericThingWord(w[i])) out.noun.push_back(w[i]);
                    out.attributive = !out.noun.empty();
                    // the name it would be: what is said after the frame («красный фонарь»)
                    const std::vector<std::string> what = NameWords(w, frame);
                    if (out.attributive) out.rest = Join(what, 0, what.size());
                }
                return out;
            }
        }
    }

    // a name of the thing under the crosshair
    auto name_from = [&](size_t k, bool plain) {
        if (k == std::string::npos || k >= w.size()) return false;
        const std::vector<std::string> name = NameWords(w, k);
        if (name.empty() || name.size() > 3) return false;
        if (plain) {
            if (InnerPunct(heard) || heard.find('!') != std::string_view::npos) return false;   // «Вот это клатч, жесть!»
            for (const std::string& x : name)
                if (PlainStop(x)) return false;
        }
        out.kind = TeachKind::Name;
        out.rest = Join(name, 0, name.size());
        out.plain = plain;
        return true;
    };
    if (name_from(AfterAny(w, 0, {
            "назови это", "назови его", "назови ее", "назовем это", "это называется", "это будет", "пусть это будет",
            // the owner's own (2026-10-30): «Называй теперь это фонарь», «Называй это теперь камень», «Это называется фонарь»
            "называй это", "называй его", "называй ее", "называй теперь это", "теперь называй это", "назови теперь это",
            "теперь назови это", "зови это", "зови его", "зови ее", "теперь это называется", "это теперь называется",
            "теперь зови это",
            "пусть это называется", "запомни это", "запомни это называется", "запомни это будет", "запомни что это",
            "его зовут", "ее зовут", "call this", "call it", "call that", "name this", "name it", "this is called",
            "that is called", "it's called", "its called", "this one is called", "let's call this", "lets call this",
            "let's call it", "lets call it", "remember this is", "remember this as", "remember that this is", "llámalo",
            "llamalo", "llámala", "llamala", "esto se llama", "eso se llama", "se llama", "llamemos esto",
            "llamemos a esto", "recuerda que esto es", "recuerda esto como"}), false))
        return out;
    if (name_from(AfterAny(w, 0, {"это", "вот это", "это у нас", "this is", "that is", "that's", "thats", "this here is",
                                  "this one is", "esto es", "eso es", "este es", "esta es", "ese es", "esa es"}), true))
        return out;
    return TeachLine();
}

// A line of two sentences or parts or more that is no teaching line as a whole: a name said in one of them by its own words («Это
// называется фонарь. Называй теперь это фонарь.», the owner, 2026-10-30). Only an explicit name counts there, and every sentence
// that gives one gives the same: a plain «это X» in a longer line is talk
TeachLine ReadTeach(std::string_view heard, const std::string& lang) {
    TeachLine whole = ReadTeachOne(heard, lang);
    if (whole.kind != TeachKind::None) return whole;
    std::vector<std::string_view> parts;
    size_t b = 0;
    for (size_t j = 0; j <= heard.size(); ++j)
        if (j == heard.size() || heard[j] == '.' || heard[j] == '!' || heard[j] == '?' || heard[j] == ',' || heard[j] == ';') {
            if (j > b) parts.push_back(heard.substr(b, j - b));
            b = j + 1;
        }
    if (parts.size() < 2) return whole;
    TeachLine found;
    for (std::string_view part : parts) {
        const TeachLine t = ReadTeachOne(part, lang);
        if (t.kind != TeachKind::Name || t.plain) continue;
        // "scrap the rappel, call it off", "call it in": "call it" in a part of a line is the radio's, no name
        if (MemoryNorm(part).rfind("call ", 0) == 0) continue;
        bool stop = false;
        for (const std::string& x : MemoryWords(t.rest)) stop = stop || PlainStop(x);
        if (stop) continue;
        if (found.kind == TeachKind::Name && found.rest != t.rest) return TeachLine();
        found = t;
    }
    return found;
}

namespace {

// drops «брат», "bro", «hermano», «пожалуйста», "please" from a short answer: «да, брат» is «да»
std::vector<std::string> WithoutFiller(const std::vector<std::string>& w) {
    static const std::unordered_set<std::string> kFiller = {"брат", "братан", "братишка", "bro", "brother", "dude",
                                                            "hermano", "пожалуйста", "please", "por", "favor"};
    std::vector<std::string> out;
    for (const std::string& x : w)
        if (!kFiller.count(x)) out.push_back(x);
    return out;
}

// "No, ..." / «No, ...»: the line's first word is "no" and a comma or a stop follows it as said
bool NoThenStop(std::string_view heard) {
    const std::vector<SpanWord> sw = SpanWords(heard);
    if (sw.empty() || sw[0].norm != "no") return false;
    for (size_t j = sw[0].end; j < heard.size(); ++j) {
        if (heard[j] == ' ') continue;
        return std::string_view(",.!;:").find(heard[j]) != std::string_view::npos;
    }
    return false;
}

}  // namespace

static ThingWords ReadThingWordsOne(std::string_view heard, bool bare) {
    ThingWords out;
    const std::vector<std::string> w = WithoutFiller(MemoryWords(MemoryNorm(heard)));
    size_t i = 0;
    // "no", «нет», «не то», "wrong" in front
    for (int step = 0; step < 3 && i < w.size(); ++step) {
        static const std::unordered_set<std::string> kNo = {"нет", "неа", "no", "nope", "nah"};
        if (kNo.count(w[i])) {
            // «no es una mesa»: Spanish "no" before "es" is "it is not", the line's own words; «No, es una mesa» is "no"
            if (i == 0 && w[i] == "no" && i + 1 < w.size() && w[i + 1] == "es" && i + 2 < w.size() && w[i + 2] != "eso" &&
                !NoThenStop(heard))
                break;
            out.denied = true;
            ++i;
            continue;
        }
        if (w[i] == "ну") {
            ++i;
            continue;
        }
        // «Не это белый стол.»: the recognizer's «нет, это белый стол» (the owner's log, 2026-10-30)
        if (w[i] == "не" && i + 1 < w.size() && (w[i + 1] == "это" || w[i + 1] == "он" || w[i + 1] == "она" || w[i + 1] == "оно") &&
            i + 2 < w.size()) {
            out.denied = true;
            ++i;
            continue;
        }
        const size_t k = AfterAny(w, i, {"не то", "не так", "неправильно", "неверно", "not that", "wrong", "that's wrong",
                                         "thats wrong", "eso no", "no es eso"});
        if (k == std::string::npos) break;
        out.denied = true;
        i = k;
    }
    if (i >= w.size()) return out;
    static const std::initializer_list<std::string_view> kFrames = {
        "это", "вот это", "это у нас", "он", "она", "оно", "it's", "its", "it is", "that's", "thats", "that is", "this is",
        "es", "eso es", "esto es", "no es"};
    size_t k = AfterAny(w, i, kFrames);
    // «нет, он жёлтый»: "he" / "she" / "it" said of the thing only after "no" («она красивая» is no answer)
    if (k != std::string::npos && !out.denied && !bare && (w[i] == "он" || w[i] == "она" || w[i] == "оно") &&
        ColoursIn(std::vector<std::string>(w.begin() + static_cast<std::ptrdiff_t>(k), w.end())).empty())
        return out;
    std::vector<std::string> what;
    if (k != std::string::npos) {
        // «это не стол, а верстак», "it's not a table, it's a workbench", «no es una mesa, es un taller»: the words after
        // the second part's start
        const bool spanish_not = After(w, i, "no es") != std::string::npos;
        if (spanish_not || (k < w.size() && (w[k] == "не" || w[k] == "not"))) {
            size_t from = std::string::npos;
            for (size_t j = k + 1; j < w.size(); ++j) {
                const size_t m = AfterAny(w, j, {"а", "а это", "это", "но", "it's", "its", "it is", "but", "but it's",
                                                 "es", "sino", "sino un", "sino una"});
                if (m != std::string::npos) from = m;
            }
            if (from == std::string::npos || from >= w.size()) return out;   // «это не важно»: no thing said
            what.assign(w.begin() + static_cast<std::ptrdiff_t>(from), w.end());
        } else {
            what.assign(w.begin() + static_cast<std::ptrdiff_t>(k), w.end());
        }
    } else if (bare) {
        what.assign(w.begin() + static_cast<std::ptrdiff_t>(i), w.end());
    } else {
        return out;
    }
    if (!what.empty() && what[0] == "а") what.erase(what.begin());   // «не это, а верстак»
    what = NameWords(what, 0);
    if (what.empty() || what.size() > 3) return out;
    for (const std::string& x : what)
        if (PlainStop(x) && ColourOf(x).empty()) return out;
    out.ok = true;
    out.words = std::move(what);
    return out;
}

// ReadThingWords, and with a short lead before the last comma read past it: «Ты что, не понимаешь, это камень.» (the owner,
// 2026-10-30) is «это камень», said against the bot's answer
ThingWords ReadThingWords(std::string_view heard, bool bare) {
    ThingWords out = ReadThingWordsOne(heard, bare);
    if (out.ok || bare) return out;
    const size_t comma = heard.rfind(',');
    if (comma == std::string_view::npos || comma + 1 >= heard.size()) return out;
    if (MemoryWords(MemoryNorm(heard.substr(0, comma))).size() > 4) return out;
    ThingWords tail = ReadThingWordsOne(heard.substr(comma + 1), false);
    if (!tail.ok) return out;
    tail.denied = true;   // said against the answer
    return tail;
}

bool BareDenial(std::string_view heard) {
    const std::vector<std::string> w = WithoutFiller(MemoryWords(MemoryNorm(heard)));
    std::string line;
    for (const std::string& x : w) line += (line.empty() ? "" : " ") + x;
    return IsAny(line, {"нет", "неа", "нет нет", "не то", "нет не то", "не так", "нет не так", "неправильно",
                        "нет неправильно", "неверно", "нет неверно", "ошибаешься", "ты ошибаешься", "нет ты ошибаешься",
                        "это не то", "не это", "no", "nope", "nah", "no no", "wrong", "that's wrong", "thats wrong",
                        "no that's wrong", "no thats wrong", "not that", "no not that", "you're wrong", "youre wrong",
                        "no you're wrong", "incorrect", "not quite", "eso no", "no es eso", "no no es eso", "incorrecto",
                        "te equivocas", "no te equivocas", "mal", "está mal", "esta mal"});
}

bool ColourQuestion(std::string_view heard, std::vector<std::string>* rest) {
    const std::vector<std::string> w = WithoutFiller(MemoryWords(MemoryNorm(heard)));
    if (w.empty() || w.size() > 9) return false;
    static const std::unordered_set<std::string> kColourWord = {"цвета", "цвет", "цветом", "colour", "color", "colours", "colors"};
    static const std::unordered_set<std::string> kAsk = {"какого", "какой", "каким", "каков", "какая", "какое", "what", "which",
                                                         "what's", "whats", "qué", "que", "cuál", "cual"};
    bool colour = false, ask = false;
    for (const std::string& x : w) {
        colour = colour || kColourWord.count(x) > 0;
        ask = ask || kAsk.count(x) > 0;
    }
    // «что за цвет», «что это за цвет»
    ask = ask || (std::find(w.begin(), w.end(), "что") != w.end() && std::find(w.begin(), w.end(), "за") != w.end());
    if (!colour || !ask) return false;
    static const std::unordered_set<std::string> kSkip = {
        "какого", "какой", "каким", "каков", "какая", "какое", "цвета", "цвет", "цветом", "что", "за", "это", "этот", "эта",
        "эти", "он", "она", "оно", "у", "него", "нее", "неё", "этого", "этой", "а", "и", "ну", "скажи", "мне", "ты", "знаешь",
        "вот", "тот", "та", "то", "там", "тут", "what", "which", "what's", "whats", "colour", "color", "colours", "colors",
        "is", "it", "this", "that", "the", "of", "are", "its", "it's", "tell", "me", "do", "you", "know", "qué", "que", "de",
        "color", "es", "esto", "eso", "este", "esta", "ese", "esa", "el", "la", "tiene", "cuál", "cual", "dime", "sabes", "y"};
    if (rest) {
        rest->clear();
        for (const std::string& x : w)
            if (!kSkip.count(x)) rest->push_back(x);
    }
    return true;
}

int YesNo(std::string_view heard) {
    const std::vector<std::string> w = WithoutFiller(MemoryWords(MemoryNorm(heard)));
    if (w.empty()) return 0;
    std::string line;
    for (const std::string& x : w) line += (line.empty() ? "" : " ") + x;
    if (IsAny(line, {"да", "да да", "ага", "угу", "давай", "конечно", "да конечно", "запомни", "да запомни", "запоминай",
                     "точно", "верно", "именно", "ладно", "хорошо", "ок", "окей", "да давай", "yes", "yeah", "yep", "yup",
                     "sure", "ok", "okay", "right", "correct", "yes please", "do it", "remember it", "yes remember it",
                     "yeah remember it", "of course", "sí", "si", "claro", "sí claro", "si claro", "vale", "dale",
                     "correcto", "exacto", "recuérdalo", "recuerdalo", "sí recuérdalo", "si recuerdalo"}))
        return 1;
    static const std::unordered_set<std::string> kNo = {"нет", "неа", "не", "no", "nope", "nah", "don't", "dont"};
    if (w.size() <= 4 && kNo.count(w[0])) return -1;
    return 0;
}

bool GenericThingWord(const std::string& word) {
    static const std::unordered_set<std::string> kGeneric = {"штука", "штуку", "штуки", "штуковина", "штуковину", "вещь",
                                                             "вещица", "предмет", "объект", "thing", "one", "object", "item",
                                                             "stuff", "cosa", "objeto"};
    return kGeneric.count(word) > 0;
}

std::string ColourAdjective(const std::string& id, const std::string& lang, char gender, bool acc) {
    if (lang == "ru") {
        // stem, and its endings: 'h' hard (-ый), 's' soft (-ий), 'o' stressed (-ой)
        static const std::vector<std::pair<std::string, std::pair<std::string, char>>> kRu = {
            {"red", {"красн", 'h'}}, {"blue", {"син", 's'}}, {"yellow", {"жёлт", 'h'}}, {"white", {"бел", 'h'}},
            {"brown", {"коричнев", 'h'}}, {"green", {"зелён", 'h'}}, {"black", {"чёрн", 'h'}}, {"grey", {"сер", 'h'}},
            {"orange", {"оранжев", 'h'}}, {"purple", {"фиолетов", 'h'}}, {"pink", {"розов", 'h'}},
            {"light_blue", {"голуб", 'o'}}};
        for (const auto& c : kRu) {
            if (c.first != id) continue;
            const std::string& stem = c.second.first;
            const bool soft = c.second.second == 's';
            switch (gender) {
                case 'f': return stem + (soft ? (acc ? "юю" : "яя") : (acc ? "ую" : "ая"));
                case 'n': return stem + (soft ? "ее" : "ое");
                case 'p': return stem + (soft ? "ие" : "ые");
                default: return stem + (soft ? "ий" : c.second.second == 'o' ? "ой" : "ый");
            }
        }
        return {};
    }
    if (lang == "es") {
        static const std::vector<std::pair<std::string, std::pair<std::string, std::string>>> kEs = {
            {"red", {"rojo", "roja"}}, {"blue", {"azul", "azul"}}, {"yellow", {"amarillo", "amarilla"}},
            {"white", {"blanco", "blanca"}}, {"brown", {"marrón", "marrón"}}, {"green", {"verde", "verde"}},
            {"black", {"negro", "negra"}}, {"grey", {"gris", "gris"}}, {"orange", {"naranja", "naranja"}},
            {"purple", {"morado", "morada"}}, {"pink", {"rosa", "rosa"}}, {"light_blue", {"celeste", "celeste"}}};
        for (const auto& c : kEs)
            if (c.first == id) return gender == 'f' ? c.second.second : c.second.first;
        return {};
    }
    if (std::find(ColourIds().begin(), ColourIds().end(), id) == ColourIds().end()) return {};
    std::string s = id;
    std::replace(s.begin(), s.end(), '_', ' ');
    return s;
}

}  // namespace coop
