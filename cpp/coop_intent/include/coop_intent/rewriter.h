// The decoder in front of the classifier, for the lines it cannot read alone (scripts/coop/stt/chains2_v54.py,
// the "pieces" decoders; reports/Дообучение языковой модели и цепочки приказов.md). A line that gives several
// orders, or that leans on what was said before it, is rewritten as orders that stand by themselves, and each of
// those goes through the bot as any line does:
//
//   transcript --Router--+--> one complete order ------------------------------> classifier, slots, places, planner
//                        +--> several orders, or leans on the talk
//                               --Rewriter(earlier lines, the bot's line, the line)--> order lines, each one --^
//
// The router is a two-class DeBERTa-v3-small in ONNX Runtime, like a bot's member. The rewriter is a Qwen3-1.7B with
// its LoRA adapter merged in, as a 4-bit GGUF, run by llama.cpp: on the GPU with the Vulkan build (any vendor's card),
// on the CPU alone with gpu_layers = 0. The system turn's keys and values stay in the context between lines, so a
// line costs its own tokens and its answer's.
#pragma once

#include <memory>
#include <string>
#include <string_view>
#include <vector>

namespace coop {

// The user turn the decoder was trained on (chains2_v54.turn): "before: <line>" for each earlier line of the player,
// oldest first, "bot: <line>" if the bot said something after them, "scene: <scene>" when the game sent one (decoder
// v65, chains9_v65.py), then "now: <line>"; one per row.
std::string RewriterTurn(const std::vector<std::string>& before, std::string_view bot, std::string_view line,
                         std::string_view scene = {});

// What the bot deals with, as the game sends it (the world's "scene"), and the line the decoder is shown
// (chains9_v65.scene_text): "holding a <thing>; standing on a <thing>; no car near | a car <m> m away; last thing:
// <thing>, <m> m", the parts in that order, each but the car's left out when there is nothing to say.
constexpr double kSceneCarNear = 25;   // metres: a car farther than that is "no car near" (the game's CarNearEnough)
struct Scene {
    std::string holding, standing_on, last;   // empty: none
    bool has_car = false;
    double car_m = 0, last_m = 0;             // metres; 0 m for the car: the bot is in it
    // decoder v67: an order the bot could not carry out lately, "<the order's English>, <why>" ("climb onto the white table,
    // too high"); after the car's part as "failed: ...". Empty: none
    std::string failed;
};
std::string SceneLine(const Scene& scene);

// The prompt as the model's chat template renders it with thinking off (qlora_v54.Turns.text): the system turn, the
// user turn, and the assistant turn opened with an empty think block.
std::string RewriterPrompt(std::string_view system, std::string_view turn);

// The answer as order lines: its rows, stripped, without the empty ones.
std::vector<std::string> RewriterPieces(std::string_view answer);

// Router: the probability of "for the decoder" from the model's two logits (softmax in double, as Softmax()).
double RouteProbability(const std::vector<float>& logits);

struct RewriterOptions {
    std::string model_path;   // the .gguf
    std::string system;       // the system turn the adapter was trained with (rewriter_config.json)
    int gpu_layers = 99;      // 0: the CPU alone
    int threads = 4;
    int context = 1024;       // tokens: the system turn, the earlier lines and the line, the answer
    int max_new = 96;         // the longest answer (chains2_v54.MAX_NEW)
};

class Rewriter {
public:
    Rewriter();
    ~Rewriter();
    Rewriter(const Rewriter&) = delete;
    Rewriter& operator=(const Rewriter&) = delete;

    bool Load(const RewriterOptions& options, std::string* error);
    bool Ready() const;

    struct Stats {
        int cached = 0;      // prompt tokens whose keys and values were already in the context
        int evaluated = 0;   // prompt tokens computed for this line
        int generated = 0;   // answer tokens
    };
    // the model's answer to one user turn, generated greedily until the end-of-turn token
    bool Answer(std::string_view turn, std::string* answer, Stats* stats, std::string* error);
    // the orders the player gives now, each standing by itself; `scene`: SceneLine, empty for none
    bool Rewrite(const std::vector<std::string>& before, std::string_view bot, std::string_view scene, std::string_view line,
                 std::vector<std::string>* pieces, std::string* error);
    // "llama.cpp b11429"
    static std::string Backend();

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace coop
