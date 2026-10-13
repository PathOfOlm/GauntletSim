"""CLI entry: Phase 1 status, Phase 2 map, Phase 3 prep demo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gauntletsim import __version__
from gauntletsim.config import AppConfig, SimConfig
from gauntletsim.game_rules import DEFAULT_ASSUMPTIONS_PATH, DEFAULT_RULES_PATH, GameRules
from gauntletsim.prep import PrepSim
from gauntletsim.route import write_route_artifacts
from gauntletsim.scenarios import (
    LOADOUT_T3_DUAL_T2ARM,
    find_loadout_seed,
    loadout_gaps,
    loadout_met,
    run_loadout_scenario,
)
from gauntletsim.simulation import Phase2Sim


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gauntletsim",
        description="GauntletSim — Corrupted Gauntlet offline simulator",
    )
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES_PATH)
    parser.add_argument("--assumptions", type=Path, default=DEFAULT_ASSUMPTIONS_PATH)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--phase2",
        action="store_true",
        help="Generate dungeon, print ASCII map",
    )
    parser.add_argument(
        "--explore-fish",
        action="store_true",
        help="With --phase2, explore toward the guaranteed fish room",
    )
    parser.add_argument(
        "--phase3",
        action="store_true",
        help="Run prep demo with tile pathing (Phase 3.5)",
    )
    parser.add_argument(
        "--phase3.5",
        dest="phase3_5",
        action="store_true",
        help="Phase 3.5 prep demo (tile pathing + tick buckets)",
    )
    parser.add_argument(
        "--loadout",
        type=str,
        default=None,
        metavar="NAME",
        help=(
            "Named prep loadout scenario (requires --phase3 / --phase3.5). "
            f"Known: {LOADOUT_T3_DUAL_T2ARM}"
        ),
    )
    parser.add_argument(
        "--find-loadout-seed",
        action="store_true",
        help="With --loadout, search seeds 0..79 for a completing run (ignores --seed)",
    )
    parser.add_argument(
        "--seed-search-limit",
        type=int,
        default=80,
        help="Upper exclusive bound for --find-loadout-seed (default 80)",
    )
    parser.add_argument(
        "--show-route",
        dest="show_route",
        action="store_true",
        default=None,
        help="Print room-route + hub tile-trail panel after Phase 3.5 runs",
    )
    parser.add_argument(
        "--no-show-route",
        dest="show_route",
        action="store_false",
        help="Disable route visualization",
    )
    parser.add_argument(
        "--write-route",
        nargs="?",
        const="results",
        default=None,
        metavar="DIR",
        help="Write route ASCII+SVG under DIR (default: results/)",
    )
    return parser


def _want_show_route(args: argparse.Namespace, *, loadout: bool) -> bool:
    if args.show_route is not None:
        return bool(args.show_route)
    # Default on for loadout; compact on for plain phase3.5 as well.
    return True


def _emit_route(sim: PrepSim, args: argparse.Namespace, *, stem: str) -> None:
    print()
    print(sim.route_panel())
    if args.write_route is not None:
        out_dir = Path(args.write_route)
        written = write_route_artifacts(
            out_dir, sim.dungeon, sim.route, stem=stem
        )
        print()
        print("route_files:")
        for path in written:
            print(f"  {path}")


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
            sim=SimConfig(master_seed=args.seed),
        )

    for line in phase1_status_lines(rules, config):
        print(line)

    if args.loadout and not (args.phase3 or args.phase3_5):
        print("error: --loadout requires --phase3 or --phase3.5", file=sys.stderr)
        return 2

    if (args.phase3 or args.phase3_5) and args.loadout:
        loadout = args.loadout
        if args.find_loadout_seed or args.seed is None:
            found = find_loadout_seed(
                rules,
                loadout=loadout,
                seeds=range(0, max(1, args.seed_search_limit)),
                account=config.account,
            )
            if found is None:
                print()
                print(
                    f"loadout search failed: no seed in "
                    f"[0, {args.seed_search_limit}) completed {loadout!r}"
                )
                # Show last attempt gaps via seed 0 for debugging.
                sim = run_loadout_scenario(rules, config, loadout=loadout)
                print()
                for line in sim.status_lines():
                    print(line)
                print(f"loadout_met: {loadout_met(sim)}")
                print(f"loadout_gaps: {loadout_gaps(sim)}")
                print()
                print("--- prep log ---")
                for line in sim.log:
                    print(line)
                return 1
            seed, sim = found
            print()
            print(f"loadout_seed: {seed}")
        else:
            sim = run_loadout_scenario(rules, config, loadout=loadout)
        print()
        for line in sim.status_lines():
            print(line)
        print(f"loadout: {loadout}")
        print(f"loadout_met: {loadout_met(sim)}")
        print(f"loadout_gaps: {loadout_gaps(sim)}")
        print(f"timed_out: {sim.timed_out()}")
        print()
        print("--- prep log ---")
        for line in sim.log:
            print(line)
        print()
        print(sim.ascii_map())
        if _want_show_route(args, loadout=True):
            seed = sim.dungeon.layout.master_seed
            _emit_route(
                sim,
                args,
                stem=f"loadout-{loadout}-seed{seed}",
            )
        return 0 if loadout_met(sim) else 1

    if args.phase3 or args.phase3_5:
        sim = PrepSim.create(rules, config, use_tile_pathing=True)
        sim.demo_prep_slice()
        print()
        for line in sim.status_lines():
            print(line)
        print()
        print("--- prep log ---")
        for line in sim.log:
            print(line)
        print()
        print(sim.ascii_map())
        if _want_show_route(args, loadout=False):
            seed = sim.dungeon.layout.master_seed
            _emit_route(sim, args, stem=f"phase35-demo-seed{seed}")
    elif args.phase2:
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
        print(
            "hint: --phase2 for map, --phase3 / --phase3.5 for prep demo, "
            f"--phase3.5 --loadout {LOADOUT_T3_DUAL_T2ARM} for named loadout"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
