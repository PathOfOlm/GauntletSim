"""Inventory capacity and stackable item management (Phase 3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ItemId(str, Enum):
    # Tools / starters
    AXE = "axe"
    PICKAXE = "pickaxe"
    HARPOON = "harpoon"
    PESTLE = "pestle_and_mortar"
    TELEPORT_CRYSTAL = "teleport_crystal"
    # Materials (stackable)
    ORE = "ore"
    BARK = "bark"
    LINUM = "linum"
    GRYM_LEAF = "grym_leaf"
    SHARDS = "shards"
    # Food / potion intermediates
    RAW_PADDLEFISH = "raw_paddlefish"
    PADDLEFISH = "paddlefish"
    CORRUPTED_PADDLEFISH = "corrupted_paddlefish"
    VIAL = "vial"
    WATER_VIAL = "water_vial"
    GRYM_POTION_UNF = "grym_potion_unf"
    EGNIOL_3 = "egniol_3"
    # Frames / T3 parts / weapons / armour
    WEAPON_FRAME = "weapon_frame"
    SPIKE = "spike"
    ORB = "orb"
    BOWSTRING = "bowstring"
    BOW_BASIC = "bow_basic"
    BOW_ATTUNED = "bow_attuned"
    BOW_PERFECTED = "bow_perfected"
    STAFF_BASIC = "staff_basic"
    STAFF_ATTUNED = "staff_attuned"
    STAFF_PERFECTED = "staff_perfected"
    HALBERD_BASIC = "halberd_basic"
    HALBERD_ATTUNED = "halberd_attuned"
    HALBERD_PERFECTED = "halberd_perfected"
    HELM_BASIC = "helm_basic"
    HELM_ATTUNED = "helm_attuned"
    HELM_PERFECTED = "helm_perfected"
    BODY_BASIC = "body_basic"
    BODY_ATTUNED = "body_attuned"
    BODY_PERFECTED = "body_perfected"
    LEGS_BASIC = "legs_basic"
    LEGS_ATTUNED = "legs_attuned"
    LEGS_PERFECTED = "legs_perfected"


STACKABLE = frozenset(
    {
        ItemId.ORE,
        ItemId.BARK,
        ItemId.LINUM,
        ItemId.GRYM_LEAF,
        ItemId.SHARDS,
        ItemId.RAW_PADDLEFISH,
        ItemId.PADDLEFISH,
        ItemId.CORRUPTED_PADDLEFISH,
        ItemId.VIAL,
        ItemId.WATER_VIAL,
        ItemId.GRYM_POTION_UNF,
        ItemId.EGNIOL_3,
        ItemId.WEAPON_FRAME,
        ItemId.SPIKE,
        ItemId.ORB,
        ItemId.BOWSTRING,
    }
)


class InventoryError(ValueError):
    """Illegal inventory operation."""


@dataclass
class Inventory:
    capacity: int = 28
    # Non-stackables occupy one slot each (list). Stackables use qty map + one slot.
    _stacks: dict[ItemId, int] = field(default_factory=dict)
    _uniques: list[ItemId] = field(default_factory=list)

    def slots_used(self) -> int:
        return len(self._stacks) + len(self._uniques)

    def free_slots(self) -> int:
        return self.capacity - self.slots_used()

    def count(self, item: ItemId) -> int:
        if item in STACKABLE:
            return self._stacks.get(item, 0)
        return sum(1 for u in self._uniques if u == item)

    def has(self, item: ItemId, qty: int = 1) -> bool:
        return self.count(item) >= qty

    def can_add(self, item: ItemId, qty: int = 1) -> bool:
        if qty <= 0:
            return True
        if item in STACKABLE:
            if item in self._stacks:
                return True
            return self.free_slots() >= 1
        return self.free_slots() >= qty

    def add(self, item: ItemId, qty: int = 1) -> None:
        if qty <= 0:
            return
        if not self.can_add(item, qty):
            raise InventoryError(
                f"inventory full (need space for {qty}× {item.value})"
            )
        if item in STACKABLE:
            self._stacks[item] = self._stacks.get(item, 0) + qty
        else:
            for _ in range(qty):
                if self.free_slots() < 1:
                    raise InventoryError("inventory full")
                self._uniques.append(item)

    def remove(self, item: ItemId, qty: int = 1) -> None:
        if qty <= 0:
            return
        if not self.has(item, qty):
            raise InventoryError(f"missing {qty}× {item.value}")
        if item in STACKABLE:
            new = self._stacks[item] - qty
            if new == 0:
                del self._stacks[item]
            else:
                self._stacks[item] = new
        else:
            for _ in range(qty):
                self._uniques.remove(item)

    def summary(self) -> dict[str, int]:
        out: dict[str, int] = {k.value: v for k, v in sorted(self._stacks.items())}
        for u in self._uniques:
            out[u.value] = out.get(u.value, 0) + 1
        return out


def starting_inventory(capacity: int = 28) -> Inventory:
    """Sceptre is wielded (not in inv); 5 starter tool slots."""
    inv = Inventory(capacity=capacity)
    for item in (
        ItemId.AXE,
        ItemId.PICKAXE,
        ItemId.HARPOON,
        ItemId.PESTLE,
        ItemId.TELEPORT_CRYSTAL,
    ):
        inv.add(item)
    return inv
