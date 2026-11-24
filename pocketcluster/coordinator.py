import inspect
import json
import textwrap
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


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
        self._server = ThreadingHTTPServer((host, port), self._make_handler())
        self.port = self._server.server_address[1]
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    # ---- public API ----
    def map(self, fn, items, timeout=None, chunksize=1):
        src = textwrap.dedent(inspect.getsource(fn))
        name = fn.__name__
        job = uuid.uuid4().hex[:8]
        ids = []
        items = list(items)
        many = chunksize > 1
        units = [items[i:i + chunksize] for i in range(0, len(items), chunksize)] if many else items
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
            states = [t["state"] for t in self._tasks.values()]
            return {
                "workers_online": sum(1 for s in self._workers.values() if now - s < 15),
                "queued": states.count("queued"),
                "running": states.count("running"),
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

    def _register(self):
        wid = uuid.uuid4().hex[:6]
        with self._lock:
            self._workers[wid] = time.time()
        return wid

    def _claim(self, worker):
        with self._cv:
            self._workers[worker] = time.time()
            self._requeue_expired()
            while self._pending:
                tid = self._pending.pop(0)
                t = self._tasks.get(tid)
                if t is None or t["state"] != "queued":
                    continue
                t["state"] = "running"
                t["worker"] = worker
                t["deadline"] = time.time() + self.lease
                return {"id": tid, "name": t["name"], "src": t["src"], "item": t["item"], "many": t["many"]}
        return None

    def _finish(self, tid, result, error):
        with self._cv:
            t = self._tasks.get(tid)
            if t is None or t["state"] == "done":
                return
            t["state"] = "done"
            t["result"] = result
            t["error"] = error
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
                if self.headers.get("X-Token") != cluster.token:
                    self._send(401, {"error": "bad token"})
                    return False
                return True

            def do_GET(self):
                if not self._auth():
                    return
                if self.path == "/status":
                    self._send(200, cluster.status())
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
                    self._send(200, {"worker": cluster._register()})
                elif self.path == "/task":
                    self._send(200, {"task": cluster._claim(data.get("worker", ""))})
                elif self.path == "/result":
                    cluster._finish(data.get("id"), data.get("result"), data.get("error"))
                    self._send(200, {})
                else:
                    self._send(404, {"error": "not found"})

        return Handler
