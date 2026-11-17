"""
Metrics calculation, path validation, and reporting for pathfinding evaluations.
No high-level or external graph libraries are used.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
import math

from algorithms.base import SearchResult, validate_path

SQRT2 = math.sqrt(2)


@dataclass
class ScenarioEvaluationRecord:
    """Holds the measurement metrics for a single algorithm run on a scenario."""
    algorithm: str
    map_name: str
    map_size_tier: str
    distance_tier: str
    bucket: int
    optimal_cost: float

    # Outcome
    success: bool
    path_valid: bool
    validation_error: Optional[str]

    # Metrics
    execution_time_ms: float
    path_cost: float
    suboptimality_ratio: float  # path_cost / optimal_cost (1.0 = optimal)
    nodes_explored: int
    nodes_generated: int
    max_frontier_size: int
    path_length_steps: int


@dataclass
class AggregatedMetrics:
    """Statistical summary across multiple evaluation runs."""
    algorithm: str
    total_scenarios: int
    successful_runs: int
    success_rate_pct: float

    # Time stats (ms)
    time_mean: float
    time_median: float
    time_std: float
    time_min: float
    time_max: float

    # Nodes explored stats
    nodes_mean: float
    nodes_median: float
    nodes_min: int
    nodes_max: int

    # Suboptimality stats (for successful runs)
    suboptimality_mean: float
    suboptimality_median: float
    suboptimality_max: float


def compute_statistics(values: List[float]) -> Tuple[float, float, float, float, float]:
    """Returns (mean, median, std_dev, min, max) for a list of numbers."""
    if not values:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    n = len(values)
    mean_val = sum(values) / n
    sorted_vals = sorted(values)
    median_val = (
        sorted_vals[n // 2]
        if n % 2 != 0
        else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0
    )
    variance = sum((x - mean_val) ** 2 for x in values) / n if n > 1 else 0.0
    std_val = math.sqrt(variance)
    return mean_val, median_val, std_val, sorted_vals[0], sorted_vals[-1]


def evaluate_result(
    grid_map: Any,
    result: SearchResult,
    map_name: str,
    map_size_tier: str,
    distance_tier: str,
    bucket: int,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    optimal_cost: float
) -> ScenarioEvaluationRecord:
    """
    Evaluates a single search result, validating path correctness and computing metrics.
    """
    is_valid = False
    validation_err: Optional[str] = None
    suboptimality = 0.0

    if result.found and result.path:
        is_valid, validation_err = validate_path(grid_map, result.path, start, goal)
        if is_valid and optimal_cost > 0:
            suboptimality = result.path_cost / optimal_cost
        elif is_valid and optimal_cost == 0:
            suboptimality = 1.0
    elif not result.found:
        validation_err = result.error_message or "Path not found"

    success = result.found and is_valid

    return ScenarioEvaluationRecord(
        algorithm=result.algorithm,
        map_name=map_name,
        map_size_tier=map_size_tier,
        distance_tier=distance_tier,
        bucket=bucket,
        optimal_cost=optimal_cost,
        success=success,
        path_valid=is_valid,
        validation_error=validation_err,
        execution_time_ms=result.execution_time_ms,
        path_cost=result.path_cost if success else float("nan"),
        suboptimality_ratio=suboptimality if success else float("nan"),
        nodes_explored=result.nodes_explored,
        nodes_generated=result.nodes_generated,
        max_frontier_size=result.max_frontier_size,
        path_length_steps=result.step_count if success else 0
    )


def aggregate_records(records: List[ScenarioEvaluationRecord]) -> AggregatedMetrics:
    """Computes aggregated performance metrics for a collection of evaluation records."""
    if not records:
        raise ValueError("Cannot aggregate empty records")

    algo = records[0].algorithm
    total = len(records)
    successes = [r for r in records if r.success]
    succ_count = len(successes)
    success_rate = (succ_count / total) * 100.0 if total > 0 else 0.0

    times = [r.execution_time_ms for r in records]
    t_mean, t_median, t_std, t_min, t_max = compute_statistics(times)

    nodes = [float(r.nodes_explored) for r in records]
    n_mean, n_median, _, n_min, n_max = compute_statistics(nodes)

    sub_ratios = [r.suboptimality_ratio for r in successes if not math.isnan(r.suboptimality_ratio)]
    s_mean, s_median, _, _, s_max = compute_statistics(sub_ratios)

    return AggregatedMetrics(
        algorithm=algo,
        total_scenarios=total,
        successful_runs=succ_count,
        success_rate_pct=success_rate,
        time_mean=t_mean,
        time_median=t_median,
        time_std=t_std,
        time_min=t_min,
        time_max=t_max,
        nodes_mean=n_mean,
        nodes_median=n_median,
        nodes_min=int(n_min),
        nodes_max=int(n_max),
        suboptimality_mean=s_mean,
        suboptimality_median=s_median,
        suboptimality_max=s_max
    )


def verify_path(grid: Any, path: List[Tuple[int, int]], start: Tuple[int, int], goal: Tuple[int, int]) -> Tuple[bool, Optional[float]]:
    """
    Return (is_valid, octile_cost). Cost is None when invalid.

    Verifies that a path is continuous, collision-free, respects bounds,
    does not cut corners diagonally, and connects start to goal.

    Works with GridMap objects (from utils.map_loader) which provide
    in_bounds(x, y) and is_passable(x, y) methods.
    """
    if not path or path[0] != start or path[-1] != goal:
        return False, None

    # Check all cells in the path are passable
    for x, y in path:
        if not grid.in_bounds(x, y) or not grid.is_passable(x, y):
            return False, None

    cost = 0.0

    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        dx, dy = x1 - x0, y1 - y0

        # Check for illegal step (teleport or no movement)
        if abs(dx) > 1 or abs(dy) > 1 or (dx == 0 and dy == 0):
            return False, None

        # Corner cutting check for diagonal moves
        if dx != 0 and dy != 0:
            if not (grid.is_passable(x0 + dx, y0) and grid.is_passable(x0, y0 + dy)):
                return False, None
            cost += SQRT2
        else:
            cost += 1.0

    return True, cost


def size_tier(grid: Any) -> str:
    """Classify map into Small, Medium, or Large tier based on cell count."""
    cells = grid.width * grid.height
    return "small" if cells < 30_000 else "medium" if cells <= 200_000 else "large"
