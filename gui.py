#!/usr/bin/env python3
"""
Pathfinding Algorithm Visualizer GUI for Dragon Age 2 (DA2) Benchmark.
Clean, focused interface centered on Map Navigation, Custom Coordinate Placement,
and Benchmark Metrics Comparison across BFS, DFS, Dijkstra, GBFS, A*, and Jump Point Search.
"""

import argparse
import math
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.map_loader import load_map, GridMap
from utils.scenario_loader import load_scenarios, Scenario
from algorithms import ALGORITHMS
from algorithms.base import compute_path_cost, validate_path, SearchResult

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from PIL import Image, ImageTk, ImageDraw


# Algorithm visual configuration (consistent with benchmark reports)
ALGO_CONFIG = {
    "astar": {
        "name": "A* Search",
        "key": "astar",
        "color": "#9467bd",  # Purple
        "desc": "Cost + Octile Heuristic (Optimal)",
    },
    "jps": {
        "name": "Jump Point Search",
        "key": "jps",
        "color": "#8c564b",  # Amber/Brown
        "desc": "A* with Symmetry Pruning (Optimal)",
    },
    "dijkstra": {
        "name": "Dijkstra",
        "key": "dijkstra",
        "color": "#2ca02c",  # Emerald Green
        "desc": "Uniform Cost Search (Optimal)",
    },
    "gbfs": {
        "name": "Greedy Best-First",
        "key": "gbfs",
        "color": "#d62728",  # Crimson Red
        "desc": "Heuristic Only (Fast, Suboptimal)",
    },
    "bfs": {
        "name": "BFS",
        "key": "bfs",
        "color": "#1f77b4",  # Blue
        "desc": "Unweighted FIFO (Hop-Optimal)",
    },
    "dfs": {
        "name": "DFS",
        "key": "dfs",
        "color": "#ff7f0e",  # Safety Orange
        "desc": "Depth-First LIFO (Exploratory)",
    },
}

ENVIRONMENT_NAMES = {
    "ca_": "Caves & Caverns",
    "dr_": "Deep Roads & Dungeons",
    "ht_": "Hightown (Urban Estates)",
    "lt_": "Lowtown (Dense Alleys)",
    "w_": "Wilderness & Outskirts",
}


def classify_category(map_name: str) -> str:
    for prefix, name in ENVIRONMENT_NAMES.items():
        if map_name.startswith(prefix):
            return name
    return "Other"


def classify_size_tier(width: int, height: int) -> str:
    cells = width * height
    if cells < 30_000:
        return "Small (<30k)"
    elif cells <= 200_000:
        return "Medium (30k-200k)"
    else:
        return "Large (>200k)"


def compute_perpendicular_offset_path(
    screen_pts: List[Tuple[float, float]],
    offset_px: float
) -> List[Tuple[float, float]]:
    """
    Computes a path offset by `offset_px` perpendicular to each segment direction.
    Allows parallel ribbons for paths that overlap on identical grid segments.
    """
    n = len(screen_pts)
    if n < 2 or abs(offset_px) < 1e-3:
        return screen_pts

    result: List[Tuple[float, float]] = []
    for i in range(n):
        x, y = screen_pts[i]
        if i == 0:
            dx = screen_pts[1][0] - x
            dy = screen_pts[1][1] - y
        elif i == n - 1:
            dx = x - screen_pts[n - 2][0]
            dy = y - screen_pts[n - 2][1]
        else:
            dx = screen_pts[i + 1][0] - screen_pts[i - 1][0]
            dy = screen_pts[i + 1][1] - screen_pts[i - 1][1]

        mag = math.hypot(dx, dy)
        if mag == 0:
            result.append((x, y))
        else:
            px = -dy / mag
            py = dx / mag
            result.append((x + px * offset_px, y + py * offset_px))

    return result


