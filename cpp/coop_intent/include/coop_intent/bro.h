// The bot's habit of calling the player «брат» / "bro" / "hermano" (2026-10-24, the owner). It is a habit of speech, not an
// order: the classifier never sees it. The words of the player's line, as said (in his language), switch it:
//
//   - a word for "brother" anywhere in the line ("брат", "эй братан, иди сюда", "bro", "hermano, ven") turns it on;
//   - the same word with a "stop calling me that" around it ("не называй меня брат", "stop calling me bro", "no me llames
//     hermano") turns it off. The bot always agrees ("Okay, I won't anymore.");
//   - the brat persona (the bot from Uzbekistan) cannot help it: switched off, it comes back 30 seconds later.
//
// While it is on, the bot's lines are written from the persona's reply table (replies_<lang>_brat.json: the same
// sentences with «брат» in most of them); voice and language stay as they are.
#pragma once

#include <string>

namespace coop {

class BroHabit {
public:
    enum class Heard { None, On, Off };

    // relapse_s > 0: switched off, it comes back that many seconds later (the brat persona); on: how it starts
    void Configure(bool on, double relapse_s) {
        on_ = on;
        relapse_s_ = relapse_s;
        back_at_ = -1;
    }

    // what the line says about the habit (the words only; nothing changes)
    static Heard Read(const std::string& line);

    // the line, at `now` seconds: the habit as it says. Returns what it heard
    Heard Hear(const std::string& line, double now);

    // on at `now` (a relapse due by then happens here; relapsed() tells it did, once)
    bool Active(double now);
    bool TakeRelapse() {
        const bool r = relapsed_;
        relapsed_ = false;
        return r;
    }
    double RelapseSeconds() const { return relapse_s_; }

private:
    bool on_ = false;
    double relapse_s_ = 0;
    double back_at_ = -1;
    bool relapsed_ = false;
};

}  // namespace coop
