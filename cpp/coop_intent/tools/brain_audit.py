"""What the bot's brain makes of the lines that need no named place, in the worlds a map nobody has marked gives it.
   python brain_audit.py [--exe PATH] [--bot DIR] [--out FILE]
Starts coop_cli --serve --no-stt and sends every line with a world: GAZE (the crosshair is on something 12 m ahead),
PIN (that, and the player's pin 15 m to the right), SKY (the crosshair is on nothing, no pin). Every line starts from
a reset brain unless it is a step of a dialogue ("a > b"). Prints per line the intent, the action, the places, the
grounding, the order the game would get and the bot's words; --out also writes them as JSON. A reading aid, not a
test: nothing is asserted. The findings of 2026-10-10 are in COOP-BOT.md, "A map nobody has marked"."""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.normpath(os.path.join(HERE, "..", "build", "Release", "coop_cli.exe"))
BOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v54", "cpp"))
OUT = None
a = sys.argv[1:]
while a:
    k = a.pop(0)
    if k == "--exe": EXE = a.pop(0)
    elif k == "--bot": BOT = a.pop(0)
    elif k == "--out": OUT = a.pop(0)

GAZE = {"id": "gaze", "object": None, "qualifier": None, "zone": None, "bearing": 0.0, "distance": 12.0, "elevation": 0.3, "tags": []}
PINW = {"id": "pin", "entity": None, "bearing": 35.0, "distance": 15.0, "elevation": 0.0}
BASE = {"player": {"downed": False}, "bot": {"stance": "stand", "items": []}, "bot_pin": None}
WORLDS = {
    "GAZE": dict(BASE, entities=[GAZE], player_gaze="gaze", player_pin=None),
    "PIN": dict(BASE, entities=[GAZE], player_gaze="gaze", player_pin=PINW),
    "SKY": dict(BASE, entities=[], player_gaze=None, player_pin=None),
}

