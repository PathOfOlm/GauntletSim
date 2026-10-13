"""CLI entry: Phase 1 status + Phase 2 dungeon demo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gauntletsim import __version__
from gauntletsim.config import AppConfig, SimConfig
from gauntletsim.game_rules import DEFAULT_ASSUMPTIONS_PATH, DEFAULT_RULES_PATH, GameRules
from gauntletsim.simulation import Phase2Sim


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gauntletsim",
        description="GauntletSim — Corrupted Gauntlet offline simulator",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=DEFAULT_RULES_PATH,
        help="Path to corrupted_gauntlet.json",
    )
    parser.add_argument(
        "--assumptions",
        type=Path,
        default=DEFAULT_ASSUMPTIONS_PATH,
        help="Path to assumptions defaults.json",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Master seed (default: config demo seed)",
    )
    parser.add_argument(
        "--phase2",
        action="store_true",
        help="Generate dungeon, print ASCII map (Phase 2)",
    )
    parser.add_argument(
        "--explore-fish",
        action="store_true",
        help="With --phase2, explore toward the guaranteed fish room",
    )
    return parser


def phase1_status_lines(rules: GameRules, config: AppConfig) -> list[str]:
    width, height = rules.grid_size
    return [
        f"GauntletSim v{__version__} — status",
        f"mode: {config.sim.mode}",
        f"rules_path: {rules.rules_path}",
        f"assumptions_path: {rules.assumptions_path}",
        f"rule_entries: {rules.rule_entry_count}",
        f"assumption_entries: {rules.assumption_count}",
        f"unresolved_unknowns: {rules.unresolved_unknown_count}",
        f"tick_seconds: {rules.tick_seconds}",
        f"prep_seconds: {rules.prep_seconds}",
        f"prep_ticks: {rules.prep_ticks}",
        f"grid: {width}x{height}",
        f"hunllef_hitpoints: {rules.hunllef_hitpoints}",
        (
            "account: "
            f"magic={config.account.magic} ranged={config.account.ranged} "
            f"attack={config.account.attack} strength={config.account.strength} "
            f"defence={config.account.defence} hitpoints={config.account.hitpoints} "
            f"prayer={config.account.prayer} agility={config.account.agility} "
            f"cooking={config.account.cooking}"
        ),
        f"master_seed: {config.sim.master_seed}",
    ]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rules = GameRules.load(rules_path=args.rules, assumptions_path=args.assumptions)
    config = AppConfig.phase1_demo()
    if args.seed is not None:
        config = AppConfig(
            account=config.account,
            sim=SimConfig(
                master_seed=args.seed,
                prep_ticks=config.sim.prep_ticks,
                log_level=config.sim.log_level,
                mode=config.sim.mode,
            ),
        )

    for line in phase1_status_lines(rules, config):
        print(line)

    if args.phase2:
        sim = Phase2Sim.create(rules, config)
        print()
        for line in sim.status_lines():
            print(line)
        if args.explore_fish:
            sim.explore_to(sim.dungeon.layout.fish_room)
            print(f"explored_to_fish_ticks: {sim.dungeon.player.tick}")
        print()
        print(sim.ascii_map())
    else:
        print("phase2: pass --phase2 to generate dungeon ASCII map")

    return 0


if __name__ == "__main__":
    sys.exit(main())
