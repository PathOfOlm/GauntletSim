"""Phase 3 / 3.5 preparation simulation: gather, fight drops, craft, timer, tile pathing."""

from __future__ import annotations

from dataclasses import dataclass, field

from gauntletsim.config import AppConfig
from gauntletsim.crafting import ArmourSlot, CraftingBench, WeaponStyle
from gauntletsim.demibosses import PrepEncounters
from gauntletsim.dungeon import DungeonState
from gauntletsim.game_rules import GameRules
from gauntletsim.hub import (
    HubError,
    HubStation,
    is_adjacent_to_station,
    nearest_approach_tile,
    require_start_room,
)
from gauntletsim.inventory import ItemId
from gauntletsim.movement import MovementEngine, TickLedger
from gauntletsim.player import PlayerState
from gauntletsim.resources import GatherSystem
from gauntletsim.room import Coord, NodeType, RoomKind
from gauntletsim.route import RouteRecorder, render_route_panel
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
    movement: MovementEngine
    log: list[str] = field(default_factory=list)
    use_tile_pathing: bool = True
    route: RouteRecorder = field(default_factory=RouteRecorder)

    @classmethod
    def create(
        cls, rules: GameRules, config: AppConfig, *, use_tile_pathing: bool = True
    ) -> PrepSim:
        dungeon = DungeonState.generate(rules, config.sim.master_seed)
        start = dungeon.layout.start
        account_player = PlayerState.from_account(start, config.account)
        # Keep hub-aware spawn from dungeon.generate (adjacent to tool storage).
        account_player.tile = dungeon.player.tile
        account_player.run_energy = int(rules.get("timing", "run_energy_max_units"))
        dungeon.player = account_player
        dungeon.room(start).discovered = True
        gather = GatherSystem.create(rules, dungeon.rooms, config.sim.master_seed)
        encounters = PrepEncounters.create(rules, config.sim.master_seed)
        crafting = CraftingBench(rules)
        limit = (
            config.sim.prep_ticks
            if config.sim.prep_ticks is not None
            else rules.prep_ticks
        )
        assert dungeon.movement is not None
        route = RouteRecorder()
        dungeon.movement.route = route
        sim = cls(
            rules=rules,
            config=config,
            dungeon=dungeon,
            gather=gather,
            encounters=encounters,
            crafting=crafting,
            prep_limit=limit,
            movement=dungeon.movement,
            use_tile_pathing=use_tile_pathing,
            route=route,
        )
        # Seed spawn into the route before any travel.
        route.record_position(
            account_player.tile,
            start,
            tick=0,
            kind="spawn",
            label="spawn",
        )
        return sim

    @property
    def player(self) -> PlayerState:
        return self.dungeon.player

    @property
    def ledger(self) -> TickLedger:
        return self.movement.ledger

    def _spend(self, ticks: int, bucket: str, note: str = "") -> None:
        self.player.advance(ticks, self.prep_limit)
        if bucket == "gather":
            self.ledger.gather += ticks
        elif bucket == "craft":
            self.ledger.craft += ticks
        elif bucket == "fight":
            self.ledger.fight += ticks
        elif bucket == "teleport":
            self.ledger.teleport += ticks
        elif bucket == "light":
            self.ledger.light += ticks
        elif bucket == "move":
            self.ledger.move += ticks
        if note:
            self.log.append(f"t={self.player.tick}: {note}")

    def remaining(self) -> int:
        return self.player.remaining_prep_ticks(self.prep_limit)

    def timed_out(self) -> bool:
        return self.player.timed_out or self.player.tick >= self.prep_limit

    def go_to(self, goal: Coord, max_steps: int = 80) -> int:
        if self.use_tile_pathing and self.dungeon.geometry is not None:
            before = self.player.tick
            self.movement.travel_to_room(
                self.player,
                goal,
                self.dungeon.rooms,
                prep_limit=self.prep_limit,
                max_iters=max_steps * 4,
            )
            return max(0, self.player.tick - before)

        # Legacy coarse room hops (Phase 3).
        steps = 0
        while self.player.coord != goal and steps < max_steps and not self.timed_out():
            before = self.player.tick
            self.dungeon.step_toward(goal)
            if self.player.tick >= self.prep_limit:
                self.player.timed_out = True
            spent = self.player.tick - before
            if spent:
                self.ledger.move += spent
            steps += 1
        return steps

    def _approach_tile(self, goal, *, label: str) -> int:
        """Full path to a walkable tile; logs move ticks. Returns ticks spent."""
        if (
            not self.use_tile_pathing
            or self.dungeon.geometry is None
            or self.player.tile is None
            or goal is None
        ):
            return 0
        if self.player.tile == goal:
            return 0
        before = self.player.tick
        self.movement.travel_to_tile(
            self.player, goal, self.dungeon.rooms, prep_limit=self.prep_limit
        )
        spent = max(0, self.player.tick - before)
        if spent:
            self.log.append(f"t={self.player.tick}: move → {label} ({spent} ticks)")
        return spent

    def _node_approach_tile(self, prefer: NodeType | None = None):
        """Walkable tile on/adjacent to the next gatherable node."""
        geom = self.dungeon.geometry
        assert geom is not None
        coord = self.player.coord
        rr = self.gather.room_resources[coord]
        node = rr.next_gatherable(prefer)
        if node is None or node.local is None:
            return geom.rooms[coord].center_tile()
        rt = geom.rooms[coord]
        lx, ly = node.local
        if rt.local_walkable(lx, ly):
            return rt.to_global(lx, ly)
        for dx, dy in (
            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1),
            (1, 1),
            (-1, -1),
            (1, -1),
            (-1, 1),
        ):
            nx, ny = lx + dx, ly + dy
            if rt.local_walkable(nx, ny):
                return rt.to_global(nx, ny)
        return rt.center_tile()

    def clear_here(self) -> dict[str, int]:
        # Path to combat tile (room center) before spending fight ticks.
        if self.use_tile_pathing and self.dungeon.geometry is not None:
            combat = self.dungeon.geometry.rooms[self.player.coord].center_tile()
            self._approach_tile(combat, label="combat")
        room = self.dungeon.room(self.player.coord)
        # Protect Magic before demi rooms (video meta); damage not modeled yet.
        if room.mob_tier.value == "demi_boss" and self.player.protect_prayer != "magic":
            self.player.protect_prayer = "magic"
            self.log.append(
                f"t={self.player.tick}: protect_magic before demi @ "
                f"({room.coord.x},{room.coord.y})"
            )
        ticks, drops = self.encounters.clear_room(room, self.player.inventory)
        self._last_fight_ticks = ticks
        if ticks:
            self._spend(ticks, "fight", f"clear {room.mob_tier.value} {drops}")
        return drops

    def gather_here(self, prefer: NodeType | None = None) -> dict:
        if self.timed_out():
            return {}
        if self.use_tile_pathing and self.dungeon.geometry is not None:
            approach = self._node_approach_tile(prefer)
            self._approach_tile(approach, label=f"gather:{(prefer.value if prefer else 'any')}")
        ticks, gained = self.gather.gather_one(
            self.player.coord, self.player.inventory, prefer=prefer
        )
        self._last_gather_ticks = getattr(self, "_last_gather_ticks", 0) + ticks
        self._spend(
            ticks, "gather", f"gather { {k.value: v for k, v in gained.items()} }"
        )
        rr = self.gather.room_resources[self.player.coord]
        if rr.all_depleted():
            self.dungeon.room(self.player.coord).searched_depleted = True
        return gained

    def begin_room_visit_overlap(self) -> None:
        """Reset per-visit fight/gather counters used for overlap rebate."""
        self._last_fight_ticks = 0
        self._last_gather_ticks = 0

    def apply_fight_gather_overlap(self) -> int:
        """
        Deterministic rebate when fight+gather happen in the same room visit.

        rebate = int(min(fight, gather) * overlap_fraction) removed from fight bucket.
        """
        fight = int(getattr(self, "_last_fight_ticks", 0))
        gather = int(getattr(self, "_last_gather_ticks", 0))
        if fight <= 0 or gather <= 0:
            return 0
        try:
            frac = float(
                self.rules.assumption_default(
                    "combat.prep_fight_gather_overlap_fraction"
                )
            )
        except KeyError:
            frac = 0.0
        rebate = int(min(fight, gather) * frac)
        if rebate <= 0:
            return 0
        rebate = min(rebate, self.player.tick, self.ledger.fight)
        self.player.tick -= rebate
        if self.player.tick < self.prep_limit:
            self.player.timed_out = False
        self.ledger.fight -= rebate
        self.log.append(
            f"t={self.player.tick}: fight+gather overlap rebate={rebate} "
            f"(fight={fight} gather={gather} frac={frac})"
        )
        self._last_fight_ticks = 0
        self._last_gather_ticks = 0
        return rebate

    def fill_vial_at_fish(self) -> int:
        """Fill an empty vial at a fishing spot (not only the hub pump)."""
        if not self.rules.get("resources", "fill_vial_at_fishing_spot"):
            raise HubError("fill_vial_at_fishing_spot disabled in rules")
        room = self.dungeon.room(self.player.coord)
        has_fish = room.fishing_spots >= 1 or room.nodes.get(NodeType.FISH, 0) > 0
        if not has_fish:
            raise HubError("no fishing spot in this room")
        if self.use_tile_pathing and self.dungeon.geometry is not None:
            approach = self._node_approach_tile(NodeType.FISH)
            self._approach_tile(approach, label="fill_vial@fish")
        ticks = self.crafting.fill_vial(self.player.inventory)
        self._spend(ticks, "craft", "fill vial @ fishing spot")
        return ticks

    def craft_egniol_field(self) -> int:
        """Make one egniol from water vial + grym + dust (no hub station required)."""
        inv = self.player.inventory
        ticks = self.crafting.make_grym_unf(inv)
        ticks += self.crafting.make_egniol(inv)
        self._spend(ticks, "craft", "egniol on the move")
        return ticks

    def crush_spare_t3(self, item: ItemId) -> int:
        ticks = self.crafting.crush_t3_component(self.player.inventory, item)
        self._spend(ticks, "craft", f"crush {item.value} → shards")
        return ticks

    def sip_egniol_if_low_energy(self, *, threshold_units: int = 2500) -> bool:
        """Drink egniol when run energy is low during prep (stamina + prayer)."""
        inv = self.player.inventory
        if not inv.has(ItemId.EGNIOL_3):
            return False
        if self.player.run_energy >= threshold_units:
            return False
        restore = self.crafting.egniol_prayer_restore(self.config.account.prayer)
        energy_pct = int(self.rules.get("crafting", "egniol_run_energy_percent"))
        stamina = int(self.rules.get("timing", "stamina_effect_ticks"))
        energy_max = int(self.rules.get("timing", "run_energy_max_units"))
        self.player.drink_egniol(
            restore,
            energy_pct,
            energy_max=energy_max,
            stamina_ticks=stamina,
        )
        self.log.append(
            f"t={self.player.tick}: sip egniol (energy→{self.player.run_energy})"
        )
        return True

    def teleport_to_start(self) -> bool:
        """Use teleport crystal if available (not already at start)."""
        if self.at_hub():
            return False
        if not self.player.inventory.has(ItemId.TELEPORT_CRYSTAL):
            return False
        ticks = int(self.rules.assumption_default("timing.teleport_crystal_ticks"))
        self.player.inventory.remove(ItemId.TELEPORT_CRYSTAL)
        start = self.dungeon.layout.start
        self.player.coord = start
        hub = self.dungeon.hub
        if self.dungeon.geometry is not None and hub is not None:
            self.player.tile = nearest_approach_tile(
                self.dungeon.geometry,
                hub,
                HubStation.TOOL_STORAGE,
                discovered={start},
            )
        elif self.dungeon.geometry is not None:
            self.player.tile = self.dungeon.geometry.spawn_tile(start)
        self._spend(ticks, "teleport", "teleport crystal → start")
        self.route.record_teleport(
            start, self.player.tile, tick=self.player.tick
        )
        return True

    def return_to_start(self, *, prefer_teleport: bool = True) -> None:
        if prefer_teleport and self.teleport_to_start():
            return
        self.go_to(self.dungeon.layout.start)

    def at_hub(self) -> bool:
        return self.dungeon.room(self.player.coord).kind == RoomKind.START

    def at_station(self, station: HubStation) -> bool:
        hub = self.dungeon.hub
        if hub is None or self.dungeon.geometry is None:
            return self.at_hub()  # coarse mode: room presence only
        return is_adjacent_to_station(
            self.dungeon.geometry, hub, self.player.tile, station
        )

    def approach_station(self, station: HubStation) -> int:
        """Walk/run to a tile adjacent to a hub station; returns move ticks spent."""
        if not self.use_tile_pathing or self.dungeon.hub is None:
            if not self.at_hub():
                self.go_to(self.dungeon.layout.start)
            return 0
        hub = self.dungeon.hub
        geom = self.dungeon.geometry
        assert geom is not None
        if self.player.coord != hub.start:
            self.go_to(hub.start)
        if self.timed_out():
            return 0
        if self.at_station(station):
            return 0
        goal = nearest_approach_tile(
            geom, hub, station, discovered=self.dungeon.discovered_coords()
        )
        spent = self._approach_tile(goal, label=station.value)
        self.route.record_event(
            "station",
            station.value,
            tick=self.player.tick,
            room=self.player.coord,
            tile=self.player.tile,
        )
        return spent

    def approach_boss_door(self) -> int:
        """Path to the start-side doorway facing the boss room (barrier approach)."""
        if not self.use_tile_pathing or self.dungeon.geometry is None:
            return 0
        from gauntletsim.geometry import doorway_entry_tile

        boss = self.dungeon.layout.boss
        start = self.dungeon.layout.start
        # Stand on the start-room doorway abutting the boss.
        door = doorway_entry_tile(self.dungeon.geometry, boss, start)
        if self.player.coord != start:
            self.go_to(start)
        return self._approach_tile(door, label="boss_door")

    def _require_station(self, station: HubStation) -> None:
        if not self.use_tile_pathing or self.dungeon.hub is None:
            if not self.at_hub():
                raise HubError(f"must be in start room for {station.value}")
            return
        require_start_room(self.player.coord, self.dungeon.hub)
        if not self.at_station(station):
            raise HubError(f"must be adjacent to {station.value}")

    def hub_craft_basic_weapon(self, style: WeaponStyle) -> int:
        self.approach_station(HubStation.SINGING_BOWL)
        self._require_station(HubStation.SINGING_BOWL)
        ticks = self.crafting.craft_basic_weapon(self.player.inventory, style)
        self._spend(ticks, "craft", f"craft {style.value} basic @ bowl")
        return ticks

    def hub_upgrade_weapon_attuned(self, style: WeaponStyle) -> int:
        self.approach_station(HubStation.SINGING_BOWL)
        self._require_station(HubStation.SINGING_BOWL)
        ticks = self.crafting.upgrade_weapon_attuned(self.player.inventory, style)
        self._spend(ticks, "craft", f"craft {style.value} attuned @ bowl")
        return ticks

    def hub_upgrade_weapon_perfected(self, style: WeaponStyle) -> int:
        self.approach_station(HubStation.SINGING_BOWL)
        self._require_station(HubStation.SINGING_BOWL)
        ticks = self.crafting.upgrade_weapon_perfected(self.player.inventory, style)
        self._spend(ticks, "craft", f"craft {style.value} perfected @ bowl")
        return ticks

    def hub_craft_armour_basic(self, slot: ArmourSlot) -> int:
        self.approach_station(HubStation.SINGING_BOWL)
        self._require_station(HubStation.SINGING_BOWL)
        ticks = self.crafting.craft_armour_basic(self.player.inventory, slot)
        self._spend(ticks, "craft", f"craft {slot.value} basic @ bowl")
        return ticks

    def hub_upgrade_armour_attuned(self, slot: ArmourSlot) -> int:
        self.approach_station(HubStation.SINGING_BOWL)
        self._require_station(HubStation.SINGING_BOWL)
        ticks = self.crafting.upgrade_armour_attuned(self.player.inventory, slot)
        self._spend(ticks, "craft", f"craft {slot.value} attuned @ bowl")
        return ticks

    def hub_craft_vial(self) -> int:
        self.approach_station(HubStation.SINGING_BOWL)
        self._require_station(HubStation.SINGING_BOWL)
        ticks = self.crafting.craft_vial(self.player.inventory)
        self._spend(ticks, "craft", "craft vial @ bowl")
        return ticks

    def hub_craft_teleport_crystal(self) -> int:
        self.approach_station(HubStation.SINGING_BOWL)
        self._require_station(HubStation.SINGING_BOWL)
        ticks = self.crafting.craft_teleport_crystal(self.player.inventory)
        self._spend(ticks, "craft", "craft teleport crystal @ bowl")
        return ticks

    def hub_fill_vial(self) -> int:
        self.approach_station(HubStation.WATER_PUMP)
        self._require_station(HubStation.WATER_PUMP)
        ticks = self.crafting.fill_vial(self.player.inventory)
        self._spend(ticks, "craft", "fill vial @ pump")
        return ticks

    def hub_cook_paddlefish(self) -> tuple[int, bool]:
        self.approach_station(HubStation.RANGE)
        self._require_station(HubStation.RANGE)
        ticks, ok = self.crafting.cook_paddlefish(
            self.player.inventory, self.config.account.cooking
        )
        self._spend(ticks, "craft", "cook paddlefish @ range" if ok else "burn @ range")
        return ticks, ok

    def demo_prep_slice(self) -> None:
        """
        Deterministic fog-of-war demo:
        expand frontier → react to fish/demi/ore when discovered → hub craft.
        """
        from gauntletsim.fog import FogKnowledge

        fog = FogKnowledge(self)
        start = fog.start()
        fish_coord = None
        demi_cleared = False
        ore_done = False

        for _ in range(40):
            if self.timed_out():
                break
            # Gather fish once found.
            if fish_coord is None:
                for known in fog.known_rooms():
                    if known.gather_remaining.get(NodeType.FISH, 0) > 0:
                        fish_coord = known.coord
                        break
            if fish_coord is not None and fog.is_discovered(fish_coord):
                if self.player.coord != fish_coord:
                    self.go_to(fish_coord)
                if not self.timed_out():
                    known = fog.observe(fish_coord)
                    if known.has_combat:
                        self.clear_here()
                    while (
                        not self.timed_out()
                        and self.gather.room_resources[fish_coord].has_gatherable(
                            NodeType.FISH
                        )
                        and self.player.inventory.count(ItemId.RAW_PADDLEFISH) < 8
                    ):
                        try:
                            self.gather_here(NodeType.FISH)
                        except Exception as exc:  # noqa: BLE001
                            self.log.append(f"gather stop: {exc}")
                            break

            # Clear one discovered demi if any.
            if not demi_cleared and not self.timed_out():
                demis = fog.known_demis(uncleared_only=True)
                if demis:
                    demis.sort(key=lambda k: k.coord.manhattan(self.player.coord))
                    self.go_to(demis[0].coord)
                    if not self.timed_out():
                        self.clear_here()
                    demi_cleared = True

            # Ore from a known room.
            if not ore_done and not self.timed_out():
                ore_rooms = [
                    k
                    for k in fog.known_rooms()
                    if k.gather_remaining.get(NodeType.ORE, 0) > 0
                ]
                if ore_rooms:
                    ore_rooms.sort(key=lambda k: k.coord.manhattan(self.player.coord))
                    target = ore_rooms[0].coord
                    self.go_to(target)
                    if not self.timed_out():
                        known = fog.observe(target)
                        if known.has_combat:
                            self.clear_here()
                        for ntype in (
                            NodeType.ORE,
                            NodeType.PHREN,
                            NodeType.LINUM,
                            NodeType.GRYM,
                        ):
                            while (
                                not self.timed_out()
                                and self.gather.room_resources[target].has_gatherable(
                                    ntype
                                )
                            ):
                                try:
                                    self.gather_here(ntype)
                                except Exception:
                                    break
                    ore_done = self.player.inventory.count(ItemId.ORE) >= 1

            if (
                fish_coord is not None
                and demi_cleared
                and ore_done
            ) or self.timed_out():
                break

            # Expand fog if still missing pieces.
            frontier = fog.frontier()
            if not frontier:
                break
            boss = fog.boss
            frontier.sort(
                key=lambda c: (
                    0 if c.manhattan(boss) == 1 else 1,
                    c.manhattan(self.player.coord),
                )
            )
            self.go_to(frontier[0])

        self.return_to_start(prefer_teleport=True)
        if self.player.coord != start and not self.at_hub():
            self.go_to(start)
        if self.timed_out():
            self.log.append("prep timed out before crafting")
            return

        inv = self.player.inventory
        if inv.has(ItemId.WEAPON_FRAME) and not self.timed_out():
            self.hub_craft_basic_weapon(WeaponStyle.BOW)
        if inv.has(ItemId.BOW_BASIC) and inv.count(ItemId.SHARDS) >= 50 and not self.timed_out():
            self.hub_upgrade_weapon_attuned(WeaponStyle.BOW)
        if (
            inv.has(ItemId.BOW_ATTUNED)
            and inv.has(ItemId.BOWSTRING)
            and not self.timed_out()
        ):
            self.hub_upgrade_weapon_perfected(WeaponStyle.BOW)
        if (
            inv.has(ItemId.ORE)
            and inv.has(ItemId.BARK)
            and inv.has(ItemId.LINUM)
            and inv.count(ItemId.SHARDS) >= 50
            and not self.timed_out()
        ):
            self.hub_craft_armour_basic(ArmourSlot.HELM)

        while inv.has(ItemId.RAW_PADDLEFISH) and not self.timed_out():
            self.hub_cook_paddlefish()

        if (
            inv.has(ItemId.GRYM_LEAF)
            and inv.count(ItemId.SHARDS) >= 20
            and not self.timed_out()
        ):
            self.hub_craft_vial()
            self.hub_fill_vial()
            # Inventory combines — no extra hub station (pestle anywhere).
            self._spend(self.crafting.make_grym_unf(inv), "craft", "grym unf")
            self._spend(self.crafting.make_egniol(inv), "craft", "egniol")

        self.player.equipment.sync_from_inventory(inv)
        self.log.append(
            f"done tick={self.player.tick}/{self.prep_limit} "
            f"timeout={self.timed_out()} inv={inv.summary()}"
        )
        self.log.append(f"tick_buckets: {self.ledger.as_dict()}")

    def status_lines(self) -> list[str]:
        p = self.player
        buckets = self.ledger.as_dict()
        energy_pct = p.run_energy / 100.0
        return [
            "GauntletSim — Phase 3.5 prep (tile pathing)",
            f"master_seed: {self.dungeon.layout.master_seed}",
            f"tick: {p.tick}/{self.prep_limit} remaining={self.remaining()}",
            f"timeout: {self.timed_out()} entered_boss: {p.entered_boss}",
            f"hp: {p.hitpoints}/{p.hitpoints_max} prayer: {p.prayer}/{p.prayer_max}",
            f"pos_room: ({p.coord.x},{p.coord.y}) "
            f"tile: {None if p.tile is None else (p.tile.x, p.tile.y)}",
            f"run_energy: {energy_pct:.1f}% running={p.running} "
            f"stamina_ticks={p.stamina_ticks_remaining}",
            f"equipment: helm={p.equipment.helm_tier} body={p.equipment.body_tier} "
            f"legs={p.equipment.legs_tier} bow={p.equipment.has_bow} "
            f"staff={p.equipment.has_staff} halb={p.equipment.has_halberd}",
            f"frames={self.encounters.state.frames_dropped} "
            f"demi_kills={self.encounters.state.demi_kills} "
            f"t3={sorted(x.value for x in self.encounters.state.t3_parts)}",
            f"inventory_slots: {p.inventory.slots_used()}/{p.inventory.capacity}",
            f"inventory: {p.inventory.summary()}",
            (
                "ticks: "
                f"move={buckets['move']} light={buckets['light']} "
                f"gather={buckets['gather']} craft={buckets['craft']} "
                f"fight={buckets['fight']} teleport={buckets['teleport']} "
                f"sum={buckets['total']}"
            ),
        ]

    def ascii_map(self) -> str:
        return render_ascii(self.dungeon)

    def route_panel(self) -> str:
        """ASCII room-route overlay + hub tile trail."""
        return render_route_panel(
            self.dungeon,
            self.route,
            geometry=self.dungeon.geometry,
            hub=self.dungeon.hub,
        )
