"""Player position and exploration movement (Phase 2)."""

from __future__ import annotations

from dataclasses import dataclass

from gauntletsim.room import Coord, Room, RoomKind, orthogonal_neighbors


class MovementError(ValueError):
    """Illegal movement / lighting action."""


@dataclass
class PlayerState:
    coord: Coord
    tick: int = 0

    def move_or_light(
        self,
        rooms: dict[Coord, Room],
        target: Coord,
        *,
        width: int = 7,
        height: int = 7,
        light_ticks: int = 1,
        move_ticks: int = 1,
    ) -> int:
        """
        Move into an orthogonally adjacent room.

        - Already discovered: costs `move_ticks`.
        - Undiscovered non-boss: light then enter for `light_ticks`.
        - Boss room: rejected here; use `enter_boss`.
        Returns ticks spent.
        """
        if target not in rooms:
            raise MovementError(f"no room at {target}")
        if target not in orthogonal_neighbors(self.coord, width, height):
            raise MovementError("target not orthogonally adjacent")

        room = rooms[target]
        if not room.exists:
            raise MovementError("room does not exist")

        if room.discovered:
            self.coord = target
            self.tick += move_ticks
            return move_ticks

        if room.kind == RoomKind.BOSS:
            raise MovementError(
                "boss room not entered via light; use enter_boss when ready"
            )

        room.discovered = True
        self.coord = target
        self.tick += light_ticks
        return light_ticks

    def enter_boss(self, rooms: dict[Coord, Room], boss: Coord) -> int:
        """Manually enter boss room from an adjacent tile."""
        if self.coord.manhattan(boss) != 1:
            raise MovementError("must be adjacent to boss to enter")
        boss_room = rooms[boss]
        boss_room.discovered = True
        self.coord = boss
        self.tick += 1
        return 1
