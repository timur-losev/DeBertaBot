"""
A time said with an order (round v68, the owner 2026-10-28: "когда я говорю подожди, сколько-то секунд, он должен
подождать именно столько секунд"; then "вообще понятия таймера для бота. Беги 10 секунд вперёд ... Прыгай 10 секунд").

    find("run forward for 10 seconds")  -> {"kind": "for", "seconds": 10.0, ...}, rest "run forward"
    find("in ten seconds, get to the door") -> {"kind": "after", "seconds": 10.0, ...}, rest "get to the door"

The line is English: the player's own, or the decoder's line for a Russian or Spanish one. The time never changes what
the order is, so the classifier, the router and the place matcher read `rest`, the line without it.

The owner's rules (scripts/coop/stt/chains2/ml_v68/TODO_v68.md, 1a G):
- "wait a minute", "hang on a sec", "just a moment", "in a minute": the idiom "hold on", no time (said without "for");
  "for a minute" and "one minute" are 60 s, "for a second" 1 s.
- "a couple of seconds" = 2 s; "a few seconds" / "several seconds" = a random time from 3 to 7 s (min and max); a range
  "10 to 15 seconds" / "10-15 seconds" = a random time within it.
- "5 more seconds" / "another 5 seconds" (more): added to a timed order still running, else 5 s.
- "in 10 seconds" / "after 10 seconds" / "10 seconds from now" / "count to ten": the order starts after the time (kind
  "after"); every other time is how long the order lasts (kind "for").
- The longest time is 60 s: a longer one is cut to 60 ("capped").
- "second" as an ordinal ("the second floor", "on second") is no time: only "N second(s)" or "a second".

The C++ twin is cpp/coop_intent/src/time_phrase.cpp; time_phrase_tests.jsonl (made by `python time_phrase.py --write`)
holds every case below with its answer, and `coop_cli --time-tests` checks the C++ against it.

    python time_phrase.py           the cases, checked
    python time_phrase.py --write   ... and the parity file
"""
import io, json, math, os, re, sys

MAX_SECONDS = 60.0
FEW = (3.0, 7.0)

UNITS = {"second": 1.0, "seconds": 1.0, "sec": 1.0, "secs": 1.0, "s": 1.0,
         "minute": 60.0, "minutes": 60.0, "min": 60.0, "mins": 60.0, "hour": 3600.0, "hours": 3600.0}
ONES = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
        "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
        "seventeen": 17, "eighteen": 18, "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
ABOUT = {"about", "around", "roughly", "approximately", "some", "maybe", "like", "almost", "nearly", "just", "only"}

TOKEN = re.compile(r"[a-z0-9]+(?:[.,][0-9]+)?")


def tokens(line):
    """(text, start, end) of each word or number of the lowercased line ("1.5" and "1,5" are one token)."""
    return [(m.group(0), m.start(), m.end()) for m in TOKEN.finditer(line.lower())]


def number(toks, i):
    """A number at toks[i]: (value, next index), or None. Digits ("10", "1.5", "5s" is read by unit()), words
    ("twenty five", "one and a half", "two and a half")."""
    if i >= len(toks):
        return None
    t = toks[i][0]
    if re.fullmatch(r"[0-9]+(?:[.,][0-9]+)?", t):
        v, j = float(t.replace(",", ".")), i + 1
    elif t in TENS:
        v, j = float(TENS[t]), i + 1
        if j < len(toks) and toks[j][0] in ONES and 0 < ONES[toks[j][0]] < 10:
            v, j = v + ONES[toks[j][0]], j + 1
    elif t in ONES:
        v, j = float(ONES[t]), i + 1
    else:
        return None
    # "one and a half", "two and a half"
    if j + 2 < len(toks) and [x[0] for x in toks[j:j + 3]] == ["and", "a", "half"]:
        v, j = v + 0.5, j + 3
    return v, j


def unit(toks, i):
    """A unit at toks[i]: (seconds per unit, next index), or None."""
    if i < len(toks) and toks[i][0] in UNITS:
        return UNITS[toks[i][0]], i + 1
    return None


