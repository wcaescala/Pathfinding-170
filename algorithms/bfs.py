"""
Breadth-First Search (BFS) implementation for grid pathfinding.
Implemented entirely using standard Python without any high-level or external graph libraries.
"""

from collections import deque
from time import perf_counter
from typing import List, Tuple, Optional, Any, Dict, Set
from .base import SearchResult, Coordinate, compute_path_cost, SQRT2


def bfs(
    grid_map: Any,
    start: Coordinate,
    goal: Coordinate,
    allow_diagonal: bool = True,
    max_nodes: Optional[int] = None,
    timeout_seconds: Optional[float] = None
) -> SearchResult:
    """
    Executes Breadth-First Search (BFS) on a 2D grid map from start to goal.

    BFS explores uniformly outward layer-by-layer using a FIFO queue.
    In unweighted graphs or uniform-cost grid steps, BFS guarantees finding
    the minimum-hop path. Note that under octile movement (where diagonals cost sqrt(2)),
    BFS minimizes hop count, which can sometimes produce slight sub-optimality in total
    octile distance compared to algorithms that account for edge weights (such as Dijkstra or A*).

    Parameters:
        grid_map: An object providing `in_bounds(x, y)`, `is_passable(x, y)`,
                  and optionally `neighbors(x, y)`.
        start: (x, y) start coordinate.
        goal: (x, y) target goal coordinate.
        allow_diagonal: If True, uses 8-neighbor movement without corner cutting;
                        otherwise 4-cardinal movement.
        max_nodes: Maximum number of node expansions permitted before aborting.
        timeout_seconds: Maximum wall-clock time in seconds before aborting.

    Returns:
        SearchResult containing path, expanded, generated, peak_frontier, and status.
    """
    start_time = perf_counter()

    # Trivial validation
    sx, sy = start
    gx, gy = goal

    if not grid_map.in_bounds(sx, sy) or not grid_map.is_passable(sx, sy):
        return SearchResult(
            path=None,
            expanded=0,
            generated=0,
            peak_frontier=0,
            status="no_path"
        )

    if not grid_map.in_bounds(gx, gy) or not grid_map.is_passable(gx, gy):
        return SearchResult(
            path=None,
            expanded=0,
            generated=0,
            peak_frontier=0,
            status="no_path"
        )

    # Edge case: start is already goal
    if start == goal:
        return SearchResult(
            path=[start],
            expanded=0,
            generated=1,
            peak_frontier=1,
            status="ok"
        )

    # Data structures (Pure Python standard library)
    frontier: deque[Coordinate] = deque([start])
    visited: Set[Coordinate] = {start}
    parent: Dict[Coordinate, Coordinate] = {}

    nodes_explored = 0
    nodes_generated = 1
    max_frontier_size = 1
    path_found = False

    # Octile move offsets: 4 cardinal followed by 4 diagonal
    if allow_diagonal:
        moves = (
            (0, -1), (0, 1), (-1, 0), (1, 0),
            (-1, -1), (1, -1), (-1, 1), (1, 1)
        )
    else:
        moves = ((0, -1), (0, 1), (-1, 0), (1, 0))

    while frontier:
        # Check timeout limit
        if timeout_seconds is not None:
            if (perf_counter() - start_time) >= timeout_seconds:
                return SearchResult(
                    path=None,
                    expanded=nodes_explored,
                    generated=nodes_generated,
                    peak_frontier=max_frontier_size,
                    status="timeout"
                )

        # Check node exploration limit
        if max_nodes is not None and nodes_explored >= max_nodes:
            return SearchResult(
                path=None,
                expanded=nodes_explored,
                generated=nodes_generated,
                peak_frontier=max_frontier_size,
                status="node_limit"
            )

        current = frontier.popleft()
        nodes_explored += 1

        if current == goal:
            path_found = True
            break

        cx, cy = current

        # Generate successors
        # If grid_map has a native neighbors generator matching our diagonal mode, use it:
        if allow_diagonal and hasattr(grid_map, "neighbors"):
            neighbor_iter = (pos for pos, _ in grid_map.neighbors(cx, cy))
        else:
            # Explicit standard neighbor generation with corner-cutting prevention
            def _gen_neighbors():
                for dx, dy in moves:
                    nx, ny = cx + dx, cy + dy
                    if not grid_map.in_bounds(nx, ny) or not grid_map.is_passable(nx, ny):
                        continue
                    # For diagonal moves, enforce no corner cutting:
                    if dx != 0 and dy != 0:
                        if not (grid_map.is_passable(cx + dx, cy) and grid_map.is_passable(cx, cy + dy)):
                            continue
                    yield (nx, ny)
            neighbor_iter = _gen_neighbors()

        for neighbor in neighbor_iter:
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                frontier.append(neighbor)
                nodes_generated += 1

                # Early goal check optimization for BFS (unweighted)
                if neighbor == goal:
                    nodes_explored += 1
                    path_found = True
                    break

        if path_found:
            break

        if len(frontier) > max_frontier_size:
            max_frontier_size = len(frontier)

    if not path_found:
        return SearchResult(
            path=None,
            expanded=nodes_explored,
            generated=nodes_generated,
            peak_frontier=max_frontier_size,
            status="no_path"
        )

    # Reconstruct path from parent pointers
    path: List[Coordinate] = []
    curr: Optional[Coordinate] = goal
    while curr is not None:
        path.append(curr)
        curr = parent.get(curr)
    path.reverse()

    return SearchResult(
        path=path,
        expanded=nodes_explored,
        generated=nodes_generated,
        peak_frontier=max_frontier_size,
        status="ok"
    )
