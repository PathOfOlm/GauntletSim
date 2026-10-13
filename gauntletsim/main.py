"""CLI entry: load Phase 1 rules/config and print status."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gauntletsim import __version__
from gauntletsim.config import AppConfig
from gauntletsim.game_rules import DEFAULT_ASSUMPTIONS_PATH, DEFAULT_RULES_PATH, GameRules


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gauntletsim",
        description="GauntletSim Phase 1 — Corrupted Gauntlet rules/config loader",
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
    return parser


def phase1_status_lines(rules: GameRules, config: AppConfig) -> list[str]:
    width, height = rules.grid_size
    return [
        f"GauntletSim v{__version__} — Phase 1 status",
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
        "gameplay_modules: not implemented in Phase 1 (architecture placeholders only)",
    ]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rules = GameRules.load(rules_path=args.rules, assumptions_path=args.assumptions)
    config = AppConfig.phase1_demo()
    for line in phase1_status_lines(rules, config):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
