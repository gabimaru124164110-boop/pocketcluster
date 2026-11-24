import threading
import unittest

from pocketcluster import Cluster
from pocketcluster.worker import run_worker


def square(n):
    return n * n


class TestMap(unittest.TestCase):
    def test_map_keeps_order(self):
        c = Cluster(host="127.0.0.1", port=0, token="t")
        url = f"http://127.0.0.1:{c.port}"
        for _ in range(3):
            threading.Thread(target=run_worker, args=(url, "t", 0.05), daemon=True).start()
        out = c.map(square, list(range(30)), timeout=20)
        self.assertEqual(out, [n * n for n in range(30)])
        c.close()


if __name__ == "__main__":
    unittest.main()
