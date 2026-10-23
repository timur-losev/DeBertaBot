// The bot's voice as audio: Piper (a VITS model, by default the en_GB vctk-medium export with 109 speakers)
// through sherpa-onnx's C API, the library that already runs the speech recognizer. coop_cli --serve --tts-piper
// hands the game each line as 16-bit samples, and the game plays them from the bot (tools/coop_cli.cpp, RunServe).
//
//   line --PiperVoice::Speak--> mono samples at SampleRate() (22050 Hz for vctk-medium)
//
// A model directory holds what sherpa-onnx's Piper exports hold: one <name>.onnx, its <name>.onnx.json (the speaker
// names), tokens.txt and espeak-ng-data/. Or a Kokoro model as sherpa-onnx exports it (model.onnx, voices.bin,
// tokens.txt, espeak-ng-data/; 2026-10-23, the Spanish test voice em_santa): its speakers go by number. Either may
// hold a voice.json, {"speaker": "53", "lang": "es"}, the speaker and the language used when none is asked for.
#pragma once

#include <memory>
#include <string>
#include <vector>

namespace coop {

struct VoiceOptions {
    std::string model_dir;
    // a speaker of the model, by its name in <name>.onnx.json ("p311") or its number ("38"); empty: the first
    std::string speaker;
    int threads = 1;
    // > 1 speaks faster (the model's length scale is divided by it)
    float speed = 1.0f;
    // a Kokoro model's language ("es"); empty: voice.json's, else the model's default
    std::string lang;
};

class PiperVoice {
public:
    PiperVoice();
    ~PiperVoice();
    PiperVoice(const PiperVoice&) = delete;
    PiperVoice& operator=(const PiperVoice&) = delete;

    bool Load(const VoiceOptions& options, std::string* error);
    bool Ready() const;
    // mono samples in -1..1 at SampleRate(). Speaker: as in VoiceOptions, empty for the one loaded; speed 0: as loaded
    bool Speak(const std::string& utf8, std::vector<float>* samples, std::string* error, const std::string& speaker = {},
               float speed = 0.0f) const;
    int SampleRate() const;
    int NumSpeakers() const;
    // a speaker's number by name or number, -1 when the model has no such speaker
    int SpeakerId(const std::string& speaker) const;
    // every speaker's name, in the model's order of numbers
    std::vector<std::string> Speakers() const;
    // "en_GB-vctk-medium, p311 (38 of 109)", for the log
    std::string Describe() const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace coop
