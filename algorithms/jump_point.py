"""
Jump Point Search (JPS) implementation for grid pathfinding.
Implemented entirely using standard Python without any high-level or external graph libraries.
Uses Octile Distance as its heuristic function.

Assumptions (standard JPS):
	- Uniform-cost grid: orthogonal step = 1, diagonal step = sqrt(2).
	- 8-connected movement with no corner cutting: a diagonal step is only legal when
	  both adjacent orthogonal cells are passable.
	- Optimality is only guaranteed when grid_map follows the same movement rules.
"""

import heapq
from time import perf_counter
from typing import List, Tuple, Optional, Any, Dict, Set
from .base import SearchResult, Coordinate, octile_distance
from .a_star import a_star


def jump_point_search(
	grid_map: Any,
	start: Coordinate,
	goal: Coordinate,
	allow_diagonal: bool = True,
	max_nodes: Optional[int] = None,
	timeout_seconds: Optional[float] = None
) -> SearchResult:
	"""
	Executes Jump Point Search on a 2D grid map from start to goal.

	JPS is A* with symmetry pruning: instead of pushing every neighbor, it "jumps" along
	straight and diagonal lines until it finds a jump point (the goal, or a cell with a
	forced neighbor) and only those cells enter the open list. The search still uses
	f(n) = g(n) + h(n) with the octile distance as h(n).

	Parameters:
		grid_map: An object providing `in_bounds(x, y)` and `is_passable(x, y)`.
		start: (x, y) start coordinate.
		goal: (x, y) target goal coordinate.
		allow_diagonal: JPS requires 8-connected movement. If False, this falls back
		                to plain A* with diagonals disabled.
		max_nodes: Maximum number of jump point expansions permitted before aborting.
		timeout_seconds: Maximum wall-clock time in seconds before aborting.

	Returns:
		SearchResult containing the full (interpolated) path, cost, jump points
		expanded, time, and status.
	"""
	if not allow_diagonal:
		# JPS pruning rules assume 8-connected movement
		return a_star(grid_map, start, goal, False, max_nodes, timeout_seconds)

	start_time = perf_counter()

	sx, sy = start
	gx, gy = goal

	if not grid_map.in_bounds(sx, sy) or not grid_map.is_passable(sx, sy):
		elapsed_ms = (perf_counter() - start_time) * 1000.0
		return SearchResult(
			algorithm="JPS",
			found=False,
			execution_time_ms=elapsed_ms,
			error_message=f"Start position {start} is out of bounds or impassable."
		)

	if not grid_map.in_bounds(gx, gy) or not grid_map.is_passable(gx, gy):
		elapsed_ms = (perf_counter() - start_time) * 1000.0
		return SearchResult(
			algorithm="JPS",
			found=False,
			execution_time_ms=elapsed_ms,
			error_message=f"Goal position {goal} is out of bounds or impassable."
		)

	if start == goal:
		elapsed_ms = (perf_counter() - start_time) * 1000.0
		return SearchResult(
			algorithm="JPS",
			found=True,
			path=[start],
			path_cost=0.0,
			nodes_explored=0,
			nodes_generated=1,
			execution_time_ms=elapsed_ms,
			max_frontier_size=1
		)

	in_bounds = grid_map.in_bounds
	is_passable = grid_map.is_passable

	def walkable(x: int, y: int) -> bool:
		return in_bounds(x, y) and is_passable(x, y)

	def jump(x: int, y: int, dx: int, dy: int) -> Optional[Coordinate]:
		"""
		Scans from (x, y) in direction (dx, dy) and returns the first jump point,
		or None if the scan hits an obstacle first. Iterative along the scan line;
		diagonal scans spawn straight scans (at most one level of nesting).
		"""
		while True:
			nx, ny = x + dx, y + dy

			if not walkable(nx, ny):
				return None

			# No corner cutting on diagonal steps
			if dx != 0 and dy != 0 and not (walkable(nx, y) and walkable(x, ny)):
				return None

			x, y = nx, ny

			if x == gx and y == gy:
				return (x, y)

			if dx != 0 and dy != 0:
				# Diagonal: a jump point if either straight scan finds one
				if jump(x, y, dx, 0) is not None or jump(x, y, 0, dy) is not None:
					return (x, y)
			elif dx != 0:
				# Horizontal: forced neighbor above/below if the cell behind it is blocked
				if (walkable(x, y + 1) and not walkable(x - dx, y + 1)) or \
				   (walkable(x, y - 1) and not walkable(x - dx, y - 1)):
					return (x, y)
			else:
				# Vertical: forced neighbor left/right if the cell behind it is blocked
				if (walkable(x + 1, y) and not walkable(x + 1, y - dy)) or \
				   (walkable(x - 1, y) and not walkable(x - 1, y - dy)):
					return (x, y)

	def pruned_directions(x: int, y: int, dx: int, dy: int) -> List[Tuple[int, int]]:
		"""
		Directions worth scanning from (x, y) given the travel direction (dx, dy)
		used to reach it. A direction of (0, 0) means the start node (all 8 directions).
		"""
		dirs: List[Tuple[int, int]] = []

		if dx == 0 and dy == 0:
			for ddx in (-1, 0, 1):
				for ddy in (-1, 0, 1):
					if ddx != 0 or ddy != 0:
						dirs.append((ddx, ddy))
			return dirs

		if dx != 0 and dy != 0:
			# Diagonal: two straight components plus the diagonal itself
			dirs.append((dx, 0))
			dirs.append((0, dy))
			dirs.append((dx, dy))
		elif dx != 0:
			# Horizontal: natural neighbor plus forced neighbors
			dirs.append((dx, 0))
			for sy_ in (1, -1):
				if walkable(x, y + sy_) and not walkable(x - dx, y + sy_):
					dirs.append((0, sy_))
					dirs.append((dx, sy_))
		else:
			# Vertical: natural neighbor plus forced neighbors
			dirs.append((0, dy))
			for sx_ in (1, -1):
				if walkable(x + sx_, y) and not walkable(x + sx_, y - dy):
					dirs.append((sx_, 0))
					dirs.append((sx_, dy))

		return dirs

	oct_dist = octile_distance(start, goal)
	# Min-Heap: stores (f_cost, oct_dist_cost, coordinates)
	min_heap: List[Tuple[float, float, Coordinate]] = [(oct_dist, oct_dist, start)]
	# Shortest path distance from start to each jump point
	opt_path: Dict[Coordinate, float] = {start: 0.0}
	visited: Set[Coordinate] = set()
	# Parent pointers only link jump points (not every cell along the way)
	parent: Dict[Coordinate, Coordinate] = {}

	nodes_explored = 0
	nodes_generated = 1
	max_frontier_size = 1
	path_found = False
	iterations = 0

	while min_heap:
		# Check timeout limit (rate-limited to keep perf_counter out of the hot loop)
		iterations += 1
		if timeout_seconds is not None and (iterations & 0xFF) == 1:
			if (perf_counter() - start_time) >= timeout_seconds:
				elapsed_ms = (perf_counter() - start_time) * 1000.0
				return SearchResult(
					algorithm="JPS",
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
				algorithm="JPS",
				found=False,
				nodes_explored=nodes_explored,
				nodes_generated=nodes_generated,
				execution_time_ms=elapsed_ms,
				max_frontier_size=max_frontier_size,
				error_message=f"Node expansion limit reached ({max_nodes} nodes)"
			)

		# Pop the smallest(root) f_cost from the min_heap
		_, _, current = heapq.heappop(min_heap)

		if current in visited:
			continue

		visited.add(current)
		nodes_explored += 1

		if current == goal:
			path_found = True
			break

		cx, cy = current
		current_cost = opt_path[current]

		# Travel direction used to reach the current jump point (sign of the parent segment)
		par = parent.get(current)
		if par is None:
			pdx, pdy = 0, 0
		else:
			pdx = (cx > par[0]) - (cx < par[0])
			pdy = (cy > par[1]) - (cy < par[1])

		for dx, dy in pruned_directions(cx, cy, pdx, pdy):
			jump_point = jump(cx, cy, dx, dy)
			if jump_point is None or jump_point in visited:
				continue

			# Straight/diagonal segment, so octile distance is the exact segment cost
			comp_path = current_cost + octile_distance(current, jump_point)

			# Update if new computed path is a better path
			if comp_path < opt_path.get(jump_point, float("inf")):
				# update shortest path cost g(n)
				opt_path[jump_point] = comp_path
				parent[jump_point] = current

				# then the heuristic and f(n)
				jump_h = octile_distance(jump_point, goal)
				jump_f = comp_path + jump_h

				heapq.heappush(min_heap, (jump_f, jump_h, jump_point))
				nodes_generated += 1

		if len(min_heap) > max_frontier_size:
			max_frontier_size = len(min_heap)

	elapsed_ms = (perf_counter() - start_time) * 1000.0

	if not path_found:
		return SearchResult(
			algorithm="JPS",
			found=False,
			nodes_explored=nodes_explored,
			nodes_generated=nodes_generated,
			execution_time_ms=elapsed_ms,
			max_frontier_size=max_frontier_size,
			error_message="No path exists between start and goal."
		)

	# Reconstruct the jump point chain from parent pointers
	jump_points: List[Coordinate] = []
	curr: Optional[Coordinate] = goal
	while curr is not None:
		jump_points.append(curr)
		curr = parent.get(curr)
	jump_points.reverse()

	# Expand jump points into the full cell-by-cell path
	path: List[Coordinate] = [jump_points[0]]
	for i in range(1, len(jump_points)):
		px, py = path[-1]
		tx, ty = jump_points[i]
		step_x = (tx > px) - (tx < px)
		step_y = (ty > py) - (ty < py)
		while (px, py) != (tx, ty):
			px += step_x
			py += step_y
			path.append((px, py))

	return SearchResult(
		algorithm="JPS",
		found=True,
		path=path,
		path_cost=opt_path[goal],
		nodes_explored=nodes_explored,
		nodes_generated=nodes_generated,
		execution_time_ms=elapsed_ms,
		max_frontier_size=max_frontier_size
	)