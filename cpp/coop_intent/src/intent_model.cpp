#include "coop_intent/intent_model.h"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <thread>

namespace coop {

std::vector<float> Softmax(const std::vector<float>& logits) {
    std::vector<float> p(logits.size());
    if (logits.empty()) return p;
    const double m = *std::max_element(logits.begin(), logits.end());
    double sum = 0;
    std::vector<double> e(logits.size());
    for (size_t i = 0; i < logits.size(); ++i) sum += e[i] = std::exp(static_cast<double>(logits[i]) - m);
    for (size_t i = 0; i < logits.size(); ++i) p[i] = static_cast<float>(e[i] / sum);
    return p;
}

std::vector<int> TopK(const std::vector<float>& probs, int k) {
    std::vector<int> idx(probs.size());
    std::iota(idx.begin(), idx.end(), 0);
    k = std::min<int>(k, static_cast<int>(idx.size()));
    std::stable_sort(idx.begin(), idx.end(), [&](int a, int b) { return probs[a] > probs[b]; });
    idx.resize(static_cast<size_t>(k));
    return idx;
}

EnsembleBackend::EnsembleBackend(std::vector<std::unique_ptr<ILogitsBackend>> members, bool parallel)
    : members_(std::move(members)), parallel_(parallel) {}

bool EnsembleBackend::Run(const std::vector<int64_t>& ids, std::vector<float>* logits, std::string* error) {
    const size_t n = members_.size();
    if (n == 0) {
        if (error) *error = "empty ensemble";
        return false;
    }
    std::vector<std::vector<float>> out(n);
    std::vector<std::string> errs(n);
    std::vector<char> ok(n, 0);
    auto run = [&](size_t i) { ok[i] = members_[i]->Run(ids, &out[i], &errs[i]); };
    if (parallel_ && n > 1) {
        std::vector<std::thread> threads;
        for (size_t i = 1; i < n; ++i) threads.emplace_back(run, i);
        run(0);
        for (auto& t : threads) t.join();
    } else {
        for (size_t i = 0; i < n; ++i) run(i);
    }
    std::vector<double> mean;
    for (size_t i = 0; i < n; ++i) {
        if (!ok[i]) {
            if (error) *error = "member " + std::to_string(i) + ": " + errs[i];
            return false;
        }
        const std::vector<float> p = Softmax(out[i]);
        if (i == 0) mean.assign(p.size(), 0.0);
        if (p.size() != mean.size()) {
            if (error) *error = "members disagree on the number of labels";
            return false;
        }
        for (size_t j = 0; j < p.size(); ++j) mean[j] += p[j];
    }
    logits->resize(mean.size());
    for (size_t j = 0; j < mean.size(); ++j)
        (*logits)[j] = static_cast<float>(std::log(std::max(mean[j] / static_cast<double>(n), 1e-300)));
    return true;
}

}  // namespace coop
