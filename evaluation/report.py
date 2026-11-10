"""
One-command report generation.
Runs aggregate and plots on a run directory, optionally generates a REPORT.md.
"""

from pathlib import Path
import argparse
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.aggregate import generate_all_tables
from evaluation.plots import generate_all_figures


def generate_report(run_dir: Path, create_markdown: bool = True) -> None:
    """
    Generate tables and figures for a run directory.

    Parameters:
        run_dir: Path to the run directory containing raw.csv
        create_markdown: If True, create a REPORT.md file
    """
    print(f"\n{'='*60}")
    print(f"GENERATING REPORT FOR: {run_dir}")
    print(f"{'='*60}")

    # Generate tables
    print("\n[1/2] Generating tables...")
    generate_all_tables(run_dir)

    # Generate figures
    print("\n[2/2] Generating figures...")
    generate_all_figures(run_dir)

    # Optionally create REPORT.md
    if create_markdown:
        create_report_markdown(run_dir)

    print(f"\n{'='*60}")
    print(f"REPORT COMPLETE")
    print(f"{'='*60}")
    print(f"\nResults directory: {run_dir}")
    print(f"  - Tables: {run_dir / 'tables'}")
    print(f"  - Figures: {run_dir / 'figures'}")
    if create_markdown:
        print(f"  - Report: {run_dir / 'REPORT.md'}")


def create_report_markdown(run_dir: Path) -> None:
    """Create a REPORT.md file that embeds tables and links to figures."""
    report_path = run_dir / "REPORT.md"

    config_path = run_dir / "config.json"
    if config_path.exists():
        import json
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {}

    md_content = f"""# Pathfinding Benchmark Report

**Run ID:** {run_dir.name}
**Date:** {config.get('run_id', 'N/A')}
**Seed:** {config.get('seed', 'N/A')}
**Samples per tier:** {config.get('k', 'N/A')}
**Algorithms:** {', '.join(config.get('algorithms', []))}
**Maps:** {len(config.get('maps', []))} maps
**Timeout:** {config.get('timeout_s', 'N/A')}s
**Max nodes:** {config.get('max_nodes', 'N/A')}

---

## Tables

### T1: Overall Performance

![T1 Overall](tables/t1_overall.md)

### T2: Performance by Distance Tier

![T2 By Distance](tables/t2_by_distance.md)

### T3: Performance by Environment

![T3 By Environment](tables/t3_by_environment.md)

### T4: Performance by Map Size

![T4 By Size](tables/t4_by_size.md)

### T5: Failure Breakdown

![T5 Failure Breakdown](tables/t5_failure_breakdown.md)

---

## Figures

### F1: Median Time by Distance Tier

![F1 Time by Distance](figures/f1_time_by_distance.png)

*Median execution time (ms) grouped by distance tier. Log scale.*

### F2: Nodes Expanded Distribution

![F2 Expanded Boxplot](figures/f2_expanded_boxplot.png)

*Boxplot of nodes expanded (successful runs only). Log scale.*

### F3: Nodes Expanded vs. Optimal Length

![F3 Optimal vs Expanded](figures/f3_optimal_vs_expanded.png)

*Scatter plot showing growth rate of node expansions with path length. Log-log scale.*

### F4: Success Rate by Environment

![F4 Success Heatmap](figures/f4_success_heatmap.png)

*Heatmap of success rate (%) across environment categories.*

### F5: Alpha Distribution

![F5 Alpha Boxplot](figures/f5_alpha_boxplot.png)

*Boxplot of alpha (suboptimality ratio = path_cost / optimal). Red line at 1.0 indicates optimal.*

### F6: Speed vs. Quality Trade-off

![F6 Time vs Alpha](figures/f6_time_vs_alpha.png)

*Scatter plot of median time vs. median alpha. Lower-left corner is ideal (fast and optimal).*

### F7: Performance Profile

![F7 Performance Profile](figures/f7_performance_profile.png)

*Dolan-Moré performance profile. Higher curves indicate more robust performance across scenarios.*

---

## Configuration

```json
{config}
```
"""

    with open(report_path, "w") as f:
        f.write(md_content)

    print(f"Created REPORT.md: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate a complete report from raw benchmark results.")
    parser.add_argument("run_dir", type=str,
                        help="Path to the run directory containing raw.csv")
    parser.add_argument("--no-markdown", action="store_true",
                        help="Skip creating REPORT.md")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Error: Directory {run_dir} does not exist")
        sys.exit(1)

    generate_report(run_dir, create_markdown=not args.no_markdown)


if __name__ == "__main__":
    main()
