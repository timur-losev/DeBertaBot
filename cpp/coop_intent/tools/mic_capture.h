// The microphone for coop_cli --voice: the default input device at 16 kHz mono, open from Start() on
// (mic_capture_win.cpp on Windows, mic_capture_mac.mm on macOS).
// The device stays open between clips, so that a clip can begin a moment BEFORE the key went down
// (people start talking as they press). Nothing is kept or handed out except between Begin() and End().
#pragma once

#include <memory>
#include <string>
#include <vector>

class MicCapture {
public:
    static constexpr int kSampleRate = 16000;
    static constexpr double kPreRollSeconds = 0.20;   // audio before Begin() that goes into the clip
    static constexpr double kTailSeconds = 0.15;      // End() waits this long for the last syllable

    MicCapture();
    ~MicCapture();
    bool Start(std::string* error);
    void Begin();                    // the key went down
    std::vector<float> End();        // the key went up: the clip, samples in -1..1
    // the open microphone (coop_cli --serve's "open_mic", 2026-11-01): with the tap on, everything heard is kept for Drain,
    // clip or no clip (60 s at most: the oldest goes); off drops it
    void Tap(bool on);
    void Drain(std::vector<float>* out);   // appends what was heard since the last Drain, samples in -1..1

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