GROUPS = [
    ("no place", "GAZE", """follow me|on me|stay with me|stick with me|come with me|stay close|let's move
come back|come here|get back here|back to me|regroup|regroup on me|get over here|come to me|to me
hold position|stay here|stay put|hold here|stop|don't move|wait here|stay where you are|hold this spot|freeze|stay
hold this angle|watch this angle|watch that way|cover this angle|watch it|keep an eye on that|keep watch
hold the other angle|watch the other side|take the other side|watch the other way
cover me|watch my back|cover me while i move|watch my six|i'm moving cover me|cover my back
fall back|retreat|back off|pull back|get out of there|get back
take cover|get to cover|get down|hide|find cover|get behind cover
attack|engage|take him out|kill him|get him|shoot him|attack them|engage the enemy
open fire|weapons free|fire at will|fire|shoot|light them up
hold fire|cease fire|stop shooting|don't shoot|hold your fire|weapons tight
suppress|suppressing fire|covering fire|pin them down|keep them pinned|lay down fire
frag out|throw a grenade|grenade|toss a frag|throw a frag
flank|flank them|go around|hit them from the side|go around them
push in|go in|clear the room|push|push up|move in|move up
check it|check it out|go check|clear it|go take a look
look at me|eyes on me|face me|turn to me
help me|i need help|come help me|need backup|i need you here
revive me|i'm down|pick me up|get me up
wait|hold up|hang on|wait for my signal|not yet|wait a second
go|go go go|now|do it|execute|move
jump|jump up|jump over|jump down|hop over it
crouch|stay low|get low|duck|crouch down
go prone|lie down|hit the dirt|get on the ground
stand up|get up|on your feet|stand
never mind|cancel that|forget it|don't|stop that|belay that|scratch that
throw a smoke|flash out|send the drone|rappel down|plant the bomb|defuse it|breach|breach it
nice shot|what's up|can you see me|thanks|good job|where are you|how many are there|enemy down|i'm reloading|contact left"""),
    ("pin", "PIN", """go to my pin|move to my pin|stay at my pin|hold my pin|hold at my mark|go to the marker|move to the marker|go to the ping|go to my mark|go to my marker|go where i marked|move to where i pinged|go to the waypoint|get to my pin|on my pin
watch my pin|look at my pin|look at the marker|keep an eye on my pin|cover my pin|hold the angle on my pin
check my pin|check the pin|check out my mark|go check the marker|clear my pin
frag my pin|frag out at my mark|throw a grenade at my pin|grenade on my mark|put a frag on my pin
suppress my pin|fire on my pin|shoot at my mark|covering fire on my pin|open fire on my mark
flank my pin|attack my pin|push to my pin|push my pin|take cover at my pin|fall back to my pin|jump to my pin|hide at my pin
wait at my pin|regroup at my pin|go to my pin and hold|crouch at my pin"""),
    ("pin, none placed", "GAZE", "go to my pin|hold my pin|check my pin|frag my pin|watch my pin|suppress my mark"),
    ("gaze", "GAZE", """go there|move there|go over there|move up there|get over there|go to that spot|go where i'm looking|go where i'm pointing|go to that position|move to that spot|head over there|get there
stay there|hold there|hold that spot|hold that position|wait there|stay over there|hold over there
watch there|watch over there|look there|look over there|look at that|look at this|look where i'm looking|watch that|watch that spot|cover that|hold that angle|keep an eye over there|eyes over there
check there|check over there|check that|check that out|check this out|check that room|check that corner|check this|go check over there|clear that
frag there|throw a grenade there|grenade over there|frag that|toss a frag over there|throw a grenade at that
suppress there|suppress that|suppress that position|fire there|shoot there|shoot at that|shoot that|open fire on that|covering fire over there
attack there|push there|push over there|flank there|flank that|attack that position|move in there
take cover there|take cover over there|hide there|hide behind that|get behind that|take cover behind that
fall back there|fall back over there|jump there|jump on that|jump over that|jump down there|climb up there|get up there
go here|move here|stay here|hold here|wait here|look here|over here|check here|come over here|hold right here|stay right here|right here"""),
    ("gaze on nothing", "SKY", "go there|hold there|watch there|check that|frag there|suppress that|stay here|look over there|flank there"),
    ("direction", "GAZE", """go left|go right|go forward|go back|move left|move right|move forward|move back|move up|go straight|keep going|go ahead
push forward|push left|push right|advance|step back|back up|step forward|a bit to the left|a little to the right|move to the left|move to the right|go to the left|go to the right
watch left|watch right|watch behind|watch behind us|watch our back|watch the rear|watch the front|watch ahead|watch your left|watch the left side|watch our six|watch my left|watch my right
look left|look right|look behind you|look up|look down|look ahead|look back|look forward|look to your left|turn around|turn left|turn right
check left|check right|check behind us|check the left side|check ahead|check up there|check down there
suppress left|suppress right|fire left|shoot right|covering fire to the left|suppress forward
frag left|grenade right|throw a grenade forward|frag out ahead|throw a grenade behind that
flank left|flank right|go around the left|go around the right|flank from the left|take the left flank
jump forward|jump back|jump left|jump right
hold left|hold the left side|hold right|take the left|take the right side|cover left|cover the right|cover our rear|cover the front
watch nine o'clock|look at three o'clock|check six o'clock|suppress twelve o'clock|go to your two o'clock
go up|go down|go upstairs|go downstairs|move up a level|get up high|get down low
fall back left|fall back to the right|take cover on the left|take cover to the right|attack left|attack on the right|push right side"""),
    ("the speaker", "GAZE", """get behind me|stay behind me|go in front of me|stay on my left|on my right|next to me|stay next to me|by my side|go ahead of me|take point|lead the way|watch my left|watch my right
cover my left|cover my right|on my six|stay on my six|form up on me|move to my position|come to my position|hold my position|defend me|protect me|guard me"""),
    ("a named place, pointed at", "PIN", """go to that door|hold that door|watch that window|check that door|frag that window|suppress that window|go through that door|open that door|check this room|go up those stairs|watch those stairs|hold that doorway|cover that window|look at that door|take that door
go to the door at my pin|check the door by my pin|hold the window at my mark|watch the door near my pin"""),
    ("a named place, not pointed at", "GAZE", "go to the door|hold the door|watch the window|check the stairs|frag the window|go to the north door|go upstairs to the roof|get to the roof|go to the second floor|check the basement|hold the main door"),
    ("dialogues", "PIN", """hold the door > there
hold the door > over there
hold the door > that one
hold the door > at my pin
hold the door > my pin
hold the door > on the left
hold the door > the one i'm looking at
hold the door > never mind
hold the door > no
hold the door > follow me
check the window > there > hold fire
frag out on my go > go
go there on my go > go
hold there on my signal > now
check my pin on my go > wait > go
go to my pin when i say > go go go
go there > wait > go
go there > stop > continue
go there > never mind
follow me > stay here > come back
go there > the other one
go there > back there
crouch > crouch > stand up
suppress there > cease fire
hold this angle > watch the other side
hold the door > there on my go > go
go to my pin > go
go upstairs > there
go upstairs > at my pin
get to the roof > up there
hold the door > left
hold the door > right there
hold the door > it's over there
check the window > the one i'm looking at
frag the window > where i'm looking
hold the door on my go > over there > go
stay here on my go > go"""),
    ("pin placed after the question", "GAZE", "go to my pin"),
    ("this and here", "GAZE", """hold this spot|hold this position|stay right here|check this|look at this|go to this spot|watch this angle|watch this|frag this|hold here|come here|move here|check here|look here|wait here|hide here|take cover here|regroup here|stay here and watch|hold it here|over here|defend this spot|guard this position"""),
]

