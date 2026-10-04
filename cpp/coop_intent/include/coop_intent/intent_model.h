// The model behind an interface: the standalone build runs ONNX Runtime (OrtBackend), the UE5 port
// implements the same Run() on NNE. Input is one tokenized line ([CLS] ... [SEP], mask all ones),
// output one logit per label.
#pragma once

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace coop {

class ILogitsBackend {
public:
    virtual ~ILogitsBackend() = default;
    virtual bool Run(const std::vector<int64_t>& ids, std::vector<float>* logits, std::string* error) = 0;
};

// probabilities, computed in double and rounded to float (what torch.softmax gives the Python bot)
std::vector<float> Softmax(const std::vector<float>& logits);

// the k best labels, best first
std::vector<int> TopK(const std::vector<float>& probs, int k);

// several models over the same labels with their probabilities averaged (train_v2.py "ens3").
// Run() returns log(mean probability), so Softmax() of it gives the mean back.
class EnsembleBackend : public ILogitsBackend {
public:
    // parallel: every member on its own thread (lower latency, more cores busy at once)
    EnsembleBackend(std::vector<std::unique_ptr<ILogitsBackend>> members, bool parallel);
    bool Run(const std::vector<int64_t>& ids, std::vector<float>* logits, std::string* error) override;

private:
    std::vector<std::unique_ptr<ILogitsBackend>> members_;
    bool parallel_;
};

class OrtBackend : public ILogitsBackend {
public:
    struct Options {
        int threads = 4;              // intra-op threads; 0 = ONNX Runtime's default (all cores)
        bool allow_spinning = true;   // false: worker threads sleep between calls (a game wants that)
    };
    OrtBackend();
    ~OrtBackend() override;
    bool Load(const std::string& onnx_path_utf8, const Options& options, std::string* error);
    bool Run(const std::vector<int64_t>& ids, std::vector<float>* logits, std::string* error) override;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace coop
