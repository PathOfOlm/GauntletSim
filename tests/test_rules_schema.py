"""Rules JSON schema and loader validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gauntletsim.game_rules import (
    DEFAULT_RULES_PATH,
    GameRules,
    RulesLoadError,
    validate_rules_document,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_default_rules_file_loads() -> None:
    rules = GameRules.load()
    assert rules.rule_entry_count > 0
    assert rules.prep_ticks == 750
    assert rules.tick_seconds == 0.6
    assert rules.grid_size == (7, 7)
    assert rules.hunllef_hitpoints == 1000
    assert rules.get("topology", "ordinary_inner_ring_mitigation_applies") is False


def test_rules_schema_required_sections_and_fields() -> None:
    raw = json.loads(DEFAULT_RULES_PATH.read_text(encoding="utf-8"))
    validated = validate_rules_document(raw)
    for section in (
        "timing",
        "topology",
        "resources",
        "crafting",
        "enemies",
        "boss",
        "inventory",
    ):
        assert section in validated
        assert validated[section]


def test_rules_reject_unknown_top_level_key(tmp_path: Path) -> None:
    raw = json.loads(DEFAULT_RULES_PATH.read_text(encoding="utf-8"))
    raw["unexpected_section"] = {}
    path = tmp_path / "bad_rules.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(RulesLoadError, match="unknown key"):
        GameRules.load(rules_path=path)


def test_rules_reject_unknown_entry_key(tmp_path: Path) -> None:
    raw = json.loads(DEFAULT_RULES_PATH.read_text(encoding="utf-8"))
    raw["timing"]["tick_seconds"]["extra"] = True
    path = tmp_path / "bad_entry.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(RulesLoadError, match="unknown key"):
        GameRules.load(rules_path=path)


def test_rules_reject_inferred_confidence_without_assumption(tmp_path: Path) -> None:
    """Critical combat numbers must not be stored as inferred facts in rules JSON."""
    raw = json.loads(DEFAULT_RULES_PATH.read_text(encoding="utf-8"))
    raw["boss"]["made_up_hit_chance"] = {
        "value": 0.42,
        "confidence": "inferred",
        "source_ids": ["wiki-corrupted-hunllef"],
    }
    path = tmp_path / "inferred.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(RulesLoadError, match="inferred"):
        GameRules.load(rules_path=path)


def test_rules_reject_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(RulesLoadError, match="invalid JSON"):
        GameRules.load(rules_path=path)


def test_loader_deterministic() -> None:
    a = GameRules.load()
    b = GameRules.load()
    assert a.rule_entry_count == b.rule_entry_count
    assert a.prep_ticks == b.prep_ticks
    assert a.get("boss", "attacks_per_style_switch") == b.get(
        "boss", "attacks_per_style_switch"
    )


def test_rules_topology_grid() -> None:
    rules = GameRules.load()
    assert rules.get("topology", "grid_width") == 7
    assert rules.get("topology", "grid_height") == 7


def test_rules_prep_seconds() -> None:
    rules = GameRules.load()
    assert rules.prep_seconds == 450


def test_rules_weapon_costs() -> None:
    rules = GameRules.load()
    assert rules.get("crafting", "weapon_basic_shards") == 0
    assert rules.get("crafting", "weapon_attuned_shards") == 50
