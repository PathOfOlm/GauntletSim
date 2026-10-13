"""Seeded Corrupted Gauntlet dungeon layout generator (Phase 2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gauntletsim.game_rules import GameRules
from gauntletsim.rng import make_stream, shuffled, weighted_choice, weighted_index
from gauntletsim.room import (
    Coord,
    DemiType,
    MobTier,
    NodeType,
    Room,
    RoomKind,
    iter_grid,
    orthogonal_neighbors,
)

BOSS_COORD = Coord(3, 3)
CARDINAL_OUTER = {
    "N": Coord(3, 0),
    "E": Coord(6, 3),
    "S": Coord(3, 6),
    "W": Coord(0, 3),
}
DEMI_TYPES = [DemiType.BEAR, DemiType.DRAGON, DemiType.DARK_BEAST]
NODE_TYPES_FOR_FILL = [
    NodeType.ORE,
    NodeType.LINUM,
    NodeType.PHREN,
    NodeType.GRYM,
    NodeType.FISH,
]


@dataclass(frozen=True)
class DungeonLayout:
    """Immutable snapshot of a generated dungeon."""

    master_seed: int
    width: int
    height: int
    boss: Coord
    start: Coord
    fish_room: Coord
    rooms: dict[Coord, Room]
    demi_rooms: tuple[Coord, ...]

    def room(self, coord: Coord) -> Room:
        return self.rooms[coord]


def _assumption_default(rules: GameRules, parameter: str) -> Any:
    return rules.assumption_default(parameter)


def _edge_or_corner_coords(width: int = 7, height: int = 7) -> list[Coord]:
    out: list[Coord] = []
    for c in iter_grid(width, height):
        if c.x in (0, width - 1) or c.y in (0, height - 1):
            out.append(c)
    return out


def _place_nodes(
    rng,
    count: int,
    *,
    force_fish: int | None = None,
) -> dict[NodeType, int]:
    """Distribute `count` nodes across types (mixable). Force fish spots if set."""
    nodes: dict[NodeType, int] = {}
    remaining = count
    if force_fish is not None:
        nodes[NodeType.FISH] = force_fish
        remaining = max(0, count - force_fish)
        # Fish room: wiki guarantees 3 fishing spots; total nodes may be >= 3.
        if count < force_fish:
            nodes[NodeType.FISH] = force_fish
            remaining = 0
    for _ in range(remaining):
        choice = rng.choice(NODE_TYPES_FOR_FILL)
        nodes[choice] = nodes.get(choice, 0) + 1
    return nodes


def generate_layout(rules: GameRules, master_seed: int) -> DungeonLayout:
    """Generate a reproducible 7×7 Corrupted Gauntlet layout."""
    width, height = rules.grid_size
    if width != 7 or height != 7:
        raise ValueError(f"Phase 2 expects 7x7 grid, got {width}x{height}")

    rng = make_stream(master_seed, "dungeon_layout")

    # Start: one of four rooms orthogonally adjacent to boss.
    start_candidates = orthogonal_neighbors(BOSS_COORD, width, height)
    start = rng.choice(start_candidates)

    # Guaranteed 3-fish room: adjacent to boss, not start/boss.
    fish_candidates = [
        c for c in start_candidates if c != start and c != BOSS_COORD
    ]
    fish_room = rng.choice(fish_candidates)

    node_weights = list(_assumption_default(rules, "dungeon.node_count_weights"))
    if len(node_weights) != 6:
        raise ValueError("dungeon.node_count_weights must have 6 entries for 0..5")
    mob_weights_raw = _assumption_default(rules, "dungeon.mob_spawn_weights")
    mob_items = ["none", "weak", "strong"]
    mob_weights = [float(mob_weights_raw[k]) for k in mob_items]
    extra_demi = int(_assumption_default(rules, "dungeon.demi_boss_extra_count"))
    if extra_demi < 0:
        raise ValueError("demi_boss_extra_count must be non-negative")

    rooms: dict[Coord, Room] = {}
    for coord in iter_grid(width, height):
        if coord == BOSS_COORD:
            rooms[coord] = Room(coord=coord, kind=RoomKind.BOSS)
        elif coord == start:
            rooms[coord] = Room(
                coord=coord, kind=RoomKind.START, discovered=True
            )
        else:
            rooms[coord] = Room(coord=coord, kind=RoomKind.RESOURCE)

    # Resource contents (nodes + mobs) — fish room forced.
    for coord, room in rooms.items():
        if room.kind != RoomKind.RESOURCE:
            continue
        if coord == fish_room:
            # At least 3 fishing spots; total nodes in 3..5 so fish fits.
            total = max(3, weighted_index(rng, node_weights))
            # weighted_index returns 0..5; ensure >= 3 for fish room.
            if total < 3:
                total = 3
            room.nodes = _place_nodes(rng, total, force_fish=3)
        else:
            total = weighted_index(rng, node_weights)
            room.nodes = _place_nodes(rng, total)
        tier_name = weighted_choice(rng, mob_items, mob_weights)
        room.mob_tier = MobTier(tier_name)

    # Demi-bosses: 4 cardinals + extras on edges/corners.
    demi_coords: list[Coord] = []
    for card in CARDINAL_OUTER.values():
        room = rooms[card]
        if room.kind == RoomKind.START:
            # Extremely unlikely (start is adjacent to boss, cardinals are outer).
            continue
        room.mob_tier = MobTier.DEMI_BOSS
        room.demi_type = rng.choice(DEMI_TYPES)
        demi_coords.append(card)

    occupied = set(demi_coords) | {BOSS_COORD, start}
    edge_pool = [
        c
        for c in _edge_or_corner_coords(width, height)
        if c not in occupied and rooms[c].kind == RoomKind.RESOURCE
    ]
    edge_pool = shuffled(rng, edge_pool)
    for coord in edge_pool[:extra_demi]:
        room = rooms[coord]
        room.mob_tier = MobTier.DEMI_BOSS
        room.demi_type = rng.choice(DEMI_TYPES)
        demi_coords.append(coord)

    return DungeonLayout(
        master_seed=master_seed,
        width=width,
        height=height,
        boss=BOSS_COORD,
        start=start,
        fish_room=fish_room,
        rooms=rooms,
        demi_rooms=tuple(demi_coords),
    )


def validate_layout_rules(layout: DungeonLayout, rules: GameRules) -> list[str]:
    """Return human-readable violations (empty if legal)."""
    errors: list[str] = []
    if layout.boss != BOSS_COORD:
        errors.append("boss not at center")
    if layout.start.manhattan(layout.boss) != 1:
        errors.append("start not orthogonally adjacent to boss")
    if layout.fish_room.manhattan(layout.boss) != 1:
        errors.append("fish room not adjacent to boss")
    if layout.fish_room == layout.start:
        errors.append("fish room coincides with start")
    fish_room = layout.room(layout.fish_room)
    if fish_room.fishing_spots < 3:
        errors.append("fish room has fewer than 3 fishing spots")

    for card in CARDINAL_OUTER.values():
        room = layout.room(card)
        if room.mob_tier != MobTier.DEMI_BOSS:
            errors.append(f"cardinal {card} missing demi-boss")

    for coord in layout.demi_rooms:
        room = layout.room(coord)
        if not (room.is_edge or room.is_corner):
            errors.append(f"demi-boss at non-edge {coord}")
        if room.demi_type is None:
            errors.append(f"demi-boss at {coord} missing type")

    # Full orthogonal connectivity: every in-bounds orthogonal neighbor is an edge.
    for coord in layout.rooms:
        for n in orthogonal_neighbors(coord, layout.width, layout.height):
            if n not in layout.rooms:
                errors.append(f"missing neighbor room {n}")

    expected_extra = int(rules.assumption_default("dungeon.demi_boss_extra_count"))
    # Cardinals always 4 when start isn't on a cardinal (it never is).
    if len(layout.demi_rooms) != 4 + expected_extra:
        # Allow if edge pool was smaller than requested (shouldn't happen on 7x7).
        if len(layout.demi_rooms) < 4:
            errors.append(f"expected at least 4 demi rooms, got {len(layout.demi_rooms)}")
        elif len(layout.demi_rooms) != 4 + expected_extra:
            errors.append(
                f"demi count {len(layout.demi_rooms)} != 4+{expected_extra}"
            )

    return errors
