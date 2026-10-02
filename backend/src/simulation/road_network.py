"""Graph construction and shortest-path routines (Dijkstra) on the road network."""
from __future__ import annotations

import heapq
import math
from typing import Optional

Adjacency = dict[str, list[tuple[str, float, str]]]


def haversine_m(a: list[float], b: list[float]) -> float:
    r = 6371000.0
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[0] - a[0]) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def build_adjacency(roads: dict, node_ids, travel_minutes: dict[str, Optional[float]]) -> Adjacency:
    """Undirected graph. Roads whose travel time is None (closed) are excluded entirely."""
    adj: Adjacency = {n: [] for n in node_ids}
    for rid, road in roads.items():
        w = travel_minutes.get(rid)
        if w is None:
            continue
        adj[road.start_node_id].append((road.end_node_id, w, rid))
        adj[road.end_node_id].append((road.start_node_id, w, rid))
    return adj


def dijkstra(adj: Adjacency, source: str, exclude_road: Optional[str] = None):
    dist: dict[str, float] = {source: 0.0}
    prev: dict[str, tuple[str, str]] = {}
    heap = [(0.0, source)]
    done = set()
    while heap:
        d, u = heapq.heappop(heap)
        if u in done:
            continue
        done.add(u)
        for v, w, rid in adj[u]:
            if rid == exclude_road:
                continue
            nd = d + w
            if nd < dist.get(v, math.inf) - 1e-12:
                dist[v] = nd
                prev[v] = (u, rid)
                heapq.heappush(heap, (nd, v))
    return dist, prev


def path_roads(prev: dict, target: str, source: str) -> list[str]:
    out: list[str] = []
    cur = target
    while cur != source:
        if cur not in prev:
            return []
        cur, rid = prev[cur][0], prev[cur][1]
        out.append(rid)
    out.reverse()
    return out


def components(adj: Adjacency) -> list[set[str]]:
    seen: set[str] = set()
    comps = []
    for n in adj:
        if n in seen:
            continue
        stack, comp = [n], {n}
        while stack:
            u = stack.pop()
            for v, _, _ in adj[u]:
                if v not in comp:
                    comp.add(v)
                    stack.append(v)
        seen |= comp
        comps.append(comp)
    return comps


def is_connected(adj: Adjacency) -> bool:
    return len(components(adj)) == 1
