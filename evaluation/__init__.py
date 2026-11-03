"""
Evaluation module for pathfinding benchmarks.
"""

from .sampler import (
    BenchmarkSampler,
    SampledScenario,
    MapMetadata,
    classify_size_tier,
    classify_distance_tier,
    ENVIRONMENT_CATEGORIES,
)
from .metrics import (
    ScenarioEvaluationRecord,
    AggregatedMetrics,
    compute_statistics,
    evaluate_result,
    aggregate_records,
)

__all__ = [
    "BenchmarkSampler",
    "SampledScenario",
    "MapMetadata",
    "classify_size_tier",
    "classify_distance_tier",
    "ENVIRONMENT_CATEGORIES",
    "ScenarioEvaluationRecord",
    "AggregatedMetrics",
    "compute_statistics",
    "evaluate_result",
    "aggregate_records",
]
