"""Fog-of-war knowledge for prep agents (discovered rooms only)."""

from __future__ import annotations

from dataclasses import dataclass, field

from gauntletsim.map_generator import BOSS_COORD
from gauntletsim.room import (
    Coord,
    DemiType,
    MobTier,
    NodeType,
    RoomKind,
    orthogonal_neighbors,
)


class FogError(PermissionError):
    """Agent attempted to read undiscovered / omniscient dungeon info."""


@dataclass(frozen=True)
class KnownRoom:
    """Contents visible only after the room has been lit/entered."""

    coord: Coord
    kind: RoomKind
    mob_tier: MobTier
    demi_type: DemiType | None
    nodes: dict[NodeType, int]
    cleared: bool
    gather_remaining: dict[NodeType, int] = field(default_factory=dict)

    @property
    def is_demi(self) -> bool:
        return self.mob_tier == MobTier.DEMI_BOSS

    @property
    def has_combat(self) -> bool:
        return self.mob_tier != MobTier.NONE and not self.cleared

    def supply_for(self, deficits: dict[str, int]) -> int:
        """How many needed gather units remain here (0 if none needed)."""
        mapping = (
            (NodeType.ORE, "ore"),
            (NodeType.PHREN, "bark"),
            (NodeType.LINUM, "linum"),
            (NodeType.GRYM, "grym"),
            (NodeType.FISH, "fish"),
        )
        score = 0
        for ntype, key in mapping:
            need = deficits.get(key, 0)
            if need <= 0:
                continue
            avail = self.gather_remaining.get(ntype, 0)
            score += min(need, avail)
        return score


@dataclass
class FogKnowledge:
    """
    Agent-facing dungeon view.

    Legal: discovered rooms' contents, adjacent unlit doorways (frontier only),
    public constants (boss cell always (3,3) in Corrupted).

    Forbidden: layout.fish_room, layout.demi_rooms, scanning undiscovered rooms.
    """

    _sim: object  # PrepSim — typed loosely to avoid cycles

    @property
    def boss(self) -> Coord:
        return BOSS_COORD

    def start(self) -> Coord:
        for c in self.discovered_coords():
            if self._room_raw(c).kind == RoomKind.START:
                return c
        # Spawn always begins discovered in start.
        return self._sim.player.coord  # type: ignore[attr-defined]

    def discovered_coords(self) -> list[Coord]:
        return sorted(self._sim.dungeon.discovered_coords())  # type: ignore[attr-defined]

    def is_discovered(self, coord: Coord) -> bool:
        return bool(self._room_raw(coord).discovered)

    def _room_raw(self, coord: Coord):
        return self._sim.dungeon.room(coord)  # type: ignore[attr-defined]

    def observe(self, coord: Coord) -> KnownRoom:
        """Return known contents; raises FogError if room is still fog."""
        room = self._room_raw(coord)
        if not room.discovered:
            raise FogError(
                f"cannot observe undiscovered room ({coord.x},{coord.y})"
            )
        cleared = coord in self._sim.encounters.state.cleared_rooms  # type: ignore[attr-defined]
        remaining: dict[NodeType, int] = {}
        rr = self._sim.gather.room_resources.get(coord)  # type: ignore[attr-defined]
        if rr is not None:
            for n in rr.nodes:
                if n.remaining > 0:
                    remaining[n.node_type] = remaining.get(n.node_type, 0) + n.remaining
        return KnownRoom(
            coord=coord,
            kind=room.kind,
            mob_tier=room.mob_tier,
            demi_type=room.demi_type,
            nodes=dict(room.nodes),
            cleared=cleared,
            gather_remaining=remaining,
        )

    def frontier(self) -> list[Coord]:
        """
        Adjacent unlit doorways from discovered rooms.

        Returns coords of undiscovered non-boss neighbors (door exists ⇒
        enterable frontier). Boss is excluded — barrier, not a prep room.
        """
        width = self._sim.dungeon.layout.width  # type: ignore[attr-defined]
        height = self._sim.dungeon.layout.height  # type: ignore[attr-defined]
        # Width/height are public grid facts, not room contents.
        out: set[Coord] = set()
        for c in self.discovered_coords():
            for n in orthogonal_neighbors(c, width, height):
                room = self._room_raw(n)
                if room.discovered:
                    continue
                if room.kind == RoomKind.BOSS or n == self.boss:
                    continue
                out.add(n)
        return sorted(out)

    def known_rooms(self) -> list[KnownRoom]:
        return [self.observe(c) for c in self.discovered_coords()]

    def known_with_supply(self, deficits: dict[str, int]) -> list[KnownRoom]:
        return [k for k in self.known_rooms() if k.supply_for(deficits) > 0]

    def known_demis(self, *, uncleared_only: bool = True) -> list[KnownRoom]:
        out = []
        for k in self.known_rooms():
            if not k.is_demi:
                continue
            if uncleared_only and k.cleared:
                continue
            out.append(k)
        return out

    def known_combat(self, *, uncleared_only: bool = True) -> list[KnownRoom]:
        out = []
        for k in self.known_rooms():
            if k.mob_tier == MobTier.NONE:
                continue
            if uncleared_only and k.cleared:
                continue
            out.append(k)
        return out


class LayoutFogProxy:
    """
    Wrap a DungeonLayout so `fish_room` / `demi_rooms` peeks raise FogError.

    Movement may use width/height/rooms/start/boss; agents must not read the
    omniscient target lists.
    """

    _BLOCKED = frozenset({"fish_room", "demi_rooms"})

    def __init__(self, inner) -> None:
        object.__setattr__(self, "_inner", inner)

    def __getattr__(self, name: str):
        if name in self._BLOCKED:
            raise FogError(
                f"omniscient layout.{name} is forbidden under fog-of-war"
            )
        return getattr(self._inner, name)

    def __setattr__(self, name: str, value) -> None:
        if name == "_inner":
            object.__setattr__(self, name, value)
            return
        setattr(self._inner, name, value)
