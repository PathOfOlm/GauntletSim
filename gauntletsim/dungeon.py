"""Mutable dungeon state wrapping a generated layout."""

from __future__ import annotations

from dataclasses import dataclass, field

from gauntletsim.game_rules import GameRules
from gauntletsim.geometry import DungeonGeometry, generate_dungeon_geometry
from gauntletsim.map_generator import DungeonLayout, generate_layout, validate_layout_rules
from gauntletsim.movement import MovementEngine
from gauntletsim.pathfinding import reachable_coords, shortest_path
from gauntletsim.player import MovementError, PlayerState
from gauntletsim.room import Coord, Room


@dataclass
class DungeonState:
    layout: DungeonLayout
    player: PlayerState
    light_ticks: int = 1
    move_ticks: int = 1
    geometry: DungeonGeometry | None = None
    movement: MovementEngine | None = None
    rules_errors: list[str] = field(default_factory=list)

    @classmethod
    def generate(cls, rules: GameRules, master_seed: int) -> DungeonState:
        layout = generate_layout(rules, master_seed)
        errors = validate_layout_rules(layout, rules)
        light = int(rules.get("timing", "room_light_ticks"))
        geometry = generate_dungeon_geometry(rules, layout.rooms, master_seed)
        movement = MovementEngine.create(rules, geometry)
        player = PlayerState(coord=layout.start, tick=0)
        player.tile = geometry.spawn_tile(layout.start)
        player.run_energy = int(rules.get("timing", "run_energy_max_units"))
        state = cls(
            layout=layout,
            player=player,
            light_ticks=light,
            geometry=geometry,
            movement=movement,
            rules_errors=errors,
        )
        # Start is discovered at generation time.
        state.room(layout.start).discovered = True
        return state

    @property
    def rooms(self) -> dict[Coord, Room]:
        return self.layout.rooms

    def room(self, coord: Coord) -> Room:
        return self.layout.rooms[coord]

    def discovered_coords(self) -> set[Coord]:
        return {c for c, r in self.rooms.items() if r.discovered}

    def reachable(self) -> set[Coord]:
        return reachable_coords(
            self.rooms,
            self.player.coord,
            width=self.layout.width,
            height=self.layout.height,
        )

    def path_to(self, goal: Coord) -> list[Coord] | None:
        return shortest_path(
            self.rooms,
            self.player.coord,
            goal,
            width=self.layout.width,
            height=self.layout.height,
            require_discovered=True,
        )

    def step_toward(self, goal: Coord) -> int:
        """Light/move one step toward goal without entering boss via lighting."""
        from gauntletsim.room import RoomKind

        if goal == self.layout.boss:
            return self.player.enter_boss(self.rooms, self.layout.boss)

        if goal.manhattan(self.player.coord) == 1:
            return self.player.move_or_light(
                self.rooms,
                goal,
                width=self.layout.width,
                height=self.layout.height,
                light_ticks=self.light_ticks,
                move_ticks=self.move_ticks,
            )
        path = self.path_to(goal)
        if path is not None and len(path) >= 2:
            nxt = path[1]
            return self.player.move_or_light(
                self.rooms,
                nxt,
                width=self.layout.width,
                height=self.layout.height,
                light_ticks=self.light_ticks,
                move_ticks=self.move_ticks,
            )

        # Fog frontier: light an adjacent non-boss undiscovered room closest to goal.
        candidates = sorted(
            (
                n
                for n in self.player.coord.neighbors()
                if n in self.rooms
                and not self.rooms[n].discovered
                and self.rooms[n].kind != RoomKind.BOSS
            ),
            key=lambda c: c.manhattan(goal),
        )
        if not candidates:
            # Move into a discovered neighbor that gets closer (detour around boss).
            discovered_opts = sorted(
                (
                    n
                    for n in self.player.coord.neighbors()
                    if n in self.rooms
                    and self.rooms[n].discovered
                    and self.rooms[n].kind != RoomKind.BOSS
                ),
                key=lambda c: c.manhattan(goal),
            )
            if not discovered_opts:
                raise MovementError(f"no path toward {goal}")
            return self.player.move_or_light(
                self.rooms,
                discovered_opts[0],
                width=self.layout.width,
                height=self.layout.height,
                light_ticks=self.light_ticks,
                move_ticks=self.move_ticks,
            )
        return self.player.move_or_light(
            self.rooms,
            candidates[0],
            width=self.layout.width,
            height=self.layout.height,
            light_ticks=self.light_ticks,
            move_ticks=self.move_ticks,
        )

    def mark_searched(self, coord: Coord) -> None:
        self.room(coord).searched_depleted = True
