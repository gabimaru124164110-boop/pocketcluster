from pocketcluster import Cluster


def slow_square(n):
    import time
    time.sleep(1.0)
    return n * n


if __name__ == "__main__":
    cluster = Cluster(token="pocket", lease=4)
    print(f"Dashboard: http://127.0.0.1:{cluster.port}/  (token: pocket)")
    input("Start 3 workers, then press Enter...")
    while True:
        out = cluster.map(slow_square, list(range(60)))
        print("done, correct:", out == [n * n for n in range(60)])
        if input("Enter to run again, q to quit: ").strip().lower() == "q":
            break
