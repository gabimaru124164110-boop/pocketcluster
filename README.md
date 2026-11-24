# PocketCluster

Turn the old Android phones in your drawer into a compute cluster.
Pure Python, zero dependencies, runs in Termux.

Status: early development. Core scheduler coming first.

## Idea

    from pocketcluster import Cluster
    results = Cluster().map(work, chunks)

One phone coordinates, the others pull work and send results back.
