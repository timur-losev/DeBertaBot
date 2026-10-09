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
    std::vector<std::string> ignore;
    std::unordered_map<std::string, std::vector<std::string>> words;   // the rules' word lists
};

// whose place it is. A place with a role is not a destination: the player's own (Mine), the enemy's
// (Them), the place to leave (From), negated or corrected (Not), only reported on (Status)
enum class PlaceRole { None, Not, From, Mine, Them, Status };
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
// pin", "check that room")
enum class PlacePointer { None, Pin, This };
const char* PlaceRoleName(PlaceRole r);   // "not", "from", "mine", "them", "status" or ""
const char* PlaceFlagName(PlaceFlag f);   // "unknown_modifier", "unsure", "other" or ""
const char* PlaceDirectionName(PlaceDirection d);   // "up", "down", "left", "right", "forward", "back" or ""
const char* PlacePointerName(PlacePointer p);   // "pin", "this" or ""

struct PlaceTarget {
    int object = -1, qualifier = -1, zone = -1;   // indices into the vocabulary, -1: none
    PlaceDirection direction = PlaceDirection::None;
    PlacePointer pointer = PlacePointer::None;
    PlaceRole role = PlaceRole::None;
    PlaceFlag flag = PlaceFlag::None;
    bool inferred = false;              // the object was not said ("take blue", "you take the south one")
};

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
    const std::string& QualifierId(int i) const { return qualifiers_[static_cast<size_t>(i)]; }
    const std::string& ZoneId(int i) const { return zones_[static_cast<size_t>(i)]; }

private:
    enum class Kind { Object, Qualifier, Named, Zone, Ignore, ZoneEnd };
    struct Phrase {
        Kind kind;
        int a = -1, b = -1;   // object / qualifier / zone index; Named: object and qualifier
    };
    bool In(const char* list, const std::string& word) const;

    bool ready_ = false;
    bool directions_ = false;                  // rule set v4: the vocabulary has "directions"
    bool pointers_ = false;                    // rule set v5: ... and the pin_* / point_* word lists
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
