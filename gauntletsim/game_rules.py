"""Load and validate Corrupted Gauntlet rules and assumption defaults."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
DEFAULT_RULES_PATH = REPO_ROOT / "data" / "rules" / "corrupted_gauntlet.json"
DEFAULT_ASSUMPTIONS_PATH = REPO_ROOT / "data" / "assumptions" / "defaults.json"

RULES_ALLOWED_TOP_KEYS = frozenset(
    {
        "meta",
        "sources",
        "timing",
        "topology",
        "resources",
        "crafting",
        "enemies",
        "boss",
        "inventory",
    }
)

RULE_ENTRY_ALLOWED_KEYS = frozenset({"value", "confidence", "source_ids"})
ALLOWED_CONFIDENCE = frozenset(
    {"verified", "strongly_supported", "inferred", "unknown"}
)

ASSUMPTIONS_ALLOWED_TOP_KEYS = frozenset({"meta", "assumptions"})
ASSUMPTION_ENTRY_REQUIRED = frozenset(
    {"id", "label", "parameter", "default", "range", "unit"}
)
ASSUMPTION_ENTRY_ALLOWED = ASSUMPTION_ENTRY_REQUIRED


class RulesLoadError(ValueError):
    """Raised when rules or assumptions JSON is malformed or has unknown keys."""


def _require_mapping(data: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(data, dict):
        raise RulesLoadError(f"{label} must be a JSON object")
    return data


def _reject_unknown_keys(
    mapping: Mapping[str, Any], allowed: frozenset[str], label: str
) -> None:
    unknown = set(mapping) - allowed
    if unknown:
        keys = ", ".join(sorted(unknown))
        raise RulesLoadError(f"{label} has unknown key(s): {keys}")


def _load_json(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RulesLoadError(f"cannot read {path}: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RulesLoadError(f"invalid JSON in {path}: {exc}") from exc


def _validate_rule_entry(entry: Any, path: str) -> Any:
    mapping = _require_mapping(entry, path)
    _reject_unknown_keys(mapping, RULE_ENTRY_ALLOWED_KEYS, path)
    for key in ("value", "confidence", "source_ids"):
        if key not in mapping:
            raise RulesLoadError(f"{path} missing required field '{key}'")
    confidence = mapping["confidence"]
    if confidence not in ALLOWED_CONFIDENCE:
        raise RulesLoadError(
            f"{path}.confidence must be one of {sorted(ALLOWED_CONFIDENCE)}"
        )
    if confidence in {"inferred", "unknown"}:
        raise RulesLoadError(
            f"{path} has confidence '{confidence}'; "
            "rules JSON may only contain verified or strongly_supported entries"
        )
    source_ids = mapping["source_ids"]
    if not isinstance(source_ids, list) or not source_ids:
        raise RulesLoadError(f"{path}.source_ids must be a non-empty list")
    if not all(isinstance(s, str) and s for s in source_ids):
        raise RulesLoadError(f"{path}.source_ids must be non-empty strings")
    return mapping["value"]


def _validate_rules_section(
    section: Mapping[str, Any], section_name: str
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, entry in section.items():
        path = f"{section_name}.{key}"
        out[key] = _validate_rule_entry(entry, path)
    return out


def validate_rules_document(data: Mapping[str, Any]) -> dict[str, Any]:
    _reject_unknown_keys(data, RULES_ALLOWED_TOP_KEYS, "rules root")
    for required in RULES_ALLOWED_TOP_KEYS:
        if required not in data:
            raise RulesLoadError(f"rules missing top-level key '{required}'")

    meta = _require_mapping(data["meta"], "meta")
    sources = _require_mapping(data["sources"], "sources")
    if not sources:
        raise RulesLoadError("sources must not be empty")

    sections: dict[str, Any] = {"meta": dict(meta), "sources": dict(sources)}
    for name in (
        "timing",
        "topology",
        "resources",
        "crafting",
        "enemies",
        "boss",
        "inventory",
    ):
        section = _require_mapping(data[name], name)
        sections[name] = _validate_rules_section(section, name)
    return sections


def validate_assumptions_document(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    _reject_unknown_keys(data, ASSUMPTIONS_ALLOWED_TOP_KEYS, "assumptions root")
    if "assumptions" not in data:
        raise RulesLoadError("assumptions document missing 'assumptions'")
    raw = data["assumptions"]
    if not isinstance(raw, list) or not raw:
        raise RulesLoadError("'assumptions' must be a non-empty list")

    seen_ids: set[str] = set()
    seen_params: set[str] = set()
    out: list[dict[str, Any]] = []
    for i, entry in enumerate(raw):
        label = f"assumptions[{i}]"
        mapping = _require_mapping(entry, label)
        _reject_unknown_keys(mapping, ASSUMPTION_ENTRY_ALLOWED, label)
        missing = ASSUMPTION_ENTRY_REQUIRED - set(mapping)
        if missing:
            raise RulesLoadError(
                f"{label} missing field(s): {', '.join(sorted(missing))}"
            )
        assumption_id = mapping["id"]
        parameter = mapping["parameter"]
        if not isinstance(assumption_id, str) or not assumption_id:
            raise RulesLoadError(f"{label}.id must be a non-empty string")
        if assumption_id in seen_ids:
            raise RulesLoadError(f"duplicate assumption id '{assumption_id}'")
        if not isinstance(parameter, str) or not parameter:
            raise RulesLoadError(f"{label}.parameter must be a non-empty string")
        if parameter in seen_params:
            raise RulesLoadError(f"duplicate assumption parameter '{parameter}'")
        if not isinstance(mapping["label"], str) or not mapping["label"]:
            raise RulesLoadError(f"{label}.label must be a non-empty string")
        if "range" not in mapping or mapping["range"] in (None, ""):
            raise RulesLoadError(f"{label}.range is required")
        seen_ids.add(assumption_id)
        seen_params.add(parameter)
        out.append(dict(mapping))
    return out


@dataclass(frozen=True)
class GameRules:
    """Typed accessors over validated rules + assumptions."""

    rules_path: Path
    assumptions_path: Path
    _sections: dict[str, Any]
    assumptions: tuple[dict[str, Any], ...]

    @classmethod
    def load(
        cls,
        rules_path: Path | None = None,
        assumptions_path: Path | None = None,
    ) -> GameRules:
        rules_path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
        assumptions_path = (
            Path(assumptions_path) if assumptions_path else DEFAULT_ASSUMPTIONS_PATH
        )
        rules_doc = validate_rules_document(
            _require_mapping(_load_json(rules_path), "rules root")
        )
        assumptions = validate_assumptions_document(
            _require_mapping(_load_json(assumptions_path), "assumptions root")
        )
        return cls(
            rules_path=rules_path,
            assumptions_path=assumptions_path,
            _sections=rules_doc,
            assumptions=tuple(assumptions),
        )

    def section(self, name: str) -> Mapping[str, Any]:
        if name not in self._sections:
            raise KeyError(name)
        value = self._sections[name]
        if not isinstance(value, dict):
            raise KeyError(name)
        return value

    def get(self, section_name: str, key: str) -> Any:
        return self.section(section_name)[key]

    @property
    def sources(self) -> Mapping[str, str]:
        return self.section("sources")  # type: ignore[return-value]

    @property
    def tick_seconds(self) -> float:
        return float(self.get("timing", "tick_seconds"))

    @property
    def prep_seconds(self) -> int:
        return int(self.get("timing", "prep_seconds"))

    @property
    def prep_ticks(self) -> int:
        return int(self.get("timing", "prep_ticks"))

    @property
    def grid_size(self) -> tuple[int, int]:
        return (
            int(self.get("topology", "grid_width")),
            int(self.get("topology", "grid_height")),
        )

    @property
    def hunllef_hitpoints(self) -> int:
        return int(self.get("boss", "hitpoints"))

    @property
    def rule_entry_count(self) -> int:
        count = 0
        for name in (
            "timing",
            "topology",
            "resources",
            "crafting",
            "enemies",
            "boss",
            "inventory",
        ):
            count += len(self.section(name))
        return count

    @property
    def assumption_count(self) -> int:
        return len(self.assumptions)

    @property
    def unresolved_unknown_count(self) -> int:
        """Number of labeled assumptions (= open unknowns for Phase 1)."""
        return self.assumption_count

    def assumption_by_id(self, assumption_id: str) -> dict[str, Any]:
        for item in self.assumptions:
            if item["id"] == assumption_id:
                return item
        raise KeyError(assumption_id)

    def assumption_default(self, parameter: str) -> Any:
        for item in self.assumptions:
            if item["parameter"] == parameter:
                return item["default"]
        raise KeyError(parameter)
