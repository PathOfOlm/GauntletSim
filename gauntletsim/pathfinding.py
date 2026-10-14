"""Grid pathfinding on discovered / lit rooms."""

from __future__ import annotations

from collections import deque

from gauntletsim.room import Coord, Room, orthogonal_neighbors


def is_passable(room: Room, *, require_discovered: bool = True) -> bool:
    if not room.exists:
        return False
    if require_discovered and not room.discovered:
        return False
    return True


def bfs_distances(
    rooms: dict[Coord, Room],
    start: Coord,
    *,
    width: int = 7,
    height: int = 7,
    require_discovered: bool = True,
) -> dict[Coord, int]:
    """Shortest path lengths in rooms from start (orthogonal)."""
    if start not in rooms or not is_passable(
        rooms[start], require_discovered=require_discovered
    ):
        return {}
    dist = {start: 0}
    q: deque[Coord] = deque([start])
    while q:
        cur = q.popleft()
        for n in orthogonal_neighbors(cur, width, height):
            if n in dist or n not in rooms:
                continue
            if not is_passable(rooms[n], require_discovered=require_discovered):
                continue
            dist[n] = dist[cur] + 1
            q.append(n)
    return dist


def shortest_path(
    rooms: dict[Coord, Room],
    start: Coord,
    goal: Coord,
    *,
    width: int = 7,
    height: int = 7,
    require_discovered: bool = True,
) -> list[Coord] | None:
    if start == goal:
        return [start]
    if start not in rooms or goal not in rooms:
        return None
    parent: dict[Coord, Coord | None] = {start: None}
    q: deque[Coord] = deque([start])
    while q:
        cur = q.popleft()
        for n in orthogonal_neighbors(cur, width, height):
            if n in parent or n not in rooms:
                continue
            if not is_passable(rooms[n], require_discovered=require_discovered):
                continue
            parent[n] = cur
            if n == goal:
                path = [goal]
                while path[-1] != start:
                    prev = parent[path[-1]]
                    assert prev is not None
                    path.append(prev)
                path.reverse()
                return path
            q.append(n)
    return None


def reachable_coords(
    rooms: dict[Coord, Room],
    start: Coord,
    *,
    width: int = 7,
    height: int = 7,
) -> set[Coord]:
    return set(
        bfs_distances(
            rooms, start, width=width, height=height, require_discovered=True
        )
    )
