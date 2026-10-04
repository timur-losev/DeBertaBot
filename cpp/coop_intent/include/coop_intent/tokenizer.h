// The tokenizer the model was trained with -- transformers' fast DebertaV2 tokenizer, i.e. the HF
// tokenizers pipeline in the model's tokenizer.json -- reproduced step by step:
//   added tokens   [CLS] [SEP] [PAD] [UNK] [MASK] typed in the text are matched first, as themselves;
//                  the text between them goes through the rest separately
//   normalizer     every run of 2+ whitespace and every \n \r \t -> one space; NFC; strip on the right
//   pre-tokenizer  Metaspace: spaces -> U+2581, U+2581 prepended, a new word at every U+2581
//   model          Unigram: the highest-scoring split of each word into vocabulary pieces (Viterbi);
//                  a character no piece covers is [UNK], consecutive ones fused into one
//   post           [CLS] pieces [SEP], the pieces cut to max_len - 2
// It is checked id for id against the Python tokenizer (coop_cli --tokenizer-tests, --golden).
#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace coop {

class DebertaTokenizer {
public:
    struct AddedToken {
        std::string text;
        int32_t id;
    };
    struct Options {
        int32_t cls_id = 1, sep_id = 2, unk_id = 3;
        int max_len = 64;                 // including [CLS] and [SEP]
        std::vector<AddedToken> added;    // matched in the raw text
    };

    // vocab_tsv: one "piece<TAB>score" per line, line number = id (scripts/coop/export_cpp.py)
    bool Load(std::string_view vocab_tsv, Options options, std::string* error);

    // [CLS] ... [SEP] for one line of UTF-8 text
    std::vector<int64_t> Encode(std::string_view utf8) const;

    // the steps, for tests and debugging
    std::string Normalize(std::string_view utf8) const;           // normalizer only
    std::vector<std::string> Words(std::string_view utf8) const;  // normalizer + pre-tokenizer
    const std::string& Piece(int64_t id) const;
    size_t VocabSize() const { return pieces_.size(); }

private:
    std::u32string NormalizeSegment(std::u32string_view s) const;
    void EncodeWord(const std::string& word, std::vector<int64_t>& ids) const;

    Options opt_;
    std::vector<std::string> pieces_;
    std::vector<double> scores_;
    std::unordered_map<std::string_view, int32_t> piece_ids_;   // views into pieces_
    std::vector<std::u32string> added_text_;
    size_t max_piece_bytes_ = 0;
    double unk_score_ = 0;
};

}  // namespace coop
