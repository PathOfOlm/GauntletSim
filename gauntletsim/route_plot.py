"""Human-readable PNG/HTML prep-route figures (optional [viz] extra)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from gauntletsim.geometry import DungeonGeometry
from gauntletsim.hub import HubLayout, HubStation
from gauntletsim.room import Coord, MobTier, RoomKind
from gauntletsim.route import RouteRecorder, _room_type_glyph

if TYPE_CHECKING:
    from gauntletsim.dungeon import DungeonState


class VizDependencyError(RuntimeError):
    """Raised when matplotlib is not installed."""


def _require_matplotlib():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D
        from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
    except ImportError as exc:  # pragma: no cover - exercised when extras missing
        raise VizDependencyError(
            'Route PNG needs the viz extra: pip install -e ".[viz]"'
        ) from exc
    return plt, FancyArrowPatch, FancyBboxPatch, Rectangle, Line2D


# High-contrast room fills (light enough for dark text labels).
_ROOM_COLORS = {
    "start": "#7dcea0",
    "boss": "#e74c3c",
    "fish": "#5dade2",
    "demi": "#e67e22",
    "strong": "#f5b041",
    "weak": "#f9e79f",
    "resource": "#a9dfbf",
    "empty": "#d5d8dc",
    "fog": "#566573",
    "visited_edge": "#1a5276",
}


def _room_color_key(state: DungeonState, coord: Coord) -> str:
    room = state.room(coord)
    if room.kind == RoomKind.BOSS:
        return "boss"
    if room.kind == RoomKind.START:
        return "start"
    if room.mob_tier == MobTier.DEMI_BOSS:
        return "demi"
    if room.fishing_spots >= 3 and coord == state.layout.fish_room:
        return "fish"
    if room.mob_tier == MobTier.STRONG:
        return "strong"
    if room.mob_tier == MobTier.WEAK:
        return "weak"
    if room.node_count() > 0:
        return "resource"
    if not room.discovered:
        return "fog"
    return "empty"


def _room_label(state: DungeonState, coord: Coord, route: RouteRecorder) -> str:
    glyph = _room_type_glyph(state, coord)
    n = route.room_first_visit.get(coord)
    if n is not None:
        return f"{n}\n{glyph}"
    if not state.room(coord).discovered:
        return "?"
    return glyph


def render_route_figure(
    state: DungeonState,
    route: RouteRecorder,
    *,
    title: str | None = None,
    loadout: str | None = None,
    geometry: DungeonGeometry | None = None,
    hub: HubLayout | None = None,
):
    """Build a matplotlib Figure: 7×7 route + hub craft trail."""
    plt, _FancyArrowPatch, FancyBboxPatch, Rectangle, Line2D = _require_matplotlib()

    geom = geometry or state.geometry
    hub_layout = hub or state.hub
    width = state.layout.width
    height = state.layout.height
    ticks = state.player.tick
    seed = state.layout.master_seed

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(14.5, 8.2),
        gridspec_kw={"width_ratios": [1.15, 1.0], "wspace": 0.18},
    )
    fig.patch.set_facecolor("#f4f6f7")
    ax_map, ax_hub = axes

    # ---- Left: 7×7 room map ----
    ax_map.set_facecolor("#eaecee")
    ax_map.set_xlim(-0.5, width - 0.5)
    ax_map.set_ylim(height - 0.5, -0.5)  # y-down like game grid
    ax_map.set_aspect("equal")
    ax_map.set_xticks(range(width))
    ax_map.set_yticks(range(height))
    ax_map.tick_params(labelsize=11)
    ax_map.set_xlabel("room x", fontsize=12)
    ax_map.set_ylabel("room y", fontsize=12)
    ax_map.set_title("Dungeon rooms — visit order", fontsize=14, fontweight="bold", pad=10)

    for y in range(height):
        for x in range(width):
            c = Coord(x, y)
            if c not in route.room_first_visit and not state.room(c).discovered:
                key = "fog"
            else:
                key = _room_color_key(state, c)
            color = _ROOM_COLORS[key]
            edge = (
                _ROOM_COLORS["visited_edge"]
                if c in route.room_first_visit
                else "#7f8c8d"
            )
            lw = 2.2 if c in route.room_first_visit else 0.8
            ax_map.add_patch(
                FancyBboxPatch(
                    (x - 0.46, y - 0.46),
                    0.92,
                    0.92,
                    boxstyle="round,pad=0.02,rounding_size=0.08",
                    facecolor=color,
                    edgecolor=edge,
                    linewidth=lw,
                )
            )
            label = _room_label(state, c, route)
            text_color = "#f8f9f9" if key == "fog" else "#1b2631"
            ax_map.text(
                x,
                y,
                label,
                ha="center",
                va="center",
                fontsize=13 if "\n" in label else 15,
                fontweight="bold",
                color=text_color,
                linespacing=1.05,
            )

    # Path polyline + arrows (room steps)
    if len(route.room_steps) >= 2:
        xs = [c.x for c in route.room_steps]
        ys = [c.y for c in route.room_steps]
        ax_map.plot(
            xs,
            ys,
            color="#1a252f",
            linewidth=2.0,
            alpha=0.35,
            zorder=3,
            solid_capstyle="round",
        )
        for i in range(len(route.room_steps) - 1):
            a, b = route.room_steps[i], route.room_steps[i + 1]
            teleport = abs(a.x - b.x) + abs(a.y - b.y) > 1
            style = "dashed" if teleport else "solid"
            color = "#8e44ad" if teleport else "#c0392b"
            ax_map.annotate(
                "",
                xy=(b.x, b.y),
                xytext=(a.x, a.y),
                arrowprops={
                    "arrowstyle": "-|>",
                    "color": color,
                    "lw": 2.4 if not teleport else 2.0,
                    "linestyle": style,
                    "mutation_scale": 16,
                    "shrinkA": 14,
                    "shrinkB": 14,
                    "alpha": 0.92,
                },
                zorder=4,
            )
        # Start / end markers
        ax_map.scatter(
            [route.room_steps[0].x],
            [route.room_steps[0].y],
            s=120,
            c="#145a32",
            edgecolors="white",
            linewidths=1.5,
            zorder=5,
            label="start",
        )
        ax_map.scatter(
            [route.room_steps[-1].x],
            [route.room_steps[-1].y],
            s=120,
            c="#922b21",
            edgecolors="white",
            linewidths=1.5,
            zorder=5,
            label="end",
        )

    legend_handles = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor=_ROOM_COLORS["start"], markersize=12, label="Start"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=_ROOM_COLORS["fish"], markersize=12, label="Fish"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=_ROOM_COLORS["demi"], markersize=12, label="Demi"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=_ROOM_COLORS["strong"], markersize=12, label="Strong"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=_ROOM_COLORS["weak"], markersize=12, label="Weak"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=_ROOM_COLORS["resource"], markersize=12, label="Nodes"),
        Line2D([0], [0], color="#c0392b", lw=2.4, label="Path"),
        Line2D([0], [0], color="#8e44ad", lw=2.0, linestyle="--", label="Teleport"),
    ]
    ax_map.legend(
        handles=legend_handles,
        loc="upper left",
        bbox_to_anchor=(0.0, -0.08),
        ncol=4,
        fontsize=10,
        frameon=True,
        fancybox=True,
    )

    # ---- Right: hub start-room trail ----
    ax_hub.set_facecolor("#fdfefe")
    ax_hub.set_title("Start room — hub craft trail", fontsize=14, fontweight="bold", pad=10)
    if geom is None or hub_layout is None:
        ax_hub.text(0.5, 0.5, "No hub geometry", ha="center", va="center", fontsize=14)
        ax_hub.set_xticks([])
        ax_hub.set_yticks([])
    else:
        size = geom.room_size
        start = hub_layout.start
        rt = geom.rooms[start]
        ax_hub.set_xlim(-0.5, size - 0.5)
        ax_hub.set_ylim(size - 0.5, -0.5)
        ax_hub.set_aspect("equal")
        ax_hub.set_xticks(range(0, size, 2))
        ax_hub.set_yticks(range(0, size, 2))
        ax_hub.tick_params(labelsize=10)
        ax_hub.set_xlabel("local x", fontsize=12)
        ax_hub.set_ylabel("local y", fontsize=12)

        # Floor / walls
        for ly in range(size):
            for lx in range(size):
                walk = rt.local_walkable(lx, ly)
                ax_hub.add_patch(
                    Rectangle(
                        (lx - 0.5, ly - 0.5),
                        1,
                        1,
                        facecolor="#d6eaf8" if walk else "#2c3e50",
                        edgecolor="#aab7b8",
                        linewidth=0.3,
                    )
                )

        # Trail polyline (local coords)
        trail = [t for t in route.tiles if geom.room_of(t) == start]
        if len(trail) >= 2:
            txs = [geom.local_of(t)[0] for t in trail]
            tys = [geom.local_of(t)[1] for t in trail]
            ax_hub.plot(
                txs,
                tys,
                color="#c0392b",
                linewidth=2.6,
                alpha=0.9,
                zorder=3,
                solid_capstyle="round",
            )
            # Direction arrows every few steps
            step = max(1, len(trail) // 12)
            for i in range(0, len(trail) - 1, step):
                a, b = trail[i], trail[min(i + step, len(trail) - 1)]
                ax, ay = geom.local_of(a)
                bx, by = geom.local_of(b)
                if (ax, ay) == (bx, by):
                    continue
                ax_hub.annotate(
                    "",
                    xy=(bx, by),
                    xytext=(ax, ay),
                    arrowprops={
                        "arrowstyle": "-|>",
                        "color": "#922b21",
                        "lw": 1.6,
                        "mutation_scale": 12,
                        "shrinkA": 2,
                        "shrinkB": 2,
                        "alpha": 0.85,
                    },
                    zorder=4,
                )
            ax_hub.scatter(
                [txs[0]], [tys[0]], s=90, c="#145a32", zorder=5, edgecolors="white"
            )
            ax_hub.scatter(
                [txs[-1]], [tys[-1]], s=90, c="#922b21", zorder=5, edgecolors="white"
            )

        station_style = {
            HubStation.SINGING_BOWL: ("Bowl", "#1abc9c"),
            HubStation.WATER_PUMP: ("Pump", "#3498db"),
            HubStation.RANGE: ("Range", "#e74c3c"),
            HubStation.TOOL_STORAGE: ("Tools", "#7f8c8d"),
            HubStation.TELEPORT_PLATFORM: ("Tele", "#9b59b6"),
            HubStation.RECIPE_GUIDES: ("Guide", "#b7950b"),
        }
        for st, (label, color) in station_style.items():
            for lx, ly in hub_layout.object_locals(st):
                ax_hub.scatter(
                    [lx],
                    [ly],
                    s=220,
                    c=color,
                    marker="s",
                    edgecolors="#1b2631",
                    linewidths=1.4,
                    zorder=6,
                )
                ax_hub.text(
                    lx,
                    ly - 0.85,
                    label,
                    ha="center",
                    va="top",
                    fontsize=11,
                    fontweight="bold",
                    color="#1b2631",
                    zorder=7,
                    bbox={
                        "boxstyle": "round,pad=0.15",
                        "facecolor": "white",
                        "edgecolor": color,
                        "alpha": 0.92,
                    },
                )

        ax_hub.text(
            0.02,
            -0.08,
            "Red line = walking trail in start room (bowl → pump → range).",
            transform=ax_hub.transAxes,
            fontsize=10,
            color="#1b2631",
        )

    loadout_bit = f" · loadout={loadout}" if loadout else ""
    fig.suptitle(
        title
        or (
            f"GauntletSim prep route — seed {seed} · {ticks} ticks"
            f"{loadout_bit} · {len(route.room_first_visit)} rooms / "
            f"{len(route.room_steps)} steps"
        ),
        fontsize=16,
        fontweight="bold",
        y=0.98,
        color="#1b2631",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    return fig


def write_route_png(
    out_path: Path,
    state: DungeonState,
    route: RouteRecorder,
    *,
    loadout: str | None = None,
    title: str | None = None,
    dpi: int = 160,
) -> Path:
    plt, *_ = _require_matplotlib()
    fig = render_route_figure(state, route, title=title, loadout=loadout)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def write_route_html(
    out_path: Path,
    png_path: Path,
    *,
    title: str,
) -> Path:
    """Simple HTML wrapper that displays the PNG in a browser."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rel = png_path.name if png_path.parent == out_path.parent else str(png_path)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
  <style>
    body {{ margin: 0; background: #1b2631; color: #f4f6f7;
           font-family: system-ui, sans-serif; }}
    header {{ padding: 1rem 1.25rem; }}
    h1 {{ margin: 0; font-size: 1.25rem; font-weight: 650; }}
    p {{ margin: 0.35rem 0 0; opacity: 0.85; font-size: 0.95rem; }}
    main {{ padding: 0 1.25rem 1.5rem; }}
    img {{ max-width: 100%; height: auto; background: #f4f6f7;
           border-radius: 8px; display: block; }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <p>Open this file in a browser. Image: <code>{rel}</code></p>
  </header>
  <main>
    <img src="{rel}" alt="{title}"/>
  </main>
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")
    return out_path


def viz_available() -> bool:
    try:
        _require_matplotlib()
        return True
    except VizDependencyError:
        return False
