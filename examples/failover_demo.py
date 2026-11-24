from pocketcluster import Cluster


def slow_square(n):
    import time
    time.sleep(1.0)
    return n * n


if __name__ == "__main__":
    cluster = Cluster(token="pocket", lease=4)
    print(f"Dashboard: http://THIS_PHONE_IP:{cluster.port}/?token=pocket")
    input("Start 3 workers, then press Enter...")
    out = cluster.map(slow_square, list(range(60)))
    print("done, correct:", out == [n * n for n in range(60)])
