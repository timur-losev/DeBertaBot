// decider_eval: a decider GGUF on llama.cpp's CPU (or Vulkan) backend, as the game would run it.
//
// The prompt's token ids come from Python (upstream's own tokenizer, prep_gguf.py): one prefix (the question and the 57
// options, ~1,050 tokens) and one suffix per line ("\n\nContext:\n<line>\n\nAnswer: ("). The prefix is decoded once into
// sequence 0. Each line: sequence 0 is copied to sequence 1 (llama.cpp shares the prefix's attention cells and gives the
// recurrent delta-net state its own cell before writing), the suffix is decoded there, the logits of the last token are
// read at the 57 label token ids, and sequence 1 is removed. Wall time per line is measured around that.
//
//   decider_eval <model.gguf> <rows.json> <out.jsonl> [--threads N] [--gpu-layers N] [--check K] [--limit N]
//
// rows.json: {"prefix": [ids], "labels": [57 ids], "rows": [{"id": "...", "suffix": [ids]}, ...]}
// out.jsonl: one line per row: {"id": ..., "logits": [57], "ms": ...}; first a header line with the load and prefix times.
// --check K: for the first K rows also decode prefix + suffix whole in a fresh sequence and print the largest difference.
#include <chrono>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

#include "llama.h"
#include "nlohmann/json.hpp"

using json = nlohmann::json;
using clk = std::chrono::steady_clock;

static double ms_since(clk::time_point t0) { return std::chrono::duration<double, std::milli>(clk::now() - t0).count(); }

// Decodes `toks` into `seq` at positions pos0.. ; logits only for the last token. Returns false on failure.
static bool decode(llama_context* ctx, const std::vector<llama_token>& toks, llama_seq_id seq, llama_pos pos0, int n_batch) {
    for (size_t i = 0; i < toks.size(); i += n_batch) {
        const int n = (int)std::min(toks.size() - i, (size_t)n_batch);
        llama_batch b = llama_batch_init(n, 0, 1);
        for (int j = 0; j < n; ++j) {
            b.token[j] = toks[i + j];
            b.pos[j] = pos0 + (llama_pos)(i + j);
            b.n_seq_id[j] = 1;
            b.seq_id[j][0] = seq;
            b.logits[j] = (i + j + 1 == toks.size());
        }
        b.n_tokens = n;
        const int rc = llama_decode(ctx, b);
        llama_batch_free(b);
        if (rc != 0) { std::fprintf(stderr, "llama_decode failed: %d\n", rc); return false; }
    }
    return true;
}

static std::vector<float> label_logits(llama_context* ctx, const std::vector<llama_token>& labels) {
    const float* lg = llama_get_logits_ith(ctx, -1);
    std::vector<float> out;
    out.reserve(labels.size());
    for (auto t : labels) out.push_back(lg[t]);
    return out;
}

