"""
Unit and integration tests for the Pathfinding Algorithm Visualizer GUI.
"""

import unittest
from pathlib import Path
import tkinter as tk

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gui import PathfindingVisualizerApp, compute_perpendicular_offset_path, ALGO_CONFIG
from utils.map_loader import load_map


class TestPathfindingGUI(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_gui_initialization(self):
        app = PathfindingVisualizerApp(self.root, initial_map="ht_store.map")
        self.assertEqual(app.current_map_name, "ht_store.map")
        self.assertIsNotNone(app.current_gmap)
        self.assertIsNotNone(app.start_coord)
        self.assertIsNotNone(app.goal_coord)
        self.assertGreater(len(app.current_scenarios), 0)

    def test_ribbon_offset_math(self):
        path = [(0, 0), (1, 0), (2, 0), (3, 0)]
        offset_path = compute_perpendicular_offset_path(path, 2.0)
        self.assertEqual(len(offset_path), len(path))
        # Tangent is along x (+1, 0), perpendicular is (-0, +1) -> y should be offset by 2.0
        for (_, orig_y), (_, off_y) in zip(path, offset_path):
            self.assertAlmostEqual(off_y, orig_y + 2.0, places=3)

    def test_run_algorithms_in_gui(self):
        app = PathfindingVisualizerApp(self.root, initial_map="ht_store.map", initial_scen=0)
        app._run_algorithms_worker(["astar", "bfs", "dijkstra"], timeout_sec=2.0, max_nodes=50000)
        self.root.update()

        self.assertIn("astar", app.results)
        self.assertIn("bfs", app.results)
        self.assertIn("dijkstra", app.results)

        for key in ["astar", "bfs", "dijkstra"]:
            res = app.results[key]
            self.assertEqual(res["status"], "ok")
            self.assertIsNotNone(res["path"])
            self.assertGreater(len(res["path"]), 0)
            self.assertAlmostEqual(res["path_cost"], 3.8284, places=3)


if __name__ == "__main__":
    unittest.main()

