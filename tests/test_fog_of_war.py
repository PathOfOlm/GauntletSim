"""Fog-of-war: agents cannot read undiscovered room contents or layout peeks."""

from __future__ import annotations

import pytest

from gauntletsim.config import AppConfig, SimConfig
from gauntletsim.fog import FogError, FogKnowledge, LayoutFogProxy
from gauntletsim.game_rules import GameRules
from gauntletsim.prep import PrepSim
from gauntletsim.room import RoomKind
from gauntletsim.scenarios import (
    LOADOUT_T3_DUAL_T2ARM,
    LoadoutScenario,
    loadout_met,
    run_loadout_scenario,
)


@pytest.fixture
def rules() -> GameRules:
    return GameRules.load()


@pytest.fixture
def sim(rules: GameRules) -> PrepSim:
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=1),
    )
    return PrepSim.create(rules, cfg, use_tile_pathing=True)


def test_observe_undiscovered_raises(sim: PrepSim) -> None:
    fog = FogKnowledge(sim)
    start = fog.start()
    assert fog.is_discovered(start)
    # Pick an undiscovered neighbor if any, else a far room.
    frontier = fog.frontier()
    assert frontier, "start should have a frontier"
    target = frontier[0]
    assert not fog.is_discovered(target)
    with pytest.raises(FogError, match="undiscovered"):
        fog.observe(target)


def test_layout_proxy_blocks_fish_and_demi(sim: PrepSim) -> None:
    inner = sim.dungeon.layout
    proxy = LayoutFogProxy(inner)
    sim.dungeon.layout = proxy  # type: ignore[assignment]
    assert proxy.start == inner.start
    assert proxy.boss == inner.boss
    assert proxy.width == inner.width
    with pytest.raises(FogError, match="fish_room"):
        _ = proxy.fish_room
    with pytest.raises(FogError, match="demi_rooms"):
        _ = proxy.demi_rooms


def test_loadout_scenario_enforces_layout_proxy(rules: GameRules) -> None:
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=1),
    )
    sim = PrepSim.create(rules, cfg, use_tile_pathing=True)
    LoadoutScenario(sim, enforce_fog=True)
    with pytest.raises(FogError):
        _ = sim.dungeon.layout.fish_room
    with pytest.raises(FogError):
        _ = sim.dungeon.layout.demi_rooms


def test_frontier_only_lists_unknown_doors(sim: PrepSim) -> None:
    fog = FogKnowledge(sim)
    for c in fog.frontier():
        assert not fog.is_discovered(c)
        assert sim.dungeon.room(c).kind != RoomKind.BOSS


def test_seed1_fog_loadout_runs(rules: GameRules) -> None:
    """Fog agent must complete without omniscient peeks (success preferred, not required)."""
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=1),
    )
    sim = run_loadout_scenario(rules, cfg, loadout=LOADOUT_T3_DUAL_T2ARM)
    assert any("fog=1" in line for line in sim.log)
    # Layout peek still blocked after run.
    with pytest.raises(FogError):
        _ = sim.dungeon.layout.fish_room
    # Report-only: met may be True or False under fog.
    _ = loadout_met(sim), sim.player.tick, sim.timed_out()


def test_planning_with_full_layout_api_forbidden(sim: PrepSim) -> None:
    """Explicit forbidden-API contract for agent planning helpers."""
    fog = FogKnowledge(sim)
    sim.dungeon.layout = LayoutFogProxy(sim.dungeon.layout)  # type: ignore[assignment]

    def omniscient_plan_fish():
        return sim.dungeon.layout.fish_room

    def omniscient_plan_demis():
        return list(sim.dungeon.layout.demi_rooms)

    with pytest.raises(FogError):
        omniscient_plan_fish()
    with pytest.raises(FogError):
        omniscient_plan_demis()
    # Legal: frontier + observe after discover.
    nxt = fog.frontier()[0]
    sim.go_to(nxt)
    known = fog.observe(nxt)
    assert known.coord == nxt