p = subprocess.Popen([EXE, "--serve", "--model-dir", BOT, "--threads", "3", "--no-spin", "--no-stt"], stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1)


def read():
    while True:
        line = p.stdout.readline()
        if not line:
            raise SystemExit("the service closed its stdout: " + p.stderr.read()[-600:])
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)


def ask(req):
    p.stdin.write(json.dumps(req) + "\n")
    p.stdin.flush()
    return read()


ready = read()
rows = []
out = open(OUT, "w", encoding="utf-8") if OUT else None


def emit(s):
    print(s)
    if out:
        out.write(s + "\n")


def show(group, world, text, r, step):
    o = r.get("order")
    order = "-"
    if o:
        order = o["intent"] + (" @" + o["entity"] if o["entity"] else "") + (" dir=" + o["direction"] if o["direction"] else "") + \
            (" zone=" + o["zone"] if o["zone"] else "") + (" ptr=" + o["pointer"] if o["pointer"] else "") + (" other" if o["other"] else "") + \
            (" cands=" + ",".join(o["candidates"]) if o["candidates"] and not o["entity"] else "") +             (" via=" + o["via"] if o.get("via") else "") + (" NEAR" if o.get("near") else "")
    ground = ";".join(g["status"][:3] + ("/" + g["via"] if g["via"] else "") + ("=" + g["entity"] if g["entity"] else "") for g in r.get("ground", []))
    extra = ""
    if r.get("question"): extra += " Q:" + r["question"]["kind"]
    if r.get("pending"): extra += " pending=" + r["pending"] + ("@" + r["pending_entity"] if r.get("pending_entity") else "")
    emit(f"{'  > ' if step else ''}{text!r:42s} {r.get('intent') or '-':16s} {r.get('prob', 0):.2f} {r.get('action'):9s} places[{r.get('places', '')}] "
         f"ground[{ground}] order[{order}]{extra} say={r.get('say')!r}")
    rows.append({"group": group, "world": world, "text": text, "step": step, "intent": r.get("intent"), "prob": r.get("prob"), "action": r.get("action"),
                 "places": r.get("places"), "ground": r.get("ground"), "order": o, "say": r.get("say"), "question": r.get("question"),
                 "pending": r.get("pending"), "pending_entity": r.get("pending_entity"), "top": r.get("top")})


n = 0
t0 = time.perf_counter()
for group, world, block in GROUPS:
    emit(f"\n=== {group} (world {world}) ===")
    for line in block.replace("\n", "|").split("|"):
        line = line.strip()
        if not line:
            continue
        ask({"cmd": "reset"})
        for i, text in enumerate(s.strip() for s in line.split(">")):
            n += 1
            r = ask({"cmd": "text", "id": n, "text": text, "world": WORLDS[world]})
            if r.get("event") != "reply":
                emit(f"{text!r}: {r}")
                continue
            show(group, world, text, r, i > 0)
emit(f"\n{n} lines in {time.perf_counter() - t0:.1f} s")
p.stdin.write('{"cmd":"quit"}\n'); p.stdin.flush()
p.wait(timeout=20)
if OUT:
    json.dump(rows, open(OUT + ".json", "w", encoding="utf-8"), indent=1)
