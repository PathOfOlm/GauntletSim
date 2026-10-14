"""Video-gap prep features: multi-trip, C-path, fog, vials@fish, drops, crush."""

from __future__ import annotations

import pytest

from gauntletsim.config import AppConfig, SimConfig
from gauntletsim.crafting import CraftingBench
from gauntletsim.demibosses import PrepEncounters
from gauntletsim.fog import FogError
from gauntletsim.game_rules import GameRules
from gauntletsim.inventory import Inventory, ItemId
from gauntletsim.prep import PrepSim
from gauntletsim.room import Coord, MobTier, Room, RoomKind
from gauntletsim.scenarios import (
    LOADOUT_T3_DUAL_T2ARM,
    LoadoutScenario,
    loadout_met,
    run_loadout_scenario,
)


@pytest.fixture
def rules() -> GameRules:
    return GameRules.load()


def test_fill_vial_at_fishing_spot_rule(rules: GameRules) -> None:
    assert rules.get("resources", "fill_vial_at_fishing_spot") is True


def test_monsters_drop_fish_grym_tele_rule(rules: GameRules) -> None:
    assert rules.get("resources", "monsters_drop_fish_grym_teleport") is True


def test_crush_t3_component_shards(rules: GameRules) -> None:
    bench = CraftingBench(rules)
    inv = Inventory()
    inv.add(ItemId.PESTLE)
    inv.add(ItemId.SPIKE)
    ticks = bench.crush_t3_component(inv, ItemId.SPIKE)
    assert ticks == 1
    assert not inv.has(ItemId.SPIKE)
    assert inv.count(ItemId.SHARDS) == int(
        rules.get("crafting", "crush_t3_component_shards")
    )


def test_secondary_drops_can_roll(rules: GameRules) -> None:
    enc = PrepEncounters.create(rules, master_seed=7)
    inv = Inventory()
    saw_secondary = False
    for i in range(120):
        room = Room(
            coord=Coord(i % 7, (i // 7) % 7),
            kind=RoomKind.RESOURCE,
            mob_tier=MobTier.WEAK,
        )
        enc.state.cleared_rooms.clear()
        _ticks, drops = enc.clear_room(room, inv)
        if any(k in drops for k in ("raw_paddlefish", "grym_leaf", "teleport_crystal")):
            saw_secondary = True
            break
    assert saw_secondary


def test_multi_trip_and_c_path_logged(rules: GameRules) -> None:
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=28),
    )
    sim = run_loadout_scenario(rules, cfg, loadout=LOADOUT_T3_DUAL_T2ARM)
    assert loadout_met(sim)
    joined = "\n".join(sim.log)
    assert "c_path=" in joined
    assert "multi_trip=1" in joined
    assert "mid-hub" in joined
    assert "protect_magic" in joined
    assert "fog=1" in joined


def test_fog_still_blocks_layout_peeks(rules: GameRules) -> None:
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=28),
    )
    sim = PrepSim.create(rules, cfg, use_tile_pathing=True)
    LoadoutScenario(sim).run()
    with pytest.raises(FogError):
        _ = sim.dungeon.layout.fish_room
    with pytest.raises(FogError):
        _ = sim.dungeon.layout.demi_rooms


def test_fill_vial_at_fish_api(rules: GameRules) -> None:
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=1),
    )
    sim = PrepSim.create(rules, cfg, use_tile_pathing=True)
    fish = sim.dungeon.layout.fish_room
    sim.player.inventory.add(ItemId.VIAL)
    sim.go_to(fish)
    ticks = sim.fill_vial_at_fish()
    assert ticks >= 1
    assert sim.player.inventory.has(ItemId.WATER_VIAL)
