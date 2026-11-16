// The bot, and the game's other people, talking in a role (2026-11-11, the owner: «бот будет отыгрывать свою роль, сначала
// просто репликами и ответами ... роутить «не команды» на LLM»; then «нужна будет ещё роль продавца»). A plain chat model
// (Qwen3-1.7B as its author published it, a 4-bit GGUF, no adapter: the game's decoder was trained to write orders and does
// not talk) answers a line that gives no order, as the role's system turn describes the speaker. It never gives orders: what
// the bot does stays the classifier's and the planner's.
//
//   a line to the bot --> decoder, classifier, planner --+--> an order, a question, a state question ....... as before
//                                                         +--> small talk, a question about itself, a question with no order
//                                                                --> Talker(the bot's role, the talk so far, the line)
//   a line to someone else (the game's "to": the seller) ----------> Talker(their role, the talk with them, the line)
#pragma once

#include <cstdint>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

namespace coop {

// one exchange of the talk so far: the player's line and the answer it got
struct TalkTurn {
    std::string user, assistant;
};

// The prompt as Qwen3's chat template renders it with thinking off: the system turn, the talk so far, the line, and the
// assistant turn opened with an empty think block (rewriter.h's RewriterPrompt, with earlier turns)
std::string TalkPrompt(std::string_view system, const std::vector<TalkTurn>& before, std::string_view line);

// The answer as the speaker says it: think blocks and chat markup out, one line, a leading "Name:" and surrounding quotes off,
// pictographs out; an answer the token limit cut off loses its unfinished last sentence. Empty: nothing sayable is left
std::string TalkAnswer(std::string_view raw, bool cut_off);

// Whether the text is written in the language: Russian has Cyrillic letters (and more of them than Latin ones); English and
// Spanish have Latin letters and no Cyrillic
bool TalkInLanguage(std::string_view text, std::string_view language);

// The sentences of the text that are written in the language (TalkInLanguage), in their order. Empty: none
std::string TalkSentencesInLanguage(std::string_view text, std::string_view language);

// The answer to say in the language: TalkAnswer; all of it when it is in the language, else the sentences of it that are (an answer
// that slid into English halfway: «Пleased to meet you, Тимур. Я Лео, и у меня тоже хорошее имя.» -> «Я Лео, и у меня тоже хорошее
// имя.», 2026-11-16). *part: only some of it was kept. Empty: nothing to say
std::string TalkSayableIn(std::string_view raw, bool cut_off, std::string_view language, bool* part = nullptr);

struct TalkerOptions {
    std::string model_path;          // the .gguf
    int gpu_layers = 99;             // 0: the CPU alone
    int threads = 4;
    int context = 2048;              // tokens: the role, the talk so far, the line, the answer
    int max_new = 72;                // the longest answer
    float temperature = 0.7f;        // Qwen3's advice with thinking off: 0.7, top-p 0.8, top-k 20
    float top_p = 0.8f;
    int top_k = 20;
    uint32_t seed = 0xFFFFFFFFu;     // llama.cpp's LLAMA_DEFAULT_SEED: a new draw for every answer; a fixed one repeats them
};

class Talker {
public:
    Talker();
    ~Talker();
    Talker(const Talker&) = delete;
    Talker& operator=(const Talker&) = delete;

    bool Load(const TalkerOptions& options, std::string* error);
    bool Ready() const;
    const TalkerOptions& Options() const;

    struct Stats {
        int cached = 0;        // prompt tokens already in the context (the role's system turn, after its first line)
        int evaluated = 0;     // prompt tokens computed for this line
        int generated = 0;     // answer tokens
        int dropped = 0;       // earlier exchanges left out to fit the context
        bool cut_off = false;  // the answer reached max_new before its end
    };
    // The model's answer, as it wrote it (TalkAnswer makes it sayable), to the line in the role: sampled (temperature, top-k,
    // top-p) until the end of its turn or max_new tokens. The oldest exchanges go first when the talk does not fit. Each answer
    // starts its draw from the seed (a fixed seed answers the same prompt the same way); redraw: the draw goes on from the last
    // answer instead, for another answer to the same prompt
    bool Reply(std::string_view system, const std::vector<TalkTurn>& before, std::string_view line, std::string* raw, Stats* stats,
               std::string* error, bool redraw = false);
    // "llama.cpp b11429"
    static std::string Backend();

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace coop
