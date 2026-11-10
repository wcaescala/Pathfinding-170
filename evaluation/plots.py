"""
Generate figures from raw benchmark results.
Reads raw.csv and produces matplotlib figures (PNG and PDF).
"""

from pathlib import Path
import argparse
import sys
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Algorithm colors (consistent across all figures)
ALGO_COLORS = {
    "bfs": "#1f77b4",
    "dfs": "#ff7f0e",
    "dijkstra": "#2ca02c",
    "gbfs": "#d62728",
    "astar": "#9467bd",
    "jps": "#8c564b",
}


def apply_style() -> None:
    """Apply consistent matplotlib styling."""
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams["figure.figsize"] = (10, 6)
    plt.rcParams["font.size"] = 10
    plt.rcParams["axes.labelsize"] = 11
    plt.rcParams["axes.titlesize"] = 12
    plt.rcParams["legend.fontsize"] = 10


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


def save_figure(fig, out_dir: Path, fig_name: str) -> None:
    """Save figure as both PNG (200 DPI) and PDF."""
    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Save PNG
    fig.savefig(figures_dir / f"{fig_name}.png", dpi=200, bbox_inches="tight")

    # Save PDF
    fig.savefig(figures_dir / f"{fig_name}.pdf", bbox_inches="tight")

    plt.close(fig)
    print(f"Generated {fig_name}: {figures_dir / f'{fig_name}.png'}")


def generate_f1_time_by_distance(df: pd.DataFrame, out_dir: Path) -> None:
    """
    F1: Grouped bars - median time, algorithm x distance tier, log y
    Purpose: Cost scaling with difficulty
    """
    apply_style()

    # Get median time per algorithm x distance tier
    time_median = df.groupby(["algorithm", "distance_tier"])["time_ms"].median().unstack(level=1)

    # Ensure tiers are in order
    tiers = ["Short", "Medium", "Long"]
    time_median = time_median[[t for t in tiers if t in time_median.columns]]

    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(time_median.index))
    width = 0.25

    for i, tier in enumerate(tiers):
        if tier not in time_median.columns:
            continue
        values = time_median[tier].values
        ax.bar(x + i * width, values, width, label=tier.capitalize(),
               color=ALGO_COLORS.get(f"tier_{tier}", "gray"))

    ax.set_xlabel("Algorithm")
    ax.set_ylabel("Median Time (ms)")
    ax.set_title("Median Execution Time by Distance Tier")
    ax.set_xticks(x + width)
    ax.set_xticklabels(time_median.index)
    ax.legend(title="Distance Tier")
    ax.set_yscale("log")

    save_figure(fig, out_dir, "f1_time_by_distance")


def generate_f2_expanded_boxplot(df: pd.DataFrame, out_dir: Path) -> None:
    """
    F2: Boxplots - nodes expanded per algorithm, log y
    Purpose: Spread, not only the center
    """
    apply_style()

    # Filter successful runs for meaningful comparison
    df_success = df[df["success"]]

    fig, ax = plt.subplots(figsize=(12, 6))

    # Prepare data for boxplot
    algos = sorted(df_success["algorithm"].unique())
    data = [df_success[df_success["algorithm"] == algo]["expanded"].values for algo in algos]
    colors = [ALGO_COLORS.get(algo, "gray") for algo in algos]

    bp = ax.boxplot(data, labels=algos, patch_artist=True)

    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)

    ax.set_xlabel("Algorithm")
    ax.set_ylabel("Nodes Expanded")
    ax.set_title("Distribution of Nodes Expanded (Successful Runs)")
    ax.set_yscale("log")

    save_figure(fig, out_dir, "f2_expanded_boxplot")


def generate_f3_optimal_vs_expanded(df: pd.DataFrame, out_dir: Path) -> None:
    """
    F3: Log-log scatter - optimal length vs. nodes expanded
    Purpose: Growth rate
    """
    apply_style()

    # Filter successful runs
    df_success = df[df["success"]]

    fig, ax = plt.subplots(figsize=(10, 8))

    for algo in sorted(df_success["algorithm"].unique()):
        algo_data = df_success[df_success["algorithm"] == algo]
        ax.scatter(algo_data["optimal"], algo_data["expanded"],
                   label=algo, alpha=0.5, color=ALGO_COLORS.get(algo, "gray"), s=20)

    ax.set_xlabel("Optimal Path Length")
    ax.set_ylabel("Nodes Expanded")
    ax.set_title("Nodes Expanded vs. Optimal Path Length")
    ax.legend()
    ax.set_xscale("log")
    ax.set_yscale("log")

    save_figure(fig, out_dir, "f3_optimal_vs_expanded")


