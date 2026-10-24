"""The owner's recording booth for his bot voice: serves rec/index.html on http://127.0.0.1:8765 and keeps every take
in work/owner_rec/wav/<id>.wav, with metadata.csv (wav|text, the Piper training format) rewritten after each change.
Standard library only; any Python 3.9+:

    python rec_server.py [--data work/owner_rec] [--port 8765]

The page records in the browser (microphone on localhost is allowed without https) and sends each take as a WAV."""
import argparse
import json
import re
import threading
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE / "rec" / "index.html"
ID = re.compile(r"^[a-z]+_\d{4}$")
LOCK = threading.Lock()


class Booth:
    def __init__(self, data):
        self.data = Path(data)
        self.wav = self.data / "wav"
        self.wav.mkdir(parents=True, exist_ok=True)
        self.lines = json.loads((self.data / "lines.json").read_text(encoding="utf-8"))["lines"]
        self.by_id = {line["id"]: line for line in self.lines}
        self.state_path = self.data / "state.json"
        self.state = json.loads(self.state_path.read_text(encoding="utf-8")) if self.state_path.exists() else {"skipped": []}

    def seconds(self, uid):
        path = self.wav / f"{uid}.wav"
        if not path.exists():
            return None
        try:
            with wave.open(str(path)) as w:
                return round(w.getnframes() / w.getframerate(), 2)
        except (wave.Error, EOFError):
            return None

    def snapshot(self):
        recorded = {}
        for line in self.lines:
            s = self.seconds(line["id"])
            if s is not None:
                recorded[line["id"]] = s
        return {"lines": self.lines, "recorded": recorded, "skipped": self.state["skipped"]}

    def write_metadata(self):
        rows = [f"{line['id']}.wav|{line['text']}" for line in self.lines
                if (self.wav / f"{line['id']}.wav").exists() and line["id"] not in self.state["skipped"]]
        (self.data / "metadata.csv").write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")

    def save_state(self):
        self.state_path.write_text(json.dumps(self.state, ensure_ascii=False, indent=1), encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    booth: Booth = None

    def log_message(self, fmt, *args):
        pass

    def send(self, code, body=b"", ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def json(self, obj, code=200):
        self.send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def uid(self, prefix):
        uid = self.path.split("?")[0][len(prefix):].removesuffix(".wav")
        return uid if ID.match(uid) and uid in self.booth.by_id else None

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/state":
            with LOCK:
                self.json(self.booth.snapshot())
        elif path.startswith("/take/"):
            uid = self.uid("/take/")
            f = uid and self.booth.wav / f"{uid}.wav"
            if f and f.exists():
                self.send(200, f.read_bytes(), "audio/wav")
            else:
                self.send(404)
        else:
            self.send(404)

    def do_PUT(self):
        uid = self.uid("/api/take/")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        if not uid or body[:4] != b"RIFF" or body[8:12] != b"WAVE":
            return self.json({"error": "bad take"}, 400)
        with LOCK:
            (self.booth.wav / f"{uid}.wav").write_bytes(body)
            if uid in self.booth.state["skipped"]:
                self.booth.state["skipped"].remove(uid)
                self.booth.save_state()
            self.booth.write_metadata()
            self.json({"ok": True, "seconds": self.booth.seconds(uid)})

    def do_DELETE(self):
        uid = self.uid("/api/take/")
        if not uid:
            return self.json({"error": "no such line"}, 404)
        with LOCK:
            (self.booth.wav / f"{uid}.wav").unlink(missing_ok=True)
            self.booth.write_metadata()
            self.json({"ok": True})

    def do_POST(self):
        uid = self.uid("/api/skip/")
        if not uid:
            return self.json({"error": "no such line"}, 404)
        with LOCK:
            skipped = self.booth.state["skipped"]
            if uid in skipped:
                skipped.remove(uid)
            else:
                skipped.append(uid)
            self.booth.save_state()
            self.booth.write_metadata()
            self.json({"ok": True, "skipped": uid in skipped})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE / "work" / "owner_rec"))
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    Handler.booth = Booth(args.data)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"booth: http://127.0.0.1:{args.port}/  ({len(Handler.booth.lines)} lines, takes in {Handler.booth.wav})", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
