"""Singing-bowl crafting, cooking, and egniol (Phase 3)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from gauntletsim.game_rules import GameRules
from gauntletsim.inventory import Inventory, InventoryError, ItemId


class CraftError(ValueError):
    pass


class WeaponStyle(str, Enum):
    BOW = "bow"
    STAFF = "staff"
    HALBERD = "halberd"


class ArmourSlot(str, Enum):
    HELM = "helm"
    BODY = "body"
    LEGS = "legs"


_BASIC = {
    WeaponStyle.BOW: ItemId.BOW_BASIC,
    WeaponStyle.STAFF: ItemId.STAFF_BASIC,
    WeaponStyle.HALBERD: ItemId.HALBERD_BASIC,
}
_ATTUNED = {
    WeaponStyle.BOW: ItemId.BOW_ATTUNED,
    WeaponStyle.STAFF: ItemId.STAFF_ATTUNED,
    WeaponStyle.HALBERD: ItemId.HALBERD_ATTUNED,
}
_PERFECTED = {
    WeaponStyle.BOW: ItemId.BOW_PERFECTED,
    WeaponStyle.STAFF: ItemId.STAFF_PERFECTED,
    WeaponStyle.HALBERD: ItemId.HALBERD_PERFECTED,
}
_T3_PART = {
    WeaponStyle.BOW: ItemId.BOWSTRING,
    WeaponStyle.STAFF: ItemId.ORB,
    WeaponStyle.HALBERD: ItemId.SPIKE,
}
_ARMOUR_BASIC = {
    ArmourSlot.HELM: ItemId.HELM_BASIC,
    ArmourSlot.BODY: ItemId.BODY_BASIC,
    ArmourSlot.LEGS: ItemId.LEGS_BASIC,
}
_ARMOUR_ATTUNED = {
    ArmourSlot.HELM: ItemId.HELM_ATTUNED,
    ArmourSlot.BODY: ItemId.BODY_ATTUNED,
    ArmourSlot.LEGS: ItemId.LEGS_ATTUNED,
}
_ARMOUR_PERFECTED = {
    ArmourSlot.HELM: ItemId.HELM_PERFECTED,
    ArmourSlot.BODY: ItemId.BODY_PERFECTED,
    ArmourSlot.LEGS: ItemId.LEGS_PERFECTED,
}


@dataclass
class CraftingBench:
    rules: GameRules

    @property
    def sing_ticks(self) -> int:
        return int(self.rules.get("crafting", "sing_ticks_per_item"))

    def _need(self, inv: Inventory, item: ItemId, qty: int) -> None:
        if not inv.has(item, qty):
            raise CraftError(f"need {qty}× {item.value}")

    def craft_basic_weapon(self, inv: Inventory, style: WeaponStyle) -> int:
        self._need(inv, ItemId.WEAPON_FRAME, 1)
        shards = int(self.rules.get("crafting", "weapon_basic_shards"))
        if shards:
            self._need(inv, ItemId.SHARDS, shards)
        out = _BASIC[style]
        if not inv.can_add(out):
            raise InventoryError("no space for weapon")
        inv.remove(ItemId.WEAPON_FRAME, 1)
        if shards:
            inv.remove(ItemId.SHARDS, shards)
        inv.add(out)
        return self.sing_ticks

    def upgrade_weapon_attuned(self, inv: Inventory, style: WeaponStyle) -> int:
        basic = _BASIC[style]
        self._need(inv, basic, 1)
        shards = int(self.rules.get("crafting", "weapon_attuned_shards"))
        self._need(inv, ItemId.SHARDS, shards)
        out = _ATTUNED[style]
        inv.remove(basic, 1)
        inv.remove(ItemId.SHARDS, shards)
        inv.add(out)
        return self.sing_ticks

    def upgrade_weapon_perfected(self, inv: Inventory, style: WeaponStyle) -> int:
        attuned = _ATTUNED[style]
        part = _T3_PART[style]
        self._need(inv, attuned, 1)
        self._need(inv, part, 1)
        out = _PERFECTED[style]
        inv.remove(attuned, 1)
        inv.remove(part, 1)
        inv.add(out)
        return self.sing_ticks

    def craft_armour_basic(self, inv: Inventory, slot: ArmourSlot) -> int:
        mats = self.rules.get("crafting", "armour_materials")["basic_any"]
        shards = int(self.rules.get("crafting", "armour_shards")["basic_any"])
        self._need(inv, ItemId.ORE, mats["ore"])
        self._need(inv, ItemId.BARK, mats["bark"])
        self._need(inv, ItemId.LINUM, mats["linum"])
        self._need(inv, ItemId.SHARDS, shards)
        out = _ARMOUR_BASIC[slot]
        if not inv.can_add(out):
            raise InventoryError("no space for armour")
        inv.remove(ItemId.ORE, mats["ore"])
        inv.remove(ItemId.BARK, mats["bark"])
        inv.remove(ItemId.LINUM, mats["linum"])
        inv.remove(ItemId.SHARDS, shards)
        inv.add(out)
        return self.sing_ticks

    def upgrade_armour_attuned(self, inv: Inventory, slot: ArmourSlot) -> int:
        basic = _ARMOUR_BASIC[slot]
        self._need(inv, basic, 1)
        key = {
            ArmourSlot.BODY: "attuned_body",
            ArmourSlot.HELM: "attuned_helm",
            ArmourSlot.LEGS: "attuned_legs",
        }[slot]
        mats = self.rules.get("crafting", "armour_materials")[key]
        shards = int(self.rules.get("crafting", "armour_shards")[key])
        self._need(inv, ItemId.ORE, mats["ore"])
        self._need(inv, ItemId.BARK, mats["bark"])
        self._need(inv, ItemId.LINUM, mats["linum"])
        self._need(inv, ItemId.SHARDS, shards)
        out = _ARMOUR_ATTUNED[slot]
        inv.remove(basic, 1)
        inv.remove(ItemId.ORE, mats["ore"])
        inv.remove(ItemId.BARK, mats["bark"])
        inv.remove(ItemId.LINUM, mats["linum"])
        inv.remove(ItemId.SHARDS, shards)
        inv.add(out)
        return self.sing_ticks

    def cook_paddlefish(self, inv: Inventory, cooking_level: int) -> tuple[int, bool]:
        """Cook one raw fish. Returns (ticks, success). Burn only below level 47."""
        self._need(inv, ItemId.RAW_PADDLEFISH, 1)
        ticks = int(self.rules.get("timing", "cook_paddlefish_ticks"))
        stop = int(self.rules.get("resources", "paddlefish_stop_burn_cooking_level"))
        inv.remove(ItemId.RAW_PADDLEFISH, 1)
        if cooking_level >= stop:
            if not inv.can_add(ItemId.PADDLEFISH):
                inv.add(ItemId.RAW_PADDLEFISH, 1)
                raise InventoryError("no space for cooked fish")
            inv.add(ItemId.PADDLEFISH)
            return ticks, True
        # Below stop level: burn chance from assumptions
        burn_p = float(
            self.rules.assumption_default(
                "crafting.paddlefish_burn_probability_below_47"
            )
        )
        # Deterministic without RNG here: treat as success for craft API;
        # PrepSim passes RNG when needed. Default path: no burn if p==0.
        if burn_p <= 0:
            inv.add(ItemId.PADDLEFISH)
            return ticks, True
        # Caller should use cook_paddlefish_rng for stochastic burns.
        inv.add(ItemId.PADDLEFISH)
        return ticks, True

    def cook_paddlefish_rng(
        self, inv: Inventory, cooking_level: int, rng
    ) -> tuple[int, bool]:
        self._need(inv, ItemId.RAW_PADDLEFISH, 1)
        ticks = int(self.rules.get("timing", "cook_paddlefish_ticks"))
        stop = int(self.rules.get("resources", "paddlefish_stop_burn_cooking_level"))
        inv.remove(ItemId.RAW_PADDLEFISH, 1)
        if cooking_level >= stop:
            inv.add(ItemId.PADDLEFISH)
            return ticks, True
        burn_p = float(
            self.rules.assumption_default(
                "crafting.paddlefish_burn_probability_below_47"
            )
        )
        if rng.random() < burn_p:
            return ticks, False
        inv.add(ItemId.PADDLEFISH)
        return ticks, True

    def craft_vial(self, inv: Inventory) -> int:
        shards = int(self.rules.get("crafting", "vial_shards"))
        self._need(inv, ItemId.SHARDS, shards)
        if not inv.can_add(ItemId.VIAL):
            raise InventoryError("no space for vial")
        inv.remove(ItemId.SHARDS, shards)
        inv.add(ItemId.VIAL)
        return self.sing_ticks

    def fill_vial(self, inv: Inventory) -> int:
        self._need(inv, ItemId.VIAL, 1)
        inv.remove(ItemId.VIAL, 1)
        inv.add(ItemId.WATER_VIAL)
        return int(self.rules.get("timing", "fill_vial_ticks"))

    def make_grym_unf(self, inv: Inventory) -> int:
        self._need(inv, ItemId.WATER_VIAL, 1)
        self._need(inv, ItemId.GRYM_LEAF, 1)
        inv.remove(ItemId.WATER_VIAL, 1)
        inv.remove(ItemId.GRYM_LEAF, 1)
        inv.add(ItemId.GRYM_POTION_UNF)
        return 1

    def make_egniol(self, inv: Inventory) -> int:
        dust = int(self.rules.get("crafting", "egniol_dust_shards"))
        self._need(inv, ItemId.GRYM_POTION_UNF, 1)
        self._need(inv, ItemId.SHARDS, dust)
        self._need(inv, ItemId.PESTLE, 1)
        inv.remove(ItemId.GRYM_POTION_UNF, 1)
        inv.remove(ItemId.SHARDS, dust)
        inv.add(ItemId.EGNIOL_3)
        return int(self.rules.get("timing", "egniol_create_ticks"))

    def egniol_prayer_restore(self, prayer_level: int) -> int:
        div = int(self.rules.get("crafting", "egniol_prayer_restore_divisor"))
        flat = int(self.rules.get("crafting", "egniol_prayer_restore_flat"))
        return prayer_level // div + flat

    def crush_t3_component(self, inv: Inventory, item: ItemId) -> int:
        """Pestle a spare T3 demi component into crystal shards."""
        if item not in (ItemId.SPIKE, ItemId.ORB, ItemId.BOWSTRING):
            raise ValueError(f"cannot crush {item}")
        self._need(inv, item, 1)
        self._need(inv, ItemId.PESTLE, 1)
        shards = int(self.rules.get("crafting", "crush_t3_component_shards"))
        inv.remove(item, 1)
        if not inv.can_add(ItemId.SHARDS, shards):
            raise InventoryError("no space for crushed shards")
        inv.add(ItemId.SHARDS, shards)
        return 1

    def craft_teleport_crystal(self, inv: Inventory) -> int:
        shards = int(self.rules.get("crafting", "teleport_crystal_shards"))
        self._need(inv, ItemId.SHARDS, shards)
        if not inv.can_add(ItemId.TELEPORT_CRYSTAL):
            raise InventoryError("no space for teleport crystal")
        inv.remove(ItemId.SHARDS, shards)
        inv.add(ItemId.TELEPORT_CRYSTAL)
        return self.sing_ticks
