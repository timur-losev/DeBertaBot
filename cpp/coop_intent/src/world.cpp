#include "coop_intent/world.h"

#include <algorithm>
#include <cmath>

namespace coop {

namespace {

// world.py: SECTORS, BACK_FROM, ELEVATION, CLEARLY_NEARER
constexpr double kElevation = 1.5;
constexpr double kStorey = 1.5;   // "upstairs": the places within 1.5 m of the nearest one above, not the floors beyond
constexpr double kBackFrom = 120.0;
constexpr double kClearlyNearer = 1.5;
// world.py FETCHED: things the bot fetches or rides; "go find ammo", "get in the car" mean the nearest one, never a question
bool Fetched(const std::string& object) { return object == "ammo" || object == "weapon" || object == "health" || object == "car"; }
constexpr double kPi = 3.14159265358979323846;

bool InSector(PlaceDirection d, double bearing, double elevation) {
    switch (d) {
        case PlaceDirection::Up: return elevation >= kElevation;
        case PlaceDirection::Down: return elevation <= -kElevation;
        case PlaceDirection::Back: return std::fabs(bearing) >= kBackFrom;
        case PlaceDirection::Left: return -150.0 <= bearing && bearing <= -20.0;
        case PlaceDirection::Right: return 20.0 <= bearing && bearing <= 150.0;
        case PlaceDirection::Forward: return -60.0 <= bearing && bearing <= 60.0;
        case PlaceDirection::None: break;
    }
    return true;
}

const char* SectorWord(double b, double el) {
    if (el >= kElevation) return "above";
    if (el <= -kElevation) return "below";
    if (std::fabs(b) <= 45.0) return "ahead";
    if (std::fabs(b) >= 135.0) return "behind you";
    return b < 0 ? "on the left" : "on the right";
}

void Xy(double bearing, double distance, double* x, double* y) {
    const double r = bearing * kPi / 180.0;   // math.radians
    *x = distance * std::sin(r);
    *y = distance * std::cos(r);
}

double DistBetween(double b1, double d1, double b2, double d2) {
    double ax, ay, bx, by;
    Xy(b1, d1, &ax, &ay);
    Xy(b2, d2, &bx, &by);
    return std::hypot(ax - bx, ay - by);
}

Grounding Out(const char* status, std::string entity = {}, std::vector<std::string> candidates = {}, const char* via = "") {
    Grounding g;
    g.status = status;
    g.entity = std::move(entity);
    g.candidates = std::move(candidates);
    g.via = via;
    return g;
}

// world.py: NEAR_WORDS, NEAR_DET, FAR_WORDS, ANSWER_LEADS, ANSWER_MAX_TOKENS, ZONE_NAMES
const char* const kNearWords[] = {"here"};
const char* const kNearDet[] = {"this", "these"};
const char* const kFarWords[] = {"there", "that", "those", "looking", "pointing", "aiming", "facing"};
const char* const kAnswerLeads[] = {"there", "here", "over", "at", "on", "in", "by", "near", "to", "the", "that", "this", "those", "these", "my",
                                    "right", "left", "behind", "up", "down", "where", "it", "its", "one", "ahead", "forward", "back", "straight",
                                    "around", "next", "beside", "above", "below", "under", "inside", "outside", "toward", "towards", "just"};
constexpr size_t kAnswerMaxTokens = 6;

// world.py, "a short context": CONTEXT_SECONDS, FRAGMENT_UNSURE, FIRE, PIN_DEFAULT, CARRY, POINTED_HERE, PLACE_INTENTS,
// NO_LEADS, LOST_POINTERS
constexpr double kContextSeconds = 8.0;
constexpr double kFragmentUnsure = 0.5;
const char* const kFire[] = {"OPEN_FIRE", "SUPPRESS", "ATTACK"};
const char* const kPinDefault[] = {"OPEN_FIRE", "SUPPRESS", "ATTACK", "MOVE_TO", "CHECK", "ENTRY", "FLANK"};
const char* const kCarry[] = {"OPEN_FIRE", "SUPPRESS", "ATTACK", "MOVE_TO", "CHECK", "ENTRY", "FLANK", "HOLD_ANGLE", "LOOK_AT"};
const char* const kPointedHere[] = {"OPEN_FIRE", "SUPPRESS", "ATTACK", "FRAG", "FLASH", "SMOKE", "LOOK_AT", "CHECK", "HOLD_ANGLE", "SEE_THING"};
const char* const kPlaceIntents[] = {"OPEN_FIRE", "SUPPRESS", "ATTACK", "MOVE_TO", "CHECK", "ENTRY", "FLANK", "HOLD_ANGLE", "LOOK_AT",
                                     "FRAG", "FLASH", "SMOKE", "HOLD_POSITION", "JUMP", "TAKE_COVER", "FALL_BACK", "COME_BACK",
                                     "BREACH", "VAULT_WINDOW", "OPEN"};
// world.NO_PLACE (bot v56): orders whose place is not the line's: going back (the bot's own earlier place, the game keeps
// it), letting the player out (where the player is). Their lines' places are neither grounded nor asked about. Bot v57:
// taking out or reloading a weapon the bot carries ("switch to your pistol" names no weapon lying in the world)
// bot v62: the talk intents; a place in "thanks for the cover at the door" is no order's
const char* const kNoPlace[] = {"GO_BACK", "HELP_INTERACTION", "SWITCH_WEAPON", "RELOAD", "SEE_ME", "SMALL_TALK", "PRAISE", "KILL_YOURSELF"};
// world.ITEM_INTENTS (items_v60.json "intents") and FARM_INTENTS: the farmer's and the builder's orders. They join
// PLACE_INTENTS: "no, by the barn" gives the same order at another place
const char* const kItemIntents[] = {"PLANT_CROP", "WATER", "HARVEST", "FEED", "COLLECT", "DELIVER", "BUILD", "REPAIR", "DEMOLISH"};
const char* const kFarmIntents[] = {"PLANT_CROP", "WATER", "HARVEST", "FEED", "COLLECT", "DELIVER", "BUILD", "REPAIR", "DEMOLISH", "TILL"};
// world.REFUSE: what the bot says when the game's catalogue lacks the item ("{item}" is the words said)
const std::pair<const char*, const char*> kRefuse[] = {
    {"BUILD", "I can't build that: no {item} in my build menu."}, {"PLANT_CROP", "I can't plant that: I have no {item} to plant."},
    {"WATER", "I can't water that: I see no {item}."}, {"HARVEST", "I can't harvest that: I see no {item}."},
    {"FEED", "I can't feed that: I see no {item}."}, {"COLLECT", "I can't collect that: I see no {item}."},
    {"DELIVER", "I can't bring that: I have no {item}."}, {"REPAIR", "I can't repair that: I see no {item}."},
    {"DEMOLISH", "I can't tear that down: I see no {item}."}};
const char* const kNoLeads[] = {"no", "nope", "nah", "not", "negative", "wrong"};
const char* const kSaidWords[] = {"said", "meant", "mean"};   // world.py SAID_WORDS
const char* const kLostPointers[] = {"there", "here"};

template <size_t N>
bool OneOf(std::string_view s, const char* const (&list)[N]) {
    for (const char* x : list)
        if (s == x) return true;
    return false;
}

// "again", "once more", "one more time" among the words of the line
bool SaysAgain(const std::vector<std::string>& w) {
    for (size_t i = 0; i < w.size(); ++i) {
        if (w[i] == "again") return true;
        if (i + 1 < w.size() && (w[i] == "once" || w[i] == "one") && w[i + 1] == "more") return true;
    }
    return false;
}

const char* DirectionWords(PlaceDirection d) {
    switch (d) {
        case PlaceDirection::Left: return "to the left";
        case PlaceDirection::Right: return "to the right";
        case PlaceDirection::Forward: return "forward";
        case PlaceDirection::Back: return "back";
        case PlaceDirection::Up: return "up";
        case PlaceDirection::Down: return "down";
        case PlaceDirection::None: break;
    }
    return "";
}

// locations.tokenize: a token is a maximal run of ASCII letters and digits (A-Z lowercased), every other byte separates
std::vector<std::string> Words(std::string_view text) {
    std::vector<std::string> out;
    std::string word;
    for (unsigned char c : text) {
        if (c >= 'A' && c <= 'Z') c = static_cast<unsigned char>(c - 'A' + 'a');
        if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')) {
            word.push_back(static_cast<char>(c));
        } else if (!word.empty()) {
            out.push_back(std::move(word));
            word.clear();
        }
    }
    if (!word.empty()) out.push_back(std::move(word));
    return out;
}

template <size_t N>
bool AnyOf(const std::vector<std::string>& words, const char* const (&list)[N]) {
    for (const std::string& w : words)
        for (const char* x : list)
            if (w == x) return true;
    return false;
}

bool PlaceIntent(std::string_view label) { return OneOf(label, kPlaceIntents) || OneOf(label, kFarmIntents); }

std::string JoinWords(const std::vector<std::string>& w) {
    std::string s;
    for (size_t i = 0; i < w.size(); ++i) s += (i ? " " : "") + w[i];
    return s;
}

// world.singular: a plural's singular, near enough to compare a said word with a catalogue's
bool EndsWith(const std::string& w, const char* tail) {
    const size_t n = std::char_traits<char>::length(tail);
    return w.size() >= n && w.compare(w.size() - n, n, tail) == 0;
}
std::string Singular(const std::string& w) {
    if (w.size() > 4 && EndsWith(w, "ies")) return w.substr(0, w.size() - 3) + "y";
    if (w.size() > 4 && (EndsWith(w, "oes") || EndsWith(w, "ches") || EndsWith(w, "shes") || EndsWith(w, "sses") || EndsWith(w, "xes")))
        return w.substr(0, w.size() - 2);
    if (w.size() > 3 && EndsWith(w, "s") && !EndsWith(w, "ss") && !EndsWith(w, "us")) return w.substr(0, w.size() - 1);
    return w;
}
// world.same_words: every word of a phrase (single spaces) singular
std::string SameWords(const std::string& p) {
    std::string out;
    for (size_t start = 0;;) {
        const size_t sp = p.find(' ', start);
        if (start) out += ' ';
        out += Singular(p.substr(start, sp == std::string::npos ? std::string::npos : sp - start));
        if (sp == std::string::npos) return out;
        start = sp + 1;
    }
}
std::string LastWord(const std::string& p) {
    const size_t sp = p.rfind(' ');
    return sp == std::string::npos ? p : p.substr(sp + 1);
}

std::string ZoneName(const std::string& zone) {
    static const std::pair<const char*, const char*> kNames[] = {
        {"basement", "the basement"}, {"floor_1", "the first floor"}, {"floor_2", "the second floor"}, {"top_floor", "the top floor"},
        {"roof", "the roof"}, {"up", "the way up"}, {"down", "the way down"}, {"inside", "the way in"}};
    for (const auto& n : kNames)
        if (zone == n.first) return n.second;
    return "that place";
}

std::string Capitalized(std::string s) {   // Python str.capitalize() on an ASCII phrase
    for (size_t i = 0; i < s.size(); ++i) {
        char& c = s[i];
        if (i == 0 && c >= 'a' && c <= 'z') c = static_cast<char>(c - 'a' + 'A');
        if (i > 0 && c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
    }
    return s;
}

}  // namespace

const std::vector<Prior>& DefaultPriors() {
    // world.PRIORS: 0.75 everywhere (the simulation in stt/priors_v54.py: all of the gain of a right world, almost
    // none of the cost of a wrong one)
    constexpr double x = 0.75;
    static const std::vector<Prior> kPriors = {
        {"CROUCH", "stance=crouch", x}, {"PRONE", "stance=prone", x}, {"STAND_UP", "stance=stand", x},
        {"VAULT_WINDOW", "no_object=window", x}, {"OPEN", "no_object=door", x}, {"GET_IN", "no_object=car", x},
        {"DEFUSE", "no_tag=bomb", x}, {"PLANT", "bot_without=bomb", x}, {"REVIVE_ME", "player_up", x},   // REVIVE_ME: bots up to v55
        {"YES", "no_question", x}, {"NO", "no_question", x}, {"MAYBE", "no_question", x}, {"DONT_KNOW", "no_question", x},
    };
    return kPriors;
}

std::string Describe(const WorldEntity& e) {
    // int(round(distance)): Python rounds half to even, as nearbyint does under the default rounding mode
    return std::string(SectorWord(e.bearing, e.elevation)) + ", " + std::to_string(static_cast<long long>(std::nearbyint(e.distance))) + " m";
}

bool ValidateWorld(const WorldState& w, const LocationMatcher& places, std::string* error) {
    auto fail = [&](const std::string& msg) {
        if (error) *error = "world state refused: " + msg;
        return false;
    };
    std::vector<std::string> ids;
    for (const WorldEntity& e : w.entities) {
        if (e.id.empty()) return fail("an entity without an id");
        if (std::find(ids.begin(), ids.end(), e.id) != ids.end()) return fail("entity id " + e.id + " twice");
        ids.push_back(e.id);
        if (!e.object.empty() && places.ObjectIndex(e.object) < 0) return fail(e.id + ": unknown object " + e.object);
        if (!e.qualifier.empty() && places.QualifierIndex(e.qualifier) < 0) return fail(e.id + ": unknown qualifier " + e.qualifier);
        if (!e.zone.empty() && places.ZoneIndex(e.zone) < 0) return fail(e.id + ": unknown zone " + e.zone);
        if (!(-180.0 < e.bearing && e.bearing <= 180.0)) return fail(e.id + ": bearing out of (-180, 180]");
        if (!(e.distance >= 0.0)) return fail(e.id + ": negative distance");
    }
    for (const WorldPin* p : {w.has_player_pin ? &w.player_pin : nullptr, w.has_bot_pin ? &w.bot_pin : nullptr}) {
        if (!p) continue;
        if (!p->entity.empty() && std::find(ids.begin(), ids.end(), p->entity) == ids.end()) return fail("pin on an unknown entity " + p->entity);
        if (!(-180.0 < p->bearing && p->bearing <= 180.0)) return fail("pin bearing out of (-180, 180]");
    }
    if (!w.player_gaze.empty() && std::find(ids.begin(), ids.end(), w.player_gaze) == ids.end()) return fail("gaze on an unknown entity " + w.player_gaze);
    if (w.bot_stance != "stand" && w.bot_stance != "crouch" && w.bot_stance != "prone") return fail("unknown stance " + w.bot_stance);
    if (w.has_time && !(w.time >= 0.0)) return fail("negative time");
    for (const auto& c : w.catalog) {   // world.validate_world: per intent with an item, entries with an id and words
        if (!OneOf(c.first, kItemIntents)) return fail("a catalog for " + c.first + ", which has no item");
        std::vector<std::string> seen;
        for (const CatalogEntry& e : c.second) {
            if (e.id.empty()) return fail("catalog " + c.first + ": an entry without an id");
            if (std::find(seen.begin(), seen.end(), e.id) != seen.end()) return fail("catalog " + c.first + ": entry id " + e.id + " twice");
            seen.push_back(e.id);
            if (e.words.empty()) return fail("catalog " + c.first + ": entry " + e.id + " has no words");
            for (const std::string& x : e.words)
                if (x.empty() || x != JoinWords(Words(x)))
                    return fail("catalog " + c.first + ": entry " + e.id + ": \"" + x + "\" must be lowercase ASCII words with one space between");
        }
    }
    return true;
}

std::string MatchCatalog(const std::string& item, const std::vector<CatalogEntry>& entries) {
    const std::string said = SameWords(item);
    for (const CatalogEntry& e : entries)
        for (const std::string& w : e.words)
            if (SameWords(w) == said) return e.id;
    const std::string head = LastWord(said);
    for (const CatalogEntry& e : entries)
        for (const std::string& w : e.words)
            if (SameWords(w) == head) return e.id;
    if (said.find(' ') == std::string::npos) {
        for (const CatalogEntry& e : entries)
            for (const std::string& w : e.words)
                if (LastWord(SameWords(w)) == said) return e.id;
    }
    return {};
}

// world.item_object: the map object an item names with its last words ("crate", "chicken coop"), or -1
static int ItemObject(const std::string& item, const LocationMatcher& places) {
    if (item.empty()) return -1;
    std::vector<std::string> w;
    for (size_t start = 0;;) {
        const size_t sp = item.find(' ', start);
        w.push_back(item.substr(start, sp == std::string::npos ? std::string::npos : sp - start));
        if (sp == std::string::npos) break;
        start = sp + 1;
    }
    for (size_t n = std::min(w.size(), places.MaxPhraseLen()); n >= 1; --n) {
        std::string joined;
        for (size_t i = w.size() - n; i < w.size(); ++i) joined += (joined.empty() ? "" : " ") + w[i];
        int index = -1;
        const char* kind = places.PhraseKind(joined, &index);
        if (kind && std::string(kind) == "object") return index;
    }
    return -1;
}

// world.without_item_place: the line's places without the one that is the item itself (BUILD, COLLECT, DELIVER)
static PlaceRecord WithoutItemPlace(const PlaceRecord& record, const std::string& item, bool keeps_object, const LocationMatcher& places) {
    const int obj = keeps_object ? ItemObject(item, places) : -1;
    if (obj < 0 || record.targets.empty()) return record;
    PlaceRecord out;
    int primary = -1;
    for (size_t i = 0; i < record.targets.size(); ++i) {
        if (record.targets[i].object == obj) continue;
        if (static_cast<int>(i) == record.primary) primary = static_cast<int>(out.targets.size());
        out.targets.push_back(record.targets[i]);
    }
    if (out.targets.size() == record.targets.size()) return record;
    if (primary < 0) {
        for (size_t i = 0; i < out.targets.size(); ++i)
            if (out.targets[i].role == PlaceRole::None) {
                primary = static_cast<int>(i);
                break;
            }
    }
    out.primary = primary;
    return out;
}

std::string Deixis(std::string_view text) {
    const std::vector<std::string> w = Words(text);
    if (AnyOf(w, kFarWords)) return {};
    if (AnyOf(w, kNearWords)) return "here";
    if (AnyOf(w, kNearDet)) return "near";
    return {};
}

bool Elliptical(std::string_view text) {
    const std::vector<std::string> w = Words(text);
    if (w.empty() || w.size() > kAnswerMaxTokens) return false;
    for (const char* x : kAnswerLeads)
        if (w[0] == x) return true;
    return false;
}

// world.after_no: the words of a line after its "no"s and an "I said" / "I meant" / "I mean"
std::vector<std::string> AfterNo(const std::vector<std::string>& w) {
    size_t i = 0;
    while (i < w.size() && OneOf(w[i], kNoLeads)) ++i;
    if (i + 1 < w.size() && w[i] == "i" && OneOf(w[i + 1], kSaidWords)) i += 2;
    return std::vector<std::string>(w.begin() + static_cast<std::ptrdiff_t>(i), w.end());
}

bool Usable(const Grounding& g) {
    return g.status == "resolved" && (!g.entity.empty() || g.via == "direction" || g.via == "here" || g.via == "inside" ||
                                      (g.via == "zone" && !g.candidates.empty()));
}

// world.ground_target
// "upstairs", "downstairs": a floor named by where it is from the speaker
static bool RelativeZone(const std::string& zone) { return zone == "up" || zone == "down"; }
// world.INSIDE (bot v56): indoors, where the player looks. No entity is "inside": the game finds the way in, and an object
// said with it is not narrowed by it
static const char* const kInside = "inside";

// whether an entity is on the floor the line names: its own zone, or any marked floor above / below the speaker
static bool OnZone(const WorldEntity& e, const std::string& zone) {
    if (RelativeZone(zone)) return !e.zone.empty() && InSector(zone == "up" ? PlaceDirection::Up : PlaceDirection::Down, 0.0, e.elevation);
    return e.zone == zone;
}

static Grounding GroundTarget(const PlaceTarget& t, const WorldState& world, const Memory& memory, const LocationMatcher& places, bool here) {
    const std::string obj = t.object >= 0 ? places.ObjectId(t.object) : std::string();
    const std::string qual = t.qualifier >= 0 ? places.QualifierId(t.qualifier) : std::string();
    const std::string zone = t.zone >= 0 ? places.ZoneId(t.zone) : std::string();
    const WorldEntity* gaze = nullptr;
    const WorldEntity* last = nullptr;
    for (const WorldEntity& e : world.entities) {
        if (!world.player_gaze.empty() && e.id == world.player_gaze) gaze = &e;
        if (!memory.last_entity.empty() && e.id == memory.last_entity) last = &e;
    }
    auto ids_of = [](const std::vector<const WorldEntity*>& v) {
        std::vector<std::string> ids;
        for (const WorldEntity* e : v) ids.push_back(e->id);
        return ids;
    };

    if (t.pointer == PlacePointer::Pin) {
        if (!world.has_player_pin) return Out("missing", {}, {}, "pin");
        const WorldPin& pin = world.player_pin;
        if (obj.empty()) return Out("resolved", pin.entity.empty() ? pin.id : pin.entity, {}, "pin");
        std::vector<const WorldEntity*> cands;
        for (const WorldEntity& e : world.entities)
            if (e.object == obj && (qual.empty() || e.qualifier == qual)) cands.push_back(&e);
        // "the door at my pin" on a map without doors marked: what the pin is on is that door
        if (cands.empty()) return Out("resolved", pin.entity.empty() ? pin.id : pin.entity, {}, "pin");
        std::stable_sort(cands.begin(), cands.end(), [&](const WorldEntity* a, const WorldEntity* b) {
            const double da = DistBetween(a->bearing, a->distance, pin.bearing, pin.distance);
            const double db = DistBetween(b->bearing, b->distance, pin.bearing, pin.distance);
            return da != db ? da < db : a->id < b->id;
        });
        return Out("resolved", cands[0]->id, ids_of(cands), "pin");
    }
    if (obj.empty()) {
        if (t.pointer == PlacePointer::This) {
            // "here": where the speaker stands, whatever the crosshair is on
            if (here && zone.empty() && t.direction == PlaceDirection::None) return Out("resolved", {}, {}, "here");
            if (gaze) return Out("resolved", gaze->id, {}, "gaze");
            if (last) return Out("resolved", last->id, {}, "memory");
            // the one place that is marked
            if (world.has_player_pin) return Out("resolved", world.player_pin.entity.empty() ? world.player_pin.id : world.player_pin.entity, {}, "pin");
            return Out("missing", {}, {}, "this");
        }
        if (zone == kInside) return Out("resolved", {}, {}, "inside");   // the game finds the way in, where the player looks
        if (!zone.empty()) {
            std::vector<const WorldEntity*> on;
            for (const WorldEntity& e : world.entities)
                if (OnZone(e, zone)) on.push_back(&e);
            if (RelativeZone(zone) && !on.empty()) {
                // the next floor that way: "upstairs" is one floor up, not the roof
                double nearest = std::abs(on[0]->elevation);
                for (const WorldEntity* e : on) nearest = std::min(nearest, std::abs(e->elevation));
                on.erase(std::remove_if(on.begin(), on.end(), [&](const WorldEntity* e) { return std::abs(e->elevation) > nearest + kStorey; }), on.end());
            }
            if (on.empty()) return Out("missing", {}, {}, "zone");   // a floor the world has no place on
            return Out("resolved", {}, ids_of(on), "zone");
        }
        if (t.direction != PlaceDirection::None) return Out("resolved", {}, {}, "direction");
        return Out("missing");
    }
    std::vector<const WorldEntity*> cands;
    for (const WorldEntity& e : world.entities)
        if (e.object == obj) cands.push_back(&e);
    // a way up or down (bot v56): "go up by the stairs", "take the steps down", "go up these stairs" with no stairs singled
    // out is the direction, and the game takes the nearest way that way, the one the player looks at first; the stairs the
    // world has go with it as the candidates. Only the stairs under the crosshair are those stairs. Never a question:
    // stairs the world does not have are no reason to ask either
    if ((t.direction == PlaceDirection::Up || t.direction == PlaceDirection::Down) && places.Vertical(t.object) && qual.empty() &&
        (zone.empty() || zone == kInside) && t.flag == PlaceFlag::None) {
        std::stable_sort(cands.begin(), cands.end(), [](const WorldEntity* a, const WorldEntity* b) {
            return a->distance != b->distance ? a->distance < b->distance : a->id < b->id;
        });
        const std::vector<std::string> ids = ids_of(cands);
        if (t.pointer == PlacePointer::This && gaze && std::find(ids.begin(), ids.end(), gaze->id) != ids.end())
            return Out("resolved", gaze->id, ids, "gaze");
        return Out("resolved", {}, ids, "direction");
    }
    if (cands.empty()) {
        // "that door" where no door is marked: the thing the crosshair is on is that door, if it is not a marked place
        // of another kind
        if (t.pointer == PlacePointer::This && gaze && gaze->object.empty()) return Out("resolved", gaze->id, {}, "gaze");
        return Out("missing");
    }
    auto keep = [&](auto pred) { cands.erase(std::remove_if(cands.begin(), cands.end(), [&](const WorldEntity* e) { return !pred(e); }), cands.end()); };
    if (!qual.empty()) keep([&](const WorldEntity* e) { return e->qualifier == qual; });
    if (!zone.empty() && zone != kInside) keep([&](const WorldEntity* e) { return OnZone(*e, zone); });   // "the door upstairs": a door on a floor above
    // "up the blue stairs": up is the way along a vertical object, not where it stands
    const bool along = (t.direction == PlaceDirection::Up || t.direction == PlaceDirection::Down) && places.Vertical(t.object);
    if (t.direction != PlaceDirection::None && !along)
        keep([&](const WorldEntity* e) { return InSector(t.direction, e->bearing, e->elevation); });
    if (t.flag == PlaceFlag::Other && last) keep([&](const WorldEntity* e) { return e->id != last->id; });
    if (cands.empty()) return Out("missing");
    std::stable_sort(cands.begin(), cands.end(), [](const WorldEntity* a, const WorldEntity* b) {
        return a->distance != b->distance ? a->distance < b->distance : a->id < b->id;
    });
    std::vector<std::string> ids = ids_of(cands);
    if (t.pointer == PlacePointer::This && gaze && std::find(ids.begin(), ids.end(), gaze->id) != ids.end())
        return Out("resolved", gaze->id, ids, "gaze");
    if (cands.size() == 1) return Out("resolved", ids[0], ids, "only");
    if (t.flag == PlaceFlag::UnknownModifier) return Out("ambiguous", {}, ids, "unknown_modifier");
    if (Fetched(obj) || cands[1]->distance >= kClearlyNearer * cands[0]->distance) return Out("resolved", ids[0], ids, "nearest");
    return Out("ambiguous", {}, ids, "distance");
}

std::vector<Grounding> Ground(const PlaceRecord& record, const WorldState& world, const Memory& memory, const LocationMatcher& places,
                              std::string_view text, std::string_view intent) {
    const bool here = Deixis(text) == "here" && !OneOf(intent, kPointedHere);
    std::vector<Grounding> out;
    for (const PlaceTarget& t : record.targets) out.push_back(GroundTarget(t, world, memory, places, here));
    return out;
}

static bool ConditionHolds(const std::string& cond, const WorldState& world, const Memory& memory) {
    auto starts = [&](const char* p) { return cond.rfind(p, 0) == 0; };
    if (starts("stance=")) return world.bot_stance == cond.substr(7);
    if (starts("no_object=")) {
        const std::string o = cond.substr(10);
        return std::none_of(world.entities.begin(), world.entities.end(), [&](const WorldEntity& e) { return e.object == o; });
    }
    if (starts("no_tag=")) {
        const std::string tag = cond.substr(7);
        return std::none_of(world.entities.begin(), world.entities.end(), [&](const WorldEntity& e) {
            return std::find(e.tags.begin(), e.tags.end(), tag) != e.tags.end();
        });
    }
    if (starts("bot_without=")) {
        const std::string item = cond.substr(12);
        return std::find(world.bot_items.begin(), world.bot_items.end(), item) == world.bot_items.end();
    }
    if (cond == "player_up") return !world.player_downed;
    if (cond == "no_question") return !memory.has_question;
    return false;   // an unknown condition never holds (world.py raises; the config is checked at load)
}

bool ApplyPriors(std::vector<double>* probs, const std::vector<std::string>& labels, const WorldState& world, const Memory& memory,
                 const std::vector<Prior>& priors) {
    bool changed = false;
    for (size_t j = 0; j < labels.size() && j < probs->size(); ++j)
        for (const Prior& p : priors)
            if (p.label == labels[j] && ConditionHolds(p.condition, world, memory)) {
                (*probs)[j] *= p.x;
                changed = true;
            }
    return changed;   // not renormalized: a prior only lowers, it never lifts another intent over the threshold
}

// ---- the planner ---------------------------------------------------------------------------------

void Planner::Init(BotBrain* brain, std::vector<Prior> priors) {
    brain_ = brain;
    priors_ = std::move(priors);
    world_ = WorldState();
    Reset();
}

bool Planner::SetWorld(const WorldState& world, std::string* error) {
    if (!ValidateWorld(world, brain_->Places(), error)) return false;
    world_ = world;
    return true;
}

void Planner::Reset() {
    brain_->Reset();
    memory_ = Memory();
    DropPending();
    frame_in_line_ = false;
}

void Planner::DropPending() {
    pending_entity_.clear();
    pending_here_ = pending_near_ = false;
    pending_item_ = ItemInfo();
}

// world.Planner._plants_crops
bool Planner::PlantsCrops() const {
    if (brain_->LabelIndex("PLANT_CROP") < 0) return false;
    if (std::find(world_.bot_items.begin(), world_.bot_items.end(), "bomb") != world_.bot_items.end()) return false;
    const std::vector<CatalogEntry>* seeds = world_.Catalog("PLANT_CROP");
    return seeds && !seeds->empty();
}

// world.Planner._item
bool Planner::ItemOf(std::string_view text, const std::string& intent, ItemInfo* item, std::string* refused) const {
    *item = ItemInfo();
    refused->clear();
    const ItemFound f = brain_->Items().Find(text, intent, brain_->Places());
    if (f.has_item) item->said = f.item;
    const std::vector<CatalogEntry>* cat = world_.Catalog(intent);
    if (item->said.empty() || !cat) return true;
    item->id = MatchCatalog(item->said, *cat);
    if (!item->id.empty()) return true;
    for (const auto& r : kRefuse) {
        if (intent != r.first) continue;
        std::string say = r.second;
        const size_t at = say.find("{item}");
        *refused = say.replace(at, 6, item->said);
    }
    return false;
}

const WorldEntity* Planner::Entity(const std::string& id) const {
    for (const WorldEntity& e : world_.entities)
        if (e.id == id) return &e;
    return nullptr;
}

const std::string& Planner::Label(int intent) const { return brain_->Config().labels[static_cast<size_t>(intent)]; }

// world.Planner._alive
bool Planner::Alive(const Memory::Frame& f) const {
    if (!f.has || !world_.has_time || !f.has_time) return false;
    const double age = world_.time - f.time;
    return world_.bot_busy || (0.0 <= age && age <= kContextSeconds);
}

// world.Planner._known
bool Planner::Known(const Grounding& g) const {
    if (g.entity.empty()) return true;
    if (Entity(g.entity)) return true;
    return world_.has_player_pin && (g.entity == world_.player_pin.id || (!world_.player_pin.entity.empty() && g.entity == world_.player_pin.entity));
}

// world.Planner._where
std::string Planner::Where(const PlaceTarget* t, const Grounding* g) const {
    if (!g) return {};
    const bool on_pin = world_.has_player_pin && !g->entity.empty() &&
                        (g->entity == world_.player_pin.id || (!world_.player_pin.entity.empty() && g->entity == world_.player_pin.entity));
    if (g->via == "pin" || g->via == "pin_default" || on_pin) return "on your pin";
    if (g->via == "here") return "here";
    if (!g->entity.empty()) return "there";
    return t ? DirectionWords(t->direction) : "";
}

// world.Planner._echo
std::string Planner::Echo(int intent, const PlaceTarget* t, const Grounding* g) const {
    const std::string phrase = Capitalized(brain_->Config().phrases.at(Label(intent)));
    const std::string where = Where(t, g);
    return where.empty() ? phrase + "." : phrase + ", " + where + ".";
}

// world.Planner._default_place
bool Planner::DefaultPlace(int intent, PlaceTarget* t, Grounding* g) const {
    const std::string& label = Label(intent);
    if (OneOf(label, kFire) && !world_.player_gaze.empty()) {
        const WorldEntity* gaze = Entity(world_.player_gaze);
        // the game takes the enemy under the crosshair
        if (gaze && std::find(gaze->tags.begin(), gaze->tags.end(), "enemy") != gaze->tags.end()) return false;
    }
    const Memory::Frame& f = memory_.frame;
    if (OneOf(label, kCarry) && f.has && f.intent == intent && f.has_target && Alive(f) && Known(f.ground)) {
        *t = f.target;
        *g = f.ground;
        return true;
    }
    if (OneOf(label, kPinDefault) && world_.has_player_pin) {
        *t = PlaceTarget();
        t->pointer = PlacePointer::Pin;
        *g = Out("resolved", world_.player_pin.entity.empty() ? world_.player_pin.id : world_.player_pin.entity, {}, "pin_default");
        return true;
    }
    return false;
}

// world.Planner._reissue
void Planner::Reissue(const Memory::Frame& f, const PlaceTarget* t, const Grounding* g, bool nearby, const char* lead, PlannerResult* out) {
    PlaceRecord rec;
    std::vector<Grounding> grounding;
    if (t) {
        rec.targets = {*t};
        rec.primary = 0;
        grounding = {*g};
    }
    const int intent = f.intent;
    const bool other = f.other;
    out->action = "resolved";
    out->has_order = true;
    const ItemInfo item = f.item;
    out->order = MakeOrder(intent, rec, grounding, t ? 0 : -1, other, nearby, nullptr, &item);
    out->say = std::string(lead) + Echo(intent, t, g);
}

// world.Planner._context
bool Planner::Context(std::string_view text, const Decision& d, PlannerResult* out) {
    const Memory::Frame f = memory_.frame;   // a copy: giving the order again replaces the frame
    const std::vector<std::string> w = Words(text);
    if (!f.has || w.empty()) return false;
    const std::string& frame_label = Label(f.intent);
    const bool alive = Alive(f);
    const PlaceRecord& record = d.places;
    const int k = record.targets.empty() ? -1 : record.primary;
    const bool has_target = k >= 0;
    const std::string deixis = Deixis(text);
    PlaceTarget place_t;
    Grounding place_g;
    bool has_place = false;
    if (has_target && record.targets[static_cast<size_t>(k)].role == PlaceRole::None) {
        // the place as the previous order reads it: "here" after "shoot" is the crosshair's point
        place_t = record.targets[static_cast<size_t>(k)];
        place_g = GroundTarget(place_t, world_, memory_, brain_->Places(), deixis == "here" && !OneOf(frame_label, kPointedHere));
        has_place = Usable(place_g);
    }
    const bool nearby = !deixis.empty();
    const bool unsure = d.action == Action::SayAgain || d.action == Action::Ignore || d.action == Action::Answer;
    if (OneOf(w.front(), kNoLeads) && has_target) {
        // "No, come here.": an order of its own after the "no", read as it stands; a place alone is the correction
        const std::vector<std::string> rest = AfterNo(w);
        const bool place_only = !rest.empty() && rest.size() <= kAnswerMaxTokens && OneOf(rest.front(), kAnswerLeads);
        if (!rest.empty() && !place_only) return false;
    }
    if (!has_target && alive && d.action == Action::SayAgain && d.prob < kFragmentUnsure && OneOf(w.back(), kLostPointers) &&
        PlaceIntent(frame_label)) {
        // the place matcher takes "there" only after an order word; here the order word is what was misheard
        PlaceTarget lost;
        lost.pointer = PlacePointer::This;
        const Grounding g = GroundTarget(lost, world_, memory_, brain_->Places(), w.back() == "here" && !OneOf(frame_label, kPointedHere));
        if (Usable(g)) {
            Reissue(f, &lost, &g, nearby, "Got it. ", out);
            return true;
        }
    }
    if (OneOf(w.front(), kNoLeads) && alive && d.action != Action::Negated) {
        if (has_place && PlaceIntent(frame_label)) {
            Reissue(f, &place_t, &place_g, nearby, "Got it. ", out);
            return true;
        }
        if (!has_target && unsure) {
            memory_.frame = Memory::Frame();
            out->action = "negated";
            out->say = "Copy, stopping.";
            return true;
        }
    }
    if (SaysAgain(w) && !has_place && !has_target) {
        const bool same = d.action == Action::Act && d.intent == f.intent && f.has_target && Known(f.ground);
        if (((unsure && alive) || same) && (!f.has_target || Known(f.ground))) {
            Reissue(f, f.has_target ? &f.target : nullptr, f.has_target ? &f.ground : nullptr, f.nearby, "", out);
            return true;
        }
    }
    if (alive && has_place && PlaceIntent(frame_label) &&
        ((Elliptical(text) && (unsure || d.action == Action::Act)) || (d.action == Action::SayAgain && d.prob < kFragmentUnsure))) {
        Reissue(f, &place_t, &place_g, nearby, "Got it. ", out);
        return true;
    }
    return false;
}

// world.names_again
static bool NamesAgain(const PlaceTarget& t, const PlaceTarget& said) {
    return t.object >= 0 && t.object == said.object && (t.flag == PlaceFlag::None || t.flag == said.flag) && (t.qualifier < 0 || t.qualifier == said.qualifier) &&
           (t.zone < 0 || t.zone == said.zone) && (t.direction == PlaceDirection::None || t.direction == said.direction) &&
           (t.pointer == PlacePointer::None || t.pointer == said.pointer);
}

// world.Planner._same_place
void Planner::SamePlace(const PlaceRecord& record, std::vector<Grounding>* grounding) const {
    const Memory::Frame& f = memory_.frame;
    const int k = record.targets.empty() ? -1 : record.primary;
    if (!f.has || k < 0 || !f.has_target || f.ground.entity.empty() || !Known(f.ground)) return;
    const PlaceTarget& t = record.targets[static_cast<size_t>(k)];
    if (t.role != PlaceRole::None || !NamesAgain(t, f.has_said ? f.said : f.target)) return;
    (*grounding)[static_cast<size_t>(k)] = f.ground;
}

Order Planner::MakeOrder(int intent, const PlaceRecord& record, const std::vector<Grounding>& grounding, int k, bool other, bool nearby,
                         const PlaceTarget* said, const ItemInfo* item) {
    Order o;
    o.intent = intent;
    o.other = other;
    if (brain_->Items().HasItem(Label(intent))) {   // what it acts on: the v60 bots' orders only
        o.has_item = true;
        if (item) {
            o.item = item->said;
            o.item_id = item->id;
        }
    }
    if (Label(intent) != "GO_NOW") {   // "go" with nothing queued is not an order to come back to
        Memory::Frame f;
        f.has = true;
        f.intent = intent;
        f.other = other;
        f.nearby = nearby;
        f.has_time = world_.has_time;
        f.time = world_.time;
        if (k >= 0) {
            f.has_target = true;
            f.target = record.targets[static_cast<size_t>(k)];
            f.ground = grounding[static_cast<size_t>(k)];
        }
        if (said) {
            f.has_said = true;
            f.said = *said;
        }
        if (item) f.item = *item;
        memory_.frame = f;
        frame_in_line_ = true;
    }
    if (k >= 0) {
        const PlaceTarget& t = record.targets[static_cast<size_t>(k)];
        const Grounding& g = grounding[static_cast<size_t>(k)];
        o.entity = g.entity;
        o.candidates = g.candidates;
        o.direction = t.direction;
        o.zone = t.zone;
        o.object = t.object;
        o.pointer = t.pointer;
        o.via = g.via;
        o.nearby = nearby && t.pointer == PlacePointer::This;
        if (!g.entity.empty()) memory_.last_entity = g.entity;
    }
    memory_.last_order = brain_->Config().labels[static_cast<size_t>(intent)];
    return o;
}

void Planner::Ask(int intent, const PlaceRecord& record, const std::vector<Grounding>& grounding, int k, bool other, bool queued,
                  PlannerResult* out, const ItemInfo* item) {
    const Grounding& g = grounding[static_cast<size_t>(k)];
    const PlaceTarget& t = record.targets[static_cast<size_t>(k)];
    const std::string obj = t.object >= 0 ? brain_->Places().ObjectId(t.object) : "place";
    Memory::Question& q = memory_.question;
    q = Memory::Question();
    q.intent = intent;
    q.record = record;
    q.k = k;
    q.other = other;
    q.queued = queued;
    if (item) q.item = *item;
    memory_.has_question = true;
    out->action = "ask";
    if (g.status == "missing") {
        q.kind = "missing";
        const std::string what = g.via == "pin" ? "I don't see a pin."
                                 : g.via == "this" ? "I don't know where you mean."
                                 : g.via == "zone" ? "I can't find " + ZoneName(t.zone >= 0 ? brain_->Places().ZoneId(t.zone) : std::string()) + "."
                                                   : "I see no " + obj + ".";
        out->say = what + " Where?";
        return;
    }
    q.kind = "which";
    q.candidates = g.candidates;
    out->say = "Which " + obj + "? The one " + Describe(*Entity(g.candidates[0])) + "?";
}

// world.Planner._other_one
bool Planner::OtherOne(std::vector<std::string> left, const PlaceTarget* said, PlannerResult* out) {
    Memory::Question& q = memory_.question;
    left.erase(std::remove(left.begin(), left.end(), q.candidates[static_cast<size_t>(q.offered)]), left.end());
    if (left.size() == 1) {
        const Memory::Question copy = q;
        memory_.has_question = false;
        Settle(copy, left[0], "Got it.", out, said);
        return true;
    }
    if (left.empty()) return false;
    out->action = "ask";
    out->say = "The one " + Describe(*Entity(left[0])) + "?";
    q.candidates = std::move(left);
    q.offered = 0;
    return true;
}

void Planner::Settle(const Memory::Question& q, const std::string& entity, const std::string& say, PlannerResult* out, const PlaceTarget* said) {
    const std::string& phrase = brain_->Config().phrases.at(brain_->Config().labels[static_cast<size_t>(q.intent)]);
    out->action = "resolved";
    if (q.queued) {
        brain_->SetPending(q.intent, q.record, q.other);
        DropPending();
        pending_entity_ = entity;
        pending_item_ = q.item;
        memory_.last_entity = entity;
        out->say = say + " Ready to " + phrase + ". On your go.";
        return;
    }
    std::vector<Grounding> grounding = {Out("resolved", entity, q.candidates, "answer")};
    PlaceRecord rec;
    rec.targets = {q.record.targets[static_cast<size_t>(q.k)]};
    rec.primary = 0;
    out->say = say + " " + Capitalized(phrase) + ".";
    out->has_order = true;
    out->order = MakeOrder(q.intent, rec, grounding, 0, q.other, false, said, &q.item);
}

// world.Planner._settle_place
void Planner::SettlePlace(const Memory::Question& q, const PlaceRecord& rec, const Grounding& g, bool queued, bool nearby, PlannerResult* out) {
    memory_.has_question = false;
    const std::string& phrase = brain_->Config().phrases.at(brain_->Config().labels[static_cast<size_t>(q.intent)]);
    out->action = "resolved";
    if (queued) {
        brain_->SetPending(q.intent, rec, q.other);
        pending_entity_ = g.entity;
        pending_here_ = g.via == "here";
        pending_near_ = nearby;
        pending_item_ = q.item;
        if (!g.entity.empty()) memory_.last_entity = g.entity;
        out->say = "Got it. Ready to " + phrase + ". On your go.";
        return;
    }
    out->say = "Got it. " + Capitalized(phrase) + ".";
    out->has_order = true;
    out->order = MakeOrder(q.intent, rec, {g}, 0, q.other, nearby, &q.record.targets[static_cast<size_t>(q.k)], &q.item);
}

// world.Planner._place_answer
bool Planner::PlaceAnswer(std::string_view text, const Decision& d, PlannerResult* out) {
    const Memory::Question q = memory_.question;   // a copy: settling drops the question
    const PlaceRecord& record = d.places;
    const int k = record.targets.empty() ? -1 : record.primary;
    const bool nearby = !Deixis(text).empty();
    if (k >= 0) {
        const PlaceTarget t = record.targets[static_cast<size_t>(k)];
        const Grounding g = out->ground[static_cast<size_t>(k)];
        const bool answers = d.action == Action::SayAgain || d.action == Action::Ignore || d.action == Action::Answer ||
                             ((d.action == Action::Act || d.action == Action::Queued) && (d.intent == q.intent || Elliptical(text)));
        if (t.role != PlaceRole::None || !Usable(g) || !answers) return false;
        if (d.action == Action::Queued) brain_->Reset();   // the line's own "on my go" queued another order
        PlaceRecord rec;
        rec.targets = {t};
        rec.primary = 0;
        SettlePlace(q, rec, g, q.queued || d.action == Action::Queued, nearby, out);
        return true;
    }
    const bool yes = d.action == Action::Answer && d.intent >= 0 && brain_->Config().labels[static_cast<size_t>(d.intent)] == "YES";
    if (d.action == Action::Go || yes) {
        const PlaceTarget t0 = q.record.targets[static_cast<size_t>(q.k)];
        const Grounding g = GroundTarget(t0, world_, memory_, brain_->Places(), false);
        if (Usable(g)) {
            PlaceRecord rec;
            rec.targets = {t0};
            rec.primary = 0;
            SettlePlace(q, rec, g, q.queued, false, out);
            return true;
        }
    }
    return false;
}

bool Planner::Answer(int intent, PlannerResult* out) {
    const std::vector<std::string>& labels = brain_->Config().labels;
    const std::string& name = labels[static_cast<size_t>(intent)];
    const bool yes = name == "YES", no = name == "NO", unsure = name == "MAYBE" || name == "DONT_KNOW";
    Memory::Question& q = memory_.question;
    if (q.kind != "which") {
        if (unsure || yes) return false;
        memory_.has_question = false;
        out->action = "resolved";
        out->say = "Copy, never mind.";
        return true;
    }
    if (yes || unsure) {
        const std::string pick = yes ? q.candidates[static_cast<size_t>(q.offered)] : q.candidates[0];
        const Memory::Question copy = q;
        memory_.has_question = false;
        Settle(copy, pick, yes ? "Got it." : "I'll take the one " + Describe(*Entity(pick)) + ".", out);
        return true;
    }
    (void)no;
    ++q.offered;
    if (q.offered < static_cast<int>(q.candidates.size())) {
        out->action = "ask";
        out->say = "The one " + Describe(*Entity(q.candidates[static_cast<size_t>(q.offered)])) + "?";
        return true;
    }
    memory_.has_question = false;
    out->action = "resolved";
    out->say = "Which one, then? Point at it.";
    return true;
}

PlannerResult Planner::Step(std::string_view text, const std::vector<float>& probs, bool continued) {
    if (!continued) frame_in_line_ = false;
    PlannerResult out;
    std::vector<double> adjusted(probs.begin(), probs.end());
    out.adjusted = ApplyPriors(&adjusted, brain_->Config().labels, world_, memory_, priors_);
    std::vector<float> p2;
    p2.reserve(adjusted.size());
    for (double x : adjusted) p2.push_back(static_cast<float>(x));
    Decision d = brain_->Decide(text, out.adjusted ? p2 : probs);
    out.decision = d;
    out.intent = d.intent;
    out.prob = d.prob;
    out.action = ActionName(d.action);
    if (d.intent >= 0 && (d.action == Action::Act || d.action == Action::Queued) && OneOf(Label(d.intent), kNoPlace))
        d.places = PlaceRecord();   // going back, letting the player out: the line's place is not the order's
    const bool order_line = d.intent >= 0 && (d.action == Action::Act || d.action == Action::Queued);
    if (order_line && Label(d.intent) == "PLANT" && PlantsCrops()) {
        // a bare "plant it": no bomb on the bot, seeds in its bag
        d.intent = out.intent = out.decision.intent = brain_->LabelIndex("PLANT_CROP");
        if (d.action == Action::Queued) brain_->SetPending(d.intent, brain_->PendingPlaces(), brain_->PendingOther());
    }
    ItemInfo item;
    const bool has_item = order_line && brain_->Items().HasItem(Label(d.intent));
    if (has_item) {
        std::string refused;
        if (!ItemOf(text, Label(d.intent), &item, &refused)) {   // the game's catalogue lacks it: said, no order
            if (d.action == Action::Queued) brain_->Reset();
            memory_.has_question = false;
            out.action = "refused";
            out.say = refused;
            return out;
        }
        d.places = WithoutItemPlace(d.places, item.said, brain_->Items().KeepsObject(Label(d.intent)), brain_->Places());
        if (d.action == Action::Queued) brain_->SetPending(brain_->Pending(), d.places, brain_->PendingOther());
    }
    PlaceRecord record = d.places;   // a copy: an order that names no place may get one from the context
    const LocationMatcher& places = brain_->Places();
    if (!record.targets.empty()) out.ground = Ground(record, world_, memory_, places, text, d.intent >= 0 ? Label(d.intent) : std::string());
    if (continued && frame_in_line_) SamePlace(record, &out.ground);
    const bool nearby = !Deixis(text).empty();
    const bool had_question = memory_.has_question;

    if (had_question && memory_.question.kind == "which" && d.other && record.targets.empty() &&
        (d.action == Action::SayAgain || d.action == Action::Ignore || (d.action == Action::Answer && Label(d.intent) == "NO") ||
         (d.action == Action::Act && (d.intent == memory_.question.intent || Label(d.intent) == "HOLD_OTHER_ANGLE")))) {
        // "the other one", "no, the other one": no place said. The classifier reads the words as nothing, as a no, as
        // the order asked about, or as the other angle
        if (OtherOne(memory_.question.candidates, nullptr, &out)) return out;
    }
    if (had_question && d.action == Action::Answer) {
        if (Answer(d.intent, &out)) return out;
    }
    if (had_question && memory_.question.kind == "missing") {
        if (PlaceAnswer(text, d, &out)) return out;
    }
    if (had_question && memory_.question.kind == "which" && !record.targets.empty() &&
        (d.action == Action::SayAgain || d.action == Action::Ignore ||
         ((d.action == Action::Act || d.action == Action::Queued) && d.intent == memory_.question.intent))) {
        // a place instead of yes / no: "the left one", "the north door" -- if it narrows the candidates to one. A line
        // the classifier reads as another order is that order, and the question is dropped below
        const int k = record.primary;
        if (k >= 0 && record.targets[static_cast<size_t>(k)].role == PlaceRole::None) {
            const PlaceTarget& t = record.targets[static_cast<size_t>(k)];
            const Memory::Question& q = memory_.question;
            std::vector<std::string> left;
            for (const std::string& c : q.candidates) {
                const WorldEntity& e = *Entity(c);
                if (t.object >= 0 && e.object != places.ObjectId(t.object)) continue;
                if (t.qualifier >= 0 && e.qualifier != places.QualifierId(t.qualifier)) continue;
                if (t.direction != PlaceDirection::None && !InSector(t.direction, e.bearing, e.elevation)) continue;
                if (t.pointer == PlacePointer::This && !(world_.player_gaze.empty() || world_.player_gaze == c)) continue;
                left.push_back(c);
            }
            if (t.pointer == PlacePointer::Pin && world_.has_player_pin && !left.empty()) {
                // "Stairs on my pin.": of the candidates, the one nearest the pin (as GroundTarget takes it)
                const WorldPin& pin = world_.player_pin;
                std::string best;
                double best_d = 0.0;
                for (const std::string& c : left) {
                    const WorldEntity& e = *Entity(c);
                    const double dd = DistBetween(e.bearing, e.distance, pin.bearing, pin.distance);
                    if (best.empty() || dd < best_d || (dd == best_d && c < best)) {
                        best = c;
                        best_d = dd;
                    }
                }
                left = {best};
            }
            if (t.flag == PlaceFlag::Other) {
                if (OtherOne(left, &t, &out)) return out;   // "the other door"
            } else if (left.size() == 1 && (t.object >= 0 || t.direction != PlaceDirection::None || t.pointer != PlacePointer::None)) {
                const Memory::Question copy = q;
                memory_.has_question = false;
                Settle(copy, left[0], "Got it.", &out);
                return out;
            }
        }
    }
    if (d.action != Action::SayAgain) memory_.has_question = false;   // any other line drops the question

    // nothing was asked: the line may be about the previous order
    if (!had_question && Context(text, d, &out)) return out;
    bool defaulted = false;
    PlaceTarget default_t;
    Grounding default_g;
    if ((d.action == Action::Act || d.action == Action::Queued) && record.targets.empty() && DefaultPlace(d.intent, &default_t, &default_g)) {
        // an order that names no place: the context has one
        defaulted = true;
        record.targets = {default_t};
        record.primary = 0;
        out.ground = {default_g};
        if (d.action == Action::Queued) brain_->SetPending(d.intent, record, d.other);   // it goes with the place it was given
    }

    if (d.action == Action::Act || d.action == Action::Queued) {
        const int k = record.primary;
        if (k >= 0 && record.targets[static_cast<size_t>(k)].role == PlaceRole::None) {
            const Grounding& g = out.ground[static_cast<size_t>(k)];
            if (g.status == "ambiguous" || g.status == "missing") {
                if (d.action == Action::Queued) brain_->Reset();   // the question decides the queued order's place
                Ask(d.intent, record, out.ground, k, d.other, d.action == Action::Queued, &out, has_item ? &item : nullptr);
                return out;
            }
        }
        if (d.action == Action::Act) {
            out.has_order = true;
            out.order = MakeOrder(d.intent, record, out.ground, k, d.other, nearby, nullptr, has_item ? &item : nullptr);
            if (defaulted) out.say = Echo(d.intent, &default_t, &default_g);   // the bot says what it assumed
        } else {
            DropPending();
            if (has_item) pending_item_ = item;
            if (k >= 0) {
                pending_entity_ = out.ground[static_cast<size_t>(k)].entity;
                pending_here_ = out.ground[static_cast<size_t>(k)].via == "here";
                pending_near_ = nearby;
            }
        }
    } else if (d.action == Action::Execute) {
        const PlaceRecord& ex = d.executed_places;
        const int k = ex.targets.empty() ? -1 : ex.primary;
        out.has_order = true;
        if (k >= 0 && (!pending_entity_.empty() || pending_here_)) {
            // the place the queued order was given, not what the crosshair is on now
            std::vector<Grounding> g = {Out("resolved", pending_entity_, {}, pending_here_ ? "here" : "queued")};
            PlaceRecord rec2;
            rec2.targets = {ex.targets[static_cast<size_t>(k)]};
            rec2.primary = 0;
            out.order = MakeOrder(d.executed, rec2, g, 0, d.executed_other, pending_near_, nullptr, &pending_item_);
        } else if (!pending_entity_.empty()) {
            out.order = MakeOrder(d.executed, PlaceRecord(), {}, -1, d.executed_other, false, nullptr, &pending_item_);
        } else {
            std::vector<Grounding> g2;
            if (!ex.targets.empty()) g2 = Ground(ex, world_, memory_, places);
            out.order = MakeOrder(d.executed, ex, g2, k, d.executed_other, pending_near_, nullptr, &pending_item_);
        }
        DropPending();
    } else if (d.action == Action::Go) {
        out.has_order = true;
        out.order = MakeOrder(d.intent, record, out.ground, -1, false);
    } else if (d.action == Action::Wait || d.action == Action::Negated) {
        DropPending();
        memory_.frame = Memory::Frame();
    }
    if (out.has_order && !out.order.entity.empty()) {   // the bot marks where it goes
        world_.has_bot_pin = true;
        world_.bot_pin = WorldPin();
        world_.bot_pin.id = "bot_pin";
        world_.bot_pin.entity = out.order.entity;
    }
    return out;
}

}  // namespace coop
