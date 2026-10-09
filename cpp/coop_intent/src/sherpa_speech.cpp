// SpeechRecognizer on sherpa-onnx's C API: an offline NeMo transducer (Parakeet TDT), greedy search,
// the configuration scripts/coop/stt/run_stt.py gives the Python package ("nemo_transducer").
#include "coop_intent/speech.h"

#include <cstring>
#include <filesystem>
#include <fstream>
#include <limits>

#include "sherpa-onnx/c-api/c-api.h"

namespace coop {

struct SpeechRecognizer::Impl {
    const SherpaOnnxOfflineRecognizer* recognizer = nullptr;
    ~Impl() {
        if (recognizer) SherpaOnnxDestroyOfflineRecognizer(recognizer);
    }
};

SpeechRecognizer::SpeechRecognizer() : impl_(new Impl) {}
SpeechRecognizer::~SpeechRecognizer() = default;

bool SpeechRecognizer::Ready() const { return impl_->recognizer != nullptr; }

std::string SpeechRecognizer::Backend() { return std::string("sherpa-onnx ") + SherpaOnnxGetVersionStr(); }

bool SpeechRecognizer::Load(const SpeechOptions& options, std::string* error) {
    const std::string encoder = options.model_dir + "/encoder.int8.onnx", decoder = options.model_dir + "/decoder.int8.onnx",
                      joiner = options.model_dir + "/joiner.int8.onnx", tokens = options.model_dir + "/tokens.txt";
    // sherpa-onnx reports a missing file on stderr and may not return: name it here instead
    for (const std::string* f : {&encoder, &decoder, &joiner, &tokens}) {
        if (!std::ifstream(std::filesystem::u8path(*f), std::ios::binary)) {
            if (error) *error = "cannot open " + *f;
            return false;
        }
    }
    SherpaOnnxOfflineRecognizerConfig config;
    std::memset(&config, 0, sizeof config);   // every model family and option the C API has, switched off
    config.feat_config.sample_rate = 16000;
    config.feat_config.feature_dim = 80;
    config.model_config.transducer.encoder = encoder.c_str();
    config.model_config.transducer.decoder = decoder.c_str();
    config.model_config.transducer.joiner = joiner.c_str();
    config.model_config.tokens = tokens.c_str();
    config.model_config.num_threads = options.threads;
    config.model_config.provider = "cpu";
    config.model_config.model_type = "nemo_transducer";
    config.decoding_method = "greedy_search";
    const SherpaOnnxOfflineRecognizer* r = SherpaOnnxCreateOfflineRecognizer(&config);
    if (!r) {
        if (error) *error = "sherpa-onnx refused the model in " + options.model_dir;
        return false;
    }
    if (impl_->recognizer) SherpaOnnxDestroyOfflineRecognizer(impl_->recognizer);
    impl_->recognizer = r;
    return true;
}

bool SpeechRecognizer::Transcribe(const float* samples, size_t count, int sample_rate, std::string* text,
                                  std::string* error) const {
    text->clear();
    if (!impl_->recognizer) {
        if (error) *error = "the speech recognizer is not loaded";
        return false;
    }
    if (count > static_cast<size_t>(std::numeric_limits<int32_t>::max())) {
        if (error) *error = "the clip is too long";
        return false;
    }
    if (count == 0) return true;
    const SherpaOnnxOfflineStream* stream = SherpaOnnxCreateOfflineStream(impl_->recognizer);
    if (!stream) {
        if (error) *error = "sherpa-onnx gave no stream";
        return false;
    }
    SherpaOnnxAcceptWaveformOffline(stream, sample_rate, samples, static_cast<int32_t>(count));
    SherpaOnnxDecodeOfflineStream(impl_->recognizer, stream);
    const SherpaOnnxOfflineRecognizerResult* result = SherpaOnnxGetOfflineStreamResult(stream);
    if (result && result->text) *text = result->text;
    if (result) SherpaOnnxDestroyOfflineRecognizerResult(result);
    SherpaOnnxDestroyOfflineStream(stream);
    return true;
}

}  // namespace coop
