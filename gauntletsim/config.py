"""Account profile and simulation parameters for GauntletSim."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

# Stats that must be provided explicitly (no silent defaults).
REQUIRED_COMBAT_STATS = (
    "attack",
    "strength",
    "defence",
    "hitpoints",
    "prayer",
    "magic",
    "ranged",
)

# Non-combat skills that affect prep; also required explicitly.
REQUIRED_OTHER_STATS = ("agility", "cooking")

DEFAULT_MAGIC = 85
DEFAULT_RANGED = 85


class ConfigError(ValueError):
    """Raised when account or sim configuration is incomplete or invalid."""


@dataclass(frozen=True)
class AccountProfile:
    """Combat and skill levels for a simulated account."""

    attack: int
    strength: int
    defence: int
    hitpoints: int
    prayer: int
    magic: int
    ranged: int
    agility: int
    cooking: int
    unlock_rigour: bool = False
    unlock_augury: bool = False
    unlock_piety: bool = False

    def __post_init__(self) -> None:
        for name in (*REQUIRED_COMBAT_STATS, *REQUIRED_OTHER_STATS):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise ConfigError(f"stat '{name}' must be an int")
            if value < 1 or value > 99:
                raise ConfigError(f"stat '{name}' must be in 1..99, got {value}")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> AccountProfile:
        if not isinstance(data, Mapping):
            raise ConfigError("account profile must be a mapping")
        missing = [
            key
            for key in (*REQUIRED_COMBAT_STATS, *REQUIRED_OTHER_STATS)
            if key not in data
        ]
        # Magic/Ranged may be omitted only when using from_defaults helpers;
        # from_mapping requires all required stats explicitly.
        if missing:
            raise ConfigError(
                "missing required account stats: " + ", ".join(sorted(missing))
            )
        known = {
            "attack",
            "strength",
            "defence",
            "hitpoints",
            "prayer",
            "magic",
            "ranged",
            "agility",
            "cooking",
            "unlock_rigour",
            "unlock_augury",
            "unlock_piety",
        }
        unknown = set(data) - known
        if unknown:
            raise ConfigError(
                "unknown account profile key(s): " + ", ".join(sorted(unknown))
            )
        return cls(
            attack=int(data["attack"]),
            strength=int(data["strength"]),
            defence=int(data["defence"]),
            hitpoints=int(data["hitpoints"]),
            prayer=int(data["prayer"]),
            magic=int(data["magic"]),
            ranged=int(data["ranged"]),
            agility=int(data["agility"]),
            cooking=int(data["cooking"]),
            unlock_rigour=bool(data.get("unlock_rigour", False)),
            unlock_augury=bool(data.get("unlock_augury", False)),
            unlock_piety=bool(data.get("unlock_piety", False)),
        )

    @classmethod
    def with_phase1_defaults(
        cls,
        *,
        attack: int,
        strength: int,
        defence: int,
        hitpoints: int,
        prayer: int,
        agility: int,
        cooking: int,
        magic: int = DEFAULT_MAGIC,
        ranged: int = DEFAULT_RANGED,
        unlock_rigour: bool = False,
        unlock_augury: bool = False,
        unlock_piety: bool = False,
    ) -> AccountProfile:
        """Build a profile with Magic/Ranged defaulting to 85; other stats required."""
        return cls(
            attack=attack,
            strength=strength,
            defence=defence,
            hitpoints=hitpoints,
            prayer=prayer,
            magic=magic,
            ranged=ranged,
            agility=agility,
            cooking=cooking,
            unlock_rigour=unlock_rigour,
            unlock_augury=unlock_augury,
            unlock_piety=unlock_piety,
        )


@dataclass(frozen=True)
class SimConfig:
    """Simulation parameters (seeds, prep override, logging)."""

    master_seed: int = 0
    prep_ticks: int | None = None
    log_level: str = "INFO"
    mode: str = "corrupted_gauntlet"

    def __post_init__(self) -> None:
        if not isinstance(self.master_seed, int):
            raise ConfigError("master_seed must be an int")
        if self.prep_ticks is not None and (
            not isinstance(self.prep_ticks, int) or self.prep_ticks < 0
        ):
            raise ConfigError("prep_ticks must be a non-negative int or None")
        if self.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            raise ConfigError("log_level must be DEBUG|INFO|WARNING|ERROR")
        if self.mode != "corrupted_gauntlet":
            raise ConfigError("Phase 1 only supports mode 'corrupted_gauntlet'")


@dataclass(frozen=True)
class AppConfig:
    """Top-level configuration bundle."""

    account: AccountProfile
    sim: SimConfig = field(default_factory=SimConfig)

    @classmethod
    def phase1_demo(cls) -> AppConfig:
        """Explicit demo profile: Magic/Ranged 85; other stats stated (not silent)."""
        account = AccountProfile.with_phase1_defaults(
            attack=80,
            strength=80,
            defence=80,
            hitpoints=90,
            prayer=77,
            agility=70,
            cooking=70,
            magic=DEFAULT_MAGIC,
            ranged=DEFAULT_RANGED,
            unlock_rigour=True,
            unlock_augury=True,
            unlock_piety=True,
        )
        return cls(account=account, sim=SimConfig(master_seed=0))
