"""Named prep scenarios / loadout goals (Phase 3.5)."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, pi

from gauntletsim.config import AppConfig, SimConfig
from gauntletsim.crafting import ArmourSlot, WeaponStyle
from gauntletsim.fog import FogKnowledge, KnownRoom, LayoutFogProxy
from gauntletsim.game_rules import GameRules
from gauntletsim.hub import HubError, HubStation
from gauntletsim.inventory import ItemId
from gauntletsim.map_generator import CARDINAL_OUTER
from gauntletsim.prep import PrepSim
from gauntletsim.room import Coord, DemiType, NodeType, RoomKind

LOADOUT_T3_DUAL_T2ARM = "t3-dual-t2arm-3pot-21food"

# Resource targets for T3 bow+staff, T2 armour set, 3 egniol, 21 food.
TARGET_ORE = 7
TARGET_BARK = 7
TARGET_LINUM = 7
TARGET_GRYM = 3
TARGET_FISH = 21
# Weapons 100 + armour 350 + potions 60
TARGET_SHARDS_SOFT = 520


@dataclass(frozen=True)
class LoadoutGoal:
    id: str
    bow_tier: int = 3
    staff_tier: int = 3
    helm_tier: int = 2
    body_tier: int = 2
    legs_tier: int = 2
    egniol: int = 3
    paddlefish: int = 21


GOAL_T3_DUAL = LoadoutGoal(id=LOADOUT_T3_DUAL_T2ARM)


def loadout_met(sim: PrepSim, goal: LoadoutGoal = GOAL_T3_DUAL) -> bool:
    inv = sim.player.inventory
    eq = sim.player.equipment
    eq.sync_from_inventory(inv)
    return (
        eq.has_bow >= goal.bow_tier
        and eq.has_staff >= goal.staff_tier
        and eq.helm_tier >= goal.helm_tier
        and eq.body_tier >= goal.body_tier
        and eq.legs_tier >= goal.legs_tier
        and inv.count(ItemId.EGNIOL_3) >= goal.egniol
        and inv.count(ItemId.PADDLEFISH) >= goal.paddlefish
        and not sim.timed_out()
    )


def loadout_gaps(sim: PrepSim, goal: LoadoutGoal = GOAL_T3_DUAL) -> list[str]:
    inv = sim.player.inventory
    eq = sim.player.equipment
    eq.sync_from_inventory(inv)
    gaps: list[str] = []
    if eq.has_bow < goal.bow_tier:
        gaps.append(f"bow_tier={eq.has_bow}<{goal.bow_tier}")
    if eq.has_staff < goal.staff_tier:
        gaps.append(f"staff_tier={eq.has_staff}<{goal.staff_tier}")
    if eq.helm_tier < goal.helm_tier:
        gaps.append(f"helm={eq.helm_tier}<{goal.helm_tier}")
    if eq.body_tier < goal.body_tier:
        gaps.append(f"body={eq.body_tier}<{goal.body_tier}")
    if eq.legs_tier < goal.legs_tier:
        gaps.append(f"legs={eq.legs_tier}<{goal.legs_tier}")
    if inv.count(ItemId.EGNIOL_3) < goal.egniol:
        gaps.append(f"egniol={inv.count(ItemId.EGNIOL_3)}<{goal.egniol}")
    if inv.count(ItemId.PADDLEFISH) < goal.paddlefish:
        gaps.append(f"fish={inv.count(ItemId.PADDLEFISH)}<{goal.paddlefish}")
    if sim.timed_out():
        gaps.append("timed_out")
    return gaps


class LoadoutScenario:
    """Tick-accurate prep agent aiming for a named loadout (fog-of-war only)."""

    def __init__(
        self,
        sim: PrepSim,
        goal: LoadoutGoal = GOAL_T3_DUAL,
        *,
        enforce_fog: bool = True,
    ) -> None:
        self.sim = sim
        self.goal = goal
        self.fog = FogKnowledge(sim)
        # Capture start from spawn (already discovered) — do not read layout.start later.
        self._start = self.fog.start()
        self._mid_crafted = False
        self.hub_returns = 0
        self.noted_fish: list[Coord] = []
        self.noted_grym: list[Coord] = []
        self.noted_demis: list[Coord] = []
        boss = self.fog.boss
        start = self._start
        cards = list(CARDINAL_OUTER.values())
        base = atan2(start.y - boss.y, start.x - boss.x)
        cards.sort(key=lambda c: (atan2(c.y - boss.y, c.x - boss.x) - base) % (2 * pi))
        self.c_path_order = cards
        if enforce_fog:
            # Block omniscient peeks for the rest of this agent run.
            sim.dungeon.layout = LayoutFogProxy(sim.dungeon.layout)  # type: ignore[assignment]

    @property
    def inv(self):
        return self.sim.player.inventory

    def _ensure_space(self, need: int = 1) -> None:
        if self.inv.free_slots() >= need:
            return
        # Never drop frames / T3 parts / last teleport — drop tools/fish/mats first.
        for item in (
            ItemId.SPIKE,
            ItemId.AXE,
            ItemId.PICKAXE,
            ItemId.HARPOON,
            ItemId.RAW_PADDLEFISH,
            ItemId.ORE,
            ItemId.BARK,
            ItemId.LINUM,
        ):
            if self.inv.free_slots() >= need:
                return
            if not self.inv.has(item):
                continue
            if item == ItemId.RAW_PADDLEFISH and self.inv.count(item) <= 14:
                continue
            self.inv.drop(item)
            self.sim.log.append(f"t={self.sim.player.tick}: drop {item.value}")

    def _return_hub(self) -> None:
        if self.sim.at_hub():
            return
        if self.inv.has(ItemId.TELEPORT_CRYSTAL):
            self.sim.teleport_to_start()
        else:
            self.sim.go_to(self._start)
        self.hub_returns += 1

    def _note_room(self, known: KnownRoom) -> None:
        if known.gather_remaining.get(NodeType.FISH, 0) or known.nodes.get(NodeType.FISH, 0):
            if known.coord not in self.noted_fish:
                self.noted_fish.append(known.coord)
        if known.gather_remaining.get(NodeType.GRYM, 0):
            if known.coord not in self.noted_grym:
                self.noted_grym.append(known.coord)
        if known.is_demi and known.coord not in self.noted_demis:
            self.noted_demis.append(known.coord)

    def _has_frame_or_weapon(self) -> bool:
        eq = self.sim.player.equipment
        eq.sync_from_inventory(self.inv)
        return (
            self.inv.has(ItemId.WEAPON_FRAME)
            or eq.has_bow > 0
            or eq.has_staff > 0
        )

    def _sip_stamina(self) -> None:
        have = self.inv.count(ItemId.EGNIOL_3)
        if have > self.goal.egniol:
            self.sim.sip_egniol_if_low_energy(threshold_units=2500)
        elif have >= 1 and self.sim.player.run_energy < 800:
            self.sim.sip_egniol_if_low_energy(threshold_units=800)

    def _field_potions(self) -> None:
        if self.sim.timed_out():
            return
        want = self.goal.egniol
        while (
            self.inv.count(ItemId.EGNIOL_3) < want
            and not self.sim.timed_out()
            and self.inv.count(ItemId.GRYM_LEAF) >= 1
            and self.inv.count(ItemId.SHARDS) >= 20
            and self.inv.has(ItemId.PESTLE)
        ):
            if not self.inv.has(ItemId.WATER_VIAL):
                if not self.inv.has(ItemId.VIAL):
                    break
                try:
                    self.sim.fill_vial_at_fish()
                except HubError:
                    break
            if not self.inv.has(ItemId.WATER_VIAL):
                break
            self._ensure_space(1)
            try:
                self.sim.craft_egniol_field()
            except Exception as exc:  # noqa: BLE001
                self.sim.log.append(f"field egniol stop: {exc}")
                break

    def _crush_spare_parts(self) -> None:
        if not self.inv.has(ItemId.PESTLE):
            return
        if (
            self.inv.has(ItemId.SPIKE)
            and self.inv.has(ItemId.ORB)
            and self.inv.has(ItemId.BOWSTRING)
        ):
            try:
                self.sim.crush_spare_t3(ItemId.SPIKE)
            except Exception as exc:  # noqa: BLE001
                self.sim.log.append(f"crush stop: {exc}")

    def _maybe_drop_tools(self) -> None:
        mapping = (
            (ItemId.PICKAXE, ItemId.ORE, TARGET_ORE),
            (ItemId.AXE, ItemId.BARK, TARGET_BARK),
            (ItemId.HARPOON, ItemId.RAW_PADDLEFISH, TARGET_FISH),
        )
        for tool, item, target in mapping:
            if self.inv.has(tool) and self.inv.count(item) >= target:
                self.inv.drop(tool)
                self.sim.log.append(
                    f"t={self.sim.player.tick}: drop {tool.value} (resource done)"
                )

    def _can_mid_hub(self) -> bool:
        return (
            not self._mid_crafted
            and self._has_frame_or_weapon()
            and self.inv.count(ItemId.SHARDS) >= 90
            and self.sim.player.tick <= 200
            and (
                self.inv.has(ItemId.TELEPORT_CRYSTAL)
                or self.sim.at_hub()
            )
        )

    def phase_mid_hub_craft(self) -> None:
        """G01: mid-prep T2 weapon + vials + replacement teleport."""
        if self.sim.timed_out():
            return
        sim = self.sim
        inv = self.inv
        self._mid_crafted = True
        sim.log.append(f"mid-hub craft tick={sim.player.tick}")
        prefer = WeaponStyle.BOW
        for known in self.fog.known_rooms():
            if known.demi_type == DemiType.DRAGON:
                prefer = WeaponStyle.STAFF
                break
            if known.demi_type == DemiType.DARK_BEAST:
                prefer = WeaponStyle.BOW
                break
        basic = {
            WeaponStyle.BOW: ItemId.BOW_BASIC,
            WeaponStyle.STAFF: ItemId.STAFF_BASIC,
        }[prefer]
        attuned = {
            WeaponStyle.BOW: ItemId.BOW_ATTUNED,
            WeaponStyle.STAFF: ItemId.STAFF_ATTUNED,
        }[prefer]
        perfected = {
            WeaponStyle.BOW: ItemId.BOW_PERFECTED,
            WeaponStyle.STAFF: ItemId.STAFF_PERFECTED,
        }[prefer]
        if not inv.has(attuned) and not inv.has(perfected):
            if not inv.has(basic) and inv.has(ItemId.WEAPON_FRAME):
                try:
                    sim.hub_craft_basic_weapon(prefer)
                except Exception as exc:  # noqa: BLE001
                    sim.log.append(f"mid weapon basic fail: {exc}")
            if inv.has(basic) and inv.count(ItemId.SHARDS) >= 50:
                try:
                    sim.hub_upgrade_weapon_attuned(prefer)
                except Exception as exc:  # noqa: BLE001
                    sim.log.append(f"mid weapon attuned fail: {exc}")
        for _ in range(3):
            if inv.count(ItemId.VIAL) + inv.count(ItemId.WATER_VIAL) + inv.count(
                ItemId.EGNIOL_3
            ) >= 3:
                break
            if inv.count(ItemId.SHARDS) < 10:
                break
            try:
                sim.hub_craft_vial()
                sim.hub_fill_vial()
            except HubError as exc:
                sim.log.append(f"mid vial fail: {exc}")
                break
        if not inv.has(ItemId.TELEPORT_CRYSTAL):
            try:
                cost = int(sim.rules.get("crafting", "teleport_crystal_shards"))
                if inv.count(ItemId.SHARDS) >= cost:
                    sim.hub_craft_teleport_crystal()
            except Exception as exc:  # noqa: BLE001
                sim.log.append(f"mid tele fail: {exc}")
        # Drop surplus mats only above armour targets.
        for mat, cap in (
            (ItemId.ORE, TARGET_ORE),
            (ItemId.BARK, TARGET_BARK),
            (ItemId.LINUM, TARGET_LINUM),
        ):
            while inv.count(mat) > cap:
                inv.drop(mat)
        while inv.has(ItemId.SPIKE):
            inv.drop(ItemId.SPIKE)
        sim.player.equipment.sync_from_inventory(inv)
        sim.log.append(
            f"mid-hub end tick={sim.player.tick} inv={inv.summary()} "
            f"eq_bow={sim.player.equipment.has_bow} "
            f"eq_staff={sim.player.equipment.has_staff} multi_trip=1"
        )

    def _visit_and_clear(self, coord: Coord) -> None:
        if self.sim.timed_out():
            return
        self.sim.begin_room_visit_overlap()
        self.sim.go_to(coord)
        if self.sim.timed_out():
            return
        if self.fog.is_discovered(coord):
            known = self.fog.observe(coord)
            if known.is_demi:
                self.sim.player.protect_prayer = "magic"
                self.sim.log.append(
                    f"t={self.sim.player.tick}: protect_magic before demi enter"
                )
            self._ensure_space(3 if known.is_demi else 2)
        self.sim.clear_here()

    def _gather_type(self, coord: Coord, ntype: NodeType, until: int, item: ItemId) -> None:
        # Only gather in rooms we have discovered (go_to lights them).
        if not self.fog.is_discovered(coord):
            return
        while (
            not self.sim.timed_out()
            and self.inv.count(item) < until
            and self.sim.gather.room_resources[coord].has_gatherable(ntype)
        ):
            self._ensure_space(1)
            try:
                self.sim.gather_here(ntype)
            except Exception as exc:  # noqa: BLE001
                self.sim.log.append(f"gather stop: {exc}")
                break

    def _mats_ok(self) -> bool:
        return (
            self.inv.count(ItemId.ORE) >= TARGET_ORE
            and self.inv.count(ItemId.BARK) >= TARGET_BARK
            and self.inv.count(ItemId.LINUM) >= TARGET_LINUM
        )

    def _parts_ok(self) -> bool:
        return self.inv.has(ItemId.BOWSTRING) and self.inv.has(ItemId.ORB)

    def _frames_ok(self) -> bool:
        # Frames may already be spent on weapons (count styles started, not tiers).
        eq = self.sim.player.equipment
        eq.sync_from_inventory(self.inv)
        styles_started = sum(1 for t in (eq.has_bow, eq.has_staff) if t > 0)
        return self.inv.count(ItemId.WEAPON_FRAME) + styles_started >= 2

    def _shards_ok(self) -> bool:
        return self.inv.count(ItemId.SHARDS) >= TARGET_SHARDS_SOFT

    def _fish_ok(self) -> bool:
        return (
            self.inv.count(ItemId.RAW_PADDLEFISH)
            + self.inv.count(ItemId.PADDLEFISH)
            >= TARGET_FISH
        )

    def _grym_ok(self) -> bool:
        made = self.inv.count(ItemId.EGNIOL_3) + self.inv.count(ItemId.GRYM_POTION_UNF)
        return self.inv.count(ItemId.GRYM_LEAF) + made >= TARGET_GRYM

    def _gather_ready(self) -> bool:
        return (
            self._mats_ok()
            and self._grym_ok()
            and self._fish_ok()
            and self._parts_ok()
            and self._frames_ok()
            and self._shards_ok()
        )

    def _deficits(self) -> dict[str, int]:
        made = self.inv.count(ItemId.EGNIOL_3) + self.inv.count(ItemId.GRYM_POTION_UNF)
        fish_have = self.inv.count(ItemId.RAW_PADDLEFISH) + self.inv.count(
            ItemId.PADDLEFISH
        )
        return {
            "ore": max(0, TARGET_ORE - self.inv.count(ItemId.ORE)),
            "bark": max(0, TARGET_BARK - self.inv.count(ItemId.BARK)),
            "linum": max(0, TARGET_LINUM - self.inv.count(ItemId.LINUM)),
            "grym": max(0, TARGET_GRYM - self.inv.count(ItemId.GRYM_LEAF) - made),
            "fish": max(0, TARGET_FISH - fish_have),
        }

    def _gather_needed_here(self, coord: Coord) -> None:
        if not self.fog.is_discovered(coord):
            return
        known = self.fog.observe(coord)
        d = self._deficits()
        if d["ore"] and known.gather_remaining.get(NodeType.ORE, 0):
            self._gather_type(coord, NodeType.ORE, TARGET_ORE, ItemId.ORE)
        if d["bark"] and known.gather_remaining.get(NodeType.PHREN, 0):
            self._gather_type(coord, NodeType.PHREN, TARGET_BARK, ItemId.BARK)
        if d["linum"] and known.gather_remaining.get(NodeType.LINUM, 0):
            self._gather_type(coord, NodeType.LINUM, TARGET_LINUM, ItemId.LINUM)
        if d["grym"] and known.gather_remaining.get(NodeType.GRYM, 0):
            self._gather_type(coord, NodeType.GRYM, TARGET_GRYM, ItemId.GRYM_LEAF)
        if d["fish"] and known.gather_remaining.get(NodeType.FISH, 0):
            until = TARGET_FISH - self.inv.count(ItemId.PADDLEFISH)
            self._gather_type(
                coord, NodeType.FISH, until, ItemId.RAW_PADDLEFISH
            )
            self._field_potions()

    def _react_in_room(self, coord: Coord) -> None:
        """After lighting a room: clear/gather based on observed contents only."""
        if self.sim.timed_out() or not self.fog.is_discovered(coord):
            return
        self.sim.begin_room_visit_overlap()
        known = self.fog.observe(coord)
        self._note_room(known)
        need_parts = not self._parts_ok()
        need_frames = not self._frames_ok()
        need_shards = not self._shards_ok()
        # Prefer clearing demis when hunting T3 parts / frames.
        if known.is_demi and not known.cleared and (need_parts or need_frames or need_shards):
            self.sim.player.protect_prayer = "magic"
            self.sim.log.append(
                f"t={self.sim.player.tick}: protect_magic before demi enter"
            )
            self._ensure_space(3)
            self.sim.clear_here()
            known = self.fog.observe(coord)
            self._note_room(known)
        elif known.has_combat and (need_frames or need_shards):
            self._ensure_space(2)
            self.sim.clear_here()
            known = self.fog.observe(coord)
            self._note_room(known)
        if known.supply_for(self._deficits()) > 0:
            self._gather_needed_here(coord)
        self.sim.apply_fight_gather_overlap()
        self._field_potions()
        self._crush_spare_parts()
        self._sip_stamina()
        self._maybe_drop_tools()

    def _pick_known_work(self) -> Coord | None:
        """Choose a discovered room that still helps deficits / combat needs."""
        here = self.sim.player.coord
        deficits = self._deficits()
        candidates: list[tuple[tuple, Coord]] = []

        for known in self.fog.known_rooms():
            if known.kind == RoomKind.START:
                continue
            supply = known.supply_for(deficits)
            want_demi = (
                known.is_demi
                and not known.cleared
                and (not self._parts_ok() or not self._frames_ok())
            )
            want_combat = (
                known.has_combat
                and not known.is_demi
                and (not self._frames_ok() or not self._shards_ok())
            )
            if supply <= 0 and not want_demi and not want_combat:
                continue
            # Priority: demi parts → supply → other combat; then distance.
            demi_rank = 0 if want_demi else 1
            # Prefer dragon/dark_beast once seen (known demi_type).
            type_rank = 0
            if known.demi_type in (DemiType.DRAGON, DemiType.DARK_BEAST):
                type_rank = -1
            elif known.demi_type is not None:
                type_rank = 0
            supply_rank = -supply
            combat_rank = 0 if want_combat else 1
            dist = known.coord.manhattan(here)
            candidates.append(
                ((demi_rank, type_rank, supply_rank, combat_rank, dist), known.coord)
            )
        if not candidates:
            return None
        candidates.sort(key=lambda t: t[0])
        return candidates[0][1]

    def _pick_frontier(self) -> Coord | None:
        """C-path / cardinal-biased fog expansion (G02)."""
        frontier = self.fog.frontier()
        if not frontier:
            return None
        here = self.sim.player.coord
        boss = self.fog.boss
        next_card = next(
            (c for c in self.c_path_order if not self.fog.is_discovered(c)), None
        )

        def key(c: Coord) -> tuple:
            # Corrupted prior: fish room is adjacent to boss — explore those first
            # when still needing fish (public topology, not a layout peek).
            boss_adj = 0 if (not self._fish_ok() and c.manhattan(boss) == 1) else 1
            card_dist = c.manhattan(next_card) if next_card is not None else 99
            outer = 0 if (c.x in (0, 6) or c.y in (0, 6)) else 1
            # Early: boss ring; later / post mid-hub: push outer cardinals.
            if self._mid_crafted or self._mats_ok():
                return (outer, card_dist, boss_adj, c.manhattan(here), c.x, c.y)
            return (boss_adj, card_dist, c.manhattan(here), c.x, c.y)

        frontier.sort(key=key)
        return frontier[0]

    def phase_scout_and_gather(self) -> None:
        """Explore fog frontier; optional mid-hub craft; gather from known rooms only."""
        self.sim.log.append(
            f"scout start c_path={[ (c.x, c.y) for c in self.c_path_order ]}"
        )
        max_iters = 120
        for _ in range(max_iters):
            if self.sim.timed_out() or self._gather_ready():
                break
            # G01 multi-trip: early mid-hub when frame+shards ready.
            if self._can_mid_hub():
                self._return_hub()
                self.phase_mid_hub_craft()
                if self.sim.timed_out():
                    break
                continue
            work = self._pick_known_work()
            if work is not None:
                known = self.fog.observe(work)
                need_clear = known.has_combat and (
                    (known.is_demi and (not self._parts_ok() or not self._frames_ok()))
                    or (
                        not known.is_demi
                        and (not self._frames_ok() or not self._shards_ok())
                    )
                )
                self.sim.begin_room_visit_overlap()
                if need_clear:
                    if known.is_demi:
                        self.sim.player.protect_prayer = "magic"
                        self.sim.log.append(
                            f"t={self.sim.player.tick}: protect_magic before demi enter"
                        )
                    self.sim.go_to(work)
                    if self.sim.timed_out():
                        break
                    self._ensure_space(3 if known.is_demi else 2)
                    self.sim.clear_here()
                else:
                    self.sim.go_to(work)
                if self.sim.timed_out():
                    break
                self._gather_needed_here(work)
                self.sim.apply_fight_gather_overlap()
                self._field_potions()
                self._crush_spare_parts()
                self._sip_stamina()
                self._maybe_drop_tools()
                continue

            nxt = self._pick_frontier()
            if nxt is None:
                self.sim.log.append(
                    f"fog stuck deficits={self._deficits()} "
                    f"discovered={len(self.fog.discovered_coords())} "
                    f"parts={self._parts_ok()} frames={self._frames_ok()} "
                    f"shards={self.inv.count(ItemId.SHARDS)}"
                )
                break
            self.sim.go_to(nxt)  # lights the room
            if self.sim.timed_out():
                break
            self._react_in_room(nxt)
        else:
            self.sim.log.append("fog exploration aborted: max_iters")

        self._return_hub()
        self.sim.log.append(
            f"gather phase end tick={self.sim.player.tick} "
            f"ready={self._gather_ready()} deficits={self._deficits()} "
            f"shards={self.inv.count(ItemId.SHARDS)} "
            f"parts_ok={self._parts_ok()} frames_ok={self._frames_ok()} "
            f"discovered={len(self.fog.discovered_coords())} fog=1 "
            f"multi_trip={1 if self._mid_crafted else 0} hub_returns={self.hub_returns}"
        )

    def phase_craft_loadout(self) -> None:
        """Hub crafting: weapons → armour → potions → cook food."""
        if self.sim.timed_out():
            return
        sim = self.sim
        inv = self.inv

        # Drop gathering tools to free slots; keep pestle for egniol.
        for tool in (ItemId.AXE, ItemId.PICKAXE, ItemId.HARPOON, ItemId.TELEPORT_CRYSTAL):
            if inv.has(tool):
                inv.drop(tool)
                sim.log.append(f"t={sim.player.tick}: drop {tool.value} at hub")

        self._crush_spare_parts()

        # Weapons: bow then staff to perfected.
        for style, part in (
            (WeaponStyle.BOW, ItemId.BOWSTRING),
            (WeaponStyle.STAFF, ItemId.ORB),
        ):
            if sim.timed_out():
                return
            basic = {
                WeaponStyle.BOW: ItemId.BOW_BASIC,
                WeaponStyle.STAFF: ItemId.STAFF_BASIC,
            }[style]
            attuned = {
                WeaponStyle.BOW: ItemId.BOW_ATTUNED,
                WeaponStyle.STAFF: ItemId.STAFF_ATTUNED,
            }[style]
            perfected = {
                WeaponStyle.BOW: ItemId.BOW_PERFECTED,
                WeaponStyle.STAFF: ItemId.STAFF_PERFECTED,
            }[style]
            if inv.has(perfected):
                continue
            if not inv.has(basic) and not inv.has(attuned):
                if inv.has(ItemId.WEAPON_FRAME):
                    sim.hub_craft_basic_weapon(style)
            if inv.has(basic) and inv.count(ItemId.SHARDS) >= 50:
                sim.hub_upgrade_weapon_attuned(style)
            if inv.has(attuned) and inv.has(part):
                sim.hub_upgrade_weapon_perfected(style)

        # Armour T1 → T2 for helm, body, legs.
        for slot in (ArmourSlot.HELM, ArmourSlot.BODY, ArmourSlot.LEGS):
            if sim.timed_out():
                return
            basic = {
                ArmourSlot.HELM: ItemId.HELM_BASIC,
                ArmourSlot.BODY: ItemId.BODY_BASIC,
                ArmourSlot.LEGS: ItemId.LEGS_BASIC,
            }[slot]
            attuned = {
                ArmourSlot.HELM: ItemId.HELM_ATTUNED,
                ArmourSlot.BODY: ItemId.BODY_ATTUNED,
                ArmourSlot.LEGS: ItemId.LEGS_ATTUNED,
            }[slot]
            if inv.has(attuned):
                continue
            if not inv.has(basic):
                if (
                    inv.count(ItemId.ORE) >= 1
                    and inv.count(ItemId.BARK) >= 1
                    and inv.count(ItemId.LINUM) >= 1
                    and inv.count(ItemId.SHARDS) >= 50
                ):
                    sim.hub_craft_armour_basic(slot)
            if inv.has(basic):
                try:
                    sim.hub_upgrade_armour_attuned(slot)
                except Exception as exc:  # noqa: BLE001
                    sim.log.append(f"armour upgrade fail {slot.value}: {exc}")

        # Drop leftover mats; keep frames/parts until weapons are done.
        for junk in (ItemId.ORE, ItemId.BARK, ItemId.LINUM, ItemId.SPIKE):
            if inv.has(junk):
                inv.drop(junk)
        eq = sim.player.equipment
        eq.sync_from_inventory(inv)
        if eq.has_bow > 0 and eq.has_staff > 0 and inv.has(ItemId.WEAPON_FRAME):
            inv.drop(ItemId.WEAPON_FRAME)
        if eq.has_bow >= 3 and inv.has(ItemId.BOWSTRING):
            inv.drop(ItemId.BOWSTRING)
        if eq.has_staff >= 3 and inv.has(ItemId.ORB):
            inv.drop(ItemId.ORB)

        # 3 egniol potions.
        while inv.count(ItemId.EGNIOL_3) < self.goal.egniol and not sim.timed_out():
            if inv.count(ItemId.GRYM_LEAF) < 1 or inv.count(ItemId.SHARDS) < 20:
                sim.log.append("egniol stop: missing grym/shards")
                break
            if not inv.has(ItemId.PESTLE):
                sim.log.append("egniol stop: no pestle")
                break
            self._ensure_space(1)
            try:
                sim.hub_craft_vial()
                sim.hub_fill_vial()
                sim._spend(sim.crafting.make_grym_unf(inv), "craft", "grym unf")
                sim._spend(sim.crafting.make_egniol(inv), "craft", "egniol")
            except HubError as exc:
                sim.log.append(f"egniol hub retry: {exc}")
                sim.approach_station(HubStation.SINGING_BOWL)
                try:
                    sim.hub_craft_vial()
                    sim.hub_fill_vial()
                    sim._spend(sim.crafting.make_grym_unf(inv), "craft", "grym unf")
                    sim._spend(sim.crafting.make_egniol(inv), "craft", "egniol")
                except HubError as exc2:
                    sim.log.append(f"egniol stop: {exc2}")
                    break

        # Cook paddlefish to target.
        while (
            inv.count(ItemId.PADDLEFISH) < self.goal.paddlefish
            and inv.has(ItemId.RAW_PADDLEFISH)
            and not sim.timed_out()
        ):
            self._ensure_space(1)
            try:
                sim.hub_cook_paddlefish()
            except HubError as exc:
                sim.log.append(f"cook hub retry: {exc}")
                sim.approach_station(HubStation.RANGE)
                try:
                    sim.hub_cook_paddlefish()
                except HubError as exc2:
                    sim.log.append(f"cook stop: {exc2}")
                    break

        # Drop pestle / leftover raw if at goal.
        if loadout_met(sim, self.goal):
            for extra in (ItemId.PESTLE, ItemId.RAW_PADDLEFISH, ItemId.GRYM_LEAF, ItemId.SHARDS):
                if inv.has(extra) and inv.count(ItemId.PADDLEFISH) >= self.goal.paddlefish:
                    # Keep shards optional; drop pestle/raw for clean final inv.
                    if extra in (ItemId.PESTLE, ItemId.RAW_PADDLEFISH):
                        inv.drop(extra)

        sim.player.equipment.sync_from_inventory(inv)
        gaps = loadout_gaps(sim, self.goal)
        sim.log.append(
            f"loadout done tick={sim.player.tick}/{sim.prep_limit} "
            f"timeout={sim.timed_out()} met={not gaps} gaps={gaps} "
            f"inv={inv.summary()} multi_trip={1 if self._mid_crafted else 0} "
            f"hub_returns={self.hub_returns}"
        )
        sim.log.append(f"tick_buckets: {sim.ledger.as_dict()}")

    def run(self) -> bool:
        self.phase_scout_and_gather()
        self.phase_craft_loadout()
        return loadout_met(self.sim, self.goal)


def run_loadout_scenario(
    rules: GameRules,
    config: AppConfig,
    *,
    loadout: str = LOADOUT_T3_DUAL_T2ARM,
) -> PrepSim:
    if loadout != LOADOUT_T3_DUAL_T2ARM:
        raise ValueError(f"unknown loadout {loadout!r}")
    sim = PrepSim.create(rules, config, use_tile_pathing=True)
    LoadoutScenario(sim, GOAL_T3_DUAL).run()
    return sim


def find_loadout_seed(
    rules: GameRules,
    *,
    loadout: str = LOADOUT_T3_DUAL_T2ARM,
    seeds: range | None = None,
    account=None,
) -> tuple[int, PrepSim] | None:
    """Try seeds until loadout completes within prep limit."""
    if account is None:
        account = AppConfig.phase1_demo().account
    for seed in seeds or range(0, 80):
        cfg = AppConfig(account=account, sim=SimConfig(master_seed=seed))
        sim = run_loadout_scenario(rules, cfg, loadout=loadout)
        if loadout_met(sim):
            return seed, sim
    return None


@dataclass(frozen=True)
class LoadoutSeedScore:
    seed: int
    ticks: int
    move: int
    gather: int
    fight: int
    craft: int
    rooms: int
    steps: int
    tiles: int
    met: bool
    timed_out: bool
    error: str = ""


def _score_one_seed(args: tuple[int, str]) -> LoadoutSeedScore:
    """Worker for process-pool optimize (picklable top-level)."""
    seed, loadout = args
    try:
        rules = GameRules.load()
        account = AppConfig.phase1_demo().account
        cfg = AppConfig(account=account, sim=SimConfig(master_seed=seed))
        sim = run_loadout_scenario(rules, cfg, loadout=loadout)
        b = sim.ledger.as_dict()
        return LoadoutSeedScore(
            seed=seed,
            ticks=sim.player.tick,
            move=b["move"],
            gather=b["gather"],
            fight=b["fight"],
            craft=b["craft"],
            rooms=len(sim.route.room_first_visit),
            steps=len(sim.route.room_steps),
            tiles=len(sim.route.tiles),
            met=loadout_met(sim),
            timed_out=sim.timed_out(),
        )
    except Exception as exc:  # noqa: BLE001 — sweep must not abort on one bad seed
        return LoadoutSeedScore(
            seed=seed,
            ticks=10**9,
            move=0,
            gather=0,
            fight=0,
            craft=0,
            rooms=0,
            steps=0,
            tiles=0,
            met=False,
            timed_out=True,
            error=f"{type(exc).__name__}: {exc}",
        )


def optimize_loadout_seeds(
    rules: GameRules,
    *,
    loadout: str = LOADOUT_T3_DUAL_T2ARM,
    seeds: range | list[int] | None = None,
    workers: int | None = None,
) -> tuple[LoadoutSeedScore | None, list[LoadoutSeedScore]]:
    """
    Run loadout prep across many seeds in parallel; return (best, all scores).

    Best = lowest ticks among successes (then move, steps, seed).
    `rules` is accepted for API symmetry; workers reload rules themselves.
    """
    from concurrent.futures import ProcessPoolExecutor, as_completed

    del rules  # workers load independently for pickling safety
    seed_list = list(seeds if seeds is not None else range(100))
    scores: list[LoadoutSeedScore] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(_score_one_seed, (seed, loadout)): seed for seed in seed_list
        }
        for fut in as_completed(futs):
            scores.append(fut.result())
    scores.sort(key=lambda s: s.seed)
    ok = [s for s in scores if s.met and not s.timed_out and not s.error]
    if not ok:
        return None, scores
    ok.sort(key=lambda s: (s.ticks, s.move, s.steps, s.seed))
    return ok[0], scores
