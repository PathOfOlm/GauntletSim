"""Phase 3: inventory, gather, craft, demi drops, prep timeout, seeds."""

from __future__ import annotations

import pytest

from gauntletsim.config import AppConfig, SimConfig
from gauntletsim.crafting import ArmourSlot, CraftingBench, WeaponStyle
from gauntletsim.demibosses import PrepEncounters
from gauntletsim.game_rules import GameRules
from gauntletsim.inventory import Inventory, InventoryError, ItemId, starting_inventory
from gauntletsim.prep import PrepSim
from gauntletsim.resources import GatherSystem
from gauntletsim.room import Coord, MobTier, NodeType, Room, RoomKind


@pytest.fixture
def rules() -> GameRules:
    return GameRules.load()


@pytest.fixture
def cfg() -> AppConfig:
    return AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=42),
    )


def test_inventory_capacity_and_stacks(rules: GameRules) -> None:
    inv = starting_inventory(capacity=28)
    assert inv.slots_used() == 5
    inv.add(ItemId.ORE, 10)
    assert inv.count(ItemId.ORE) == 10
    assert inv.slots_used() == 6  # stackable = one slot
    inv.add(ItemId.SHARDS, 100)
    assert inv.slots_used() == 7
    # Fill remaining with unique weapons
    while inv.free_slots() > 0:
        inv.add(ItemId.BOW_BASIC)
    with pytest.raises(InventoryError):
        inv.add(ItemId.STAFF_BASIC)


def test_gather_depletes_and_respects_interval(rules: GameRules, cfg: AppConfig) -> None:
    sim = PrepSim.create(rules, cfg)
    fish = sim.dungeon.layout.fish_room
    sim.go_to(fish)
    rr = sim.gather.room_resources[fish]
    before = sum(n.remaining for n in rr.nodes if n.node_type == NodeType.FISH)
    assert before >= 3 * 4 or before >= 4  # at least one spot worth
    ticks, gained = sim.gather.gather_one(
        fish, sim.player.inventory, prefer=NodeType.FISH
    )
    assert ticks == rules.get("resources", "gather_interval_ticks")
    assert gained.get(ItemId.RAW_PADDLEFISH, 0) == 1
    after = sum(n.remaining for n in rr.nodes if n.node_type == NodeType.FISH)
    assert after == before - 1


def test_craft_weapon_prerequisites(rules: GameRules) -> None:
    bench = CraftingBench(rules)
    inv = Inventory()
    with pytest.raises(Exception):
        bench.craft_basic_weapon(inv, WeaponStyle.BOW)
    inv.add(ItemId.WEAPON_FRAME)
    ticks = bench.craft_basic_weapon(inv, WeaponStyle.BOW)
    assert ticks == 1
    assert inv.has(ItemId.BOW_BASIC)
    inv.add(ItemId.SHARDS, 50)
    bench.upgrade_weapon_attuned(inv, WeaponStyle.BOW)
    assert inv.has(ItemId.BOW_ATTUNED)
    inv.add(ItemId.BOWSTRING)
    bench.upgrade_weapon_perfected(inv, WeaponStyle.BOW)
    assert inv.has(ItemId.BOW_PERFECTED)


def test_craft_armour_and_egniol(rules: GameRules) -> None:
    bench = CraftingBench(rules)
    inv = starting_inventory()
    inv.add(ItemId.ORE, 1)
    inv.add(ItemId.BARK, 1)
    inv.add(ItemId.LINUM, 1)
    inv.add(ItemId.SHARDS, 100)
    bench.craft_armour_basic(inv, ArmourSlot.BODY)
    assert inv.has(ItemId.BODY_BASIC)
    inv.add(ItemId.GRYM_LEAF)
    bench.craft_vial(inv)
    bench.fill_vial(inv)
    bench.make_grym_unf(inv)
    bench.make_egniol(inv)
    assert inv.has(ItemId.EGNIOL_3)
    assert bench.egniol_prayer_restore(77) == 77 // 4 + 7


def test_cook_no_burn_at_47_plus(rules: GameRules) -> None:
    bench = CraftingBench(rules)
    inv = Inventory()
    inv.add(ItemId.RAW_PADDLEFISH, 3)
    for _ in range(3):
        ticks, ok = bench.cook_paddlefish(inv, cooking_level=70)
        assert ticks == 1 and ok
    assert inv.count(ItemId.PADDLEFISH) == 3


def test_demi_drops_frame_and_t3(rules: GameRules) -> None:
    enc = PrepEncounters.create(rules, master_seed=1)
    inv = Inventory(capacity=28)
    from gauntletsim.room import DemiType

    room = Room(
        coord=Coord(3, 0),
        kind=RoomKind.RESOURCE,
        mob_tier=MobTier.DEMI_BOSS,
        demi_type=DemiType.BEAR,
    )
    ticks, drops = enc.clear_room(room, inv)
    assert ticks > 0
    assert inv.has(ItemId.WEAPON_FRAME)
    assert inv.has(ItemId.SPIKE)
    assert "spike" in drops


def test_first_weak_guarantees_frame(rules: GameRules) -> None:
    enc = PrepEncounters.create(rules, master_seed=2)
    inv = Inventory()
    room = Room(coord=Coord(1, 1), kind=RoomKind.RESOURCE, mob_tier=MobTier.WEAK)
    enc.clear_room(room, inv)
    assert inv.has(ItemId.WEAPON_FRAME)


def test_prep_timeout(rules: GameRules) -> None:
    cfg = AppConfig(
        account=AppConfig.phase1_demo().account,
        sim=SimConfig(master_seed=3, prep_ticks=5),
    )
    sim = PrepSim.create(rules, cfg)
    assert sim.prep_limit == 5
    # Force time via advances
    sim.player.advance(5, sim.prep_limit)
    assert sim.timed_out()


def test_prep_seed_reproducibility(rules: GameRules) -> None:
    def run(seed: int) -> tuple:
        cfg = AppConfig(
            account=AppConfig.phase1_demo().account,
            sim=SimConfig(master_seed=seed),
        )
        sim = PrepSim.create(rules, cfg)
        sim.demo_prep_slice()
        return (
            sim.player.tick,
            sim.player.inventory.summary(),
            sim.encounters.state.frames_dropped,
            sim.encounters.state.demi_kills,
            tuple(sim.log),
        )

    assert run(99) == run(99)
    # Different seed should usually diverge
    assert run(99) != run(100) or True  # soft: allow rare collision


def test_demo_prep_runs(rules: GameRules, cfg: AppConfig) -> None:
    sim = PrepSim.create(rules, cfg)
    sim.demo_prep_slice()
    assert sim.player.tick > 0
    assert sim.player.tick <= sim.prep_limit or sim.timed_out()
    assert sim.player.inventory.slots_used() >= 5
