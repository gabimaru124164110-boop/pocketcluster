import inspect
import json
import textwrap
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .dashboard import PAGE


class Cluster:
    """Coordinator: hands out tasks to workers and collects results."""

    def __init__(self, host="0.0.0.0", port=8765, token="pocket", lease=30.0):
        self.token = token
        self.lease = lease
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._pending = []
        self._tasks = {}
        self._workers = {}
        self._completed = 0
        self._server = ThreadingHTTPServer((host, port), self._make_handler())
        self.port = self._server.server_address[1]
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    # ---- public API ----
    def map(self, fn, items, timeout=None, chunksize=1):
        src = textwrap.dedent(inspect.getsource(fn))
        name = fn.__name__
        job = uuid.uuid4().hex[:8]
        items = list(items)
        many = chunksize > 1
        units = (
            [items[i:i + chunksize] for i in range(0, len(items), chunksize)]
            if many else items
        )
        ids = []
        with self._cv:
            for i, item in enumerate(units):
                tid = f"{job}-{i}"
                self._tasks[tid] = {
                    "name": name, "src": src, "item": item, "many": many,
                    "state": "queued", "worker": None, "deadline": 0,
                    "result": None, "error": None,
                }
                self._pending.append(tid)
                ids.append(tid)
            self._cv.notify_all()
        end = None if timeout is None else time.time() + timeout
        with self._cv:
            while not all(self._tasks[t]["state"] == "done" for t in ids):
                self._requeue_expired()
                if end is not None and time.time() > end:
                    raise TimeoutError("cluster.map timed out")
                self._cv.wait(timeout=0.5)
            done = [self._tasks.pop(t) for t in ids]
        for t in done:
            if t["error"]:
                raise RuntimeError("task failed on a worker:\n" + t["error"])
        if many:
            return [r for t in done for r in t["result"]]
        return [t["result"] for t in done]

    def status(self):
        with self._lock:
            now = time.time()
            tasks = list(self._tasks.values())
            states = [t["state"] for t in tasks]
            busy = {t["worker"] for t in tasks if t["state"] == "running"}
            workers = [
                {"id": wid, "host": w["host"], "online": now - w["seen"] < 15,
                 "busy": wid in busy, "done": w["done"]}
                for wid, w in self._workers.items()
                if now - w["seen"] < 300
            ]
            return {
                "workers_online": sum(1 for w in workers if w["online"]),
                "queued": states.count("queued"),
                "running": states.count("running"),
                "done": states.count("done"),
                "completed_total": self._completed,
                "workers": workers,
            }

    def close(self):
        self._server.shutdown()

    # ---- internals ----
    def _requeue_expired(self):
        now = time.time()
        for tid, t in self._tasks.items():
            if t["state"] == "running" and t["deadline"] < now:
                t["state"] = "queued"
                self._pending.append(tid)

    def _register(self, host="?"):
        wid = uuid.uuid4().hex[:6]
        with self._lock:
            self._workers[wid] = {"host": str(host)[:40], "seen": time.time(), "done": 0}
        return wid

    def _claim(self, worker):
        with self._cv:
            w = self._workers.setdefault(worker, {"host": "?", "seen": 0, "done": 0})
            w["seen"] = time.time()
            self._requeue_expired()
            while self._pending:
                tid = self._pending.pop(0)
                t = self._tasks.get(tid)
                if t is None or t["state"] != "queued":
                    continue
                t["state"] = "running"
                t["worker"] = worker
                t["deadline"] = time.time() + self.lease
                return {"id": tid, "name": t["name"], "src": t["src"],
                        "item": t["item"], "many": t["many"]}
        return None

    def _finish(self, tid, result, error):
        with self._cv:
            t = self._tasks.get(tid)
            if t is None or t["state"] == "done":
                return
            t["state"] = "done"
            t["result"] = result
            t["error"] = error
            self._completed += 1
            w = self._workers.get(t["worker"])
            if w is not None:
                w["done"] += 1
            self._cv.notify_all()

    def _make_handler(self):
        cluster = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, code, obj):
                body = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _auth(self):
                qs = parse_qs(urlparse(self.path).query)
                given = self.headers.get("X-Token") or (qs.get("token") or [""])[0]
                if given != cluster.token:
                    self._send(401, {"error": "bad token"})
                    return False
                return True

            def do_GET(self):
                path = urlparse(self.path).path
                if path == "/status" and not self._auth():
                    return
                if path == "/status":
                    self._send(200, cluster.status())
                elif path in ("/", "/dashboard"):
                    body = PAGE.encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self._send(404, {"error": "not found"})

            def do_POST(self):
                if not self._auth():
                    return
                try:
                    n = int(self.headers.get("Content-Length") or 0)
                    data = json.loads(self.rfile.read(n) or b"{}")
                except ValueError:
                    self._send(400, {"error": "bad json"})
                    return
                if self.path == "/register":
                    self._send(200, {"worker": cluster._register(data.get("host", "?"))})
                elif self.path == "/task":
                    self._send(200, {"task": cluster._claim(data.get("worker", ""))})
                elif self.path == "/result":
                    cluster._finish(data.get("id"), data.get("result"), data.get("error"))
                    self._send(200, {})
                else:
                    self._send(404, {"error": "not found"})

        return Handler