def generate_f4_success_heatmap(df: pd.DataFrame, out_dir: Path) -> None:
    """
    F4: Heatmap - success rate, algorithm x environment (or map)
    Purpose: Where each algorithm breaks
    """
    apply_style()

    # Compute success rate per algorithm x category
    success_rate = df.groupby(["algorithm", "category"])["success"].mean() * 100
    success_table = success_rate.unstack(level=1, fill_value=0)

    fig, ax = plt.subplots(figsize=(10, 6))

    im = ax.imshow(success_table.values, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")

    ax.set_xticks(np.arange(len(success_table.columns)))
    ax.set_yticks(np.arange(len(success_table.index)))
    ax.set_xticklabels(success_table.columns)
    ax.set_yticklabels(success_table.index)

    # Add text annotations
    for i in range(len(success_table.index)):
        for j in range(len(success_table.columns)):
            text = ax.text(j, i, f"{success_table.values[i, j]:.0f}%",
                          ha="center", va="center", color="black", fontsize=9)

    ax.set_xlabel("Environment Category")
    ax.set_ylabel("Algorithm")
    ax.set_title("Success Rate by Environment (%)")

    plt.colorbar(im, ax=ax, label="Success Rate (%)")

    save_figure(fig, out_dir, "f4_success_heatmap")


def generate_f5_alpha_boxplot(df: pd.DataFrame, out_dir: Path) -> None:
    """
    F5: Alpha boxplot or ECDF
    Purpose: Optimality trade-off
    """
    apply_style()

    # Filter successful runs
    df_success = df[df["success"]]

    fig, ax = plt.subplots(figsize=(12, 6))

    # Prepare data for boxplot
    algos = sorted(df_success["algorithm"].unique())
    data = [df_success[df_success["algorithm"] == algo]["alpha"].dropna().values for algo in algos]
    colors = [ALGO_COLORS.get(algo, "gray") for algo in algos]

    bp = ax.boxplot(data, labels=algos, patch_artist=True)

    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)

    ax.set_xlabel("Algorithm")
    ax.set_ylabel("Alpha (Suboptimality Ratio)")
    ax.set_title("Distribution of Alpha (Path Cost / Optimal)")
    ax.axhline(y=1.0, color="red", linestyle="--", alpha=0.5, label="Optimal")
    ax.legend()

    save_figure(fig, out_dir, "f5_alpha_boxplot")


def generate_f6_time_vs_alpha(df: pd.DataFrame, out_dir: Path) -> None:
    """
    F6: Scatter - median time vs. median alpha
    Purpose: Speed/quality Pareto view
    """
    apply_style()

    # Filter successful runs
    df_success = df[df["success"]]

    # Compute median time and alpha per algorithm
    summary = df_success.groupby("algorithm").agg({
        "time_ms": "median",
        "alpha": "median"
    })

    fig, ax = plt.subplots(figsize=(10, 6))

    for algo in summary.index:
        ax.scatter(summary.loc[algo, "time_ms"], summary.loc[algo, "alpha"],
                   label=algo, color=ALGO_COLORS.get(algo, "gray"), s=100)
        ax.annotate(algo, (summary.loc[algo, "time_ms"], summary.loc[algo, "alpha"]),
                   xytext=(5, 5), textcoords="offset points", fontsize=9)

    ax.set_xlabel("Median Time (ms)")
    ax.set_ylabel("Median Alpha")
    ax.set_title("Speed vs. Quality Trade-off")
    ax.set_xscale("log")

    save_figure(fig, out_dir, "f6_time_vs_alpha")


def generate_f7_performance_profile(df: pd.DataFrame, out_dir: Path) -> None:
    """
    F7: Performance profile (Dolan-More)
    Purpose: Robust solver ranking
    """
    apply_style()

    # Filter successful runs
    df_success = df[df["success"]]

    # Compute best time per scenario
    best_time = df_success.groupby("scenario_id")["time_ms"].min()

    # Compute ratio to best time for each algorithm
    ratios = df_success.merge(best_time.rename("best_time"), left_on="scenario_id", right_index=True)
    ratios["ratio"] = ratios["time_ms"] / ratios["best_time"]

    fig, ax = plt.subplots(figsize=(10, 6))

    taus = np.logspace(0, 3, 200)

    for algo in sorted(ratios["algorithm"].unique()):
        algo_ratios = ratios[ratios["algorithm"] == algo]["ratio"]
        # Replace inf with max tau
        algo_ratios = algo_ratios.replace([np.inf], taus[-1] * 2)

        profile = [(algo_ratios <= t).mean() for t in taus]
        ax.step(taus, profile, where="post", label=algo, color=ALGO_COLORS.get(algo, "gray"))

    ax.set_xlabel("Performance Ratio (τ)")
    ax.set_ylabel("Fraction of Scenarios")
    ax.set_title("Performance Profile (Dolan-Moré)")
    ax.set_xscale("log")
    ax.legend()
    ax.grid(True, alpha=0.3)

    save_figure(fig, out_dir, "f7_performance_profile")


def generate_all_figures(run_dir: Path) -> None:
    """Generate all figures F1-F7 from raw.csv."""
    print(f"\nLoading raw data from {run_dir / 'raw.csv'}")
    df = load_raw_data(run_dir)
    print(f"Loaded {len(df)} rows")

    print("\nGenerating figures...")
    generate_f1_time_by_distance(df, run_dir)
    generate_f2_expanded_boxplot(df, run_dir)
    generate_f3_optimal_vs_expanded(df, run_dir)
    generate_f4_success_heatmap(df, run_dir)
    generate_f5_alpha_boxplot(df, run_dir)
    generate_f6_time_vs_alpha(df, run_dir)
    generate_f7_performance_profile(df, run_dir)

    print(f"\nAll figures generated in {run_dir / 'figures'}")


def main():
    parser = argparse.ArgumentParser(description="Generate figures from raw benchmark results.")
    parser.add_argument("run_dir", type=str,
                        help="Path to the run directory containing raw.csv")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Error: Directory {run_dir} does not exist")
        sys.exit(1)

    generate_all_figures(run_dir)


if __name__ == "__main__":
    main()
