// The brain's tier 0: the world the bot acts in, without UE5 -- the C++ twin of scripts/coop/world.py (the rules and
// their reasons are documented there; this file follows it step by step and is checked against it: coop_cli
// --world-tests).
//
//   grounding   a place record resolved to the entities of the world state the game hands over before every line:
//               which door, which pin, where the player looks. One candidate: resolved. Several and nothing to tell
//               them apart: ambiguous -- the planner asks. None: missing -- the planner asks.
//   memory      the last place resolved, the last order, the question the bot asked. "there" without a gaze is the
//               last place; "the other door" is not the last door.
//   priors      what the world makes unlikely (a bot already prone, a window order without a window in sight, an
//               answer when nothing was asked): multipliers on the classifier's probabilities before the gate, not
//               renormalized. They never raise a probability.
//   planner     BotBrain's decision, then the world: an order with its entity for the game, or a question the player
//               answers with yes / no (the answer intents of a v54 bot) or with a place ("the left one").
//
// A world without named places (a map nobody has marked yet) leaves the pin, the crosshair, directions and the two
// people. The rules for it are about the words of the line, so they live here and not in the game: "here" is where
// the speaker is, not what the crosshair is on (Deixis); "that door" where no door is marked is the thing the
// crosshair is on; a "Where?" the bot asked is answered by pointing ("there", "at my pin", "on the left": Elliptical).
//
// A short context. The planner keeps ONE frame of the order it took last (what, where, when) and reads the next line
// against it before it reads it as a new order: a correction ("No, here, on my pin."), a repeat ("shoot again"), a
// fragment ("on my pin", "over there": a place and no action). An order that names no place takes one from the
// context: the same order's place a moment ago, else the standing pin; "here" is the speaker for "come here" and the
// crosshair's point for "shoot here". The game gives the time and whether the bot is still busy with the order; a
// game that sends no time gets no context. The rules and their reasons: scripts/coop/world.py, "a short context".
//
// A line of several orders. The decoder in front of the classifier (rewriter.h) writes "smoke the door then go in" as
// two order lines, and each goes through Step() as a line of its own, the second and later ones with continued = true.
// A place a further order names as the order before it did, in the same words or in fewer, is then that order's
// place: with two doors, or with none marked and the player pointing, the bot does not ask the same question twice.
// And "the other one" in answer to "Which door? The one ahead, 8 m?" is not the door the bot just offered.
// scripts/coop/world.py, "a line of several orders".
//
// The farmer and the builder (the v60 bots, a config with "items"). The intent is the verb; what it acts on is the item
// the line names (items.h: "build a pillar" = "pillar"). The game may send, per intent, what it has (WorldState::catalog:
// its build menu, the seeds the bot carries, what lies around): an item the intent's catalogue lacks is refused with the
// reason ("I can't build that: no pillar in my build menu.") and no order goes out; an intent without a catalogue passes
// the item on as said. For BUILD, COLLECT and DELIVER a place of the line that is the item itself ("carry the crate to the
// barn") is not where the order goes. A bare "plant" is planting a crop when the bot carries no bomb and has seeds.
// scripts/coop/world.py, "the farmer's and the builder's orders".
//
// Bearings are degrees in the player's view (0 ahead, positive to the right, (-180, 180]), distances and elevations
// metres. Entities carry the vocabulary's object, qualifier and zone ids (locations.json): the game tags its actors
// with the names the map callouts use.
#pragma once

#include <string>
#include <string_view>
#include <vector>

#include "coop_intent/bot_brain.h"
#include "coop_intent/locations.h"

