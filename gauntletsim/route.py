"""Prep route recording and ASCII/SVG visualization (Phase 3.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from gauntletsim.geometry import DungeonGeometry, Tile
from gauntletsim.hub import HubLayout, HubStation
from gauntletsim.room import Coord, MobTier, RoomKind

if TYPE_CHECKING:
    from gauntletsim.dungeon import DungeonState


@dataclass
class RouteEvent:
    tick: int
    kind: str
    room: Coord | None
    tile: Tile | None
    label: str = ""


@dataclass
class RouteRecorder:
    """Records room/tile movement and labeled prep events."""

    tiles: list[Tile] = field(default_factory=list)
    room_steps: list[Coord] = field(default_factory=list)
    room_first_visit: dict[Coord, int] = field(default_factory=dict)
    events: list[RouteEvent] = field(default_factory=list)
    _last_tile: Tile | None = None
    _last_room: Coord | None = None

    def record_position(
        self,
        tile: Tile | None,
        room: Coord,
        *,
        tick: int = 0,
        kind: str = "move",
        label: str = "",
    ) -> None:
        if tile is not None and tile != self._last_tile:
            self.tiles.append(tile)
            self._last_tile = tile
        self._note_room(room, tick=tick, kind=kind, label=label, tile=tile)

    def _note_room(
        self,
        room: Coord,
        *,
        tick: int,
        kind: str,
        label: str = "",
        tile: Tile | None = None,
    ) -> None:
        if room != self._last_room:
            self.room_steps.append(room)
            if room not in self.room_first_visit:
                self.room_first_visit[room] = len(self.room_first_visit) + 1
            self._last_room = room
            if kind == "move" and not label:
                label = f"enter ({room.x},{room.y})"
            self.events.append(
                RouteEvent(tick=tick, kind=kind, room=room, tile=tile, label=label)
            )
        elif label and kind != "move":
            self.events.append(
                RouteEvent(tick=tick, kind=kind, room=room, tile=tile, label=label)
            )

    def record_teleport(
        self, room: Coord, tile: Tile | None, *, tick: int
    ) -> None:
        self._last_tile = None  # force tile append after warp
        self.record_position(
            tile, room, tick=tick, kind="teleport", label="teleport → start"
        )

    def record_event(
        self,
        kind: str,
        label: str,
        *,
        tick: int,
        room: Coord | None,
        tile: Tile | None,
    ) -> None:
        self.events.append(
            RouteEvent(tick=tick, kind=kind, room=room, tile=tile, label=label)
        )

    def room_path_string(self) -> str:
        if not self.room_steps:
            return "(no rooms)"
        parts = [f"({c.x},{c.y})" for c in self.room_steps]
        return " → ".join(parts)

    def unique_rooms_in_order(self) -> list[Coord]:
        seen: set[Coord] = set()
        out: list[Coord] = []
        for c in self.room_steps:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out


def _room_type_glyph(state: DungeonState, coord: Coord) -> str:
    room = state.room(coord)
    if room.kind == RoomKind.BOSS:
        return "H"
    if room.kind == RoomKind.START:
        return "S"
    if room.mob_tier == MobTier.DEMI_BOSS and room.demi_type is not None:
        return {"bear": "B", "dragon": "D", "dark_beast": "K"}[room.demi_type.value]
    if room.fishing_spots >= 3:
        return "F"
    if room.mob_tier == MobTier.STRONG:
        return "m"
    if room.mob_tier == MobTier.WEAK:
        return "w"
    if room.node_count() > 0:
        return "·"
    return "."


def _arrow(a: Coord, b: Coord) -> str:
    dx, dy = b.x - a.x, b.y - a.y
    if abs(dx) + abs(dy) != 1 and max(abs(dx), abs(dy)) > 1:
        return "⌁"  # non-adjacent (teleport / long hop)
    if dx == 1 and dy == 0:
        return "→"
    if dx == -1 and dy == 0:
        return "←"
    if dx == 0 and dy == 1:
        return "↓"
    if dx == 0 and dy == -1:
        return "↑"
    if dx == 1 and dy == 1:
        return "↘"
    if dx == -1 and dy == 1:
        return "↙"
    if dx == 1 and dy == -1:
        return "↗"
    if dx == -1 and dy == -1:
        return "↖"
    return "·"


def render_room_route_ascii(state: DungeonState, route: RouteRecorder) -> str:
    """7×7 overlay: first-visit index + room type; itinerary with arrows."""
    width = state.layout.width
    height = state.layout.height
    lines: list[str] = [
        "=== room route (first-visit # + type) ===",
        f"seed={state.layout.master_seed} rooms_visited="
        f"{len(route.room_first_visit)} steps={len(route.room_steps)} "
        f"tiles={len(route.tiles)}",
    ]
    # Header column indices
    header = "    " + "".join(f" {x:^4}" for x in range(width))
    lines.append(header)
    sep = "   +" + ("-----+" * width)
    for y in range(height):
        lines.append(sep)
        row = f" {y} |"
        for x in range(width):
            c = Coord(x, y)
            glyph = _room_type_glyph(state, c)
            n = route.room_first_visit.get(c)
            if n is not None:
                cell = f"{n:02d}{glyph}"
            elif state.room(c).discovered:
                cell = f"  {glyph} "
            else:
                cell = "  ? "
            row += f"{cell:^5}|"
        lines.append(row)
    lines.append(sep)
    lines.append("itinerary (room steps, revisits included):")
    # Chunk itinerary for readability
    chain = []
    for i, c in enumerate(route.room_steps):
        n = route.room_first_visit[c]
        piece = f"{n:02d}@({c.x},{c.y})"
        if i > 0:
            chain.append(_arrow(route.room_steps[i - 1], c))
        chain.append(piece)
    # wrap ~10 tokens per line
    buf: list[str] = []
    line_parts: list[str] = []
    for tok in chain:
        line_parts.append(tok)
        if len(line_parts) >= 14:
            buf.append(" ".join(line_parts))
            line_parts = []
    if line_parts:
        buf.append(" ".join(line_parts))
    lines.extend(buf if buf else ["(empty)"])
    lines.append(
        "legend: ## = first-visit order, letter = room type "
        "(S start H boss F fish B/D/K demi w/m mobs)"
    )
    return "\n".join(lines)


def render_hub_tile_trail_ascii(
    geometry: DungeonGeometry,
    hub: HubLayout,
    route: RouteRecorder,
    *,
    max_marks: int = 36,
) -> str:
    """Dense start-room tile trail with hub station markers."""
    start = hub.start
    size = geometry.room_size
    rt = geometry.rooms[start]
    # Collect start-room trail tiles in order (dedupe consecutive).
    trail = [t for t in route.tiles if geometry.room_of(t) == start]
    # Map local -> earliest mark index (1-based, capped charset)
    marks = "123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    local_mark: dict[tuple[int, int], str] = {}
    mark_i = 0
    for t in trail:
        lx, ly = geometry.local_of(t)
        if (lx, ly) in local_mark:
            continue
        if mark_i >= len(marks) or mark_i >= max_marks:
            local_mark.setdefault((lx, ly), "*")
            continue
        local_mark[(lx, ly)] = marks[mark_i]
        mark_i += 1

    station_glyph = {
        HubStation.SINGING_BOWL: "B",
        HubStation.RANGE: "R",
        HubStation.WATER_PUMP: "P",
        HubStation.TOOL_STORAGE: "T",
        HubStation.TELEPORT_PLATFORM: "X",
        HubStation.RECIPE_GUIDES: "G",
    }
    station_at: dict[tuple[int, int], str] = {}
    for st, g in station_glyph.items():
        for lx, ly in hub.object_locals(st):
            station_at[(lx, ly)] = g

    lines = [
        "=== hub tile trail (start room) ===",
        f"start_room=({start.x},{start.y}) trail_tiles={len(trail)} "
        f"unique_marks={len(local_mark)}",
        "stations: B=bowl R=range P=pump T=tools X=teleport G=guides",
        "trail marks: 1..9 a..z in visit order (* = overflow)",
    ]
    # column header every 4
    hdr = "   " + "".join(f"{x%10}" for x in range(size))
    lines.append(hdr)
    for ly in range(size):
        row = f"{ly:2d} "
        for lx in range(size):
            if (lx, ly) in station_at:
                row += station_at[(lx, ly)]
            elif (lx, ly) in local_mark:
                row += local_mark[(lx, ly)]
            elif not rt.local_walkable(lx, ly):
                row += "#"
            else:
                row += "."
        lines.append(row)
    # Hub station segment from events
    hub_events = [
        e
        for e in route.events
        if e.kind in {"station", "craft"}
        or (e.label and any(s in e.label for s in ("bowl", "pump", "range", "singing", "water", "cook")))
    ]
    if hub_events:
        lines.append("hub actions:")
        for e in hub_events[-20:]:
            tile_s = (
                f"({e.tile.x},{e.tile.y})" if e.tile is not None else "-"
            )
            lines.append(f"  t={e.tick}: {e.kind} {e.label} @ {tile_s}")
    return "\n".join(lines)


def render_route_panel(
    state: DungeonState,
    route: RouteRecorder,
    *,
    geometry: DungeonGeometry | None = None,
    hub: HubLayout | None = None,
) -> str:
    parts = [
        render_room_route_ascii(state, route),
        "",
        f"room_path: {route.room_path_string()}",
    ]
    geom = geometry or state.geometry
    hub_layout = hub or state.hub
    if geom is not None and hub_layout is not None:
        parts.extend(["", render_hub_tile_trail_ascii(geom, hub_layout, route)])
    return "\n".join(parts)


def render_room_route_svg(
    state: DungeonState,
    route: RouteRecorder,
    *,
    cell: int = 48,
    margin: int = 24,
) -> str:
    """Simple SVG: 7×7 rooms, visit numbers, polyline of room-step centers."""
    width = state.layout.width
    height = state.layout.height
    w = margin * 2 + width * cell
    h = margin * 2 + height * cell + 40
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">',
        '<rect width="100%" height="100%" fill="#1a1d23"/>',
        f'<text x="{margin}" y="16" fill="#c8d0dc" font-family="monospace" '
        f'font-size="12">seed={state.layout.master_seed} room route '
        f"({len(route.room_first_visit)} rooms)</text>",
    ]
    # cells
    for y in range(height):
        for x in range(width):
            c = Coord(x, y)
            px = margin + x * cell
            py = margin + 20 + y * cell
            visited = c in route.room_first_visit
            fill = "#2f6fed" if visited else ("#2a2f3a" if state.room(c).discovered else "#12151a")
            stroke = "#6b7380"
            parts.append(
                f'<rect x="{px}" y="{py}" width="{cell - 2}" height="{cell - 2}" '
                f'rx="4" fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
            )
            glyph = _room_type_glyph(state, c)
            n = route.room_first_visit.get(c)
            label = f"{n:02d}{glyph}" if n is not None else glyph
            parts.append(
                f'<text x="{px + cell / 2 - 1}" y="{py + cell / 2 + 4}" '
                f'fill="#e8edf5" font-family="monospace" font-size="11" '
                f'text-anchor="middle">{label}</text>'
            )
    # polyline through room step centers
    if len(route.room_steps) >= 2:
        pts = []
        for c in route.room_steps:
            cx = margin + c.x * cell + (cell - 2) / 2
            cy = margin + 20 + c.y * cell + (cell - 2) / 2
            pts.append(f"{cx},{cy}")
        parts.append(
            f'<polyline points="{" ".join(pts)}" fill="none" '
            f'stroke="#ffb454" stroke-width="2" stroke-opacity="0.85"/>'
        )
        # start / end dots
        c0 = route.room_steps[0]
        c1 = route.room_steps[-1]
        for c, color in ((c0, "#7dffa0"), (c1, "#ff6b6b")):
            cx = margin + c.x * cell + (cell - 2) / 2
            cy = margin + 20 + c.y * cell + (cell - 2) / 2
            parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="4" fill="{color}"/>'
            )
    parts.append("</svg>")
    return "\n".join(parts)


def write_route_artifacts(
    out_dir: Path,
    state: DungeonState,
    route: RouteRecorder,
    *,
    stem: str = "route",
    loadout: str | None = None,
    ascii_panel: bool = False,
) -> list[Path]:
    """Write route artifacts under out_dir. Prefer PNG/HTML when [viz] is installed."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    # Human-readable PNG + HTML (optional matplotlib).
    try:
        from gauntletsim.route_plot import (
            VizDependencyError,
            write_route_html,
            write_route_png,
        )

        png_path = out_dir / f"{stem}-route.png"
        write_route_png(png_path, state, route, loadout=loadout)
        written.append(png_path)
        html_path = out_dir / f"{stem}-route.html"
        title = (
            f"Prep route — seed {state.layout.master_seed} · "
            f"{state.player.tick} ticks"
            + (f" · {loadout}" if loadout else "")
        )
        write_route_html(html_path, png_path, title=title)
        written.append(html_path)
    except VizDependencyError:
        pass

    # Always keep a compact room-path text file.
    path_file = out_dir / f"{stem}-rooms.txt"
    path_file.write_text(route.room_path_string() + "\n", encoding="utf-8")
    written.append(path_file)

    # Optional dense ASCII / SVG (stdlib fallbacks).
    if ascii_panel:
        panel = render_route_panel(state, route)
        txt_path = out_dir / f"{stem}.txt"
        txt_path.write_text(panel + "\n", encoding="utf-8")
        written.append(txt_path)
        svg_path = out_dir / f"{stem}.svg"
        svg_path.write_text(render_room_route_svg(state, route) + "\n", encoding="utf-8")
        written.append(svg_path)
    return written