int main(int argc, char** argv) {
    if (argc < 4) { std::fprintf(stderr, "usage: decider_eval <model.gguf> <rows.json> <out.jsonl> [--threads N] [--gpu-layers N] [--check K] [--limit N]\n"); return 2; }
    int threads = 8, gpu_layers = 0, check = 0, limit = -1;
    for (int i = 4; i + 1 < argc; i += 2) {
        const std::string a = argv[i];
        if (a == "--threads") threads = std::atoi(argv[i + 1]);
        else if (a == "--gpu-layers") gpu_layers = std::atoi(argv[i + 1]);
        else if (a == "--check") check = std::atoi(argv[i + 1]);
        else if (a == "--limit") limit = std::atoi(argv[i + 1]);
    }
    json in = json::parse(std::ifstream(argv[2]));
    const std::vector<llama_token> prefix = in["prefix"].get<std::vector<llama_token>>();
    const std::vector<llama_token> labels = in["labels"].get<std::vector<llama_token>>();
    const json& rows = in["rows"];

    llama_log_set([](ggml_log_level lvl, const char* t, void*) { if (lvl >= GGML_LOG_LEVEL_ERROR) std::fputs(t, stderr); }, nullptr);
    llama_backend_init();
    auto t0 = clk::now();
    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = gpu_layers;
    // on the CPU no device at all: with a GPU listed and no layers on it, llama.cpp still sends large products (the
    // prefix) to the GPU (cpp/coop_intent/src/llama_rewriter.cpp). The first version of this tool did not do this: its
    // prefix times and its cached-vs-whole check mixed the GPU in.
    ggml_backend_dev_t no_devices[] = {nullptr};
    if (gpu_layers == 0) mp.devices = no_devices;
    llama_model* model = llama_model_load_from_file(argv[1], mp);
    if (!model) { std::fprintf(stderr, "cannot load %s\n", argv[1]); return 1; }
    llama_context_params cp = llama_context_default_params();
    cp.n_ctx = 4096;
    cp.n_batch = 2048;
    cp.n_ubatch = 512;
    cp.n_seq_max = 3;
    cp.n_threads = threads;
    cp.n_threads_batch = threads;
    if (gpu_layers == 0) cp.offload_kqv = cp.op_offload = false;
    llama_context* ctx = llama_init_from_model(model, cp);
    if (!ctx) { std::fprintf(stderr, "cannot create the context\n"); return 1; }
    llama_memory_t mem = llama_get_memory(ctx);
    const double load_ms = ms_since(t0);

    t0 = clk::now();
    if (!decode(ctx, prefix, 0, 0, cp.n_batch)) return 1;
    const double prefix_ms = ms_since(t0);
    std::fprintf(stderr, "loaded in %.0f ms; prefix of %zu tokens in %.0f ms; %d threads, %d GPU layers\n", load_ms,
                 prefix.size(), prefix_ms, threads, gpu_layers);

    std::ofstream out(argv[3]);
    out << json{{"model", argv[1]}, {"threads", threads}, {"gpu_layers", gpu_layers}, {"load_ms", load_ms},
                {"prefix_ms", prefix_ms}, {"prefix_tokens", prefix.size()}}.dump() << "\n";
    const int n = limit < 0 ? (int)rows.size() : std::min(limit, (int)rows.size());
    double total = 0, worst_check = 0;
    for (int r = 0; r < n; ++r) {
        const std::vector<llama_token> suf = rows[r]["suffix"].get<std::vector<llama_token>>();
        auto t1 = clk::now();
        llama_memory_seq_cp(mem, 0, 1, -1, -1);
        if (!decode(ctx, suf, 1, (llama_pos)prefix.size(), cp.n_batch)) return 1;
        std::vector<float> lg = label_logits(ctx, labels);
        llama_memory_seq_rm(mem, 1, -1, -1);
        const double ms = ms_since(t1);
        total += ms;
        if (r < check) {
            std::vector<llama_token> whole = prefix;
            whole.insert(whole.end(), suf.begin(), suf.end());
            if (!decode(ctx, whole, 2, 0, cp.n_batch)) return 1;
            std::vector<float> ref = label_logits(ctx, labels);
            llama_memory_seq_rm(mem, 2, -1, -1);
            float d = 0;
            for (size_t j = 0; j < lg.size(); ++j) d = std::max(d, std::abs(lg[j] - ref[j]));
            worst_check = std::max(worst_check, (double)d);
            std::fprintf(stderr, "check %s: max |d logit| cached vs whole %.5f\n", rows[r]["id"].get<std::string>().c_str(), d);
        }
        out << json{{"id", rows[r]["id"]}, {"logits", lg}, {"ms", ms}}.dump() << "\n";
        if ((r + 1) % 200 == 0) std::fprintf(stderr, "%d/%d rows, %.1f ms per line\n", r + 1, n, total / (r + 1));
    }
    std::fprintf(stderr, "%d rows, %.1f ms per line on average%s\n", n, total / std::max(1, n),
                 check ? (" ; worst check " + std::to_string(worst_check)).c_str() : "");
    llama_free(ctx);
    llama_model_free(model);
    llama_backend_free();
    return 0;
}