namespace coop {

struct WorldEntity {
    std::string id;
    std::string object, qualifier, zone;   // vocabulary ids; empty: none
    double bearing = 0, distance = 0, elevation = 0;
    std::vector<std::string> tags;         // "closed", "cover", "bomb", ...: the priors read them
};

struct WorldPin {
    std::string id;
    std::string entity;   // the entity the pin is on, if any
    double bearing = 0, distance = 0, elevation = 0;
};

// one thing the game has for an intent: its id and the words players use for it (lowercase tokens, one space between)
struct CatalogEntry {
    std::string id;
    std::vector<std::string> words;
};

struct WorldState {
    std::vector<WorldEntity> entities;
    bool has_player_pin = false;
    WorldPin player_pin;
    bool has_bot_pin = false;
    WorldPin bot_pin;        // the bot marks where it goes (set by the planner on an order with an entity)
    std::string player_gaze;   // the entity under the player's crosshair; empty: none
    bool player_downed = false;
    std::string bot_stance = "stand";   // stand | crouch | prone
    std::vector<std::string> bot_items;   // "bomb", ...
    bool bot_busy = false;     // the bot is still carrying out the order it took last
    bool has_time = false;     // the game sends its clock: without it there is no context
    double time = 0;           // seconds
    // per intent with an item ("BUILD", "PLANT_CROP", ...), what the game has; an intent not listed has no catalogue
    std::vector<std::pair<std::string, std::vector<CatalogEntry>>> catalog;
    const std::vector<CatalogEntry>* Catalog(const std::string& intent) const {
        for (const auto& c : catalog)
            if (c.first == intent) return &c.second;
        return nullptr;
    }
};

// what an order acts on: the words said and the catalogue entry they name; empty: none
struct ItemInfo {
    std::string said, id;
};

// the world state the game hands over; false with a message on anything the rules cannot read
bool ValidateWorld(const WorldState& w, const LocationMatcher& places, std::string* error);

// one target of a place record resolved against the world
struct Grounding {
    std::string status;      // "resolved", "ambiguous", "missing"
    std::string entity;      // resolved: the entity (empty for a direction, "here" or a zone, which the planner takes as is)
    std::vector<std::string> candidates;   // the entities of its kind that fit, nearest first
    std::string via;         // how: "pin", "gaze", "memory", "zone", "direction", "here", "only", "nearest", "unknown_modifier", "distance", "this"
};

struct Prior {
    std::string label, condition;   // condition: "stance=crouch", "no_object=window", "no_tag=bomb", "bot_without=bomb", "player_up", "no_question"
    double x = 1;
};
const std::vector<Prior>& DefaultPriors();   // world.PRIORS

struct Memory {
    std::string last_entity, last_order;
    // the order taken last: what the next line may correct, repeat or give a new place to
    struct Frame {
        bool has = false;
        int intent = -1;
        bool has_target = false;   // the order had a place
        PlaceTarget target;
        Grounding ground;
        bool other = false, nearby = false;
        bool has_time = false;
        double time = 0;
        // what the place was called, when that is not `target`: the door of "smoke the door" when "there" answered the
        // bot's "Where?" (target is the "there"), "the other door" when that settled "Which door?" (target is "the door")
        bool has_said = false;
        PlaceTarget said;
        ItemInfo item;             // what the order acts on: a correction gives the same order with it
    } frame;
    bool has_question = false;
    struct Question {
        std::string kind;   // "which" (candidates offered one by one), "missing"
        int intent = -1;
        PlaceRecord record;
        int k = -1;         // the target the question is about
        bool other = false, queued = false;   // the order's "other" slot; it was given "on my go"
        std::vector<std::string> candidates;
        int offered = 0;    // the candidate last offered ("The one on the left, 8 m?")
        ItemInfo item;      // what the order asked about acts on
    } question;
};

struct Order {
    int intent = -1;
    std::string entity;                    // empty: none (a direction, a zone, a posture)
    std::vector<std::string> candidates;
    PlaceDirection direction = PlaceDirection::None;
    int zone = -1;
    // the object the line named (bot v56): with no entity, "go up by the stairs" still says the way is a staircase
    int object = -1;
    PlacePointer pointer = PlacePointer::None;
    bool other = false;
    std::string via;                       // how the place was found (Grounding::via); "here": where the speaker is
    bool nearby = false;                     // the line pointed with "this" / "here" and no far word ("hold this spot")
    // the farmer's and the builder's orders (an intent with an item): what it acts on -- the words said and the game's
    // catalogue entry, each empty when there is none
    bool has_item = false;
    std::string item, item_id;
};

struct PlannerResult {
    std::string action;   // the bot's action (ActionName), or "ask" / "resolved"
    std::string say;      // what the bot says: the planner's own words on "ask" / "resolved", else the chat's choice
    std::vector<Grounding> ground;   // every target of the line's places
    bool has_order = false;
    Order order;          // what the game gets to do
    int intent = -1;
    double prob = 0;
    bool adjusted = false;   // a prior held and lowered a probability
    Decision decision;    // the brain's decision this is built on
};

// text: the line, for "here" (without it a this-pointer is the crosshair, as for a queued order grounded again on the go).
// intent: the label of the order the line gives: "here" is the speaker's place for "come here" and the crosshair's
// point for "shoot here"
std::vector<Grounding> Ground(const PlaceRecord& record, const WorldState& world, const Memory& memory,
                              const LocationMatcher& places, std::string_view text = {}, std::string_view intent = {});
// "here" (the line says here and nothing far), "near" (this / these and nothing far), or empty
std::string Deixis(std::string_view text);
// a short line that starts with a place word: an answer to "Where?", not an order
bool Elliptical(std::string_view text);
// a grounding the game can act on: an entity, a direction, "here", or a floor that has places
bool Usable(const Grounding& g);
// (the row with the multipliers that hold, not renormalized; whether any held)
bool ApplyPriors(std::vector<double>* probs, const std::vector<std::string>& labels, const WorldState& world,
                 const Memory& memory, const std::vector<Prior>& priors);
std::string Describe(const WorldEntity& e);   // "on the left, 8 m"
// world.match_catalog: the id of the entry an item names (its words, plurals aside; else its last word; else, for one
// word, the first entry ending in it), or empty
std::string MatchCatalog(const std::string& item, const std::vector<CatalogEntry>& entries);

class Planner {
public:
    // the brain must be Init()ed; the planner keeps a pointer to it
    void Init(BotBrain* brain, std::vector<Prior> priors = DefaultPriors());
    bool SetWorld(const WorldState& world, std::string* error);
    const WorldState& World() const { return world_; }
    const Memory& Mem() const { return memory_; }
    // the chat took the line for something else than the planner did (coop_cli: "got any ammo?" is a question about the
    // bot, not a walk to the ammo the planner asked "Where?" about): the question it asked is no longer open. Not in
    // world.py: no planner step calls it
    void DropQuestion() { memory_.has_question = false; }
    const std::string& PendingEntity() const { return pending_entity_; }
    bool PendingHere() const { return pending_here_; }   // the queued order's place is "here"
    bool PendingNear() const { return pending_near_; }   // ... and it pointed with "this" / "here"
    void Reset();
    // continued: the line is a further order of the line the player just said (the decoder's order lines)
    PlannerResult Step(std::string_view text, const std::vector<float>& probs, bool continued = false);

private:
    Order MakeOrder(int intent, const PlaceRecord& record, const std::vector<Grounding>& grounding, int k, bool other, bool nearby = false,
                    const PlaceTarget* said = nullptr, const ItemInfo* item = nullptr);
    bool PlantsCrops() const;   // a bare "plant" is planting a crop: no bomb on the bot, seeds in its bag
    // what the order acts on; false with *refused set when the intent's catalogue lacks it
    bool ItemOf(std::string_view text, const std::string& intent, ItemInfo* item, std::string* refused) const;
    // a further order of the line being read: a place it names as the order before it did is that order's place
    void SamePlace(const PlaceRecord& record, std::vector<Grounding>* grounding) const;
    void Ask(int intent, const PlaceRecord& record, const std::vector<Grounding>& grounding, int k, bool other, bool queued,
             PlannerResult* out, const ItemInfo* item = nullptr);
    bool Answer(int intent, PlannerResult* out);
    // "the other one" in answer to "Which ...? The one ...?": not the one just offered. left: the candidates the line
    // still fits; said: how the line named the place ("the other door"), if it did. False: no other is left, the line
    // is something else
    bool OtherOne(std::vector<std::string> left, const PlaceTarget* said, PlannerResult* out);
    // said: how the line that settled the question named the place, when that is not how the order's own line did
    void Settle(const Memory::Question& q, const std::string& entity, const std::string& say, PlannerResult* out, const PlaceTarget* said = nullptr);
    // a "Where?" answered by pointing, or by "yes" / "go" once the place the order named is there
    bool PlaceAnswer(std::string_view text, const Decision& d, PlannerResult* out);
    void SettlePlace(const Memory::Question& q, const PlaceRecord& rec, const Grounding& g, bool queued, bool nearby, PlannerResult* out);
    void DropPending();
    const WorldEntity* Entity(const std::string& id) const;
    // ---- the short context
    const std::string& Label(int intent) const;
    bool Alive(const Memory::Frame& f) const;     // the previous order is still what the conversation is about
    bool Known(const Grounding& g) const;         // a grounding kept from an earlier line still points at something
    std::string Where(const PlaceTarget* t, const Grounding* g) const;
    std::string Echo(int intent, const PlaceTarget* t, const Grounding* g) const;   // "Open fire, on your pin."
    bool DefaultPlace(int intent, PlaceTarget* t, Grounding* g) const;              // the place of an order that names none
    void Reissue(const Memory::Frame& f, const PlaceTarget* t, const Grounding* g, bool nearby, const char* lead, PlannerResult* out);
    bool Context(std::string_view text, const Decision& d, PlannerResult* out);     // a correction, a repeat, a fragment

    BotBrain* brain_ = nullptr;
    std::vector<Prior> priors_;
    WorldState world_;
    Memory memory_;
    std::string pending_entity_;   // the queued order's resolved entity
    bool pending_here_ = false, pending_near_ = false;
    ItemInfo pending_item_;        // ... and what it acts on
    bool frame_in_line_ = false;   // the frame is of an order of the line being read (Step(..., continued))
};

}  // namespace coop
