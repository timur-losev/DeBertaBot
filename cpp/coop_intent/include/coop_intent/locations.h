// Where the order points: the map's named places found in a transcript -- the C++ twin of
// scripts/coop/locations.py (the rules and their reasons are documented there; this file follows it
// step by step and is checked against it line by line: coop_cli --location-tests).
//
// The classifier picks the intent; this gives the planner the places in the line, in order:
//   "i'll take the north door, you take the south window"
//       -> door/north (role mine), window/south <- primary: the place the bot acts on
//   "go up the blue stairs then go left"               (rule set v4: a vocabulary with "directions")
//       -> stairs/blue direction up <- primary, then a target that is only a direction: left
//   "hold that window", "stay at my pin"               (rule set v5: a vocabulary with the pin_* / point_* lists)
//       -> window pointer this; a target that is only a pointer: pin <- primary
// Everything is defined on the UTF-8 bytes: a token is a maximal run of ASCII letters and digits
// (A-Z lowercased), every other byte separates. No regex, no Unicode tables.
//
// The rule set follows the vocabulary: one without "directions" (a bot exported before rule set v4)
// is matched by rule set v3, as it was when its test files were written -- no target has a direction.
// One with "directions" and without the pin_* / point_* word lists (exported before rule set v5) is
// matched by rule set v4 -- no target has a pointer.
#pragma once

#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace coop {

// locations.json as data ("locations" in intent_config.json); ids are the names the planner maps to tags
struct LocationVocab {
    struct Object {
        std::string id;
        std::vector<std::string> words, qualifiers;
        bool vertical = false;   // up / down next to it is its direction ("up the blue stairs")
    };
    struct Qualifier {
        std::string id;
        std::vector<std::string> words;
        std::string lone;   // the object a lone mention means ("blue" -> stairs); empty: none (a direction)
    };
    struct Named {
        std::string phrase, object, qualifier;
    };
    struct Zone {
        std::string id;
        std::vector<std::string> words;
        std::vector<std::string> words_end;   // phrases that count only where they end their phrase ("on second")
    };
    struct Direction {
        std::string id;                   // one of the six PlaceDirection names
        std::vector<std::string> words;   // "left"; "ahead", "front", "straight"
        std::vector<std::string> clock;   // the hours that mean it: "nine" (o'clock) is left
    };
    std::vector<Object> objects;
    std::vector<Qualifier> qualifiers;
    std::vector<Named> named;
    std::vector<Zone> zones;
    // rule set v4: the "directions" section. Without it (has_directions false) the vocabulary is a
    // rule set v3 one: it has none of the dir_* word lists and no target gets a direction
    bool has_directions = false;
    std::vector<Direction> directions;
    // rule set v5: "words" holds the pin_* and point_* lists. Without them (has_pointers false) the
    // vocabulary is a rule set v4 or v3 one: it has none of those lists and no target gets a pointer
    bool has_pointers = false;
    // a word list of rule set v5, by its name: "pin_noun", "point_det", ... A loader sets has_pointers
    // when "words" has any such list; Init then wants every one of them, and "directions"
    static bool PointerList(std::string_view name) { return name.rfind("pin_", 0) == 0 || name.rfind("point_", 0) == 0; }
    // rule set v8: "words" holds the it_* lists (the "it" pointer: "jump over it"). Without them (has_it false) no target
    // gets that pointer. A loader sets has_it when "words" has any such list; Init then wants every one of them
    bool has_it = false;
    static bool ItList(std::string_view name) { return name.rfind("it_", 0) == 0; }
    // rule set v9 (round v67): "words" holds the means_* lists (the thing an order is done with: "climb onto the table using
    // the crate"). A loader sets has_means when "words" has any such list; Init then wants every one of them
    bool has_means = false;
    static bool MeansList(std::string_view name) { return name.rfind("means_", 0) == 0; }
    std::vector<std::string> ignore;
    std::unordered_map<std::string, std::vector<std::string>> words;   // the rules' word lists
};

// whose place it is. A place with a role is not a destination: the player's own (Mine), the enemy's
// (Them), the place to leave (From), negated or corrected (Not), only reported on (Status); rule set v9: the thing the
// order is done with (Means: "using the crate", "standing on the spool")
enum class PlaceRole { None, Not, From, Mine, Them, Status, Means };
// UnknownModifier: the player singled out one object in a way the map names cannot express ("the back
// door"): do not fall back to the nearest one. Other: the other one of its kind. Unsure: a lone name
// before a word the vocabulary does not know; most are real places
enum class PlaceFlag { None, UnknownModifier, Unsure, Other };
// the direction the line gives the action (rule set v4). The six are fixed: the rules name them, the
// vocabulary only lists their words. It is the object's when said in its noun phrase ("the left
// window", "up the blue stairs", "the door behind you"); any other direction is a target of its own,
// with no object, qualifier or zone ("go left")
enum class PlaceDirection { None, Up, Down, Left, Right, Forward, Back };
// how the line points at the place (rule set v5). Pin: the player's 3D marker ("my pin", "the ping",
// "on my mark", "where i marked"). This: this / that / here / there ("that window", "over there",
// "where i'm looking"). It is a place's or a direction's when said in its noun phrase, right after it
// or on the way to it ("the window by my ping", "get up there", "that room by the north door"); any
// other pointer is a target of its own, with no object, qualifier, zone or direction ("stay at my
// pin", "check that room"). It (rule set v8): "it" after a preposition or a verb of the it_* lists ("jump
// over it", "open it"), always a target of its own; the planner grounds it from the conversation first
enum class PlacePointer { None, Pin, This, It };
const char* PlaceRoleName(PlaceRole r);   // "not", "from", "mine", "them", "status" or ""
const char* PlaceFlagName(PlaceFlag f);   // "unknown_modifier", "unsure", "other" or ""
const char* PlaceDirectionName(PlaceDirection d);   // "up", "down", "left", "right", "forward", "back" or ""
const char* PlacePointerName(PlacePointer p);   // "pin", "this", "it" or ""

