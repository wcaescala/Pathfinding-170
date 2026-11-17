"""
Base definitions and utilities for pathfinding algorithms.
No high-level or external graph libraries are used.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Any
import math

SQRT2 = math.sqrt(2)

# Coordinate type alias: (x, y)
Coordinate = Tuple[int, int]


@dataclass
class SearchResult:
    """
    Represents the outcome and performance metrics of a pathfinding search.
    Standardized interface for all algorithms in the benchmark pipeline.
    """
    path: Optional[List[Coordinate]]  # None if not found
    expanded: int                     # nodes popped and evaluated
    generated: int                    # successors pushed to the frontier
    peak_frontier: int                # max frontier size
    status: str                       # "ok" | "timeout" | "node_limit" | "no_path"


def compute_path_cost(path: List[Coordinate]) -> float:
    """
    Computes the total octile cost of a grid path.
    Cardinal movement costs 1.0; diagonal movement costs sqrt(2).
    """
    if len(path) < 2:
        return 0.0

    total_cost = 0.0
    for i in range(len(path) - 1):
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)

        if dx > 1 or dy > 1 or (dx == 0 and dy == 0):
            raise ValueError(f"Illegal step in path from ({x1}, {y1}) to ({x2}, {y2})")

        if dx == 1 and dy == 1:
            total_cost += SQRT2
        else:
            total_cost += 1.0

    return total_cost


def octile_distance(a: Coordinate, b: Coordinate) -> float:
    """
    Computes the octile (heuristic) distance between two coordinates.
    Made for 8-connected grids with cardinal=1.0 and diagonal=sqrt(2).
    """
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])

    return (dx + dy) + (SQRT2 - 2.0) * min(dx, dy)


def validate_path(
    grid_map: Any,
    path: List[Coordinate],
    start: Coordinate,
    goal: Coordinate
) -> Tuple[bool, Optional[str]]:
    """
    Validates that a path is continuous, collision-free, respects bounds,
    does not cut corners diagonally, and connects start to goal.

    Returns (is_valid, error_reason).
    """
    if not path:
        return False, "Path is empty"

    if path[0] != start:
        return False, f"Path start {path[0]} does not match expected start {start}"

    if path[-1] != goal:
        return False, f"Path goal {path[-1]} does not match expected goal {goal}"

    for idx, (x, y) in enumerate(path):
        if not grid_map.in_bounds(x, y):
            return False, f"Node at index {idx} ({x}, {y}) is out of bounds"
        if not grid_map.is_passable(x, y):
            return False, f"Node at index {idx} ({x}, {y}) is impassable/obstacle"

    for i in range(len(path) - 1):
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        dx = x2 - x1
        dy = y2 - y1

        if abs(dx) > 1 or abs(dy) > 1 or (dx == 0 and dy == 0):
            return False, f"Discontinuous step between ({x1}, {y1}) and ({x2}, {y2})"

        # Corner cutting check for diagonal moves
        if dx != 0 and dy != 0:
            if not grid_map.is_passable(x1 + dx, y1) or not grid_map.is_passable(x1, y1 + dy):
                return False, (
                    f"Diagonal step from ({x1}, {y1}) to ({x2}, {y2}) cuts corners "
                    f"where intermediate cardinals are blocked"
                )

    return True, None


def compute_path_cost(path: List[Coordinate]) -> float:
    """
    Computes the total octile cost of a grid path.
    Cardinal movement costs 1.0; diagonal movement costs sqrt(2).
    """
    if len(path) < 2:
        return 0.0

    total_cost = 0.0
    for i in range(len(path) - 1):
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)

        if dx > 1 or dy > 1 or (dx == 0 and dy == 0):
            raise ValueError(f"Illegal step in path from ({x1}, {y1}) to ({x2}, {y2})")

        if dx == 1 and dy == 1:
            total_cost += SQRT2
        else:
            total_cost += 1.0

    return total_cost

def octile_distance(a: Coordinate, b: Coordinate) -> float:
    """
    Computes the octile (heuristic) distance between two coordinates.
    Made for 8-connected grids with cardinal=1.0 and diagonal=sqrt(2).
    """
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    
    return (dx + dy) + (SQRT2 - 2.0) * min(dx, dy)

def validate_path(
    grid_map: Any,
    path: List[Coordinate],
    start: Coordinate,
    goal: Coordinate
) -> Tuple[bool, Optional[str]]:
    """
    Validates that a path is continuous, collision-free, respects bounds,
    does not cut corners diagonally, and connects start to goal.
    
    Returns (is_valid, error_reason).
    """
    if not path:
        return False, "Path is empty"

    if path[0] != start:
        return False, f"Path start {path[0]} does not match expected start {start}"

    if path[-1] != goal:
        return False, f"Path goal {path[-1]} does not match expected goal {goal}"

    for idx, (x, y) in enumerate(path):
        if not grid_map.in_bounds(x, y):
            return False, f"Node at index {idx} ({x}, {y}) is out of bounds"
        if not grid_map.is_passable(x, y):
            return False, f"Node at index {idx} ({x}, {y}) is impassable/obstacle"

    for i in range(len(path) - 1):
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        dx = x2 - x1
        dy = y2 - y1

        if abs(dx) > 1 or abs(dy) > 1 or (dx == 0 and dy == 0):
            return False, f"Discontinuous step between ({x1}, {y1}) and ({x2}, {y2})"

        # Corner cutting check for diagonal moves
        if dx != 0 and dy != 0:
            if not grid_map.is_passable(x1 + dx, y1) or not grid_map.is_passable(x1, y1 + dy):
                return False, (
                    f"Diagonal step from ({x1}, {y1}) to ({x2}, {y2}) cuts corners "
                    f"where intermediate cardinals are blocked"
                )

    return True, None
