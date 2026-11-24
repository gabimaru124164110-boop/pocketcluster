import argparse

from .worker import run_worker


def main():
    p = argparse.ArgumentParser(prog="pocketcluster")
    sub = p.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("worker", help="join a coordinator and run tasks")
    w.add_argument("url", help="e.g. http://192.168.1.5:8765")
    w.add_argument("--token", default="pocket")
    args = p.parse_args()
    if args.cmd == "worker":
        run_worker(args.url, args.token)


if __name__ == "__main__":
    main()
