# Pathfinding-170

## Group x

- AJ
- Wendy 
- Bart
- Ters

## Project Files for running


| File | Purpose |
| ---- | ------- |
| `evaluation/runner.py` | Main entry point: runs the algorithms on sampled scenarios |
| `evaluation/sampler.py` | Stratified sampling of scenarios by map environment, map size, and distance tier |
| `evaluation/metrics.py` | Per-run metrics, path verification, and suboptimality (alpha) computation |
| `evaluation/aggregate.py` | Builds summary tables (CSV and Markdown) from `raw.csv` |
| `evaluation/plots.py` | Generates figures (PNG and PDF) from `raw.csv` |
| `evaluation/report.py` | Runs aggregate + plots on a results folder and writes `REPORT.md` |
| `requirements.txt` | Python dependencies (pandas, numpy, matplotlib, seaborn, tabulate, scipy, pytest); install with `pip install -r requirements.txt` |
| `algorithms/base.py` | Shared `SearchResult` type, octile distance, path cost computation, and path validation |
| `algorithms/bfs.py` | Breadth-First Search implementation |
| `algorithms/dfs.py` | Depth-First Search implementation (iterative) |
| `algorithms/dijkstra.py` | Dijkstra's algorithm implementation |
| `algorithms/a_star.py` | A* Search implementation (octile heuristic) |
| `algorithms/gbfs.py` | Greedy Best-First Search implementation (octile heuristic) |
| `algorithms/jump_point.py` | Jump Point Search implementation |
| `utils/map_loader.py` | Loads Moving AI `.map` files into a `GridMap` (passability and neighbor moves) |
| `utils/scenario_loader.py` | Loads Moving AI `.scen` files into `Scenario` objects (start, goal, optimal length) |
| `benchmarks/maps/` | Dragon Age 2 benchmark map files (`.map`) used as the search grids |
| `benchmarks/scenarios/` | Matching scenario files (`.map.scen`) with start/goal pairs and optimal lengths |



I hereby declare that the work I am submitting is faithful
to the letters of the CMSC 170 AI Operator's Covenant. I
affirm that I understand every part of this work, have
complied with the covenant, and accept full responsibility
for all submitted content.
---

## Pathfinding Algorithm Visualizer GUI

An interactive visualizer that marks and compares the path taken by each algorithm:
- **A\* Search** (Purple `#9467bd`)
- **Jump Point Search (JPS)** (Amber/Brown `#8c564b`)
- **Dijkstra's Algorithm** (Emerald Green `#2ca02c`)
- **Greedy Best-First Search (GBFS)** (Crimson Red `#d62728`)
- **Breadth-First Search (BFS)** (Blue `#1f77b4`)
- **Depth-First Search (DFS)** (Safety Orange `#ff7f0e`)

### How to Run

```bash
python3 gui.py
# or
make gui
```

### Key Features
- **Map Selection:** Browse all 67 Dragon Age 2 benchmark maps across 5 environments (Caves `ca_`, Deep Roads `dr_`, Hightown `ht_`, Lowtown `lt_`, Wilderness `w_`).
- **Custom Endpoints:** Set custom Start and Goal coordinates via text entry or click directly on the map (Left Click = 🟢 Start, Right Click = 🔴 Goal).
- **Run Algorithms:** Click **🚀 RUN ALGORITHMS** to execute all algorithms and visualize their paths.
- **Multi-Path Ribbon Overlay:** Parallel line offsets prevent overlapping paths from hiding one another.
- **Benchmark Metrics Comparison:** Live table comparing Path Cost, Optimal Cost, Suboptimality ($\alpha$), Hops, Nodes Expanded, Nodes Generated, Peak Frontier, and Runtime (ms). Double-click any row to highlight that algorithm's path.
