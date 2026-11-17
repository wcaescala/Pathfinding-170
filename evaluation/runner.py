"""
Evaluation runner script that benchmarks pathfinding algorithms on sampled DA2 scenarios.
Outputs structured CSV data that can be aggregated into tables and figures.
No high-level or external graph libraries are used.
"""

from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
import argparse
import csv
import gc
import json
import math
import statistics
import subprocess
import sys
import time
from datetime import datetime

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.map_loader import load_map, GridMap
from utils.scenario_loader import load_scenarios, Scenario
from evaluation.sampler import BenchmarkSampler, SampledScenario, classify_distance_tier
from evaluation.metrics import verify_path, size_tier
from algorithms import ALGORITHMS

# CSV field names for raw.csv
FIELDS = [
    "algorithm", "map", "category", "size_tier", "distance_tier", "scenario_id",
    "optimal", "path_cost", "alpha", "time_ms", "expanded", "generated",
    "peak_frontier", "success", "failure"
]

# Representative map portfolio (9 maps spanning 5 environments and 3 size tiers)
REPRESENTATIVE_MAPS = [
    # Small maps (<30k cells)
    "ht_store.map",          # 37x37 (1,369 cells) - Micro indoor shop
    "lt_foundry_n.map",      # 109x92 (10,028 cells) - Small industrial interior
    "ht_playershouse_n.map", # 185x68 (12,580 cells) - Long corridor / rooms

    # Medium maps (30k-200k cells)
    "ca_cave.map",           # 183x277 (50,691 cells) - Organic cave network
    "ht_keep.map",           # 281x357 (100,317 cells) - Castle layout with chokepoints
    "w_encounter1.map",      # 258x514 (132,612 cells) - Outdoor encounter

    # Large maps (>200k cells)
    "lt_0_lowtown.map",      # 514x514 (264,196 cells) - Full urban slum
    "w_woundedcoast.map",    # 642x578 (371,076 cells) - Rugged coastal terrain
    "dr_0_deeproads.map",    # 560x733 (410,480 cells) - Vast underground highway
]


def load_completed_keys(csv_path: Path) -> Set[Tuple[str, str]]:
    """Load (algorithm, scenario_id) pairs that have already been completed."""
    if not csv_path.exists():
        return set()

    completed = set()
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            completed.add((row["algorithm"], row["scenario_id"]))
    return completed


def load_map_cached(map_path: Path) -> GridMap:
    """Load a map file (cached by caller)."""
    return load_map(map_path)


def classify_size_tier_from_map(grid: GridMap) -> str:
    """Classify map size tier from GridMap object."""
    cells = grid.width * grid.height
    return "small" if cells < 30_000 else "medium" if cells <= 200_000 else "large"


