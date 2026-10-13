"""Hub station placement and bowl→pump movement ticks."""

from __future__ import annotations

import pytest

from gauntletsim.config import AppConfig, SimConfig
from gauntletsim.dungeon import DungeonState
from gauntletsim.game_rules import GameRules
from gauntletsim.hub import HubError, HubStation, is_adjacent_to_station
from gauntletsim.inventory import ItemId
from gauntletsim.prep import PrepSim


@pytest.fixture
def rules() -> GameRules:
    return GameRules.load()


@pytest.fixture
def cfg() -> AppConfig:
    return AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=42),
    )


def test_hub_stations_placed_and_blocked(rules: GameRules) -> None:
    dungeon = DungeonState.generate(rules, 42)
    assert dungeon.hub is not None
    assert dungeon.geometry is not None
    hub = dungeon.hub
    rt = dungeon.geometry.rooms[hub.start]
    for station in (
        HubStation.SINGING_BOWL,
        HubStation.WATER_PUMP,
        HubStation.RANGE,
        HubStation.TOOL_STORAGE,
    ):
        lx, ly = hub.object_locals(station)[0]
        assert (lx, ly) in rt.blocked
    # Spawn is walkable and adjacent to tool storage.
    assert dungeon.player.tile is not None
    assert dungeon.geometry.is_walkable(dungeon.player.tile)
    assert is_adjacent_to_station(
        dungeon.geometry, hub, dungeon.player.tile, HubStation.TOOL_STORAGE
    )


def test_fill_requires_pump_adjacency(rules: GameRules, cfg: AppConfig) -> None:
    sim = PrepSim.create(rules, cfg, use_tile_pathing=True)
    sim.player.inventory.add(ItemId.SHARDS, 50)
    sim.hub_craft_vial()
    assert sim.at_station(HubStation.SINGING_BOWL)
    assert not sim.at_station(HubStation.WATER_PUMP)
    # Cannot fill while still at the bowl.
    with pytest.raises(HubError, match="water_pump"):
        sim._require_station(HubStation.WATER_PUMP)
    # hub_fill_vial paths to pump then fills.
    move_before = sim.ledger.move
    sim.hub_fill_vial()
    assert sim.at_station(HubStation.WATER_PUMP)
    assert sim.player.inventory.has(ItemId.WATER_VIAL)
    assert sim.ledger.move > move_before


def test_bowl_to_pump_costs_move_ticks(rules: GameRules, cfg: AppConfig) -> None:
    sim = PrepSim.create(rules, cfg, use_tile_pathing=True)
    sim.player.inventory.add(ItemId.SHARDS, 80)
    sim.player.inventory.add(ItemId.GRYM_LEAF, 1)
    sim.approach_station(HubStation.SINGING_BOWL)
    move_at_bowl = sim.ledger.move
    sim.hub_craft_vial()
    assert sim.ledger.craft >= 1
    # Crossing start room to pump must add movement ticks.
    sim.hub_fill_vial()
    assert sim.ledger.move > move_at_bowl
    # Bowl and pump are in different quadrants — Chebyshev distance > 2.
    hub = sim.dungeon.hub
    assert hub is not None
    bowl = hub.primary_tile(HubStation.SINGING_BOWL)
    pump = hub.primary_tile(HubStation.WATER_PUMP)
    dist = max(abs(bowl.x - pump.x), abs(bowl.y - pump.y))
    assert dist >= 6


def test_cook_requires_range(rules: GameRules, cfg: AppConfig) -> None:
    sim = PrepSim.create(rules, cfg, use_tile_pathing=True)
    sim.player.inventory.add(ItemId.RAW_PADDLEFISH, 1)
    sim.approach_station(HubStation.SINGING_BOWL)
    assert not sim.at_station(HubStation.RANGE)
    move_before = sim.ledger.move
    sim.hub_cook_paddlefish()
    assert sim.at_station(HubStation.RANGE)
    assert sim.player.inventory.has(ItemId.PADDLEFISH)
    assert sim.ledger.move >= move_before


def test_demo_logs_hub_moves(rules: GameRules, cfg: AppConfig) -> None:
    sim = PrepSim.create(rules, cfg, use_tile_pathing=True)
    sim.demo_prep_slice()
    joined = "\n".join(sim.log)
    assert "bowl" in joined or "pump" in joined or "range" in joined
    # Movement between hub stations should appear when egniol path runs.
    if "craft vial" in joined or "craft vial @ bowl" in joined:
        assert sim.ledger.move > 0
