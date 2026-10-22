// decider: a second reader of a line beside the DeBERTa ensemble, optional (coop_cli --decider DIR).
//
// The model is Mapika's decider-2b (Qwen3.5-2B-Base, Apache-2.0) with the bot's LoRA merged in, as a GGUF for llama.cpp
// (scripts/coop/decider: run.py, gguf.py, export_game.py; the study in its README.md). It reads one forward pass: the
// logits of its own LM head at an "Answer: (" slot, restricted to the 57 option-label tokens. The prompt is decider's
// schema-first layout: the question and the 57 options first (the prefix, ~1,050 tokens, decoded once at load), then
// "\n\nContext:\n" + the line + "\n\nAnswer: (". Per line only the line's own tokens are computed: sequence 0 holds the
// prefix, each line is decoded in sequence 1 from a copy of it and the copy is dropped after.
//
// The token ids of the fixed parts come from upstream's own tokenizer (decider.json, written by export_game.py); the line
// is tokenized by llama.cpp from the GGUF's vocabulary (checked against upstream's on the study's test lines:
// coop_cli --decider DIR --decider-tests).
#pragma once

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace coop {

struct DeciderOptions {
    std::string model_path;              // the .gguf
    std::vector<int32_t> prefix;         // the question and the options
    std::vector<int32_t> label_ids;      // one token per label, in the bot's label order
    std::vector<int32_t> context_ids;    // "\n\nContext:\n"
    std::vector<int32_t> answer_ids;     // "\n\nAnswer: ("
    int max_line_tokens = 1536;          // a longer line is cut (upstream's max_ctx_tokens)
    double temperature = 1.0;
    int threads = 8;
    int gpu_layers = 0;                  // 0: the CPU alone (no device is given to llama.cpp at all)
};

class Decider {
public:
    Decider();
    ~Decider();
    Decider(const Decider&) = delete;
    Decider& operator=(const Decider&) = delete;

    // loads the model and decodes the prefix; the time of both is in load_ms() and prefix_ms()
    bool Load(const DeciderOptions& options, std::string* error);
    bool Ready() const;

    // the probabilities of the labels for a line (the text as the classifier gets it); `ids` gets the line's tokens
    bool Probs(const std::string& text, std::vector<float>* probs, std::string* error, std::vector<int32_t>* ids = nullptr);

    double load_ms() const;
    double prefix_ms() const;
    size_t prefix_tokens() const;
    static std::string Backend();

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace coop
