#include "coop_intent/speech.h"

#include "coop_intent/unicode.h"

namespace coop {

// Python: re.sub(r"[.!?]+$", "", t.strip()).lower() -- the order matters ("go ." keeps its inner space)
std::string SpeechTextForClassifier(std::string_view transcript) {
    const std::u32string u = DecodeUtf8(transcript);
    size_t b = 0, e = u.size();
    while (b < e && IsPySpace(u[b])) ++b;
    while (e > b && IsPySpace(u[e - 1])) --e;
    while (e > b && (u[e - 1] == U'.' || u[e - 1] == U'!' || u[e - 1] == U'?')) --e;
    std::u32string out(u, b, e - b);
    for (char32_t& c : out)
        if (c >= U'A' && c <= U'Z') c += U'a' - U'A';
    return EncodeUtf8(out);
}

std::vector<SpeechWord> SpeechWords(const std::vector<std::string>& tokens, const std::vector<float>& starts) {
    static const std::string kMark = "\xE2\x96\x81";   // U+2581, SentencePiece's word mark
    std::vector<SpeechWord> words;
    if (starts.size() != tokens.size()) return words;
    bool begins = true;      // the next piece starts a word
    bool marked_at = false;  // ... and a word mark said when (a mark alone as a token passes its time on)
    double begun = 0;
    for (size_t i = 0; i < tokens.size(); ++i) {
        std::string t = tokens[i];
        bool marked = false;
        while (t.rfind(kMark, 0) == 0 || (!t.empty() && t[0] == ' ')) {
            t.erase(0, t[0] == ' ' ? 1 : kMark.size());
            marked = true;
        }
        if (marked) begins = true, marked_at = true, begun = starts[i];
        if (t.empty()) continue;
        if (begins || words.empty()) words.push_back({t, marked_at ? begun : starts[i]});
        else words.back().text += t;
        begins = false;
        marked_at = false;
    }
    return words;
}

}  // namespace coop
