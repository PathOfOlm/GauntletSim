"""Room and coordinate types for the Corrupted Gauntlet grid."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class RoomKind(str, Enum):
    BOSS = "boss"
    START = "start"
    RESOURCE = "resource"


class MobTier(str, Enum):
    NONE = "none"
    WEAK = "weak"
    STRONG = "strong"
    DEMI_BOSS = "demi_boss"


class DemiType(str, Enum):
    BEAR = "bear"
    DRAGON = "dragon"
    DARK_BEAST = "dark_beast"


class NodeType(str, Enum):
    ORE = "ore_deposit"
    LINUM = "linum_tirinum"
    PHREN = "phren_roots"
    GRYM = "grym_root"
    FISH = "fishing_spot"


@dataclass(frozen=True, order=True)
class Coord:
    x: int
    y: int

    def neighbors(self) -> tuple[Coord, Coord, Coord, Coord]:
        return (
            Coord(self.x, self.y - 1),
            Coord(self.x + 1, self.y),
            Coord(self.x, self.y + 1),
            Coord(self.x - 1, self.y),
        )

    def manhattan(self, other: Coord) -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)


DIRECTIONS = {
    "N": Coord(0, -1),
    "E": Coord(1, 0),
    "S": Coord(0, 1),
    "W": Coord(-1, 0),
}


@dataclass
class Room:
    coord: Coord
    kind: RoomKind
    exists: bool = True
    discovered: bool = False
    searched_depleted: bool = False
    mob_tier: MobTier = MobTier.NONE
    demi_type: DemiType | None = None
    # Node multiset counts by type (Phase 2 layout only; gathering is Phase 3).
    nodes: dict[NodeType, int] = field(default_factory=dict)

    @property
    def is_edge(self) -> bool:
        """True if room is on the outer ring of a 7×7 grid (0..6)."""
        return self.coord.x in (0, 6) or self.coord.y in (0, 6)

    @property
    def is_corner(self) -> bool:
        return self.coord.x in (0, 6) and self.coord.y in (0, 6)

    @property
    def fishing_spots(self) -> int:
        return self.nodes.get(NodeType.FISH, 0)

    def node_count(self) -> int:
        return sum(self.nodes.values())


def in_bounds(coord: Coord, width: int = 7, height: int = 7) -> bool:
    return 0 <= coord.x < width and 0 <= coord.y < height


def orthogonal_neighbors(
    coord: Coord, width: int = 7, height: int = 7
) -> list[Coord]:
    return [n for n in coord.neighbors() if in_bounds(n, width, height)]


def iter_grid(width: int = 7, height: int = 7) -> Iterable[Coord]:
    for y in range(height):
        for x in range(width):
            yield Coord(x, y)
