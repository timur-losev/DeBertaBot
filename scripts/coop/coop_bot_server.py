"""
The same co-op bot as coop_bot.py, kept loaded behind a tiny local HTTP endpoint, so a conversation
can be relayed to it line by line (the bot keeps its state -- a queued "on my go" order -- between
lines). CPU only.

    python coop_bot_server.py                       # jev environment; listens on 127.0.0.1:8765
    POST /say        {"text": "breach on my go"}  -> reply, top-3, action, slots, queued order, ms
    POST /threshold  {"t": 0.6}
    GET  /health
"""
import json, os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import torch  # noqa: E402
from coop_bot import Bot  # noqa: E402

torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))
BOT = Bot()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(200, {"ok": True, "threshold": BOT.threshold, "pending": BOT.pending})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/threshold":
            BOT.threshold = float(body["t"])
            return self._send(200, {"threshold": BOT.threshold})
        reply, rec = BOT.respond(body.get("text", ""))
        rec["families"] = [BOT.family[i] for i, _ in rec["top3"]]
        self._send(200, {"reply": reply, **rec, "pending": BOT.pending})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("co-op bot ready on http://127.0.0.1:8765", flush=True)
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
