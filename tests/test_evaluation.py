"""
Unit tests for the evaluation sampling and metrics module.
"""

import unittest
from pathlib import Path
import sys
import math

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.sampler import (
    BenchmarkSampler,
    classify_size_tier,
    classify_distance_tier,
)
from evaluation.metrics import (
    compute_statistics,
    ScenarioEvaluationRecord,
    aggregate_records,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestEvaluation(unittest.TestCase):

    def test_tier_classification(self):
        self.assertEqual(classify_size_tier(15_000), "Small")
        self.assertEqual(classify_size_tier(100_000), "Medium")
        self.assertEqual(classify_size_tier(500_000), "Large")

        self.assertEqual(classify_distance_tier(10.0, 2), "Short")
        self.assertEqual(classify_distance_tier(50.0, 10), "Medium")
        self.assertEqual(classify_distance_tier(150.0, 30), "Long")

    def test_statistics_computation(self):
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        mean, med, std, v_min, v_max = compute_statistics(vals)
        self.assertAlmostEqual(mean, 30.0)
        self.assertAlmostEqual(med, 30.0)
        self.assertAlmostEqual(v_min, 10.0)
        self.assertAlmostEqual(v_max, 50.0)
        self.assertGreater(std, 0.0)

    def test_sampler_indexing(self):
        bench_dir = PROJECT_ROOT / "benchmarks"
        sampler = BenchmarkSampler(bench_dir)
        self.assertEqual(len(sampler.metadata_catalog), 67)
        self.assertIn("ca_cave.map", sampler.metadata_catalog)

        # Sample scenarios
        sampled = sampler.sample_scenarios(map_names=["ht_store.map"], samples_per_tier=1, seed=42)
        self.assertGreaterEqual(len(sampled), 1)
        for item in sampled:
            self.assertEqual(item.map_name, "ht_store.map")


if __name__ == "__main__":
    unittest.main()
