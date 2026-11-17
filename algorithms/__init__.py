"""
Pathfinding algorithms package.
"""

from .base import SearchResult, Coordinate, compute_path_cost, validate_path, octile_distance
from .bfs import bfs
from .dfs import dfs
from .dijkstra import dijkstra
from .a_star import a_star
from .gbfs import gbfs
from .jump_point import jump_point_search

ALGORITHMS = {
    "bfs": bfs,
    "dfs": dfs,
    "dijkstra": dijkstra,
    "gbfs": gbfs,
    "astar": a_star,
    "jps": jump_point_search,
}

__all__ = [
    "SearchResult",
    "Coordinate",
    "compute_path_cost",
    "validate_path",
    "bfs",
    "dfs",
    "dijkstra",
    "a_star",
    "gbfs",
    "jump_point_search",
    "ALGORITHMS",
]
