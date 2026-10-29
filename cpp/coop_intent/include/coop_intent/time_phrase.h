// A time said with an order (round v68): "wait 5 seconds", "run forward for 10 seconds", "in ten seconds, get to the
// door", "a few seconds" (3..7), "10-15 seconds", "5 more seconds", "count to ten". The twin of
// scripts/coop/time_phrase.py, checked against its cases (time_phrase_tests.jsonl, `coop_cli --time-tests FILE`).
//
// The line is English (the player's own, or the decoder's line for a Russian or Spanish one). The time never changes what
// the order is: the classifier, the router and the place matcher read `rest`, the line without it. The owner's rules
// (scripts/coop/stt/chains2/ml_v68/TODO_v68.md, 1a G): "wait a minute" / "a sec" said without "for" is the idiom, no
// time; 60 s at most ("capped"); "in / after N", "N from now", "count to N" start the order after the time.
#pragma once

#include <string>
#include <string_view>

namespace coop {

struct TimePhrase {
    bool found = false;
    bool after = false;        // "in 10 seconds": the order starts after it; else it lasts that long
    bool range = false;        // a random time from min to max ("a few seconds", "10-15 seconds"); else `seconds`
    double seconds = 0, min = 0, max = 0;
    bool more = false;         // "5 more seconds", "another 5 seconds": added to a timed order still running
    bool capped = false;       // said longer than 60 s, cut to it
    std::string said;          // the words of the time, as in the line
};

constexpr double kMaxOrderSeconds = 60.0;

// The time the line says, and in `rest` the line without it (the line itself when it says none).
TimePhrase FindTimePhrase(std::string_view line, std::string* rest);

}  // namespace coop
