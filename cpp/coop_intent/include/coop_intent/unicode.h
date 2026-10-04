// Unicode pieces the tokenizer and the regex slots need, driven by generated tables
// (src/unicode_tables.inc, tools/gen_unicode_tables.py) -- no ICU, no OS calls, same on every platform.
#pragma once

#include <string>
#include <string_view>

namespace coop {

// UTF-8 -> code points; every invalid or truncated sequence (and every encoded surrogate) becomes U+FFFD
std::u32string DecodeUtf8(std::string_view s);
std::string EncodeUtf8(std::u32string_view s);
void AppendUtf8(std::string& out, char32_t c);

// canonical composition (NFC) with the tables of the HF tokenizers library the model was trained with
std::u32string Nfc(std::u32string_view s);

bool IsNormalizerSpace(char32_t c);  // \s of the normalizer's regex (Oniguruma)
bool IsStripWhitespace(char32_t c);  // what Strip removes (Rust char::is_whitespace)
bool IsPyWordChar(char32_t c);       // \w of Python's re module
bool IsPySpace(char32_t c);          // Python's str.isspace() (what str.strip() removes)
char PyAsciiFold(char32_t c);        // the ASCII letter a non-ASCII c matches under re.IGNORECASE, or 0

}  // namespace coop
