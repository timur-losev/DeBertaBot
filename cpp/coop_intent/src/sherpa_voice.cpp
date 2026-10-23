// PiperVoice on sherpa-onnx's C API: a VITS model with espeak-ng phonemes, the configuration sherpa-onnx's own
// Piper examples give it; the noise scales and the length scale are the ones the model's .onnx.json carries.
#include "coop_intent/voice.h"

#include <algorithm>
#include <cstring>
#include <filesystem>
#include <fstream>

#include "nlohmann/json.hpp"
#include "sherpa-onnx/c-api/c-api.h"

namespace coop {

struct PiperVoice::Impl {
    const SherpaOnnxOfflineTts* tts = nullptr;
    std::string name;                    // the model's file name without .onnx
    std::vector<std::string> speakers;   // by number
    int speaker = 0;
    float speed = 1.0f;
    ~Impl() {
        if (tts) SherpaOnnxDestroyOfflineTts(tts);
    }
};

PiperVoice::PiperVoice() : impl_(new Impl) {}
PiperVoice::~PiperVoice() = default;

bool PiperVoice::Ready() const { return impl_->tts != nullptr; }

int PiperVoice::SampleRate() const { return impl_->tts ? SherpaOnnxOfflineTtsSampleRate(impl_->tts) : 0; }

int PiperVoice::NumSpeakers() const { return impl_->tts ? SherpaOnnxOfflineTtsNumSpeakers(impl_->tts) : 0; }

std::vector<std::string> PiperVoice::Speakers() const { return impl_->speakers; }

int PiperVoice::SpeakerId(const std::string& speaker) const {
    if (speaker.empty()) return impl_->speaker;
    for (size_t i = 0; i < impl_->speakers.size(); ++i)
        if (impl_->speakers[i] == speaker) return static_cast<int>(i);
    if (speaker.find_first_not_of("0123456789") == std::string::npos && speaker.size() < 6) {
        const int n = std::stoi(speaker);
        if (n >= 0 && n < std::max(1, NumSpeakers())) return n;
    }
    return -1;
}

std::string PiperVoice::Describe() const {
    const int n = NumSpeakers();
    const std::string who = impl_->speaker < static_cast<int>(impl_->speakers.size()) ? impl_->speakers[static_cast<size_t>(impl_->speaker)]
                                                                                      : std::to_string(impl_->speaker);
    return "piper " + impl_->name + (n > 1 ? ", " + who + " (" + std::to_string(impl_->speaker) + " of " + std::to_string(n) + ")" : std::string());
}

bool PiperVoice::Load(const VoiceOptions& options, std::string* error) {
    namespace fs = std::filesystem;
    auto fail = [&](const std::string& message) {
        if (error) *error = message;
        return false;
    };
    const fs::path dir = fs::u8path(options.model_dir);
    fs::path model;
    std::error_code ec;
    for (const fs::directory_entry& e : fs::directory_iterator(dir, ec))
        if (e.is_regular_file() && e.path().extension() == ".onnx") model = e.path();
    if (model.empty()) return fail("no .onnx model in " + options.model_dir);
    const fs::path tokens = dir / "tokens.txt", data = dir / "espeak-ng-data", card = fs::path(model.u8string() + ".json");
    if (!fs::exists(tokens)) return fail("no tokens.txt in " + options.model_dir);
    if (!fs::is_directory(data)) return fail("no espeak-ng-data in " + options.model_dir);
    // the deploy's choice of speaker and language for this folder
    std::string speaker_default, lang = options.lang;
    if (std::ifstream vin{dir / "voice.json"}) {
        try {
            const nlohmann::json v = nlohmann::json::parse(vin);
            speaker_default = v.value("speaker", std::string());
            if (lang.empty()) lang = v.value("lang", std::string());
        } catch (const std::exception& e) {
            return fail((dir / "voice.json").u8string() + ": " + e.what());
        }
    }
    const fs::path voices = dir / "voices.bin";
    const bool kokoro = fs::exists(voices);

    // the speakers' names and the scales the model was published with
    float noise = 0.667f, noise_w = 0.8f, length = 1.0f;
    std::vector<std::string> speakers;
    if (std::ifstream in{card}) {
        try {
            const nlohmann::json j = nlohmann::json::parse(in);
            if (j.contains("inference")) {
                const nlohmann::json& inf = j["inference"];
                noise = inf.value("noise_scale", noise);
                noise_w = inf.value("noise_w", noise_w);
                length = inf.value("length_scale", length);
            }
            if (j.contains("speaker_id_map") && j["speaker_id_map"].is_object()) {
                speakers.resize(j["speaker_id_map"].size());
                for (auto it = j["speaker_id_map"].begin(); it != j["speaker_id_map"].end(); ++it) {
                    const int n = it.value().get<int>();
                    if (n >= 0 && n < static_cast<int>(speakers.size())) speakers[static_cast<size_t>(n)] = it.key();
                }
            }
        } catch (const std::exception& e) {
            return fail(card.u8string() + ": " + e.what());
        }
    }

    const std::string model_s = model.u8string(), tokens_s = tokens.u8string(), data_s = data.u8string(), voices_s = voices.u8string();
    SherpaOnnxOfflineTtsConfig config;
    std::memset(&config, 0, sizeof config);   // every other model family and option of the C API, switched off
    if (kokoro) {
        config.model.kokoro.model = model_s.c_str();
        config.model.kokoro.voices = voices_s.c_str();
        config.model.kokoro.tokens = tokens_s.c_str();
        config.model.kokoro.data_dir = data_s.c_str();
        config.model.kokoro.length_scale = 1.0f;
        config.model.kokoro.lang = lang.c_str();
    } else {
        config.model.vits.model = model_s.c_str();
        config.model.vits.tokens = tokens_s.c_str();
        config.model.vits.data_dir = data_s.c_str();
        config.model.vits.noise_scale = noise;
        config.model.vits.noise_scale_w = noise_w;
        config.model.vits.length_scale = length;
    }
    config.model.num_threads = options.threads;
    config.model.provider = "cpu";
    config.max_num_sentences = 1;
    const SherpaOnnxOfflineTts* tts = SherpaOnnxCreateOfflineTts(&config);
    if (!tts) return fail("sherpa-onnx refused the voice in " + options.model_dir);
    if (impl_->tts) SherpaOnnxDestroyOfflineTts(impl_->tts);
    impl_->tts = tts;
    impl_->name = kokoro ? "kokoro " + dir.filename().u8string() : model.stem().u8string();
    impl_->speakers = std::move(speakers);
    impl_->speed = options.speed > 0 ? options.speed : 1.0f;
    impl_->speaker = 0;
    const std::string asked = options.speaker.empty() ? speaker_default : options.speaker;
    const int speaker = SpeakerId(asked);
    if (speaker < 0) return fail("the voice " + impl_->name + " has no speaker " + asked);
    impl_->speaker = speaker;
    return true;
}

bool PiperVoice::Speak(const std::string& utf8, std::vector<float>* samples, std::string* error, const std::string& speaker, float speed) const {
    samples->clear();
    if (!impl_->tts) {
        if (error) *error = "the voice is not loaded";
        return false;
    }
    const int sid = SpeakerId(speaker);
    if (sid < 0) {
        if (error) *error = "the voice " + impl_->name + " has no speaker " + speaker;
        return false;
    }
    if (utf8.empty()) return true;
    SherpaOnnxGenerationConfig config;
    std::memset(&config, 0, sizeof config);
    config.sid = sid;
    config.speed = speed > 0 ? speed : impl_->speed;
    config.silence_scale = 0.2f;
    const SherpaOnnxGeneratedAudio* audio = SherpaOnnxOfflineTtsGenerateWithConfig(impl_->tts, utf8.c_str(), &config, nullptr, nullptr);
    if (!audio) {
        if (error) *error = "sherpa-onnx made no audio of \"" + utf8 + "\"";
        return false;
    }
    samples->assign(audio->samples, audio->samples + audio->n);
    SherpaOnnxDestroyOfflineTtsGeneratedAudio(audio);
    return true;
}

}  // namespace coop
