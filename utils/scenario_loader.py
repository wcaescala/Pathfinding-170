# Initial commit: 10/14/2025 
# Last updated: 10/14/2025 12:42PM

from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Scenario:
    bucket: int
    map_name: str
    map_width: int
    map_height: int
    start: tuple[int, int]
    goal: tuple[int, int]
    optimal_length: float
 
    def __repr__(self) -> str:
        return (f"Scenario(bucket={self.bucket}, start={self.start}, "
                f"goal={self.goal}, optimal={self.optimal_length:.4f})")
 
 
def load_scenarios(path: str | Path) -> list[Scenario]:
    # Load a Moving AI .scen file (tab/whitespace separated, 9 columns).
    scenarios: list[Scenario] = []
    with Path(path).open("r", encoding="utf-8", errors="replace") as f:
        for line_no, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.lower().startswith("version"):
                continue
            parts = line.split()
            if len(parts) != 9:
                raise ValueError(
                    f"{path}:{line_no}: expected 9 fields, got {len(parts)}")
            bucket, name, w, h, sx, sy, gx, gy, opt = parts
            scenarios.append(Scenario(
                int(bucket), name, int(w), int(h),
                (int(sx), int(sy)), (int(gx), int(gy)), float(opt)))
    return scenarios
 