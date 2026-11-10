"""
Evaluation runner script that benchmarks pathfinding algorithms on sampled DA2 scenarios.
Outputs structured comparison tables and summary metrics.
No high-level or external graph libraries are used.
"""

from pathlib import Path
from typing import List, Dict, Callable, Optional
import argparse
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.map_loader import load_map, GridMap
from algorithms.bfs import bfs
from algorithms.dfs import dfs
from algorithms.dijkstra import dijkstra
from algorithms.a_star import a_star
from algorithms.gbfs import gbfs
from algorithms.jump_point import jump_point_search
from evaluation.sampler import BenchmarkSampler, SampledScenario
from evaluation.metrics import (
    ScenarioEvaluationRecord,
    AggregatedMetrics,
    evaluate_result,
    aggregate_records
)


def run_benchmark(
    sampler: BenchmarkSampler,
    algorithms: Dict[str, Callable],
    map_names: Optional[List[str]] = None,
    samples_per_tier: int = 3,
    max_nodes: int = 250_000,
    timeout_seconds: float = 10.0,
    seed: int = 42
) -> Dict[str, List[ScenarioEvaluationRecord]]:
    """
    Executes benchmark comparison on sampled scenarios across specified algorithms.
    """
    sampled_scenarios = sampler.sample_scenarios(
        map_names=map_names,
        samples_per_tier=samples_per_tier,
        seed=seed
    )

    print(f"\n=======================================================")
    print(f" BENCHMARK EVALUATION: {len(sampled_scenarios)} Total Scenarios")
    print(f" Algorithms: {', '.join(algorithms.keys())}")
    print(f" Seed: {seed} | Samples Per Tier: {samples_per_tier}")
    print(f" Limits: max_nodes={max_nodes:,}, timeout={timeout_seconds}s")
    print(f"=======================================================\n")

    # Cache loaded maps so we do not reload repeatedly
    loaded_maps: Dict[str, GridMap] = {}
    records_by_algo: Dict[str, List[ScenarioEvaluationRecord]] = {k: [] for k in algorithms.keys()}

    total_items = len(sampled_scenarios)
    for idx, item in enumerate(sampled_scenarios, 1):
        m_name = item.map_name
        if m_name not in loaded_maps:
            loaded_maps[m_name] = load_map(item.map_metadata.map_path)
        gmap = loaded_maps[m_name]

        sc = item.scenario
        sx, sy = sc.start
        gx, gy = sc.goal

        print(f"[{idx:3d}/{total_items:3d}] {m_name:<20} ({item.map_metadata.size_tier:<6}) | "
              f"Tier: {item.distance_tier:<6} | Start: ({sx:3d},{sy:3d}) -> Goal: ({gx:3d},{gy:3d}) | "
              f"OptCost: {sc.optimal_length:8.2f}")

        for algo_name, algo_fn in algorithms.items():
            result = algo_fn(
                gmap,
                sc.start,
                sc.goal,
                allow_diagonal=True,
                max_nodes=max_nodes,
                timeout_seconds=timeout_seconds
            )

            rec = evaluate_result(
                grid_map=gmap,
                result=result,
                map_name=m_name,
                map_size_tier=item.map_metadata.size_tier,
                distance_tier=item.distance_tier,
                bucket=sc.bucket,
                start=sc.start,
                goal=sc.goal,
                optimal_cost=sc.optimal_length
            )
            records_by_algo[algo_name].append(rec)

            status_str = "OK" if rec.success else "FAIL"
            print(f"    -> {algo_name:<5}: {status_str} | "
                  f"Cost: {rec.path_cost:8.2f} (x{rec.suboptimality_ratio:5.2f}) | "
                  f"Nodes: {rec.nodes_explored:7,d} | "
                  f"Time: {rec.execution_time_ms:7.2f} ms")

    return records_by_algo


def print_summary_table(records_by_algo: Dict[str, List[ScenarioEvaluationRecord]]) -> None:
    """Formats and prints summary metrics table."""
    print("\n" + "=" * 95)
    print(f"{'OVERALL PERFORMANCE SUMMARY':^95}")
    print("=" * 95)
    header = (
        f"{'Algorithm':<10} | {'Success%':<8} | {'Mean Time':<11} | {'Med Time':<10} | "
        f"{'Mean Nodes':<12} | {'Med Nodes':<11} | {'Mean Subopt':<11} | {'Max Subopt':<10}"
    )
    print(header)
    print("-" * 95)

    for algo_name, records in records_by_algo.items():
        summary = aggregate_records(records)
        row = (
            f"{algo_name:<10} | "
            f"{summary.success_rate_pct:7.1f}% | "
            f"{summary.time_mean:8.2f} ms | "
            f"{summary.time_median:7.2f} ms | "
            f"{summary.nodes_mean:10.1f} | "
            f"{summary.nodes_median:9.1f} | "
            f"x{summary.suboptimality_mean:9.3f} | "
            f"x{summary.suboptimality_max:8.3f}"
        )
        print(row)
    print("=" * 95)

    # Breakdown by Distance Tier
    print("\n" + "=" * 95)
    print(f"{'BREAKDOWN BY DISTANCE TIER':^95}")
    print("=" * 95)
    print(f"{'Tier':<8} | {'Algorithm':<10} | {'Success%':<8} | {'Mean Time':<11} | {'Mean Nodes':<12} | {'Mean Subopt':<11}")
    print("-" * 95)

    for tier in ["Short", "Medium", "Long"]:
        for algo_name, records in records_by_algo.items():
            tier_records = [r for r in records if r.distance_tier == tier]
            if not tier_records:
                continue
            s = aggregate_records(tier_records)
            print(
                f"{tier:<8} | {algo_name:<10} | {s.success_rate_pct:7.1f}% | "
                f"{s.time_mean:8.2f} ms | {s.nodes_mean:10.1f} | x{s.suboptimality_mean:9.3f}"
            )
        print("-" * 95)
    print("=" * 95 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Evaluate pathfinding algorithms on DA2 benchmark.")
    parser.add_argument("--maps", nargs="*", default=None, help="Specific map names to test.")
    parser.add_argument("--samples-per-tier", type=int, default=2, help="Number of scenarios per distance tier.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling.")
    parser.add_argument("--max-nodes", type=int, default=100_000, help="Max node expansion limit.")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout in seconds per query.")
    args = parser.parse_args()

    benchmarks_dir = PROJECT_ROOT / "benchmarks"
    sampler = BenchmarkSampler(benchmarks_dir)

    algos = {
        "BFS": bfs,
        "DFS": dfs,
        "Dijkstra": dijkstra,
        "A*": a_star,
        "GBFS": gbfs,
        "JPS": jump_point_search,
    }

    # If no maps specified, default to a compact representative set for quick CLI runs
    target_maps = args.maps if args.maps else [
        "ht_store.map",      # Small
        "ca_cave.map",       # Medium
        "w_encounter1.map",  # Medium
    ]

    records = run_benchmark(
        sampler=sampler,
        algorithms=algos,
        map_names=target_maps,
        samples_per_tier=args.samples_per_tier,
        max_nodes=args.max_nodes,
        timeout_seconds=args.timeout,
        seed=args.seed
    )

    print_summary_table(records)


if __name__ == "__main__":
    main()