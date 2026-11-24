# PocketCluster

Turn the old Android phones in your drawer into a compute cluster.
Pure Python, zero dependencies, runs in Termux.

## Quickstart

On one phone, write a script:

    from pocketcluster import Cluster

    def square(n):
        return n * n

    cluster = Cluster(token="my-secret")
    print(cluster.map(square, list(range(100))))

On every other phone (or extra Termux sessions):

    python -m pocketcluster worker http://COORDINATOR_IP:8765 --token my-secret

Workers pull tasks, compute, and send results back. If a phone dies
mid-task, the task is re-queued automatically.

## Demo: Mandelbrot across phones

    PYTHONPATH=. python examples/mandelbrot.py --workers 4

## Notes

- Put imports inside the function you map; workers only receive its source.
- Items and results must be JSON-serializable.
- Workers execute code sent by the coordinator. Only join coordinators
  you trust, and change the default token.

Status: early development.