def amount(toks, i):
    """A time at toks[i] without its lead word: (dict, next index, more) or None. dict: {"seconds"} or {"min", "max"};
    more: "N more seconds" / "another N seconds"."""
    j, more = i, False
    if j < len(toks) and toks[j][0] == "another":
        more, j = True, j + 1
    while j < len(toks) and toks[j][0] in ABOUT:
        j += 1
    w = [x[0] for x in toks[j:j + 4]]
    # between 5 and 10 seconds (the blind test of 2026-10-29: read as 10 s before)
    if w[:1] == ["between"]:
        lo = number(toks, j + 1)
        if lo and lo[1] < len(toks) and toks[lo[1]][0] == "and":
            hi = number(toks, lo[1] + 1)
            u = unit(toks, hi[1]) if hi else None
            if hi and u and hi[0] > lo[0]:
                return {"min": lo[0] * u[0], "max": hi[0] * u[0]}, u[1], more
    # half a minute, a half minute, half minute, half of a minute
    for words, value in ((["half", "a", "minute"], 30.0), (["a", "half", "minute"], 30.0), (["half", "of", "a", "minute"], 30.0),
                         (["half", "minute"], 30.0)):
        if w[:len(words)] == words:
            return {"seconds": value}, j + len(words), more
    # a minute and a half, a second and a half (the blind test: "a second and a half" was 1 s)
    if len(w) >= 2 and w[0] in ("a", "one") and w[1] in ("minute", "second", "sec") and             [x[0] for x in toks[j + 2:j + 5]] == ["and", "a", "half"]:
        return {"seconds": 1.5 * UNITS[w[1]]}, j + 5, more
    # a couple of seconds, couple seconds, a couple more seconds
    k = j + (1 if w[:1] == ["a"] else 0)
    if k < len(toks) and toks[k][0] == "couple":
        k += 1 + (1 if k + 1 < len(toks) and toks[k + 1][0] == "of" else 0)
        if k < len(toks) and toks[k][0] in ("more", "extra"):
            more, k = True, k + 1
        u = unit(toks, k)
        if u:
            return {"seconds": 2.0 * u[0]}, u[1], more
    # a few seconds, few seconds, several seconds, a few more seconds (decoder v68s wrote it, 2026-10-29)
    k = j + (1 if w[:1] == ["a"] else 0)
    if k < len(toks) and toks[k][0] in ("few", "several"):
        k += 1
        if k < len(toks) and toks[k][0] in ("more", "extra"):
            more, k = True, k + 1
        u = unit(toks, k)
        if u and u[0] == 1.0:
            return {"min": FEW[0], "max": FEW[1]}, u[1], more
    # a second, a minute ("for a minute"; without "for" the idiom, find() skips it)
    if j < len(toks) and toks[j][0] in ("a", "an"):
        u = unit(toks, j + 1)
        if u and toks[j + 1][0] in ("second", "sec", "minute", "min", "hour"):
            return {"seconds": u[0]}, u[1], more
    # 5s, 10sec
    if j < len(toks):
        m = re.fullmatch(r"([0-9]+)(s|sec|secs)", toks[j][0])
        if m:
            return {"seconds": float(m.group(1))}, j + 1, more
    n = number(toks, j)
    if not n:
        return None
    v, k = n
    # a range: 10 to 15 seconds, 10 or 15 seconds, 10-15 seconds (two numbers in a row), between 10 and 15
    hi = None
    if k < len(toks) and toks[k][0] in ("to", "or"):
        hi = number(toks, k + 1)
    elif k < len(toks):
        hi = number(toks, k)
        if hi and hi[0] <= v:
            hi = None
    if hi and hi[0] > v and unit(toks, hi[1]):
        u = unit(toks, hi[1])
        return {"min": v * u[0], "max": hi[0] * u[0]}, u[1], more
    # N more seconds, N extra seconds
    if k < len(toks) and toks[k][0] in ("more", "extra"):
        more, k = True, k + 1
    u = unit(toks, k)
    if not u:
        return None
    seconds, end = v * u[0], u[1]
    # 1 minute 30 seconds, a minute and 20 seconds
    if u[0] > 1.0:
        k = end + (1 if end < len(toks) and toks[end][0] == "and" else 0)
        n = number(toks, k)
        if n and unit(toks, n[1]) and unit(toks, n[1])[0] == 1.0:
            seconds, end = seconds + n[0], unit(toks, n[1])[1]
    return {"seconds": seconds}, end, more


