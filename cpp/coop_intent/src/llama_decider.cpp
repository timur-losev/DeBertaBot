// decider.h on llama.cpp's C API (the same build as the decoder, llama_rewriter.cpp).
#include "coop_intent/decider.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <mutex>

#include "llama.h"

namespace coop {
namespace {

using Clock = std::chrono::steady_clock;
double Ms(Clock::duration d) { return std::chrono::duration<double, std::milli>(d).count(); }

void LogErrorsOnly(ggml_log_level level, const char* text, void*) {
    if (level >= GGML_LOG_LEVEL_ERROR) std::fputs(text, stderr);
}

// `tokens` into sequence `seq` from position `pos0`, the logits of the last token only
bool Decode(llama_context* ctx, const std::vector<llama_token>& tokens, llama_seq_id seq, llama_pos pos0, int n_batch,
            std::string* error) {
    for (size_t i = 0; i < tokens.size(); i += static_cast<size_t>(n_batch)) {
        const int n = static_cast<int>(std::min(tokens.size() - i, static_cast<size_t>(n_batch)));
        llama_batch b = llama_batch_init(n, 0, 1);
        for (int j = 0; j < n; ++j) {
            b.token[j] = tokens[i + j];
            b.pos[j] = pos0 + static_cast<llama_pos>(i + j);
            b.n_seq_id[j] = 1;
            b.seq_id[j][0] = seq;
            b.logits[j] = (i + j + 1 == tokens.size());
        }
        b.n_tokens = n;
        const int rc = llama_decode(ctx, b);
        llama_batch_free(b);
        if (rc != 0) {
            if (error) *error = "llama_decode failed (" + std::to_string(rc) + ")";
            return false;
        }
    }
    return true;
}

}  // namespace

struct Decider::Impl {
    llama_model* model = nullptr;
    llama_context* ctx = nullptr;
    const llama_vocab* vocab = nullptr;
    DeciderOptions opt;
    int n_batch = 0;
    double load_ms = 0, prefix_ms = 0;

    void Free() {
        if (ctx) llama_free(ctx);
        if (model) llama_model_free(model);
        ctx = nullptr;
        model = nullptr;
    }
    ~Impl() { Free(); }
};

Decider::Decider() : impl_(new Impl) {}
Decider::~Decider() = default;

bool Decider::Ready() const { return impl_->ctx != nullptr; }
double Decider::load_ms() const { return impl_->load_ms; }
double Decider::prefix_ms() const { return impl_->prefix_ms; }
size_t Decider::prefix_tokens() const { return impl_->opt.prefix.size(); }
std::string Decider::Backend() { return "llama.cpp " COOP_LLAMA_BUILD; }

bool Decider::Load(const DeciderOptions& options, std::string* error) {
    if (!std::ifstream(std::filesystem::u8path(options.model_path), std::ios::binary)) {
        if (error) *error = "cannot open " + options.model_path;
        return false;
    }
    if (options.prefix.empty() || options.label_ids.empty() || options.answer_ids.empty()) {
        if (error) *error = "the decider's prompt is incomplete (prefix, label ids, answer ids)";
        return false;
    }
    static std::once_flag once;
    std::call_once(once, [] {
        llama_log_set(LogErrorsOnly, nullptr);
        llama_backend_init();
    });
    Impl& s = *impl_;
    s.Free();
    const auto t0 = Clock::now();
    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = options.gpu_layers;
    // on the CPU the model is given no device at all: with a GPU in its list and no layers on it, llama.cpp still sends
    // large products (the prefix) to the GPU (llama_rewriter.cpp)
    ggml_backend_dev_t no_devices[] = {nullptr};
    const bool cpu = options.gpu_layers == 0;
    if (cpu) mp.devices = no_devices;
    s.model = llama_model_load_from_file(options.model_path.c_str(), mp);
    if (!s.model) {
        if (error) *error = "llama.cpp refused the model " + options.model_path;
        return false;
    }
    const int line_room = options.max_line_tokens + static_cast<int>(options.context_ids.size() + options.answer_ids.size()) + 8;
    llama_context_params cp = llama_context_default_params();
    cp.n_ctx = static_cast<uint32_t>(options.prefix.size() + line_room);
    cp.n_batch = cp.n_ctx;
    cp.n_ubatch = 512;
    cp.n_seq_max = 2;                 // 0: the prefix, 1: the line being read
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
    const int n_vocab = llama_vocab_n_tokens(s.vocab);
    for (int32_t id : options.label_ids)
        if (id < 0 || id >= n_vocab) {
            s.Free();
            if (error) *error = "a label token id is outside the model's vocabulary";
            return false;
        }
    s.opt = options;
    s.n_batch = static_cast<int>(cp.n_batch);
    s.load_ms = Ms(Clock::now() - t0);
    const auto t1 = Clock::now();
    if (!Decode(s.ctx, options.prefix, 0, 0, s.n_batch, error)) {
        s.Free();
        return false;
    }
    s.prefix_ms = Ms(Clock::now() - t1);
    return true;
}

bool Decider::Probs(const std::string& text, std::vector<float>* probs, std::string* error, std::vector<int32_t>* ids) {
    Impl& s = *impl_;
    if (!s.ctx) {
        if (error) *error = "the decider is not loaded";
        return false;
    }
    // the line as upstream tokenizes it: no special tokens added, special-token text matched
    std::vector<llama_token> line(text.size() + 8);
    int n = llama_tokenize(s.vocab, text.data(), static_cast<int32_t>(text.size()), line.data(), static_cast<int32_t>(line.size()),
                           /*add_special=*/false, /*parse_special=*/true);
    if (n < 0) {
        line.resize(static_cast<size_t>(-n));
        n = llama_tokenize(s.vocab, text.data(), static_cast<int32_t>(text.size()), line.data(), static_cast<int32_t>(line.size()),
                           false, true);
    }
    if (n < 0) {
        if (error) *error = "llama.cpp could not tokenize the line";
        return false;
    }
    line.resize(static_cast<size_t>(std::min(n, s.opt.max_line_tokens)));
    if (ids) ids->assign(line.begin(), line.end());
    std::vector<llama_token> suffix(s.opt.context_ids.begin(), s.opt.context_ids.end());
    suffix.insert(suffix.end(), line.begin(), line.end());
    suffix.insert(suffix.end(), s.opt.answer_ids.begin(), s.opt.answer_ids.end());

    llama_memory_t mem = llama_get_memory(s.ctx);
    llama_memory_seq_cp(mem, 0, 1, -1, -1);
    const bool ok = Decode(s.ctx, suffix, 1, static_cast<llama_pos>(s.opt.prefix.size()), s.n_batch, error);
    if (ok) {
        const float* logits = llama_get_logits_ith(s.ctx, -1);
        const size_t k = s.opt.label_ids.size();
        probs->assign(k, 0.0f);
        double top = -1e30, sum = 0;
        for (size_t j = 0; j < k; ++j) top = std::max(top, static_cast<double>(logits[s.opt.label_ids[j]]));
        std::vector<double> e(k);
        for (size_t j = 0; j < k; ++j) sum += e[j] = std::exp((logits[s.opt.label_ids[j]] - top) / s.opt.temperature);
        for (size_t j = 0; j < k; ++j) (*probs)[j] = static_cast<float>(e[j] / sum);
    }
    llama_memory_seq_rm(mem, 1, -1, -1);
    return ok;
}

}  // namespace coop
