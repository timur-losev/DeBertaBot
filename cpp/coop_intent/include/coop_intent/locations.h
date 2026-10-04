// Where the order points: the map's named places found in a transcript -- the C++ twin of
// scripts/coop/locations.py (the rules and their reasons are documented there; this file follows it
// step by step and is checked against it line by line: coop_cli --location-tests).
//
// The classifier picks the intent; this gives the planner the places in the line, in order:
//   "i'll take the north door, you take the south window"
//       -> door/north (role mine), window/south <- primary: the place the bot acts on
// Everything is defined on the UTF-8 bytes: a token is a maximal run of ASCII letters and digits
// (A-Z lowercased), every other byte separates. No regex, no Unicode tables.
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
    };
    std::vector<Object> objects;
    std::vector<Qualifier> qualifiers;
    std::vector<Named> named;
    std::vector<Zone> zones;
    std::vector<std::string> ignore;
    std::unordered_map<std::string, std::vector<std::string>> words;   // the rules' word lists
};

enum class PlaceRole { None, Not, From, Mine, Them, Status };          // whose place: the bot is not sent to a place with a role
enum class PlaceFlag { None, UnknownModifier, Unsure, Other };
const char* PlaceRoleName(PlaceRole r);   // "not", "from", "mine", "them", "status" or ""
const char* PlaceFlagName(PlaceFlag f);   // "unknown_modifier", "unsure", "other" or ""

struct PlaceTarget {
    int object = -1, qualifier = -1, zone = -1;   // indices into the vocabulary, -1: none
    PlaceRole role = PlaceRole::None;
    PlaceFlag flag = PlaceFlag::None;   // UnknownModifier: do not fall back to the nearest one; Unsure: confirm
    bool inferred = false;              // the object was not said ("take blue")
    int first = 0, last = 0;            // token positions in the line
};

struct PlaceRecord {
    std::vector<PlaceTarget> targets;   // in line order
    int primary = -1;                   // the target the bot acts on, -1: the line names no place
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
    enum class Kind { Object, Qualifier, Named, Zone, Ignore };
    struct Phrase {
        Kind kind;
        int a = -1, b = -1;   // object / qualifier / zone index; Named: object and qualifier
    };
    bool In(const char* list, const std::string& word) const;

    bool ready_ = false;
    std::vector<std::string> objects_, qualifiers_, zones_;
    std::vector<std::vector<bool>> allowed_;   // [object][qualifier]
    std::vector<int> lone_;                    // qualifier -> object or -1
    std::unordered_map<std::string, Phrase> phrases_;   // tokens joined by one space
    size_t max_len_ = 1;
    std::unordered_map<std::string, std::unordered_set<std::string>> lists_;
};

}  // namespace coop
