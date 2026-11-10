"""
Aggregate raw benchmark results into summary tables.
Reads raw.csv and writes tables in CSV and Markdown formats.
"""

from pathlib import Path
import argparse
import sys
import pandas as pd

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_raw_data(run_dir: Path) -> pd.DataFrame:
    """Load raw.csv from the specified run directory."""
    csv_path = run_dir / "raw.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"raw.csv not found in {run_dir}")

    df = pd.read_csv(csv_path)
    # Convert numeric columns
    numeric_cols = ["optimal", "path_cost", "alpha", "time_ms", "expanded", "generated", "peak_frontier"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Convert success to boolean
    df["success"] = df["success"].astype(bool)

    return df


def save_table(df: pd.DataFrame, out_dir: Path, table_name: str) -> None:
    """Save a table as both CSV and Markdown."""
    tables_dir = out_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    # Save CSV
    df.to_csv(tables_dir / f"{table_name}.csv", index=True)

    # Save Markdown
    md_path = tables_dir / f"{table_name}.md"
    with open(md_path, "w") as f:
        f.write(df.to_markdown(index=True))


def generate_t1_overall(df: pd.DataFrame, out_dir: Path) -> None:
    """
    T1 Overall: Group by algorithm
    Columns: success %, mean/median/std time, median expanded, mean alpha
    """
    # Compute success rate from all runs
    success_pct = df.groupby("algorithm")["success"].mean() * 100

    # Compute time metrics from all runs
    time_stats = df.groupby("algorithm")["time_ms"].agg(["mean", "median", "std"])

    # Compute expanded median from all runs
    expanded_median = df.groupby("algorithm")["expanded"].median()

    # Compute alpha mean from successful runs only
    df_success = df[df["success"]]
    alpha_mean = df_success.groupby("algorithm")["alpha"].mean()

    # Combine
    t1 = pd.DataFrame({
        "success_pct": success_pct,
        "time_mean_ms": time_stats["mean"],
        "time_median_ms": time_stats["median"],
        "time_std_ms": time_stats["std"],
        "expanded_median": expanded_median,
        "alpha_mean": alpha_mean
    }).round(3)

    save_table(t1, out_dir, "t1_overall")
    print(f"Generated T1 Overall: {out_dir / 'tables' / 't1_overall.md'}")


def generate_t2_by_distance(df: pd.DataFrame, out_dir: Path) -> None:
    """
    T2 By distance tier: algorithm x tier
    Columns: median time, median expanded, success %
    """
    # Success rate per algorithm x tier
    success_pct = df.groupby(["algorithm", "distance_tier"])["success"].mean() * 100

    # Median time per algorithm x tier
    time_median = df.groupby(["algorithm", "distance_tier"])["time_ms"].median()

    # Median expanded per algorithm x tier
    expanded_median = df.groupby(["algorithm", "distance_tier"])["expanded"].median()

    # Combine
    t2 = pd.DataFrame({
        "success_pct": success_pct,
        "time_median_ms": time_median,
        "expanded_median": expanded_median
    }).round(3)

    t2 = t2.unstack(level=1)  # Put distance_tier as columns
    save_table(t2, out_dir, "t2_by_distance")
    print(f"Generated T2 By Distance: {out_dir / 'tables' / 't2_by_distance.md'}")


def generate_t3_by_environment(df: pd.DataFrame, out_dir: Path) -> None:
    """
    T3 By environment: algorithm x category
    Columns: median time, median expanded, success %
    """
    # Success rate per algorithm x category
    success_pct = df.groupby(["algorithm", "category"])["success"].mean() * 100

    # Median time per algorithm x category
    time_median = df.groupby(["algorithm", "category"])["time_ms"].median()

    # Median expanded per algorithm x category
    expanded_median = df.groupby(["algorithm", "category"])["expanded"].median()

    # Combine
    t3 = pd.DataFrame({
        "success_pct": success_pct,
        "time_median_ms": time_median,
        "expanded_median": expanded_median
    }).round(3)

    t3 = t3.unstack(level=1)  # Put category as columns
    save_table(t3, out_dir, "t3_by_environment")
    print(f"Generated T3 By Environment: {out_dir / 'tables' / 't3_by_environment.md'}")


def generate_t4_by_size(df: pd.DataFrame, out_dir: Path) -> None:
    """
    T4 By size tier: algorithm x size_tier
    Columns: median time, median expanded, success %
    """
    # Success rate per algorithm x size_tier
    success_pct = df.groupby(["algorithm", "size_tier"])["success"].mean() * 100

    # Median time per algorithm x size_tier
    time_median = df.groupby(["algorithm", "size_tier"])["time_ms"].median()

    # Median expanded per algorithm x size_tier
    expanded_median = df.groupby(["algorithm", "size_tier"])["expanded"].median()

    # Combine
    t4 = pd.DataFrame({
        "success_pct": success_pct,
        "time_median_ms": time_median,
        "expanded_median": expanded_median
    }).round(3)

    t4 = t4.unstack(level=1)  # Put size_tier as columns
    save_table(t4, out_dir, "t4_by_size")
    print(f"Generated T4 By Size: {out_dir / 'tables' / 't4_by_size.md'}")


def generate_t5_failure_breakdown(df: pd.DataFrame, out_dir: Path) -> None:
    """
    T5 Failure breakdown: algorithm x failure reason
    Columns: count per failure reason
    """
    # Filter failed runs
    df_failed = df[~df["success"]]

    # Count failures per algorithm x failure reason
    failure_counts = df_failed.groupby(["algorithm", "failure"]).size()

    # Pivot to table
    t5 = failure_counts.unstack(level=1, fill_value=0)
    save_table(t5, out_dir, "t5_failure_breakdown")
    print(f"Generated T5 Failure Breakdown: {out_dir / 'tables' / 't5_failure_breakdown.md'}")


def generate_all_tables(run_dir: Path) -> None:
    """Generate all tables T1-T5 from raw.csv."""
    print(f"\nLoading raw data from {run_dir / 'raw.csv'}")
    df = load_raw_data(run_dir)
    print(f"Loaded {len(df)} rows")

    print("\nGenerating tables...")
    generate_t1_overall(df, run_dir)
    generate_t2_by_distance(df, run_dir)
    generate_t3_by_environment(df, run_dir)
    generate_t4_by_size(df, run_dir)
    generate_t5_failure_breakdown(df, run_dir)

    print(f"\nAll tables generated in {run_dir / 'tables'}")


def main():
    parser = argparse.ArgumentParser(description="Aggregate raw benchmark results into summary tables.")
    parser.add_argument("run_dir", type=str,
                        help="Path to the run directory containing raw.csv")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Error: Directory {run_dir} does not exist")
        sys.exit(1)

    generate_all_tables(run_dir)


if __name__ == "__main__":
    main()
