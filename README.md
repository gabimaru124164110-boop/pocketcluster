# PocketCluster

Turn the old Android phones in your drawer into a compute cluster.
Pure Python, zero dependencies, runs in Termux.

## Quickstart

On one phone, write a script:

    from pocketcluster import Cluster

    def square(n):
        return n * n

    cluster = Cluster(token="my-secret")
    print(cluster.map(square, list(range(100)), chunksize=8))

On every other phone (or extra Termux sessions):

    python -m pocketcluster worker http://COORDINATOR_IP:8765 --token my-secret

Workers pull tasks, compute, and send results back. If a phone dies
mid-task, the task is re-queued automatically.

Live dashboard: open http://COORDINATOR_IP:8765/?token=my-secret in a browser.

## Demos

    PYTHONPATH=. python examples/mandelbrot.py --workers 4
    PYTHONPATH=. python examples/failover_demo.py

## Benchmark

Mandelbrot 640x480, 200 iterations, 4 rows per task, median of 3 runs,
all workers on a single phone (so they share its cores and heat budget):

    workers   time    speedup
    1         7.5s    1.0x
    2         3.9s    1.9x
    4         2.8s    2.7x

Batching matters: sending one row per task made a single worker 2.4x
slower because of per-task HTTP overhead. Use chunksize. The first run
after a cold start is slower; reproduce with benchmarks/bench.sh.

## Notes

- Put imports inside the function you map; workers only receive its source.
- Items and results must be JSON-serializable.
- Workers execute code sent by the coordinator. Only join coordinators
  you trust, and change the default token.

Status: early development.
