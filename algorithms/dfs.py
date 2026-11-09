"""
Depth-First Search (DFS) implementation for grid pathfinding.
Implemented entirely using standard Python without any high-level or external graph libraries.
"""

from time import perf_counter
from typing import List, Tuple, Optional, Any, Dict, Set
from .base import SearchResult, Coordinate, compute_path_cost


def dfs(
    grid_map: Any,
    start: Coordinate,
    goal: Coordinate,
    allow_diagonal: bool = True,
    max_nodes: Optional[int] = None,
    timeout_seconds: Optional[float] = None
) -> SearchResult:
    """
    Executes Depth-First Search (DFS) on a 2D grid map from start to goal.

    DFS explores deeply along each branch before backtracking using a LIFO stack.
    To avoid recursion limits and stack overflow in Python (default limit ~1000), 
    this algorithm is implemented ITERATIVELY with an explicit Python list stack.
    
    DFS does not guarantee the shortest path or optimal cost, often resulting in 
    meandering, winding paths. Cycle prevention is enforced via a visited set.

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
        SearchResult containing path, cost, nodes explored, time, and status.
    """
    start_time = perf_counter()

    sx, sy = start
    gx, gy = goal

    if not grid_map.in_bounds(sx, sy) or not grid_map.is_passable(sx, sy):
        elapsed_ms = (perf_counter() - start_time) * 1000.0
        return SearchResult(
            algorithm="DFS",
            found=False,
            execution_time_ms=elapsed_ms,
            error_message=f"Start position {start} is out of bounds or impassable."
        )

    if not grid_map.in_bounds(gx, gy) or not grid_map.is_passable(gx, gy):
        elapsed_ms = (perf_counter() - start_time) * 1000.0
        return SearchResult(
            algorithm="DFS",
            found=False,
            execution_time_ms=elapsed_ms,
            error_message=f"Goal position {goal} is out of bounds or impassable."
        )

    if start == goal:
        elapsed_ms = (perf_counter() - start_time) * 1000.0
        return SearchResult(
            algorithm="DFS",
            found=True,
            path=[start],
            path_cost=0.0,
            nodes_explored=0,
            nodes_generated=1,
            execution_time_ms=elapsed_ms,
            max_frontier_size=1
        )

    # LIFO stack (pure Python list)
    stack: List[Coordinate] = [start]
    visited: Set[Coordinate] = {start}
    parent: Dict[Coordinate, Coordinate] = {}

    nodes_explored = 0
    nodes_generated = 1
    max_frontier_size = 1
    path_found = False

    # Octile moves: cardinal then diagonal
    if allow_diagonal:
        moves = (
            (0, -1), (0, 1), (-1, 0), (1, 0),
            (-1, -1), (1, -1), (-1, 1), (1, 1)
        )
    else:
        moves = ((0, -1), (0, 1), (-1, 0), (1, 0))

    while stack:
        # Check timeout limit
        if timeout_seconds is not None:
            if (perf_counter() - start_time) >= timeout_seconds:
                elapsed_ms = (perf_counter() - start_time) * 1000.0
                return SearchResult(
                    algorithm="DFS",
                    found=False,
                    nodes_explored=nodes_explored,
                    nodes_generated=nodes_generated,
                    execution_time_ms=elapsed_ms,
                    max_frontier_size=max_frontier_size,
                    error_message=f"Timeout reached ({timeout_seconds:.2f}s)"
                )

        # Check node exploration limit
        if max_nodes is not None and nodes_explored >= max_nodes:
            elapsed_ms = (perf_counter() - start_time) * 1000.0
            return SearchResult(
                algorithm="DFS",
                found=False,
                nodes_explored=nodes_explored,
                nodes_generated=nodes_generated,
                execution_time_ms=elapsed_ms,
                max_frontier_size=max_frontier_size,
                error_message=f"Node expansion limit reached ({max_nodes} nodes)"
            )

        current = stack.pop()
        nodes_explored += 1

        if current == goal:
            path_found = True
            break

        cx, cy = current

        # Generate successors
        if allow_diagonal and hasattr(grid_map, "neighbors"):
            raw_neighbors = [pos for pos, _ in grid_map.neighbors(cx, cy)]
        else:
            raw_neighbors = []
            for dx, dy in moves:
                nx, ny = cx + dx, cy + dy
                if not grid_map.in_bounds(nx, ny) or not grid_map.is_passable(nx, ny):
                    continue
                if dx != 0 and dy != 0:
                    if not (grid_map.is_passable(cx + dx, cy) and grid_map.is_passable(cx, cy + dy)):
                        continue
                raw_neighbors.append((nx, ny))

        # Push unvisited neighbors onto the stack.
        # Iterating in reverse ensures the first generated neighbor is popped first.
        for neighbor in reversed(raw_neighbors):
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                stack.append(neighbor)
                nodes_generated += 1

                # Early exit check if neighbor is goal
                if neighbor == goal:
                    nodes_explored += 1
                    path_found = True
                    break

        if path_found:
            break

        if len(stack) > max_frontier_size:
            max_frontier_size = len(stack)

    elapsed_ms = (perf_counter() - start_time) * 1000.0

    if not path_found:
        return SearchResult(
            algorithm="DFS",
            found=False,
            nodes_explored=nodes_explored,
            nodes_generated=nodes_generated,
            execution_time_ms=elapsed_ms,
            max_frontier_size=max_frontier_size,
            error_message="No path exists between start and goal."
        )

    # Reconstruct path from parent pointers
    path: List[Coordinate] = []
    curr: Optional[Coordinate] = goal
    while curr is not None:
        path.append(curr)
        curr = parent.get(curr)
    path.reverse()

    path_cost = compute_path_cost(path)

    return SearchResult(
        algorithm="DFS",
        found=True,
        path=path,
        path_cost=path_cost,
        nodes_explored=nodes_explored,
        nodes_generated=nodes_generated,
        execution_time_ms=elapsed_ms,
        max_frontier_size=max_frontier_size
    )