class PathfindingVisualizerApp:
    def __init__(self, root: tk.Tk, initial_map: Optional[str] = None, initial_scen: Optional[int] = None):
        self.root = root
        self.root.title("Pathfinding Algorithm Visualizer — DA2 Benchmark")
        self.root.geometry("1350x850")
        self.root.minsize(1000, 650)

        # Style configuration
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Data state
        self.maps_dir = PROJECT_ROOT / "benchmarks" / "maps"
        self.scens_dir = PROJECT_ROOT / "benchmarks" / "scenarios"
        self.map_files: List[Path] = sorted(list(self.maps_dir.glob("*.map")), key=lambda p: p.name)

        self.current_gmap: Optional[GridMap] = None
        self.current_map_name: str = ""
        self.current_scenarios: List[Scenario] = []
        self.selected_scenario: Optional[Scenario] = None

        self.start_coord: Optional[Tuple[int, int]] = None
        self.goal_coord: Optional[Tuple[int, int]] = None

        # Algorithm run results: algo_key -> dict of metrics & path
        self.results: Dict[str, Dict[str, Any]] = {}
        self.is_running: bool = False
        self.focused_algo: Optional[str] = None

        # Interactive state
        self.click_placement_mode: tk.StringVar = tk.StringVar(value="none")  # "none", "start", "goal"

        # Viewport navigation state
        self.zoom: float = 1.0
        self.pan_x: float = 0.0
        self.pan_y: float = 0.0
        self.last_mouse_x: int = 0
        self.last_mouse_y: int = 0
        self.base_pil_image: Optional[Image.Image] = None
        self.photo_image: Optional[ImageTk.PhotoImage] = None

        # Build UI layout
        self._build_ui()

        # Initial map load
        target_map = initial_map or ("ht_store.map" if (self.maps_dir / "ht_store.map").exists() else (self.map_files[0].name if self.map_files else ""))
        if target_map:
            self._select_map_by_name(target_map, initial_scen)

    def _build_ui(self):
        # Main split container: Left Sidebar (Controls) | Right Panel (Canvas + Metrics Table)
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # Left Sidebar (Focused: Map Selection + Coordinates + Run + Legend)
        sidebar_frame = ttk.Frame(main_paned, width=310, padding=10)
        main_paned.add(sidebar_frame, weight=0)

        # Right Split Panel (Canvas Top, Metrics Table Bottom)
        right_paned = ttk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(right_paned, weight=1)

        # ------------------ SIDEBAR CONTENT ------------------
        self._build_sidebar_widgets(sidebar_frame)

        # ------------------ RIGHT CONTENT: CANVAS ------------------
        canvas_frame = ttk.Frame(right_paned)
        right_paned.add(canvas_frame, weight=3)

        # Canvas toolbar on top of canvas
        top_bar = ttk.Frame(canvas_frame, padding=(6, 4))
        top_bar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(top_bar, text="🔍 Zoom In (+)", command=self._zoom_in).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_bar, text="🔍 Zoom Out (-)", command=self._zoom_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_bar, text="⛶ Fit Map", command=self._fit_to_screen).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_bar, text="↺ Reset Pan", command=self._reset_pan).pack(side=tk.LEFT, padx=2)

        ttk.Separator(top_bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # Click placement tool buttons
        self.btn_set_start = ttk.Button(
            top_bar, text="🟢 Place Start", command=lambda: self._toggle_placement_mode("start")
        )
        self.btn_set_start.pack(side=tk.LEFT, padx=2)

        self.btn_set_goal = ttk.Button(
            top_bar, text="🔴 Place Goal", command=lambda: self._toggle_placement_mode("goal")
        )
        self.btn_set_goal.pack(side=tk.LEFT, padx=2)

        # Status & coordinates indicator
        self.lbl_coord_info = ttk.Label(top_bar, text="Coord: (—, —) | Tile: —", font=("Menlo", 10))
        self.lbl_coord_info.pack(side=tk.RIGHT, padx=6)

        # Main interactive Tkinter Canvas
        self.canvas = tk.Canvas(canvas_frame, bg="#0f172a", highlightthickness=0)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Canvas mouse event bindings
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_left_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<ButtonPress-2>", self._on_canvas_right_click)
        self.canvas.bind("<ButtonPress-3>", self._on_canvas_right_click)
        self.canvas.bind("<Motion>", self._on_canvas_mouse_move)

        # Scroll wheel zooming (macOS, Windows, Linux)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", lambda e: self._zoom_at(e.x, e.y, 1.2))
        self.canvas.bind("<Button-5>", lambda e: self._zoom_at(e.x, e.y, 0.8))
        self.canvas.bind("<Configure>", lambda e: self._on_canvas_resize())

        # ------------------ RIGHT CONTENT: METRICS TABLE ------------------
        metrics_frame = ttk.LabelFrame(right_paned, text="Benchmark Results & Path Metrics Comparison", padding=8)
        right_paned.add(metrics_frame, weight=1)

        columns = (
            "color", "algo", "status", "cost", "opt", "alpha", "hops",
            "expanded", "generated", "frontier", "time_ms"
        )
        self.tree = ttk.Treeview(metrics_frame, columns=columns, show="headings", height=8)
        self.tree.heading("color", text="●")
        self.tree.heading("algo", text="Algorithm")
        self.tree.heading("status", text="Status")
        self.tree.heading("cost", text="Path Cost")
        self.tree.heading("opt", text="Optimal")
        self.tree.heading("alpha", text="Subopt (α)")
        self.tree.heading("hops", text="Hops")
        self.tree.heading("expanded", text="Expanded")
        self.tree.heading("generated", text="Generated")
        self.tree.heading("frontier", text="Peak Front.")
        self.tree.heading("time_ms", text="Time (ms)")

        self.tree.column("color", width=35, anchor="center")
        self.tree.column("algo", width=150, anchor="w")
        self.tree.column("status", width=85, anchor="center")
        self.tree.column("cost", width=95, anchor="e")
        self.tree.column("opt", width=95, anchor="e")
        self.tree.column("alpha", width=85, anchor="e")
        self.tree.column("hops", width=70, anchor="e")
        self.tree.column("expanded", width=90, anchor="e")
        self.tree.column("generated", width=90, anchor="e")
        self.tree.column("frontier", width=90, anchor="e")
        self.tree.column("time_ms", width=90, anchor="e")

        tree_vscroll = ttk.Scrollbar(metrics_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_vscroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_vscroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self._on_table_row_double_click)

    def _build_sidebar_widgets(self, parent: ttk.Frame):
        # ==================== SECTION 1: MAP SELECTION ====================
        sec_map = ttk.LabelFrame(parent, text="Map Selection", padding=10)
        sec_map.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(sec_map, text="Environment Filter:").pack(anchor="w", pady=(0, 2))
        self.cbo_env_filter = ttk.Combobox(
            sec_map,
            values=["All Environments", "Caves & Caverns (ca_)", "Deep Roads & Dungeons (dr_)",
                    "Hightown (ht_)", "Lowtown (lt_)", "Wilderness (w_)"],
            state="readonly"
        )
        self.cbo_env_filter.current(0)
        self.cbo_env_filter.pack(fill=tk.X, pady=(0, 8))
        self.cbo_env_filter.bind("<<ComboboxSelected>>", lambda e: self._filter_maps())

        ttk.Label(sec_map, text="Select Map (67 available):").pack(anchor="w", pady=(0, 2))
        self.cbo_map = ttk.Combobox(sec_map, state="readonly")
        self.cbo_map.pack(fill=tk.X, pady=(0, 8))
        self.cbo_map.bind("<<ComboboxSelected>>", self._on_map_dropdown_select)

        self.lbl_map_info = ttk.Label(
            sec_map, text="Dimensions: — | Passable: —", font=("Helvetica", 9, "italic"), wraplength=280
        )
        self.lbl_map_info.pack(anchor="w")

        # ==================== SECTION 2: CUSTOM COORDINATES ====================
        sec_coord = ttk.LabelFrame(parent, text="Coordinates (Start & Goal)", padding=10)
        sec_coord.pack(fill=tk.X, pady=(0, 10))

        coord_grid = ttk.Frame(sec_coord)
        coord_grid.pack(fill=tk.X, pady=(0, 6))

        # Start (x, y)
        ttk.Label(coord_grid, text="Start (x, y):", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        self.ent_start_x = ttk.Entry(coord_grid, width=6)
        self.ent_start_x.grid(row=0, column=1, padx=3, pady=2)
        self.ent_start_y = ttk.Entry(coord_grid, width=6)
        self.ent_start_y.grid(row=0, column=2, padx=3, pady=2)

        # Goal (x, y)
        ttk.Label(coord_grid, text="Goal (x, y):", font=("Helvetica", 10, "bold")).grid(row=1, column=0, sticky="w", pady=4)
        self.ent_goal_x = ttk.Entry(coord_grid, width=6)
        self.ent_goal_x.grid(row=1, column=1, padx=3, pady=4)
        self.ent_goal_y = ttk.Entry(coord_grid, width=6)
        self.ent_goal_y.grid(row=1, column=2, padx=3, pady=4)

        btn_apply = ttk.Button(sec_coord, text="Set Custom Coordinates", command=self._apply_manual_coordinates)
        btn_apply.pack(fill=tk.X, pady=(4, 6))

        hint_lbl = ttk.Label(
            sec_coord,
            text="💡 Tip: Click on the map to place endpoints!\n• Left-Click (or button above) = Start (🟢)\n• Right-Click = Goal (🔴)",
            font=("Helvetica", 8, "italic"),
            foreground="#64748b",
            justify=tk.LEFT
        )
        hint_lbl.pack(anchor="w")

        # ==================== SECTION 3: RUN BUTTON ====================
        self.btn_run = tk.Button(
            parent,
            text="🚀 RUN ALGORITHMS",
            bg="#2563eb",
            fg="white",
            font=("Helvetica", 12, "bold"),
            relief="raised",
            cursor="hand2",
            padx=10,
            pady=8,
            command=self._start_search_thread
        )
        self.btn_run.pack(fill=tk.X, pady=(4, 12))

        # ==================== SECTION 4: ALGORITHM LEGEND ====================
        sec_legend = ttk.LabelFrame(parent, text="Algorithm Paths & Legend", padding=10)
        sec_legend.pack(fill=tk.X, pady=(0, 6))

        for key, conf in ALGO_CONFIG.items():
            row = ttk.Frame(sec_legend)
            row.pack(fill=tk.X, pady=3)

            # Color badge
            lbl_color = tk.Label(row, bg=conf["color"], width=3, height=1, relief="ridge")
            lbl_color.pack(side=tk.LEFT, padx=(0, 8))

            # Name and description
            info_frame = ttk.Frame(row)
            info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

            ttk.Label(info_frame, text=conf["name"], font=("Helvetica", 10, "bold")).pack(anchor="w")
            ttk.Label(info_frame, text=conf["desc"], font=("Helvetica", 8), foreground="#64748b").pack(anchor="w")

        tip_table = ttk.Label(
            sec_legend,
            text="💡 Double-click any row in the metrics table below to highlight that algorithm's path.",
            font=("Helvetica", 8, "italic"),
            foreground="#64748b",
            wraplength=280
        )
        tip_table.pack(anchor="w", pady=(8, 0))

    # ------------------ MAP & COORDINATES LOGIC ------------------

    def _filter_maps(self):
        sel = self.cbo_env_filter.get()
        prefix = ""
        if "ca_" in sel:
            prefix = "ca_"
        elif "dr_" in sel:
            prefix = "dr_"
        elif "ht_" in sel:
            prefix = "ht_"
        elif "lt_" in sel:
            prefix = "lt_"
        elif "w_" in sel:
            prefix = "w_"

        filtered = [p.name for p in self.map_files if p.name.startswith(prefix)] if prefix else [p.name for p in self.map_files]
        self.cbo_map["values"] = filtered
        if filtered:
            self.cbo_map.set(filtered[0])
            self._load_selected_map()

    def _select_map_by_name(self, map_name: str, scen_idx: Optional[int] = None):
        self._filter_maps()
        if map_name in self.cbo_map["values"]:
            self.cbo_map.set(map_name)
        elif self.cbo_map["values"]:
            self.cbo_map.current(0)
        self._load_selected_map(scen_idx)

    def _on_map_dropdown_select(self, event=None):
        self._load_selected_map()

    def _load_selected_map(self, target_scen_idx: Optional[int] = 0):
        map_name = self.cbo_map.get()
        if not map_name:
            return

        map_path = self.maps_dir / map_name
        if not map_path.exists():
            messagebox.showerror("Error", f"Map file not found: {map_path}")
            return

        self.current_map_name = map_name
        self.current_gmap = load_map(map_path)

        # Pre-render base PIL image
        h, w = self.current_gmap.height, self.current_gmap.width
        # Dark modern theme: Slate-200 for walkable corridors, Slate-900 for walls
        rgb = np.zeros((h, w, 3), dtype=np.uint8)
        rgb[self.current_gmap.passable] = [226, 232, 240]
        rgb[~self.current_gmap.passable] = [15, 23, 42]
        self.base_pil_image = Image.fromarray(rgb, mode="RGB")

        # Update map info
        passable_count = int(self.current_gmap.passable.sum())
        cat = classify_category(map_name)
        tier = classify_size_tier(w, h)
        self.lbl_map_info.config(
            text=f"{w}x{h} ({w*h:,} cells) | Passable: {passable_count:,} | {tier}"
        )

        # Reset results and metrics table
        self.results.clear()
        self.focused_algo = None
        self._update_metrics_table()

        # Load scenarios to pick initial start/goal and ground-truth optimal cost
        scen_path = self.scens_dir / f"{map_name}.scen"
        self.current_scenarios = []
        if scen_path.exists():
            try:
                self.current_scenarios = load_scenarios(scen_path)
            except Exception as e:
                print(f"Error loading scenarios: {e}")

        if self.current_scenarios:
            idx = target_scen_idx if (target_scen_idx is not None and target_scen_idx < len(self.current_scenarios)) else 0
            self.selected_scenario = self.current_scenarios[idx]
            self.start_coord = self.selected_scenario.start
            self.goal_coord = self.selected_scenario.goal
        else:
            self.selected_scenario = None
            self._pick_default_start_goal()

        self._sync_coord_entries()
        self._fit_to_screen()

    def _pick_default_start_goal(self):
        if not self.current_gmap:
            return
        passable_y, passable_x = np.where(self.current_gmap.passable)
        if len(passable_x) >= 2:
            self.start_coord = (int(passable_x[0]), int(passable_y[0]))
            self.goal_coord = (int(passable_x[-1]), int(passable_y[-1]))
            self._sync_coord_entries()

    def _sync_coord_entries(self):
        self.ent_start_x.delete(0, tk.END)
        self.ent_start_y.delete(0, tk.END)
        if self.start_coord:
            self.ent_start_x.insert(0, str(self.start_coord[0]))
            self.ent_start_y.insert(0, str(self.start_coord[1]))

        self.ent_goal_x.delete(0, tk.END)
        self.ent_goal_y.delete(0, tk.END)
        if self.goal_coord:
            self.ent_goal_x.insert(0, str(self.goal_coord[0]))
            self.ent_goal_y.insert(0, str(self.goal_coord[1]))

    def _apply_manual_coordinates(self):
        if not self.current_gmap:
            return
        try:
            sx = int(self.ent_start_x.get().strip())
            sy = int(self.ent_start_y.get().strip())
            gx = int(self.ent_goal_x.get().strip())
            gy = int(self.ent_goal_y.get().strip())
        except ValueError:
            messagebox.showwarning("Invalid Coordinates", "Coordinates must be integer values.")
            return

        if not self.current_gmap.in_bounds(sx, sy) or not self.current_gmap.is_passable(sx, sy):
            messagebox.showwarning("Impassable Start", f"Start ({sx}, {sy}) is out of bounds or an obstacle!")
            return
        if not self.current_gmap.in_bounds(gx, gy) or not self.current_gmap.is_passable(gx, gy):
            messagebox.showwarning("Impassable Goal", f"Goal ({gx}, {gy}) is out of bounds or an obstacle!")
            return

        self.start_coord = (sx, sy)
        self.goal_coord = (gx, gy)
        self.selected_scenario = None
        self._redraw_canvas()

    def _toggle_placement_mode(self, mode: str):
        if self.click_placement_mode.get() == mode:
            self.click_placement_mode.set("none")
            self.btn_set_start.config(text="🟢 Place Start")
            self.btn_set_goal.config(text="🔴 Place Goal")
            self.canvas.config(cursor="")
        else:
            self.click_placement_mode.set(mode)
            self.canvas.config(cursor="crosshair")
            if mode == "start":
                self.btn_set_start.config(text="👉 Click on Map!")
                self.btn_set_goal.config(text="🔴 Place Goal")
            else:
                self.btn_set_start.config(text="🟢 Place Start")
                self.btn_set_goal.config(text="👉 Click on Map!")

    # ------------------ ALGORITHM RUNNER (THREADED) ------------------

    def _start_search_thread(self):
        if self.is_running:
            return
        if not self.current_gmap or not self.start_coord or not self.goal_coord:
            messagebox.showwarning("Missing Endpoints", "Please set a valid start and goal coordinate.")
            return

        # Run all 6 benchmark algorithms
        selected_algos = list(ALGO_CONFIG.keys())

        self.is_running = True
        self.btn_run.config(text="⏳ RUNNING SEARCH...", state=tk.DISABLED, bg="#94a3b8")

        thread = threading.Thread(
            target=self._run_algorithms_worker,
            args=(selected_algos, 5.0, 100000),
            daemon=True
        )
        thread.start()

    def _run_algorithms_worker(self, algos: List[str], timeout_sec: float, max_nodes: int):
        results = {}
        optimal_cost = self.selected_scenario.optimal_length if self.selected_scenario else None

        for algo_key in algos:
            algo_fn = ALGORITHMS[algo_key]
            t0 = time.perf_counter()
            try:
                res: SearchResult = algo_fn(
                    self.current_gmap,
                    self.start_coord,
                    self.goal_coord,
                    allow_diagonal=True,
                    max_nodes=max_nodes,
                    timeout_seconds=timeout_sec
                )
            except Exception as e:
                res = SearchResult(path=None, expanded=0, generated=0, peak_frontier=0, status=f"error: {e}")
            t1 = time.perf_counter()
            time_ms = (t1 - t0) * 1000.0

            path_cost = compute_path_cost(res.path) if (res.path and len(res.path) > 1) else (0.0 if res.path else None)

            # If optimal not known from scenario, use A* / Dijkstra path cost as reference
            ref_opt = optimal_cost
            if ref_opt is None and "astar" in results and results["astar"]["path_cost"] is not None:
                ref_opt = results["astar"]["path_cost"]

            alpha = (path_cost / ref_opt) if (path_cost is not None and ref_opt and ref_opt > 0) else None

            results[algo_key] = {
                "name": ALGO_CONFIG[algo_key]["name"],
                "color": ALGO_CONFIG[algo_key]["color"],
                "status": res.status,
                "path": res.path,
                "path_cost": path_cost,
                "optimal": ref_opt,
                "alpha": alpha,
                "hops": len(res.path) if res.path else 0,
                "expanded": res.expanded,
                "generated": res.generated,
                "peak_frontier": res.peak_frontier,
                "time_ms": time_ms,
            }

        # Back to main thread
        self.root.after(0, self._on_algorithms_finished, results)

    def _on_algorithms_finished(self, new_results: Dict[str, Dict[str, Any]]):
        self.is_running = False
        self.btn_run.config(text="🚀 RUN ALGORITHMS", state=tk.NORMAL, bg="#2563eb")
        self.results.update(new_results)
        self._update_metrics_table()
        self._redraw_canvas()

    def _update_metrics_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for key, conf in ALGO_CONFIG.items():
            if key not in self.results:
                continue
            r = self.results[key]
            cost_str = f"{r['path_cost']:.3f}" if r["path_cost"] is not None else "—"
            opt_str = f"{r['optimal']:.3f}" if r["optimal"] is not None else "—"
            alpha_str = f"{r['alpha']:.3f}" if r["alpha"] is not None else "—"
            hops_str = str(r["hops"]) if r["path"] else "—"
            time_str = f"{r['time_ms']:.2f}"

            self.tree.insert(
                "",
                tk.END,
                iid=key,
                values=(
                    "●",
                    r["name"],
                    r["status"].upper(),
                    cost_str,
                    opt_str,
                    alpha_str,
                    hops_str,
                    f"{r['expanded']:,}",
                    f"{r['generated']:,}",
                    f"{r['peak_frontier']:,}",
                    time_str,
                )
            )

    def _on_table_row_double_click(self, event):
        item_id = self.tree.focus()
        if item_id in ALGO_CONFIG:
            if self.focused_algo == item_id:
                self.focused_algo = None
            else:
                self.focused_algo = item_id
            self._redraw_canvas()

    # ------------------ CANVAS DRAWING & NAVIGATION ------------------

    def _fit_to_screen(self):
        if not self.current_gmap:
            return
        cw = max(self.canvas.winfo_width(), 400)
        ch = max(self.canvas.winfo_height(), 400)
        mw, mh = self.current_gmap.width, self.current_gmap.height

        scale_x = (cw - 40) / mw
        scale_y = (ch - 40) / mh
        self.zoom = max(0.2, min(scale_x, scale_y))

        render_w = mw * self.zoom
        render_h = mh * self.zoom
        self.pan_x = (cw - render_w) / 2.0
        self.pan_y = (ch - render_h) / 2.0

        self._redraw_canvas()

    def _reset_pan(self):
        self._fit_to_screen()

    def _zoom_in(self):
        cw = self.canvas.winfo_width() / 2.0
        ch = self.canvas.winfo_height() / 2.0
        self._zoom_at(cw, ch, 1.3)

    def _zoom_out(self):
        cw = self.canvas.winfo_width() / 2.0
        ch = self.canvas.winfo_height() / 2.0
        self._zoom_at(cw, ch, 1.0 / 1.3)

    def _zoom_at(self, screen_x: float, screen_y: float, factor: float):
        old_zoom = self.zoom
        new_zoom = max(0.1, min(100.0, old_zoom * factor))
        if abs(new_zoom - old_zoom) < 1e-4:
            return
        self.pan_x = screen_x - (screen_x - self.pan_x) * (new_zoom / old_zoom)
        self.pan_y = screen_y - (screen_y - self.pan_y) * (new_zoom / old_zoom)
        self.zoom = new_zoom
        self._redraw_canvas()

    def _on_mouse_wheel(self, event):
        if event.delta:
            factor = 1.15 if event.delta > 0 else (1.0 / 1.15)
        else:
            factor = 1.0
        self._zoom_at(event.x, event.y, factor)

    def _on_canvas_resize(self):
        if self.base_pil_image and self.zoom == 1.0:
            self._fit_to_screen()
        else:
            self._redraw_canvas()

    def _on_canvas_left_click(self, event):
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

        mode = self.click_placement_mode.get()
        if mode in ("start", "goal"):
            gx, gy = self._screen_to_grid(event.x, event.y)
            if self.current_gmap and self.current_gmap.in_bounds(gx, gy):
                if self.current_gmap.is_passable(gx, gy):
                    if mode == "start":
                        self.start_coord = (gx, gy)
                    else:
                        self.goal_coord = (gx, gy)
                    self._sync_coord_entries()
                    self._toggle_placement_mode(mode)
                    self._redraw_canvas()
                else:
                    messagebox.showinfo("Obstacle", f"Cell ({gx}, {gy}) is an impassable wall/obstacle!")

    def _on_canvas_drag(self, event):
        if self.click_placement_mode.get() == "none":
            dx = event.x - self.last_mouse_x
            dy = event.y - self.last_mouse_y
            self.pan_x += dx
            self.pan_y += dy
            self.last_mouse_x = event.x
            self.last_mouse_y = event.y
            self._redraw_canvas()

    def _on_canvas_release(self, event):
        pass

    def _on_canvas_right_click(self, event):
        # Quick-set Goal on Right-Click
        gx, gy = self._screen_to_grid(event.x, event.y)
        if self.current_gmap and self.current_gmap.in_bounds(gx, gy):
            if self.current_gmap.is_passable(gx, gy):
                self.goal_coord = (gx, gy)
                self._sync_coord_entries()
                self._redraw_canvas()

    def _on_canvas_mouse_move(self, event):
        if not self.current_gmap:
            return
        gx, gy = self._screen_to_grid(event.x, event.y)
        if self.current_gmap.in_bounds(gx, gy):
            passable = self.current_gmap.is_passable(gx, gy)
            tile_char = self.current_gmap.tiles[gy, gx]
            status_txt = f"Passable ('{tile_char}')" if passable else f"Obstacle ('{tile_char}')"

            on_paths = []
            for k, res in self.results.items():
                if res.get("path") and (gx, gy) in res["path"]:
                    on_paths.append(ALGO_CONFIG[k]["name"].split()[0])
            paths_txt = f" | Paths: {', '.join(on_paths)}" if on_paths else ""

            self.lbl_coord_info.config(text=f"Coord: ({gx}, {gy}) | Tile: {status_txt}{paths_txt}")
        else:
            self.lbl_coord_info.config(text="Coord: (Out of bounds)")

    def _grid_to_screen(self, gx: float, gy: float) -> Tuple[float, float]:
        return (gx + 0.5) * self.zoom + self.pan_x, (gy + 0.5) * self.zoom + self.pan_y

    def _screen_to_grid(self, sx: float, sy: float) -> Tuple[int, int]:
        gx = int(math.floor((sx - self.pan_x) / self.zoom))
        gy = int(math.floor((sy - self.pan_y) / self.zoom))
        return gx, gy

    def _redraw_canvas(self):
        self.canvas.delete("all")
        if not self.current_gmap or not self.base_pil_image:
            return

        mw, mh = self.current_gmap.width, self.current_gmap.height
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        target_w = max(1, int(mw * self.zoom))
        target_h = max(1, int(mh * self.zoom))

        # Viewport rendering slice
        x0 = max(0, -self.pan_x)
        y0 = max(0, -self.pan_y)
        x1 = min(target_w, cw - self.pan_x)
        y1 = min(target_h, ch - self.pan_y)

        if x1 > x0 and y1 > y0:
            gx0 = max(0, int(x0 / self.zoom))
            gy0 = max(0, int(y0 / self.zoom))
            gx1 = min(mw, int(math.ceil(x1 / self.zoom)))
            gy1 = min(mh, int(math.ceil(y1 / self.zoom)))

            if gx1 > gx0 and gy1 > gy0:
                crop = self.base_pil_image.crop((gx0, gy0, gx1, gy1))
                crop_w = int((gx1 - gx0) * self.zoom)
                crop_h = int((gy1 - gy0) * self.zoom)
                if crop_w > 0 and crop_h > 0:
                    scaled_crop = crop.resize((crop_w, crop_h), Image.Resampling.NEAREST)
                    self.photo_image = ImageTk.PhotoImage(scaled_crop)
                    self.canvas.create_image(
                        gx0 * self.zoom + self.pan_x,
                        gy0 * self.zoom + self.pan_y,
                        anchor="nw",
                        image=self.photo_image
                    )

        # Draw subtle grid lines if zoomed in
        if self.zoom >= 14:
            line_color = "#334155"
            for gx in range(mw + 1):
                sx = gx * self.zoom + self.pan_x
                self.canvas.create_line(sx, self.pan_y, sx, mh * self.zoom + self.pan_y, fill=line_color, width=1)
            for gy in range(mh + 1):
                sy = gy * self.zoom + self.pan_y
                self.canvas.create_line(self.pan_x, sy, mw * self.zoom + self.pan_x, sy, fill=line_color, width=1)

        # Draw algorithm paths
        self._draw_algorithm_paths()

        # Draw Start and Goal markers
        self._draw_endpoints()

    def _draw_algorithm_paths(self):
        active_algos = [k for k in ALGO_CONFIG if k in self.results and self.results[k].get("path")]
        num_active = len(active_algos)

        for idx, k in enumerate(active_algos):
            r = self.results[k]
            path = r["path"]
            if not path or len(path) < 2:
                continue

            screen_pts = [self._grid_to_screen(x, y) for x, y in path]

            # Ribbon offset so overlapping paths are clearly visible
            if num_active > 1 and not self.focused_algo:
                spread_px = 3.2
                offset_factor = (idx - (num_active - 1) / 2.0)
                offset_px = offset_factor * spread_px
                draw_pts = compute_perpendicular_offset_path(screen_pts, offset_px)
            else:
                draw_pts = screen_pts

            flat_coords = [c for pt in draw_pts for c in pt]
            color = ALGO_CONFIG[k]["color"]

            if self.focused_algo:
                if k == self.focused_algo:
                    line_w = 5.0
                else:
                    line_w = 1.0
            else:
                line_w = 3.0

            self.canvas.create_line(
                flat_coords,
                fill=color,
                width=line_w,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
                tags="path_line"
            )

    def _draw_endpoints(self):
        r = max(6.0, min(22.0, self.zoom * 0.45))

        # Start Marker (Green circle with 'S')
        if self.start_coord:
            sx, sy = self._grid_to_screen(self.start_coord[0], self.start_coord[1])
            self.canvas.create_oval(
                sx - r - 2, sy - r - 2, sx + r + 2, sy + r + 2,
                fill="#065f46", outline="#34d399", width=2
            )
            self.canvas.create_oval(
                sx - r, sy - r, sx + r, sy + r,
                fill="#10b981", outline="#ffffff", width=2
            )
            font_size = max(8, int(r * 1.0))
            self.canvas.create_text(
                sx, sy, text="S", fill="#ffffff", font=("Helvetica", font_size, "bold")
            )

        # Goal Marker (Red circle with 'G')
        if self.goal_coord:
            gx, gy = self._grid_to_screen(self.goal_coord[0], self.goal_coord[1])
            self.canvas.create_oval(
                gx - r - 2, gy - r - 2, gx + r + 2, gy + r + 2,
                fill="#7f1d1d", outline="#f87171", width=2
            )
            self.canvas.create_oval(
                gx - r, gy - r, gx + r, gy + r,
                fill="#ef4444", outline="#ffffff", width=2
            )
            font_size = max(8, int(r * 1.0))
            self.canvas.create_text(
                gx, gy, text="G", fill="#ffffff", font=("Helvetica", font_size, "bold")
            )


def main():
    parser = argparse.ArgumentParser(description="Pathfinding Algorithm Visualizer GUI")
    parser.add_argument("--map", type=str, default=None, help="Initial map filename to load")
    parser.add_argument("--scen", type=int, default=None, help="Initial scenario index to load")
    args = parser.parse_args()

    root = tk.Tk()
    app = PathfindingVisualizerApp(root, initial_map=args.map, initial_scen=args.scen)
    root.mainloop()


if __name__ == "__main__":
    main()
