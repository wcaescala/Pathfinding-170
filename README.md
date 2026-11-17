# Pathfinding-170

## Group x

AJ Rabaria  
Wendy Escala  
Bart  
Ters  

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
