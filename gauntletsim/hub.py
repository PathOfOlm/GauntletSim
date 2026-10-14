"""Starting-room hub stations (singing bowl, range, water pump, …)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from gauntletsim.game_rules import GameRules
from gauntletsim.geometry import DungeonGeometry, Tile
from gauntletsim.room import Coord


class HubStation(str, Enum):
    SINGING_BOWL = "singing_bowl"
    RANGE = "range"
    WATER_PUMP = "water_pump"
    TOOL_STORAGE = "tool_storage"
    TELEPORT_PLATFORM = "teleport_platform"
    RECIPE_GUIDES = "recipe_guides"


class HubError(ValueError):
    """Illegal hub interaction (wrong station / not adjacent)."""


# Wiki File:The_Gauntlet_Starting_Room.png quadrants (N=low ly in our geometry).
# Exact local tiles are assumptions for room_size=16; see A-HUB-STATIONS-01.
_DEFAULT_LOCAL: dict[str, list[int]] = {
    "singing_bowl": [4, 4],  # NW — craft / sing
    "teleport_platform": [11, 4],  # NE — abandon challenge
    "tool_storage": [8, 8],  # center pedestal
    "water_pump": [12, 7],  # E wall, slightly N of mid (east door)
    "range": [11, 12],  # SE — cook paddlefish
    "recipe_guides": [4, 12],  # SW — bookstands (non-blocking interact)
}


@dataclass(frozen=True)
class HubLayout:
    """Hub station object tiles in the start room (local + global)."""

    start: Coord
    # station -> list of blocked/object local tiles
    locals: dict[HubStation, tuple[tuple[int, int], ...]]
    room_size: int

    def object_locals(self, station: HubStation) -> tuple[tuple[int, int], ...]:
        return self.locals[station]

    def object_tiles(self, station: HubStation) -> list[Tile]:
        out: list[Tile] = []
        for lx, ly in self.locals[station]:
            out.append(
                Tile(self.start.x * self.room_size + lx, self.start.y * self.room_size + ly)
            )
        return out

    def primary_tile(self, station: HubStation) -> Tile:
        return self.object_tiles(station)[0]


def load_hub_local_map(rules: GameRules) -> dict[str, list[int]]:
    raw = rules.assumption_default("topology.hub_station_local_tiles")
    if not isinstance(raw, dict):
        return dict(_DEFAULT_LOCAL)
    merged = dict(_DEFAULT_LOCAL)
    for key, value in raw.items():
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            merged[str(key)] = [int(value[0]), int(value[1])]
    return merged


def build_hub_layout(rules: GameRules, start: Coord) -> HubLayout:
    size = int(rules.assumption_default("topology.room_size_tiles"))
    coords = load_hub_local_map(rules)
    locals_map: dict[HubStation, tuple[tuple[int, int], ...]] = {}
    for station in HubStation:
        pair = coords[station.value]
        lx, ly = int(pair[0]), int(pair[1])
        # Keep on interior (not perimeter wall).
        lx = max(1, min(size - 2, lx))
        ly = max(1, min(size - 2, ly))
        locals_map[station] = ((lx, ly),)
    return HubLayout(start=start, locals=locals_map, room_size=size)


def apply_hub_blocks(geometry: DungeonGeometry, hub: HubLayout) -> None:
    """Mark hub scenery tiles blocked (interact from adjacent tiles)."""
    rt = geometry.rooms[hub.start]
    # Clear corridor first, then place scenery so tool storage stays solid.
    from gauntletsim.geometry import _ensure_door_connectivity
    import random

    _ensure_door_connectivity(rt, random.Random(0))
    for _station, tiles in hub.locals.items():
        for lx, ly in tiles:
            rt.blocked.add((lx, ly))


def is_adjacent_to_station(
    geometry: DungeonGeometry,
    hub: HubLayout,
    tile: Tile | None,
    station: HubStation,
) -> bool:
    if tile is None:
        return False
    if geometry.room_of(tile) != hub.start:
        return False
    for obj in hub.object_tiles(station):
        if max(abs(tile.x - obj.x), abs(tile.y - obj.y)) <= 1 and tile != obj:
            return True
        # Standing on the object tile is not allowed (blocked), but tolerate equality
        # if somehow unblocked in tests.
        if tile == obj:
            return True
    return False


def nearest_approach_tile(
    geometry: DungeonGeometry,
    hub: HubLayout,
    station: HubStation,
    *,
    discovered: set[Coord] | None = None,
) -> Tile:
    """Nearest walkable tile adjacent to the station object."""
    candidates: list[Tile] = []
    for obj in hub.object_tiles(station):
        for n in obj.neighbors8():
            if geometry.room_of(n) != hub.start:
                continue
            if not geometry.is_walkable(n, discovered=discovered):
                continue
            candidates.append(n)
    if not candidates:
        raise HubError(f"no approach tile for {station.value}")
    # Prefer south/east of object for stable demo paths; else first by coord.
    candidates.sort(key=lambda t: (t.y, t.x))
    return candidates[0]


def station_for_action(action: str) -> HubStation:
    """Map prep actions to required hub stations."""
    key = action.lower()
    if key in {"sing", "craft", "vial", "weapon", "armour", "bowl"}:
        return HubStation.SINGING_BOWL
    if key in {"cook", "range", "paddlefish"}:
        return HubStation.RANGE
    if key in {"fill", "pump", "water"}:
        return HubStation.WATER_PUMP
    if key in {"tools", "tool_storage"}:
        return HubStation.TOOL_STORAGE
    raise HubError(f"unknown hub action {action!r}")


def require_start_room(player_coord: Coord, hub: HubLayout) -> None:
    if player_coord != hub.start:
        raise HubError("must be in starting room for hub stations")
