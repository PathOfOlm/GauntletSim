"""Route recording and PNG/ASCII visualization."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from gauntletsim.config import AppConfig, SimConfig
from gauntletsim.game_rules import GameRules
from gauntletsim.prep import PrepSim
from gauntletsim.route import (
    render_room_route_ascii,
    render_room_route_svg,
    write_route_artifacts,
)
from gauntletsim.route_plot import viz_available, write_route_png
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


def test_write_route_artifacts_rooms_txt(tmp_path: Path) -> None:
    rules = GameRules.load()
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=1),
    )
    sim = run_loadout_scenario(rules, cfg, loadout=LOADOUT_T3_DUAL_T2ARM)
    written = write_route_artifacts(
        tmp_path, sim.dungeon, sim.route, stem="demo", ascii_panel=True
    )
    names = {p.name for p in written}
    assert "demo-rooms.txt" in names
    assert "demo.txt" in names
    assert "demo.svg" in names


@pytest.mark.skipif(not viz_available(), reason="matplotlib viz extra not installed")
def test_write_route_png(tmp_path: Path) -> None:
    rules = GameRules.load()
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=1),
    )
    sim = run_loadout_scenario(rules, cfg, loadout=LOADOUT_T3_DUAL_T2ARM)
    png = tmp_path / "route.png"
    write_route_png(png, sim.dungeon, sim.route, loadout=LOADOUT_T3_DUAL_T2ARM)
    assert png.is_file()
    assert png.stat().st_size > 10_000
    written = write_route_artifacts(
        tmp_path, sim.dungeon, sim.route, stem="demo", loadout=LOADOUT_T3_DUAL_T2ARM
    )
    names = {p.name for p in written}
    assert "demo-route.png" in names
    assert "demo-route.html" in names


def test_cli_show_route_writes_results(tmp_path: Path) -> None:
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
    assert "route_files:" in proc.stdout
    assert (out / f"loadout-{LOADOUT_T3_DUAL_T2ARM}-seed1-rooms.txt").is_file()
    if viz_available():
        assert "ROUTE IMAGE:" in proc.stdout
        assert list(out.glob("*-route.png"))
        assert list(out.glob("*-route.html"))
