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

}  // namespace coop
