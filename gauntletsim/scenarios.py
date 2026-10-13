"""Named prep scenarios / loadout goals (Phase 3.5)."""

from __future__ import annotations

from dataclasses import dataclass

from gauntletsim.config import AppConfig, SimConfig
from gauntletsim.crafting import ArmourSlot, WeaponStyle
from gauntletsim.game_rules import GameRules
from gauntletsim.hub import HubError, HubStation
from gauntletsim.inventory import ItemId
from gauntletsim.prep import PrepSim
from gauntletsim.room import Coord, DemiType, MobTier, NodeType, RoomKind

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
    """Tick-accurate prep agent aiming for a named loadout."""

    def __init__(self, sim: PrepSim, goal: LoadoutGoal = GOAL_T3_DUAL) -> None:
        self.sim = sim
        self.goal = goal

    @property
    def inv(self):
        return self.sim.player.inventory

    def _ensure_space(self, need: int = 1) -> None:
        if self.inv.free_slots() >= need:
            return
        # Drop least-critical junk first.
        for item in (
            ItemId.SPIKE,
            ItemId.WEAPON_FRAME,
            ItemId.AXE,
            ItemId.PICKAXE,
            ItemId.HARPOON,
            ItemId.TELEPORT_CRYSTAL,
        ):
            if self.inv.free_slots() >= need:
                return
            if self.inv.has(item):
                self.inv.drop(item)
                self.sim.log.append(f"t={self.sim.player.tick}: drop {item.value}")

    def _return_hub(self) -> None:
        if self.sim.at_hub():
            return
        if self.inv.has(ItemId.TELEPORT_CRYSTAL):
            self.sim.teleport_to_start()
        else:
            self.sim.go_to(self.sim.dungeon.layout.start)

    def _visit_and_clear(self, coord: Coord) -> None:
        if self.sim.timed_out():
            return
        self.sim.go_to(coord)
        if self.sim.timed_out():
            return
        self.sim.clear_here()

    def _gather_type(self, coord: Coord, ntype: NodeType, until: int, item: ItemId) -> None:
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
        return self.inv.count(ItemId.RAW_PADDLEFISH) >= TARGET_FISH

    def _grym_ok(self) -> bool:
        return self.inv.count(ItemId.GRYM_LEAF) >= TARGET_GRYM

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
        return {
            "ore": max(0, TARGET_ORE - self.inv.count(ItemId.ORE)),
            "bark": max(0, TARGET_BARK - self.inv.count(ItemId.BARK)),
            "linum": max(0, TARGET_LINUM - self.inv.count(ItemId.LINUM)),
            "grym": max(0, TARGET_GRYM - self.inv.count(ItemId.GRYM_LEAF)),
            "fish": max(0, TARGET_FISH - self.inv.count(ItemId.RAW_PADDLEFISH)),
        }

    def _room_supply_score(self, coord: Coord) -> int:
        """How many needed gather units this room can still provide."""
        d = self._deficits()
        if not any(d.values()):
            return 0
        rr = self.sim.gather.room_resources[coord]
        score = 0
        mapping = (
            (NodeType.ORE, "ore"),
            (NodeType.PHREN, "bark"),
            (NodeType.LINUM, "linum"),
            (NodeType.GRYM, "grym"),
            (NodeType.FISH, "fish"),
        )
        for ntype, key in mapping:
            need = d[key]
            if need <= 0:
                continue
            avail = sum(n.remaining for n in rr.nodes if n.node_type == ntype)
            score += min(need, avail)
        return score

    def _gather_needed_here(self, coord: Coord) -> None:
        d = self._deficits()
        if d["ore"]:
            self._gather_type(coord, NodeType.ORE, TARGET_ORE, ItemId.ORE)
        if d["bark"]:
            self._gather_type(coord, NodeType.PHREN, TARGET_BARK, ItemId.BARK)
        if d["linum"]:
            self._gather_type(coord, NodeType.LINUM, TARGET_LINUM, ItemId.LINUM)
        if d["grym"]:
            self._gather_type(coord, NodeType.GRYM, TARGET_GRYM, ItemId.GRYM_LEAF)
        if d["fish"]:
            self._gather_type(
                coord, NodeType.FISH, TARGET_FISH, ItemId.RAW_PADDLEFISH
            )

    def phase_scout_and_gather(self) -> None:
        """Targeted route: fish → needed demis → shop mats → hub."""
        layout = self.sim.dungeon.layout

        # 1) Guaranteed fish room — food + first frame/shards from mobs.
        self._visit_and_clear(layout.fish_room)
        self._gather_type(
            layout.fish_room, NodeType.FISH, TARGET_FISH, ItemId.RAW_PADDLEFISH
        )

        # 2) Only the demis we need for orb / bowstring (+ frames). Stop early.
        demis = list(layout.demi_rooms)
        demis.sort(
            key=lambda c: (
                0
                if self.sim.dungeon.room(c).demi_type
                in (DemiType.DRAGON, DemiType.DARK_BEAST)
                else 1,
                c.manhattan(self.sim.player.coord),
            )
        )
        for coord in demis:
            if self.sim.timed_out():
                break
            if self._parts_ok() and self._frames_ok():
                break
            self._visit_and_clear(coord)

        # 3) If still short on frames/shards, clear a few nearby combat rooms.
        if not self.sim.timed_out() and (not self._frames_ok() or not self._shards_ok()):
            combat_rooms = [
                c
                for c, r in self.sim.dungeon.rooms.items()
                if r.kind == RoomKind.RESOURCE
                and r.mob_tier != MobTier.NONE
                and c not in self.sim.encounters.state.cleared_rooms
            ]
            combat_rooms.sort(key=lambda c: c.manhattan(self.sim.player.coord))
            for coord in combat_rooms:
                if self.sim.timed_out():
                    break
                if self._frames_ok() and self._shards_ok():
                    break
                # Prefer rooms that also supply missing mats.
                if self._room_supply_score(coord) <= 0 and self._shards_ok():
                    continue
                self._visit_and_clear(coord)
                self._gather_needed_here(coord)

        # 4) Shopping loop: repeatedly visit the nearest room with the most supply.
        while not self.sim.timed_out() and not self._gather_ready():
            candidates = [
                c
                for c, r in self.sim.dungeon.rooms.items()
                if r.kind == RoomKind.RESOURCE and self._room_supply_score(c) > 0
            ]
            if not candidates:
                self.sim.log.append(
                    f"gather stuck deficits={self._deficits()} "
                    f"parts={self._parts_ok()} frames={self._frames_ok()} "
                    f"shards={self.inv.count(ItemId.SHARDS)}"
                )
                break
            candidates.sort(
                key=lambda c: (
                    -self._room_supply_score(c),
                    c.manhattan(self.sim.player.coord),
                )
            )
            coord = candidates[0]
            # Clear only if we still need shards/frames; otherwise gather-only.
            need_clear = (
                coord not in self.sim.encounters.state.cleared_rooms
                and (
                    not self._frames_ok()
                    or not self._shards_ok()
                    or self.sim.dungeon.room(coord).mob_tier == MobTier.NONE
                )
            )
            if need_clear and self.sim.dungeon.room(coord).mob_tier != MobTier.NONE:
                self._visit_and_clear(coord)
            else:
                self.sim.go_to(coord)
            if self.sim.timed_out():
                break
            self._gather_needed_here(coord)

        self._return_hub()
        self.sim.log.append(
            f"gather phase end tick={self.sim.player.tick} "
            f"ready={self._gather_ready()} deficits={self._deficits()} "
            f"shards={self.inv.count(ItemId.SHARDS)} "
            f"parts_ok={self._parts_ok()} frames_ok={self._frames_ok()}"
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

        # Drop leftover mats / frames / spike to make space before potions+food.
        for junk in (
            ItemId.ORE,
            ItemId.BARK,
            ItemId.LINUM,
            ItemId.WEAPON_FRAME,
            ItemId.SPIKE,
            ItemId.BOWSTRING,
            ItemId.ORB,
        ):
            if inv.has(junk):
                inv.drop(junk)

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
            f"inv={inv.summary()}"
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
