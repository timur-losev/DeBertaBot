"""Relay one line to coop_bot_server.py and print the exchange.  python say.py "breach on my go" """
import json, sys, urllib.request

text = " ".join(sys.argv[1:])
req = urllib.request.Request("http://127.0.0.1:8765/say", data=json.dumps({"text": text}).encode("utf-8"),
                             headers={"Content-Type": "application/json"})
r = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
sys.stdout.reconfigure(encoding="utf-8")
top = " | ".join(f"{i} {p:.2f}" for i, p in r["top3"])
slots = [s for s, on in (("on my signal", r["on_signal"]), ("other", r["other"])) if on]
print(f"you> {text}")
print(f"bot> {r['reply']}")
print(f"     {top} | {r['action']}" + (f" | slots: {', '.join(slots)}" if slots else "")
      + (f" | queued: {r['pending']}" if r["pending"] else "") + f" | {r['ms']:.0f} ms (CPU)")
