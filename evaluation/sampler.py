"""
Sampling module for Dragon Age 2 (DA2) Moving AI Benchmark.
Provides stratified sampling across map environments, map size tiers, 
and scenario difficulty/distance buckets.
No high-level or external graph libraries are used.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import random

from utils.scenario_loader import Scenario, load_scenarios
from utils.map_loader import GridMap, load_map


# Map categories in Dragon Age 2
ENVIRONMENT_CATEGORIES = {
    "ca": "Caves & Caverns",
    "dr": "Deep Roads & Dungeons",
    "ht": "Hightown (Urban & Estates)",
    "lt": "Lowtown (Slums & Alleys)",
    "w": "Wilderness & Outskirts",
}


@dataclass
class MapMetadata:
    name: str
    category: str
    category_name: str
    width: int
    height: int
    total_cells: int
    size_tier: str  # "Small", "Medium", "Large"
    map_path: Path
    scenario_path: Path
    scenario_count: int


@dataclass
class SampledScenario:
    map_name: str
    map_metadata: MapMetadata
    scenario: Scenario
    distance_tier: str  # "Short", "Medium", "Long"


def classify_size_tier(total_cells: int) -> str:
    """Classifies map into Small, Medium, or Large tier based on cell count."""
    if total_cells < 30_000:
        return "Small"
    elif total_cells < 200_000:
        return "Medium"
    else:
        return "Large"


def classify_distance_tier(optimal_length: float, bucket: int) -> str:
    """Classifies scenario into Short, Medium, or Long distance tier."""
    if optimal_length < 20.0 or bucket <= 4:
        return "Short"
    elif optimal_length <= 100.0 or bucket <= 19:
        return "Medium"
    else:
        return "Long"


class BenchmarkSampler:
    """
    Manages discovery and stratified sampling of Dragon Age 2 maps and scenarios.
    """

    def __init__(self, benchmark_dir: Path | str):
        self.benchmark_dir = Path(benchmark_dir)
        self.maps_dir = self.benchmark_dir / "maps"
        self.scenarios_dir = self.benchmark_dir / "scenarios"
        self.metadata_catalog: Dict[str, MapMetadata] = {}
        self._index_dataset()

    def _index_dataset(self) -> None:
        """Indexes all available .map and .map.scen files."""
        for map_file in sorted(self.maps_dir.glob("*.map")):
            scen_file = self.scenarios_dir / f"{map_file.name}.scen"
            if not scen_file.exists():
                continue

            # Read map dimensions from header
            w, h = 0, 0
            with map_file.open("r", encoding="utf-8", errors="replace") as f:
                for _ in range(6):
                    line = f.readline().strip()
                    if line.startswith("width"):
                        w = int(line.split()[1])
                    elif line.startswith("height"):
                        h = int(line.split()[1])

            prefix = map_file.name.split("_")[0]
            cat_name = ENVIRONMENT_CATEGORIES.get(prefix, "Other")
            total = w * h
            tier = classify_size_tier(total)

            # Quick count of scenario entries
            with scen_file.open("r", encoding="utf-8", errors="replace") as sf:
                scen_count = sum(1 for line in sf if line.strip() and not line.lower().startswith("version"))

            self.metadata_catalog[map_file.name] = MapMetadata(
                name=map_file.name,
                category=prefix,
                category_name=cat_name,
                width=w,
                height=h,
                total_cells=total,
                size_tier=tier,
                map_path=map_file,
                scenario_path=scen_file,
                scenario_count=scen_count,
            )

    def get_representative_maps(self) -> List[str]:
        """
        Returns a balanced default portfolio of representative maps spanning
        all 5 environments and 3 size tiers.
        """
        return [
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

    def sample_scenarios(
        self,
        map_names: Optional[List[str]] = None,
        samples_per_tier: int = 4,
        seed: int = 42
    ) -> List[SampledScenario]:
        """
        Samples scenarios across Short, Medium, and Long distance tiers.

        Parameters:
            map_names: Specific map filenames to sample from. Defaults to representative set.
            samples_per_tier: Number of scenarios to sample from each distance tier per map.
            seed: Deterministic random seed for benchmark reproducibility.

        Returns:
            List of SampledScenario objects.
        """
        rng = random.Random(seed)
        target_maps = map_names if map_names is not None else self.get_representative_maps()
        sampled: List[SampledScenario] = []

        for name in target_maps:
            meta = self.metadata_catalog.get(name)
            if not meta:
                continue

            all_scens = load_scenarios(meta.scenario_path)

            # Partition scenarios into distance tiers
            tiers: Dict[str, List[Scenario]] = {
                "Short": [],
                "Medium": [],
                "Long": []
            }

            for s in all_scens:
                dt = classify_distance_tier(s.optimal_length, s.bucket)
                tiers[dt].append(s)

            for dt in ["Short", "Medium", "Long"]:
                pool = tiers[dt]
                if not pool:
                    continue
                k = min(samples_per_tier, len(pool))
                chosen = rng.sample(pool, k)
                # Sort selected scenarios by optimal length for clean progression
                chosen.sort(key=lambda s: s.optimal_length)
                for sc in chosen:
                    sampled.append(SampledScenario(
                        map_name=name,
                        map_metadata=meta,
                        scenario=sc,
                        distance_tier=dt
                    ))

        return sampled
