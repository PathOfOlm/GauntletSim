"""Phase 3.5: tile pathing, walls, movement ticks, seed reproducibility."""

from __future__ import annotations

import pytest

from gauntletsim.config import AppConfig, SimConfig
from gauntletsim.dungeon import DungeonState
from gauntletsim.game_rules import GameRules
from gauntletsim.geometry import force_block_tile
from gauntletsim.movement import run_energy_drain_per_tick
from gauntletsim.prep import PrepSim
from gauntletsim.tile_pathfinding import astar_path, path_length


@pytest.fixture
def rules() -> GameRules:
    return GameRules.load()


@pytest.fixture
def cfg() -> AppConfig:
    return AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=42),
    )


def test_rules_walk_run_tiles(rules: GameRules) -> None:
    assert rules.get("timing", "walk_tiles_per_tick") == 1
    assert rules.get("timing", "run_tiles_per_tick") == 2
    assert rules.get("timing", "run_energy_max_units") == 10000


def test_room_geometry_size(rules: GameRules) -> None:
    assert rules.assumption_default("topology.room_size_tiles") == 16
    dungeon = DungeonState.generate(rules, 1)
    assert dungeon.geometry is not None
    assert dungeon.geometry.room_size == 16
    start = dungeon.layout.start
    rt = dungeon.geometry.rooms[start]
    # Center is tool-storage (blocked); spawn / center_tile must still be walkable.
    assert not rt.local_walkable(*rt.center_local())
    spawn = rt.center_tile()
    lx, ly = dungeon.geometry.local_of(spawn)
    assert rt.local_walkable(lx, ly)


def test_blocked_tile_pathing_avoids_walls(rules: GameRules) -> None:
    dungeon = DungeonState.generate(rules, 7)
    geom = dungeon.geometry
    assert geom is not None
    start_room = dungeon.layout.start
    rt = geom.rooms[start_room]
    a = rt.center_tile()
    # Pick a walkable goal in the same room.
    goal = None
    for ly in range(1, rt.size - 1):
        for lx in range(1, rt.size - 1):
            t = rt.to_global(lx, ly)
            if t != a and rt.local_walkable(lx, ly):
                goal = t
                break
        if goal:
            break
    assert goal is not None
    path = astar_path(geom, a, goal)
    assert path is not None
    assert path[0] == a and path[-1] == goal
    for t in path:
        assert geom.is_walkable(t)


def test_walls_force_detour(rules: GameRules) -> None:
    dungeon = DungeonState.generate(rules, 3)
    geom = dungeon.geometry
    assert geom is not None
    start = dungeon.layout.start
    rt = geom.rooms[start]
    # Clear interior then build a wall line that forces a detour.
    cx, cy = rt.center_local()
    for ly in range(1, rt.size - 1):
        for lx in range(1, rt.size - 1):
            rt.blocked.discard((lx, ly))
    # Vertical wall with one gap at bottom.
    wall_x = cx + 2
    for ly in range(1, rt.size - 2):
        rt.blocked.add((wall_x, ly))
    left = rt.to_global(cx - 1, cy)
    right = rt.to_global(cx + 4, cy)
    assert rt.local_walkable(cx - 1, cy)
    assert rt.local_walkable(cx + 4, cy)
    path = astar_path(geom, left, right)
    assert path is not None
    # Straight Chebyshev distance would be ~5; detour must be longer.
    assert path_length(path) > abs(right.x - left.x)
    for t in path:
        lx, ly = geom.local_of(t)
        assert (lx, ly) not in rt.blocked


def test_no_walking_through_walls(rules: GameRules) -> None:
    dungeon = DungeonState.generate(rules, 9)
    geom = dungeon.geometry
    assert geom is not None
    start = dungeon.layout.start
    rt = geom.rooms[start]
    wall = rt.to_global(0, 0)  # corner perimeter wall
    force_block_tile(geom, wall)
    center = rt.center_tile()
    assert astar_path(geom, center, wall) is None


def test_gather_and_craft_still_spend_ticks(rules: GameRules, cfg: AppConfig) -> None:
    from gauntletsim.crafting import WeaponStyle
    from gauntletsim.inventory import ItemId

    sim = PrepSim.create(rules, cfg, use_tile_pathing=True)
    fish = sim.dungeon.layout.fish_room
    sim.go_to(fish)
    before = sim.player.tick
    gather_before = sim.ledger.gather
    sim.gather_here()
    assert sim.ledger.gather > gather_before
    assert sim.player.tick > before

    sim.return_to_start(prefer_teleport=True)
    if not sim.player.inventory.has(ItemId.WEAPON_FRAME):
        sim.player.inventory.add(ItemId.WEAPON_FRAME)
    if sim.player.inventory.count(ItemId.SHARDS) < 40:
        sim.player.inventory.add(ItemId.SHARDS, 200)
    craft_before = sim.ledger.craft
    sim.hub_craft_basic_weapon(WeaponStyle.BOW)
    assert sim.ledger.craft == craft_before + 1


def test_prep_seed_reproducibility_tile(rules: GameRules) -> None:
    a = PrepSim.create(
        rules, AppConfig(account=AppConfig.phase1_demo().account, sim=SimConfig(42))
    )
    b = PrepSim.create(
        rules, AppConfig(account=AppConfig.phase1_demo().account, sim=SimConfig(42))
    )
    a.demo_prep_slice()
    b.demo_prep_slice()
    assert a.player.tick == b.player.tick
    assert a.ledger.as_dict() == b.ledger.as_dict()
    assert a.player.inventory.summary() == b.player.inventory.summary()
    assert a.player.tile == b.player.tile


def test_run_energy_drain(rules: GameRules) -> None:
    drain = run_energy_drain_per_tick(70, 0.0)
    assert drain > 0
    stamina = run_energy_drain_per_tick(70, 0.0, stamina_multiplier=0.3)
    assert stamina < drain


def test_demo_move_ticks_dominate_vs_coarse(rules: GameRules, cfg: AppConfig) -> None:
    fine = PrepSim.create(rules, cfg, use_tile_pathing=True)
    fine.demo_prep_slice()
    coarse = PrepSim.create(rules, cfg, use_tile_pathing=False)
    coarse.demo_prep_slice()
    # Tile pathing should spend substantially more ticks (travel realism).
    assert fine.player.tick > coarse.player.tick
    assert fine.ledger.move + fine.ledger.light > 0
    # Movement+light should be a large share of the fine demo.
    moveish = fine.ledger.move + fine.ledger.light + fine.ledger.teleport
    assert moveish >= fine.ledger.craft
