"""Local development server that exposes the same handlers as API Gateway (stdlib only)."""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.handlers.api import dispatch  # noqa: E402

ORIGINS = {"http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173"}


class H(BaseHTTPRequestHandler):
    def _run(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n).decode("utf-8") if n else ""
        ev = {"requestContext": {"http": {"method": self.command}}, "rawPath": self.path.split("?")[0], "body": body}
        res = dispatch(ev)
        self.send_response(res["statusCode"])
        origin = self.headers.get("Origin")
        if origin in ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Headers", "content-type")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        for k, v in res["headers"].items():
            self.send_header(k, v)
        data = res["body"].encode("utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_OPTIONS = _run

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8787"))
    print(f"Resilience Simulator local API on http://127.0.0.1:{port}/api/v1/health")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
