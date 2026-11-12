// talker.h on llama.cpp's C API (the same build as the decoder, llama_rewriter.cpp): one context, the prompt's common prefix
// kept between lines (the role's system turn is computed once while the role stays the same), the answer sampled.
#include "coop_intent/talker.h"

#include <cstdio>
#include <filesystem>
#include <fstream>
#include <mutex>

#include "llama.h"

namespace coop {

namespace {

void LogErrorsOnly(enum ggml_log_level level, const char* text, void*) {
    if (level == GGML_LOG_LEVEL_ERROR) std::fputs(text, stderr);
}

bool Tokenize(const llama_vocab* vocab, const std::string& text, std::vector<llama_token>* out) {
    out->assign(text.size() + 8, 0);
    int n = llama_tokenize(vocab, text.c_str(), static_cast<int32_t>(text.size()), out->data(), static_cast<int32_t>(out->size()), false, true);
    if (n < 0) {
        out->assign(static_cast<size_t>(-n), 0);
        n = llama_tokenize(vocab, text.c_str(), static_cast<int32_t>(text.size()), out->data(), static_cast<int32_t>(out->size()), false, true);
    }
    if (n <= 0) return false;
    out->resize(static_cast<size_t>(n));
    return true;
}

}  // namespace

struct Talker::Impl {
    llama_model* model = nullptr;
    llama_context* ctx = nullptr;
    llama_sampler* sampler = nullptr;
    const llama_vocab* vocab = nullptr;
    TalkerOptions opt;
    std::vector<llama_token> held;   // the tokens whose keys and values the context holds, in order

    ~Impl() { Free(); }
    void Free() {
        if (sampler) llama_sampler_free(sampler);
        if (ctx) llama_free(ctx);
        if (model) llama_model_free(model);
        sampler = nullptr;
        ctx = nullptr;
        model = nullptr;
        vocab = nullptr;
        held.clear();
    }
};

Talker::Talker() : impl_(new Impl) {}
Talker::~Talker() = default;

bool Talker::Ready() const { return impl_->ctx != nullptr; }
const TalkerOptions& Talker::Options() const { return impl_->opt; }
std::string Talker::Backend() { return "llama.cpp " COOP_LLAMA_BUILD; }

bool Talker::Load(const TalkerOptions& options, std::string* error) {
    if (!std::ifstream(std::filesystem::u8path(options.model_path), std::ios::binary)) {
        if (error) *error = "cannot open " + options.model_path;
        return false;
    }
    static std::once_flag once;
    std::call_once(once, [] {
        llama_log_set(LogErrorsOnly, nullptr);
        llama_backend_init();
    });
    Impl& s = *impl_;
    s.Free();
    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = options.gpu_layers;
    // on the CPU the model is given no device at all (llama_rewriter.cpp: else the prompt's large products go to the GPU)
    ggml_backend_dev_t no_devices[] = {nullptr};
    const bool cpu = options.gpu_layers == 0;
    if (cpu) mp.devices = no_devices;
    s.model = llama_model_load_from_file(options.model_path.c_str(), mp);
    if (!s.model) {
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
    s.ctx = llama_init_from_model(s.model, cp);
    if (!s.ctx) {
        s.Free();
        if (error) *error = "llama.cpp gave no context for " + options.model_path;
        return false;
    }
    s.vocab = llama_model_get_vocab(s.model);
    // Qwen3's advice for talk with thinking off: temperature 0.7, top-p 0.8, top-k 20; the draw from the seed
    s.sampler = llama_sampler_chain_init(llama_sampler_chain_default_params());
    llama_sampler_chain_add(s.sampler, llama_sampler_init_top_k(options.top_k));
    llama_sampler_chain_add(s.sampler, llama_sampler_init_top_p(options.top_p, 1));
    llama_sampler_chain_add(s.sampler, llama_sampler_init_temp(options.temperature));
    llama_sampler_chain_add(s.sampler, llama_sampler_init_dist(options.seed));
    s.opt = options;
    return true;
}

bool Talker::Reply(std::string_view system, const std::vector<TalkTurn>& before, std::string_view line, std::string* raw, Stats* stats,
                   std::string* error, bool redraw) {
    raw->clear();
    Impl& s = *impl_;
    if (!s.ctx) {
        if (error) *error = "the talking model is not loaded";
        return false;
    }
    // the talk so far, the oldest exchanges dropped until the prompt and the longest answer fit
    std::vector<TalkTurn> kept(before.begin(), before.end());
    std::vector<llama_token> tokens;
    int dropped = 0;
    for (;;) {
        if (!Tokenize(s.vocab, TalkPrompt(system, kept, line), &tokens)) {
            if (error) *error = "the prompt could not be tokenized";
            return false;
        }
        if (static_cast<int>(tokens.size()) + s.opt.max_new <= s.opt.context) break;
        if (kept.empty()) {
            if (error) *error = "the role and the line do not fit the talking model's " + std::to_string(s.opt.context) + " tokens";
            return false;
        }
        kept.erase(kept.begin());
        ++dropped;
    }
    // keep what the context already holds of this prompt, drop the rest
    size_t keep = 0;
    while (keep < s.held.size() && keep < tokens.size() && s.held[keep] == tokens[keep]) ++keep;
    if (keep == tokens.size()) --keep;   // the last token is computed again: its logits give the answer's first token
    if (keep < s.held.size()) {
        if (!llama_memory_seq_rm(llama_get_memory(s.ctx), 0, static_cast<llama_pos>(keep), -1)) {
            llama_memory_clear(llama_get_memory(s.ctx), true);
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
    // a fixed seed draws the same way for every answer (tests); the default seed draws anew. A redraw goes on where it was
    if (!redraw) llama_sampler_reset(s.sampler);
    int generated = 0;
    bool ended = false;
    for (; generated < s.opt.max_new; ++generated) {
        llama_token next = llama_sampler_sample(s.sampler, s.ctx, -1);
        if (llama_vocab_is_eog(s.vocab, next)) {
            ended = true;
            break;
        }
        char buf[256];
        const int len = llama_token_to_piece(s.vocab, next, buf, sizeof buf, 0, false);
        if (len > 0) raw->append(buf, static_cast<size_t>(len));
        if (llama_decode(s.ctx, llama_batch_get_one(&next, 1)) != 0) {
            s.held.clear();
            llama_memory_clear(llama_get_memory(s.ctx), true);
            if (error) *error = "llama.cpp failed on the answer";
            return false;
        }
        s.held.push_back(next);
    }
    if (stats) {
        stats->cached = static_cast<int>(keep);
        stats->evaluated = static_cast<int>(tokens.size() - keep);
        stats->generated = generated;
        stats->dropped = dropped;
        stats->cut_off = !ended;
    }
    return true;
}

}  // namespace coop
