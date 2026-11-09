"""
Unit and integration tests for Breadth-First Search (BFS).
"""

import unittest
from pathlib import Path
import numpy as np

from utils.map_loader import GridMap, load_map
from utils.scenario_loader import load_scenarios
from algorithms.base import validate_path, compute_path_cost, SQRT2
from algorithms.bfs import bfs

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class MockGrid:
    """A lightweight mock grid map for testing corner cutting and edge cases."""
    def __init__(self, width: int, height: int, blocked: set):
        self.width = width
        self.height = height
        self.blocked = blocked

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_passable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and (x, y) not in self.blocked


class TestBFS(unittest.TestCase):

    def test_start_equals_goal(self):
        grid = MockGrid(5, 5, set())
        result = bfs(grid, (2, 2), (2, 2))
        self.assertTrue(result.found)
        self.assertEqual(result.path, [(2, 2)])
        self.assertEqual(result.path_cost, 0.0)
        self.assertEqual(result.nodes_explored, 0)

    def test_impassable_start_or_goal(self):
        grid = MockGrid(5, 5, {(0, 0), (4, 4)})
        res1 = bfs(grid, (0, 0), (2, 2))
        self.assertFalse(res1.found)
        self.assertIn("impassable", res1.error_message)

        res2 = bfs(grid, (2, 2), (4, 4))
        self.assertFalse(res2.found)
        self.assertIn("impassable", res2.error_message)

    def test_unreachable_goal(self):
        # Enclose (4, 4) with walls
        walls = {(3, 4), (4, 3), (3, 3)}
        grid = MockGrid(5, 5, walls)
        result = bfs(grid, (0, 0), (4, 4))
        self.assertFalse(result.found)
        self.assertEqual(len(result.path), 0)

    def test_corner_cutting_prevention(self):
        """
        Verify that diagonal movement between (0,0) and (1,1) is disallowed
        if (1,0) and (0,1) are obstacles.
        """
        walls = {(1, 0), (0, 1)}
        grid = MockGrid(3, 3, walls)
        result = bfs(grid, (0, 0), (1, 1), allow_diagonal=True)
        # Cannot cut corner through walls at (1,0) and (0,1)
        self.assertFalse(result.found)

    def test_node_limit(self):
        grid = MockGrid(50, 50, set())
        result = bfs(grid, (0, 0), (49, 49), max_nodes=10)
        self.assertFalse(result.found)
        self.assertIn("Node expansion limit reached", result.error_message)
        self.assertLessEqual(result.nodes_explored, 15)

    def test_real_benchmark_map(self):
        map_path = PROJECT_ROOT / "benchmarks" / "maps" / "ca_cave.map"
        scen_path = PROJECT_ROOT / "benchmarks" / "scenarios" / "ca_cave.map.scen"

        gmap = load_map(map_path)
        scens = load_scenarios(scen_path)
        s0 = scens[0]

        result = bfs(gmap, s0.start, s0.goal)
        self.assertTrue(result.found)
        is_valid, err = validate_path(gmap, result.path, s0.start, s0.goal)
        self.assertTrue(is_valid, f"Validation failed: {err}")
        # Optimal cost comparison
        self.assertAlmostEqual(result.path_cost, s0.optimal_length, places=3)


if __name__ == "__main__":
    unittest.main()
