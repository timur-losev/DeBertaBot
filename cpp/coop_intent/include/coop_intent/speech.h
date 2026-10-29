// Speech in front of the bot: one push-to-talk clip in, its transcript out, and the form of that
// transcript the classifier was trained on.
//
//   clip --SpeechRecognizer--> transcript --+--> SpeechTextForClassifier --> tokenizer --> model
//                                           +--> BotBrain::Decide (regex slots, places): the transcript itself
//
// The recognizer is NVIDIA Parakeet TDT 0.6B v2 through sherpa-onnx (scripts/coop/stt/README.md: the
// owner's choice; about 0.7 GB of RAM, about 200 ms after the key is released on 2 threads). It is
// "offline": the whole clip is decoded at once, which is what push-to-talk gives it.
#pragma once

#include <cstddef>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

namespace coop {

// What the classifier is given for a spoken line, as the voice-chain bots were trained
// (scripts/coop/stt/build_v4.py `norm`): whitespace stripped at both ends, then a final run of . ! ?
// removed, then lowercased; punctuation inside the line stays. Only ASCII letters are lowercased:
// Parakeet prints ASCII (7178 of 7178 transcripts of the study).
std::string SpeechTextForClassifier(std::string_view transcript);

struct SpeechOptions {
    // a sherpa-onnx export of the model: encoder.int8.onnx, decoder.int8.onnx, joiner.int8.onnx, tokens.txt
    std::string model_dir;
    int threads = 2;
};

// A word of the transcript and when it began, in seconds from the clip's start (the model's token timestamps: the first
// token of the word). The game puts each order of a line at the moment its pointer word was said ("take THIS box", run,
// "put it HERE"): the crosshair and the player's place then, not when the talk key came up.
struct SpeechWord {
    std::string text;   // as printed, punctuation included
    double start = 0;
};

// The words of a token sequence: a token that begins with SentencePiece's word mark (U+2581) or a space starts a word.
// tokens and starts are parallel; an empty starts gives no words.
std::vector<SpeechWord> SpeechWords(const std::vector<std::string>& tokens, const std::vector<float>& starts);

class SpeechRecognizer {
public:
    SpeechRecognizer();
    ~SpeechRecognizer();
    SpeechRecognizer(const SpeechRecognizer&) = delete;
    SpeechRecognizer& operator=(const SpeechRecognizer&) = delete;

    bool Load(const SpeechOptions& options, std::string* error);
    bool Ready() const;
    // mono samples in -1..1; the model wants 16000 Hz (sherpa-onnx resamples another rate itself).
    // The transcript is UTF-8, as the recognizer prints it: capitals and punctuation included. words (optional): the
    // transcript's words with their start times, when the model gives timestamps (empty otherwise)
    bool Transcribe(const float* samples, size_t count, int sample_rate, std::string* text, std::string* error,
                    std::vector<SpeechWord>* words = nullptr) const;
    // "sherpa-onnx 1.13.8"
    static std::string Backend();
    // The ONNX Runtime the recognizer runs on, "1.28.2": the one the loader gave sherpa-onnx's library. On Windows
    // that is the process's one onnxruntime.dll, the bot's too; on macOS the library brings its own and the bot
    // keeps the engine's (OrtBackend::RuntimeVersion)
    static std::string RuntimeVersion();

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace coop