def find(line):
    """The time the line says: (time, rest) where time is {"kind", "seconds" | "min" + "max", "more", "capped", "said"}
    and rest the line without the words of the time; (None, line) when it says none."""
    toks = tokens(line)
    for i in range(len(toks)):
        t = toks[i][0]
        # count to ten
        if t == "count" and i + 1 < len(toks):
            j = i + 1 + (1 if toks[i + 1][0] == "to" else 0)
            n = number(toks, j)
            if n:
                return finish(line, toks, i, n[1], "after", {"seconds": n[0]}, False, rest_if_empty="wait")
        lead = t if t in ("for", "in", "after", "within") else None
        start = i
        # "give me 5 seconds", "gimme a minute": a wait (the rest would read as "give me")
        give = 0
        if t in ("give", "gimme") and not lead:
            give = 2 if t == "give" and i + 1 < len(toks) and toks[i + 1][0] == "me" else 1
            if t == "give" and give == 1:
                continue
        j = i + (1 if lead else give)
        if lead and j < len(toks) and [x[0] for x in toks[j:j + 2]] == ["the", "next"]:
            j += 2
        if lead == "within":
            lead = "for"
        a = amount(toks, j)
        if not a:
            continue
        time, end, more = a
        # "a second" / "a minute" / "a moment" with no "for": the idiom, no time ("wait a minute", "in a sec", "just a sec")
        k = j
        while k < len(toks) and toks[k][0] in ("just", "only"):
            k += 1
        if k < len(toks) and toks[k][0] == "a" and end - k == 2 and lead != "for":
            continue
        # "for 10 seconds more", "for half a minute more"
        if not more and end < len(toks) and toks[end][0] in ("more", "extra"):
            more, end = True, end + 1
        if give:
            return finish(line, toks, start, end, "for", time, more, rest_if_empty="wait", rest_instead="wait")
        kind = "after" if lead in ("in", "after") else "for"
        # 10 seconds from now, 10 seconds later
        if end < len(toks) and [x[0] for x in toks[end:end + 2]] == ["from", "now"]:
            kind, end = "after", end + 2
        elif end < len(toks) and toks[end][0] == "later":
            kind, end = "after", end + 1
        # or so
        if end + 1 < len(toks) and [x[0] for x in toks[end:end + 2]] == ["or", "so"]:
            end += 2
        return finish(line, toks, start, end, kind, time, more)
    return None, line


def finish(line, toks, start, end, kind, time, more, rest_if_empty="wait", rest_instead=None):
    out = {"kind": kind, "more": more, "capped": False}
    for key in ("seconds", "min", "max"):
        if key in time:
            v = math.floor(float(time[key]) * 10.0 + 0.5) / 10.0   # tenths, rounded the same way in the C++ twin
            if v > MAX_SECONDS:
                v, out["capped"] = MAX_SECONDS, True
            out[key] = v
    if "min" in out and out["min"] >= out["max"]:
        out["seconds"] = out.pop("max")   # "2 to 3 minutes": both cut to 60 s
        del out["min"]
    if out.get("seconds", 1.0) <= 0.0:
        return None, line
    a, b = toks[start][1], toks[end - 1][2]
    out["said"] = line[a:b]
    rest = (line[:a] + " " + line[b:]).strip()
    rest = re.sub(r"\s+([,.!?;:])", r"\1", re.sub(r"\s+", " ", rest))
    rest = re.sub(r"^[,.;:\s]+", "", rest)
    rest = re.sub(r",\s*([.!?]?)$", r"\1", rest).strip()
    if rest_instead:
        rest = (rest_instead + " " + rest).strip()
    if not re.search(r"[A-Za-z]", rest):
        rest = rest_if_empty   # a line that is only a time ("five seconds", the answer to "how long?"): a wait
    return out, rest


