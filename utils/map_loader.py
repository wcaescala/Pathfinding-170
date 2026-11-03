# Initial commit: 10/14/2025 
# Last updated: 10/14/2025 12:38PM 

import numpy as np
from pathlib import Path # Standard library import
from typing import Iterable # Standard library import
import math
from dataclasses import dataclass

DEFAULT_PASSABLE = frozenset(".GS")
SQRT2 = math.sqrt(2)

# 8-direction movements: (dx, dy, cost)
_MOVES = (
    (0, -1, 1.0),    # North
    (0, 1, 1.0),     # South
    (-1, 0, 1.0),    # West
    (1, 0, 1.0),     # East
    (-1, -1, SQRT2), # North-West
    (1, -1, SQRT2),  # North-East
    (-1, 1, SQRT2),  # South-West
    (1, 1, SQRT2),   # South-East
)

@dataclass
class GridMap:
    # A grid map. `tiles` has shape (height, width) and holds single chars.
    name: str
    width: int
    height: int
    tiles: np.ndarray                      # dtype '<U1', indexed [y, x]
    passable_chars: frozenset = DEFAULT_PASSABLE
 
    # Initialize the grid map
    def __post_init__(self) -> None:
        self._refresh_passable()
 
    # Refresh the passable array for the current passable characters
    def _refresh_passable(self) -> None:
        self.passable = np.isin(self.tiles, list(self.passable_chars))
 
    # Set the passable characters to the given characters and refresh the passable array
    def set_passable_chars(self, chars: Iterable[str]) -> None:
        self.passable_chars = frozenset(chars)
        self._refresh_passable()
 
    # Check if a position is within the bounds of the grid
    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height
 
    # Check if a position is passable
    def is_passable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and bool(self.passable[y, x])
 
    # Get the neighbors of a position
    def neighbors(self, x: int, y: int):
        # Yield ((nx, ny), cost) for legal moves, forbidding corner cutting.
        for dx, dy, cost in _MOVES:
            nx, ny = x + dx, y + dy
            if not self.is_passable(nx, ny):
                continue
            if dx and dy and not (self.is_passable(x + dx, y)
                                  and self.is_passable(x, y + dy)):
                continue
            yield (nx, ny), cost
 
    # String representation of the grid map
    def __repr__(self) -> str:
        return (f"GridMap(name={self.name!r}, {self.width}x{self.height}, "
                f"passable={int(self.passable.sum())} cells)")
 
 
def load_map(path: str | Path, passable_chars: Iterable[str] = DEFAULT_PASSABLE) -> GridMap:
    # Load a Moving AI .map file (octile format).
    path = Path(path)
    with path.open("r", encoding="utf-8", errors="replace") as f:
        lines = [ln.rstrip("\r\n") for ln in f]
 
    # Parse the header
    header: dict[str, str] = {}
    idx = 0
    # Loop through the lines until we reach the map header
    while idx < len(lines):
        line = lines[idx].strip()
        idx += 1
        if line == "map":
            break
        if line:
            key, _, value = line.partition(" ")
            header[key.lower()] = value.strip()
    else:
        raise ValueError(f"{path}: missing 'map' header terminator")
 
    try:
        height, width = int(header["height"]), int(header["width"])
    except KeyError as e:
        raise ValueError(f"{path}: missing header field {e}") from None
 
    # Get the rows of the map
    rows = [ln for ln in lines[idx:] if ln != ""][:height]
    if len(rows) != height:
        raise ValueError(f"{path}: expected {height} rows, found {len(rows)}")
    # Check the length of each row
    for i, row in enumerate(rows):
        if len(row) != width:
            raise ValueError(
                f"{path}: row {i} has length {len(row)}, expected {width}")
 
    # Create the tiles array
    tiles = np.array([list(r) for r in rows], dtype="<U1")
    return GridMap(path.name, width, height, tiles, frozenset(passable_chars))
 
 