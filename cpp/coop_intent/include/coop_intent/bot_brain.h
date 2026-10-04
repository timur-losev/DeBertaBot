// The game side of scripts/coop/coop_bot.py (Bot.respond), without the model: it takes the
// classifier's probabilities for a line and decides what the bot does, keeping the one order that
// waits for the player's signal.
//
//   1. a leading negation ("don't ...", "uh, never ...") of an order -> stand down, drop the queued order
//   2. confidence under the threshold (the top intent's probability, or
//      its family's mass under the family gate)                    -> say again
//   3. NONE (a callout, chatter)                                    -> acknowledge, do nothing
//   4. GO_NOW                                                       -> execute the queued order, if any
//   5. WAIT                                                         -> drop the queued order
//   6. "on my go / when I say / on three"                           -> queue the order
//   7. anything else                                                -> act
// "other / another / opposite" is reported as a slot for the planner, and so are the map places the
// line names (locations.h); a queued order keeps its places and executes with them.
#pragma once

#include <atomic>
#include <regex>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

#include "coop_intent/locations.h"

namespace coop {

struct IntentConfig {
    std::vector<std::string> labels;                        // model output order
    std::unordered_map<std::string, std::string> families;  // label -> family
    std::unordered_map<std::string, std::string> phrases;   // label -> what the bot calls it
    double threshold = 0.78;
    // "top": act on the top intent if its probability reaches the threshold; "family": take the
    // family with the most probability mass and its top intent, if that mass reaches the threshold
    std::string gate = "top";
    std::vector<std::string> safe_intents;                  // a leading negation does not cancel these
    // Python re patterns (ASCII only), matched case-insensitively with Python's Unicode \w and \b
    std::string on_signal, other, negation;
    // the map's named places (locations.json); without it the bot reports no places
    bool has_locations = false;
    LocationVocab locations;
};

enum class Action { Negated, SayAgain, Ignore, Execute, Go, Wait, Queued, Act };
const char* ActionName(Action a);   // the names coop_bot.py logs: "negated", "say_again", ...

struct Decision {
    int intent = -1;           // the picked label (index into labels)
    double prob = 0;           // its confidence: its probability, or its family's mass (gate "family")
    Action action = Action::Ignore;
    int executed = -1;         // Execute: the queued order that fires now
    bool on_signal = false;    // slot: the order waits for the player's signal
    bool other = false;        // slot: the planner takes the other object
    bool negated = false;      // the line starts with a negation
    PlaceRecord places;        // the map places this line names (every action: under Ignore they are contacts)
    PlaceRecord executed_places;   // Execute: the places of the queued order that fires now
};

// the three regexes with Python re semantics, in std::regex:
//  - Unicode: each code point is matched as a one-byte ASCII stand-in with the same \w class and
//    the same IGNORECASE match, so \w, \W and \b see what re sees (patterns must be ASCII)
//  - anchors: re without MULTILINE matches ^ only at the start of the text, MSVC's std::regex also
//    after every newline (it has no multiline flag), so a leading ^ becomes match_continuous; any
//    other ^ or $ is refused at Init
class SlotPatterns {
public:
    bool Init(const IntentConfig& config, std::string* error);
    void Match(std::string_view utf8, Decision* d) const;
    static std::string Shadow(std::string_view utf8);

private:
    struct Pattern {
        std::regex re;
        bool anchored = false;
        mutable std::atomic<unsigned> errors{0};   // searches std::regex gave up on (treated as no match)
        bool Compile(std::string pattern, std::string* error);
        bool Search(const std::string& s) const;
    };
    Pattern on_signal_, other_, negation_;

public:
    // lines on which a slot pattern exceeded std::regex's recursion limit (MSVC: a group repeated
    // ~1000 times, e.g. ~118 leading filler words before a negation); such a slot counts as absent
    unsigned SearchErrors() const { return on_signal_.errors + other_.errors + negation_.errors; }
};

class BotBrain {
public:
    bool Init(IntentConfig config, std::string* error);
    Decision Decide(std::string_view text, const std::vector<float>& probs);
    // the gate alone: the picked intent and its confidence; false if probs does not fit the labels
    bool Pick(const std::vector<float>& probs, int* intent, double* confidence) const;
    unsigned SlotSearchErrors() const { return slots_.SearchErrors(); }

    int Pending() const { return pending_; }   // the queued order, -1 if none
    const PlaceRecord& PendingPlaces() const { return pending_places_; }   // and the places it named
    const LocationMatcher& Places() const { return places_; }
    void Reset() {
        pending_ = -1;
        pending_places_ = PlaceRecord();
    }
    double threshold = 0.78;
    const IntentConfig& Config() const { return cfg_; }
    int LabelIndex(const std::string& label) const;

private:
    IntentConfig cfg_;
    SlotPatterns slots_;
    std::vector<bool> safe_;
    std::vector<int> family_;   // label -> family index, numbered in order of first appearance
    int families_ = 0;
    bool family_gate_ = false;
    int none_ = -1, go_now_ = -1, wait_ = -1;
    int pending_ = -1;
    PlaceRecord pending_places_;
    LocationMatcher places_;
};

}  // namespace coop
