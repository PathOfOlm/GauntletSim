"""Resource nodes, gathering, and depletion (Phase 3)."""

from __future__ import annotations

from dataclasses import dataclass, field
import random

from gauntletsim.game_rules import GameRules
from gauntletsim.inventory import Inventory, InventoryError, ItemId
from gauntletsim.rng import make_stream
from gauntletsim.room import Coord, NodeType, Room


NODE_TO_ITEM = {
    NodeType.ORE: ItemId.ORE,
    NodeType.LINUM: ItemId.LINUM,
    NodeType.PHREN: ItemId.BARK,
    NodeType.GRYM: ItemId.GRYM_LEAF,
    NodeType.FISH: ItemId.RAW_PADDLEFISH,
}

NODE_YIELD_KEYS = {
    NodeType.ORE: "ore_deposit",
    NodeType.LINUM: "linum_tirinum",
    NodeType.PHREN: "phren_roots",
    NodeType.GRYM: "grym_root",
    NodeType.FISH: "fishing_spot",
}


@dataclass
class ResourceNode:
    node_type: NodeType
    remaining: int
    # Local tile inside the room (blocked for standing-on; gather from adjacent).
    local: tuple[int, int] | None = None

    @property
    def depleted(self) -> bool:
        return self.remaining <= 0


def _place_node_locals(count: int, room_size: int = 16) -> list[tuple[int, int]]:
    """Deterministic interior placements away from perimeter (assumption layout)."""
    # Ring of candidate spots inside the walkable interior.
    spots = [
        (3, 3),
        (room_size - 4, 3),
        (3, room_size - 4),
        (room_size - 4, room_size - 4),
        (room_size // 2, 3),
        (room_size // 2, room_size - 4),
        (3, room_size // 2),
        (room_size - 4, room_size // 2),
        (5, 5),
        (room_size - 6, 5),
        (5, room_size - 6),
        (room_size - 6, room_size - 6),
    ]
    out: list[tuple[int, int]] = []
    for i in range(count):
        out.append(spots[i % len(spots)])
    return out


@dataclass
class RoomResources:
    """Mutable gather state for one room."""

    nodes: list[ResourceNode] = field(default_factory=list)

    @classmethod
    def from_room_layout(cls, room: Room, yields: dict[str, int]) -> RoomResources:
        instances: list[ResourceNode] = []
        # Flatten in stable NodeType order for reproducible local placement.
        planned: list[tuple[NodeType, int]] = []
        for ntype in NodeType:
            count = int(room.nodes.get(ntype, 0))
            per = int(yields[NODE_YIELD_KEYS[ntype]])
            for _ in range(count):
                planned.append((ntype, per))
        locals_ = _place_node_locals(len(planned))
        for (ntype, per), loc in zip(planned, locals_, strict=True):
            instances.append(ResourceNode(node_type=ntype, remaining=per, local=loc))
        return cls(nodes=instances)

    def next_gatherable(self, prefer: NodeType | None = None) -> ResourceNode | None:
        for n in self.nodes:
            if n.depleted:
                continue
            if prefer is None or n.node_type == prefer:
                return n
        return None

    def has_gatherable(self, prefer: NodeType | None = None) -> bool:
        for n in self.nodes:
            if n.depleted:
                continue
            if prefer is None or n.node_type == prefer:
                return True
        return False

    def all_depleted(self) -> bool:
        return all(n.depleted for n in self.nodes) if self.nodes else True


class GatherError(ValueError):
    pass


@dataclass
class GatherSystem:
    rules: GameRules
    room_resources: dict[Coord, RoomResources]
    rng: random.Random
    interval_ticks: int
    shard_chance_num: int
    shard_chance_den: int
    shard_qty_min: int
    shard_qty_max: int
    non_ore_fish_success: float

    @classmethod
    def create(
        cls,
        rules: GameRules,
        rooms: dict[Coord, Room],
        master_seed: int,
    ) -> GatherSystem:
        yields = dict(rules.get("resources", "node_yields"))
        room_resources = {
            c: RoomResources.from_room_layout(r, yields)
            for c, r in rooms.items()
        }
        try:
            success = float(
                rules.assumption_default(
                    "resources.gather_success_probability_non_ore_fish"
                )
            )
        except KeyError:
            success = 1.0
        return cls(
            rules=rules,
            room_resources=room_resources,
            rng=make_stream(master_seed, "gather"),
            interval_ticks=int(rules.get("resources", "gather_interval_ticks")),
            shard_chance_num=int(rules.get("resources", "gather_shard_chance_numerator")),
            shard_chance_den=int(
                rules.get("resources", "gather_shard_chance_denominator")
            ),
            shard_qty_min=int(rules.get("resources", "gather_shard_quantity_min")),
            shard_qty_max=int(rules.get("resources", "gather_shard_quantity_max")),
            non_ore_fish_success=success,
        )

    def gather_one(
        self,
        coord: Coord,
        inventory: Inventory,
        *,
        prefer: NodeType | None = None,
    ) -> tuple[int, dict[ItemId, int]]:
        """
        One gather roll at `coord`. Returns (ticks_spent, items_gained).
        Respects inventory capacity; raises if no space for the primary item.
        Caller must path to the node tile (or adjacency) before invoking.
        """
        rr = self.room_resources.get(coord)
        if rr is None or not rr.has_gatherable(prefer):
            raise GatherError("nothing to gather here")

        node = rr.next_gatherable(prefer)
        if node is None:
            raise GatherError("nothing to gather here")
        item = NODE_TO_ITEM[node.node_type]

        # Success: ore/fish Always; others use assumption.
        if node.node_type in (NodeType.ORE, NodeType.FISH):
            success = True
        else:
            success = self.rng.random() < self.non_ore_fish_success

        gained: dict[ItemId, int] = {}
        if success:
            if not inventory.can_add(item, 1):
                raise InventoryError(f"no space for {item.value}")
            inventory.add(item, 1)
            gained[item] = 1
            node.remaining -= 1
            # Shard roll on successful gather
            if self.rng.random() < (
                self.shard_chance_num / self.shard_chance_den
            ):
                qty = self.rng.randint(self.shard_qty_min, self.shard_qty_max)
                if inventory.can_add(ItemId.SHARDS, qty):
                    inventory.add(ItemId.SHARDS, qty)
                    gained[ItemId.SHARDS] = qty

        if rr.all_depleted():
            # Caller may mark room searched_depleted.
            pass
        return self.interval_ticks, gained

    def gather_all_of_type(
        self,
        coord: Coord,
        inventory: Inventory,
        node_type: NodeType,
        *,
        max_rolls: int = 64,
    ) -> tuple[int, dict[ItemId, int]]:
        total_ticks = 0
        totals: dict[ItemId, int] = {}
        rolls = 0
        while rolls < max_rolls and self.room_resources[coord].has_gatherable(
            node_type
        ):
            try:
                ticks, gained = self.gather_one(coord, inventory, prefer=node_type)
            except InventoryError:
                break
            total_ticks += ticks
            for k, v in gained.items():
                totals[k] = totals.get(k, 0) + v
            rolls += 1
        return total_ticks, totals
