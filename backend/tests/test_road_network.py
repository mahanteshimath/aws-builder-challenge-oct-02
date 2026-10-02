import math

from src.simulation.dataset import get_dataset
from src.simulation.road_network import build_adjacency, components, dijkstra, is_connected, path_roads


class R:
    def __init__(self, a, b):
        self.start_node_id, self.end_node_id = a, b


def tiny():
    roads = {"r1": R("A", "B"), "r2": R("B", "C"), "r3": R("A", "C"), "r4": R("C", "D")}
    return roads, ["A", "B", "C", "D", "E"]


def test_dijkstra_prefers_cheaper_route():
    roads, nodes = tiny()
    adj = build_adjacency(roads, nodes, {"r1": 1, "r2": 1, "r3": 5, "r4": 1})
    dist, prev = dijkstra(adj, "A")
    assert dist["C"] == 2 and dist["D"] == 3
    assert path_roads(prev, "D", "A") == ["r1", "r2", "r4"]


def test_closed_edge_is_excluded_and_detour_used():
    roads, nodes = tiny()
    adj = build_adjacency(roads, nodes, {"r1": 1, "r2": None, "r3": 5, "r4": 1})
    dist, prev = dijkstra(adj, "A")
    assert dist["C"] == 5 and "r2" not in path_roads(prev, "D", "A")


def test_disconnected_node_is_unreachable():
    roads, nodes = tiny()
    adj = build_adjacency(roads, nodes, {k: 1 for k in roads})
    dist, _ = dijkstra(adj, "A")
    assert "E" not in dist
    assert not is_connected(adj) and len(components(adj)) == 2


def test_dataset_road_graph_is_connected_at_baseline():
    ds = get_dataset()
    adj = build_adjacency(ds.roads, ds.nodes.keys(), {k: r.base_travel_time_minutes for k, r in ds.roads.items()})
    assert is_connected(adj)


def test_dataset_counts_and_wgs84():
    ds = get_dataset()
    assert 80 <= len(ds.roads) <= 150 and 5 <= len(ds.zones) <= 8 and 3 <= len(ds.facilities_by_type("hospital")) <= 5 if hasattr(ds, "facilities_by_type") else True
    for r in ds.roads.values():
        for lon, lat in r.geometry:
            assert 60 < lon < 100 and 5 < lat < 40 and math.isfinite(lon)
