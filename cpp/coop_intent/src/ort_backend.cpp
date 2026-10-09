// OrtBackend: the model in ONNX Runtime's C++ API (standalone build only; UE5 goes through NNE).
//
// The C++ API is initialized by hand, with the API level of the runtime that is actually loaded: built
// against the 1.30 headers, the engine still runs on an older onnxruntime.dll. A process holds one
// onnxruntime.dll, and with speech-to-text that is the one sherpa-onnx was built with (CMakeLists.txt).
// Everything called here has been in the C API for many versions.
#define ORT_API_MANUAL_INIT
#include <onnxruntime_cxx_api.h>
#undef ORT_API_MANUAL_INIT

#include <array>
#include <cstdlib>
#include <mutex>

#include "coop_intent/intent_model.h"
#include "coop_intent/unicode.h"

namespace coop {

namespace {

// "1.28.2" -> 28: the newest API level this runtime has (asking it for a newer one fails, and it says so on stderr)
bool InitOrt(std::string* error) {
    static std::once_flag once;
    static bool ok = false;
    std::call_once(once, [] {
        const OrtApiBase* base = OrtGetApiBase();
        const char* version = base->GetVersionString();
        const char* dot = version;
        while (*dot && *dot != '.') ++dot;
        const int minor = *dot ? std::atoi(dot + 1) : 0;
        const OrtApi* api = base->GetApi(static_cast<uint32_t>(minor > 0 && minor < ORT_API_VERSION ? minor : ORT_API_VERSION));
        if (api) Ort::InitApi(api);
        ok = api != nullptr;
    });
    if (!ok && error) *error = std::string("ONNX Runtime ") + OrtGetApiBase()->GetVersionString() + " gave no API";
    return ok;
}

}  // namespace

std::string OrtBackend::RuntimeVersion() { return OrtGetApiBase()->GetVersionString(); }

struct OrtBackend::Impl {
    Ort::Env env{ORT_LOGGING_LEVEL_WARNING, "coop_intent"};
    std::unique_ptr<Ort::Session> session;
    Ort::MemoryInfo cpu = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
};

OrtBackend::OrtBackend() = default;
OrtBackend::~OrtBackend() = default;

bool OrtBackend::Load(const std::string& path, const Options& o, std::string* error) {
    if (!InitOrt(error)) return false;
    try {
        impl_ = std::make_unique<Impl>();
        Ort::SessionOptions so;
        so.SetIntraOpNumThreads(o.threads);
        so.SetInterOpNumThreads(1);
        so.SetExecutionMode(ORT_SEQUENTIAL);
        so.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
        so.AddConfigEntry("session.intra_op.allow_spinning", o.allow_spinning ? "1" : "0");
#ifdef _WIN32
        std::wstring wpath;   // ONNX Runtime takes a wide path on Windows
        for (char32_t c : DecodeUtf8(path)) {
            if (c < 0x10000) {
                wpath.push_back(static_cast<wchar_t>(c));
            } else {
                wpath.push_back(static_cast<wchar_t>(0xD800 + ((c - 0x10000) >> 10)));
                wpath.push_back(static_cast<wchar_t>(0xDC00 + ((c - 0x10000) & 0x3FF)));
            }
        }
        impl_->session = std::make_unique<Ort::Session>(impl_->env, wpath.c_str(), so);
#else
        impl_->session = std::make_unique<Ort::Session>(impl_->env, path.c_str(), so);
#endif
        return true;
    } catch (const Ort::Exception& e) {
        impl_.reset();
        if (error) *error = e.what();
        return false;
    }
}

bool OrtBackend::Run(const std::vector<int64_t>& ids, std::vector<float>* logits, std::string* error) {
    if (!impl_ || !impl_->session) {
        if (error) *error = "model not loaded";
        return false;
    }
    try {
        // local buffers: Session::Run is thread-safe, and so is this as long as each caller owns its ids
        std::vector<int64_t> mask(ids.size(), 1);
        const std::array<int64_t, 2> shape{1, static_cast<int64_t>(ids.size())};
        std::array<Ort::Value, 2> inputs{
            Ort::Value::CreateTensor<int64_t>(impl_->cpu, const_cast<int64_t*>(ids.data()), ids.size(),
                                              shape.data(), shape.size()),
            Ort::Value::CreateTensor<int64_t>(impl_->cpu, mask.data(), mask.size(), shape.data(), shape.size())};
        static const char* kIn[] = {"input_ids", "attention_mask"};
        static const char* kOut[] = {"logits"};
        auto out = impl_->session->Run(Ort::RunOptions{nullptr}, kIn, inputs.data(), inputs.size(), kOut, 1);
        const auto info = out[0].GetTensorTypeAndShapeInfo();
        const float* data = out[0].GetTensorData<float>();
        logits->assign(data, data + info.GetElementCount());
        return true;
    } catch (const Ort::Exception& e) {
        if (error) *error = e.what();
        return false;
    }
}

}  // namespace coop
