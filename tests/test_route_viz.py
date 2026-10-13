"""Route recording and ASCII/SVG visualization."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from gauntletsim.config import AppConfig, SimConfig
from gauntletsim.game_rules import GameRules
from gauntletsim.prep import PrepSim
from gauntletsim.route import (
    render_room_route_ascii,
    render_room_route_svg,
    write_route_artifacts,
)
from gauntletsim.scenarios import LOADOUT_T3_DUAL_T2ARM, run_loadout_scenario

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_route_records_rooms_and_tiles_on_loadout() -> None:
    rules = GameRules.load()
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=1),
    )
    sim = run_loadout_scenario(rules, cfg, loadout=LOADOUT_T3_DUAL_T2ARM)
    assert len(sim.route.room_steps) >= 3
    assert len(sim.route.tiles) >= 10
    assert sim.dungeon.layout.start in sim.route.room_first_visit
    assert sim.dungeon.layout.fish_room in sim.route.room_first_visit
    panel = sim.route_panel()
    assert "room route" in panel
    assert "hub tile trail" in panel
    assert "singing_bowl" in panel or "B=bowl" in panel


def test_room_route_ascii_and_svg() -> None:
    rules = GameRules.load()
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=1),
    )
    sim = PrepSim.create(rules, cfg, use_tile_pathing=True)
    sim.go_to(sim.dungeon.layout.fish_room)
    ascii_map = render_room_route_ascii(sim.dungeon, sim.route)
    assert "01" in ascii_map
    assert "itinerary" in ascii_map
    svg = render_room_route_svg(sim.dungeon, sim.route)
    assert svg.strip().startswith("<svg")
    assert "polyline" in svg or "rect" in svg


def test_write_route_artifacts(tmp_path: Path) -> None:
    rules = GameRules.load()
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=1),
    )
    sim = run_loadout_scenario(rules, cfg, loadout=LOADOUT_T3_DUAL_T2ARM)
    written = write_route_artifacts(tmp_path, sim.dungeon, sim.route, stem="demo")
    names = {p.name for p in written}
    assert "demo.txt" in names
    assert "demo.svg" in names
    assert "demo-rooms.txt" in names
    text = (tmp_path / "demo.txt").read_text(encoding="utf-8")
    assert "room_path:" in text or "itinerary" in text


def test_cli_show_route_and_write(tmp_path: Path) -> None:
    out = tmp_path / "routes"
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
            "--show-route",
            "--write-route",
            str(out),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "room route" in proc.stdout
    assert "hub tile trail" in proc.stdout
    assert "route_files:" in proc.stdout
    assert list(out.glob("*.svg"))
    assert list(out.glob("*.txt"))
