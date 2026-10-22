"""v61's accented audio: every spoken line (authors r6 and cs) and every seed command, read again by the Windows voices of
other languages, so that Parakeet's transcripts carry the mistakes it makes on a non-native speaker. The owner is a native
Russian speaker. The Russian voices reading English give the same kind of mishearings as the owner's own voice (a probe
of 30 commands, 2026-10-21): "shoot this wall" -> "Should kiss while", "shoot here" -> "Should here", "go there" -> "Good
here" / "Good year", "kill them" -> "Kiss him", "switch to shotgun" -> "Switch to shutgun". The German voices add other
mistakes of the same kind.

  ru   Microsoft Irina, Microsoft Pavel (ru-RU)
  de   Microsoft Hedda, Microsoft Katja, Microsoft Stefan (de-DE)

The voices are dealt in turn, at speaking rates 0 and 1 (each voice reads at both rates). Writes four lists for
synth_accent_v61.ps1 and run_stt.py:
  accent_ru_v61.json, accent_de_v61.json            the lines -> wav_ru, wav_de
  accent_seedru_v61.json, accent_seedde_v61.json    the seed commands -> wav_seedru, wav_seedde

    python export_accent_v61.py
"""
import io, json, os, sys
os.environ["COOP_TAG"] = "v61"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import coop_v2 as V

HERE = os.path.dirname(os.path.abspath(__file__))
VOICES = {"ru": ["Microsoft Irina", "Microsoft Pavel"], "de": ["Microsoft Hedda", "Microsoft Katja", "Microsoft Stefan"]}
lines = [i for i in V.load_items() if i["maj"] and i["author"] in ("r6", "cs")]
seeds = V.seed_items()
for acc, voices in VOICES.items():
    k = len(voices)
    for name, items, prefix in ((acc, lines, "l"), ("seed" + acc, seeds, "s")):
        rows = [{"id": i["id"], "text": i["text"], "maj": i["maj"], "voice": voices[n % k], "rate": (n // k) % 2,
                 "wav": f"a61{prefix}_{n:05d}.wav"} for n, i in enumerate(items)]
        json.dump(rows, io.open(os.path.join(HERE, f"accent_{name}_v61.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print(f"accent_{name}_v61.json: {len(rows)} rows")
