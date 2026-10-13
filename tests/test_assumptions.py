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
        if "research_status" in item:
            assert item["research_status"] in {
                "still_unknown",
                "constrained",
                "resolved",
            }


def test_promoted_assumptions_no_longer_open() -> None:
    """Former unknowns that were verified must not remain as open assumptions."""
    rules = GameRules.load()
    open_ids = {a["id"] for a in rules.assumptions}
    for resolved in (
        "A-SHARD-QTY-CORRUPT-01",
        "A-WEAPON-SPEED-01",
        "A-HUB-CRAFT-TICKS-01",
        "A-INV-START-SLOTS-01",
        "A-FISH-ONETICK-01",
        "A-GEN-FISH-01",
        "A-EXPLORE-01",
        "A-EXPLORE-02",
        "A-STOMP-TRIGGER-01",
        "A-COMBAT-ACCURACY-01",
        "A-MOB-STATS-01",
        "A-MOB-STATS-SCORPION-WOLF",
        "A-DEMI-SPAWN-02",
        "A-RUN-ENERGY-01",
        "A-PRAYER-DRAIN-01",
    ):
        assert resolved not in open_ids
    assert rules.get("combat", "weapon_attack_speed_ticks")["bow_rapid"] == 4
    assert rules.get("inventory", "starting_occupied_inventory_slots") == 5
    assert rules.get("timing", "room_light_ticks") == 1
    assert rules.get("topology", "demi_boss_guaranteed_count") == 4
    assert rules.get("enemies", "demi_boss_type_uniform") is True
    assert "scorpion" in rules.get("enemies", "combat_stats")
    assert "wolf" in rules.get("enemies", "combat_stats")


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
        "A-PRAYER-DISABLE-01",
        "A-FLOOR-DMG-01",
        "A-TORNADO-DMG-01",
        "A-DEMI-SPAWN-01",
        "A-GEN-NODES-01",
        "A-MOB-SPAWN-01",
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
