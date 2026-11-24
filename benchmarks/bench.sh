cd ~/pocketcluster
export PYTHONPATH=.
for n in 1 2 4; do
  pkill -f "pocketcluster worker" 2>/dev/null
  sleep 1
  for i in $(seq $n); do
    python -m pocketcluster worker http://127.0.0.1:8765 --token pocket > /dev/null 2>&1 &
  done
  for run in 1 2 3; do
    echo "workers=$n run=$run: $(python examples/mandelbrot.py --workers $n --chunk 4 --width 640 --height 480 --iters 200 --out bench.png | grep Rendered)"
  done
done
pkill -f "pocketcluster worker" 2>/dev/null
