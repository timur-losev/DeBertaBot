#include "coop_intent/bot_brain.h"

#include <algorithm>

#include "coop_intent/unicode.h"

namespace coop {

const char* ActionName(Action a) {
    switch (a) {
        case Action::Negated: return "negated";
        case Action::SayAgain: return "say_again";
        case Action::Ignore: return "ignore";
        case Action::Execute: return "execute";
        case Action::Go: return "go";
        case Action::Wait: return "wait";
        case Action::Queued: return "queued";
        case Action::Act: return "act";
    }
    return "?";
}

std::string SlotPatterns::Shadow(std::string_view utf8) {
    // ASCII stays; a non-ASCII letter IGNORECASE folds to ASCII (U+017F long s, U+212A Kelvin, dotted
    // and dotless i) becomes that letter; any other word character '_'; anything else \x01. None of
    // these stand-ins appears literally in the patterns, so only \w, \W and \b can see them.
    std::string s;
    for (char32_t c : DecodeUtf8(utf8)) {
        if (c < 0x80)
            s.push_back(static_cast<char>(c));
        else if (char f = PyAsciiFold(c))
            s.push_back(f);
        else
            s.push_back(IsPyWordChar(c) ? '_' : '\x01');
    }
    return s;
}

bool SlotPatterns::Pattern::Compile(std::string p, std::string* error) {
    auto fail = [&](const char* why) {
        if (error) *error = std::string(why) + ": " + p;
        return false;
    };
    if (std::any_of(p.begin(), p.end(), [](char c) { return static_cast<unsigned char>(c) >= 0x80; }))
        return fail("slot patterns must be ASCII");
    anchored = !p.empty() && p[0] == '^';
    int depth = 0;
    bool in_class = false;
    for (size_t i = anchored ? 1 : 0; i < p.size(); ++i) {
        const char c = p[i];
        if (c == '\\') {
            ++i;
        } else if (in_class) {
            in_class = c != ']';
        } else if (c == '[') {
            in_class = true;
            if (i + 1 < p.size() && p[i + 1] == '^') ++i;   // a negated class, not an anchor
        } else if (c == '(') {
            ++depth;
        } else if (c == ')') {
            --depth;
        } else if (c == '^' || c == '$') {
            return fail("only a leading ^ is supported");
        } else if (c == '|' && depth == 0 && anchored) {
            return fail("a leading ^ with a top-level | is not supported");
        }
    }
    if (anchored) p.erase(0, 1);
    try {
        re = std::regex(p, std::regex::ECMAScript | std::regex::icase | std::regex::optimize);
    } catch (const std::regex_error& e) {
        return fail(e.what());
    }
    return true;
}

bool SlotPatterns::Pattern::Search(const std::string& s) const {
    try {
        return std::regex_search(s, re, anchored ? std::regex_constants::match_continuous
                                                 : std::regex_constants::match_default);
    } catch (const std::regex_error&) {
        // MSVC's matcher recurses once per repetition of a group and gives up (error_stack) past
        // about 1000 levels: the negation pattern hits that after ~118 leading filler words
        // ("uh uh uh ... don't"). Python re has no such limit; here the slot is simply not found.
        ++errors;
        return false;
    }
}

bool SlotPatterns::Init(const IntentConfig& cfg, std::string* error) {
    return on_signal_.Compile(cfg.on_signal, error) && other_.Compile(cfg.other, error) &&
           negation_.Compile(cfg.negation, error);
}

void SlotPatterns::Match(std::string_view utf8, Decision* d) const {
    const std::string s = Shadow(utf8);
    d->on_signal = on_signal_.Search(s);
    d->other = other_.Search(s);
    d->negated = negation_.Search(s);
}

int BotBrain::LabelIndex(const std::string& label) const {
    auto it = std::find(cfg_.labels.begin(), cfg_.labels.end(), label);
    return it == cfg_.labels.end() ? -1 : static_cast<int>(it - cfg_.labels.begin());
}

bool BotBrain::Init(IntentConfig config, std::string* error) {
    cfg_ = std::move(config);
    threshold = cfg_.threshold;
    Reset();
    none_ = LabelIndex("NONE");
    go_now_ = LabelIndex("GO_NOW");
    wait_ = LabelIndex("WAIT");
    if (none_ < 0 || go_now_ < 0 || wait_ < 0) {
        if (error) *error = "labels must include NONE, GO_NOW and WAIT";
        return false;
    }
    if (cfg_.gate != "top" && cfg_.gate != "family") {
        if (error) *error = "gate must be \"top\" or \"family\": " + cfg_.gate;
        return false;
    }
    family_gate_ = cfg_.gate == "family";
    std::vector<std::string> names;
    family_.clear();
    for (const std::string& label : cfg_.labels) {
        auto f = cfg_.families.find(label);
        if (f == cfg_.families.end()) {
            if (error) *error = "no family for " + label;
            return false;
        }
        auto it = std::find(names.begin(), names.end(), f->second);
        family_.push_back(static_cast<int>(it - names.begin()));
        if (it == names.end()) names.push_back(f->second);
    }
    families_ = static_cast<int>(names.size());
    safe_.assign(cfg_.labels.size(), false);
    for (const std::string& s : cfg_.safe_intents) {
        const int i = LabelIndex(s);
        if (i < 0) {
            if (error) *error = "unknown safe intent " + s;
            return false;
        }
        safe_[static_cast<size_t>(i)] = true;
    }
    if (cfg_.has_locations && !places_.Init(cfg_.locations, error)) return false;
    return slots_.Init(cfg_, error);
}

bool BotBrain::Pick(const std::vector<float>& probs, int* intent, double* confidence) const {
    if (probs.size() != cfg_.labels.size()) return false;
    int best = -1;
    if (family_gate_) {
        // as coop_v2.pick / coop_bot.Bot.pick: masses summed in label order, the first family and
        // then the first label win a tie
        std::vector<double> mass(static_cast<size_t>(families_), 0.0);
        for (size_t i = 0; i < probs.size(); ++i) mass[static_cast<size_t>(family_[i])] += probs[i];
        const int f = static_cast<int>(std::max_element(mass.begin(), mass.end()) - mass.begin());
        for (size_t i = 0; i < probs.size(); ++i)
            if (family_[i] == f && (best < 0 || probs[i] > probs[static_cast<size_t>(best)])) best = static_cast<int>(i);
        *confidence = mass[static_cast<size_t>(f)];
    } else {
        best = static_cast<int>(std::max_element(probs.begin(), probs.end()) - probs.begin());
        *confidence = probs[static_cast<size_t>(best)];
    }
    *intent = best;
    return true;
}

Decision BotBrain::Decide(std::string_view text, const std::vector<float>& probs) {
    Decision d;
    if (!Pick(probs, &d.intent, &d.prob)) {   // a model that does not fit the config: never act
        d.action = Action::SayAgain;
        return d;
    }
    slots_.Match(text, &d);
    if (places_.Ready()) d.places = places_.Find(text);
    auto drop_pending = [&] {
        pending_ = -1;
        pending_places_ = PlaceRecord();
        pending_other_ = false;
    };

    if (d.negated && !safe_[static_cast<size_t>(d.intent)]) {
        drop_pending();
        d.action = Action::Negated;
    } else if (d.prob < threshold) {
        d.action = Action::SayAgain;
    } else if (d.intent == none_) {
        d.action = Action::Ignore;
    } else if (d.intent == go_now_) {
        d.action = pending_ >= 0 ? Action::Execute : Action::Go;
        d.executed = pending_;
        if (pending_ >= 0) {   // the queued order's places and "other" slot, not the GO line's
            d.executed_places = pending_places_;
            d.executed_other = pending_other_;
        }
        drop_pending();
    } else if (d.intent == wait_) {
        drop_pending();
        d.action = Action::Wait;
    } else if (d.on_signal) {
        pending_ = d.intent;
        pending_places_ = d.places;
        pending_other_ = d.other;
        d.action = Action::Queued;
    } else {
        d.action = Action::Act;
    }
    return d;
}

}  // namespace coop
