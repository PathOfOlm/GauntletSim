"""Walk/run movement ticks and run-energy accounting (Phase 3.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
import math

from gauntletsim.geometry import DungeonGeometry, Tile, doorway_entry_tile
from gauntletsim.game_rules import GameRules
from gauntletsim.room import Coord, RoomKind
from gauntletsim.tile_pathfinding import astar_path


@dataclass
class TickLedger:
    """Separate prep tick buckets for reporting."""

    move: int = 0
    light: int = 0
    gather: int = 0
    craft: int = 0
    fight: int = 0
    teleport: int = 0

    @property
    def total(self) -> int:
        return (
            self.move
            + self.light
            + self.gather
            + self.craft
            + self.fight
            + self.teleport
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "move": self.move,
            "light": self.light,
            "gather": self.gather,
            "craft": self.craft,
            "fight": self.fight,
            "teleport": self.teleport,
            "total": self.total,
        }


def clamp_weight(kg: float) -> float:
    return max(0.0, min(64.0, kg))


def run_energy_drain_per_tick(
    agility: int, weight_kg: float, *, stamina_multiplier: float = 1.0
) -> int:
    """Wiki Energy / Agility formula (internal units 0–10000)."""
    base = (60.0 + 67.0 * clamp_weight(weight_kg) / 64.0) * (1.0 - agility / 300.0)
    return max(0, int(math.floor(base * stamina_multiplier)))


def run_energy_regen_per_tick(agility: int) -> int:
    return int(math.floor(agility / 10.0 + 15.0))


@dataclass
class MovementEngine:
    rules: GameRules
    geometry: DungeonGeometry
    ledger: TickLedger = field(default_factory=TickLedger)
    walk_tiles: int = 1
    run_tiles: int = 2
    energy_max: int = 10000
    light_ticks: int = 1
    weight_kg: float = 0.0
    stamina_multiplier: float = 0.3
    stamina_effect_ticks: int = 200

    @classmethod
    def create(cls, rules: GameRules, geometry: DungeonGeometry) -> MovementEngine:
        return cls(
            rules=rules,
            geometry=geometry,
            walk_tiles=int(rules.get("timing", "walk_tiles_per_tick")),
            run_tiles=int(rules.get("timing", "run_tiles_per_tick")),
            energy_max=int(rules.get("timing", "run_energy_max_units")),
            light_ticks=int(rules.get("timing", "room_light_ticks")),
            weight_kg=float(rules.assumption_default("player.prep_weight_kg")),
            stamina_multiplier=float(rules.get("timing", "stamina_drain_multiplier")),
            stamina_effect_ticks=int(rules.get("timing", "stamina_effect_ticks")),
        )

    def discovered_set(self, rooms: dict) -> set[Coord]:
        return {c for c, r in rooms.items() if r.discovered}

    def walkable_fn(self, rooms: dict, *, allow_undiscovered: Coord | None = None):
        discovered = self.discovered_set(rooms)

        def ok(tile: Tile) -> bool:
            room = self.geometry.room_of(tile)
            if room not in rooms:
                return False
            if rooms[room].kind == RoomKind.BOSS and room not in discovered:
                return False
            if room not in discovered and room != allow_undiscovered:
                return False
            return self.geometry.is_walkable(tile)

        return ok

    def _apply_energy_tick(self, player, *, running: bool) -> None:
        agility = getattr(player, "agility", 70)
        if running and player.run_energy > 0:
            mult = (
                self.stamina_multiplier
                if player.stamina_ticks_remaining > 0
                else 1.0
            )
            drain = run_energy_drain_per_tick(
                agility, self.weight_kg, stamina_multiplier=mult
            )
            player.run_energy = max(0, player.run_energy - drain)
            if player.stamina_ticks_remaining > 0:
                player.stamina_ticks_remaining -= 1
            if player.run_energy == 0:
                player.running = False
        else:
            regen = run_energy_regen_per_tick(agility)
            player.run_energy = min(self.energy_max, player.run_energy + regen)

    def follow_path(
        self,
        player,
        path: list[Tile],
        rooms: dict,
        *,
        prep_limit: int,
        bucket: str = "move",
    ) -> int:
        """Advance along path tiles; lighting when first entering a new room."""
        if len(path) < 2:
            return 0
        spent_total = 0
        i = 1
        while i < len(path) and not player.timed_out:
            dest_room = self.geometry.room_of(path[i])
            entering_new = not rooms[dest_room].discovered
            if entering_new:
                if rooms[dest_room].kind == RoomKind.BOSS:
                    break
                # Light + step onto entry tile (replaces a move tick).
                rooms[dest_room].discovered = True
                player.tile = path[i]
                player.coord = dest_room
                player.advance(self.light_ticks, prep_limit)
                self.ledger.light += self.light_ticks
                spent_total += self.light_ticks
                i += 1
                continue

            # Movement tick: walk 1 or run up to run_tiles along path.
            running = bool(player.running and player.run_energy > 0)
            step = self.run_tiles if running else self.walk_tiles
            advanced = 0
            while advanced < step and i < len(path):
                nxt_room = self.geometry.room_of(path[i])
                if not rooms[nxt_room].discovered:
                    break
                if rooms[nxt_room].kind == RoomKind.BOSS and not player.entered_boss:
                    break
                player.tile = path[i]
                player.coord = nxt_room
                i += 1
                advanced += 1
            if advanced == 0:
                break
            self._apply_energy_tick(player, running=running and advanced > 0)
            player.advance(1, prep_limit)
            if bucket == "move":
                self.ledger.move += 1
            spent_total += 1
        return spent_total

    def path_to_tile(
        self,
        player,
        goal: Tile,
        rooms: dict,
        *,
        allow_undiscovered: Coord | None = None,
    ) -> list[Tile] | None:
        if player.tile is None:
            return None
        return astar_path(
            self.geometry,
            player.tile,
            goal,
            walkable=self.walkable_fn(rooms, allow_undiscovered=allow_undiscovered),
        )

    def travel_to_tile(
        self,
        player,
        goal: Tile,
        rooms: dict,
        *,
        prep_limit: int,
    ) -> int:
        """Path and walk/run to an already-discovered walkable tile."""
        if player.tile == goal:
            return 0
        path = self.path_to_tile(player, goal, rooms)
        if path is None:
            return 0
        return self.follow_path(
            player, path, rooms, prep_limit=prep_limit, bucket="move"
        )

    def travel_to_room(
        self,
        player,
        goal_room: Coord,
        rooms: dict,
        *,
        prep_limit: int,
        max_iters: int = 200,
    ) -> int:
        """Explore/path to goal room center with tile movement + lighting."""
        spent = 0
        iters = 0
        while iters < max_iters and not player.timed_out:
            iters += 1
            if player.coord == goal_room and rooms[goal_room].discovered:
                center = self.geometry.rooms[goal_room].center_tile()
                if player.tile == center:
                    break
                path = self.path_to_tile(player, center, rooms)
                if path is None:
                    break
                spent += self.follow_path(
                    player, path, rooms, prep_limit=prep_limit, bucket="move"
                )
                break

            next_room = self._next_room_toward(player.coord, goal_room, rooms)
            if next_room is None:
                break

            if rooms[next_room].discovered:
                target = self.geometry.rooms[next_room].center_tile()
                path = self.path_to_tile(player, target, rooms)
                if path is None:
                    break
                spent += self.follow_path(
                    player, path, rooms, prep_limit=prep_limit, bucket="move"
                )
                continue

            # Approach exit doorway in current room, then light into next.
            exit_tile = doorway_entry_tile(self.geometry, next_room, player.coord)
            path_to_exit = self.path_to_tile(player, exit_tile, rooms)
            if path_to_exit is not None and len(path_to_exit) > 1:
                spent += self.follow_path(
                    player, path_to_exit, rooms, prep_limit=prep_limit
                )
            entry = doorway_entry_tile(self.geometry, player.coord, next_room)
            path = self.path_to_tile(
                player, entry, rooms, allow_undiscovered=next_room
            )
            if path is None:
                if player.tile is not None and chebyshev_adj(player.tile, entry):
                    path = [player.tile, entry]
                else:
                    break
            spent += self.follow_path(player, path, rooms, prep_limit=prep_limit)
        return spent

    def _next_room_toward(
        self, current: Coord, goal: Coord, rooms: dict
    ) -> Coord | None:
        """First room step along a path that may light fog (avoids boss lighting)."""
        from collections import deque

        width = self.geometry.width_rooms
        height = self.geometry.height_rooms
        q: deque[Coord] = deque([current])
        parent: dict[Coord, Coord | None] = {current: None}
        found: Coord | None = None
        while q:
            cur = q.popleft()
            if cur == goal:
                found = cur
                break
            for n in cur.neighbors():
                if not (0 <= n.x < width and 0 <= n.y < height):
                    continue
                if n not in rooms or n in parent:
                    continue
                if rooms[n].kind == RoomKind.BOSS and n != goal:
                    continue
                # May traverse undiscovered non-boss rooms in the plan.
                if not rooms[n].discovered and rooms[n].kind == RoomKind.BOSS:
                    continue
                parent[n] = cur
                q.append(n)
        if found is None:
            # Fallback: frontier room closest to goal.
            best = None
            best_d = 10**9
            for c, r in rooms.items():
                if r.discovered or r.kind == RoomKind.BOSS:
                    continue
                for n in c.neighbors():
                    if n in rooms and rooms[n].discovered:
                        d = c.manhattan(goal)
                        if d < best_d:
                            best_d = d
                            best = c
                        break
            found = best
            if found is None:
                return None
            # Recompute parent path to found via discovered + found.
            q = deque([current])
            parent = {current: None}
            while q:
                cur = q.popleft()
                if cur == found:
                    break
                for n in cur.neighbors():
                    if n not in rooms or n in parent:
                        continue
                    if rooms[n].kind == RoomKind.BOSS:
                        continue
                    if not rooms[n].discovered and n != found:
                        continue
                    parent[n] = cur
                    q.append(n)
        if found not in parent and found != current:
            return None
        node = found
        while parent.get(node) is not None and parent[node] != current:
            node = parent[node]  # type: ignore[assignment]
        if node == current:
            return found if found != current else None
        return node


def chebyshev_adj(a: Tile, b: Tile) -> bool:
    return max(abs(a.x - b.x), abs(a.y - b.y)) <= 1 and a != b
