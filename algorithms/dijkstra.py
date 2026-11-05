"""
Dijkstra's Algorithm implementation for grid pathfinding.
Implemented entirely using standard Python without any high-level or external graph libraries.
"""

import heapq
from time import perf_counter
from typing import List, Tuple, Optional, Any, Dict, Set
from .base import SearchResult, Coordinate, compute_path_cost


def dijkstra(
	grid_map: Any,
	start: Coordinate,
	goal: Coordinate,
	allow_diagonal: bool = True,
	max_nodes: Optional[int] = None,
	timeout_seconds: Optional[float] = None
) -> SearchResult:
	"""
    Executes Dijkstra's Algorithm on a 2D grid map from start to goal.

    Dijkstra explores nodes in order of their accumulated path cost g(n) from the start.
    
    Unlike BFS, Dijkstra considers edge weights (cardinal step = 1.0, diagonal step = sqrt(2)),
    guaranteeing a cost-optimal path suited on an 8-connected grid.

    Parameters:
        grid_map: An object providing `in_bounds(x, y)`, `is_passable(x, y)`,
                  and `neighbors(x, y)`.
        start: (x, y) start coordinate.
        goal: (x, y) target goal coordinate.
        allow_diagonal: Passed for consistency (movement behavior managed by grid_map).
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
			algorithm="Dijkstra",
			found=False,
			execution_time_ms=elapsed_ms,
			error_message=f"Start position {start} is out of bounds or impassable."
		)

	if not grid_map.in_bounds(gx, gy) or not grid_map.is_passable(gx, gy):
		elapsed_ms = (perf_counter() - start_time) * 1000.0
		return SearchResult(
			algorithm="Dijkstra",
			found=False,
			execution_time_ms=elapsed_ms,
			error_message=f"Goal position {goal} is out of bounds or impassable."
		)

	if start == goal:
		elapsed_ms = (perf_counter() - start_time) * 1000.0
		return SearchResult(
			algorithm="Dijkstra",
			found=True,
			path=[start],
			path_cost=0.0,
			nodes_explored=0,
			nodes_generated=1,
			execution_time_ms=elapsed_ms,
			max_frontier_size=1
		)

	# Min-Heap: stores (path_cost, coordinates)
	min_heap: List[Tuple[float, Coordinate]] = [(0.0, start)]
	# Shortest path distance between start to each coordinates
	opt_path: Dict[Coordinate, float] = {start: 0.0}
	visited: Set[Coordinate] = set()
	parent: Dict[Coordinate, Coordinate] = {}

	nodes_explored = 0
	nodes_generated = 1
	max_frontier_size = 1
	path_found = False

	while min_heap:
		# Check timeout limit
		if timeout_seconds is not None:
			if (perf_counter() - start_time) >= timeout_seconds:
				elapsed_ms = (perf_counter() - start_time) * 1000.0
				return SearchResult(
					algorithm="Dijkstra",
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
				algorithm="Dijkstra",
				found=False,
				nodes_explored=nodes_explored,
				nodes_generated=nodes_generated,
				execution_time_ms=elapsed_ms,
				max_frontier_size=max_frontier_size,
				error_message=f"Node expansion limit reached ({max_nodes} nodes)"
			)

		# Pop the smallest(root) path_cost from the min_heap
		current_cost, current = heapq.heappop(min_heap)

		if current in visited:
			continue

		visited.add(current)
		nodes_explored += 1

		if current == goal:
			path_found = True
			break

		cx, cy = current

		# Let grid_map.neighbors handle valid adjacent moves and cost
		for (nx, ny), step_cost in grid_map.neighbors(cx, cy):
			neighbor = (nx, ny)
			if neighbor in visited:
				continue

			comp_path = current_cost + step_cost

			# Update if new computed path is a better path
			if comp_path < opt_path.get(neighbor, float("inf")):
				opt_path[neighbor] = comp_path
				parent[neighbor] = current
				heapq.heappush(min_heap, (comp_path, neighbor))
				nodes_generated += 1

		if len(min_heap) > max_frontier_size:
			max_frontier_size = len(min_heap)

	elapsed_ms = (perf_counter() - start_time) * 1000.0

	if not path_found:
		return SearchResult(
			algorithm="Dijkstra",
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
		algorithm="Dijkstra",
		found=True,
		path=path,
		path_cost=path_cost,
		nodes_explored=nodes_explored,
		nodes_generated=nodes_generated,
		execution_time_ms=elapsed_ms,
		max_frontier_size=max_frontier_size
	)

