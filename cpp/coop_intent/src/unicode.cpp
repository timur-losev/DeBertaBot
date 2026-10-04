#include "coop_intent/unicode.h"

#include <algorithm>
#include <cstdint>
#include <iterator>

namespace coop {
namespace {

struct CpRange { char32_t lo, hi; };
struct CpFold { char32_t cp; char ascii; };
struct CccRange { char32_t lo, hi; uint8_t ccc; };
struct DecompEntry { char32_t cp; uint16_t offset; uint8_t len; };
struct ComposePair { char32_t a, b, c; };

#include "unicode_tables.inc"

template <size_t N>
bool InRanges(const CpRange (&table)[N], char32_t c) {
    auto it = std::upper_bound(std::begin(table), std::end(table), c,
                               [](char32_t v, const CpRange& r) { return v < r.lo; });
    return it != std::begin(table) && c <= std::prev(it)->hi;
}

uint8_t Ccc(char32_t c) {
    if (c < 0x300) return 0;
    auto it = std::upper_bound(std::begin(kCcc), std::end(kCcc), c,
                               [](char32_t v, const CccRange& r) { return v < r.lo; });
    return it != std::begin(kCcc) && c <= std::prev(it)->hi ? std::prev(it)->ccc : 0;
}

// Hangul syllables decompose and compose arithmetically
constexpr char32_t kSBase = 0xAC00, kLBase = 0x1100, kVBase = 0x1161, kTBase = 0x11A7;
constexpr int kLCount = 19, kVCount = 21, kTCount = 28, kNCount = kVCount * kTCount, kSCount = kLCount * kNCount;

void Decompose(char32_t c, std::u32string& out) {
    if (c >= kSBase && c < kSBase + kSCount) {
        const int s = static_cast<int>(c - kSBase);
        out.push_back(kLBase + s / kNCount);
        out.push_back(kVBase + (s % kNCount) / kTCount);
        if (s % kTCount) out.push_back(kTBase + s % kTCount);
        return;
    }
    auto it = std::lower_bound(std::begin(kDecomp), std::end(kDecomp), c,
                               [](const DecompEntry& e, char32_t v) { return e.cp < v; });
    if (it != std::end(kDecomp) && it->cp == c)
        out.append(kDecompData + it->offset, it->len);
    else
        out.push_back(c);
}

// the primary composite of a + b, or 0
char32_t Compose(char32_t a, char32_t b) {
    if (a >= kLBase && a < kLBase + kLCount && b >= kVBase && b < kVBase + kVCount)
        return kSBase + ((a - kLBase) * kVCount + (b - kVBase)) * kTCount;
    if (a >= kSBase && a < kSBase + kSCount && (a - kSBase) % kTCount == 0 && b > kTBase && b < kTBase + kTCount)
        return a + (b - kTBase);
    auto it = std::lower_bound(std::begin(kCompose), std::end(kCompose), std::make_pair(a, b),
                               [](const ComposePair& p, const std::pair<char32_t, char32_t>& v) {
                                   return p.a != v.first ? p.a < v.first : p.b < v.second;
                               });
    return it != std::end(kCompose) && it->a == a && it->b == b ? it->c : 0;
}

}  // namespace

std::u32string DecodeUtf8(std::string_view s) {
    std::u32string out;
    out.reserve(s.size());
    const auto* p = reinterpret_cast<const unsigned char*>(s.data());
    const size_t n = s.size();
    size_t i = 0;
    while (i < n) {
        const unsigned char b = p[i];
        if (b < 0x80) { out.push_back(b); ++i; continue; }
        int len = 0;
        char32_t c = 0, min = 0;
        if (b >= 0xC2 && b <= 0xDF) { len = 2; c = b & 0x1F; min = 0x80; }
        else if (b >= 0xE0 && b <= 0xEF) { len = 3; c = b & 0x0F; min = 0x800; }
        else if (b >= 0xF0 && b <= 0xF4) { len = 4; c = b & 0x07; min = 0x10000; }
        int k = 1;
        for (; len && k < len && i + k < n && (p[i + k] & 0xC0) == 0x80; ++k) c = (c << 6) | (p[i + k] & 0x3F);
        if (len && k == len && c >= min && c <= 0x10FFFF && !(c >= 0xD800 && c <= 0xDFFF)) {
            out.push_back(c);
            i += len;
        } else {
            out.push_back(0xFFFD);
            i += len ? std::max(1, k) : 1;   // skip the bad lead byte and the continuation bytes it had
        }
    }
    return out;
}

void AppendUtf8(std::string& out, char32_t c) {
    if (c < 0x80) {
        out.push_back(static_cast<char>(c));
    } else if (c < 0x800) {
        out.push_back(static_cast<char>(0xC0 | (c >> 6)));
        out.push_back(static_cast<char>(0x80 | (c & 0x3F)));
    } else if (c < 0x10000) {
        out.push_back(static_cast<char>(0xE0 | (c >> 12)));
        out.push_back(static_cast<char>(0x80 | ((c >> 6) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | (c & 0x3F)));
    } else {
        out.push_back(static_cast<char>(0xF0 | (c >> 18)));
        out.push_back(static_cast<char>(0x80 | ((c >> 12) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | ((c >> 6) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | (c & 0x3F)));
    }
}

std::string EncodeUtf8(std::u32string_view s) {
    std::string out;
    out.reserve(s.size());
    for (char32_t c : s) AppendUtf8(out, c);
    return out;
}

std::u32string Nfc(std::u32string_view s) {
    // below U+0300 nothing combines, and precomposed Latin-1 letters compose back to themselves
    if (std::all_of(s.begin(), s.end(), [](char32_t c) { return c < 0x300; })) return std::u32string(s);

    std::u32string d;
    d.reserve(s.size() + 8);
    for (char32_t c : s) Decompose(c, d);
    // canonical ordering: a run of marks is sorted by combining class, stable
    for (size_t i = 1; i < d.size(); ++i) {
        const uint8_t k = Ccc(d[i]);
        if (!k) continue;
        for (size_t j = i; j > 0 && Ccc(d[j - 1]) > k; --j) std::swap(d[j - 1], d[j]);
    }
    // canonical composition: a mark joins the last starter unless something between blocks it
    std::u32string out;
    out.reserve(d.size());
    size_t starter = std::u32string::npos;
    for (char32_t c : d) {
        const uint8_t k = Ccc(c);
        if (starter != std::u32string::npos) {
            const bool adjacent = out.size() - 1 == starter;
            const uint8_t prev = Ccc(out.back());
            if (adjacent || (prev != 0 && prev < k)) {
                if (char32_t x = Compose(out[starter], c)) {
                    out[starter] = x;
                    continue;
                }
            }
        }
        if (k == 0) starter = out.size();
        out.push_back(c);
    }
    return out;
}

bool IsNormalizerSpace(char32_t c) { return InRanges(kOnigSpace, c); }
bool IsStripWhitespace(char32_t c) { return InRanges(kRustWhitespace, c); }
bool IsPyWordChar(char32_t c) { return InRanges(kPyWord, c); }
bool IsPySpace(char32_t c) { return InRanges(kPySpace, c); }

char PyAsciiFold(char32_t c) {
    for (const CpFold& f : kPyFold)
        if (f.cp == c) return f.ascii;
    return 0;
}

}  // namespace coop
