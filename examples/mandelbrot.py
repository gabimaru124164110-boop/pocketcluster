import argparse
import math
import struct
import time
import zlib

from pocketcluster import Cluster


def render_row(job):
    w, h, y, max_iter = job["w"], job["h"], job["y"], job["iters"]
    x_min, x_max, y_min, y_max = job["view"]
    ci = y_min + (y_max - y_min) * y / (h - 1)
    row = []
    for x in range(w):
        cr = x_min + (x_max - x_min) * x / (w - 1)
        zr = zi = 0.0
        n = 0
        while n < max_iter and zr * zr + zi * zi <= 4.0:
            zr, zi = zr * zr - zi * zi + cr, 2 * zr * zi + ci
            n += 1
        row.append(n)
    return row


def color(n, max_iter):
    if n >= max_iter:
        return (0, 0, 0)
    return (
        int(127.5 * (1 + math.sin(0.1 * n))),
        int(127.5 * (1 + math.sin(0.1 * n + 2.0))),
        int(127.5 * (1 + math.sin(0.1 * n + 4.0))),
    )


def write_png(path, pixels):
    h, w = len(pixels), len(pixels[0])
    raw = b"".join(
        b"\x00" + bytes(c for px in row for c in px) for row in pixels
    )

    def chunk(tag, data):
        body = struct.pack(">I", len(data)) + tag + data
        return body + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )
    with open(path, "wb") as f:
        f.write(png)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--width", type=int, default=320)
    p.add_argument("--height", type=int, default=240)
    p.add_argument("--iters", type=int, default=120)
    p.add_argument("--workers", type=int, default=1, help="wait for this many workers")
    p.add_argument("--token", default="pocket")
    p.add_argument("--chunk", type=int, default=8, help="rows per task")
    p.add_argument("--out", default="mandelbrot.png")
    a = p.parse_args()

    cluster = Cluster(token=a.token)
    print(f"Coordinator up on port {cluster.port}. Start workers with:")
    print(f"  python -m pocketcluster worker http://THIS_PHONE_IP:{cluster.port} --token {a.token}")
    while cluster.status()["workers_online"] < a.workers:
        print("waiting for workers:", cluster.status()["workers_online"], "/", a.workers)
        time.sleep(2)

    view = [-2.2, 1.0, -1.2, 1.2]
    jobs = [
        {"w": a.width, "h": a.height, "y": y, "iters": a.iters, "view": view}
        for y in range(a.height)
    ]
    n_workers = cluster.status()["workers_online"]
    t0 = time.time()
    rows = cluster.map(render_row, jobs, chunksize=a.chunk)
    dt = time.time() - t0
    print(f"Rendered {a.width}x{a.height} in {dt:.1f}s with {n_workers} workers")
    write_png(a.out, [[color(n, a.iters) for n in row] for row in rows])
    print("Saved", a.out)


if __name__ == "__main__":
    main()