def run(
    maps: List[str],
    algos: Dict[str, callable],
    k: int,
    seed: int,
    out_dir: Path,
    repeats: int = 3,
    timeout: float = 5.0,
    max_nodes: int = 100_000,
    workers: int = 1
) -> None:
    """
    Run benchmark on sampled scenarios and write results to CSV.

    Parameters:
        maps: List of map filenames to sample from.
        algos: Dictionary of algorithm name -> search function.
        k: Number of scenarios per distance tier per map.
        seed: Random seed for reproducibility.
        out_dir: Output directory for results.
        repeats: Number of timing repeats per successful run.
        timeout: Timeout in seconds per search.
        max_nodes: Maximum node expansions per search.
        workers: Number of parallel workers (1 for accurate timing).
    """
    # Create output directory
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write config.json
    run_id = out_dir.name
    config = {
        "run_id": run_id,
        "seed": seed,
        "k": k,
        "maps": maps,
        "algorithms": list(algos.keys()),
        "repeats": repeats,
        "timeout_s": timeout,
        "max_nodes": max_nodes,
        "python": sys.version,
        "platform": sys.platform,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, stderr=subprocess.DEVNULL).decode().strip() if (PROJECT_ROOT / ".git").exists() else "unknown",
    }
    with open(out_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    # Load completed keys for resume
    done = load_completed_keys(out_dir / "raw.csv")
    new_file = not (out_dir / "raw.csv").exists()

    # Initialize sampler
    benchmarks_dir = PROJECT_ROOT / "benchmarks"
    sampler = BenchmarkSampler(benchmarks_dir)

    # Sample scenarios
    sampled_scenarios = sampler.sample_scenarios(
        map_names=maps,
        samples_per_tier=k,
        seed=seed
    )

    print(f"\n=======================================================")
    print(f" BENCHMARK EVALUATION: {len(sampled_scenarios)} Total Scenarios")
    print(f" Algorithms: {', '.join(algos.keys())}")
    print(f" Seed: {seed} | Samples Per Tier: {k}")
    print(f" Limits: max_nodes={max_nodes:,}, timeout={timeout}s")
    print(f" Repeats: {repeats} | Workers: {workers}")
    print(f" Output: {out_dir}")
    print(f"=======================================================\n")

    # Cache loaded maps
    loaded_maps: Dict[str, GridMap] = {}

    with open(out_dir / "raw.csv", "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()

        for idx, item in enumerate(sampled_scenarios, 1):
            map_name = item.map_name
            if map_name not in loaded_maps:
                loaded_maps[map_name] = load_map(item.map_metadata.map_path)
            grid = loaded_maps[map_name]

            sc = item.scenario
            # Create stable scenario ID
            scenario_id = f"{map_name}_{sc.bucket}_{sc.start[0]}_{sc.start[1]}_{sc.goal[0]}_{sc.goal[1]}"

            # Extract category from map name (e.g., "ht" from "ht_store.map")
            category = map_name.split("_")[0]

            # Get size tier
            size_tier = classify_size_tier_from_map(grid)

            # Get distance tier
            distance_tier = item.distance_tier

            print(f"[{idx:3d}/{len(sampled_scenarios):3d}] {map_name:<20} ({size_tier:<6}) | "
                  f"Tier: {distance_tier:<6} | OptCost: {sc.optimal_length:8.2f}")

            for algo_name, algo_fn in algos.items():
                if (algo_name, scenario_id) in done:
                    print(f"    -> {algo_name:<5}: SKIPPED (already completed)")
                    continue

                times = []
                result = None

                for repeat in range(repeats):
                    gc.collect()
                    t0 = time.perf_counter()

                    # Call algorithm with signature: (grid, start, goal, timeout, max_nodes)
                    # Note: existing algorithms use different parameter names, adapt here
                    res = algo_fn(
                        grid,
                        sc.start,
                        sc.goal,
                        allow_diagonal=True,
                        max_nodes=max_nodes,
                        timeout_seconds=timeout
                    )

                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    times.append(elapsed_ms)

                    if res.status != "ok":
                        # Don't repeat failures
                        result = res
                        break

                    result = res

                # Verify path and compute cost
                ok, cost = False, None
                if result and result.path:
                    ok, cost = verify_path(grid, result.path, sc.start, sc.goal)

                # Compute alpha (suboptimality ratio)
                alpha = None
                if ok and cost is not None and sc.optimal_length > 0:
                    alpha = cost / sc.optimal_length

                # Determine failure reason
                failure = ""
                if not ok:
                    if result and result.status != "ok":
                        failure = result.status
                    else:
                        failure = "invalid_path"

                # Write row
                writer.writerow({
                    "algorithm": algo_name,
                    "map": map_name,
                    "category": category,
                    "size_tier": size_tier,
                    "distance_tier": distance_tier,
                    "scenario_id": scenario_id,
                    "optimal": sc.optimal_length,
                    "path_cost": cost if ok else "",
                    "alpha": alpha if ok else "",
                    "time_ms": statistics.median(times) if times else "",
                    "expanded": result.expanded if result else "",
                    "generated": result.generated if result else "",
                    "peak_frontier": result.peak_frontier if result else "",
                    "success": ok,
                    "failure": failure,
                })
                f.flush()  # Survive crashes

                status_str = "OK" if ok else f"FAIL ({failure})"
                cost_str = f"{cost:8.2f}" if cost else "N/A"
                alpha_str = f"{alpha:5.2f}" if alpha else "N/A"
                nodes_str = f"{result.expanded:7,d}" if result else "0"
                time_str = f"{statistics.median(times):7.2f}" if times else "0"
                print(f"    -> {algo_name:<5}: {status_str} | "
                      f"Cost: {cost_str:>8} | "
                      f"Alpha: {alpha_str:>5} | "
                      f"Nodes: {nodes_str} | "
                      f"Time: {time_str} ms")

    print(f"\nBenchmark complete. Results written to {out_dir / 'raw.csv'}")


def main():
    parser = argparse.ArgumentParser(description="Run pathfinding algorithm benchmarks on DA2 benchmark.")
    parser.add_argument("--preset", choices=["fast", "full"], default="fast",
                        help="Preset configuration (fast: k=2, 54 scenarios; full: k=5, 135 scenarios)")
    parser.add_argument("--maps", nargs="*", default=None,
                        help="Specific map names to test (overrides preset)")
    parser.add_argument("--algos", nargs="*", default=None,
                        help="Specific algorithms to test (overrides preset)")
    parser.add_argument("--k", type=int, default=None,
                        help="Samples per distance tier (overrides preset)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for sampling")
    parser.add_argument("--repeats", type=int, default=3,
                        help="Number of timing repeats per successful run")
    parser.add_argument("--timeout", type=float, default=5.0,
                        help="Timeout in seconds per search")
    parser.add_argument("--max-nodes", type=int, default=100_000,
                        help="Maximum node expansions per search")
    parser.add_argument("--workers", type=int, default=1,
                        help="Number of parallel workers (use 1 for accurate timing)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output directory name (default: YYYY-MM-DD_preset)")

    args = parser.parse_args()

    # Set preset parameters
    if args.preset == "fast":
        k_val = 2 if args.k is None else args.k
        target_maps = args.maps if args.maps else REPRESENTATIVE_MAPS
    else:  # full
        k_val = 5 if args.k is None else args.k
        target_maps = args.maps if args.maps else REPRESENTATIVE_MAPS

    # Select algorithms
    if args.algos:
        algos = {name: ALGORITHMS[name] for name in args.algos if name in ALGORITHMS}
    else:
        algos = ALGORITHMS

    # Set output directory
    if args.output:
        out_dir = PROJECT_ROOT / "results" / args.output
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
        out_dir = PROJECT_ROOT / "results" / f"{date_str}_{args.preset}"

    # Run benchmark
    run(
        maps=target_maps,
        algos=algos,
        k=k_val,
        seed=args.seed,
        out_dir=out_dir,
        repeats=args.repeats,
        timeout=args.timeout,
        max_nodes=args.max_nodes,
        workers=args.workers
    )


if __name__ == "__main__":
    main()
