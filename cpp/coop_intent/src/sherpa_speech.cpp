// SpeechRecognizer on sherpa-onnx's C API: an offline NeMo transducer (Parakeet TDT), greedy search,
// the configuration scripts/coop/stt/run_stt.py gives the Python package ("nemo_transducer").
#include "coop_intent/speech.h"

#include <cstring>
#include <filesystem>
#include <fstream>
#include <limits>

#include "sherpa-onnx/c-api/c-api.h"

namespace coop {

namespace {

// Parakeet TDT v3 has no ё among its tokens: «пошёл» comes out «пош<unk>л» (2026-11-01, the owner's «Ты куда пош<unk>л?» was read
// as HOLSTER). An <unk> with a Cyrillic letter beside it is ё; any other is left as it is
bool CyrillicByte(const std::string& s, size_t at, bool before) {
    // a Cyrillic letter in UTF-8 is two bytes, the first 0xD0 or 0xD1
    if (before) return at >= 2 && (static_cast<unsigned char>(s[at - 2]) == 0xD0 || static_cast<unsigned char>(s[at - 2]) == 0xD1);
    return at < s.size() && (static_cast<unsigned char>(s[at]) == 0xD0 || static_cast<unsigned char>(s[at]) == 0xD1);
}

std::string WithYo(std::string s) {
    static const std::string kUnk = "<unk>";
    for (size_t at = s.find(kUnk); at != std::string::npos; at = s.find(kUnk, at)) {
        if (CyrillicByte(s, at, true) || CyrillicByte(s, at + kUnk.size(), false)) {
            s.replace(at, kUnk.size(), "\xD1\x91");   // ё
            at += 2;
        } else {
            at += kUnk.size();
        }
    }
    return s;
}

}  // namespace

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

std::string SpeechRecognizer::RuntimeVersion() { return SherpaOnnxGetOnnxruntimeVersionStr(); }

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
                                  std::string* error, std::vector<SpeechWord>* words) const {
    text->clear();
    if (words) words->clear();
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
    if (result && result->text) *text = WithYo(result->text);
    if (words && result && result->timestamps && result->tokens_arr && result->count > 0) {
        std::vector<std::string> tokens;
        std::vector<float> starts;
        for (int32_t i = 0; i < result->count; ++i) {
            tokens.emplace_back(result->tokens_arr[i] ? result->tokens_arr[i] : "");
            starts.push_back(result->timestamps[i]);
        }
        *words = SpeechWords(tokens, starts);
        for (SpeechWord& w : *words) w.text = WithYo(w.text);
    }
    if (result) SherpaOnnxDestroyOfflineRecognizerResult(result);
    SherpaOnnxDestroyOfflineStream(stream);
    return true;
}

// ---- VoiceActivity: Silero VAD through sherpa-onnx's C API -----------------------------------------------------------------

struct VoiceActivity::Impl {
    const SherpaOnnxVoiceActivityDetector* vad = nullptr;
    std::string model;   // the config keeps the pointer
    VadOptions options;
    std::vector<float> pending;   // less than a window, until the next Accept
    long long fed = 0;
    static constexpr int kWindow = 512;   // Silero v5 at 16 kHz
    ~Impl() {
        if (vad) SherpaOnnxDestroyVoiceActivityDetector(vad);
    }
};

VoiceActivity::VoiceActivity() : impl_(new Impl) {}
VoiceActivity::~VoiceActivity() = default;

bool VoiceActivity::Ready() const { return impl_->vad != nullptr; }

bool VoiceActivity::Load(const VadOptions& options, std::string* error) {
    if (!std::ifstream(std::filesystem::u8path(options.model), std::ios::binary)) {
        if (error) *error = "cannot open " + options.model;
        return false;
    }
    Impl& s = *impl_;
    if (s.vad) SherpaOnnxDestroyVoiceActivityDetector(s.vad), s.vad = nullptr;
    s.options = options;
    s.model = options.model;
    SherpaOnnxVadModelConfig config;
    std::memset(&config, 0, sizeof config);
    config.silero_vad.model = s.model.c_str();
    config.silero_vad.threshold = options.threshold;
    config.silero_vad.min_silence_duration = options.min_silence;
    config.silero_vad.min_speech_duration = options.min_speech;
    config.silero_vad.max_speech_duration = options.max_speech;
    config.silero_vad.window_size = Impl::kWindow;
    config.sample_rate = kSampleRate;
    config.num_threads = 1;
    config.provider = "cpu";
    s.vad = SherpaOnnxCreateVoiceActivityDetector(&config, options.max_speech + 10.0f);
    s.pending.clear();
    s.fed = 0;
    if (!s.vad) {
        if (error) *error = "sherpa-onnx refused the voice detector " + options.model;
        return false;
    }
    return true;
}

void VoiceActivity::Accept(const float* samples, size_t count) {
    Impl& s = *impl_;
    if (!s.vad) return;
    s.pending.insert(s.pending.end(), samples, samples + count);
    size_t at = 0;
    for (; at + Impl::kWindow <= s.pending.size(); at += Impl::kWindow) {
        SherpaOnnxVoiceActivityDetectorAcceptWaveform(s.vad, s.pending.data() + at, Impl::kWindow);
        s.fed += Impl::kWindow;
    }
    s.pending.erase(s.pending.begin(), s.pending.begin() + static_cast<std::ptrdiff_t>(at));
}

bool VoiceActivity::Speaking() const { return impl_->vad && SherpaOnnxVoiceActivityDetectorDetected(impl_->vad) != 0; }

bool VoiceActivity::Pop(VadPhrase* out) {
    Impl& s = *impl_;
    if (!s.vad || SherpaOnnxVoiceActivityDetectorEmpty(s.vad)) return false;
    const SherpaOnnxSpeechSegment* seg = SherpaOnnxVoiceActivityDetectorFront(s.vad);
    if (seg) {
        out->start = seg->start;
        out->samples.assign(seg->samples, seg->samples + seg->n);
        SherpaOnnxDestroySpeechSegment(seg);
    }
    SherpaOnnxVoiceActivityDetectorPop(s.vad);
    return seg != nullptr;
}

void VoiceActivity::Reset() {
    Impl& s = *impl_;
    if (!s.vad) return;
    // made again: a phrase's start counts from 0 for certain (the C API does not say whether its reset restarts the count)
    const VadOptions options = s.options;
    std::string unused;
    Load(options, &unused);
}

long long VoiceActivity::Fed() const { return impl_->fed; }

}  // namespace coop
