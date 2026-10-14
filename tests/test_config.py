"""Account/config validation."""

from __future__ import annotations

import pytest

from gauntletsim.config import (
    DEFAULT_MAGIC,
    DEFAULT_RANGED,
    AccountProfile,
    AppConfig,
    ConfigError,
    SimConfig,
)


def test_account_from_mapping_requires_magic_and_ranged() -> None:
    data = {
        "attack": 80,
        "strength": 80,
        "defence": 80,
        "hitpoints": 90,
        "prayer": 77,
        "agility": 70,
        "cooking": 70,
    }
    with pytest.raises(ConfigError, match="magic"):
        AccountProfile.from_mapping(data)
    data["magic"] = 85
    with pytest.raises(ConfigError, match="ranged"):
        AccountProfile.from_mapping(data)


def test_account_from_mapping_requires_other_stats() -> None:
    with pytest.raises(ConfigError, match="missing required"):
        AccountProfile.from_mapping({"magic": 85, "ranged": 85})


def test_account_rejects_unknown_keys() -> None:
    with pytest.raises(ConfigError, match="unknown account"):
        AccountProfile.from_mapping(
            {
                "attack": 80,
                "strength": 80,
                "defence": 80,
                "hitpoints": 90,
                "prayer": 77,
                "magic": 85,
                "ranged": 85,
                "agility": 70,
                "cooking": 70,
                "slayer": 99,
            }
        )


def test_phase1_defaults_magic_ranged_85() -> None:
    profile = AccountProfile.with_phase1_defaults(
        attack=80,
        strength=80,
        defence=80,
        hitpoints=90,
        prayer=77,
        agility=70,
        cooking=70,
    )
    assert profile.magic == DEFAULT_MAGIC == 85
    assert profile.ranged == DEFAULT_RANGED == 85


def test_demo_config_explicit_stats() -> None:
    cfg = AppConfig.phase1_demo()
    assert cfg.account.magic == 85
    assert cfg.account.ranged == 85
    assert cfg.account.attack == 80
    assert cfg.sim.mode == "corrupted_gauntlet"


def test_sim_config_rejects_bad_mode() -> None:
    with pytest.raises(ConfigError, match="corrupted_gauntlet"):
        SimConfig(mode="ordinary_gauntlet")
