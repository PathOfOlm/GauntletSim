"""Parallel loadout seed optimization."""

from __future__ import annotations

from gauntletsim.game_rules import GameRules
from gauntletsim.scenarios import (
    LOADOUT_T3_DUAL_T2ARM,
    optimize_loadout_seeds,
    run_loadout_scenario,
)
from gauntletsim.config import AppConfig, SimConfig
from gauntletsim.scenarios import loadout_met


def test_optimize_loadout_seeds_finds_best_in_small_range() -> None:
    rules = GameRules.load()
    best, scores = optimize_loadout_seeds(
        rules,
        loadout=LOADOUT_T3_DUAL_T2ARM,
        seeds=range(0, 8),
        workers=2,
    )
    assert len(scores) == 8
    ok = [s for s in scores if s.met and not s.timed_out and not s.error]
    assert ok, "expected at least one success in seeds 0..7"
    assert best is not None
    assert best.seed == min(ok, key=lambda s: (s.ticks, s.move, s.steps, s.seed)).seed
    # Re-run best to confirm deterministic completion.
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=best.seed),
    )
    sim = run_loadout_scenario(rules, cfg, loadout=LOADOUT_T3_DUAL_T2ARM)
    assert loadout_met(sim)
    assert sim.player.tick == best.ticks
