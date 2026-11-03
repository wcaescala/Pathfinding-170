# Evaluation Plan: Dragon Age 2 (DA2) Pathfinding Benchmark

## 1. Executive Summary & Benchmark Context

This evaluation plan establishes the methodology for empirically comparing pathfinding algorithms on the **Moving AI Dragon Age 2 (DA2) Pathfinding Benchmark**. The benchmark suite provides grid maps with real video game obstacle topologies (urban districts, cavern systems, dungeons, and open wilderness) alongside thousands of pre-generated ground-truth pathfinding scenarios with proven optimal lengths.

### Algorithms Under Comparison
1. **Dijkstra's Algorithm** (Uniform-Cost Search baseline)
2. **Breadth-First Search (BFS)** (Uninformed level-by-level baseline)
3. **Depth-First Search (DFS)** (Uninformed depth-oriented exploration)
4. **Greedy Best-First Search** (Heuristic-only directed search)
5. **A\* Search** (Combined cost + admissible heuristic optimal search)
6. **Jump Point Search (JPS)** (Pruned symmetry-skipping grid optimization of A\*)

---

## 2. Dragon Age 2 Dataset Taxonomy & Characterization

The DA2 dataset contains **67 maps** and **67 scenario files (`.scen`)** with ground-truth coordinates and optimal costs. Maps fall into five distinct environmental categories and three scale tiers:

### 2.1 Environmental Categories
| Prefix | Environment | Map Count | Topology Characteristics | Pathfinding Challenges |
| :--- | :--- | :---: | :--- | :--- |
| **`ca_`** | Caves & Caverns | 6 | Irregular, organic corridors, natural dead ends | Tortuous winding paths, dead-end traps for unguided DFS |
| **`dr_`** | Deep Roads & Dungeons | 5 | Massive halls, straight subterranean routes, narrow doorways | Long distance queries, high open-area branching factor |
| **`ht_`** | Hightown (Urban Estates) | 15 | Interior manors, rectangular rooms, narrow doorways | Chokepoints, doorway bottlenecks, right-angled walls |
| **`lt_`** | Lowtown (Slums & Alleys) | 31 | Dense urban maze, courtyards, alleys, docks | High obstacle density, numerous alternative suboptimal corridors |
| **`w_`** | Wilderness & Outskirts | 10 | Expansive rocky outdoor terrains, huge open vistas | Gigantic map dimensions (up to 770x770), expansive frontiers |

### 2.2 Map Dimension & Scale Tiers
To ensure algorithms are tested against different spatial scales, maps are classified into three size tiers:
* **Small (< 30,000 total cells):** Fast execution, micro-corridors. Examples: `ht_store.map` (37x37 = 1,369 cells), `lt_foundry_n.map` (109x92 = 10,028 cells), `ht_playershouse_n.map` (185x68 = 12,580 cells).
* **Medium (30,000 – 200,000 total cells):** Standard game exploration zones. Examples: `ca_cave.map` (183x277 = 50,691 cells), `ht_keep.map` (281x357 = 100,317 cells), `w_encounter1.map` (258x514 = 132,612 cells).
* **Large (> 200,000 total cells):** Macro-scale game areas. Examples: `lt_0_lowtown.map` (514x514 = 264,196 cells), `w_woundedcoast.map` (642x578 = 371,076 cells), `dr_0_deeproads.map` (560x733 = 410,480 cells), `w_sundermount.map` (770x770 = 592,900 cells).

---

## 3. Stratified Scenario Sampling Methodology

### 3.1 Rationale for Stratified Sampling
The complete DA2 benchmark contains tens of thousands of scenario queries. Running exhaustive tests across every scenario for unguided search algorithms (especially DFS and BFS on large 770x770 grids) would require hundreds of compute hours and risk memory exhaustion. 

A **stratified sampling strategy** balances thorough representation across map topologies and path difficulties while keeping execution times manageable and statistically sound.

### 3.2 Distance Stratification Tiers
Moving AI scenario files categorize queries into integer `bucket` values corresponding to path lengths. We partition scenarios into three difficulty tiers:

1. **Short Distance (Bucket 0 – 4 | Optimal Cost < 20.0):**
   - Tests local collision avoidance and baseline algorithmic overhead.
   - Algorithms should solve these almost instantaneously.
2. **Medium Distance (Bucket 5 – 19 | Optimal Cost 20.0 – 100.0):**
   - Tests navigation through interconnected corridors and obstacles.
   - Highlights the benefit of heuristic guidance over uniform exploration.
3. **Long Distance (Bucket 20+ | Optimal Cost > 100.0):**
   - Stress-tests memory consumption, frontier growth, and asymptotic performance.
   - Magnifies differences between A\*, JPS, Dijkstra, BFS, and DFS.

### 3.3 Sampling Protocol & Representative Portfolio
For standardized evaluation, the automated sampler selects **9 representative maps** (spanning all 5 environments and 3 scale tiers):
* **Small:** `ht_store.map`, `lt_foundry_n.map`, `ht_playershouse_n.map`
* **Medium:** `ca_cave.map`, `ht_keep.map`, `w_encounter1.map`
* **Large:** `lt_0_lowtown.map`, `w_woundedcoast.map`, `dr_0_deeproads.map`

From each map, **$k$ scenarios** are sampled from each distance tier (Short, Medium, Long) using a fixed deterministic pseudo-random seed (`seed=42`).
* Recommended fast benchmark: $k = 2$ per tier $\times$ 3 tiers $\times$ 9 maps = **54 test scenarios**.
* Recommended comprehensive benchmark: $k = 5$ per tier $\times$ 3 tiers $\times$ 9 maps = **135 test scenarios**.

