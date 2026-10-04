// OrtBackend: the model in ONNX Runtime's C++ API (standalone build only; UE5 goes through NNE).
#include <onnxruntime_cxx_api.h>

#include <array>

#include "coop_intent/intent_model.h"
#include "coop_intent/unicode.h"

namespace coop {

struct OrtBackend::Impl {
    Ort::Env env{ORT_LOGGING_LEVEL_WARNING, "coop_intent"};
    std::unique_ptr<Ort::Session> session;
    Ort::MemoryInfo cpu = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
};

OrtBackend::OrtBackend() = default;
OrtBackend::~OrtBackend() = default;

bool OrtBackend::Load(const std::string& path, const Options& o, std::string* error) {
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