# ---- the cases (the C++ twin is checked against the same) ------------------------------------------------------------
CASES = [
    # line, kind, seconds or (min, max), more, rest
    ("wait 5 seconds", "for", 5, False, "wait"),
    ("wait five seconds", "for", 5, False, "wait"),
    ("Wait 5 seconds.", "for", 5, False, "Wait."),
    ("wait for 10 seconds", "for", 10, False, "wait"),
    ("hold here for 10 seconds", "for", 10, False, "hold here"),
    ("Stand here for twenty seconds.", "for", 20, False, "Stand here."),
    ("cover me for 30 seconds", "for", 30, False, "cover me"),
    ("run forward for 10 seconds", "for", 10, False, "run forward"),
    ("jump for ten seconds", "for", 10, False, "jump"),
    ("Crouch for ten seconds.", "for", 10, False, "Crouch."),
    ("Shoot there for five seconds.", "for", 5, False, "Shoot there."),
    ("follow me for a minute", "for", 60, False, "follow me"),
    ("follow me for one minute", "for", 60, False, "follow me"),
    ("wait one minute", "for", 60, False, "wait"),
    ("wait 2 minutes", "for", 60, False, "wait"),
    ("wait for 90 seconds", "for", 60, False, "wait"),
    ("wait 1.5 seconds", "for", 1.5, False, "wait"),
    ("wait one and a half seconds", "for", 1.5, False, "wait"),
    ("wait twenty five seconds", "for", 25, False, "wait"),
    ("wait twenty-five seconds", "for", 25, False, "wait"),
    ("wait 5s", "for", 5, False, "wait"),
    ("wait 5 sec", "for", 5, False, "wait"),
    ("wait 5 secs", "for", 5, False, "wait"),
    ("wait half a minute", "for", 30, False, "wait"),
    ("Wait a half minute.", "for", 30, False, "Wait."),
    ("wait for half a minute, then go to the door", "for", 30, False, "wait, then go to the door"),
    ("wait a couple of seconds", "for", 2, False, "wait"),
    ("wait a couple seconds", "for", 2, False, "wait"),
    ("wait a few seconds", "for", (3, 7), False, "wait"),
    ("wait several seconds", "for", (3, 7), False, "wait"),
    ("wait 10 to 15 seconds", "for", (10, 15), False, "wait"),
    ("wait 10-15 seconds", "for", (10, 15), False, "wait"),
    ("wait 10 or 15 seconds", "for", (10, 15), False, "wait"),
    ("wait about twenty seconds", "for", 20, False, "wait"),
    ("wait 10 seconds or so", "for", 10, False, "wait"),
    ("wait 5 more seconds", "for", 5, True, "wait"),
    ("wait another 5 seconds", "for", 5, True, "wait"),
    ("hold for another ten seconds", "for", 10, True, "hold"),
    ("look at me for a second", "for", 1, False, "look at me"),
    ("in ten seconds, get to the door", "after", 10, False, "get to the door"),
    ("In ten seconds, get to the door.", "after", 10, False, "get to the door."),
    ("in 10 seconds go to the door", "after", 10, False, "go to the door"),
    ("go to the door in 10 seconds", "after", 10, False, "go to the door"),
    ("after five seconds follow me", "after", 5, False, "follow me"),
    ("go to the door 10 seconds from now", "after", 10, False, "go to the door"),
    ("count to ten", "after", 10, False, "wait"),
    ("hold the angle for the next 20 seconds", "for", 20, False, "hold the angle"),
    ("Hop around here for five seconds.", "for", 5, False, "Hop around here."),
    ("give me 5 seconds", "for", 5, False, "wait"),
    ("gimme a minute", None, None, False, "gimme a minute"),
    ("give me a minute", None, None, False, "give me a minute"),
    ("five seconds", "for", 5, False, "wait"),
    ("Half a minute.", "for", 30, False, "wait"),
    ("wait an hour", "for", 60, False, "wait"),
    ("Stop for 3 seconds.", "for", 3, False, "Stop."),
    ("Wait five more seconds.", "for", 5, True, "Wait."),
    ("jump down 10 seconds", "for", 10, False, "jump down"),
    ("wait 1 minute 30 seconds", "for", 60, False, "wait"),
    ("wait 0 minutes and 40 seconds", "for", 40, False, "wait"),
    ("wait 2 to 3 minutes", "for", 60, False, "wait"),
    ("hold the door for twenty seconds", "for", 20, False, "hold the door"),
    ("stay on second for a minute", "for", 60, False, "stay on second"),
    ("for ten seconds hold this angle", "for", 10, False, "hold this angle"),
    ("wait between 5 and 10 seconds", "for", (5, 10), False, "wait"),
    ("hold here for between 10 and 20 seconds", "for", (10, 20), False, "hold here"),
    ("wait like a second and a half", "for", 1.5, False, "wait"),
    ("wait a minute and a half", "for", 60, False, "wait"),
    ("stay between the doors", None, None, False, "stay between the doors"),
    # decoder v68s's lines (2026-10-29): "a few more seconds", "half a minute more"
    ("go prone for a few more seconds", "for", (3, 7), True, "go prone"),
    ("lie down for a couple more seconds", "for", 2, True, "lie down"),
    ("watch the window for half a minute more", "for", 30, True, "watch the window"),
    ("cover me for 10 seconds more", "for", 10, True, "cover me"),
    ("wait a few seconds more", "for", (3, 7), True, "wait"),
    ("hold for just a second", "for", 1, False, "hold"),
    # no time
    ("wait a minute", None, None, False, "wait a minute"),
    ("wait a sec", None, None, False, "wait a sec"),
    ("hang on a second", None, None, False, "hang on a second"),
    ("just a moment", None, None, False, "just a moment"),
    ("just a sec", None, None, False, "just a sec"),
    ("wait just a minute", None, None, False, "wait just a minute"),
    ("I'll be there in a minute", None, None, False, "I'll be there in a minute"),
    ("go to the second floor", None, None, False, "go to the second floor"),
    ("stay on second", None, None, False, "stay on second"),
    ("hold the second door", None, None, False, "hold the second door"),
    ("two on red", None, None, False, "two on red"),
    ("on three, breach", None, None, False, "on three, breach"),
    ("wait for my go", None, None, False, "wait for my go"),
    ("wait", None, None, False, "wait"),
    ("wait 0 seconds", None, None, False, "wait 0 seconds"),
    ("collect five wood", None, None, False, "collect five wood"),
]


def check(write=False):
    bad = 0
    rows = []
    for line, kind, value, more, rest in CASES:
        got, got_rest = find(line)
        want = None
        if kind:
            want = {"kind": kind, "more": more}
            if isinstance(value, tuple):
                want["min"], want["max"] = float(value[0]), float(value[1])
            else:
                want["seconds"] = float(min(value, MAX_SECONDS))
        have = None if got is None else {k: got[k] for k in ("kind", "more", "seconds", "min", "max") if k in got}
        ok = have == want and got_rest == rest
        if not ok:
            bad += 1
            print("  NO  %-48s want %s %r, got %s %r" % (line, want, rest, have, got_rest))
        rows.append({"line": line, "time": got, "rest": got_rest})
    print("time phrases: %d of %d right" % (len(CASES) - bad, len(CASES)))
    if write:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "time_phrase_tests.jsonl")
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        print("wrote", path)
    return bad


if __name__ == "__main__":
    sys.exit(1 if check("--write" in sys.argv) else 0)
