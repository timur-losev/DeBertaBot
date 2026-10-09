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

class SpeechRecognizer {
public:
    SpeechRecognizer();
    ~SpeechRecognizer();
    SpeechRecognizer(const SpeechRecognizer&) = delete;
    SpeechRecognizer& operator=(const SpeechRecognizer&) = delete;

    bool Load(const SpeechOptions& options, std::string* error);
    bool Ready() const;
    // mono samples in -1..1; the model wants 16000 Hz (sherpa-onnx resamples another rate itself).
    // The transcript is UTF-8, as the recognizer prints it: capitals and punctuation included
    bool Transcribe(const float* samples, size_t count, int sample_rate, std::string* text, std::string* error) const;
    // "sherpa-onnx 1.13.8"
    static std::string Backend();

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace coop
