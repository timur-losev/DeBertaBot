// MicCapture on macOS: an input AudioQueue (AudioToolbox), PCM 16 kHz mono 16-bit from the default device --
// the queue converts whatever the device runs at. The queue's own thread hands over the 20 ms buffers as they
// fill; between clips only the last kPreRollSeconds are remembered.
//
// macOS lets a program listen only after the user agreed, once per application; for a command-line tool that
// application is the terminal it runs in. A queue that was refused still runs and delivers silence, so
// Start() asks first and names the refusal.
#include "mic_capture.h"

#import <AVFoundation/AVFoundation.h>
#include <AudioToolbox/AudioToolbox.h>
#include <CoreAudio/CoreAudio.h>

#include <atomic>
#include <chrono>
#include <cstdio>
#include <deque>
#include <mutex>
#include <thread>

struct MicCapture::Impl {
    static constexpr int kBuffers = 16, kFrames = MicCapture::kSampleRate / 50;   // 20 ms each
    AudioQueueRef queue = nullptr;
    std::atomic<bool> stop{false};
    std::mutex lock;
    std::deque<short> recent;     // the pre-roll, when no clip is being taken
    std::vector<short> clip;
    bool taking = false;

    // called by the queue when a buffer is done
    static void Filled(void* self, AudioQueueRef queue, AudioQueueBufferRef buffer, const AudioTimeStamp*, UInt32,
                       const AudioStreamPacketDescription*) {
        Impl& s = *static_cast<Impl*>(self);
        const short* p = static_cast<const short*>(buffer->mAudioData);
        const size_t n = buffer->mAudioDataByteSize / sizeof(short);
        {
            std::lock_guard<std::mutex> g(s.lock);
            if (s.taking) {
                s.clip.insert(s.clip.end(), p, p + n);
            } else {
                s.recent.insert(s.recent.end(), p, p + n);
                const size_t keep = static_cast<size_t>(MicCapture::kPreRollSeconds * MicCapture::kSampleRate);
                while (s.recent.size() > keep) s.recent.pop_front();
            }
        }
        if (!s.stop.load()) AudioQueueEnqueueBuffer(queue, buffer, 0, nullptr);
    }
};

namespace {

bool HasInputDevice() {
    const AudioObjectPropertyAddress address{kAudioHardwarePropertyDefaultInputDevice, kAudioObjectPropertyScopeGlobal,
                                             kAudioObjectPropertyElementMain};
    AudioDeviceID device = kAudioObjectUnknown;
    UInt32 size = sizeof device;
    return AudioObjectGetPropertyData(kAudioObjectSystemObject, &address, 0, nullptr, &size, &device) == noErr &&
           device != kAudioObjectUnknown;
}

// The user's answer to "may this terminal use the microphone". The first run waits for it: the dialog is macOS's
bool Allowed() {
    if ([AVCaptureDevice authorizationStatusForMediaType:AVMediaTypeAudio] == AVAuthorizationStatusNotDetermined) {
        std::fprintf(stderr, "macOS is asking whether this terminal may use the microphone: answer its dialog\n");
        dispatch_semaphore_t answered = dispatch_semaphore_create(0);
        [AVCaptureDevice requestAccessForMediaType:AVMediaTypeAudio
                                 completionHandler:^(BOOL) {
                                     dispatch_semaphore_signal(answered);
                                 }];
        dispatch_semaphore_wait(answered, DISPATCH_TIME_FOREVER);
    }
    return [AVCaptureDevice authorizationStatusForMediaType:AVMediaTypeAudio] == AVAuthorizationStatusAuthorized;
}

}  // namespace

MicCapture::MicCapture() : impl_(new Impl) {}

MicCapture::~MicCapture() {
    Impl& s = *impl_;
    s.stop.store(true);
    if (s.queue) {
        AudioQueueStop(s.queue, true);
        AudioQueueDispose(s.queue, true);   // and its buffers
    }
}

bool MicCapture::Start(std::string* error) {
    Impl& s = *impl_;
    if (!HasInputDevice()) return *error = "no audio input device", false;
    if (!Allowed())
        return *error = "macOS does not let this terminal use the microphone: allow it in System Settings > "
                        "Privacy & Security > Microphone",
               false;
    AudioStreamBasicDescription f{};
    f.mSampleRate = kSampleRate;
    f.mFormatID = kAudioFormatLinearPCM;
    f.mFormatFlags = kLinearPCMFormatFlagIsSignedInteger | kLinearPCMFormatFlagIsPacked;
    f.mChannelsPerFrame = 1;
    f.mBitsPerChannel = 16;
    f.mBytesPerFrame = 2;
    f.mFramesPerPacket = 1;
    f.mBytesPerPacket = 2;
    // no run loop: the queue calls Filled on a thread of its own
    OSStatus r = AudioQueueNewInput(&f, &Impl::Filled, &s, nullptr, nullptr, 0, &s.queue);
    if (r != noErr) {
        s.queue = nullptr;
        return *error = "cannot open the default microphone: OSStatus " + std::to_string(r), false;
    }
    for (int i = 0; i < Impl::kBuffers && r == noErr; ++i) {
        AudioQueueBufferRef buffer = nullptr;
        r = AudioQueueAllocateBuffer(s.queue, Impl::kFrames * sizeof(short), &buffer);
        if (r == noErr) r = AudioQueueEnqueueBuffer(s.queue, buffer, 0, nullptr);
    }
    if (r == noErr) r = AudioQueueStart(s.queue, nullptr);
    if (r != noErr) return *error = "the microphone did not start: OSStatus " + std::to_string(r), false;
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
    std::this_thread::sleep_for(std::chrono::duration<double>(kTailSeconds));
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
