// The text around the talking model (talker.h), without the model: the prompt, the answer made sayable, the language check.
#include <string>

#include "coop_intent/talker.h"
#include "coop_intent/unicode.h"

namespace coop {

namespace {

bool IsCyrillic(char32_t c) { return c >= 0x0400 && c <= 0x04FF; }
bool IsLatin(char32_t c) { return (c >= U'a' && c <= U'z') || (c >= U'A' && c <= U'Z') || (c >= 0x00C0 && c <= 0x024F && c != 0x00D7 && c != 0x00F7); }
bool IsLetter(char32_t c) { return IsCyrillic(c) || IsLatin(c); }
bool IsUpper(char32_t c) { return (c >= U'A' && c <= U'Z') || (c >= 0x0410 && c <= 0x042F) || c == 0x0401 || (c >= 0x00C0 && c <= 0x00DE && c != 0x00D7); }
bool EndsSentence(char32_t c) { return c == U'.' || c == U'!' || c == U'?' || c == 0x2026; }   // . ! ? …

// pictographs and other symbols a voice cannot say: the emoji planes, dingbats, arrows and the like, variation selectors
bool IsPictograph(char32_t c) {
    return (c >= 0x1F000 && c <= 0x1FAFF) || (c >= 0x2600 && c <= 0x27BF) || (c >= 0x2190 && c <= 0x21FF) || (c >= 0x2B00 && c <= 0x2BFF) ||
           (c >= 0xFE00 && c <= 0xFE0F) || c == 0x200D || c == 0x20E3;
}

bool IsQuote(char32_t c) { return c == U'"' || c == 0x00AB || c == 0x00BB || c == 0x201C || c == 0x201D || c == 0x201E || c == 0x2018 || c == 0x2019; }

// Chinese, Japanese and Korean script: Qwen lets a word of it slip into another language now and then («я не помню自己的 возраст»)
bool IsCjk(char32_t c) {
    return (c >= 0x2E80 && c <= 0x9FFF) || (c >= 0xAC00 && c <= 0xD7AF) || (c >= 0xF900 && c <= 0xFAFF) || (c >= 0xFF00 && c <= 0xFFEF) ||
           (c >= 0x20000 && c <= 0x2FA1F);
}

char32_t Upper(char32_t c) {
    if (c >= U'a' && c <= U'z') return c - 32;
    if (c >= 0x0430 && c <= 0x044F) return c - 32;   // а..я
    if (c == 0x0451) return 0x0401;                   // ё
    if (c >= 0x00E0 && c <= 0x00FE && c != 0x00F7) return c - 32;
    return c;
}

void EraseBetween(std::u32string& s, const std::u32string& open, const std::u32string& close) {
    for (size_t a = s.find(open); a != std::u32string::npos; a = s.find(open, a)) {
        const size_t b = s.find(close, a + open.size());
        s.erase(a, b == std::u32string::npos ? std::u32string::npos : b + close.size() - a);
    }
}

}  // namespace

std::string TalkPrompt(std::string_view system, const std::vector<TalkTurn>& before, std::string_view line) {
    std::string out = "<|im_start|>system\n";
    out.append(system).append("<|im_end|>\n");
    // earlier answers as the template shows them after the last line: their content alone, no think block
    for (const TalkTurn& t : before) {
        out.append("<|im_start|>user\n").append(t.user).append("<|im_end|>\n");
        out.append("<|im_start|>assistant\n").append(t.assistant).append("<|im_end|>\n");
    }
    out.append("<|im_start|>user\n").append(line).append("<|im_end|>\n");
    out += "<|im_start|>assistant\n<think>\n\n</think>\n\n";
    return out;
}

std::string TalkAnswer(std::string_view raw, bool cut_off) {
    std::u32string s = DecodeUtf8(raw);
    EraseBetween(s, U"<think>", U"</think>");
    EraseBetween(s, U"<|", U"|>");
    // one line, single spaces, no pictographs
    std::u32string t;
    for (char32_t c : s) {
        if (IsPictograph(c)) continue;
        if (c == U'\n' || c == U'\r' || c == U'\t' || IsPySpace(c)) c = U' ';
        if (c == U' ' && (t.empty() || t.back() == U' ')) continue;
        if (c == U'*' || c == U'_' || c == U'#' || c == U'`') continue;   // markdown emphasis and headings
        t += c;
    }
    while (!t.empty() && t.back() == U' ') t.pop_back();
    // a speaker's label before the words ("Бади: ...", "Max: ..."): one or two capitalized words and a colon
    {
        const size_t colon = t.find(U':');
        if (colon != std::u32string::npos && colon > 0 && colon <= 24 && colon + 1 < t.size() && t[colon + 1] == U' ' && IsUpper(t[0])) {
            int spaces = 0;
            bool letters = true;
            for (size_t i = 0; i < colon; ++i) {
                if (t[i] == U' ') ++spaces;
                else if (!IsLetter(t[i]) && t[i] != U'-') letters = false;
            }
            if (letters && spaces <= 1) t.erase(0, colon + 2);
        }
    }
    // quotes around the whole answer
    while (t.size() >= 2 && IsQuote(t.front()) && IsQuote(t.back())) t = t.substr(1, t.size() - 2);
    // cut off by the token limit: up to the last finished sentence (an answer with none is left as it is)
    if (cut_off) {
        for (size_t i = t.size(); i > 0; --i) {
            if (EndsSentence(t[i - 1])) {
                t.resize(i);
                break;
            }
        }
    }
    size_t b = 0;
    while (b < t.size() && (t[b] == U' ' || t[b] == U'-' || t[b] == 0x2014)) ++b;   // a leading dash of dialogue
    t.erase(0, b);
    while (!t.empty() && t.back() == U' ') t.pop_back();
    // a capital at each sentence's start, and the English "I" ("i'm not tired" when the player typed in small letters)
    bool start = true;
    for (size_t i = 0; i < t.size(); ++i) {
        if (start && IsLetter(t[i])) t[i] = Upper(t[i]), start = false;
        else if (EndsSentence(t[i])) start = true;
        else if (t[i] != U' ' && t[i] != U'"' && !IsQuote(t[i]) && t[i] != U'(') start = false;
        if (t[i] == U'i' && (i == 0 || t[i - 1] == U' ') && (i + 1 == t.size() || t[i + 1] == U' ' || t[i + 1] == U'\'' || t[i + 1] == 0x2019 ||
                                                              t[i + 1] == U',' || t[i + 1] == U'.' || t[i + 1] == U'!' || t[i + 1] == U'?'))
            t[i] = U'I';
    }
    bool any = false;
    for (char32_t c : t) any = any || IsLetter(c) || (c >= U'0' && c <= U'9');
    return any ? EncodeUtf8(t) : std::string();
}

std::string TalkSentencesInLanguage(std::string_view text, std::string_view language) {
    const std::u32string t = DecodeUtf8(text);
    std::u32string out, sentence;
    auto keep = [&]() {
        size_t b = 0, e = sentence.size();
        while (b < e && sentence[b] == U' ') ++b;
        while (e > b && sentence[e - 1] == U' ') --e;
        const std::u32string s = sentence.substr(b, e - b);
        if (!s.empty() && TalkInLanguage(EncodeUtf8(s), language)) out += (out.empty() ? U"" : U" ") + s;
        sentence.clear();
    };
    for (size_t i = 0; i < t.size(); ++i) {
        sentence += t[i];
        if (!EndsSentence(t[i])) continue;
        // the sentence's end: its marks ("?!", "...") and a closing quote, then a space or the text's end
        size_t j = i + 1;
        while (j < t.size() && (EndsSentence(t[j]) || IsQuote(t[j]))) sentence += t[j++];
        if (j == t.size() || t[j] == U' ') keep();
        i = j - 1;
    }
    keep();
    return EncodeUtf8(out);
}

std::string TalkSayableIn(std::string_view raw, bool cut_off, std::string_view language, bool* part) {
    if (part) *part = false;
    const std::string answer = TalkAnswer(raw, cut_off);
    if (answer.empty() || TalkInLanguage(answer, language)) return answer;
    const std::string kept = TalkSentencesInLanguage(answer, language);
    if (part) *part = !kept.empty();
    return kept;
}

bool TalkInLanguage(std::string_view text, std::string_view language) {
    int cyr = 0, lat = 0, digits = 0;
    bool word_cyr = false, word_lat = false;   // the letters of the word being read
    for (char32_t c : DecodeUtf8(text)) {
        if (IsCyrillic(c)) ++cyr, word_cyr = true;
        else if (IsLatin(c)) ++lat, word_lat = true;
        else {
            word_cyr = word_lat = false;
            if (c >= U'0' && c <= U'9') ++digits;
            else if (IsCjk(c)) return false;
        }
        // one word in two alphabets («Двойнойbest», «колou», the base model's Russian of 2026-11-11): not a word of any language
        if (word_cyr && word_lat) return false;
    }
    if (cyr == 0 && lat == 0) return digits > 0;   // a number alone ("24.") is said in any language
    if (language == "ru") return cyr >= 2 && cyr >= lat;
    return cyr == 0 && lat >= 2;
}

}  // namespace coop
