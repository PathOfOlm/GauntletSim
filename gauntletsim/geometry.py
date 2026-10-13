"""Intra-room tile geometry: walls, doorways, spawnable obstacles (Phase 3.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
import random

from gauntletsim.game_rules import GameRules
from gauntletsim.rng import make_stream
from gauntletsim.room import Coord, Room, RoomKind


@dataclass(frozen=True, order=True)
class Tile:
    """Global tile coordinate across the 7×7 room grid."""

    x: int
    y: int

    def neighbors8(self) -> list[Tile]:
        out: list[Tile] = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                out.append(Tile(self.x + dx, self.y + dy))
        return out


@dataclass
class RoomTiles:
    """Walkability for one room's local grid (size × size)."""

    room: Coord
    size: int
    blocked: set[tuple[int, int]] = field(default_factory=set)
    doorways: dict[str, list[tuple[int, int]]] = field(default_factory=dict)

    def local_walkable(self, lx: int, ly: int) -> bool:
        if not (0 <= lx < self.size and 0 <= ly < self.size):
            return False
        return (lx, ly) not in self.blocked

    def to_global(self, lx: int, ly: int) -> Tile:
        return Tile(self.room.x * self.size + lx, self.room.y * self.size + ly)

    def center_local(self) -> tuple[int, int]:
        c = self.size // 2
        return c, c

    def center_tile(self) -> Tile:
        lx, ly = self.center_local()
        # Prefer nearest walkable to geometric center.
        if self.local_walkable(lx, ly):
            return self.to_global(lx, ly)
        for r in range(1, self.size):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    nx, ny = lx + dx, ly + dy
                    if self.local_walkable(nx, ny):
                        return self.to_global(nx, ny)
        raise RuntimeError(f"no walkable tile in room {self.room}")


