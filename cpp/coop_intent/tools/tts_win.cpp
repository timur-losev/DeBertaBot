// Tts on Windows: SAPI 5 (sapi.h, ole32). The first voice whose language is English (LCID 409): the
// system default may be another language's, and it would spell the bot's English lines out.
#include "tts.h"

#define NOMINMAX
#include <windows.h>
#include <sapi.h>

#include <string>

struct Tts::Impl {
    ISpVoice* voice = nullptr;
    bool com = false;
    std::string name;
};

Tts::Tts() : impl_(new Impl) {}

Tts::~Tts() {
    if (impl_->voice) impl_->voice->Release();
    if (impl_->com) CoUninitialize();
}

static std::wstring Wide(const std::string& utf8) {
    if (utf8.empty()) return std::wstring();
    const int n = MultiByteToWideChar(CP_UTF8, 0, utf8.data(), static_cast<int>(utf8.size()), nullptr, 0);
    std::wstring w(static_cast<size_t>(n), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, utf8.data(), static_cast<int>(utf8.size()), w.data(), n);
    return w;
}

static std::string Narrow(const wchar_t* w) {
    if (!w) return std::string();
    const int n = WideCharToMultiByte(CP_UTF8, 0, w, -1, nullptr, 0, nullptr, nullptr);
    std::string s(static_cast<size_t>(n > 0 ? n - 1 : 0), '\0');
    if (n > 1) WideCharToMultiByte(CP_UTF8, 0, w, -1, s.data(), n, nullptr, nullptr);
    return s;
}

bool Tts::Start(std::string* error) {
    Impl& s = *impl_;
    const HRESULT init = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    s.com = SUCCEEDED(init);
    if (FAILED(CoCreateInstance(__uuidof(SpVoice), nullptr, CLSCTX_ALL, __uuidof(ISpVoice), reinterpret_cast<void**>(&s.voice))) || !s.voice) {
        s.voice = nullptr;
        return *error = "the system speech synthesizer (SAPI) is not available", false;
    }
    ISpObjectTokenCategory* category = nullptr;
    if (SUCCEEDED(CoCreateInstance(__uuidof(SpObjectTokenCategory), nullptr, CLSCTX_ALL, __uuidof(ISpObjectTokenCategory),
                                   reinterpret_cast<void**>(&category))) && category) {
        IEnumSpObjectTokens* tokens = nullptr;
        if (SUCCEEDED(category->SetId(SPCAT_VOICES, FALSE)) && SUCCEEDED(category->EnumTokens(L"Language=409", nullptr, &tokens)) && tokens) {
            ISpObjectToken* token = nullptr;
            ULONG got = 0;
            if (tokens->Next(1, &token, &got) == S_OK && token) {
                s.voice->SetVoice(token);
                wchar_t* text = nullptr;
                if (SUCCEEDED(token->GetStringValue(nullptr, &text)) && text) {
                    s.name = Narrow(text);
                    CoTaskMemFree(text);
                }
                token->Release();
            }
            tokens->Release();
        }
        category->Release();
    }
    if (s.name.empty()) s.name = "the system default voice (no English voice is installed)";
    s.voice->SetRate(2);   // a teammate talks a little faster than a narrator
    return true;
}

void Tts::Say(const std::string& utf8) {
    if (!impl_->voice || utf8.empty()) return;
    const std::wstring w = Wide(utf8);
    impl_->voice->Speak(w.c_str(), SPF_ASYNC | SPF_PURGEBEFORESPEAK | SPF_IS_NOT_XML, nullptr);
}

void Tts::Stop() {
    if (impl_->voice) impl_->voice->Speak(nullptr, SPF_PURGEBEFORESPEAK, nullptr);
}

const std::string& Tts::Voice() const { return impl_->name; }
