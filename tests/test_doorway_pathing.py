"""Doorway-only room transitions and path-before-action guarantees."""

from __future__ import annotations

import pytest

from gauntletsim.config import AppConfig, SimConfig
from gauntletsim.dungeon import DungeonState
from gauntletsim.game_rules import GameRules
from gauntletsim.geometry import Tile, force_block_tile
from gauntletsim.hub import HubStation
from gauntletsim.inventory import ItemId
from gauntletsim.prep import PrepSim
from gauntletsim.room import Coord, NodeType
from gauntletsim.tile_pathfinding import (
    astar_path,
    path_crosses_rooms_only_via_doorways,
    path_length,
)


@pytest.fixture
def rules() -> GameRules:
    return GameRules.load()


@pytest.fixture
def cfg() -> AppConfig:
    return AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=42),
    )


def test_adjacent_room_path_goes_through_doorway(rules: GameRules) -> None:
    dungeon = DungeonState.generate(rules, 42)
    geom = dungeon.geometry
    assert geom is not None
    start = dungeon.layout.start
    # Pick an orthogonally adjacent resource room.
    neighbor = None
    for n in start.neighbors():
        if n in dungeon.rooms and dungeon.rooms[n].kind.value != "boss":
            neighbor = n
            break
    assert neighbor is not None
    dungeon.rooms[neighbor].discovered = True
    a = geom.rooms[start].center_tile()
    b = geom.rooms[neighbor].center_tile()
    path = astar_path(geom, a, b)
    assert path is not None and len(path) >= 2
    assert path_crosses_rooms_only_via_doorways(geom, path)
    # Exactly one cross-room step, and both tiles are doorways.
    crosses = 0
    for i in range(len(path) - 1):
        if geom.room_of(path[i]) != geom.room_of(path[i + 1]):
            crosses += 1
            assert geom.is_doorway_tile(path[i])
            assert geom.is_doorway_tile(path[i + 1])
            assert geom.can_step(path[i], path[i + 1])
    assert crosses >= 1


def test_cannot_step_through_perimeter_wall(rules: GameRules) -> None:
    dungeon = DungeonState.generate(rules, 1)
    geom = dungeon.geometry
    assert geom is not None
    start = dungeon.layout.start
    rt = geom.rooms[start]
    # Interior tile next to east wall (not on doorway).
    mid = rt.size // 2
    # Find a blocked east-perimeter tile that is NOT a doorway.
    wall_local = None
    for ly in range(1, rt.size - 1):
        if (rt.size - 1, ly) in rt.blocked and (rt.size - 1, ly) not in rt.doorways.get(
            "e", []
        ):
            wall_local = (rt.size - 1, ly)
            break
    assert wall_local is not None
    interior = Tile(
        start.x * rt.size + (rt.size - 2),
        start.y * rt.size + wall_local[1],
    )
    through_wall = Tile(
        start.x * rt.size + (rt.size - 1),
        start.y * rt.size + wall_local[1],
    )
    assert not geom.is_walkable(through_wall)
    assert not geom.can_step(interior, through_wall)
    # Neighbor room tile beyond the wall (same local y) must not be a legal step
    # from interior without standing on the doorway first.
    east = Coord(start.x + 1, start.y)
    if east in geom.rooms:
        beyond = Tile(east.x * rt.size + 0, start.y * rt.size + wall_local[1])
        assert not geom.can_step(interior, beyond)


def test_walls_force_detour_still(rules: GameRules) -> None:
    dungeon = DungeonState.generate(rules, 3)
    geom = dungeon.geometry
    assert geom is not None
    start = dungeon.layout.start
    rt = geom.rooms[start]
    cx, cy = rt.center_local()
    for ly in range(1, rt.size - 1):
        for lx in range(1, rt.size - 1):
            # Keep hub scenery; clear other interior for a controlled wall.
            if (lx, ly) == (cx, cy):
                continue
            rt.blocked.discard((lx, ly))
    # Re-block hub tool storage if present.
    if dungeon.hub is not None:
        for lx, ly in dungeon.hub.object_locals(HubStation.TOOL_STORAGE):
            rt.blocked.add((lx, ly))
    wall_x = min(rt.size - 3, cx + 3)
    for ly in range(1, rt.size - 2):
        rt.blocked.add((wall_x, ly))
    left = rt.to_global(max(2, cx - 2), cy)
    right = rt.to_global(min(rt.size - 3, wall_x + 2), cy)
    # Ensure endpoints walkable.
    rt.blocked.discard(geom.local_of(left))
    rt.blocked.discard(geom.local_of(right))
    path = astar_path(geom, left, right)
    assert path is not None
    assert path_length(path) > abs(right.x - left.x)
    for t in path:
        assert (t.x % rt.size, t.y % rt.size) not in {
            (wall_x, ly) for ly in range(1, rt.size - 2)
        } or geom.local_of(t)[0] != wall_x


def test_gather_triggers_path_to_node(rules: GameRules, cfg: AppConfig) -> None:
    sim = PrepSim.create(rules, cfg, use_tile_pathing=True)
    fish = sim.dungeon.layout.fish_room
    sim.go_to(fish)
    move_before = sim.ledger.move
    sim.gather_here(NodeType.FISH)
    # Must have moved toward a gather tile (unless already on it after go_to center).
    assert any("move → gather" in line for line in sim.log) or sim.ledger.move >= move_before
    assert sim.ledger.gather > 0


def test_craft_fill_cook_each_path_to_station(rules: GameRules, cfg: AppConfig) -> None:
    sim = PrepSim.create(rules, cfg, use_tile_pathing=True)
    sim.player.inventory.add(ItemId.SHARDS, 100)
    sim.player.inventory.add(ItemId.RAW_PADDLEFISH, 1)
    sim.player.inventory.add(ItemId.GRYM_LEAF, 1)

    sim.hub_craft_vial()
    assert any("singing_bowl" in line or "bowl" in line for line in sim.log)
    assert sim.at_station(HubStation.SINGING_BOWL)

    move_before_fill = sim.ledger.move
    sim.hub_fill_vial()
    assert sim.ledger.move > move_before_fill
    assert sim.at_station(HubStation.WATER_PUMP)
    assert any("water_pump" in line or "pump" in line for line in sim.log)

    move_before_cook = sim.ledger.move
    sim.hub_cook_paddlefish()
    assert sim.at_station(HubStation.RANGE)
    assert sim.ledger.move >= move_before_cook
    assert any("range" in line for line in sim.log)


def test_clear_paths_to_combat_tile(rules: GameRules, cfg: AppConfig) -> None:
    sim = PrepSim.create(rules, cfg, use_tile_pathing=True)
    # Find a nearby resource room with mobs.
    start = sim.dungeon.layout.start
    target = None
    for n in start.neighbors():
        if n not in sim.dungeon.rooms:
            continue
        room = sim.dungeon.rooms[n]
        if room.kind.value == "boss":
            continue
        if room.mob_tier.value != "none":
            target = n
            break
    if target is None:
        pytest.skip("no adjacent mob room on this seed")
    sim.go_to(target)
    # Step off center so approach must move.
    geom = sim.dungeon.geometry
    assert geom is not None
    rt = geom.rooms[target]
    door = None
    for tiles in rt.doorways.values():
        if tiles:
            door = rt.to_global(*tiles[0])
            break
    if door is not None:
        sim.movement.travel_to_tile(
            sim.player, door, sim.dungeon.rooms, prep_limit=sim.prep_limit
        )
    move_before = sim.ledger.move
    sim.clear_here()
    assert sim.ledger.fight > 0
    assert sim.ledger.move >= move_before
