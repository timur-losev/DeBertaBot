// Rewriter on llama.cpp's C API: one context, greedy decoding, the prompt's common prefix kept in the context
// between lines (what llama-server does with cache_prompt, and what scripts/coop/stt/gguf_v54.py measured).
#include "coop_intent/rewriter.h"

#include <cstdio>
#include <filesystem>
#include <fstream>
#include <mutex>

#include "llama.h"

namespace coop {

namespace {

// llama.cpp reports its loading on stderr line by line: only its errors are passed on
void LogErrorsOnly(enum ggml_log_level level, const char* text, void*) {
    if (level == GGML_LOG_LEVEL_ERROR) std::fputs(text, stderr);
}

}  // namespace

struct Rewriter::Impl {
    llama_model* model = nullptr;
    llama_context* ctx = nullptr;
    const llama_vocab* vocab = nullptr;
    RewriterOptions opt;
    int n_vocab = 0;
    std::vector<llama_token> held;   // the tokens whose keys and values the context holds, in order

    ~Impl() { Free(); }
    void Free() {
        if (ctx) llama_free(ctx);
        if (model) llama_model_free(model);
        ctx = nullptr;
        model = nullptr;
        vocab = nullptr;
        held.clear();
    }
};

Rewriter::Rewriter() : impl_(new Impl) {}
Rewriter::~Rewriter() = default;

bool Rewriter::Ready() const { return impl_->ctx != nullptr; }

std::string Rewriter::Backend() { return "llama.cpp " COOP_LLAMA_BUILD; }

bool Rewriter::Load(const RewriterOptions& options, std::string* error) {
    if (!std::ifstream(std::filesystem::u8path(options.model_path), std::ios::binary)) {
        if (error) *error = "cannot open " + options.model_path;
        return false;
    }
    static std::once_flag once;
    std::call_once(once, [] {
        llama_log_set(LogErrorsOnly, nullptr);
        llama_backend_init();
    });
    impl_->Free();
    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = options.gpu_layers;
    // on the CPU the model is given no device at all: with a GPU in its list and no layers on it, llama.cpp still
    // sends the prompt's large products to the GPU, and the answers are then neither the CPU's nor the GPU's
    ggml_backend_dev_t no_devices[] = {nullptr};
    const bool cpu = options.gpu_layers == 0;
    if (cpu) mp.devices = no_devices;
    impl_->model = llama_model_load_from_file(options.model_path.c_str(), mp);
    if (!impl_->model) {
        if (error) *error = "llama.cpp refused the model " + options.model_path;
        return false;
    }
    llama_context_params cp = llama_context_default_params();
    cp.n_ctx = static_cast<uint32_t>(options.context);
    cp.n_batch = static_cast<uint32_t>(options.context);   // a whole prompt in one call
    cp.n_threads = options.threads;
    cp.n_threads_batch = options.threads;
    cp.no_perf = true;
    if (cpu) cp.offload_kqv = cp.op_offload = false;
    impl_->ctx = llama_init_from_model(impl_->model, cp);
    if (!impl_->ctx) {
        impl_->Free();
        if (error) *error = "llama.cpp gave no context for " + options.model_path;
        return false;
    }
    impl_->vocab = llama_model_get_vocab(impl_->model);
    impl_->n_vocab = llama_vocab_n_tokens(impl_->vocab);
    impl_->opt = options;
    return true;
}

bool Rewriter::Answer(std::string_view turn, std::string* answer, Stats* stats, std::string* error) {
    answer->clear();
    Impl& s = *impl_;
    if (!s.ctx) {
        if (error) *error = "the decoder is not loaded";
        return false;
    }
    const std::string prompt = RewriterPrompt(s.opt.system, turn);
    // the template's markers are special tokens; no BOS is added (the template has none)
    std::vector<llama_token> tokens(prompt.size() + 8);
    const int n = llama_tokenize(s.vocab, prompt.c_str(), static_cast<int32_t>(prompt.size()), tokens.data(),
                                 static_cast<int32_t>(tokens.size()), false, true);
    if (n <= 0) {
        if (error) *error = "the prompt could not be tokenized";
        return false;
    }
    tokens.resize(static_cast<size_t>(n));
    if (n + s.opt.max_new > s.opt.context) {
        if (error) *error = "the line and its context do not fit the decoder's " + std::to_string(s.opt.context) + " tokens";
        return false;
    }
    // keep what the context already holds of this prompt (the system turn at least, after the first line), drop the rest
    size_t keep = 0;
    while (keep < s.held.size() && keep < tokens.size() && s.held[keep] == tokens[keep]) ++keep;
    if (keep == tokens.size()) --keep;   // the last token is computed again: its logits are the answer's first token
    if (keep < s.held.size()) {
        if (!llama_memory_seq_rm(llama_get_memory(s.ctx), 0, static_cast<llama_pos>(keep), -1)) {
            llama_memory_clear(llama_get_memory(s.ctx), true);   // a memory that cannot drop a tail: start over
            keep = 0;
        }
        s.held.resize(keep);
    }
    if (llama_decode(s.ctx, llama_batch_get_one(tokens.data() + keep, static_cast<int32_t>(tokens.size() - keep))) != 0) {
        s.held.clear();
        llama_memory_clear(llama_get_memory(s.ctx), true);
        if (error) *error = "llama.cpp failed on the prompt";
        return false;
    }
    s.held = tokens;
    int generated = 0;
    for (; generated < s.opt.max_new; ++generated) {
        const float* logits = llama_get_logits_ith(s.ctx, -1);
        llama_token best = 0;
        for (llama_token t = 1; t < s.n_vocab; ++t)
            if (logits[t] > logits[best]) best = t;
        if (llama_vocab_is_eog(s.vocab, best)) break;
        char buf[256];
        const int len = llama_token_to_piece(s.vocab, best, buf, sizeof buf, 0, false);
        if (len > 0) answer->append(buf, static_cast<size_t>(len));
        if (llama_decode(s.ctx, llama_batch_get_one(&best, 1)) != 0) {
            s.held.clear();
            llama_memory_clear(llama_get_memory(s.ctx), true);
            if (error) *error = "llama.cpp failed on the answer";
            return false;
        }
        s.held.push_back(best);
    }
    if (stats) {
        stats->cached = static_cast<int>(keep);
        stats->evaluated = static_cast<int>(tokens.size() - keep);
        stats->generated = generated;
    }
    return true;
}

bool Rewriter::Rewrite(const std::vector<std::string>& before, std::string_view bot, std::string_view line,
                       std::vector<std::string>* pieces, std::string* error) {
    std::string answer;
    if (!Answer(RewriterTurn(before, bot, line), &answer, nullptr, error)) return false;
    *pieces = RewriterPieces(answer);
    return true;
}

}  // namespace coop