@dataclass
class DungeonGeometry:
    """Full dungeon walkability map."""

    room_size: int
    doorway_width: int
    rooms: dict[Coord, RoomTiles]
    width_rooms: int = 7
    height_rooms: int = 7

    def room_of(self, tile: Tile) -> Coord:
        return Coord(tile.x // self.room_size, tile.y // self.room_size)

    def local_of(self, tile: Tile) -> tuple[int, int]:
        return tile.x % self.room_size, tile.y % self.room_size

    def is_walkable(self, tile: Tile, *, discovered: set[Coord] | None = None) -> bool:
        room = self.room_of(tile)
        if room not in self.rooms:
            return False
        if discovered is not None and room not in discovered:
            return False
        lx, ly = self.local_of(tile)
        return self.rooms[room].local_walkable(lx, ly)

    def spawn_tile(self, start: Coord) -> Tile:
        return self.rooms[start].center_tile()


def _doorway_locals(
    size: int, width: int, direction: str
) -> list[tuple[int, int]]:
    """Local tiles of a doorway centered on a room edge."""
    mid = size // 2
    half = width // 2
    start = mid - half
    tiles: list[tuple[int, int]] = []
    for i in range(width):
        if direction == "n":
            tiles.append((start + i, 0))
        elif direction == "s":
            tiles.append((start + i, size - 1))
        elif direction == "w":
            tiles.append((0, start + i))
        elif direction == "e":
            tiles.append((size - 1, start + i))
        else:
            raise ValueError(direction)
    return tiles


def _ensure_door_connectivity(rt: RoomTiles, rng: random.Random) -> None:
    """Clear a plus-shaped corridor so all doorways remain mutually reachable."""
    size = rt.size
    cx, cy = size // 2, size // 2
    door_set: set[tuple[int, int]] = set()
    for tiles in rt.doorways.values():
        door_set.update(tiles)

    def clear(lx: int, ly: int) -> None:
        rt.blocked.discard((lx, ly))

    # Keep a cross through the center and spokes to each door.
    for x in range(size):
        clear(x, cy)
    for y in range(size):
        clear(cx, y)
    for lx, ly in door_set:
        if lx == 0 or lx == size - 1:
            for x in range(min(lx, cx), max(lx, cx) + 1):
                clear(x, ly)
        if ly == 0 or ly == size - 1:
            for y in range(min(ly, cy), max(ly, cy) + 1):
                clear(lx, y)

    # Soften rare RNG clobber: if still disconnected, carve toward center.
    from collections import deque

    if not door_set:
        return
    start = next(iter(door_set))
    q = deque([start])
    seen = {start}
    while q:
        cur = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (cur[0] + dx, cur[1] + dy)
            if not (0 <= n[0] < size and 0 <= n[1] < size):
                continue
            if n in rt.blocked or n in seen:
                continue
            seen.add(n)
            q.append(n)
    for d in door_set:
        if d in seen:
            continue
        # Carve L-path via center.
        x, y = d
        while x != cx:
            clear(x, y)
            x += 1 if cx > x else -1
        while y != cy:
            clear(x, y)
            y += 1 if cy > y else -1
        clear(cx, cy)
    _ = rng  # reserved for future organic corridor jitter


def build_room_tiles(
    room_coord: Coord,
    room: Room,
    *,
    size: int,
    doorway_width: int,
    wall_density: float,
    rng: random.Random,
    grid_w: int,
    grid_h: int,
) -> RoomTiles:
    rt = RoomTiles(room=room_coord, size=size)
    # Perimeter walls.
    for x in range(size):
        rt.blocked.add((x, 0))
        rt.blocked.add((x, size - 1))
    for y in range(size):
        rt.blocked.add((0, y))
        rt.blocked.add((size - 1, y))

    dirs = {
        "n": Coord(room_coord.x, room_coord.y - 1),
        "s": Coord(room_coord.x, room_coord.y + 1),
        "w": Coord(room_coord.x - 1, room_coord.y),
        "e": Coord(room_coord.x + 1, room_coord.y),
    }
    for dname, neighbor in dirs.items():
        if not (0 <= neighbor.x < grid_w and 0 <= neighbor.y < grid_h):
            continue
        # Boss room still gets doorways (entry via barrier later); resource links always.
        opening = _doorway_locals(size, doorway_width, dname)
        rt.doorways[dname] = opening
        for t in opening:
            rt.blocked.discard(t)

    # Start / hub rooms: keep interior open (no random walls).
    if room.kind in {RoomKind.START, RoomKind.BOSS}:
        _ensure_door_connectivity(rt, rng)
        return rt

    # Interior obstacle sprinkle (not on perimeter — already walls/doors).
    for ly in range(1, size - 1):
        for lx in range(1, size - 1):
            if rng.random() < wall_density:
                rt.blocked.add((lx, ly))
    _ensure_door_connectivity(rt, rng)
    return rt


def generate_dungeon_geometry(
    rules: GameRules,
    rooms: dict[Coord, Room],
    master_seed: int,
) -> DungeonGeometry:
    size = int(rules.assumption_default("topology.room_size_tiles"))
    door_w = int(rules.assumption_default("topology.doorway_width_tiles"))
    density = float(rules.assumption_default("topology.interior_wall_density"))
    width, height = rules.grid_size
    rng = make_stream(master_seed, "room_geometry")
    built: dict[Coord, RoomTiles] = {}
    for coord, room in rooms.items():
        built[coord] = build_room_tiles(
            coord,
            room,
            size=size,
            doorway_width=door_w,
            wall_density=density,
            rng=rng,
            grid_w=width,
            grid_h=height,
        )
    return DungeonGeometry(
        room_size=size,
        doorway_width=door_w,
        rooms=built,
        width_rooms=width,
        height_rooms=height,
    )


def doorway_entry_tile(
    geometry: DungeonGeometry,
    from_room: Coord,
    to_room: Coord,
) -> Tile:
    """Walkable doorway tile on the *destination* room side."""
    dx = to_room.x - from_room.x
    dy = to_room.y - from_room.y
    if abs(dx) + abs(dy) != 1:
        raise ValueError("rooms must be orthogonal neighbors")
    if dx == 1:
        dname = "w"  # entering from west
    elif dx == -1:
        dname = "e"
    elif dy == 1:
        dname = "n"
    else:
        dname = "s"
    rt = geometry.rooms[to_room]
    locals_ = rt.doorways.get(dname)
    if not locals_:
        # Fallback: center of shared edge
        c = rt.size // 2
        if dname == "w":
            locals_ = [(0, c)]
        elif dname == "e":
            locals_ = [(rt.size - 1, c)]
        elif dname == "n":
            locals_ = [(c, 0)]
        else:
            locals_ = [(c, rt.size - 1)]
    lx, ly = locals_[0]
    return rt.to_global(lx, ly)


def force_block_tile(geometry: DungeonGeometry, tile: Tile) -> None:
    """Test helper: mark a global tile blocked inside its room."""
    room = geometry.room_of(tile)
    lx, ly = geometry.local_of(tile)
    geometry.rooms[room].blocked.add((lx, ly))
