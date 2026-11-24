import threading
import unittest

from pocketcluster import Cluster
from pocketcluster.worker import run_worker


def triple(n):
    return n * 3


class TestChunks(unittest.TestCase):
    def test_chunked_map(self):
        c = Cluster(host="127.0.0.1", port=0, token="t")
        url = f"http://127.0.0.1:{c.port}"
        for _ in range(2):
            threading.Thread(target=run_worker, args=(url, "t", 0.05), daemon=True).start()
        out = c.map(triple, list(range(25)), timeout=20, chunksize=4)
        self.assertEqual(out, [n * 3 for n in range(25)])
        c.close()


if __name__ == "__main__":
    unittest.main()
