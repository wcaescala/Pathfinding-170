import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

map_file_path = project_root / "benchmarks" / "maps" / "ca_cave.map"
scenario_file_path = project_root / "benchmarks" / "scenarios" / "ca_cave.map.scen"

from utils.map_loader import load_map
from utils.scenario_loader import load_scenarios

# Test loading a map
map = load_map(map_file_path)

# Test loading scenarios
scenarios = load_scenarios(scenario_file_path)
print(map)
print(scenarios[0]) # Print the first scenario for testing
