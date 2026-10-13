"""Smoke test for CLI entrypoint."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from gauntletsim.main import main

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_main_returns_zero(capsys) -> None:
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "Phase 1 status" in out
    assert "rule_entries:" in out
    assert "assumption_entries:" in out
    assert "unresolved_unknowns:" in out


def test_module_invocation_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "gauntletsim.main"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Phase 1 status" in proc.stdout
