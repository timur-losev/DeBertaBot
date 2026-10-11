// The bot's voice for coop_cli --serve --tts: the operating system's own speech synthesizer, so that the
// player hears "Which door? The one ahead, 8 m?" without looking at the screen. No model, no CPU to speak
// of. Windows: SAPI, the first installed English voice. Elsewhere: Start() fails and the bot stays silent.
#pragma once

#include <memory>
#include <string>

class Tts {
public:
    Tts();
    ~Tts();
    bool Start(std::string* error);
    // speaks in the background; a line still being spoken is cut off by the next one
    void Say(const std::string& utf8);
    // silence now (the player pressed the talk key: the microphone must not hear the bot)
    void Stop();
    const std::string& Voice() const;   // the voice's name, for the log

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
