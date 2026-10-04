#include "coop_intent/tokenizer.h"

#include <algorithm>
#include <charconv>
#include <cstdlib>
#include <limits>

#include "coop_intent/unicode.h"

namespace coop {
namespace {

constexpr char32_t kMetaspace = 0x2581;   // the word-start mark the vocabulary pieces carry
constexpr double kUnkPenalty = 10.0;      // tokenizers' K_UNK_PENALTY: [UNK] scores min_score - 10

size_t Utf8Len(unsigned char lead) { return lead < 0x80 ? 1 : lead < 0xE0 ? 2 : lead < 0xF0 ? 3 : 4; }

// Metaspace(prepend_scheme always, split): spaces become the mark, the mark is prepended unless the
// text starts with one, and a word starts at every mark
template <class F>
void ForEachWord(const std::u32string& normalized, F&& emit) {
    if (normalized.empty()) return;
    std::u32string text;
    text.reserve(normalized.size() + 1);
    if (normalized.front() != U' ' && normalized.front() != kMetaspace) text.push_back(kMetaspace);
    for (char32_t c : normalized) text.push_back(c == U' ' ? kMetaspace : c);
    std::string word;
    for (char32_t c : text) {
        if (c == kMetaspace && !word.empty()) {
            emit(word);
            word.clear();
        }
        AppendUtf8(word, c);
    }
    if (!word.empty()) emit(word);
}

}  // namespace

bool DebertaTokenizer::Load(std::string_view tsv, Options options, std::string* error) {
    auto fail = [&](std::string msg) {
        if (error) *error = std::move(msg);
        return false;
    };
    opt_ = std::move(options);
    pieces_.clear();
    scores_.clear();
    piece_ids_.clear();
    added_text_.clear();
    size_t pos = 0, line = 0;
    while (pos < tsv.size()) {
        size_t end = tsv.find('\n', pos);
        if (end == std::string_view::npos) end = tsv.size();
        std::string_view row = tsv.substr(pos, end - pos);
        pos = end + 1;
        ++line;
        if (!row.empty() && row.back() == '\r') row.remove_suffix(1);
        const size_t tab = row.rfind('\t');
        if (tab == std::string_view::npos) return fail("vocab line " + std::to_string(line) + ": no tab");
        double score = 0;
#if defined(_MSC_VER) || (defined(__cpp_lib_to_chars) && __cpp_lib_to_chars >= 201611L)
        const auto [p, ec] = std::from_chars(row.data() + tab + 1, row.data() + row.size(), score);
        if (ec != std::errc() || p != row.data() + row.size())
            return fail("vocab line " + std::to_string(line) + ": bad score");
#else   // a standard library without floating-point from_chars (older libc++ on macOS)
        const std::string number(row.substr(tab + 1));
        char* stop = nullptr;
        score = std::strtod(number.c_str(), &stop);
        if (number.empty() || stop != number.c_str() + number.size())
            return fail("vocab line " + std::to_string(line) + ": bad score");
#endif
        pieces_.emplace_back(row.substr(0, tab));
        scores_.push_back(score);
    }
    if (pieces_.empty()) return fail("empty vocabulary");
    if (opt_.unk_id < 0 || static_cast<size_t>(opt_.unk_id) >= pieces_.size())
        return fail("unk_id outside the vocabulary");
    piece_ids_.reserve(pieces_.size());
    double min_score = std::numeric_limits<double>::infinity();
    for (size_t i = 0; i < pieces_.size(); ++i) {
        piece_ids_.emplace(pieces_[i], static_cast<int32_t>(i));   // a duplicate keeps the first id
        max_piece_bytes_ = std::max(max_piece_bytes_, pieces_[i].size());
        min_score = std::min(min_score, scores_[i]);
    }
    unk_score_ = min_score - kUnkPenalty;
    for (const AddedToken& a : opt_.added) added_text_.push_back(DecodeUtf8(a.text));
    return true;
}

std::u32string DebertaTokenizer::NormalizeSegment(std::u32string_view s) const {
    // Replace(regex "\s{2,}|[\n\r\t]", " ")
    std::u32string r;
    r.reserve(s.size());
    for (size_t i = 0; i < s.size();) {
        if (IsNormalizerSpace(s[i])) {
            size_t j = i;
            while (j < s.size() && IsNormalizerSpace(s[j])) ++j;
            if (j - i >= 2) {
                r.push_back(U' ');
                i = j;
                continue;
            }
        }
        const char32_t c = s[i++];
        r.push_back(c == U'\n' || c == U'\r' || c == U'\t' ? U' ' : c);
    }
    // NFC, then Strip(right)
    std::u32string n = Nfc(r);
    while (!n.empty() && IsStripWhitespace(n.back())) n.pop_back();
    return n;
}

std::string DebertaTokenizer::Normalize(std::string_view utf8) const {
    return EncodeUtf8(NormalizeSegment(DecodeUtf8(utf8)));
}

std::vector<std::string> DebertaTokenizer::Words(std::string_view utf8) const {
    std::vector<std::string> out;
    ForEachWord(NormalizeSegment(DecodeUtf8(utf8)), [&](const std::string& w) { out.push_back(w); });
    return out;
}

void DebertaTokenizer::EncodeWord(const std::string& w, std::vector<int64_t>& ids) const {
    // Viterbi over byte positions, as tokenizers' Unigram::encode_optimized: a node keeps the best
    // path ending there; candidates from one start are tried shortest first and only a strictly
    // better score replaces a node, so ties go to the path found first
    struct Node {
        double score = 0;
        size_t start = std::string::npos;
        int32_t id = 0;
    };
    const size_t n = w.size();
    const std::string_view view(w);
    std::vector<Node> best(n + 1);
    for (size_t start = 0; start < n;) {
        const double here = best[start].score;
        const size_t mblen = std::min(Utf8Len(static_cast<unsigned char>(w[start])), n - start);
        bool single = false;
        const size_t max_len = std::min(max_piece_bytes_, n - start);
        for (size_t len = 1; len <= max_len; ++len) {
            auto it = piece_ids_.find(view.substr(start, len));
            if (it == piece_ids_.end()) continue;
            Node& t = best[start + len];
            const double cand = scores_[static_cast<size_t>(it->second)] + here;
            if (t.start == std::string::npos || cand > t.score) t = {cand, start, it->second};
            if (len == mblen) single = true;
        }
        if (!single) {
            Node& t = best[start + mblen];
            const double cand = unk_score_ + here;
            if (t.start == std::string::npos || cand > t.score) t = {cand, start, opt_.unk_id};
        }
        start += mblen;
    }
    // walk back; consecutive [UNK] nodes fuse into one piece, and every piece is looked up by its
    // text (a fused run that happens to spell a vocabulary piece gets that piece's id)
    std::vector<std::string_view> parts;
    size_t unk_end = std::string::npos;
    for (size_t end = n; end > 0;) {
        const Node& node = best[end];
        if (node.id == opt_.unk_id) {
            if (unk_end == std::string::npos) unk_end = end;
        } else {
            if (unk_end != std::string::npos) {
                parts.push_back(view.substr(end, unk_end - end));
                unk_end = std::string::npos;
            }
            parts.push_back(view.substr(node.start, end - node.start));
        }
        end = node.start;
    }
    if (unk_end != std::string::npos) parts.push_back(view.substr(0, unk_end));
    for (auto it = parts.rbegin(); it != parts.rend(); ++it) {
        auto f = piece_ids_.find(*it);
        ids.push_back(f != piece_ids_.end() ? f->second : opt_.unk_id);
    }
}

std::vector<int64_t> DebertaTokenizer::Encode(std::string_view utf8) const {
    const std::u32string text = DecodeUtf8(utf8);
    std::vector<int64_t> ids;
    auto run = [&](size_t from, size_t to) {
        if (from < to)
            ForEachWord(NormalizeSegment(std::u32string_view(text).substr(from, to - from)),
                        [&](const std::string& w) { EncodeWord(w, ids); });
    };
    // added tokens, leftmost-longest, matched in the raw text before normalization
    size_t seg = 0;
    for (size_t i = 0; i < text.size();) {
        size_t best = 0, which = 0;
        for (size_t a = 0; a < added_text_.size(); ++a) {
            const std::u32string& t = added_text_[a];
            if (t.size() > best && text.compare(i, t.size(), t) == 0) {
                best = t.size();
                which = a;
            }
        }
        if (!best) {
            ++i;
            continue;
        }
        run(seg, i);
        ids.push_back(opt_.added[which].id);
        i += best;
        seg = i;
    }
    run(seg, text.size());

    const size_t keep = static_cast<size_t>(std::max(0, opt_.max_len - 2));
    if (ids.size() > keep) ids.resize(keep);
    ids.insert(ids.begin(), opt_.cls_id);
    ids.push_back(opt_.sep_id);
    return ids;
}

const std::string& DebertaTokenizer::Piece(int64_t id) const {
    static const std::string kOutside = "<outside the vocabulary>";
    for (const AddedToken& a : opt_.added)
        if (a.id == id) return a.text;
    return id >= 0 && static_cast<size_t>(id) < pieces_.size() ? pieces_[static_cast<size_t>(id)] : kOutside;
}

}  // namespace coop
