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
        "combat",
        "player",
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


def test_rules_orthogonal_edges() -> None:
    rules = GameRules.load()
    assert rules.get("topology", "orthogonal_edges_passable_once_lit") is True


def test_rules_fish_room_adjacent() -> None:
    rules = GameRules.load()
    assert rules.get("topology", "guaranteed_fish_room_adjacent_to_boss") is True


def test_rules_corrupted_shard_qty() -> None:
    rules = GameRules.load()
    qty = rules.get("enemies", "monster_shard_qty")
    assert qty["weak"] == {"min": 20, "max": 30}
    assert qty["strong"] == {"min": 80, "max": 100}
    assert qty["demi_boss"] == {"min": 50, "max": 60}


def test_rules_paddlefish_stop_burn() -> None:
    rules = GameRules.load()
    assert rules.get("resources", "paddlefish_stop_burn_cooking_level") == 47


def test_rules_corrupted_mob_stats() -> None:
    rules = GameRules.load()
    stats = rules.get("enemies", "combat_stats")
    assert stats["dark_beast"]["hitpoints"] == 100
    assert stats["bat"]["combat_level"] == 48
    assert rules.get("enemies", "weak_max_per_room") == 3
    assert rules.get("enemies", "strong_spawn_in_pairs") is True


def test_rules_sing_ticks() -> None:
    rules = GameRules.load()
    assert rules.get("crafting", "sing_ticks_per_item") == 1


def test_rules_weapon_speeds() -> None:
    rules = GameRules.load()
    speeds = rules.get("combat", "weapon_attack_speed_ticks")
    assert speeds["bow_rapid"] == 4
    assert speeds["bow_accurate"] == 5
    assert speeds["staff_accurate"] == 4
    assert speeds["halberd"] == 4
    assert rules.get("combat", "perfected_staff_max_hit") == 39


def test_rules_starting_slots() -> None:
    rules = GameRules.load()
    assert rules.get("inventory", "starting_occupied_inventory_slots") == 5
    starters = rules.get("inventory", "starting_items")
    assert starters["wielded"] == ["sceptre"]
    assert len(starters["inventory"]) == 5


def test_rules_egniol_stamina_prayer() -> None:
    rules = GameRules.load()
    assert rules.get("player", "egniol_acts_as_stamina") is True
    assert rules.get("timing", "stamina_effect_ticks") == 200
    assert rules.get("player", "prayer_drain_effect_protect") == 12
    assert rules.get("player", "prayer_drain_effect_rigour") == 24


def test_rules_stomp_trigger() -> None:
    rules = GameRules.load()
    assert rules.get("boss", "stomp_trigger") == "on_attack_tick"
