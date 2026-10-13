"""Player position, exploration, and prep vitals (Phase 2–3)."""

from __future__ import annotations

from dataclasses import dataclass, field

from gauntletsim.config import AccountProfile
from gauntletsim.inventory import Inventory, ItemId, starting_inventory
from gauntletsim.room import Coord, Room, RoomKind, orthogonal_neighbors


class MovementError(ValueError):
    """Illegal movement / lighting action."""


@dataclass
class Equipment:
    """Equipped gear tiers (0=none … 3=perfected). Weapons by style presence."""

    helm_tier: int = 0
    body_tier: int = 0
    legs_tier: int = 0
    has_bow: int = 0  # tier
    has_staff: int = 0
    has_halberd: int = 0

    def armour_tier_sum(self) -> int:
        return self.helm_tier + self.body_tier + self.legs_tier

    def sync_from_inventory(self, inv: Inventory) -> None:
        def tier(*items: tuple[ItemId, int]) -> int:
            best = 0
            for item, t in items:
                if inv.has(item):
                    best = max(best, t)
            return best

        self.helm_tier = tier(
            (ItemId.HELM_BASIC, 1),
            (ItemId.HELM_ATTUNED, 2),
            (ItemId.HELM_PERFECTED, 3),
        )
        self.body_tier = tier(
            (ItemId.BODY_BASIC, 1),
            (ItemId.BODY_ATTUNED, 2),
            (ItemId.BODY_PERFECTED, 3),
        )
        self.legs_tier = tier(
            (ItemId.LEGS_BASIC, 1),
            (ItemId.LEGS_ATTUNED, 2),
            (ItemId.LEGS_PERFECTED, 3),
        )
        self.has_bow = tier(
            (ItemId.BOW_BASIC, 1),
            (ItemId.BOW_ATTUNED, 2),
            (ItemId.BOW_PERFECTED, 3),
        )
        self.has_staff = tier(
            (ItemId.STAFF_BASIC, 1),
            (ItemId.STAFF_ATTUNED, 2),
            (ItemId.STAFF_PERFECTED, 3),
        )
        self.has_halberd = tier(
            (ItemId.HALBERD_BASIC, 1),
            (ItemId.HALBERD_ATTUNED, 2),
            (ItemId.HALBERD_PERFECTED, 3),
        )


@dataclass
class PlayerState:
    coord: Coord
    tick: int = 0
    hitpoints: int = 90
    hitpoints_max: int = 90
    prayer: int = 77
    prayer_max: int = 77
    inventory: Inventory = field(default_factory=starting_inventory)
    equipment: Equipment = field(default_factory=Equipment)
    timed_out: bool = False
    entered_boss: bool = False

    @classmethod
    def from_account(cls, coord: Coord, account: AccountProfile) -> PlayerState:
        return cls(
            coord=coord,
            hitpoints=account.hitpoints,
            hitpoints_max=account.hitpoints,
            prayer=account.prayer,
            prayer_max=account.prayer,
            inventory=starting_inventory(),
        )

    def advance(self, ticks: int, prep_limit: int) -> None:
        self.tick += ticks
        if self.tick >= prep_limit:
            self.timed_out = True

    def remaining_prep_ticks(self, prep_limit: int) -> int:
        return max(0, prep_limit - self.tick)

    def drink_egniol(self, prayer_restore: int, run_energy_percent: int = 40) -> None:
        if not self.inventory.has(ItemId.EGNIOL_3):
            raise ValueError("no egniol")
        self.inventory.remove(ItemId.EGNIOL_3)
        self.prayer = min(self.prayer_max, self.prayer + prayer_restore)
        # run energy tracked later; percent accepted for API completeness
        _ = run_energy_percent

    def eat_paddlefish(self, heal: int = 20) -> None:
        if not self.inventory.has(ItemId.PADDLEFISH):
            raise ValueError("no paddlefish")
        self.inventory.remove(ItemId.PADDLEFISH)
        self.hitpoints = min(self.hitpoints_max, self.hitpoints + heal)

    def move_or_light(
        self,
        rooms: dict[Coord, Room],
        target: Coord,
        *,
        width: int = 7,
        height: int = 7,
        light_ticks: int = 1,
        move_ticks: int = 1,
        prep_limit: int | None = None,
    ) -> int:
        if target not in rooms:
            raise MovementError(f"no room at {target}")
        if target not in orthogonal_neighbors(self.coord, width, height):
            raise MovementError("target not orthogonally adjacent")

        room = rooms[target]
        if not room.exists:
            raise MovementError("room does not exist")

        if room.discovered:
            self.coord = target
            spent = move_ticks
        elif room.kind == RoomKind.BOSS:
            raise MovementError(
                "boss room not entered via light; use enter_boss when ready"
            )
        else:
            room.discovered = True
            self.coord = target
            spent = light_ticks

        if prep_limit is not None:
            self.advance(spent, prep_limit)
        else:
            self.tick += spent
        return spent

    def enter_boss(
        self,
        rooms: dict[Coord, Room],
        boss: Coord,
        *,
        prep_limit: int | None = None,
    ) -> int:
        if self.coord.manhattan(boss) != 1:
            raise MovementError("must be adjacent to boss to enter")
        boss_room = rooms[boss]
        boss_room.discovered = True
        self.coord = boss
        self.entered_boss = True
        spent = 1
        if prep_limit is not None:
            self.advance(spent, prep_limit)
        else:
            self.tick += spent
        return spent
