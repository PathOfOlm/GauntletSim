"""Phase 3 preparation simulation: gather, fight drops, craft, timer."""

from __future__ import annotations

from dataclasses import dataclass, field

from gauntletsim.config import AppConfig
from gauntletsim.crafting import ArmourSlot, CraftingBench, WeaponStyle
from gauntletsim.demibosses import PrepEncounters
from gauntletsim.dungeon import DungeonState
from gauntletsim.game_rules import GameRules
from gauntletsim.inventory import ItemId
from gauntletsim.player import PlayerState
from gauntletsim.resources import GatherSystem
from gauntletsim.room import Coord, NodeType, RoomKind
from gauntletsim.visualization import render_ascii


@dataclass
class PrepSim:
    rules: GameRules
    config: AppConfig
    dungeon: DungeonState
    gather: GatherSystem
    encounters: PrepEncounters
    crafting: CraftingBench
    prep_limit: int
    log: list[str] = field(default_factory=list)

    @classmethod
    def create(cls, rules: GameRules, config: AppConfig) -> PrepSim:
        dungeon = DungeonState.generate(rules, config.sim.master_seed)
        # Replace bare player with account-backed vitals (keep start coord).
        start = dungeon.layout.start
        dungeon.player = PlayerState.from_account(start, config.account)
        dungeon.room(start).discovered = True
        gather = GatherSystem.create(rules, dungeon.rooms, config.sim.master_seed)
        encounters = PrepEncounters.create(rules, config.sim.master_seed)
        crafting = CraftingBench(rules)
        limit = (
            config.sim.prep_ticks
            if config.sim.prep_ticks is not None
            else rules.prep_ticks
        )
        return cls(
            rules=rules,
            config=config,
            dungeon=dungeon,
            gather=gather,
            encounters=encounters,
            crafting=crafting,
            prep_limit=limit,
        )

    @property
    def player(self) -> PlayerState:
        return self.dungeon.player

    def _spend(self, ticks: int, note: str = "") -> None:
        self.player.advance(ticks, self.prep_limit)
        if note:
            self.log.append(f"t={self.player.tick}: {note}")

    def remaining(self) -> int:
        return self.player.remaining_prep_ticks(self.prep_limit)

    def timed_out(self) -> bool:
        return self.player.timed_out or self.player.tick >= self.prep_limit

    def go_to(self, goal: Coord, max_steps: int = 80) -> int:
        steps = 0
        while self.player.coord != goal and steps < max_steps and not self.timed_out():
            before = self.player.tick
            self.dungeon.step_toward(goal)
            # step_toward uses player.move_or_light without prep_limit — sync timeout
            if self.player.tick >= self.prep_limit:
                self.player.timed_out = True
            spent = self.player.tick - before
            if spent == 0:
                # Manual: dungeon.step_toward already advanced tick via player
                pass
            steps += 1
        return steps

    def clear_here(self) -> dict[str, int]:
        room = self.dungeon.room(self.player.coord)
        ticks, drops = self.encounters.clear_room(room, self.player.inventory)
        if ticks:
            self._spend(ticks, f"clear {room.mob_tier.value} {drops}")
        return drops

    def gather_here(self, prefer: NodeType | None = None) -> dict:
        if self.timed_out():
            return {}
        ticks, gained = self.gather.gather_one(
            self.player.coord, self.player.inventory, prefer=prefer
        )
        self._spend(ticks, f"gather { {k.value: v for k, v in gained.items()} }")
        rr = self.gather.room_resources[self.player.coord]
        if rr.all_depleted():
            self.dungeon.room(self.player.coord).searched_depleted = True
        return gained

    def return_to_start(self) -> None:
        self.go_to(self.dungeon.layout.start)

    def at_hub(self) -> bool:
        return self.dungeon.room(self.player.coord).kind == RoomKind.START

    def demo_prep_slice(self) -> None:
        """
        Deterministic demo path for a seed:
        explore fish room → gather fish → clear nearby weak if any →
        hit one demi if reachable → hub craft basic bow + cook + egniol attempt.
        """
        fish = self.dungeon.layout.fish_room
        self.go_to(fish)
        self.clear_here()
        # Gather all fish spots in room
        while (
            not self.timed_out()
            and self.gather.room_resources[fish].has_gatherable(NodeType.FISH)
        ):
            try:
                self.gather_here(NodeType.FISH)
            except Exception as exc:  # noqa: BLE001 — demo stops on inventory full
                self.log.append(f"gather stop: {exc}")
                break

        # Try nearest demi
        demis = list(self.dungeon.layout.demi_rooms)
        demis.sort(key=lambda c: c.manhattan(self.player.coord))
        if demis and not self.timed_out():
            target = demis[0]
            self.go_to(target)
            self.clear_here()

        # Gather some ore/bark/linum near start for T1 armour if time
        self.return_to_start()
        for coord, room in self.dungeon.rooms.items():
            if room.kind != RoomKind.RESOURCE:
                continue
            if room.nodes.get(NodeType.ORE, 0) <= 0:
                continue
            if self.timed_out():
                break
            self.go_to(coord)
            self.clear_here()
            for ntype in (NodeType.ORE, NodeType.PHREN, NodeType.LINUM, NodeType.GRYM):
                while (
                    not self.timed_out()
                    and self.gather.room_resources[coord].has_gatherable(ntype)
                ):
                    try:
                        self.gather_here(ntype)
                    except Exception:
                        break
            if self.player.inventory.count(ItemId.ORE) >= 1:
                break

        self.return_to_start()
        if self.timed_out():
            self.log.append("prep timed out before crafting")
            return

        inv = self.player.inventory
        # Craft path
        if inv.has(ItemId.WEAPON_FRAME):
            self._spend(
                self.crafting.craft_basic_weapon(inv, WeaponStyle.BOW),
                "craft bow basic",
            )
        if inv.has(ItemId.BOW_BASIC) and inv.count(ItemId.SHARDS) >= 50:
            self._spend(
                self.crafting.upgrade_weapon_attuned(inv, WeaponStyle.BOW),
                "craft bow attuned",
            )
        if (
            inv.has(ItemId.BOW_ATTUNED)
            and inv.has(ItemId.BOWSTRING)
            and not self.timed_out()
        ):
            self._spend(
                self.crafting.upgrade_weapon_perfected(inv, WeaponStyle.BOW),
                "craft bow perfected",
            )
        if (
            inv.has(ItemId.ORE)
            and inv.has(ItemId.BARK)
            and inv.has(ItemId.LINUM)
            and inv.count(ItemId.SHARDS) >= 50
        ):
            self._spend(
                self.crafting.craft_armour_basic(inv, ArmourSlot.HELM),
                "craft helm basic",
            )

        cooking = self.config.account.cooking
        while inv.has(ItemId.RAW_PADDLEFISH) and not self.timed_out():
            ticks, ok = self.crafting.cook_paddlefish(inv, cooking)
            self._spend(ticks, "cook paddlefish" if ok else "burn paddlefish")

        if (
            inv.has(ItemId.GRYM_LEAF)
            and inv.count(ItemId.SHARDS) >= 20
            and not self.timed_out()
        ):
            self._spend(self.crafting.craft_vial(inv), "craft vial")
            self._spend(self.crafting.fill_vial(inv), "fill vial")
            self._spend(self.crafting.make_grym_unf(inv), "grym unf")
            self._spend(self.crafting.make_egniol(inv), "egniol")

        self.player.equipment.sync_from_inventory(inv)
        self.log.append(
            f"done tick={self.player.tick}/{self.prep_limit} "
            f"timeout={self.timed_out()} inv={inv.summary()}"
        )

    def status_lines(self) -> list[str]:
        p = self.player
        return [
            "GauntletSim — Phase 3 prep",
            f"master_seed: {self.dungeon.layout.master_seed}",
            f"tick: {p.tick}/{self.prep_limit} remaining={self.remaining()}",
            f"timeout: {self.timed_out()} entered_boss: {p.entered_boss}",
            f"hp: {p.hitpoints}/{p.hitpoints_max} prayer: {p.prayer}/{p.prayer_max}",
            f"pos: ({p.coord.x},{p.coord.y})",
            f"equipment: helm={p.equipment.helm_tier} body={p.equipment.body_tier} "
            f"legs={p.equipment.legs_tier} bow={p.equipment.has_bow} "
            f"staff={p.equipment.has_staff} halb={p.equipment.has_halberd}",
            f"frames={self.encounters.state.frames_dropped} "
            f"demi_kills={self.encounters.state.demi_kills} "
            f"t3={sorted(x.value for x in self.encounters.state.t3_parts)}",
            f"inventory_slots: {p.inventory.slots_used()}/{p.inventory.capacity}",
            f"inventory: {p.inventory.summary()}",
        ]

    def ascii_map(self) -> str:
        return render_ascii(self.dungeon)