---

## 4. Metric Measurement Methods & Formal Definitions

### 4.1 Metric 1: Execution Time (Milliseconds)
* **Definition:** The elapsed wall-clock search time from invocation of the search algorithm until the path is reconstructed or search termination is signaled.
* **Measurement Procedure:**
  - Measured using Python's high-resolution monotonic timer: `time.perf_counter()`.
  - Maps are pre-loaded into memory prior to the timing block to isolate search algorithm execution from file I/O latency.
  - Formula:
    $$T_{\text{exec}} = (t_{\text{end}} - t_{\text{start}}) \times 1000 \quad [\text{ms}]$$
  - Reported as mean, median, standard deviation, min, and max.

### 4.2 Metric 2: Path Length (Octile Movement Cost) & Sub-Optimality
* **Definition:** The cumulative traversal cost of the reconstructed path connecting `start` to `goal`.
* **Benchmark Movement Rules (Octile Grid):**
  - Cardinal movement (North, South, East, West): Cost $= 1.0$.
  - Diagonal movement (NE, NW, SE, SW): Cost $= \sqrt{2} \approx 1.41421356$.
  - **No Corner Cutting:** A diagonal move between $(x, y)$ and $(x+dx, y+dy)$ is legal only if both adjacent cardinal cells $(x+dx, y)$ and $(x, y+dy)$ are passable.
* **Path Cost Formula:**
  $$L_{\text{path}} = \sum_{i=1}^{m} \text{cost}(p_{i-1}, p_i)$$
* **Sub-Optimality Ratio:**
  $$\alpha = \frac{L_{\text{path}}}{L_{\text{optimal}}}$$
  Where $L_{\text{optimal}}$ is the ground-truth optimal cost provided in the benchmark `.scen` file. An optimal path has $\alpha = 1.000$.

### 4.3 Metric 3: Number of Nodes Explored (Expanded)
* **Definition:** The number of unique grid states popped from the search frontier (queue/stack/priority queue) and whose legal neighbors were evaluated.
* **Complementary Diagnostic Metrics:**
  - **Nodes Generated:** Total successor nodes added to the open set/frontier.
  - **Peak Frontier Size:** Maximum cardinality reached by the frontier during search (measures space complexity).
  - **Search Effort Efficiency:** Ratio of optimal path length to explored nodes:
    $$\eta = \frac{L_{\text{optimal}}}{\text{Nodes Explored}}$$

### 4.4 Metric 4: Success Rate (%) & Path Validation
* **Definition:** The percentage of tested scenarios in which an algorithm successfully returns a verified, legal path without exceeding computational limits.
* **Formula:**
  $$\text{Success Rate} = \left( \frac{N_{\text{success}}}{N_{\text{total}}} \right) \times 100\%$$
* **Rigorous Path Verification Criteria:**
  A path is deemed successful if and only if:
  1. The first coordinate equals `start` and the final coordinate equals `goal`.
  2. Every intermediate cell is strictly within grid bounds and marked passable.
  3. All consecutive steps are valid octile transitions ($|dx| \le 1, |dy| \le 1$).
  4. All diagonal transitions strictly satisfy the no-corner-cutting rule.
  5. The search completed within the resource guards (Timeout $\le 5.0\text{s}$, Max Nodes $\le 100,000$).

---

## 5. Preliminary Baseline: BFS vs. DFS Empirical Findings

Using the implemented pure-Python modules (`algorithms/bfs.py` and `algorithms/dfs.py`), preliminary benchmark trials on representative scenarios revealed distinctive behaviors:

| Metric | Breadth-First Search (BFS) | Depth-First Search (DFS) | Theoretical Rationale |
| :--- | :--- | :--- | :--- |
| **Optimality Ratio ($\alpha$)** | $\approx 1.000$ (Optimal or near-optimal) | $2.6\times$ to $46.0\times$ (Highly suboptimal) | BFS minimizes step count; DFS plunges down single branches without cost consideration. |
| **Nodes Explored** | High, grows quadratically with distance ($O(b^d)$) | Highly variable; depends on tie-breaking direction | BFS explores an exhaustive circular wavefront; DFS may hit goal quickly if branch aligns, or wander through thousands of nodes. |
| **Path Trajectory** | Smooth, direct, follows shortest geometry | Erratic, winding, snakes through irrelevant corridors | DFS lacks backtrack optimization once a deep path reaches the goal. |
| **Memory Footprint** | Large (stores entire expanding wavefront) | Minimal (proportional to current exploration depth) | Queue stores all frontier boundary cells vs Stack storing current depth path. |

---

## 6. Project Roadmap for Remaining Algorithms

| Algorithm | Category | Heuristic | Optimality Guarantee | Expected Trade-off vs BFS/DFS |
| :--- | :--- | :---: | :---: | :--- |
| **Dijkstra** | Uninformed | None | Yes (Cost-optimal) | Explores true uniform-cost contours, finding exact octile shortest paths; explores many nodes. |
| **Greedy Best-First** | Heuristic | Octile distance | No | Very fast execution, directs search straight toward goal; may produce suboptimal paths around large concave obstacles. |
| **A\*** | Heuristic | Octile distance (admissible) | Yes | Balances path cost $g(n)$ and heuristic $h(n)$; substantially reduces nodes explored compared to BFS/Dijkstra while guaranteeing optimality. |
| **Jump Point Search (JPS)** | Pruned Heuristic | Octile distance | Yes | Eliminates grid path symmetries by jumping directly to turning points; drastically fewer node expansions than A\* with identical optimal path length. |