struct PlaceTarget {
    int object = -1, qualifier = -1, zone = -1;   // indices into the vocabulary, -1: none
    PlaceDirection direction = PlaceDirection::None;
    PlacePointer pointer = PlacePointer::None;
    PlaceRole role = PlaceRole::None;
    PlaceFlag flag = PlaceFlag::None;
    bool inferred = false;              // the object was not said ("take blue", "you take the south one")
};

// locations.tokenize: the line's tokens, each with the punctuation before it (0 none, 1 comma, 2 . ; : ! ?)
struct PlaceToken {
    std::string word;
    int brk = 0;
};
std::vector<PlaceToken> PlaceTokens(std::string_view utf8);

struct PlaceRecord {
    std::vector<PlaceTarget> targets;   // in line order
    // the first target without a role, a place or a direction; -1: the line names neither. If every
    // target has a role it is the first target, and the line gives the bot no destination: check
    // Primary()->role.
    // Rule set v5: a target that is only a pin counts like a place; one that is only a "this" (here,
    // there, "that room") is the primary only when the line has no place, direction or pin at all
    int primary = -1;
    const PlaceTarget* Primary() const { return primary >= 0 ? &targets[static_cast<size_t>(primary)] : nullptr; }
};

class LocationMatcher {
public:
    bool Init(const LocationVocab& vocab, std::string* error);   // refuses a malformed vocabulary
    bool Ready() const { return ready_; }
    PlaceRecord Find(std::string_view utf8) const;

    const std::string& ObjectId(int i) const { return objects_[static_cast<size_t>(i)]; }
    const std::vector<std::string>& ObjectIds() const { return objects_; }   // the vocabulary's objects (the game's "ready" lists them)
    const std::string& QualifierId(int i) const { return qualifiers_[static_cast<size_t>(i)]; }
    const std::vector<std::string>& QualifierIds() const { return qualifiers_; }   // ... and its qualifiers (bot v64: big, small, cardboard)
    const std::string& ZoneId(int i) const { return zones_[static_cast<size_t>(i)]; }
    // the index of an id, -1 if the vocabulary has none (world.h: the game's entities carry these ids)
    int ObjectIndex(const std::string& id) const { return Find(objects_, id); }
    int QualifierIndex(const std::string& id) const { return Find(qualifiers_, id); }
    int ZoneIndex(const std::string& id) const { return Find(zones_, id); }
    bool Vertical(int object) const { return object >= 0 && vertical_[static_cast<size_t>(object)]; }
    // the object takes the qualifier (vocabulary "qualifiers" of the object); -1 for either: false
    bool Allows(int object, int qualifier) const {
        return object >= 0 && qualifier >= 0 && allowed_[static_cast<size_t>(object)][static_cast<size_t>(qualifier)];
    }
    // the phrase index (items.cpp, world.cpp): the kind of a phrase given as tokens joined by one space -- "object",
    // "qualifier", "named", "zone", "zone_end", "ignore" -- or nullptr; *index: its object / qualifier / zone (named:
    // its object)
    const char* PhraseKind(const std::string& joined, int* index = nullptr) const;
    size_t MaxPhraseLen() const { return max_len_; }
    bool InList(const char* list, const std::string& word) const { return In(list, word); }
    bool HasMeans() const { return means_; }   // rule set v9: an order carries the thing it is done with

private:
    enum class Kind { Object, Qualifier, Named, Zone, Ignore, ZoneEnd };
    struct Phrase {
        Kind kind;
        int a = -1, b = -1;   // object / qualifier / zone index; Named: object and qualifier
    };
    bool In(const char* list, const std::string& word) const;
    static int Find(const std::vector<std::string>& v, const std::string& id) {
        for (size_t i = 0; i < v.size(); ++i)
            if (v[i] == id) return static_cast<int>(i);
        return -1;
    }

    bool ready_ = false;
    bool directions_ = false;                  // rule set v4: the vocabulary has "directions"
    bool pointers_ = false;                    // rule set v5: ... and the pin_* / point_* word lists
    bool its_ = false;                         // rule set v8: ... and the it_* word lists
    bool means_ = false;                       // rule set v9: ... and the means_* word lists
    std::vector<std::string> objects_, qualifiers_, zones_;
    std::vector<std::vector<bool>> allowed_;   // [object][qualifier]
    std::vector<int> lone_;                    // qualifier -> object or -1
    std::vector<bool> vertical_;               // [object]
    std::unordered_map<std::string, PlaceDirection> dirs_, clock_;   // direction word / hour -> direction
    std::unordered_map<std::string, Phrase> phrases_;   // tokens joined by one space
    size_t max_len_ = 1;
    std::unordered_map<std::string, std::unordered_set<std::string>> lists_;
};

}  // namespace coop
