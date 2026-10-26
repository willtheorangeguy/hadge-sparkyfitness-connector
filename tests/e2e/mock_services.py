"""Synthetic GitHub REST service and fault-injecting proxy to the REAL Sparky API."""

import hashlib
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

LOCK = threading.Lock()
FILES = {}
SNAPSHOTS = {}
FAULT = None
METRICS = {"forwarded": 0, "injected": {}, "github_reads": 0}


def snapshot():
    commit = hashlib.sha1(json.dumps(FILES, sort_keys=True).encode(), usedforsecurity=False).hexdigest()
    SNAPSHOTS[commit] = dict(FILES)
    return commit


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, code, body, headers=None):
        payload = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == "/__health":
            return self.respond(200, {"ok": True})
        if parsed.path == "/__metrics":
            with LOCK:
                return self.respond(200, METRICS)
        if self.headers.get("Authorization") != "Bearer synthetic-github-token":
            return self.respond(401, {"error": "unauthorized"})
        with LOCK:
            commit = snapshot()
            files = SNAPSHOTS.get(parse_qs(parsed.query).get("ref", [commit])[0], {})
            path = parsed.path.removeprefix("/repos/e2e/health")
            if path == "":
                return self.respond(200, {"id": 12345, "default_branch": "main"})
            if path == "/commits/main":
                return self.respond(200, {"sha": commit})
            if path == "/contents/workouts":
                return self.respond(200, [
                    {"type": "file", "path": name,
                     "sha": hashlib.sha1(content.encode(), usedforsecurity=False).hexdigest()}
                    for name, content in files.items()
                ])
            if path.removeprefix("/contents/") in files:
                METRICS["github_reads"] += 1
                return self.respond(200, files[path.removeprefix("/contents/")])
        self.respond(404, {"error": "not found"})

    def do_POST(self):
        global FAULT
        payload = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/__configure":
            data = json.loads(payload)
            with LOCK:
                if "files" in data:
                    FILES.clear()
                    FILES.update(data["files"])
                FAULT = data.get("fault")
            return self.respond(200, {"ok": True})
        if self.path != "/api/health-data":
            return self.respond(404, {})
        with LOCK:
            fault, FAULT = FAULT, None
            if fault:
                METRICS["injected"][fault] = METRICS["injected"].get(fault, 0) + 1
        if fault == "rate_limit":
            return self.respond(429, {"error": "synthetic rate limit"}, {"Retry-After": "0"})
        if fault == "server_error":
            return self.respond(503, {"error": "synthetic outage"}, {"Retry-After": "0"})
        if fault == "partial":
            return self.respond(200, {"processed": [], "errors": [{"error": "synthetic rejection"}],
                                      "skipped": []})
        headers = {key: self.headers[key] for key in (
            "Authorization", "Content-Type", "X-Workout-Model-Version"
        ) if key in self.headers}
        request = Request("http://localhost:3010/api/health-data", data=payload, headers=headers)
        try:
            with urlopen(request, timeout=60) as response:
                code, body = response.status, response.read()
        except HTTPError as error:
            code, body = error.code, error.read()
        with LOCK:
            METRICS["forwarded"] += 1
        if fault == "lost_reply":
            self.close_connection = True
            self.connection.shutdown(socket.SHUT_RDWR)
            return
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    for port in (8080, 8081):
        server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Event().wait()
