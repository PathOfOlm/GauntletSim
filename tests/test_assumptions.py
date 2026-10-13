"""Assumption defaults completeness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gauntletsim.game_rules import (
    DEFAULT_ASSUMPTIONS_PATH,
    GameRules,
    RulesLoadError,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
UNCERTAINTY_DOC = REPO_ROOT / "docs" / "uncertainty-register.md"


def test_assumptions_have_id_range_and_label() -> None:
    rules = GameRules.load()
    assert rules.assumption_count > 0
    for item in rules.assumptions:
        assert item["id"]
        assert item["label"]
        assert item["parameter"]
        assert item["range"] not in (None, "")
        assert "default" in item
        assert item["unit"]


def test_assumption_ids_unique_and_parameters_unique() -> None:
    rules = GameRules.load()
    ids = [a["id"] for a in rules.assumptions]
    params = [a["parameter"] for a in rules.assumptions]
    assert len(ids) == len(set(ids))
    assert len(params) == len(set(params))


def test_uncertainty_register_lists_core_assumption_ids() -> None:
    text = UNCERTAINTY_DOC.read_text(encoding="utf-8")
    rules = GameRules.load()
    # Floor damage has split ids in JSON; register documents the family.
    required_prefixes = [
        "A-EXPLORE-01",
        "A-PRAYER-DISABLE-01",
        "A-FLOOR-DMG-01",
        "A-TORNADO-DMG-01",
        "A-DEMI-SPAWN-01",
    ]
    for assumption_id in required_prefixes:
        assert assumption_id in text
    for item in rules.assumptions:
        base = item["id"].rstrip("b")
        # Allow split ids like A-FLOOR-DMG-01b
        family = item["id"][:-1] if item["id"].endswith("b") else item["id"]
        assert family in text or item["id"] in text or base in text


def test_assumptions_reject_unknown_key(tmp_path: Path) -> None:
    raw = json.loads(DEFAULT_ASSUMPTIONS_PATH.read_text(encoding="utf-8"))
    raw["assumptions"][0]["bogus"] = 1
    path = tmp_path / "bad_assumptions.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(RulesLoadError, match="unknown key"):
        GameRules.load(assumptions_path=path)


def test_assumptions_reject_missing_range(tmp_path: Path) -> None:
    raw = json.loads(DEFAULT_ASSUMPTIONS_PATH.read_text(encoding="utf-8"))
    del raw["assumptions"][0]["range"]
    path = tmp_path / "no_range.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(RulesLoadError, match="missing field"):
        GameRules.load(assumptions_path=path)
