// The text around the decoder (rewriter.h), without the model: the turn, the prompt, the answer's lines, the router's
// probability. Twins of scripts/coop/stt/chains2_v54.py (turn, split) and qlora_v54.py (Turns.text).
#include <cmath>

#include "coop_intent/rewriter.h"

namespace coop {

std::string RewriterTurn(const std::vector<std::string>& before, std::string_view bot, std::string_view line) {
    std::string out;
    for (const std::string& b : before) out += "before: " + b + "\n";
    if (!bot.empty()) out.append("bot: ").append(bot).append("\n");
    out.append("now: ").append(line);
    return out;
}

std::string RewriterPrompt(std::string_view system, std::string_view turn) {
    std::string out = "<|im_start|>system\n";
    out.append(system).append("<|im_end|>\n<|im_start|>user\n").append(turn);
    out += "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n";
    return out;
}

std::vector<std::string> RewriterPieces(std::string_view answer) {
    // Python: [p.strip() for p in answer.split("\n") if p.strip()], on ASCII whitespace (the answers are ASCII)
    const auto space = [](char c) { return c == ' ' || c == '\t' || c == '\r' || c == '\f' || c == '\v'; };
    std::vector<std::string> out;
    size_t pos = 0;
    while (pos <= answer.size()) {
        size_t end = answer.find('\n', pos);
        if (end == std::string_view::npos) end = answer.size();
        size_t b = pos, e = end;
        while (b < e && space(answer[b])) ++b;
        while (e > b && space(answer[e - 1])) --e;
        if (e > b) out.emplace_back(answer.substr(b, e - b));
        pos = end + 1;
    }
    return out;
}

double RouteProbability(const std::vector<float>& logits) {
    if (logits.size() != 2) return 0.0;
    const double a = logits[0], b = logits[1];
    return 1.0 / (1.0 + std::exp(a - b));
}

}  // namespace coop
