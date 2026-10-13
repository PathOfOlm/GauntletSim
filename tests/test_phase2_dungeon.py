"""Phase 2 dungeon: connectivity, spawns, seeds, movement."""

from __future__ import annotations

import pytest

from gauntletsim.config import AppConfig, SimConfig
from gauntletsim.dungeon import DungeonState
from gauntletsim.game_rules import GameRules
from gauntletsim.map_generator import (
    BOSS_COORD,
    CARDINAL_OUTER,
    generate_layout,
    validate_layout_rules,
)
from gauntletsim.pathfinding import bfs_distances, shortest_path
from gauntletsim.player import MovementError
from gauntletsim.room import Coord, MobTier, RoomKind, orthogonal_neighbors
from gauntletsim.simulation import Phase2Sim
from gauntletsim.visualization import render_ascii


@pytest.fixture
def rules() -> GameRules:
    return GameRules.load()


def test_layout_full_orthogonal_connectivity(rules: GameRules) -> None:
    layout = generate_layout(rules, master_seed=1)
    assert len(layout.rooms) == 49
    for coord in layout.rooms:
        for n in orthogonal_neighbors(coord):
            assert n in layout.rooms
    # Undiscovered graph is still fully connected structurally.
    dist = bfs_distances(
        layout.rooms,
        layout.start,
        require_discovered=False,
    )
    assert len(dist) == 49


def test_start_and_fish_adjacent_to_boss(rules: GameRules) -> None:
    layout = generate_layout(rules, master_seed=42)
    assert layout.boss == BOSS_COORD
    assert layout.start.manhattan(layout.boss) == 1
    assert layout.fish_room.manhattan(layout.boss) == 1
    assert layout.fish_room != layout.start
    assert layout.room(layout.fish_room).fishing_spots >= 3
    assert layout.room(layout.start).kind == RoomKind.START
    assert layout.room(layout.boss).kind == RoomKind.BOSS


def test_demi_bosses_on_cardinals_and_edges(rules: GameRules) -> None:
    layout = generate_layout(rules, master_seed=7)
    errors = validate_layout_rules(layout, rules)
    assert errors == []
    for card in CARDINAL_OUTER.values():
        assert layout.room(card).mob_tier == MobTier.DEMI_BOSS
        assert layout.room(card).demi_type is not None
    extra = int(rules.assumption_default("dungeon.demi_boss_extra_count"))
    assert len(layout.demi_rooms) == 4 + extra
    for coord in layout.demi_rooms:
        room = layout.room(coord)
        assert room.is_edge or room.is_corner


def test_seed_reproducibility(rules: GameRules) -> None:
    a = generate_layout(rules, master_seed=12345)
    b = generate_layout(rules, master_seed=12345)
    c = generate_layout(rules, master_seed=12346)
    assert a.start == b.start
    assert a.fish_room == b.fish_room
    assert a.demi_rooms == b.demi_rooms
    for coord in a.rooms:
        assert a.rooms[coord].nodes == b.rooms[coord].nodes
        assert a.rooms[coord].mob_tier == b.rooms[coord].mob_tier
        assert a.rooms[coord].demi_type == b.rooms[coord].demi_type
    assert a.start != c.start or a.fish_room != c.fish_room or a.demi_rooms != c.demi_rooms


def test_movement_light_costs_one_tick(rules: GameRules) -> None:
    state = DungeonState.generate(rules, master_seed=99)
    start = state.player.coord
    # Pick an undiscovered orthogonal neighbor that is not boss.
    targets = [
        n
        for n in orthogonal_neighbors(start)
        if n != state.layout.boss and not state.room(n).discovered
    ]
    assert targets
    target = targets[0]
    spent = state.player.move_or_light(
        state.rooms,
        target,
        light_ticks=state.light_ticks,
        move_ticks=state.move_ticks,
    )
    assert spent == 1
    assert state.player.tick == 1
    assert state.player.coord == target
    assert state.room(target).discovered


def test_cannot_light_into_boss(rules: GameRules) -> None:
    state = DungeonState.generate(rules, master_seed=99)
    # Move to stay adjacent to boss if needed — start already is.
    assert state.player.coord.manhattan(state.layout.boss) == 1
    with pytest.raises(MovementError):
        state.player.move_or_light(state.rooms, state.layout.boss)
    state.player.enter_boss(state.rooms, state.layout.boss)
    assert state.player.coord == state.layout.boss
    assert state.room(state.layout.boss).discovered


def test_pathfinding_requires_discovered(rules: GameRules) -> None:
    state = DungeonState.generate(rules, master_seed=5)
    far = Coord(0, 0)
    assert shortest_path(state.rooms, state.player.coord, far) is None
    # Explore toward fish room
    sim = Phase2Sim.create(
        rules,
        AppConfig(
            account=AppConfig.phase1_demo().account,
            sim=SimConfig(master_seed=5),
        ),
    )
    sim.explore_to(sim.dungeon.layout.fish_room)
    assert sim.dungeon.player.coord == sim.dungeon.layout.fish_room
    assert sim.dungeon.room(sim.dungeon.layout.fish_room).discovered


def test_ascii_contains_player_and_legend(rules: GameRules) -> None:
    state = DungeonState.generate(rules, master_seed=2)
    text = render_ascii(state)
    assert "@" in text
    assert "S" in text or "@" in text  # player may be on start
    assert "?" in text
    assert "legend:" in text


def test_phase2_sim_status(rules: GameRules) -> None:
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=11),
    )
    sim = Phase2Sim.create(rules, cfg)
    assert sim.dungeon.rules_errors == []
    lines = "\n".join(sim.status_lines())
    assert "Phase 2" in lines
    assert "demi_rooms:" in lines
