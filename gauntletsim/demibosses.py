"""Prep-phase enemy and demi-boss encounter resolution (not full combat)."""

from __future__ import annotations

from dataclasses import dataclass, field
import random

from gauntletsim.game_rules import GameRules
from gauntletsim.inventory import Inventory, ItemId
from gauntletsim.rng import make_stream
from gauntletsim.room import Coord, DemiType, MobTier, Room


DEMI_TO_PART = {
    DemiType.BEAR: ItemId.SPIKE,
    DemiType.DRAGON: ItemId.ORB,
    DemiType.DARK_BEAST: ItemId.BOWSTRING,
}


@dataclass
class EncounterState:
    weak_kills: int = 0
    strong_kills: int = 0
    demi_kills: int = 0
    frames_dropped: int = 0
    t3_parts: set[ItemId] = field(default_factory=set)
    cleared_rooms: set[Coord] = field(default_factory=set)


@dataclass
class PrepEncounters:
    rules: GameRules
    rng: random.Random
    state: EncounterState = field(default_factory=EncounterState)

    @classmethod
    def create(cls, rules: GameRules, master_seed: int) -> PrepEncounters:
        return cls(rules=rules, rng=make_stream(master_seed, "prep_combat"))

    def _shard_drop(self, tier: str) -> tuple[int, int]:
        table = self.rules.get("enemies", "monster_shard_qty")[tier]
        return int(table["min"]), int(table["max"])

    def _add_shards(self, inv: Inventory, tier: str) -> int:
        lo, hi = self._shard_drop(tier)
        qty = self.rng.randint(lo, hi)
        # Scale by assumption if present
        try:
            scale = float(
                self.rules.assumption_default("resources.monster_shard_qty_override")
            )
        except KeyError:
            scale = 1.0
        qty = max(1, int(round(qty * scale)))
        if inv.can_add(ItemId.SHARDS, qty):
            inv.add(ItemId.SHARDS, qty)
            return qty
        return 0

    def clear_room(
        self, room: Room, inv: Inventory
    ) -> tuple[int, dict[str, int]]:
        """
        Resolve prep encounters in a room. Returns (ticks, drop summary).
        Idempotent if room already cleared.
        """
        if room.coord in self.state.cleared_rooms:
            return 0, {}
        if room.mob_tier == MobTier.NONE:
            self.state.cleared_rooms.add(room.coord)
            return 0, {}

        drops: dict[str, int] = {}
        ticks = 0

        if room.mob_tier == MobTier.WEAK:
            ticks = int(self.rules.assumption_default("combat.prep_weak_kill_ticks"))
            self.state.weak_kills += 1
            # First weak kill guarantees weapon frame
            if (
                self.rules.get("enemies", "first_weak_guarantees_weapon_frame")
                and self.state.frames_dropped == 0
            ):
                if inv.can_add(ItemId.WEAPON_FRAME):
                    inv.add(ItemId.WEAPON_FRAME)
                    self.state.frames_dropped += 1
                    drops["weapon_frame"] = 1
            shards = self._add_shards(inv, "weak")
            if shards:
                drops["shards"] = shards
            self._roll_secondary_drops(inv, "weak", drops, rolls=1)

        elif room.mob_tier == MobTier.STRONG:
            ticks = int(self.rules.assumption_default("combat.prep_strong_kill_ticks"))
            # Mid-level monsters spawn in pairs → two kills this room.
            self.state.strong_kills += 2
            # Wiki: weapon frame guaranteed after two mid-level kills.
            if self.state.frames_dropped == 0 and self.state.strong_kills >= 2:
                if inv.can_add(ItemId.WEAPON_FRAME):
                    inv.add(ItemId.WEAPON_FRAME)
                    self.state.frames_dropped += 1
                    drops["weapon_frame"] = 1
            shards = self._add_shards(inv, "strong")
            if shards:
                drops["shards"] = shards
            self._roll_secondary_drops(inv, "strong", drops, rolls=2)

        elif room.mob_tier == MobTier.DEMI_BOSS:
            ticks = int(self.rules.assumption_default("combat.prep_demi_kill_ticks"))
            self.state.demi_kills += 1
            # Always frame from demi
            if inv.can_add(ItemId.WEAPON_FRAME):
                inv.add(ItemId.WEAPON_FRAME)
                self.state.frames_dropped += 1
                drops["weapon_frame"] = drops.get("weapon_frame", 0) + 1
            shards = self._add_shards(inv, "demi_boss")
            if shards:
                drops["shards"] = shards
            assert room.demi_type is not None
            part = DEMI_TO_PART[room.demi_type]
            # Preferred part if not owned; else any missing T3 part
            owned = self.state.t3_parts
            if part not in owned:
                give = part
            else:
                missing = [p for p in DEMI_TO_PART.values() if p not in owned]
                give = self.rng.choice(missing) if missing else None
            if give is not None and inv.can_add(give):
                inv.add(give)
                self.state.t3_parts.add(give)
                drops[give.value] = 1
            # Demi secondary loot uses strong table once (assumption).
            self._roll_secondary_drops(inv, "strong", drops, rolls=1)

        self.state.cleared_rooms.add(room.coord)
        return ticks, drops

    def _roll_secondary_drops(
        self,
        inv: Inventory,
        tier: str,
        drops: dict[str, int],
        *,
        rolls: int,
    ) -> None:
        """Fish / grym / tele crystal — verified to exist; rates are assumptions."""
        if not self.rules.get("resources", "monsters_drop_fish_grym_teleport"):
            return
        try:
            table = self.rules.assumption_default(
                "enemies.monster_secondary_drop_chances"
            )
        except KeyError:
            return
        tier_table = table.get(tier, {})
        mapping = (
            ("raw_paddlefish", ItemId.RAW_PADDLEFISH),
            ("grym_leaf", ItemId.GRYM_LEAF),
            ("teleport_crystal", ItemId.TELEPORT_CRYSTAL),
        )
        for _ in range(rolls):
            for key, item in mapping:
                chance = float(tier_table.get(key, 0.0))
                if chance <= 0 or self.rng.random() >= chance:
                    continue
                if inv.can_add(item, 1):
                    inv.add(item, 1)
                    drops[key] = drops.get(key, 0) + 1
