import json
import threading
import unittest
import urllib.error
import urllib.request

from pocketcluster import Cluster
from pocketcluster.worker import run_worker


def one(n):
    return 1


class TestDashboard(unittest.TestCase):
    def test_status_and_page(self):
        c = Cluster(host="127.0.0.1", port=0, token="t")
        base = f"http://127.0.0.1:{c.port}"
        threading.Thread(target=run_worker, args=(base, "t", 0.05), daemon=True).start()
        c.map(one, [1, 2, 3], timeout=20)
        s = json.loads(urllib.request.urlopen(base + "/status?token=t").read())
        self.assertEqual(s["workers_online"], 1)
        self.assertEqual(s["workers"][0]["done"], 3)
        page = urllib.request.urlopen(base + "/?token=t").read().decode()
        self.assertIn("PocketCluster", page)
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(base + "/status?token=wrong")
        c.close()


if __name__ == "__main__":
    unittest.main()
