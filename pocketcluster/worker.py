import json
import socket
import time
import traceback
import urllib.error
import urllib.request


def _post(url, token, obj, timeout=30):
    req = urllib.request.Request(
        url,
        data=json.dumps(obj).encode(),
        headers={"Content-Type": "application/json", "X-Token": token},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def run_worker(base, token="pocket", poll=0.5):
    """Join a coordinator and process tasks forever."""
    base = base.rstrip("/")
    me = _post(base + "/register", token, {"host": socket.gethostname()})["worker"]
    print(f"worker {me} joined {base}")
    while True:
        try:
            task = _post(base + "/task", token, {"worker": me})["task"]
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print("bad token, exiting")
                return
            time.sleep(2)
            continue
        except (urllib.error.URLError, OSError):
            print("coordinator unreachable, retrying...")
            time.sleep(2)
            continue
        if task is None:
            time.sleep(poll)
            continue
        try:
            ns = {}
            exec(task["src"], ns)
            result = ns[task["name"]](task["item"])
            json.dumps(result)
            payload = {"id": task["id"], "result": result, "error": None}
        except Exception:
            payload = {"id": task["id"], "result": None,
                       "error": traceback.format_exc(limit=3)}
        try:
            _post(base + "/result", token, payload)
        except (urllib.error.URLError, OSError):
            print("could not report result")
