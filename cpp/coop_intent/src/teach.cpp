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
    size_t i = from;
    while (i < w.size() && kFront.count(w[i])) ++i;
    return std::vector<std::string>(w.begin() + static_cast<std::ptrdiff_t>(std::min(i, w.size())), w.end());
}

// words no plain «это X» names a thing with: «это круто», "that's right", «это сюда»
bool PlainStop(const std::string& word) {
    static const std::unordered_set<std::string> kStop = {
        // ru
        "не", "да", "нет", "то", "так", "все", "оно", "он", "она", "они", "мы", "вы", "ты", "я", "хорошо", "плохо", "круто",
        "отлично", "правда", "неправда", "здорово", "классно", "сюда", "туда", "здесь", "там", "вон", "мне", "тебе", "что",
        "кто", "где", "как", "зачем", "почему", "еще", "уже", "тоже", "для", "очень", "просто", "ерунда", "бред", "ок",
        "окей", "норм", "нормально", "супер", "смешно", "странно", "мое", "твое", "его", "ее", "их", "наше", "ваше", "был",
        "была", "было", "будет", "надо", "нужно", "можно", "нельзя", "конец", "всё",
        // en
        "it", "that", "this", "not", "right", "wrong", "good", "great", "fine", "ok", "okay", "enough", "correct", "true",
        "cool", "nice", "bad", "all", "me", "you", "mine", "yours", "here", "there", "what", "why", "how", "where", "who",
        "awesome", "funny", "weird", "strange", "crazy", "so", "too", "very", "just", "amazing", "perfect", "it's", "is",
        "are", "was", "were", "going", "gonna", "done", "over", "it", "him", "her", "them", "us", "fun", "insane", "nuts",
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
        default: return "none";
    }
}

TeachLine ReadTeach(std::string_view heard, const std::string& lang) {
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
        if (k != std::string::npos && k < w.size()) {
            const std::vector<std::string> what = NameWords(w, k);
            const std::string rest = Join(what, 0, what.size());
            if (!rest.empty() && !IsAny(rest, {"it", "that", "this", "about it", "about that", "everything", "it all",
                                               "это", "всё", "все", "об этом", "про это", "этом", "eso", "esto", "lo", "todo"})) {
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
                return out;
            }
        }
    }

    // a name of the thing under the crosshair
    auto name_from = [&](size_t k, bool plain) {
        if (k == std::string::npos || k >= w.size()) return false;
        const std::vector<std::string> name = NameWords(w, k);
        if (name.empty() || name.size() > 3) return false;
        if (plain)
            for (const std::string& x : name)
                if (PlainStop(x)) return false;
        out.kind = TeachKind::Name;
        out.rest = Join(name, 0, name.size());
        out.plain = plain;
        return true;
    };
    if (name_from(AfterAny(w, 0, {
            "назови это", "назови его", "назови ее", "назовем это", "это называется", "это будет", "пусть это будет",
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

}  // namespace coop
