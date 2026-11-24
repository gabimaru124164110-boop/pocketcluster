from pocketcluster import Cluster


def square(n):
    return n * n


if __name__ == "__main__":
    cluster = Cluster(token="pocket")
    print("Start workers with:")
    print("  python -m pocketcluster worker http://THIS_PHONE_IP:8765 --token pocket")
    input("Press Enter once workers have joined...")
    print(cluster.map(square, list(range(20))))
    print(cluster.status())
