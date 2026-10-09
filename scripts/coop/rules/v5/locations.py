"""
Where the order points: the map's named places (locations.json) found in a transcript.

The classifier picks the intent; this finds the places the planner resolves on the map:
    "hold the north door in the basement"            -> door / north / basement
    "i'll take the north door, you take the south"   -> door north (role mine), then door south: primary
    "take blue"                                      -> stairs / blue (inferred: only stairs are blue)
    "two on red stairs, hold the main door"          -> stairs red (role them), door main: primary
    "get to the roof"                                -> zone roof
It is a dictionary and position rules, not a model: the vocabulary is closed and the same on every
map, and a new callout must work the moment it is added to locations.json.

Everything is defined on the UTF-8 bytes of the line, so the C++ port is the same loop: a token is a
maximal run of ASCII letters and digits (A-Z lowercased), every other byte separates; between two
tokens a comma is a weak break (1) and . ; : ! ? a strong one (2). Offsets are byte offsets. Filler
words ("uh", "um") are dropped, and only the last MAX_TOKENS tokens are read (an order ends a ramble).

Rule sets (the word lists are in locations.json "words"):
  v1  frozen before any v3 test line existed (rules/v1): the only set with a blind number on the first
      v3 lines (88.0% exact).
  v2  after that run, from the r6 and cs authors' lines (rules/v2).
  v3  this file, after the review of v2: roles no longer fire on ordinary orders, "on second" is a
      floor only where it ends its phrase, zones and loose names do not attach across a clause, the
      unknown_modifier flag looks after the object too. Written after the first v3 lines had been
      seen; its blind number is on the second batch (blind/v3b, eval_v3b.py). Archived as rules/v3.
  v4  this file: rule set v3 plus directions (spec_v5.json), frozen before any v5 test line existed, after three
      critics had read the first draft (rules/critic_v4: their lines are tuning material). The places a line
      names are the ones rule set v3 finds, with these exceptions: a direction next to an object replaces the
      unknown_modifier flag ("the left window", "the door on the left", "the door in front of you"), and a
      place reported clear gets the role "status" also when the line's other target is a direction ("north
      door is clear, go left"). The primary may now be a direction. rules/v4 holds the frozen bytes; this file
      differs from them by one condition in step 6d (the frozen rules raised IndexError when a line asked for
      "the other one" and reported a direction clear: "not the north door, the other one, left is clear";
      found by the C++ port's generated lines, no study line is affected) and by one rule added AFTER the blind
      runs, from the owner's spoken test of 2026-10-09: "cover my front" is forward, as "watch my back" was back.
      Archived as rules/v4b.
  v5  this file: rule set v4 plus pointers (spec_v54.json), after the owner's test of bot v53: the game points at
      places with a 3D pin, and "Stay at my pin." gave the planner no place at all. A target gets a fifth field,
      "pointer": "pin" when the line names the player's marker, "this" when it points with this / that / here /
      there. The places and directions a line names are the ones rule set v4 finds, and so is the primary, with one
      exception: a pin that stands alone before every place the bot may act on is the primary ("go to my pin, then
      hold the north door"). A "this" that stands alone is a target but never takes the primary from a place or a
      direction ("hold here and watch the doors": the doors).
      Also new: jump / hop lead left, right, forward and back ("jump left"), as they led up and down.

  mentions    left to right, the longest vocabulary phrase at each token: object, qualifier, named
              place (object + qualifier in one phrase), zone, or an "ignore" phrase ("off the table").
              A zone's "words_end" phrase ("on second") counts only where it ends its phrase: at the
              end of the line, before punctuation or before a lone_follow word.
  before      an object takes the qualifier standing right before it (nothing, or one before_fill
              word, between; no punctuation). "north and south doors" makes two targets.
  other       an unqualified object right after an `other` word is flagged "other" ("take the other
              door"): the other one of its kind.
  unknown     the target is flagged "unknown_modifier" -- the player singled out one object in a way
              the map names cannot express, and the planner must not fall back to the nearest one --
              when: the object cannot carry the qualifier ("blue door"); two qualifiers stand side by
              side ("north west door"); an unknown_modifier word stands right before it ("back door",
              "first door"); exactly one word the vocabulary does not know stands between a determiner
              and an unqualified object ("the spiral staircase"; not a preposition, a number or an
              order verb: "a flash through window" is not flagged); or a post_prep word, an optional
              determiner and a post_modifier word follow an unqualified object ("the stairs at the
              back"). Since rule set v4 "left" / "right" in these places is the object's direction,
              not a flag ("the left window", "the left hand door", "the door on the left"; of "the
              left and right windows" the first one named).
  after       a qualifier still free attaches to the object before it when only after_fill words
              (at most 4, zone phrases skipped) stand between, without punctuation: "door on the north
              side". Across a comma only when a tail word follows it ("the stairs, blue ones"). A
              qualifier followed by a lone_block word or a zone phrase belongs to that phrase ("the
              door to the main hall"). If the object already has a qualifier, it is a second target
              of the same kind ("not the north door, the south one").
  lone        a qualifier no object took is a place only where it ends its phrase: at the end of the
              line, before punctuation, before a lone_follow word, or before a word that starts
              the next clause (a subject, a negator, a determiner, a number, an order verb: "take
              blue ill take red"). Before a lone_block word or a zone phrase ("yellow ping", "main
              hall") and after a lone_not_after word ("i'm red") it is nothing; before any other word
              it is a target flagged "unsure". Its object is the qualifier's "lone" object (blue ->
              stairs, main -> door); a compass word has none, so the target has only a qualifier (a
              direction) -- unless it points back at an object named before: "you take the south
              one", "i'll watch the east window, you watch the west" -> that kind of object.
  zone        a zone belongs to a target only inside its noun phrase: right before it ("basement
              door") or after it with only zone_after_fill words (at most 3) between, without
              punctuation. Across a comma only as shorthand, the zone an item of its own: "first
              floor, north window", "basement, the east door", "red stairs, top floor, two of them";
              not "get to the basement, the door is open". Any other zone is a target of its own.
  role        whose place it is. A place joined to the one before it by and / or shares its role
              ("they're on red and blue"). Else, looking back at most 5 words from a target
              (auxiliaries, determiners and particles not counted), not across punctuation, "you" or
              another target, and not past an order verb that starts the bot's own order
              ("im planting watch the white stairs"; a verb with its subject or negator right before
              it -- "i'll take", "i'm going to breach", "don't open", "they hold" -- hands the search
              to that subject or negator):
                not     a role_not word ("don't forget to", "don't let", "do not lose" excepted)
              (from / off / out of / leave count only right before the place, "back off to the
              basement" is a destination; and not after a negator: "dont leave the red stairs")
                from    leave / leaving; "from" or "off" after a from_lead word ("fall back from",
                        "get off") or when "to <another place>" follows ("from blue to red",
                        "from the roof rappel down to the east window"); "out of".
                        "cover me from the east window", "smoke off the main door": no role
                mine    i / i'm / i'll / i've, unless a report verb follows ("i said", "i need") or
                        it is a request ("can i get smoke on ..."); an -ing word that starts the
                        line or the clause ("pushing main", "i'm hit, falling back to the basement")
                them    a role_them word ("they", "enemy", "footsteps"). A role_them_soft word
                        ("guy", "someone", "stack") or a number, when what follows is what an enemy
                        does there: a form of "be", an -ing word or a motion_past word ("stack is
                        sitting on ...", "someone just ran up ...", "two of them pushing ..."), or a
                        number_next word where a callout starts -- the line or clause start, after
                        a lead word or after another place ("two on red", "got one at ...", "i hear
                        someone in ..."). "put one on the north door", "stack up on the north
                        door", "you guys on the main door", "no contact at ..." get no role.
                        "taking fire from the roof" is the enemy's place too
              "status" (a status_next word follows the target, and not "is yours" / "is all you") is
              given only when the line has another place to act on, or asks for "the other one":
              "north door is clear, hold the south window"; "east door's barricaded, blow it" has none.
  primary     the first target without a role. If every target has one, the first target: then the
              line gives no destination, and the role says why ("get off the roof": the place to
              leave).

  direction   (rule set v4) up / down / left / right / forward / back: the fourth field of a target, the
              direction the line gives the action. The six ids are fixed; their words are in locations.json
              "directions", and a word counts only in one of the contexts below (the dir_* word lists name
              the words) -- everywhere else it is an ordinary word. Terms: "prev" is the word right before
              in the same phrase (not a word of a place); the "lead" is prev, unless a dir_det word stands
              before it ("get your head down": a noun; dir_lead_noun words still lead: "all the way
              left"); a word "opens" when it starts the line or follows punctuation; it "stops" when the
              line, punctuation or a dir_end_next word follows; "ends its phrase" is the looser test of
              the lone qualifiers (a lone_follow word may follow).
                up, down      next to stairs: right before them ("up the blue stairs", "up blue", "up the
                              back stairs"; through a dir_stairs_prep word only when the word opens or
                              follows a climbing lead: "go down by stairs", not "put it down by the
                              stairs") or right after them ("take the stairs down", "blue stairs going
                              up"; not after a dir_split_verb: "lock the stairs down"). Before a floor
                              through a dir_zone_prep word: always with "to" / "into" / "onto" ("down to
                              the basement"), else only when the word opens, follows a climbing lead, or
                              is "up" after a dir_there_lead word that is no pronoun ("he's up on the
                              roof"; "one down in the basement" is a kill). Before "there" / "here" /
                              "top" / a ladder, hatch, ramp or rope when the word opens or follows a
                              dir_there_lead word ("get up there", "climb up the ladder"). At the end of
                              its phrase after a dir_lead_vertical word ("go up", "look down", "go back
                              up", "he went up there"). Never after a dir_vertical_block word ("lock
                              down", "set up", "hold up") or a split phrasal verb ("back me up here",
                              "set it up there"); "back up to <floor>" is a retreat unless a vertical
                              lead stands before "back"; the bare "up" never before a dir_up_block word
                              ("go up to him"). "above" / "below" unless a place or an amount follows
                              ("from above", "below us"; not "above the east window", "below half");
                              "upwards", "downwards" always.
                left, right   after a dir_lead_lateral word ("go left", "flank right", "contact left",
                              "he went left"); after a dir_prep word; after an `other` word ("the other
                              left"); before a dir_side word ("left side", "the left hallway"); after a
                              dir_det word that opens (or stands right after a place or another
                              direction), follows a dir_prep or lateral lead word, or where the phrase
                              ends ("on your left", "watch the right"); "take a left";
                              before "of" ("left of the stairs"); before a status word when it opens
                              ("left clear"); a "left" that is a phrase of its own ("Left!") -- never a
                              bare "right" ("Right, hold the north door"), except in a correction ("not
                              left, right!", "go left, no, right": the earlier one gets the role "not")
                              or after a count that opens the line ("two right").
                              Not "right" before a dir_right_noun word ("the right spot"), nor -- without
                              a determiner -- before a dir_right_block word ("right now", "right behind
                              you") or before "at" / "on" unless a dir_turn word leads and no pronoun
                              follows ("looking right at you", "go right at them"; "turn right at the
                              stairs" is a direction). Not "left" after a counted thing or a resource
                              someone has ("one enemy left", "no smoke left", "i got smoke left"; "two
                              steps left" and "throw a flash left" are directions), nor as a verb before
                              its object ("someone left the door open").
                forward       "forward" after a dir_lead_forward word or when it opens; "go straight"
                              (the phrase stops there); "ahead" after a dir_lead_ahead word or before
                              "of" + a person ("straight ahead", "up ahead", "ahead of us"; not "go
                              ahead", "go right ahead"); "in front", "up front", "to the front", "cover my
                              front" (a dir_six_verb word and a dir_det word before it, as for "watch my
                              back"), unless a place or "of the <thing>" follows ("in front of you"; not
                              "in front of the main door", "in front of the car", "the front room").
                back          "back" after a dir_lead_back word and not before a dir_back_block word
                              ("go back", "step back"; not "go back to the basement", "fall back", "back
                              up"); "at the back", "watch my back", "out back" where the phrase ends;
                              "back there"; never before a place ("the back door", "at the back of the
                              stairs"). "behind" before a dir_person word, or as the end of its phrase
                              when it opens or follows a dir_behind_lead word ("behind you", "from
                              behind", "Behind!"; not "behind the sofa", "stay behind", "we're behind").
                              "to the rear", "the rear" where the phrase ends; "backwards".
                clock         an hour before "o'clock" ("three o'clock" -> right, "nine" -> left, "twelve"
                              -> forward, "six" -> back: the "clock" lists); "your six", "check six", "one
                              at twelve"; another hour after a possessive only as "check your nine",
                              "contact on my three" ("breach on my three" is a countdown).
              Whose direction it is. It is the object's when written in its noun phrase or right after
              it: up / down next to stairs or before a floor; "above" / "below" / "behind you" / "in
              front (of you)" right after the place, also through "is" / "are" ("the window's above
              you"); left / right as in "the left window", "the door on the left", "the stairs are on
              your right". An object keeps the first direction it gets; the side that tells which object
              it is comes first ("go up the stairs on the left" = stairs + left). Any other direction is
              a target of its own with no object, qualifier or zone. It gets its role by the rules of the
              places ("i'll go left, you go right": left is mine; "they're on the stairs and the left":
              both theirs), never the role "from". Then, in this order:
                callout       a verbless direction that ends its sentence, with an order that names a
                              place after it, is a "status": "Behind you! Get to the stairs!"
                on the way    it joins the next place with the same role and no direction when only
                              prepositions, determiners, its own "side" / "me" and other places stand
                              between, without punctuation ("go left to the north door", "look up at the
                              east window", "come up from the basement to the first floor"); across one
                              comma only as a bare pointer ("on your right, the north door").
                afterthought  a direction that is a comma item of its own right after a place is that
                              place's ("north door, on the left"; "he's on the stairs, left side").
                status        a place or a direction reported clear ("left side is clear", "north door's
                              barricaded") gets the role "status" when the line has another target to
                              act on, before it or after punctuation.
              A direction that joined nothing stays a target: "flank left and hold the north door" = left
              (primary), then the door.
  pointer     (rule set v5) "pin" or "this": the fifth field of a target, set when the line points at its place.
              The words are in the pin_* and point_* lists.
                pin           the player's marker as a noun -- a pin_noun word after a pin_det word: "my pin", "the
                              ping", "that marker", "on my mark" (the owner: "mark" is the pin, not the go-signal).
                              Not the verbs ("pin them down", "mark the door"), not "pull the pin", not before a
                              form of "be" ("my ping is 200"), not after a pin_wait_verb and a pin_wait_prep word
                              ("wait for my mark": that one is a signal). Also a pin_past word with a
                              pin_past_lead word among the three words before it ("where i marked", "the spot i
                              just pinged"), and a pin_verb word with "where" among them ("where i mark").
                this          a point_det word (this / that / these / those) before a place ("that window") or
                              before a word the vocabulary does not know ("that room", "this wall"), unless a
                              point_not_prev word stands before it ("make sure that", "copy that"), a
                              point_not_next word follows ("that's", "that they"), it follows a place, a
                              person or a point_rel_prev word as a relative ("the door that leads ...",
                              "something that stops rounds"), or the word after it is a point_not_noun word
                              ("this round"). As a pronoun where the phrase ends or a point_pron_next word
                              follows, after an order verb, a preposition or a negator, or where it opens
                              ("check that", "not that one"; not "we can't win this one"). A point_loc word (here / there) after a place ("the stairs over
                              there"), after point_loc_lead words ("over there", "in here"; not "hang in there"),
                              after an order verb ("go there", "stay here") or as a phrase of its own; "here"
                              also wherever it ends its phrase, unless a point_here_not word stands before it ("i
                              need backup here"; not "almost here") -- never before a point_exist_next word or a
                              number ("there's two", "here they come").
                              "where" + a point_ing word within four words ("where i'm looking").
              Whose pointer it is. It is a place's when it stands in that place's noun phrase or right after
              it ("that north door", "the window by my ping", "the door i marked", "the stairs over there"), and
              a bare direction's when it follows it ("get up there"). A target keeps a pin over a this. Any other
              pointer is a target of its own with no object, qualifier, zone or direction. It gets its role by
              the rules of the places ("i'll hold here, you take the north door": here is mine); one that points
              at a person is the enemy's ("that guy"). Then it joins the next place with the same role and no
              pointer: a "this" when no punctuation, no order verb and at most six words stand between ("that
              room by the north door"), or across one comma as a bare pointer ("over there, the north door"); a
              pin only through prepositions and determiners ("my pin by the north door"). A pointer that joined
              nothing stays a target: "stay at my pin" = pin (primary); "go there and hold the north door" =
              there, then the door (primary).
  primary     the first target without a role that is a place, a direction or a pin, in line order; if the line has
              such targets and each has a role, the first of them (rule set v4: the role says why). Only a line with
              no place, direction or pin at all has a "this" on its own as its primary ("check that room").

normalized(text, "strip") is the line with attached qualifiers removed ("hold the north door" ->
"hold the door"), for measuring whether the classifier does better on it (eval_v3.py). Lone
qualifiers and zones are left alone: replacing them changed the meaning of orders ("push main" ->
"push the door" reads as OPEN; "go to the roof" -> "go to there" loses RAPPEL).

    python locations.py "hold the north door in the basement"
    python locations.py --dev          # the developer's regression lines (locations_dev.json)
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROLE_WINDOW = 5
ROLE_REACH = 12
ANAPHOR_MAX = 6
AFTER_MAX = 4
ZONE_AFTER_MAX = 3
GOVERN_MAX = 4
MAX_PHRASE_TOKENS = 4
MAX_TOKENS = 128
DIRECTIONS = ("up", "down", "left", "right", "forward", "back")
SECTIONS = ("version", "objects", "qualifiers", "named", "zones", "directions", "ignore", "words")
WORD_LISTS = ("before_fill", "after_fill", "tail", "zone_after_fill", "lone_follow",
              "lone_block", "lone_not_after", "unknown_modifier", "role_not", "role_from", "role_mine",
              "role_them", "number", "number_next", "status_next", "role_stop", "report_verb", "other",
              "determiner", "neutral_modifier",
              "role_them_soft", "soft_fill", "soft_lead", "number_fill", "motion_past", "role_from_of", "of_lead", "be", "not_ing", "role_from_after", "from_lead", "from_to", "ask", "number_lead",
              "status_not_next", "not_exempt", "not_unless_to", "govern", "aux", "order_verb", "from_particle",
              "filler", "anaphor", "let", "let_me", "negator", "fire", "no_words",
              "preposition", "post_prep", "post_modifier",
             "dir_adjective", "dir_adjective_tail", "dir_lead_lateral", "dir_prep", "dir_det", "dir_article",
              "dir_side", "dir_right_block", "dir_count", "dir_unit", "dir_always", "dir_relation",
              "dir_lead_vertical", "dir_vertical_block", "dir_up_block", "dir_stairs_prep", "dir_stairs_link",
              "dir_zone_prep", "dir_place_next", "dir_lead_forward", "dir_lead_ahead", "dir_front_lead",
              "dir_lead_back", "dir_back_block", "dir_back_next", "dir_back_prep", "dir_person", "dir_behind_lead",
              "dir_end_next", "dir_six_lead", "dir_six_verb", "dir_lead_climb", "dir_there_lead", "dir_right_soft",
              "dir_turn", "dir_split_object", "dir_split_verb", "dir_resource", "dir_have", "dir_amount",
              "dir_right_noun", "dir_lead_noun", "dir_throw", "dir_correction", "dir_straight_not", "dir_we",
              "pin_noun", "pin_det", "pin_block_prev", "pin_wait_verb", "pin_wait_prep", "pin_past", "pin_past_lead", "pin_past_fill",
              "pin_verb", "point_det", "point_not_prev", "point_not_next", "point_not_noun", "point_pron_next", "point_person", "point_rel_prev",
              "point_loc", "point_loc_lead", "point_here_not", "point_exist_next", "point_ing")
POINTERS = ("pin", "this")


def _is_token_byte(c):
    return 97 <= c <= 122 or 48 <= c <= 57


def tokenize(text):
    """[(word, start, end, brk)] over the UTF-8 bytes; brk is the punctuation between the previous
    token and this one: 0 none, 1 comma, 2 a sentence break (. ; : ! ?)."""
    b = text.encode("utf-8") if isinstance(text, str) else text
    out, i, n, brk = [], 0, len(b), 0
    while i < n:
        c = b[i] + 32 if 65 <= b[i] <= 90 else b[i]
        if _is_token_byte(c):
            j, word = i, []
            while j < n:
                d = b[j] + 32 if 65 <= b[j] <= 90 else b[j]
                if not _is_token_byte(d):
                    break
                word.append(d)
                j += 1
            out.append((bytes(word).decode("ascii"), i, j, brk if out else 0))
            i, brk = j, 0
        else:
            if c in b".;:!?":
                brk = 2
            elif c == 44 and brk < 2:
                brk = 1
            i += 1
    return out


def _phrase_ok(p):
    parts = p.split(" ")
    return bool(p) and all(x and all(_is_token_byte(ord(ch)) for ch in x) for x in parts) and len(parts) <= MAX_PHRASE_TOKENS


def validate(v):
    """Every reason this vocabulary must not be loaded (an empty list: it is fine)."""
    errs = []
    for k in v:
        if k not in SECTIONS and not k.startswith("_"):
            errs.append(f"unknown section {k!r}")
    for k in SECTIONS:
        if k not in v:
            errs.append(f"missing section {k!r}")
    if errs:
        return errs
    owner = {}

    def claim(phrase, who):
        if not isinstance(phrase, str) or not _phrase_ok(phrase):
            errs.append(f"{who}: phrase {phrase!r} must be 1-{MAX_PHRASE_TOKENS} lowercase ASCII tokens separated by single spaces")
        elif phrase in owner:
            errs.append(f"phrase {phrase!r} is in both {owner[phrase]} and {who}")
        else:
            owner[phrase] = who

    obj_ids, qual_ids = [o.get("id") for o in v["objects"]], [q.get("id") for q in v["qualifiers"]]
    for ids, what in ((obj_ids, "object"), (qual_ids, "qualifier"), ([z.get("id") for z in v["zones"]], "zone")):
        for i in set(ids):
            if ids.count(i) > 1:
                errs.append(f"duplicate {what} id {i!r}")
    allowed = {}
    for o in v["objects"]:
        if not o.get("words"):
            errs.append(f"object {o.get('id')!r} has no words")
        for w in o.get("words", []):
            claim(w, f"object {o.get('id')}")
        for q in o.get("qualifiers", []):
            if q not in qual_ids:
                errs.append(f"object {o.get('id')!r} allows unknown qualifier {q!r}")
        allowed[o.get("id")] = set(o.get("qualifiers", []))
    for q in v["qualifiers"]:
        for w in q.get("words", []):
            claim(w, f"qualifier {q.get('id')}")
        if not any(q.get("id") in a for a in allowed.values()):
            errs.append(f"qualifier {q.get('id')!r} is allowed by no object")
        if "lone" not in q:
            errs.append(f"qualifier {q.get('id')!r} needs an explicit \"lone\" (an object id or null)")
        elif q["lone"] is not None and q.get("id") not in allowed.get(q["lone"], ()):
            errs.append(f"qualifier {q.get('id')!r}: lone object {q['lone']!r} does not allow it")
    for t in v["named"]:
        claim(t.get("phrase"), "named")
        if t.get("qualifier") not in allowed.get(t.get("object"), ()):
            errs.append(f"named {t.get('phrase')!r}: {t.get('object')!r} does not allow {t.get('qualifier')!r}")
    for z in v["zones"]:
        if not z.get("words"):
            errs.append(f"zone {z.get('id')!r} has no words")
        for w in z.get("words", []):
            claim(w, f"zone {z.get('id')}")
        for w in z.get("words_end", []):
            claim(w, f"zone {z.get('id')} (words_end)")
    for p in v["ignore"]:
        claim(p, "ignore")
    seen = {}
    if not isinstance(v["directions"], list) or any(not isinstance(d, dict) for d in v["directions"]):
        errs.append('"directions" must be a list of {id, words, clock}')
    else:
        ids = [d.get("id") for d in v["directions"]]
        if sorted(map(str, ids)) != sorted(DIRECTIONS):     # the rules name the six
            errs.append(f"directions must be exactly {', '.join(DIRECTIONS)}: {ids}")
        fillers = v["words"].get("filler", []) if isinstance(v["words"], dict) else []
        for d in v["directions"]:
            for key in ("words", "clock"):
                if not isinstance(d.get(key), list):
                    errs.append(f"direction {d.get('id')!r} needs {key!r} (a list; \"clock\" may be empty)")
                    continue
                for w in d[key]:
                    if not isinstance(w, str) or not _phrase_ok(w) or " " in w:
                        errs.append(f"direction {d.get('id')!r}: {w!r} must be one lowercase ASCII token")
                    elif (key, w) in seen:
                        errs.append(f"direction word {w!r} is in both {seen[key, w]} and {d.get('id')}")
                    elif key == "words" and w in owner:
                        errs.append(f"direction word {w!r} is also the phrase of {owner[w]}")
                    elif w in fillers:
                        errs.append(f"direction word {w!r} is a filler word: it would never be read")
                    else:
                        seen[key, w] = d.get("id")
            if d.get("words") == []:
                errs.append(f"direction {d.get('id')!r} has no words")
        if isinstance(v["words"], dict):
            for w in v["words"].get("dir_adjective", []):
                if ("words", w) not in seen:
                    errs.append(f"dir_adjective word {w!r} is not a direction word")
    for o in v["objects"]:
        if not isinstance(o.get("vertical", False), bool):
            errs.append(f"object {o.get('id')!r}: \"vertical\" must be true or false")
    for k in WORD_LISTS:
        if k not in v["words"]:
            errs.append(f"missing word list {k!r}")
    for k, ws in v["words"].items():
        if k not in WORD_LISTS:
            errs.append(f"unknown word list {k!r}")
        for w in ws:
            if not _phrase_ok(w) or " " in w:
                errs.append(f"word list {k}: {w!r} must be one lowercase ASCII token")
    return errs


def _no_duplicate_keys(pairs):
    keys = [k for k, _ in pairs]
    for k in set(keys):
        if keys.count(k) > 1:
            raise ValueError(f"duplicate key {k!r} in the vocabulary file")
    return dict(pairs)


def load_vocab(path=None):
    v = json.load(io.open(path or os.path.join(HERE, "locations.json"), encoding="utf-8"),
                  object_pairs_hook=_no_duplicate_keys)
    errs = validate(v)
    if errs:
        raise ValueError("locations vocabulary refused:\n  " + "\n  ".join(errs))
    phrases = {}
    for o in v["objects"]:
        for w in o["words"]:
            phrases[tuple(w.split(" "))] = ("object", o["id"])
    for q in v["qualifiers"]:
        for w in q["words"]:
            phrases[tuple(w.split(" "))] = ("qualifier", q["id"])
    for t in v["named"]:
        phrases[tuple(t["phrase"].split(" "))] = ("named", (t["object"], t["qualifier"]))
    for z in v["zones"]:
        for w in z["words"]:
            phrases[tuple(w.split(" "))] = ("zone", z["id"])
        for w in z.get("words_end", []):
            phrases[tuple(w.split(" "))] = ("zone_end", z["id"])
    for p in v["ignore"]:
        phrases[tuple(p.split(" "))] = ("ignore", None)
    return {"phrases": phrases, "max_len": max(map(len, phrases)),
            "allowed": {o["id"]: set(o["qualifiers"]) for o in v["objects"]},
            "lone": {q["id"]: q["lone"] for q in v["qualifiers"]},
            "dirs": {w: d["id"] for d in v["directions"] for w in d["words"]},
            "clock": {w: d["id"] for d in v["directions"] for w in d["clock"]},
            "vertical": {o["id"] for o in v["objects"] if o.get("vertical")},
            "w": {k: set(ws) for k, ws in v["words"].items()}, "version": v["version"]}


VOCAB = load_vocab()


def _target(obj, qual, first, last, source, **more):
    t = {"object": obj, "qualifier": qual, "zone": None, "direction": None, "pointer": None, "role": None, "flag": None,
         "inferred": False, "first": first, "last": last, "obj": source, "cut": []}
    t.update(more)
    return t


def find(text, vocab=VOCAB):
    """-> {"targets": [...in line order...], "primary": index or -1, "target": the primary's
    {object, qualifier, zone, direction, pointer, role, flag} or None}. Token positions: "first" / "last"."""
    W = vocab["w"]
    toks, carry = [], 0
    for w, a, b, br in tokenize(text):
        if w in W["filler"]:              # "hold the north uh door": the recogniser's fillers are not words of the line
            carry = max(carry, br)
            continue
        toks.append((w, a, b, max(carry, br) if toks else 0))
        carry = 0
    toks = toks[-MAX_TOKENS:]             # the last ones: an order ends a ramble
    if toks:
        toks[0] = toks[0][:3] + (0,)
    words = [t[0] for t in toks]
    n = len(toks)

    def ends_phrase(j):      # token j does not continue the phrase before it
        return j >= n or toks[j][3] or words[j] in W["lone_follow"]

    mentions, i = [], 0
    while i < n:
        for k in range(min(vocab["max_len"], n - i), 0, -1):
            hit = vocab["phrases"].get(tuple(words[i:i + k]))
            # a phrase does not run across punctuation ("first, floor")
            if hit and not any(toks[j][3] for j in range(i + 1, i + k)):
                if hit[0] == "zone_end":
                    if not ends_phrase(i + k):
                        continue               # "on second thought", "to second door"
                    hit = ("zone", hit[1])
                if hit[0] != "ignore":
                    mentions.append({"kind": hit[0], "value": hit[1], "first": i, "last": i + k - 1,
                                     "start": toks[i][1], "end": toks[i + k - 1][2]})
                i += k
                break
        else:
            i += 1
    kind_at = {j: m["kind"] for m in mentions for j in range(m["first"], m["last"] + 1)}

    def brk(a, b):          # the strongest punctuation between token a and token b (a < b)
        return max((toks[j][3] for j in range(a + 1, b + 1)), default=0)

    def gap(a, b, skip=()):  # the words strictly between tokens a and b, without mentions of the kinds in skip
        return [words[j] for j in range(a + 1, b) if kind_at.get(j) not in skip]

    objects = [m for m in mentions if m["kind"] in ("object", "named")]
    quals = [m for m in mentions if m["kind"] == "qualifier"]
    zones = [m for m in mentions if m["kind"] == "zone"]
    targets = []
    for o in objects:
        obj, q = (o["value"], None) if o["kind"] == "object" else o["value"]
        targets.append(_target(obj, q, o["first"], o["last"], o))
    by_obj = {id(t["obj"]): t for t in targets}
    free = [True] * len(quals)

    # 1. the qualifier right before its object
    for t in list(targets):
        o = t["obj"]
        if t["qualifier"] is not None:
            continue
        best = None
        for k, q in enumerate(quals):
            if not free[k] or q["last"] >= o["first"]:
                continue
            g = gap(q["last"], o["first"])
            if len(g) <= 1 and set(g) <= W["before_fill"] and not brk(q["last"], o["first"]):
                if best is None or q["last"] > quals[best]["last"]:
                    best = k
        if best is None:
            continue
        q = quals[best]
        free[best] = False
        if q["value"] not in vocab["allowed"][t["object"]]:      # "blue door": not a place on these maps
            t["flag"], t["first"] = "unknown_modifier", q["first"]
            continue
        t["qualifier"], t["first"] = q["value"], q["first"]
        t["cut"].append((q["start"], o["start"]))
        # 1b. "north and south doors" (two targets) / "north west door" (not a place)
        for k2, q1 in enumerate(quals):
            if free[k2] and q1["last"] < q["first"] and q1["value"] in vocab["allowed"][t["object"]]:
                g = gap(q1["last"], q["first"])
                if g in (["and"], ["or"]) or (not g and brk(q1["last"], q["first"]) == 1):
                    free[k2] = False
                    targets.append(_target(t["object"], q1["value"], q1["first"], q1["last"], o, twin=t,
                                           cut=[(q1["start"], q["start"])]))
                elif not g and not brk(q1["last"], q["first"]):
                    free[k2] = False
                    t["flag"], t["first"] = "unknown_modifier", q1["first"]
    # 1c. a modifier word the vocabulary does not have, right before the object: "back door"
    dir_used = set()         # tokens already read as a direction or as an object's modifier (rule set v4)
    for t in targets:
        if "twin" not in t and t["first"] > 0 and words[t["first"] - 1] in W["unknown_modifier"] \
                and not toks[t["first"]][3] and kind_at.get(t["first"] - 1) is None:
            a = t["first"] - 1
            if words[a] in W["dir_adjective_tail"] and a > 0 and not toks[a][3] and words[a - 1] in W["dir_adjective"]:
                a -= 1                     # "the left hand door", "the right side window"
            if words[a] in W["dir_adjective"]:
                if a >= 2 and not toks[a][3] and not toks[a - 1][3] and words[a - 1] in ("and", "or") \
                        and words[a - 2] in W["dir_adjective"] and kind_at.get(a - 2) is None:
                    a -= 2                 # "the left and right windows": the first one named
                t["direction"] = vocab["dirs"][words[a]]      # "the left window": a direction, not an unknown name
                dir_used.update(range(a, t["first"]))
            else:
                t["flag"] = "unknown_modifier"
            t["np"] = a                    # where the object's noun phrase starts (step 6)

    # 1d. "the spiral staircase", "that broken window": one word the vocabulary does not know between
    # a determiner and an unqualified object singles out one object
    for t in targets:
        f = t["first"]
        if "twin" in t or t["flag"] or t["direction"] or t["qualifier"] is not None or f < 2:
            continue
        w = words[f - 1]
        if words[f - 2] in W["determiner"] and not toks[f - 1][3] and not toks[f][3] and kind_at.get(f - 1) is None \
                and not any(w in W[k] for k in ("neutral_modifier", "determiner", "preposition", "number", "order_verb")):
            t["flag"] = "unknown_modifier"
            t["np"] = f - 1

    # 1e. "take the other door": the object right after an `other` word is the other one of its kind
    for t in targets:
        f = t["first"]
        if "twin" not in t and t["flag"] is None and t["qualifier"] is None and f > 0 and not toks[f][3] \
                and words[f - 1] in W["other"]:
            t["flag"] = "other"
            t["np"] = f - 1

    # 2. a free qualifier after an object
    for k, q in enumerate(quals):
        if not free[k]:
            continue
        prev = [o for o in objects if o["last"] < q["first"]]
        if not prev:
            continue
        o = prev[-1]
        t = by_obj[id(o)]
        nxt = q["last"] + 1
        if nxt < n and not toks[nxt][3] and (words[nxt] in W["lone_block"] or kind_at.get(nxt) == "zone"):
            continue                       # "the door to the main hall": the name belongs to that phrase
        tail = nxt < n and words[nxt] in W["tail"] and not toks[nxt][3]
        b = brk(o["last"], q["first"])
        g = gap(o["last"], q["first"], skip=("zone",))
        if (q["value"] in vocab["allowed"][t["object"]] and len(g) <= AFTER_MAX and set(g) <= W["after_fill"]
                and (b == 0 or (b == 1 and tail))
                and not any(kind_at.get(j) == "qualifier" for j in range(o["last"] + 1, q["first"]))):
            free[k] = False
            last = q["last"] + (1 if tail else 0)
            zs = [z for z in zones if o["last"] < z["first"] < q["first"]]
            if t["qualifier"] is None:
                t["qualifier"], t["last"], t["after"] = q["value"], last, True
                t["cut"].append((zs[-1]["end"] if zs else o["end"], toks[last][2]))
            else:                          # "not the north door, the south one": a second door
                targets.append(_target(t["object"], q["value"], q["first"], last, o))
    # 2b. "doors and windows on the north side": coordinated objects share the qualifier after them
    for a, b in zip(objects, objects[1:]):
        ta, tb = by_obj[id(a)], by_obj[id(b)]
        if gap(a["last"], b["first"]) in (["and"], ["or"]) and ta["flag"] is None and ta["direction"] is None:
            ta["shares"] = tb
            if ta["qualifier"] is None and tb.get("after") and tb["qualifier"] in vocab["allowed"][ta["object"]]:
                ta["qualifier"] = tb["qualifier"]
    # 2c. "the door on the left", "the stairs at the back": a modifier after an unqualified object
    for o in objects:
        t = by_obj[id(o)]
        e = o["last"] + 1
        if t["flag"] or t["qualifier"] is not None or e >= n or toks[e][3] or words[e] not in W["post_prep"]:
            continue
        e += 1
        if e < n and not toks[e][3] and words[e] in W["determiner"]:
            e += 1
        if e < n and not toks[e][3] and words[e] in W["post_modifier"] and kind_at.get(e) is None \
                and not (words[e] == "front" and words[e - 1] == "in"):        # "the door in front ...": step 6
            if words[e] in W["dir_adjective"] and t["direction"] is None:
                t["direction"] = vocab["dirs"][words[e]]      # "the door on the left"
            else:
                t["flag"] = "unknown_modifier"
            dir_used.add(e)      # "the stairs at the back": the word is this object's, not a direction of its own

    # 3. lone qualifiers: a place only where the word ends its phrase
    for k, q in enumerate(quals):
        if not free[k]:
            continue
        if q["first"] > 0 and not toks[q["first"]][3] and words[q["first"] - 1] in W["lone_not_after"]:
            continue                       # "i'm red"
        nxt = q["last"] + 1
        flag = None
        if not ends_phrase(nxt):
            if words[nxt] in W["lone_block"] or kind_at.get(nxt) == "zone":
                continue                   # "yellow ping", "main hall"
            # a word that starts the next clause ends the phrase too: "take blue ill take red"
            if not any(words[nxt] in W[k] for k in ("role_mine", "role_not", "role_them", "govern", "determiner",
                                                    "number", "order_verb")):
                flag = "unsure"            # "the white fence": maybe a phrase the vocabulary does not know
        obj = vocab["lone"][q["value"]]
        # "you take the south one", "i'll watch the east window, you watch the west": the kind of the
        # object named before
        prev = [o for o in objects if o["last"] < q["first"] and q["value"] in vocab["allowed"][by_obj[id(o)]["object"]]]
        if prev:
            pt = by_obj[id(prev[-1])]
            one = nxt < n and not toks[nxt][3] and words[nxt] in W["anaphor"]
            bare = (obj is None and flag is None and ends_phrase(nxt) and q["first"] > 0
                    and words[q["first"] - 1] in W["determiner"] and not toks[q["first"]][3]
                    and pt["qualifier"] not in (None, q["value"]) and q["first"] - prev[-1]["last"] <= ANAPHOR_MAX)
            if one or bare:
                obj = pt["object"]
        last = q["last"] + (1 if nxt < n and words[nxt] in W["tail"] and not toks[nxt][3] else 0)
        targets.append(_target(obj, q["value"], q["first"], last, None, flag=flag, inferred=obj is not None))
    targets.sort(key=lambda t: t["first"])

    # 4. zones
    placed = []
    for z in zones:
        best = None
        for t in targets:
            if "zone_at" in t:
                continue
            if z["last"] < t["first"]:
                # "basement door"; across a comma only as shorthand, the zone an item of its own:
                # "first floor, north window", "basement, the east door, smoke it"
                g, b = gap(z["last"], t["first"]), brk(z["last"], t["first"])
                if (not g and not b) or (b == 1 and toks[z["last"] + 1][3] == 1 and (z["first"] == 0 or toks[z["first"]][3])
                                         and (not g or (len(g) == 1 and g[0] in W["determiner"]))):
                    best = best or t
            elif z["first"] > t["last"] or (t["obj"] is not None and t["obj"]["last"] < z["first"] <= t["last"]):
                a = t["obj"]["last"] if t["obj"] is not None and z["first"] <= t["last"] else t["last"]
                g = gap(a, z["first"])
                b = brk(a, z["first"])
                # across a comma only as shorthand, the zone an item of its own: "red stairs, top floor, ..."
                if (len(g) <= ZONE_AFTER_MAX and set(g) <= W["zone_after_fill"]
                        and (b == 0 or (b == 1 and not g and (z["last"] + 1 >= n or toks[z["last"] + 1][3])))
                        and not any(a < u["first"] < z["first"] for u in targets if u is not t)):
                    best = t
                    t["zone_after"] = True
        if best is not None:
            best["zone"], best["zone_at"] = z["value"], z["first"]
            if z["last"] < best["first"]:
                best["np"] = min(best.get("np", best["first"]), z["first"])       # "the basement stairs"
            elif z["first"] > best["last"]:
                best["np_last"] = z["last"]                                       # "the stairs in the basement"
            placed.append(z)
    for t in targets:
        if t.get("shares") is not None and t["zone"] is None and t["shares"].get("zone_after"):
            t["zone"] = t["shares"]["zone"]
        if t.get("twin") is not None and t["zone"] is None:
            t["zone"] = t["twin"]["zone"]
    for z in zones:
        if z not in placed:
            targets.append(_target(None, None, z["first"], z["last"], None, zone=z["value"]))
    targets.sort(key=lambda t: t["first"])

    # 5. roles: whose place it is
    owned = set()
    for t in targets:
        owned.update(range(t["first"], t["last"] + 1))

    def let_me(k):           # "let me take the north door": "me" is the subject
        return words[k] in W["let_me"] and k > 0 and not toks[k][3] and words[k - 1] in W["let"]

    def governor(j):         # the subject or negator right before the order verb at j (auxiliaries between), or -1
        k = j - 1
        for _ in range(GOVERN_MAX + 1):
            if k < 0 or toks[k + 1][3]:
                return -1
            if words[k] in W["role_not"] or words[k] in W["role_mine"] or words[k] in W["govern"] or let_me(k):
                return k
            if words[k] not in W["aux"]:
                return -1
            k -= 1
        return -1

    def ing(j):              # "camping", "sitting": a progressive form (by its ending; not_ing: "thing", "building")
        return j < n and len(words[j]) > 4 and words[j].endswith("ing") and words[j] not in W["not_ing"]

    def after(j, fill):      # the token after j and at most two filler words: "two of them | on", "guy just | went"
        k = j + 1
        for _ in range(2):
            if k < n and not toks[k][3] and words[k] in W[fill]:
                k += 1
        return k

    def acts(k):             # what an enemy does there: "is", "sitting", "went"
        return k < n and not toks[k][3] and (words[k] in W["be"] or ing(k) or words[k] in W["motion_past"])

    def starts(j, more=()):  # token j starts a callout: line or clause start, after a lead word or after another place
        return j == 0 or toks[j][3] or words[j - 1] in W["number_lead"] or j - 1 in owned or any(words[j - 1] in W[m] for m in more)

    def leads_to(t):         # "from blue to red", "from the roof rappel down to the east window"
        e = t["last"] + 1
        for skip in ("order_verb", "from_particle"):
            if e < n and not toks[e][3] and words[e] in W[skip] and kind_at.get(e) is None:
                e += 1
        if e >= n or toks[e][3] or words[e] not in W["from_to"]:
            return False
        e += 1
        if e < n and not toks[e][3] and words[e] in W["determiner"]:
            e += 1
        return e < n and not toks[e][3] and kind_at.get(e) is not None

    def negated(j):          # a negator right before token j: "dont leave", "don't move from"
        k = j - 2 if j >= 2 and words[j - 1] == "t" else j - 1
        return k >= 0 and not toks[j][3] and words[k] in W["negator"]

    def next_to(j, t):       # only determiners and neutral words between token j and the place
        return all(words[x] in W["determiner"] or words[x] in W["neutral_modifier"] for x in range(j + 1, t["first"]))

    def assign_role(ti, t, group):
        # "they're on red and blue": a place joined to the one before it by and / or shares its role
        if ti and group[ti - 1]["role"] in ("mine", "them", "not"):
            u = group[ti - 1]
            g = [words[x] for x in range(u["last"] + 1, t["first"])]
            if g and brk(u["last"], t["first"]) < 2 and any(x in ("and", "or") for x in g) \
                    and all(x in ("and", "or") or x in W["determiner"] for x in g):
                t["role"] = u["role"]
                return
        j, steps = t["first"] - 1, 0
        while j >= 0 and steps < ROLE_WINDOW and t["first"] - j <= ROLE_REACH:
            if toks[j + 1][3] or words[j] in W["role_stop"] or j in owned:
                break
            w = words[j]
            soft = False
            if w in W["role_them_soft"]:   # "stack is sitting on ...", "guy on ..."; not "stack up on the north door"
                k = after(j, "soft_fill")
                soft = k < t["first"] and (acts(k) or (words[k] in W["number_next"] and w not in W["order_verb"]
                                                       and starts(j, ("soft_lead", "number"))))
            # an order verb starts the bot's own order, unless it is a noun here ("a smoke", "the drone")
            if w in W["order_verb"] and not soft and not (j > 0 and not toks[j][3] and words[j - 1] in W["determiner"]):
                j = governor(j)
                if j < 0:
                    break                  # "im planting watch the white stairs": the bot's own order starts here
                w = words[j]               # "i'm going to breach the north door": straight to the subject
            if w in W["role_not"]:
                k = j + 2 if words[j + 1] == "t" else j + 1     # "don't" is two tokens
                if (w in W["not_unless_to"] and words[j + 1] == "to") or (k < n and words[k] in W["not_exempt"]):
                    break                  # "don't forget to smoke the north door", "do not lose the top floor"
                t["role"] = "not"
            elif w in W["role_from"]:
                if negated(j):
                    break                  # "dont leave the red stairs": stay there
                if next_to(j, t):
                    t["role"] = "from"
            elif w in W["role_from_after"]:
                lead = j - 2 if j >= 2 and not toks[j][3] and words[j - 1] in W["from_particle"] else j - 1
                if j > 0 and not toks[j][3] and words[j - 1] in W["fire"]:
                    t["role"] = "them"     # "taking fire from the roof"
                elif lead >= 0 and not toks[lead + 1][3] and words[lead] in W["from_lead"] and next_to(j, t):
                    if negated(lead):
                        break              # "don't move from the north window"
                    t["role"] = "from"     # "fall back from", "come down from"; not "back off to the basement"
                elif leads_to(t):
                    t["role"] = "from"     # else the bot's own position: "cover me from the east window"
            elif w in W["role_mine"] or let_me(j):
                k = j + 1
                while k < t["first"] and words[k] in W["aux"]:
                    k += 1
                if words[k] in W["report_verb"] or (j > 0 and not toks[j][3] and words[j - 1] in W["ask"]):
                    break                  # "I said the west door", "can i get smoke on the north door"
                t["role"] = "mine"
            elif w in W["role_from_of"]:
                if j > 0 and not toks[j][3] and words[j - 1] in W["of_lead"] and next_to(j, t):
                    t["role"] = "from"     # "get out of the basement"
            elif w in W["role_them"] or soft:
                if j > 0 and not toks[j][3] and words[j - 1] in W["no_words"]:
                    break                  # "no contact at the north door"
                t["role"] = "them"
            elif w in W["number"]:
                k = after(j, "number_fill")
                if k < t["first"] and (words[k] in W["number_next"] or acts(k)) and starts(j):
                    t["role"] = "them"     # "two on red", "got one at main"; not "put one on the north door"
            elif ing(j) and (j == 0 or toks[j][3]):
                t["role"] = "mine"         # "pushing main", "i'm hit, falling back to the basement": a report, not an order
            if t["role"]:
                break
            # auxiliaries, determiners and particles do not use up the window: "i'm falling back to the main door"
            steps += 0 if any(w in W[k] for k in ("aux", "determiner", "from_particle")) else 1
            j -= 1

    for ti, t in enumerate(targets):
        assign_role(ti, t, targets)

    # 5a. status: "north door is clear, hold the south window". Only when the line has another place to
    # act on (or asks for "the other one"): "east door's barricaded, blow it" names its own target
    def status_follows(t):
        e = t["last"] + 1
        if t["direction"] and e < n and not toks[e][3] and words[e] in W["post_prep"]:
            while e < n and not toks[e][3] and (e in dir_used or words[e] in W["post_prep"] or words[e] in W["determiner"]):
                e += 1                     # "the door on the right | is clear"
        if e >= n or toks[e][3] or words[e] not in W["status_next"]:
            return False
        return not (e + 1 < n and not toks[e + 1][3] and words[e + 1] in W["status_not_next"])

    def other_after(a):      # "... take the other one", "... you take the other"; not "on the other side"
        return any(words[j] in W["other"] and (j + 1 >= n or toks[j + 1][3] or words[j + 1] in W["anaphor"])
                   for j in range(a, n))

    cand = [t for t in targets if t["role"] is None and status_follows(t)]
    if cand and (any(t["role"] is None and not any(t is c for c in cand) for t in targets)
                 or other_after(targets[-1]["last"] + 1)):
        for t in cand:
            t["role"] = "status"

    # 5b. a correction reaches back: "smoke blue stairs, no wait, not blue, I meant white"
    for k, t in enumerate(targets):
        if t["role"] == "not" and t["qualifier"] is not None:
            for u in targets[:k]:
                if u["role"] is None and u["qualifier"] == t["qualifier"] and u["object"] in (t["object"], None):
                    u["role"] = "not"
    # 5c. "I've got the north door, you take the other one", "not the north door, the other one": no
    # named place is the bot's, and the line asks for the other one -> another object of that kind
    if targets and all(t["role"] for t in targets):
        t = targets[-1]
        if t["object"] is not None and other_after(t["last"] + 1):
            targets.append(_target(t["object"], None, n, n, None, flag="other"))

    # 6. directions (rule set v4): a direction word counts only in the contexts the module docstring lists
    D, CL = vocab["dirs"], vocab["clock"]
    np_first = lambda t: t.get("np", t["first"])         # noqa: E731  the object's noun phrase: "the back stairs",
    np_last = lambda t: t.get("np_last", t["last"])      # noqa: E731  "the basement stairs", "the stairs in the basement"
    first_of = {np_first(t): t for t in targets if t["first"] < n}
    last_of = {np_last(t): t for t in targets if t["last"] < n}
    np_tok = {j for t in targets if t["first"] < n for j in range(np_first(t), np_last(t) + 1)}

    def nb(j):               # token j exists and only spaces separate it from the token before
        return 0 < j < n and not toks[j][3]

    def plain(j):            # token j is a word of the line that belongs to no place and no direction
        return 0 <= j < n and kind_at.get(j) is None and j not in dir_used

    def place_at(j):         # a place starts at token j, after an optional determiner: "above the east window"
        if nb(j) and kind_at.get(j) is None and words[j] in W["determiner"]:
            j += 1
        return nb(j) and kind_at.get(j) is not None

    def floor(t):            # a floor on its own: "the basement", "the roof"
        return t["object"] is None and t["qualifier"] is None and t["zone"] is not None

    def place_after(j, preps):   # the place that starts at j, after one optional word of `preps` and one determiner
        if nb(j) and j not in first_of and words[j] in preps:
            j += 1
        if nb(j) and j not in first_of and words[j] in W["determiner"]:
            j += 1
        return first_of.get(j) if nb(j) else None

    def place_before(j):     # the place that ends right before token j, or before a form of "be" there: "the stairs are | on your right"
        if not nb(j):
            return None
        t = last_of.get(j - 1)
        if t is None and nb(j - 1) and kind_at.get(j - 1) is None and words[j - 1] in W["be"]:
            t = last_of.get(j - 2)
        return t

    lone = []
    for i in range(n):
        w = words[i]
        if (w not in D and w not in CL) or not plain(i) or i in owned:
            continue
        prev = words[i - 1] if nb(i) and plain(i - 1) else None              # the word before, in the same phrase
        prev2 = words[i - 2] if prev is not None and nb(i - 1) and plain(i - 2) else None
        prev3 = words[i - 3] if prev2 is not None and nb(i - 2) and plain(i - 3) else None
        nxt = words[i + 1] if nb(i + 1) else None
        nxt2 = words[i + 2] if nxt is not None and nb(i + 2) else None
        # "get your head down": a noun, not a verb (dir_lead_noun: "all the way left", "keep your eyes left")
        lead = None if prev2 in W["dir_det"] and prev not in W["dir_lead_noun"] else prev
        opens = i == 0 or toks[i][3] > 0                                     # the word starts the line or a phrase
        stop = i + 1 >= n or toks[i + 1][3] > 0 or nxt in W["dir_end_next"]  # the phrase ends here: "go straight, then ..."
        d, last, att, corrects = None, i, None, False
        if w in CL:
            c = CL[w]
            if nxt == "oclock":
                d, last = c, i + 1                        # "three oclock"
            elif nxt == "o" and nxt2 == "clock":
                d, last = c, i + 2                        # "three o'clock"
            elif c in ("back", "forward"):
                if (prev in W["dir_six_lead"] and ends_phrase(i + 1)) or (prev in W["dir_six_verb"] and stop):
                    d = c                                 # "on your six", "check six", "one at twelve"; not "my six kills"
            elif prev in W["dir_six_lead"] and stop                     and (prev2 is None or prev2 in W["dir_prep"] or prev2 in W["dir_six_verb"] or prev2 in W["dir_lead_lateral"])                     and not (prev == "my" and prev2 == "on" and prev3 not in W["role_them"] and prev3 not in W["role_them_soft"]
                             and prev3 not in W["number"]):
                d = c                                     # "check your nine", "contact on my three"; not "breach on my three" (a countdown), "i used my one"
        if d is None and w in D:
            k = D[w]
            if w in W["dir_always"]:
                d = k                                     # "upwards", "backwards"
            elif w in W["dir_relation"]:
                if not place_at(i + 1) and not (nxt is not None and (nxt.isdigit() or nxt in W["dir_amount"])):
                    d = k                                 # "from above", "below you"; not "above the east window", "below half"
                    att = place_before(i)                 # "the stairs below", "the window's above you"
            elif k in ("up", "down"):
                # "lock down the top floor", "set up on the roof"; "back me up here", "set it up there"
                blocked = prev in W["dir_vertical_block"] or (prev in W["dir_split_object"] and prev2 in W["dir_split_verb"])
                climb = lead in W["dir_lead_vertical"] or lead in W["dir_lead_climb"]
                t = None if blocked else place_after(i + 1, ())
                if t is None and not blocked and (opens or climb):
                    t = place_after(i + 1, W["dir_stairs_prep"])             # "go down by stairs"; not "put it down by the stairs"
                if t is not None and t["object"] in vocab["vertical"]:
                    d, att = k, t                         # "up the blue stairs", "up blue", "up the back stairs"
                if d is None:
                    t = last_of.get(i - 1) if nb(i) else None
                    if t is None and nb(i) and nb(i - 1) and kind_at.get(i - 1) is None and words[i - 1] in W["dir_stairs_link"]:
                        t = last_of.get(i - 2)
                    if t is not None and t["object"] in vocab["vertical"]:
                        j = np_first(t) - 1               # the verb before the stairs: "lock the stairs down", "hold blue down"
                        if j >= 0 and not toks[j + 1][3] and kind_at.get(j) is None and words[j] in W["determiner"]:
                            j -= 1
                        if not (j >= 0 and not toks[j + 1][3] and kind_at.get(j) is None and words[j] in W["dir_split_verb"]):
                            d, att = k, t                 # "take the stairs down", "blue stairs going up"
                if d is None and not blocked and not (k == "up" and prev == "back" and prev2 not in W["dir_lead_vertical"]):
                    t = place_after(i + 1, W["dir_zone_prep"])
                    # "down to the basement" always; "up on the roof" after a motion word or at the start of a phrase;
                    # "he's up on the roof" too, but "one down in the basement" is a kill; "back up to the basement" a retreat
                    if t is not None and floor(t) and (nxt in W["from_to"] or nxt == "onto" or opens or climb
                                                       or (k == "up" and prev in W["dir_there_lead"]
                                                           and prev not in W["dir_split_object"])):
                        d, att = k, t
                if d is None and not blocked and not (k == "up" and nxt in W["dir_up_block"]):
                    there = nxt2 if nxt in W["determiner"] and nxt2 in W["dir_place_next"] else nxt     # "up the ladder"
                    if there in W["dir_place_next"] and (opens or prev in W["dir_there_lead"]):
                        d = k                             # "get up there", "he's down there", "up top"
                    elif ends_phrase(i + 1) and (lead in W["dir_lead_vertical"]
                                                 or (prev == "back" and prev2 in W["dir_lead_vertical"])):
                        d = k                             # "go up", "go back up", "he went up there"; not "go down the hall", "go up to him"
            elif k in ("left", "right"):
                det, art = prev in W["dir_det"], prev in W["dir_article"]
                bare = opens and stop                     # a phrase of its own: "Left!"
                fix = bare and ((i >= 2 and words[i - 1] in W["dir_adjective"] and words[i - 1] != w
                                 and words[i - 2] in W["negator"])
                                or (i + 2 < n and words[i + 1] in W["negator"] and words[i + 2] in W["dir_adjective"]
                                    and words[i + 2] != w)
                                or (i >= 2 and words[i - 1] in W["dir_correction"]
                                    and any(x in W["dir_adjective"] and x != w for x in words[:i - 1])))
                if k == "right" and (nxt in W["dir_right_noun"]
                                     or (not det and not art
                                         and (nxt in W["dir_right_block"]
                                              or (nxt in W["dir_right_soft"]
                                                  and (lead not in W["dir_turn"] or nxt2 in W["dir_back_block"]
                                                       or nxt2 in W["dir_right_block"]))))):
                    pass          # "the right spot"; "right now", "looking right at you", "go right at them"; not "on your right now", "turn right at the stairs"
                elif k == "left" and nxt != "of" and not (nxt in W["dir_side"] and nxt not in W["anaphor"]) \
                        and ((prev2 in W["dir_count"] and prev not in W["dir_unit"]
                              and not (prev2 in W["dir_article"] and prev3 in W["dir_throw"]))
                             or (prev in W["dir_resource"] and prev2 in W["dir_have"])):
                    pass          # "one enemy left", "no smoke left", "i got smoke left"; not "two steps left", "throw a flash left"
                elif k == "left" and nxt in W["dir_det"] and (prev in W["role_them"] or prev in W["role_them_soft"]):
                    pass          # "someone left the door open", "enemy left the site"
                elif lead in W["dir_lead_lateral"] or prev in W["dir_prep"] or prev in W["other"] \
                        or (nxt in W["dir_side"] and not (k == "left" and (prev in W["role_mine"] or prev in W["govern"]
                                                                           or prev in W["role_stop"] or prev in W["dir_we"]))) \
                        or (det and (prev2 is None or prev2 in W["dir_prep"] or prev2 in W["dir_lead_lateral"]
                                     or ends_phrase(i + 1))) \
                        or (art and prev2 in W["dir_lead_lateral"]) \
                        or (nxt == "of" and prev not in W["dir_count"]) \
                        or (opens and nxt in W["status_next"]) \
                        or (bare and k == "left") or fix \
                        or (k == "right" and prev in W["number"] and prev2 is None and stop):
                    # "go left", "on your right", "the other left", "left side", "take a left", "left of the stairs",
                    # "left clear", "Left!" (never a bare "right": "Right, hold the north door"), "not left, right!",
                    # "go left, no, right", "two right"
                    d, corrects = k, fix
                    j = i - 2 if det else i - 1           # "the north door on the left": its preposition
                    if j >= 1 and nb(j + 1) and nb(j) and kind_at.get(j) is None and words[j] in W["post_prep"]:
                        att = place_before(j)             # also "the stairs are on your right"
            elif k == "forward":
                if w == "straight":
                    if lead in W["dir_lead_forward"] and lead not in W["dir_straight_not"] and stop:
                        d = k                             # "go straight"; not "go straight to the north door", "shoot straight"
                elif w == "ahead":
                    if (lead in W["dir_lead_ahead"] and not (prev == "right" and prev2 == "go")) \
                            or (nxt == "of" and nxt2 in W["dir_person"]):
                        d = k                             # "straight ahead", "up ahead", "ahead of us"; not "go ahead", "go right ahead"
                elif w == "front":
                    obj = last_of.get(i - 2) if prev == "in" and nb(i - 1) else None      # "the door in front ..."
                    if (prev in W["dir_front_lead"]
                            or (prev in W["dir_det"] and (prev2 in W["dir_prep"] or prev2 in W["dir_six_verb"]))) \
                            and not place_at(i + 2 if nxt == "of" else i + 1) \
                            and (prev not in W["dir_det"] or nxt == "of" or ends_phrase(i + 1)) \
                            and not (prev in W["dir_front_lead"] and nxt == "of" and nxt2 in W["determiner"]):
                        d, att = k, obj                   # "in front of you", "up front", "cover my front"; not "in front of the car", "the front room"
                    elif obj is not None and not obj["flag"] and obj["qualifier"] is None:
                        obj["flag"] = "unknown_modifier"  # "the door in front of the stairs": one particular door (as rule set v3)
                elif lead in W["dir_lead_forward"] or opens:
                    d = k                                 # "move forward", "forward!"
            elif w == "behind":
                if nxt in W["dir_person"]:
                    d, att = k, place_before(i)           # "behind you"; "the door behind you" is that door's
                elif stop and (opens or (prev in W["dir_behind_lead"] and not (prev == "re" and prev2 in W["dir_we"]))):
                    d = k                                 # "from behind", "Behind!"; not "behind the sofa", "stay behind", "we're behind"
            elif not place_at(i + 2 if nxt == "of" else i + 1):       # "back", "rear"; not "the back door", "at the back of the stairs"
                if w == "rear":
                    if prev in W["dir_prep"] or (prev in W["dir_det"] and (nxt == "of" or ends_phrase(i + 1))):
                        d = k                             # "to the rear"; not "the rear hallway"
                elif nxt in W["dir_back_next"] \
                        or (lead in W["dir_lead_back"] and nxt not in W["dir_back_block"]) \
                        or (prev in W["dir_det"] and (prev2 in W["dir_prep"] or prev2 in W["dir_six_verb"]
                                                      or prev2 in W["dir_back_prep"]) and (nxt == "of" or ends_phrase(i + 1))) \
                        or (prev in W["dir_back_prep"] and ends_phrase(i + 1)):
                    d = k                                 # "back there", "go back", "at the back", "out back"; not "the back room"
        if d is None:
            continue
        dir_used.update(range(i, last + 1))
        if att is None:
            lone.append(_target(None, None, i, last, None, direction=d, lone=True, corrects=corrects))
        elif att["direction"] is None:
            att["direction"] = d                          # an object keeps its first direction: "up the stairs on the left" = left
    for t in targets:                                     # "up the red or blue stairs": both
        u = t.get("twin")
        if u is not None and (t["direction"] is None) != (u["direction"] is None):
            t["direction"] = u["direction"] = t["direction"] or u["direction"]
    # the roles of the directions, by the rules of the places ("they're on the stairs and the left": both theirs);
    # a direction is never a place to leave ("come from the left")
    owned.update(j for t in lone for j in range(t["first"], t["last"] + 1))
    merged = sorted(targets + lone, key=lambda t: t["first"])
    for k, t in enumerate(merged):
        if "lone" in t:
            assign_role(k, t, merged)
            if t["role"] == "from":
                t["role"] = None
    for k, t in enumerate(lone):                          # "go left, no, right": the correction reaches back
        if t["corrects"] and t["role"] is None:
            for u in lone[:k]:
                if u["role"] is None and u["direction"] in ("left", "right") and u["direction"] != t["direction"]:
                    u["role"] = "not"

    def phrase_start(j):     # the first token of the phrase token j is in
        while j > 0 and not toks[j][3]:
            j -= 1
        return j

    def ordered(t):          # an order verb or a lateral lead stands before the direction in its phrase: "go left"
        return any(words[j] in W["order_verb"] or words[j] in W["dir_lead_lateral"] for j in range(phrase_start(t["first"]), t["first"]))

    # 6a. a verbless direction that ends its sentence is a callout when an order with a place follows:
    # "Behind you! Get to the stairs!"
    for t in lone:
        e = t["last"] + 1
        while e < n and not toks[e][3] and (words[e] in W["dir_side"] or words[e] in W["dir_person"]):
            e += 1
        if t["role"] is None and e < n and toks[e][3] == 2 and not ordered(t) \
                and any(u["role"] is None and e <= u["first"] < n for u in targets):
            t["role"] = "status"
    # 6b. a direction said on the way to a place is that place's: "go left to the north door", "look up at the east
    # window", "come up from the basement to the first floor". The place is the next one with the same role; only
    # prepositions, determiners, the direction's own "side" / "me" and other places stand between, and no
    # punctuation (a place with another role may stand between only when the direction has no role). Across one comma only as a bare pointer: "on your right,
    # the north door"
    for t in lone:
        for u in targets:
            if not t["last"] < u["first"] < n or (u["role"] != t["role"] and t["role"] is None):
                continue
            if u["direction"] is None and u["role"] == t["role"]:
                between = range(t["last"] + 1, np_first(u))
                breaks = [toks[j][3] for j in range(t["last"] + 1, u["first"] + 1) if toks[j][3]]
                on_the_way = not breaks and all(
                    j in np_tok or kind_at.get(j) is not None
                    or any(words[j] in W[x] for x in ("preposition", "determiner", "dir_side", "post_modifier", "dir_person"))
                    for j in between)             # "behind me at the north door", "the left side of the main door"
                pointer = breaks == [1] and not ordered(t) \
                    and all(words[j] in W["determiner"] or words[j] in W["dir_side"] or words[j] in W["dir_person"] for j in between)
                if on_the_way or pointer:
                    u["direction"], t["joined"] = t["direction"], True
            break
    # 6c. "north door, on the left", "he's on the stairs, left side": a direction that is a comma item of its own
    # right after a place is that place's
    for t in lone:
        if "joined" in t or t["role"] is not None:
            continue
        a, e = t["first"], t["last"] + 1
        for _ in range(2):                 # its own preposition and determiner: "on your left", "to the right"
            if a > 0 and not toks[a][3] and kind_at.get(a - 1) is None and (words[a - 1] in W["dir_prep"] or words[a - 1] in W["dir_det"]):
                a -= 1
        if e < n and not toks[e][3] and words[e] in W["dir_side"]:
            e += 1                         # "left side"
        u = last_of.get(a - 1) if a > 0 and toks[a][3] == 1 else None
        if u is not None and u["direction"] is None and u["role"] in (None, "them") and (e >= n or toks[e][3]):
            u["direction"], t["joined"] = t["direction"], True

    # 6d. status, with the directions: "left side is clear, push the main door", "north door is clear, go left" --
    # what is reported clear is not the order's target when the line has another one, before it or after punctuation
    def dir_status(t):       # "left side | is clear", "behind us | is clear"
        e = t["last"] + 1
        if e < n and not toks[e][3] and (words[e] in W["dir_side"] or words[e] in W["dir_person"]):
            e += 1
        return e < n and not toks[e][3] and words[e] in W["status_next"] \
            and not (e + 1 < n and not toks[e + 1][3] and words[e + 1] in W["status_not_next"])

    free = [t for t in lone if "joined" not in t and t["role"] is None]
    cand = [t for t in targets if t["role"] is None and status_follows(t)] + [t for t in free if dir_status(t)]
    acts_on = [t for t in free + [u for u in targets if u["role"] is None] if not any(t is c for c in cand)]
    for c in cand:              # o["first"] >= n: the "other one" the line asks for (5c) is a target to act on
        if any(o["first"] < c["first"] or o["first"] >= n or brk(c["last"], o["first"]) for o in acts_on):
            c["role"] = "status"
    targets = sorted(targets + [t for t in lone if "joined" not in t], key=lambda t: t["first"])

    # 7. pointers (rule set v5): the line points at its place -- the player's pin, or this / that / here / there
    in_np = {}               # token -> the target whose noun phrase, or direction, holds it
    for t in targets:
        if t["first"] < n:
            for j in range(np_first(t), np_last(t) + 1):
                in_np[j] = t

    def bare(j):             # a word of the line that belongs to no place and no direction
        return 0 <= j < n and j not in in_np and kind_at.get(j) is None and j not in dir_used

    def same(j):             # token j exists and continues the phrase of the token before it
        return 0 < j < n and not toks[j][3]

    def back_words(i, k):    # up to k words before token i in its phrase, the nearest first
        out, j = [], i
        while len(out) < k and same(j):
            j -= 1
            out.append(words[j])
        return out

    def place_ending(j):     # the place (not a bare direction) whose noun phrase ends at token j
        t = in_np.get(j)
        return t if t is not None and "lone" not in t and np_last(t) == j else None

    ptr = []
    for i in range(n):
        w = words[i]
        if not bare(i):
            continue
        prev = words[i - 1] if same(i) else None
        prev2 = words[i - 2] if prev is not None and same(i - 1) else None
        nxt = words[i + 1] if same(i + 1) else None
        kind, first, last, att, them = None, i, i, None, False
        if w in W["pin_verb"] and "where" in back_words(i, 3):
            b = back_words(i, 3)               # "where i mark", "where i ping": the verb, in the present
            kind, first = "pin", i - 1 - b.index("where")
        elif w in W["pin_noun"]:
            # the player's marker as a noun: "my pin", "the ping", "on my mark" -- not the verbs ("pin them down", "mark
            # the door"), the grenade's pin ("pull the pin") or the network's ("my ping is 200")
            b = back_words(i, 3)
            signal = len(b) == 3 and b[1] in W["pin_wait_prep"] and b[2] in W["pin_wait_verb"]     # "wait for my mark"
            if prev in W["pin_det"] and bare(i - 1) and prev2 not in W["pin_block_prev"] and nxt not in W["be"] and not signal:
                kind, first = "pin", i - 1
                a = first - 1                  # "the window by my ping": the place right before it
                if same(first) and bare(a) and words[a] in W["preposition"]:
                    a -= 1
                if same(a + 1):
                    att = place_ending(a)
        elif w in W["pin_past"]:
            # "where i marked", "the spot i just pinged", "the door i marked"
            if any(x in W["pin_past_lead"] for x in back_words(i, 3)):
                kind = "pin"
                a = i - 1
                while same(a + 1) and bare(a) and words[a] in W["pin_past_fill"]:
                    a -= 1
                if same(a + 1):
                    att = place_ending(a)
                first = a + 1                  # "where i marked": its "i" is not the player's own place
        elif w in W["point_ing"]:
            b = back_words(i, 4)
            if "where" in b:                   # "where i'm looking", "where i am pointing"
                kind, first = "this", i - 1 - b.index("where")
        elif w in W["point_det"]:
            u = in_np.get(i + 1) if same(i + 1) else None
            relative = w == "that" and same(i) and (in_np.get(i - 1) is not None or prev in W["role_them"]
                                                    or prev in W["role_them_soft"] or prev in W["point_rel_prev"])
            led = prev in W["order_verb"] or prev in W["preposition"] or prev in W["negator"] or i == 0 or toks[i][3] > 0
            if prev in W["point_not_prev"] or nxt in W["point_not_next"] or relative:
                pass                           # "make sure that ...", "that's a trap", "the door that leads ..."
            elif u is not None and "lone" not in u and np_first(u) == i + 1:
                kind, att = "this", u          # "that window", "this north door", "that back door"
            elif nxt is None or nxt in W["point_pron_next"]:
                # a pronoun: "check that", "smoke this one", "not that one"
                if led:
                    kind = "this"
                    if nxt in W["anaphor"]:
                        last = i + 1
            elif bare(i + 1) and nxt not in W["point_not_noun"]:
                kind = "this"                  # "that room", "this wall", "that guy"
                them = nxt in W["role_them"] or nxt in W["role_them_soft"] or nxt in W["point_person"]
        elif w in W["point_loc"]:
            if nxt in W["point_exist_next"] or nxt in W["number"]:
                continue                       # "there's two on the stairs", "here they come", "there you go"
            a = i - 1                          # the leads: "over there", "right in here", "back there"
            while same(a + 1) and i - a <= 2 and (bare(a) or a in dir_used) and words[a] in W["point_loc_lead"]:
                a -= 1
            leads = i - 1 - a
            u = in_np.get(i - 1) if same(i) else None
            if same(a + 1) and place_ending(a) is not None:
                kind, att = "this", place_ending(a)        # "the north door there", "the stairs over there"
            elif u is not None and "lone" in u:
                kind, att = "this", u                      # "get up there", "back there": the direction's
            elif leads and not (words[i - 1] == "in" and same(i - 1) and words[i - 2] == "hang"):
                kind = "this"                              # "over there", "in here", "from there"
            elif prev in W["order_verb"]:
                kind = "this"                              # "go there", "stay here", "smoke there"
            elif (i == 0 or toks[i][3] > 0) and (i + 1 >= n or toks[i + 1][3] > 0):
                kind = "this"                              # "There!", "here, the window"
            elif w == "here" and (i + 1 >= n or toks[i + 1][3] > 0) and prev not in W["point_here_not"]:
                kind = "this"                              # "i need backup here", "smoke here"
        if kind is None:
            continue
        if att is not None:
            if att["pointer"] != "pin":
                att["pointer"] = kind          # a target keeps a pin over a this
            continue
        ptr.append(_target(None, None, first, last, None, pointer=kind, ptr=True, them=them))
    if ptr:
        owned.update(j for t in ptr for j in range(t["first"], t["last"] + 1))
        merged = sorted(targets + ptr, key=lambda t: t["first"])
        for k, t in enumerate(merged):
            if "ptr" in t:
                assign_role(k, t, merged)
                if t["role"] is None and t["them"]:
                    t["role"] = "them"         # "that guy by the north door": where the enemy is
        # 7b. a pointer said on the way to a place is that place's: "that room by the north door", "over there, the
        # north door", "my pin by the north door"
        for t in ptr:
            u = next((x for x in targets if "lone" not in x and t["last"] < x["first"] < n), None)
            if u is None or u["role"] != t["role"] or u["pointer"] is not None:
                continue
            between = range(t["last"] + 1, np_first(u))
            breaks = [toks[j][3] for j in range(t["last"] + 1, u["first"] + 1) if toks[j][3]]
            links = all(words[j] in W["preposition"] or words[j] in W["determiner"] for j in between)
            if t["pointer"] == "pin":
                joins = not breaks and links
            else:
                joins = (not breaks and len(between) <= 6 and not any(words[j] in W["order_verb"] for j in between)) \
                    or (breaks == [1] and links and not ordered(t))
            if joins:
                u["pointer"], t["joined"] = t["pointer"], True
        targets = sorted(targets + [t for t in ptr if "joined" not in t], key=lambda t: t["first"])

    # a "this" with no place of its own never takes the primary from a place or a direction: only a pin does
    named = [k for k, t in enumerate(targets) if "ptr" not in t or t["pointer"] == "pin"]
    pool = named or list(range(len(targets)))
    primary = next((k for k in pool if targets[k]["role"] is None), pool[0] if pool else -1)
    keys = ("object", "qualifier", "zone", "direction", "pointer", "role", "flag")
    return {"targets": targets, "primary": primary,
            "target": {k: targets[primary][k] for k in keys} if primary >= 0 else None}


def record(text, vocab=VOCAB):
    """What the bot hands the planner: the targets in line order and which one is primary."""
    r = find(text, vocab)
    keys = ("object", "qualifier", "zone", "direction", "pointer", "role", "flag", "inferred")
    return {"primary": r["primary"], "targets": [{k: t[k] for k in keys} for t in r["targets"]]}


def normalized(text, mode, vocab=VOCAB):
    """mode "raw": the line itself. "strip": attached qualifiers removed; a line with nothing to
    remove comes back byte for byte."""
    if mode == "raw":
        return text
    assert mode == "strip", mode
    b = text.encode("utf-8")
    cuts = sorted(c for t in find(text, vocab)["targets"] for c in t["cut"])
    if not cuts:
        return text
    out, pos = bytearray(), 0
    for s, e in cuts:
        if s < pos:
            continue
        out += b[pos:s]
        pos = e
    out += b[pos:]
    res = bytearray()
    for c in out:                          # one space where a cut left two, none before a comma or at the ends
        if c == 32 and (not res or res[-1] == 32):
            continue
        if c == 44 and res and res[-1] == 32:
            res.pop()
        res.append(c)
    while res and res[-1] == 32:
        res.pop()
    return res.decode("utf-8")


def run_dev(path=None, show=True):
    """The developer's regression lines: {cat, text, accept: [[object, qualifier, zone] | null |
    "FLAG" | "ROLE"]}; a case may also fix the primary's "role" and "flag" (null: none). Tuning
    material, never a test set."""
    cases = json.load(io.open(path or os.path.join(HERE, "locations_dev.json"), encoding="utf-8"))["cases"]
    fails = {}
    for c in cases:
        t = find(c["text"])["target"]
        got = None if t is None or not (t["object"] or t["qualifier"] or t["zone"]) else [t["object"], t["qualifier"], t["zone"]]
        ok = got in [a for a in c["accept"] if not isinstance(a, str)] or \
            ("FLAG" in c["accept"] and t and t["flag"]) or ("ROLE" in c["accept"] and t and t["role"])
        for k in ("role", "flag", "direction", "pointer"):
            if k in c and (t[k] if t else None) != c[k]:
                ok = False
        if not ok:
            fails.setdefault(c["cat"], []).append((c["text"], got, t and t["role"], t and t["flag"], t and t["direction"], t and t["pointer"], c))
    n_fail = sum(map(len, fails.values()))
    if show:
        print(f"{len(cases)} dev lines, {n_fail} with a primary target the line's author would not accept")
        for cat, rows in fails.items():
            for text, got, role, flag, direction, pointer, c in rows:
                want = f"{c['accept']}" + "".join(f" {k}={c[k]}" for k in ("role", "flag", "direction", "pointer") if k in c)
                print(f"  [{cat}] {text!r}: got {got} role={role} flag={flag} direction={direction} pointer={pointer}, want {want}")
    return n_fail


if __name__ == "__main__":
    if "--dev" in sys.argv:
        sys.exit(1 if run_dev() else 0)
    for line in sys.argv[1:]:
        print(json.dumps({"text": line, **record(line), "strip": normalized(line, "strip")}))
