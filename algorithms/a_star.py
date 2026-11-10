"""
A* Search implementation for grid pathfinding.
Implemented entirely using standard Python without any high-level or external graph libraries.
Uses Octile Distance as its heuristic function.
"""

import heapq
from time import perf_counter
from typing import List, Tuple, Optional, Any, Dict, Set
from .base import SearchResult, Coordinate, compute_path_cost, octile_distance


def a_star(
	grid_map: Any,
	start: Coordinate,
	goal: Coordinate,
	allow_diagonal: bool = True,
	max_nodes: Optional[int] = None,
	timeout_seconds: Optional[float] = None
) -> SearchResult:
	"""
    Executes A* Search on a 2D grid map from start to goal.

    A* evaluates nodes using f(n) = g(n) + h(n), where g(n) is path cost from the start.
    and h(n) is the estimated octile distance to goal.

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

	if start == goal:
		return SearchResult(
			path=[start],
			expanded=0,
			generated=1,
			peak_frontier=1,
			status="ok"
		)

	oct_dist = octile_distance(start, goal)
	# Min-Heap: stores (f_cost, oct_dist_cost, coordinates)
	min_heap: List[Tuple[float, float, Coordinate]] = [(oct_dist, oct_dist, start)]
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

		# Pop the smallest(root) f_cost from the min_heap
		f_cost, heuristic_cost, current = heapq.heappop(min_heap)

		if current in visited:
			continue

		visited.add(current)
		nodes_explored += 1

		if current == goal:
			path_found = True
			break

		cx, cy = current
		current_cost = opt_path[current]

		# Let grid_map.neighbors handle valid adjacent moves and cost
		for (nx, ny), step_cost in grid_map.neighbors(cx, cy):
			neighbor = (nx, ny)
			if neighbor in visited:
				continue

			comp_path = current_cost + step_cost

			# Update if new computed path is a better path
			if comp_path < opt_path.get(neighbor, float("inf")):
				# update shortest path cost g(n)
				opt_path[neighbor] = comp_path
				parent[neighbor] = current

				# then the heuristic and f(n)
				neighbor_h = octile_distance(neighbor, goal)
				neighbor_f = comp_path + neighbor_h

				heapq.heappush(min_heap, (neighbor_f, neighbor_h, neighbor))
				nodes_generated += 1

		if len(min_heap) > max_frontier_size:
			max_frontier_size = len(min_heap)

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

