"""OSRS-style tile pathfinding (A* on walkable graph, 8-directional)."""

from __future__ import annotations

import heapq
from collections.abc import Callable

from gauntletsim.geometry import DungeonGeometry, Tile


def chebyshev(a: Tile, b: Tile) -> int:
    return max(abs(a.x - b.x), abs(a.y - b.y))


def astar_path(
    geometry: DungeonGeometry,
    start: Tile,
    goal: Tile,
    *,
    walkable: Callable[[Tile], bool] | None = None,
) -> list[Tile] | None:
    """
    Shortest path by Chebyshev steps (diagonal allowed, cost 1).
    Matches OSRS: diagonal moves cost the same tick rate as orthogonal.
    """
    if start == goal:
        return [start]

    def ok(t: Tile) -> bool:
        if walkable is not None:
            return walkable(t)
        return geometry.is_walkable(t)

    if not ok(start) or not ok(goal):
        return None

    open_heap: list[tuple[int, int, Tile]] = []
    counter = 0
    heapq.heappush(open_heap, (chebyshev(start, goal), counter, start))
    came_from: dict[Tile, Tile | None] = {start: None}
    g_score: dict[Tile, int] = {start: 0}

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if current == goal:
            path = [current]
            while came_from[path[-1]] is not None:
                path.append(came_from[path[-1]])  # type: ignore[arg-type]
            path.reverse()
            return path
        for nxt in current.neighbors8():
            if not ok(nxt):
                continue
            tentative = g_score[current] + 1
            if tentative >= g_score.get(nxt, 1_000_000_000):
                continue
            came_from[nxt] = current
            g_score[nxt] = tentative
            counter += 1
            f = tentative + chebyshev(nxt, goal)
            heapq.heappush(open_heap, (f, counter, nxt))
    return None


def path_length(path: list[Tile] | None) -> int:
    if not path or len(path) < 2:
        return 0
    return len(path) - 1
