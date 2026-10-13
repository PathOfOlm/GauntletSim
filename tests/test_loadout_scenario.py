"""Named loadout scenario: T3 dual + T2 armour + pots + food."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from gauntletsim.config import AppConfig, SimConfig
from gauntletsim.crafting import ArmourSlot, CraftingBench, WeaponStyle
from gauntletsim.game_rules import GameRules
from gauntletsim.inventory import Inventory, ItemId
from gauntletsim.prep import PrepSim
from gauntletsim.scenarios import (
    GOAL_T3_DUAL,
    LOADOUT_T3_DUAL_T2ARM,
    find_loadout_seed,
    loadout_gaps,
    loadout_met,
    run_loadout_scenario,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def rules() -> GameRules:
    return GameRules.load()


def _equip_goal_inventory(rules: GameRules) -> Inventory:
    """Hand-build a legal final loadout inventory for goal checks."""
    inv = Inventory()
    inv.add(ItemId.WEAPON_FRAME, 2)
    inv.add(ItemId.SHARDS, 520)
    inv.add(ItemId.ORE, 7)
    inv.add(ItemId.BARK, 7)
    inv.add(ItemId.LINUM, 7)
    inv.add(ItemId.BOWSTRING)
    inv.add(ItemId.ORB)
    inv.add(ItemId.GRYM_LEAF, 3)
    inv.add(ItemId.PESTLE)
    bench = CraftingBench(rules)
    for style, part in (
        (WeaponStyle.BOW, ItemId.BOWSTRING),
        (WeaponStyle.STAFF, ItemId.ORB),
    ):
        bench.craft_basic_weapon(inv, style)
        bench.upgrade_weapon_attuned(inv, style)
        # part already in inv for perfected
        bench.upgrade_weapon_perfected(inv, style)
    for slot in (ArmourSlot.HELM, ArmourSlot.BODY, ArmourSlot.LEGS):
        bench.craft_armour_basic(inv, slot)
        bench.upgrade_armour_attuned(inv, slot)
    for _ in range(3):
        bench.craft_vial(inv)
        bench.fill_vial(inv)
        bench.make_grym_unf(inv)
        bench.make_egniol(inv)
    inv.add(ItemId.PADDLEFISH, 21)
    return inv


def test_loadout_met_true_when_goal_items_present(rules: GameRules) -> None:
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=1),
    )
    sim = PrepSim.create(rules, cfg, use_tile_pathing=True)
    sim.player.inventory = _equip_goal_inventory(rules)
    sim.player.equipment.sync_from_inventory(sim.player.inventory)
    assert loadout_met(sim, GOAL_T3_DUAL)
    assert loadout_gaps(sim, GOAL_T3_DUAL) == []


def test_loadout_gaps_reports_missing_pieces(rules: GameRules) -> None:
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=1),
    )
    sim = PrepSim.create(rules, cfg, use_tile_pathing=True)
    gaps = loadout_gaps(sim, GOAL_T3_DUAL)
    assert any(g.startswith("bow_tier=") for g in gaps)
    assert any(g.startswith("egniol=") for g in gaps)
    assert any(g.startswith("fish=") for g in gaps)
    assert not loadout_met(sim)


def test_seed_1_completes_t3_dual_loadout(rules: GameRules) -> None:
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=1),
    )
    sim = run_loadout_scenario(rules, cfg, loadout=LOADOUT_T3_DUAL_T2ARM)
    assert not sim.timed_out()
    assert sim.player.tick <= rules.prep_ticks
    assert loadout_met(sim, GOAL_T3_DUAL), loadout_gaps(sim)
    inv = sim.player.inventory
    eq = sim.player.equipment
    eq.sync_from_inventory(inv)
    assert eq.has_bow == 3 and eq.has_staff == 3
    assert eq.helm_tier == 2 and eq.body_tier == 2 and eq.legs_tier == 2
    assert inv.count(ItemId.EGNIOL_3) >= 3
    assert inv.count(ItemId.PADDLEFISH) >= 21


def test_find_loadout_seed_returns_success(rules: GameRules) -> None:
    found = find_loadout_seed(rules, seeds=range(0, 10))
    assert found is not None
    seed, sim = found
    assert seed == 1
    assert loadout_met(sim)


def test_default_demo_still_available(rules: GameRules) -> None:
    """Seed-42 demo slice must remain callable (not replaced by loadout)."""
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=42),
    )
    sim = PrepSim.create(rules, cfg, use_tile_pathing=True)
    sim.demo_prep_slice()
    assert sim.player.tick > 0
    assert any("tick_buckets" in line for line in sim.log)


def test_loadout_cli_seed_1_exits_zero() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "gauntletsim.main",
            "--phase3.5",
            "--loadout",
            LOADOUT_T3_DUAL_T2ARM,
            "--seed",
            "1",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "loadout_met: True" in proc.stdout
    assert "bow_perfected" in proc.stdout or "bow=3" in proc.stdout


def test_unknown_loadout_raises(rules: GameRules) -> None:
    cfg = AppConfig.phase1_demo()
    with pytest.raises(ValueError, match="unknown loadout"):
        run_loadout_scenario(rules, cfg, loadout="not-a-real-loadout")
