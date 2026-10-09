// MicCapture on Windows: waveIn (winmm), PCM 16 kHz mono 16-bit from the default device -- the audio
// stack converts whatever the device runs at. A worker thread hands the 20 ms buffers back to the driver
// as they fill; between clips only the last kPreRollSeconds are remembered.
#include "mic_capture.h"

#define NOMINMAX
#include <windows.h>
#include <mmsystem.h>

#include <array>
#include <atomic>
#include <deque>
#include <mutex>
#include <thread>

struct MicCapture::Impl {
    static constexpr int kBuffers = 16, kFrames = MicCapture::kSampleRate / 50;   // 20 ms each
    HWAVEIN device = nullptr;
    HANDLE filled = nullptr;      // signalled by the driver when a buffer is done
    std::array<WAVEHDR, kBuffers> headers{};
    std::array<std::array<short, kFrames>, kBuffers> data{};
    std::thread worker;
    std::atomic<bool> stop{false};
    std::mutex lock;
    std::deque<short> recent;     // the pre-roll, when no clip is being taken
    std::vector<short> clip;
    bool taking = false;

    void Run() {
        while (!stop.load()) {
            WaitForSingleObject(filled, 100);
            for (WAVEHDR& h : headers) {
                if (!(h.dwFlags & WHDR_DONE)) continue;
                const short* p = reinterpret_cast<const short*>(h.lpData);
                const size_t n = h.dwBytesRecorded / sizeof(short);
                {
                    std::lock_guard<std::mutex> g(lock);
                    if (taking) {
                        clip.insert(clip.end(), p, p + n);
                    } else {
                        recent.insert(recent.end(), p, p + n);
                        const size_t keep = static_cast<size_t>(MicCapture::kPreRollSeconds * MicCapture::kSampleRate);
                        while (recent.size() > keep) recent.pop_front();
                    }
                }
                h.dwFlags &= ~static_cast<DWORD>(WHDR_DONE);
                if (!stop.load()) waveInAddBuffer(device, &h, sizeof h);
            }
        }
    }
};

MicCapture::MicCapture() : impl_(new Impl) {}

MicCapture::~MicCapture() {
    Impl& s = *impl_;
    s.stop.store(true);
    if (s.worker.joinable()) s.worker.join();
    if (s.device) {
        waveInReset(s.device);
        for (WAVEHDR& h : s.headers)
            if (h.dwFlags & WHDR_PREPARED) waveInUnprepareHeader(s.device, &h, sizeof h);
        waveInClose(s.device);
    }
    if (s.filled) CloseHandle(s.filled);
}

bool MicCapture::Start(std::string* error) {
    Impl& s = *impl_;
    if (waveInGetNumDevs() == 0) return *error = "no audio input device", false;
    WAVEFORMATEX f{};
    f.wFormatTag = WAVE_FORMAT_PCM;
    f.nChannels = 1;
    f.nSamplesPerSec = kSampleRate;
    f.wBitsPerSample = 16;
    f.nBlockAlign = 2;
    f.nAvgBytesPerSec = kSampleRate * 2;
    s.filled = CreateEventW(nullptr, FALSE, FALSE, nullptr);
    const MMRESULT r = waveInOpen(&s.device, WAVE_MAPPER, &f, reinterpret_cast<DWORD_PTR>(s.filled), 0, CALLBACK_EVENT);
    if (r != MMSYSERR_NOERROR) {
        char text[MAXERRORLENGTH] = "";
        waveInGetErrorTextA(r, text, sizeof text);
        s.device = nullptr;
        return *error = std::string("cannot open the default microphone: ") + text, false;
    }
    for (int i = 0; i < Impl::kBuffers; ++i) {
        WAVEHDR& h = s.headers[static_cast<size_t>(i)];
        h.lpData = reinterpret_cast<LPSTR>(s.data[static_cast<size_t>(i)].data());
        h.dwBufferLength = Impl::kFrames * sizeof(short);
        waveInPrepareHeader(s.device, &h, sizeof h);
        waveInAddBuffer(s.device, &h, sizeof h);
    }
    if (waveInStart(s.device) != MMSYSERR_NOERROR) return *error = "the microphone did not start", false;
    s.worker = std::thread([&s] { s.Run(); });
    return true;
}

void MicCapture::Begin() {
    Impl& s = *impl_;
    std::lock_guard<std::mutex> g(s.lock);
    s.clip.assign(s.recent.begin(), s.recent.end());
    s.recent.clear();
    s.taking = true;
}

std::vector<float> MicCapture::End() {
    Impl& s = *impl_;
    Sleep(static_cast<DWORD>(kTailSeconds * 1000));
    std::vector<short> clip;
    {
        std::lock_guard<std::mutex> g(s.lock);
        s.taking = false;
        clip.swap(s.clip);
    }
    std::vector<float> out(clip.size());
    for (size_t i = 0; i < clip.size(); ++i) out[i] = clip[i] / 32768.0f;
    return out;
}
