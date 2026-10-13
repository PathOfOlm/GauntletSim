"""ASCII map visualization for discovered dungeon state."""

from __future__ import annotations

from gauntletsim.dungeon import DungeonState
from gauntletsim.room import Coord, MobTier, RoomKind


# Cell glyphs (center char of a 3-wide cell).
def _glyph(state: DungeonState, coord: Coord) -> str:
    room = state.room(coord)
    if state.player.coord == coord:
        return "@"
    if not room.discovered:
        return "?"
    if room.kind == RoomKind.BOSS:
        return "H"
    if room.kind == RoomKind.START:
        return "S"
    if room.mob_tier == MobTier.DEMI_BOSS:
        assert room.demi_type is not None
        return {"bear": "B", "dragon": "D", "dark_beast": "K"}[room.demi_type.value]
    if room.fishing_spots >= 3 and coord == state.layout.fish_room:
        return "F"
    if room.mob_tier == MobTier.STRONG:
        return "m"
    if room.mob_tier == MobTier.WEAK:
        return "w"
    if room.node_count() > 0:
        return "·"
    return "."


def render_ascii(state: DungeonState) -> str:
    """
    Render a 7×7 ASCII map.

    Legend: @ player, S start, H Hunllef, F guaranteed fish, B/D/K demi,
    w weak, m strong, · resources, . empty discovered, ? fog.
    """
    width = state.layout.width
    height = state.layout.height
    lines: list[str] = []
    lines.append(
        f"seed={state.layout.master_seed} tick={state.player.tick} "
        f"pos=({state.player.coord.x},{state.player.coord.y}) "
        f"discovered={len(state.discovered_coords())}/{width * height}"
    )
    sep = "+" + ("---+" * width)
    for y in range(height):
        lines.append(sep)
        row = "|"
        for x in range(width):
            g = _glyph(state, Coord(x, y))
            row += f" {g} |"
        lines.append(row)
    lines.append(sep)
    lines.append(
        "legend: @player S start H boss F fish3 B/D/K demi "
        "w weak m strong · nodes . empty ? fog"
    )
    return "\n".join(lines)
