"""Deterministic generator for the synthetic "Sahyadri Resilience District" dataset.

ALL DATA PRODUCED HERE IS SYNTHETIC AND ILLUSTRATIVE. It is not official municipal data.
Run:  python backend/src/data/generate_demo_data.py
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

SEED = 20261002
DATASET_VERSION = "sahyadri-synthetic-1.0"
ORIGIN_LON, ORIGIN_LAT = 73.400, 18.720
DX, DY = 0.0105, 0.0090  # degrees per grid cell (~1.1 km x ~1.0 km)
COLS, ROWS = 9, 7

OUT = Path(__file__).resolve().parent / "geojson"

RIVER = [(0.0, 5.3), (1.8, 4.6), (3.2, 3.7), (4.8, 3.2), (6.4, 2.2), (8.0, 1.2)]
BASINS = [(1.4, 1.3, 0.9, 0.30), (6.3, 5.3, 0.8, 0.28)]  # (c, r, sigma, depth)

SPEED_KMH = {"arterial": 35, "collector": 25, "local": 15, "bridge": 25}
REPAIR_COST = {"arterial": 4.0, "collector": 2.5, "local": 1.2, "bridge": 7.0}  # INR lakh (illustrative)
TYPE_THRESHOLD_BONUS = {"arterial": 0.05, "collector": 0.0, "local": -0.03, "bridge": 0.12}


def lonlat(c: float, r: float) -> list[float]:
    return [round(ORIGIN_LON + c * DX, 6), round(ORIGIN_LAT + r * DY, 6)]


def hav(a: list[float], b: list[float]) -> float:
    R = 6371000.0
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    dphi = p2 - p1
    dl = math.radians(b[0] - a[0])
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    t = 0 if dx == dy == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def river_dist(c: float, r: float) -> float:
    return min(seg_dist((c, r), RIVER[i], RIVER[i + 1]) for i in range(len(RIVER) - 1))


def elevation(c: float, r: float) -> float:
    d = river_dist(c, r)
    e = 0.12 + 0.88 * (1 - math.exp(-d / 1.3)) + 0.04 * r / ROWS
    for bc, br, s, depth in BASINS:
        e -= depth * math.exp(-((c - bc) ** 2 + (r - br) ** 2) / (2 * s * s))
    return max(0.02, min(1.0, e))


def susceptibility(e: float) -> float:
    return round(max(0.03, min(0.98, (1 - e) * 1.15)), 3)


def seg_intersect(p1, p2, p3, p4) -> bool:
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)


def crosses_river(a, b) -> bool:
    return any(seg_intersect(a, b, RIVER[i], RIVER[i + 1]) for i in range(len(RIVER) - 1))


def connected(nodes: list[str], edges: list[tuple[str, str]]) -> bool:
    adj: dict[str, list[str]] = {n: [] for n in nodes}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    seen = {nodes[0]}
    stack = [nodes[0]]
    while stack:
        for m in adj[stack.pop()]:
            if m not in seen:
                seen.add(m)
                stack.append(m)
    return len(seen) == len(nodes)


def fc(features: list[dict], name: str) -> dict:
    return {
        "type": "FeatureCollection",
        "name": name,
        "properties": {"synthetic": True, "dataset_version": DATASET_VERSION,
                       "notice": "Synthetic demonstration data. Not official or real."},
        "features": features,
    }


def feat(geom_type: str, coords, props: dict, fid: str) -> dict:
    return {"type": "Feature", "id": fid, "properties": {"id": fid, **props},
            "geometry": {"type": geom_type, "coordinates": coords}}


def ellipse(cc, cr, rx, ry, n=28):
    pts = [lonlat(cc + rx * math.cos(2 * math.pi * i / n), cr + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]
    pts.append(pts[0])
    return [pts]


def rect(c0, r0, c1, r1):
    pts = [lonlat(c0, r0), lonlat(c1, r0), lonlat(c1, r1), lonlat(c0, r1), lonlat(c0, r0)]
    return [pts]


def generate() -> dict[str, dict]:
    rnd = random.Random(SEED)

    # ---- nodes -----------------------------------------------------------
    node_ids: dict[tuple[int, int], str] = {}
    node_pos: dict[str, list[float]] = {}
    node_grid: dict[str, tuple[int, int]] = {}
    for r in range(ROWS):
        for c in range(COLS):
            nid = f"N-{r}{c}"
            jx = 0 if c in (0, COLS - 1) else rnd.uniform(-0.12, 0.12)
            jy = 0 if r in (0, ROWS - 1) else rnd.uniform(-0.12, 0.12)
            node_ids[(r, c)] = nid
            node_pos[nid] = lonlat(c + jx, r + jy)
            node_grid[nid] = (r, c)

    major = {(3, 4): "Central Chowk", (3, 2): "Riverside Junction", (3, 6): "Eastgate Junction", (1, 4): "North Market Junction",
             (5, 4): "Hilltop Junction", (1, 2): "Lake Road Junction", (1, 6): "Canal Junction", (5, 2): "West Ridge Junction",
             (5, 6): "Hillview Junction", (3, 0): "West Gate", (3, 8): "East Gate", (0, 4): "South Gate", (6, 4): "North Gate"}
    node_feats = []
    for nid, pos in node_pos.items():
        r, c = node_grid[nid]
        node_feats.append(feat("Point", pos, {"name": major.get((r, c), nid), "is_major": (r, c) in major, "grid": [r, c]}, nid))

    # ---- candidate edges ---------------------------------------------------
    def road_class(a, b):
        (r1, c1), (r2, c2) = a, b
        if r1 == r2:  # horizontal
            r = r1
            return "arterial" if r == 3 else "collector" if r in (1, 5) else "local"
        c = c1
        return "arterial" if c == 4 else "collector" if c in (2, 6) else "local"

    cand = []
    for r in range(ROWS):
        for c in range(COLS):
            if c + 1 < COLS:
                cand.append(((r, c), (r, c + 1)))
            if r + 1 < ROWS:
                cand.append(((r, c), (r + 1, c)))

    kept, removed_pool = [], []
    collectors_crossing = 0
    for a, b in cand:
        cls = road_class(a, b)
        ga, gb = (a[1], a[0]), (b[1], b[0])
        if crosses_river(ga, gb):
            if cls == "arterial":
                kept.append((a, b, "bridge" if True else cls, cls))
            elif cls == "collector" and collectors_crossing < 2:
                collectors_crossing += 1
                kept.append((a, b, "bridge", cls))
            # all other river crossings removed (river is a real barrier)
            continue
        if cls == "local" and rnd.random() < 0.16:
            removed_pool.append((a, b, cls, cls))
            continue
        kept.append((a, b, cls, cls))
    ids = list(node_ids.values())
    while not connected(ids, [(node_ids[a], node_ids[b]) for a, b, _, _ in kept]):
        kept.append(removed_pool.pop(0))

    road_feats = []
    for i, (a, b, rtype, _cls) in enumerate(kept, start=1):
        rid = f"R-{i:03d}"
        pa, pb = node_pos[node_ids[a]], node_pos[node_ids[b]]
        mid_c = ((a[1] + b[1]) / 2)
        mid_r = ((a[0] + b[0]) / 2)
        off = 0 if rtype in ("arterial", "bridge") else rnd.uniform(-0.07, 0.07)
        if a[0] == b[0]:
            mid = lonlat(mid_c, mid_r + off)
        else:
            mid = lonlat(mid_c + off, mid_r)
        length = hav(pa, mid) + hav(mid, pb)
        e = elevation(mid_c, mid_r)
        susc = susceptibility(e)
        drain = round(max(0.2, min(0.95, rnd.uniform(0.45, 0.9) - 0.25 * susc)), 3)
        speed = SPEED_KMH[rtype]
        tt = length / 1000 / speed * 60
        cost = round(REPAIR_COST[rtype] * max(0.6, length / 1000), 2)
        road_feats.append(feat("LineString", [pa, mid, pb], {
            "start_node_id": node_ids[a], "end_node_id": node_ids[b], "road_type": rtype,
            "name": f"{'Bridge' if rtype == 'bridge' else 'Road'} {rid}",
            "length_m": round(length, 1), "base_travel_time_minutes": round(tt, 3),
            "flood_susceptibility": susc, "elevation_proxy": round(e, 3), "drainage_score": drain,
            "power_dependency": None, "current_status": "open", "closure_reason": None,
            "estimated_repair_cost": cost, "criticality_score": 0.0,
            "threshold_bonus": TYPE_THRESHOLD_BONUS[rtype],
        }, rid))

    # ---- power & drainage infrastructure ------------------------------------
    power_spec = [  # id, name, grid node (r,c), kind
        ("P-01", "Central Substation", (3, 4), "substation"),
        ("P-02", "Riverside Substation", (4, 2), "substation"),
        ("P-03", "Eastgate Transformer", (2, 7), "transformer"),
        ("P-04", "Hillview Transformer", (5, 6), "transformer"),
    ]
    infra_feats = []
    power_pos = {}
    for pid, name, (r, c), kind in power_spec:
        e = elevation(c, r)
        power_pos[pid] = node_pos[node_ids[(r, c)]]
        infra_feats.append(feat("Point", lonlat(c + 0.08, r + 0.08), {
            "infra_type": "power", "name": name, "kind": kind, "node_id": node_ids[(r, c)],
            "elevation_proxy": round(e, 3), "flood_susceptibility": susceptibility(e),
            "backup_power_available": False}, pid))
    drain_spec = [  # id, name, grid pos, power node, backup
        ("D-01", "Riverside Pump Station", (2.0, 4.4), "P-02", False),
        ("D-02", "Old Town Pump Station", (3.4, 3.5), "P-01", True),
        ("D-03", "Canal Sluice Pump", (5.6, 2.7), "P-03", False),
        ("D-04", "Lake Basin Pump", (1.5, 1.5), "P-02", False),
        ("D-05", "Hillview Drain Pump", (6.2, 5.0), "P-04", False),
        ("D-06", "Eastgate Storm Drain", (7.4, 1.8), "P-03", False),
    ]
    drain_assets = []
    for did, name, (c, r), pn, backup in drain_spec:
        infra_feats.append(feat("Point", lonlat(c, r), {
            "infra_type": "drainage", "name": name, "power_node_id": pn, "backup_power_available": backup,
            "effectiveness_radius_m": 1700.0, "drainage_boost": 0.35}, did))
        drain_assets.append(did)

    # ---- facilities -----------------------------------------------------------
    def fac(fid, name, ftype, rc, cap, power_dep, backup, backup_h, pnode, crit, min_acc):
        r, c = rc
        nid = node_ids[(r, c)]
        p = node_pos[nid]
        return feat("Point", [round(p[0] + 0.0012, 6), round(p[1] + 0.0010, 6)], {
            "name": name, "facility_type": ftype, "capacity": cap, "operational_status": "operational",
            "power_dependent": power_dep, "backup_power_available": backup, "backup_power_hours": backup_h,
            "power_node_id": pnode, "node_id": nid, "minimum_accessibility_requirement": min_acc,
            "criticality_score": crit}, fid)

    facs = [
        fac("H-01", "Sahyadri Civil Hospital", "hospital", (3, 4), 220, True, True, 24, "P-01", 1.0, 20),
        fac("H-02", "Riverside General Hospital", "hospital", (4, 2), 150, True, True, 8, "P-02", 0.9, 20),
        fac("H-03", "Eastgate Community Clinic", "hospital", (2, 7), 40, True, False, 0, "P-03", 0.6, 20),
        fac("H-04", "Hillview Maternity & Child Clinic", "hospital", (5, 6), 60, True, True, 12, "P-04", 0.75, 20),
        fac("S-01", "Lake Road School Shelter", "shelter", (1, 1), 400, False, False, 0, None, 0.6, 25),
        fac("S-02", "West Ridge Community Hall", "shelter", (5, 1), 350, False, False, 0, None, 0.6, 25),
        fac("S-03", "Eastgate Sports Complex", "shelter", (3, 6), 500, True, False, 0, "P-03", 0.7, 25),
        fac("S-04", "Canal Junction Temple Hall", "shelter", (1, 5), 300, False, False, 0, None, 0.5, 25),
        fac("S-05", "North Gate Community Centre", "shelter", (6, 4), 250, False, False, 0, None, 0.5, 25),
        fac("S-06", "Old Town Municipal Hall", "shelter", (2, 3), 200, True, True, 10, "P-01", 0.5, 25),
        fac("W-01", "Lake Road Water Point", "water", (1, 2), 1500, False, False, 0, None, 0.5, 15),
        fac("W-02", "Riverside Water Point", "water", (4, 3), 1800, True, False, 0, "P-02", 0.55, 15),
        fac("W-03", "Central Water Point", "water", (3, 5), 2200, True, True, 12, "P-01", 0.6, 15),
        fac("W-04", "Eastgate Water Point", "water", (2, 6), 1500, True, False, 0, "P-03", 0.5, 15),
        fac("W-05", "Hillview Water Point", "water", (5, 5), 1400, False, False, 0, None, 0.5, 15),
        fac("W-06", "West Ridge Water Point", "water", (5, 1), 1200, False, False, 0, None, 0.45, 15),
        fac("E-01", "Central Fire Station", "emergency", (3, 3), 30, False, False, 0, None, 0.8, 15),
        fac("E-02", "Police Control Post", "emergency", (2, 5), 25, True, True, 12, "P-01", 0.6, 15),
        fac("E-03", "Ambulance Dispatch Hub", "emergency", (4, 5), 20, True, True, 12, "P-04", 0.85, 15),
        fac("E-04", "District Emergency Operations Centre", "emergency", (5, 3), 40, True, True, 24, "P-02", 0.9, 15),
        fac("E-05", "Disaster Response Post", "emergency", (1, 7), 35, False, False, 0, None, 0.7, 15),
        fac("SC-01", "Lake Road Primary School", "school", (1, 0), 450, False, False, 0, None, 0.3, 30),
        fac("SC-02", "Old Town High School", "school", (2, 2), 700, False, False, 0, None, 0.3, 30),
        fac("SC-03", "Riverside Primary School", "school", (4, 1), 400, False, False, 0, None, 0.3, 30),
        fac("SC-04", "Central Public School", "school", (3, 5), 800, False, False, 0, None, 0.3, 30),
        fac("SC-05", "Eastgate School", "school", (3, 7), 500, False, False, 0, None, 0.3, 30),
        fac("SC-06", "Canal Road School", "school", (1, 6), 380, False, False, 0, None, 0.3, 30),
        fac("SC-07", "Hillview Public School", "school", (5, 5), 420, False, False, 0, None, 0.3, 30),
        fac("SC-08", "North Gate School", "school", (6, 3), 350, False, False, 0, None, 0.3, 30),
    ]

    # ---- population zones ----------------------------------------------------------
    zone_spec = [
        ("Z-01", "Lake Basin Colony", (0, 0, 2, 3), 9800, 1.25, 1.1, (1, 1)),
        ("Z-02", "Old Town", (2, 0, 4, 3), 13500, 1.10, 1.2, (1, 3)),
        ("Z-03", "Canal Ward", (4, 0, 6, 3), 8600, 1.00, 1.0, (1, 5)),
        ("Z-04", "Eastgate Village", (6, 0, 8, 3), 7200, 1.15, 1.1, (2, 7)),
        ("Z-05", "West Ridge", (0, 3, 2, 6), 6400, 0.95, 1.0, (5, 1)),
        ("Z-06", "Riverside Colony", (2, 3, 4, 6), 11200, 1.35, 1.25, (4, 3)),
        ("Z-07", "Hilltop Residential", (4, 3, 6, 6), 7800, 0.85, 0.95, (5, 4)),
        ("Z-08", "Hillview Hamlet", (6, 3, 8, 6), 5600, 1.05, 1.15, (5, 6)),
    ]
    zone_feats = []
    for zid, name, (c0, r0, c1, r1), pop, vuln, mob, anchor in zone_spec:
        zone_feats.append(feat("Polygon", rect(c0 + 0.03, r0 + 0.03, c1 - 0.03, r1 - 0.03), {
            "name": name, "estimated_population": pop, "vulnerability_weight": vuln,
            "mobility_constraint_factor": mob, "anchor_node_id": node_ids[anchor],
            "bbox_grid": [c0, r0, c1, r1], "nearest_facility_ids": []}, zid))

    # ---- hazard zones (candidate flood-prone areas) -------------------------------------
    hz_spec = [
        ("HZ-01", "Riverside Floodplain", (2.2, 4.2, 1.25, 0.85), 0.55, 1.0),
        ("HZ-02", "Old Town River Bend", (4.0, 3.4, 1.25, 0.75), 0.50, 1.0),
        ("HZ-03", "Canal Low Ground", (5.8, 2.6, 1.1, 0.8), 0.55, 0.95),
        ("HZ-04", "Eastgate Wetland", (7.3, 1.6, 1.0, 0.8), 0.60, 0.9),
        ("HZ-05", "Lake Basin", (1.4, 1.3, 1.0, 0.8), 0.45, 1.0),
        ("HZ-06", "Hillview Depression", (6.3, 5.3, 0.9, 0.7), 0.50, 0.85),
    ]
    hz_feats = []
    for hid, name, (c, r, rx, ry), drain, expo in hz_spec:
        susc = susceptibility(elevation(c, r))
        hz_feats.append(feat("Polygon", ellipse(c, r, rx, ry), {
            "name": name, "susceptibility_score": susc, "estimated_water_accumulation": round(susc * 0.9, 3),
            "drainage_effectiveness": drain, "exposure_factor": expo,
            "center": lonlat(c, r), "radii_grid": [rx, ry], "center_grid": [c, r]}, hid))

    # ---- staging locations / emergency resources -----------------------------------------
    stg_spec = [("STG-1", "North Depot", (6, 4)), ("STG-2", "Central Depot", (3, 3)),
                ("STG-3", "East Depot", (2, 6)), ("STG-4", "West Depot", (5, 1)), ("STG-5", "South Depot", (0, 4))]
    stg_feats = []
    for sid, name, (r, c) in stg_spec:
        p = node_pos[node_ids[(r, c)]]
        stg_feats.append(feat("Point", [round(p[0] - 0.0012, 6), round(p[1] - 0.001, 6)],
                              {"name": name, "node_id": node_ids[(r, c)]}, sid))
    res_spec = [
        ("RES-RC1", "Road Clearance Team A", "road_clearance_team", "STG-1", 1, 4500, 1.5, 30, 1),
        ("RES-RC2", "Road Clearance Team B", "road_clearance_team", "STG-2", 1, 4500, 1.5, 30, 1),
        ("RES-GEN1", "Portable Generator Pool C", "portable_generator", "STG-2", 2, 6000, 2.0, 20, 1),
        ("RES-GEN2", "Portable Generator Pool E", "portable_generator", "STG-3", 1, 6000, 2.0, 20, 1),
        ("RES-MED1", "Temporary Medical Unit", "temporary_medical_unit", "STG-4", 1, 9000, 9.0, 60, 60),
        ("RES-WAT1", "Water Distribution Unit", "water_distribution_unit", "STG-5", 2, 9000, 3.5, 45, 1500),
        ("RES-SHL1", "Temporary Shelter Kit", "temporary_shelter_kit", "STG-3", 2, 9000, 4.0, 50, 250),
    ]
    res_feats = []
    stg_map = {f["id"]: f for f in stg_feats}
    for rid, name, rtype, stg, qty, radius, cost, mins, cap in res_spec:
        res_feats.append(feat("Point", stg_map[stg]["geometry"]["coordinates"], {
            "name": name, "resource_type": rtype, "staging_id": stg, "node_id": stg_map[stg]["properties"]["node_id"],
            "quantity_available": qty, "response_radius": radius, "deployment_cost": cost,
            "deployment_time_minutes": mins, "service_capacity": cap}, rid))

    boundary = feat("Polygon", rect(-0.25, -0.25, COLS - 0.75, ROWS - 0.75), {
        "name": "Sahyadri Resilience District (fictional, synthetic)", "notice": "Synthetic demonstration geography"}, "BOUNDARY")
    river = feat("LineString", [lonlat(c, r) for c, r in RIVER], {"name": "Sahya Nadi (fictional river)"}, "RIVER-1")

    return {
        "roads": fc(road_feats, "roads"), "nodes": fc(node_feats, "nodes"), "facilities": fc(facs, "facilities"),
        "zones": fc(zone_feats, "population_zones"), "hazards": fc(hz_feats, "hazard_zones"),
        "infrastructure": fc(infra_feats, "infrastructure"), "staging": fc(stg_feats, "staging"),
        "resources": fc(res_feats, "resources"), "boundary": fc([boundary], "boundary"), "river": fc([river], "river"),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = generate()
    for name, coll in data.items():
        (OUT / f"{name}.geojson").write_text(json.dumps(coll, separators=(",", ":")), encoding="utf-8")
    manifest = {"dataset_version": DATASET_VERSION, "seed": SEED, "synthetic": True,
                "label": "Sahyadri Resilience District - fictional, synthetic demonstration data",
                "counts": {k: len(v["features"]) for k, v in data.items()}}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest["counts"]))


if __name__ == "__main__":
    main()

