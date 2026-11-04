// PiperVoice on sherpa-onnx's C API: a VITS model with espeak-ng phonemes, the configuration sherpa-onnx's own
// Piper examples give it; the noise scales and the length scale are the ones the model's .onnx.json carries.
#include "coop_intent/voice.h"

#include <algorithm>

#include <cstring>
#include <filesystem>
#include <fstream>

#include "nlohmann/json.hpp"
#include "sherpa-onnx/c-api/c-api.h"

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif

namespace coop {

namespace {

#ifdef _WIN32
// The CUDA 12 and cuDNN 9 libraries ONNX Runtime's CUDA provider loads by name (onnxruntime_providers_cuda.dll: cudart64_12,
// cublas64_12, cufft64_11, cudnn64_9): their folders go in front of this process's PATH, once. COOP_CUDA_DLL_DIRS (folders
// separated by ";") first; then the highest CUDA_PATH_V12_* the CUDA installer set, else the toolkit's v12.* folder; then
// cuDNN 9's folder for CUDA 12 under CUDNN_PATH or the default install. CUDA_PATH alone may name CUDA 13, whose are not these.
std::string Env(const char* name) {
    const DWORD n = GetEnvironmentVariableA(name, nullptr, 0);
    if (n == 0) return {};
    std::string value(n, '\0');
    value.resize(GetEnvironmentVariableA(name, value.data(), n));
    return value;
}

std::string CudaDllDirs() {
    namespace fs = std::filesystem;
    std::vector<fs::path> dirs;
    std::error_code ec;
    auto has = [&ec](const fs::path& dir, const char* file) { return fs::exists(dir / file, ec); };
    if (const std::string list = Env("COOP_CUDA_DLL_DIRS"); !list.empty()) {
        size_t at = 0;
        while (at <= list.size()) {
            const size_t end = list.find(';', at);
            const std::string one = list.substr(at, end == std::string::npos ? std::string::npos : end - at);
            if (!one.empty()) dirs.emplace_back(one);
            if (end == std::string::npos) break;
            at = end + 1;
        }
    }
    fs::path cuda;
    for (int minor = 20; minor >= 0 && cuda.empty(); --minor) {
        const std::string name = "CUDA_PATH_V12_" + std::to_string(minor);
        if (const std::string v = Env(name.c_str()); !v.empty() && has(fs::path(v) / "bin", "cudart64_12.dll")) cuda = fs::path(v) / "bin";
    }
    const fs::path toolkit = R"(C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA)";
    if (cuda.empty() && fs::is_directory(toolkit, ec)) {
        std::vector<fs::path> found;
        for (const auto& e : fs::directory_iterator(toolkit, ec))
            if (e.path().filename().string().rfind("v12.", 0) == 0 && has(e.path() / "bin", "cudart64_12.dll")) found.push_back(e.path() / "bin");
        std::sort(found.begin(), found.end());
        if (!found.empty()) cuda = found.back();
    }
    if (!cuda.empty()) dirs.push_back(cuda);
    std::vector<fs::path> roots;
    if (const std::string v = Env("CUDNN_PATH"); !v.empty()) roots.emplace_back(v);
    const fs::path cudnn_root = R"(C:\Program Files\NVIDIA\CUDNN)";
    if (fs::is_directory(cudnn_root, ec))
        for (const auto& e : fs::directory_iterator(cudnn_root, ec))
            if (e.path().filename().string().rfind("v9", 0) == 0) roots.push_back(e.path());
    std::vector<fs::path> cudnn;
    for (const fs::path& root : roots) {
        if (has(root / "bin", "cudnn64_9.dll")) cudnn.push_back(root / "bin");
        if (fs::is_directory(root / "bin", ec))
            for (const auto& e : fs::directory_iterator(root / "bin", ec))
                if (e.path().filename().string().rfind("12.", 0) == 0 && has(e.path(), "cudnn64_9.dll")) cudnn.push_back(e.path());
    }
    std::sort(cudnn.begin(), cudnn.end());
    if (!cudnn.empty()) dirs.push_back(cudnn.back());
    std::string joined;
    for (const fs::path& d : dirs) joined += (joined.empty() ? "" : ";") + d.string();
    return joined;
}

// sherpa-onnx's CUDA build next to the exe: its ONNX Runtime brings onnxruntime_providers_cuda.dll (a CPU build answers
// "cuda" by running on the CPU, and the voice would be said to be on the GPU)
bool CudaBuild() {
    char exe[MAX_PATH] = {};
    const DWORD n = GetModuleFileNameA(nullptr, exe, MAX_PATH);
    if (n == 0 || n >= MAX_PATH) return false;
    std::error_code ec;
    return std::filesystem::exists(std::filesystem::path(exe).parent_path() / "onnxruntime_providers_cuda.dll", ec);
}

void PrepareCuda() {
    static bool done = false;
    if (done) return;
    done = true;
    const std::string dirs = CudaDllDirs();
    if (dirs.empty()) return;
    const DWORD n = GetEnvironmentVariableA("PATH", nullptr, 0);
    std::string path(n, '\0');
    if (n) path.resize(GetEnvironmentVariableA("PATH", path.data(), n));
    SetEnvironmentVariableA("PATH", (dirs + ";" + path).c_str());
}
#else
bool CudaBuild() { return true; }
void PrepareCuda() {}
#endif

}  // namespace

struct PiperVoice::Impl {
    const SherpaOnnxOfflineTts* tts = nullptr;
    std::string provider = "cpu";        // where it runs
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

const std::string& PiperVoice::Provider() const { return impl_->provider; }

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
    config.max_num_sentences = 1;
    // on the GPU when asked ("auto": a Kokoro voice only) and it loads there; else on the CPU (a CPU build of sherpa-onnx says
    // "Fallback to cpu" and runs on the CPU itself; the CUDA build with no CUDA or cuDNN on the machine refuses the voice: then
    // the CPU here)
    const bool gpu = (options.provider == "cuda" || (options.provider == "auto" && kokoro)) && CudaBuild();
    if (gpu) PrepareCuda();
    config.model.provider = gpu ? "cuda" : "cpu";
    const SherpaOnnxOfflineTts* tts = SherpaOnnxCreateOfflineTts(&config);
    std::string provider = gpu ? "cuda" : "cpu";
    if (!tts && gpu) {
        config.model.provider = "cpu";
        tts = SherpaOnnxCreateOfflineTts(&config);
        provider = "cpu";
    }
    if (!tts) return fail("sherpa-onnx refused the voice in " + options.model_dir);
    impl_->provider = provider;
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
