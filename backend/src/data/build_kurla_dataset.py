"""Deterministic builder for the Kurla / Mithi River study area (Mumbai, BMC Ward L) dataset.

REAL inputs (cached in backend/data_sources/, re-fetch with --refresh):
  * Road network, bridges, flyovers, Mithi River, facilities, substations, pumping stations and
    neighbourhood names: (c) OpenStreetMap contributors, ODbL 1.0 (Overpass API).
  * Terrain: SRTM 30 m (NASA/USGS, public domain) via OpenTopoData.
  * Population density: Census of India 2011, BMC Ward L = 892,278 people on 13.46 km^2
    (as listed in Wikipedia "Administrative divisions of Mumbai").
MODELED (planning assumptions, clearly labelled in the output): zone boundaries (Voronoi of OSM
neighbourhood points), zone populations (Ward L density x land-use share), facility capacities,
backup power, power-dependency links, drainage-pump effectiveness, response resources and costs.
This is NOT an official BMC/MCGM dataset and NOT a flood forecast.

Run:  python backend/src/data/build_kurla_dataset.py [--refresh]
"""
from __future__ import annotations

import json
import math
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

DATASET_VERSION = "kurla-mithi-osm-1.0"
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "backend" / "data_sources"
OUT = Path(__file__).resolve().parent / "geojson"

# Study area: Kurla West / Kurla East / Kalina / Bail Bazar / Tilak Nagar, Mithi River on the west side.
S, W, N, E = 19.0595, 72.8600, 19.0905, 72.8990
WARD_L_POP, WARD_L_KM2 = 892_278, 13.46
DENSITY = WARD_L_POP / WARD_L_KM2  # people per km^2 (Census 2011)

SPEED_KMH = {"arterial": 30, "collector": 22, "local": 15, "bridge": 22}  # monsoon-traffic planning speeds
REPAIR_COST = {"arterial": 4.0, "collector": 2.5, "local": 1.2, "bridge": 7.0}  # INR lakh per km (illustrative)
TYPE_THRESHOLD_BONUS = {"arterial": 0.05, "collector": 0.0, "local": -0.03, "bridge": 0.12}
CLASS_OF = {"motorway": "arterial", "trunk": "arterial", "primary": "arterial", "secondary": "collector",
            "tertiary": "local", "unclassified": "local"}
RANK = {"motorway": 0, "trunk": 0, "primary": 1, "secondary": 2, "tertiary": 3, "unclassified": 4}
CLUSTER_M = 120.0
LICENSE = "Roads, river, facilities and place names (c) OpenStreetMap contributors, ODbL 1.0. Terrain: SRTM 30 m (public domain)."
NOTICE = ("Real geography of Kurla / Mithi River, Mumbai (OpenStreetMap + SRTM). Populations, capacities, power links, "
          "pumps and resources are MODELED planning assumptions - not official BMC data, not a flood forecast.")

OVERPASS = ["https://overpass-api.de/api/interpreter", "https://z.overpass-api.de/api/interpreter"]


# ------------------------------------------------------------------------------------------- helpers
def hav(a, b) -> float:
    r = 6371000.0
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[0] - a[0]) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def inside(lon, lat) -> bool:
    return W <= lon <= E and S <= lat <= N


def rnd(p):
    return [round(p[0], 6), round(p[1], 6)]


def seg_intersect(p1, p2, p3, p4) -> bool:
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)


def point_seg_m(p, a, b) -> float:
    kx = 111320 * math.cos(math.radians(p[1]))
    ky = 110540
    ax, ay, bx, by, px, py = a[0] * kx, a[1] * ky, b[0] * kx, b[1] * ky, p[0] * kx, p[1] * ky
    dx, dy = bx - ax, by - ay
    t = 0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def dist_to_line(p, line) -> float:
    return min(point_seg_m(p, line[i], line[i + 1]) for i in range(len(line) - 1))


def point_in_poly(p, ring) -> bool:
    x, y, c = p[0], p[1], False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi, xj, yj = ring[i][0], ring[i][1], ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi:
            c = not c
        j = i
    return c


def resample(line, n=7):
    """Evenly spaced points along a polyline (keeps endpoints); the middle point is the road's midpoint."""
    seg = [hav(line[i], line[i + 1]) for i in range(len(line) - 1)]
    total = sum(seg) or 1.0
    out, acc, i = [], 0.0, 0
    for k in range(n):
        target = total * k / (n - 1)
        while i < len(seg) - 1 and acc + seg[i] < target:
            acc += seg[i]
            i += 1
        t = 0 if seg[i] == 0 else min(1.0, max(0.0, (target - acc) / seg[i]))
        a, b = line[i], line[i + 1]
        out.append(rnd([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]))
    return out


def fc(features, name):
    return {"type": "FeatureCollection", "name": name,
            "properties": {"synthetic": False, "modeled_attributes": True, "dataset_version": DATASET_VERSION,
                           "notice": NOTICE, "license": LICENSE}, "features": features}


def feat(geom_type, coords, props, fid):
    return {"type": "Feature", "id": fid, "properties": {"id": fid, **props}, "geometry": {"type": geom_type, "coordinates": coords}}


# ------------------------------------------------------------------------------------------- sources
def _overpass(q: str) -> dict:
    for url in OVERPASS:
        for _ in range(2):
            try:
                req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": q}).encode(),
                                             headers={"User-Agent": "resilience-simulator/1.0 (dataset build)"})
                with urllib.request.urlopen(req, timeout=200) as r:
                    return json.loads(r.read())
            except Exception as exc:  # pragma: no cover - network
                print("overpass retry", url, repr(exc)[:100])
                time.sleep(5)
    raise RuntimeError("Overpass unavailable")


def refresh_sources() -> None:  # pragma: no cover - network, run manually
    SRC.mkdir(parents=True, exist_ok=True)
    bb = "(19.052,72.852,19.094,72.900)"
    q = f"""[out:json][timeout:180];
(way["highway"~"^(motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|unclassified)$"]{bb};
 way["waterway"~"^(river|canal|stream|drain)$"]{bb};);
out body geom;
(nwr["amenity"~"^(hospital|clinic|school|college|community_centre|fire_station|police|townhall|drinking_water|social_facility|place_of_worship)$"]{bb};
 nwr["healthcare"="hospital"]{bb}; nwr["power"~"^(substation|plant)$"]{bb};
 nwr["man_made"~"^(pumping_station|water_tower|water_works|wastewater_plant|reservoir_covered)$"]{bb};
 node["place"~"^(suburb|neighbourhood|quarter|locality)$"]{bb}; nwr["railway"="station"]{bb};);
out center tags;"""
    (SRC / "osm_kurla_raw.json").write_text(json.dumps(_overpass(q)), encoding="utf-8")
    b2 = f"({S},{W},{N},{E})"
    q2 = f"""[out:json][timeout:180];(way["landuse"]{b2};way["aeroway"="aerodrome"]{b2};relation["aeroway"="aerodrome"]{b2};
way["leisure"~"^(park|pitch|garden|playground)$"]{b2};way["natural"~"^(water|wetland|scrub)$"]{b2};);out body geom;"""
    (SRC / "osm_kurla_landuse.json").write_text(json.dumps(_overpass(q2)), encoding="utf-8")
    ny, nx = 22, 28
    lats = [S + (N - S) * i / (ny - 1) for i in range(ny)]
    lons = [W + (E - W) * j / (nx - 1) for j in range(nx)]
    pts = [(la, lo) for la in lats for lo in lons]
    elev = []
    for i in range(0, len(pts), 100):
        loc = "|".join(f"{a:.5f},{b:.5f}" for a, b in pts[i:i + 100])
        req = urllib.request.Request("https://api.opentopodata.org/v1/srtm30m?locations=" + loc, headers={"User-Agent": "resilience-simulator/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            elev += [x["elevation"] for x in json.loads(r.read())["results"]]
        time.sleep(1.1)
    grid = [elev[r * nx:(r + 1) * nx] for r in range(ny)]
    (SRC / "srtm_kurla.json").write_text(json.dumps({"source": "SRTM 30 m via OpenTopoData", "bbox": [W, S, E, N],
                                                     "lats": lats, "lons": lons, "elev": grid}), encoding="utf-8")


class Terrain:
    def __init__(self, d: dict):
        self.lats, self.lons, self.z = d["lats"], d["lons"], d["elev"]
        flat = sorted(v for row in self.z for v in row)
        self.sorted = flat

    def elev(self, p) -> float:
        lon, lat = p
        fy = (lat - self.lats[0]) / (self.lats[-1] - self.lats[0]) * (len(self.lats) - 1)
        fx = (lon - self.lons[0]) / (self.lons[-1] - self.lons[0]) * (len(self.lons) - 1)
        fy = max(0.0, min(len(self.lats) - 1.001, fy))
        fx = max(0.0, min(len(self.lons) - 1.001, fx))
        i, j = int(fy), int(fx)
        ty, tx = fy - i, fx - j
        z = self.z
        return (z[i][j] * (1 - tx) * (1 - ty) + z[i][j + 1] * tx * (1 - ty) + z[i + 1][j] * (1 - tx) * ty + z[i + 1][j + 1] * tx * ty)

    def smooth(self, p, r_m=220.0) -> float:
        """Neighbourhood mean (SRTM is noisy at single-cell scale in dense built-up areas)."""
        dlat = r_m / 110540
        dlon = r_m / (111320 * math.cos(math.radians(p[1])))
        pts = [p] + [[p[0] + dlon * math.cos(a), p[1] + dlat * math.sin(a)] for a in [k * math.pi / 4 for k in range(8)]]
        return sum(self.elev(q) for q in pts) / len(pts)

    def pct(self, v) -> float:
        lo, hi = 0, len(self.sorted)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.sorted[mid] < v:
                lo = mid + 1
            else:
                hi = mid
        return lo / len(self.sorted)


# ------------------------------------------------------------------------------------------- build
def build() -> dict:
    osm = json.loads((SRC / "osm_kurla_raw.json").read_text(encoding="utf-8"))
    lu = json.loads((SRC / "osm_kurla_landuse.json").read_text(encoding="utf-8"))
    terrain = Terrain(json.loads((SRC / "srtm_kurla.json").read_text(encoding="utf-8")))
    els = osm["elements"]

    mithi_ways = [e for e in els if e["type"] == "way" and e.get("tags", {}).get("name") == "Mithi River"]
    mithi_main = max(mithi_ways, key=lambda e: len(e["geometry"]))
    river = [[g["lon"], g["lat"]] for g in mithi_main["geometry"]]
    river_in = [p for p in river if W - 0.004 <= p[0] <= E and S - 0.004 <= p[1] <= N + 0.004]
    drains = [[[g["lon"], g["lat"]] for g in e["geometry"]] for e in els
              if e["type"] == "way" and e.get("tags", {}).get("waterway") in ("drain", "canal", "stream")]

    def flood_index(p) -> tuple[float, float]:
        """(elevation_proxy 0..1, susceptibility 0..1) from SRTM rank + Mithi / nala proximity."""
        e_rank = terrain.pct(terrain.smooth(p))
        d_river = dist_to_line(p, river_in)
        d_drain = min((dist_to_line(p, d) for d in drains if len(d) >= 2), default=5000.0)
        prox = 0.70 * math.exp(-d_river / 420.0) + 0.30 * math.exp(-d_drain / 160.0)
        susc = max(0.03, min(0.98, 0.10 + 0.55 * (1 - e_rank) + 0.55 * prox))
        elev_proxy = max(0.02, min(1.0, 1.0 - susc / 1.15))
        return round(elev_proxy, 3), round(susc, 3)

    # ---- road graph ----------------------------------------------------------------------
    ways = [e for e in els if e["type"] == "way" and "highway" in e.get("tags", {})]
    coord, use, pieces = {}, Counter(), []
    for w in ways:
        run = []
        for nid, g in zip(w["nodes"], w["geometry"]):
            if inside(g["lon"], g["lat"]):
                run.append(nid)
                coord[nid] = (g["lon"], g["lat"])
            else:
                if len(run) >= 2:
                    pieces.append((w, run))
                run = []
        if len(run) >= 2:
            pieces.append((w, run))
    for _, run in pieces:
        for n in run:
            use[n] += 1
        use[run[0]] += 1
        use[run[-1]] += 1
    junction = {n for n, c in use.items() if c >= 2}
    raw_edges = []
    for w, run in pieces:
        cur = [run[0]]
        for n in run[1:]:
            cur.append(n)
            if n in junction:
                raw_edges.append((w, cur))
                cur = [n]
        if len(cur) >= 2:
            raw_edges.append((w, cur))

    ends = Counter()
    for _, run in raw_edges:
        ends[run[0]] += 1
        ends[run[-1]] += 1
    centers: list[list] = []
    cl = {}
    for n in sorted(ends, key=lambda n: (-ends[n], n)):
        p = coord[n]
        best = None
        for ci, (c, _members) in enumerate(centers):
            d = hav(p, c)
            if d < CLUSTER_M and (best is None or d < best[0]):
                best = (d, ci)
        if best:
            cl[n] = best[1]
            centers[best[1]][1].append(n)
        else:
            cl[n] = len(centers)
            centers.append([p, [n]])
    cent = [(sum(coord[m][0] for m in mem) / len(mem), sum(coord[m][1] for m in mem) / len(mem)) for _, mem in centers]

    by_pair = defaultdict(list)
    for w, run in raw_edges:
        a, b = cl[run[0]], cl[run[-1]]
        if a == b:
            continue
        geom = [coord[n] for n in run]
        length = sum(hav(geom[i], geom[i + 1]) for i in range(len(geom) - 1))
        by_pair[tuple(sorted((a, b)))].append((length, w, geom, a, b))
    simple = []
    for key in sorted(by_pair):
        lst = sorted(by_pair[key], key=lambda x: (RANK.get(x[1]["tags"]["highway"].replace("_link", ""), 9), x[0], x[1]["id"]))
        simple.append(lst[0])

    # keep the largest connected component
    nb = defaultdict(list)
    for i, (_, _, _, a, b) in enumerate(simple):
        nb[a].append(b)
        nb[b].append(a)
    seen, comps = set(), []
    for s0 in sorted(nb):
        if s0 in seen:
            continue
        stack, comp = [s0], {s0}
        while stack:
            u = stack.pop()
            for v in nb[u]:
                if v not in comp:
                    comp.add(v)
                    stack.append(v)
        seen |= comp
        comps.append(comp)
    big = max(comps, key=len)
    simple = [e for e in simple if e[3] in big]

    # contract pass-through (degree-2) nodes so segments run junction to junction
    blocked: set = set()

    def contract_all(edges):
        while True:
            deg = defaultdict(list)
            for i, e in enumerate(edges):
                deg[e[3]].append(i)
                deg[e[4]].append(i)
            cand = None
            for n in sorted(deg):
                if n in blocked or len(deg[n]) != 2:
                    continue
                e1, e2 = edges[deg[n][0]], edges[deg[n][1]]
                b1 = e1[1]["tags"].get("bridge", "no") != "no"
                b2 = e2[1]["tags"].get("bridge", "no") != "no"
                c1 = CLASS_OF.get(e1[1]["tags"]["highway"].replace("_link", ""))
                c2 = CLASS_OF.get(e2[1]["tags"]["highway"].replace("_link", ""))
                if b1 != b2 or c1 != c2 or e1[0] + e2[0] > 1400:
                    continue
                o1 = e1[4] if e1[3] == n else e1[3]
                o2 = e2[4] if e2[3] == n else e2[3]
                if o1 == o2 or any({x[3], x[4]} == {o1, o2} for x in edges):
                    blocked.add(n)
                    continue
                cand = (n, deg[n][0], deg[n][1], o1, o2)
                break
            if cand is None:
                return edges
            n, i1, i2, o1, o2 = cand
            e1, e2 = edges[i1], edges[i2]
            g1 = e1[2] if e1[4] == n else list(reversed(e1[2]))
            g2 = e2[2] if e2[3] == n else list(reversed(e2[2]))
            w = e1[1] if RANK.get(e1[1]["tags"]["highway"].replace("_link", ""), 9) <= RANK.get(e2[1]["tags"]["highway"].replace("_link", ""), 9) else e2[1]
            edges = [x for k, x in enumerate(edges) if k not in (i1, i2)] + [(e1[0] + e2[0], w, g1 + g2[1:], o1, o2)]

    simple = contract_all(simple)
    used_nodes = sorted({e[3] for e in simple} | {e[4] for e in simple}, key=lambda c: (round(-cent[c][1], 5), round(cent[c][0], 5)))
    node_id = {c: f"N-{i + 1:03d}" for i, c in enumerate(used_nodes)}
    node_pos = {node_id[c]: rnd(cent[c]) for c in used_nodes}

    # road name lookup per node (for junction names)
    node_roads = defaultdict(Counter)
    for e in simple:
        nm = e[1]["tags"].get("name")
        if nm:
            node_roads[node_id[e[3]]][nm] += 1
            node_roads[node_id[e[4]]][nm] += 1

    # sort roads deterministically north->south, west->east by midpoint
    def mid(e):
        g = e[2]
        return g[len(g) // 2]
    simple.sort(key=lambda e: (round(-mid(e)[1], 5), round(mid(e)[0], 5)))

    places = [(e["tags"]["name"], [e["lon"], e["lat"]]) for e in els
              if e["type"] == "node" and e.get("tags", {}).get("place") in ("suburb", "neighbourhood", "quarter", "locality") and e["tags"].get("name")]

    def near_place(p) -> str:
        return min(places, key=lambda kv: (hav(kv[1], p), kv[0]))[0]

    road_feats = []
    for i, (length, w, geom, a, b) in enumerate(simple, start=1):
        rid = f"R-{i:03d}"
        t = w["tags"]
        hw = t["highway"].replace("_link", "")
        rclass = CLASS_OF.get(hw, "local")
        line = [list(node_pos[node_id[a]])] + [list(p) for p in geom[1:-1]] + [list(node_pos[node_id[b]])]
        crosses_mithi = any(seg_intersect(line[k], line[k + 1], river_in[j], river_in[j + 1])
                            for k in range(len(line) - 1) for j in range(len(river_in) - 1))
        is_bridge = t.get("bridge", "no") != "no"
        elevated = is_bridge and not crosses_mithi  # flyovers / rail over-bridges
        rtype = "bridge" if (crosses_mithi or (is_bridge and rclass != "arterial")) else rclass
        length_m = max(60.0, sum(hav(line[k], line[k + 1]) for k in range(len(line) - 1)))
        mpt = line[len(line) // 2] if len(line) > 2 else [(line[0][0] + line[1][0]) / 2, (line[0][1] + line[1][1]) / 2]
        e_proxy, susc = flood_index(mpt)
        if elevated:
            susc = round(max(0.03, susc * 0.35), 3)
            e_proxy = round(min(1.0, e_proxy + 0.35), 3)
        # drainage: arterials have better side drains; low-lying segments drain worse (deterministic)
        drain = round(max(0.2, min(0.95, {"arterial": 0.78, "collector": 0.68, "local": 0.58, "bridge": 0.72}[rtype] - 0.30 * susc
                                   + 0.04 * math.sin(i * 1.7))), 3)
        speed = SPEED_KMH[rtype]
        tt = length_m / 1000 / speed * 60
        cost = round(REPAIR_COST[rtype] * max(0.6, length_m / 1000), 2)
        name = t.get("name") or t.get("ref") or (f"Mithi crossing near {near_place(mpt)}" if crosses_mithi else f"Unnamed {hw} road near {near_place(mpt)}")
        bonus = TYPE_THRESHOLD_BONUS[rtype] + (0.15 if elevated else 0.0)
        road_feats.append(feat("LineString", resample(line, 7), {
            "start_node_id": node_id[a], "end_node_id": node_id[b], "road_type": rtype, "name": name,
            "osm_way_id": w["id"], "osm_highway": t["highway"], "elevated": elevated, "crosses_mithi": crosses_mithi,
            "length_m": round(length_m, 1), "base_travel_time_minutes": round(tt, 3),
            "flood_susceptibility": susc, "elevation_proxy": e_proxy, "drainage_score": drain,
            "power_dependency": None, "current_status": "open", "closure_reason": None,
            "estimated_repair_cost": cost, "criticality_score": 0.0, "threshold_bonus": round(bonus, 3),
        }, rid))

    node_feats = []
    for nid, pos in node_pos.items():
        names = [n for n, _ in node_roads[nid].most_common(2)]
        is_major = len(node_roads[nid]) >= 2
        label = " / ".join(names) if is_major else (names[0] if names else nid)
        node_feats.append(feat("Point", pos, {"name": f"{label} junction" if is_major else label, "is_major": is_major}, nid))

    def nearest_node(p, exclude=()):
        return min((n for n in node_pos if n not in exclude), key=lambda n: (hav(node_pos[n], p), n))

    node_degree = Counter()
    for f in road_feats:
        node_degree[f["properties"]["start_node_id"]] += 1
        node_degree[f["properties"]["end_node_id"]] += 1

    def nearest_junction(p):
        """Zone anchors use a real junction (>= 3 roads) so a dead-end spur is not mistaken for a district bottleneck."""
        return min((n for n in node_pos if node_degree[n] >= 3), key=lambda n: (hav(node_pos[n], p), n))

    # ---- POIs ----------------------------------------------------------------------------
    def ll(e):
        return [e.get("lon") or e.get("center", {}).get("lon"), e.get("lat") or e.get("center", {}).get("lat")]

    pois = [e for e in els if "highway" not in e.get("tags", {}) and "waterway" not in e.get("tags", {})]

    def find(name_sub, key=None, val=None):
        for e in pois:
            t = e["tags"]
            if name_sub.lower() in (t.get("name") or "").lower() and (key is None or t.get(key) == val):
                p = ll(e)
                if p[0] is not None:
                    return e, p
        raise KeyError(name_sub)

    # ---- power + drainage (real OSM assets where they exist; others modeled) ------------
    power_spec = [  # id, name, kind, location source, real?
        ("P-01", "Tata Power Kurla Receiving Station", "substation", find("Tata Power Kurla")[1], True),
        ("P-02", "Kalina / Mithi-bank distribution substation (modeled)", "substation", [72.8705, 19.0745], False),
        ("P-03", "Tilak Nagar distribution substation (modeled)", "transformer", [72.8935, 19.0668], False),
        ("P-04", "Kurla West (LBS Marg) feeder substation (modeled)", "transformer", [72.8795, 19.0712], False),
    ]
    infra_feats, power_node = [], {}
    for pid, name, kind, p, real in power_spec:
        e_proxy, susc = flood_index(p)
        nn = nearest_node(p)
        power_node[pid] = nn
        infra_feats.append(feat("Point", rnd(p), {"infra_type": "power", "name": name, "kind": kind, "node_id": nn,
                                                  "elevation_proxy": e_proxy, "flood_susceptibility": susc,
                                                  "backup_power_available": False, "source": "OpenStreetMap" if real else "modeled"}, pid))
    drain_spec = [  # id, name, location, power node, backup, real?
        ("D-01", "BMC Kalina Sewage Water Pumping Station", find("Kalina Sewage")[1], "P-02", False, True),
        ("D-02", "Bail Bazar storm-water pump (modeled)", [72.8800, 19.0835], "P-01", True, False),
        ("D-03", "Tilak Nagar storm-water pump (modeled)", [72.8920, 19.0640], "P-03", False, False),
        ("D-04", "Mithi / CST Road flood gate pump (modeled)", [72.8742, 19.0695], "P-02", False, False),
        ("D-05", "Kurla station subway pump (modeled)", [72.8800, 19.0655], "P-04", False, False),
        ("D-06", "Kranti Nagar nala pump (modeled)", [72.8770, 19.0782], "P-04", False, False),
    ]
    for did, name, p, pn, backup, real in drain_spec:
        infra_feats.append(feat("Point", rnd(p), {"infra_type": "drainage", "name": name, "power_node_id": pn,
                                                  "backup_power_available": backup, "effectiveness_radius_m": 900.0,
                                                  "drainage_boost": 0.35, "source": "OpenStreetMap" if real else "modeled"}, did))

    # ---- facilities (all names/locations from OSM; capacities and power links modeled) ---
    def fac(fid, query, ftype, cap, power_dep, backup, backup_h, pnode, crit, min_acc, key=None, val=None, label=None):
        e, p = find(query, key, val)
        nn = nearest_node(p)
        return feat("Point", rnd(p), {"name": label or e["tags"]["name"], "facility_type": ftype, "capacity": cap,
                                      "operational_status": "operational", "power_dependent": power_dep,
                                      "backup_power_available": backup, "backup_power_hours": backup_h, "power_node_id": pnode,
                                      "node_id": nn, "minimum_accessibility_requirement": min_acc, "criticality_score": crit,
                                      "osm_id": f"{e['type']}/{e['id']}", "capacity_source": "modeled"}, fid)

    facs = [
        fac("H-01", "bhabha hospital", "hospital", 300, True, True, 24, "P-04", 1.0, 20, label="K.B. Bhabha Municipal General Hospital (BMC)"),
        fac("H-02", "Kalina Hospital", "hospital", 80, True, True, 8, "P-02", 0.8, 20),
        fac("H-03", "Kurla Municipal Hospital", "hospital", 60, True, False, 0, "P-03", 0.7, 20),
        fac("H-04", "CritiCare Asia", "hospital", 150, True, True, 12, "P-01", 0.9, 20),
        fac("S-01", "Holy Cross Church", "shelter", 400, False, False, 0, None, 0.6, 25, label="Holy Cross Church hall (Kurla Christian Village)"),
        fac("S-02", "Our Lady of Egypt", "shelter", 300, False, False, 0, None, 0.6, 25, label="Our Lady of Egypt Church hall, Kalina"),
        fac("S-03", "Tilak Nagar Municipal School", "shelter", 500, True, False, 0, "P-03", 0.7, 25),
        fac("S-04", "Kohinoor Educational Complex", "shelter", 450, False, False, 0, None, 0.5, 25),
        fac("S-05", "Orchids The International School", "shelter", 350, False, False, 0, None, 0.5, 25),
        fac("S-06", "Shree Swami Samartha Math", "shelter", 200, True, True, 10, "P-04", 0.5, 25),
        fac("W-01", "Fatima High School", "water", 1500, False, False, 0, None, 0.5, 15, label="Water point - Fatima High School"),
        fac("W-02", "Our Lady of Egypt", "water", 1800, True, False, 0, "P-02", 0.55, 15, label="Water point - Kalina (Our Lady of Egypt)"),
        fac("W-03", "Rehmaniya Masjid", "water", 2200, True, True, 12, "P-01", 0.6, 15, label="Water point - Bail Bazar (Rehmaniya Masjid)"),
        fac("W-04", "Lokamaniya Tilak High School", "water", 1500, True, False, 0, "P-03", 0.5, 15, label="Water point - Tilak Nagar"),
        fac("W-05", "Shri Balaji Mandir", "water", 1400, False, False, 0, None, 0.5, 15, label="Water point - Kurla West (Balaji Mandir)"),
        fac("W-06", "Umar Masjid", "water", 1200, False, False, 0, None, 0.45, 15, label="Water point - Kismat Nagar (Umar Masjid)"),
        fac("E-01", "Kurla Agnishaman Kendra", "emergency", 30, False, False, 0, None, 0.8, 15, label="Kurla Fire Station (Agnishaman Kendra)"),
        fac("E-02", "VB Nagar Police Station", "emergency", 25, True, True, 12, "P-01", 0.6, 15),
        fac("E-03", "Tilak Nagar Police Station", "emergency", 20, True, True, 12, "P-03", 0.85, 15),
        fac("E-04", "Bail Bazar Police Station", "emergency", 40, True, True, 24, "P-02", 0.9, 15),
        fac("E-05", "Nehru Nagar Kurla E Police Chowky", "emergency", 35, False, False, 0, None, 0.7, 15),
        fac("SC-01", "Fatima High School", "school", 450, False, False, 0, None, 0.3, 30),
        fac("SC-02", "Adarsha Vidyalaya", "school", 700, False, False, 0, None, 0.3, 30),
        fac("SC-03", "Dhirubhai Ambani International", "school", 400, False, False, 0, None, 0.3, 30),
        fac("SC-04", "Municipal School", "school", 800, False, False, 0, None, 0.3, 30, label="BMC Municipal School, Tilak Nagar"),
        fac("SC-05", "Chembur Vidya Niketan", "school", 500, False, False, 0, None, 0.3, 30),
        fac("SC-06", "Lokmaniya Tilak Jr", "school", 380, False, False, 0, None, 0.3, 30),
        fac("SC-07", "Holy cross centenary", "school", 420, False, False, 0, None, 0.3, 30, label="Holy Cross High School, Kurla"),
        fac("SC-08", "American School of Bombay", "school", 350, False, False, 0, None, 0.3, 30),
    ]
    # keep facilities inside the study area
    for f in facs:
        lon, lat = f["geometry"]["coordinates"]
        if not inside(lon, lat):
            raise ValueError(f"{f['id']} {f['properties']['name']} outside study area")

    # ---- population zones: Voronoi (clipped grid) of real OSM neighbourhood points --------
    zone_seeds = [  # id, OSM place name (exact), display name, vulnerability, mobility
        ("Z-01", "Kalina Village", "Kalina", 1.10, 1.05),
        ("Z-02", "Kismat Nagar", "Kismat Nagar (Mithi bank)", 1.35, 1.25),
        ("Z-03", "Kurla Christian Village", "Old Kurla / Kurla Christian Village", 1.05, 1.00),
        ("Z-04", "Sahayog Nagar", "Bail Bazar / Sahayog Nagar", 1.30, 1.20),
        ("Z-05", "Kurla West", "Kurla West (LBS Marg)", 1.15, 1.10),
        ("Z-06", "Nehru Nagar", "Nehru Nagar, Kurla East", 1.20, 1.15),
        ("Z-07", "Tilak Nagar", "Tilak Nagar", 0.90, 0.95),
        ("Z-08", "Vidya Vihar West", "Vidyavihar West / Kirol", 0.95, 1.00),
    ]
    seed_pos = {}
    for zid, q, _, _, _ in zone_seeds:
        e = next(e for e in pois if e["tags"].get("place") and e["tags"].get("name") == q)
        seed_pos[zid] = ll(e)

    airport = None
    for e in lu["elements"]:
        if e.get("tags", {}).get("aeroway") == "aerodrome" and e["type"] == "way":
            airport = [[g["lon"], g["lat"]] for g in e["geometry"]]
    built = []
    for e in lu["elements"]:
        t = e.get("tags", {})
        if e["type"] == "way" and t.get("landuse") in ("residential", "commercial", "retail") and len(e.get("geometry", [])) >= 4:
            built.append([[g["lon"], g["lat"]] for g in e["geometry"]])

    GX, GY = 60, 50
    cells = defaultdict(list)
    cell_area_km2 = (hav([W, S], [E, S]) / GX) * (hav([W, S], [W, N]) / GY) / 1e6
    for i in range(GX):
        for j in range(GY):
            p = [W + (E - W) * (i + 0.5) / GX, S + (N - S) * (j + 0.5) / GY]
            if airport and point_in_poly(p, airport):
                continue
            if dist_to_line(p, river_in) < 35:
                continue  # river channel
            zid = min(seed_pos, key=lambda z: (hav(seed_pos[z], p), z))
            cells[zid].append(p)

    def hull(points):
        pts = sorted(set((round(p[0], 6), round(p[1], 6)) for p in points))
        if len(pts) < 3:
            return [list(p) for p in pts]

        def cross(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
        lower, upper = [], []
        for p in pts:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)
        for p in reversed(pts):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)
        return [list(p) for p in lower[:-1] + upper[:-1]]

    zone_feats, zone_cells = [], {}
    for zid, q, name, vuln, mob in zone_seeds:
        pts = cells[zid]
        built_share = sum(1 for p in pts if any(point_in_poly(p, b) for b in built)) / max(1, len(pts))
        area = len(pts) * cell_area_km2
        # Ward L 2011 density applied to the residential/commercial-weighted share of each zone (modeled)
        pop = int(round(DENSITY * area * (0.45 + 0.55 * built_share) / 100.0) * 100)
        ring = hull(pts)
        ring.append(ring[0])
        anchor = nearest_junction(seed_pos[zid])
        zone_cells[zid] = pts
        zone_feats.append(feat("Polygon", [ring], {
            "name": name, "estimated_population": pop, "vulnerability_weight": vuln, "mobility_constraint_factor": mob,
            "anchor_node_id": anchor, "osm_place": q, "area_km2": round(area, 3),
            "population_source": "modeled: Census 2011 Ward L density x built-up share",
            "bbox_grid": [0, 0, 1, 1], "nearest_facility_ids": []}, zid))

    # ---- hazard zones: low-lying, Mithi-adjacent pockets (from the same flood index) -----
    hz_spec = [  # id, name, center lon/lat, rx_m, ry_m, drainage, exposure
        ("HZ-01", "Kranti Nagar / Mithi bank (CST Road)", [72.8735, 19.0725], 520, 380, 0.50, 1.00),
        ("HZ-02", "Kismat Nagar - Bail Bazar Mithi bend", [72.8770, 19.0790], 480, 360, 0.50, 1.00),
        ("HZ-03", "Kalina - Vakola nala low ground", [72.8665, 19.0770], 450, 330, 0.55, 0.95),
        ("HZ-04", "Kurla station subway & LBS Marg dip", [72.8805, 19.0660], 420, 300, 0.55, 0.90),
        ("HZ-05", "Jarimari - airport boundary drain", [72.8810, 19.0875], 420, 320, 0.45, 1.00),
        ("HZ-06", "Tilak Nagar - SCLR underpass", [72.8925, 19.0655], 380, 280, 0.50, 0.85),
    ]
    hz_feats = []
    for hid, name, c, rx, ry, drain, expo in hz_spec:
        _, susc = flood_index(c)
        kx = 111320 * math.cos(math.radians(c[1]))
        ring = [rnd([c[0] + rx / kx * math.cos(2 * math.pi * k / 28), c[1] + ry / 110540 * math.sin(2 * math.pi * k / 28)]) for k in range(28)]
        ring.append(ring[0])
        hz_feats.append(feat("Polygon", [ring], {
            "name": name, "susceptibility_score": susc, "estimated_water_accumulation": round(susc * 0.9, 3),
            "drainage_effectiveness": drain, "exposure_factor": expo, "center": rnd(c),
            "center_grid": [c[0], c[1]], "radii_grid": [rx / kx, ry / 110540]}, hid))

    # exposure samples are lon/lat cells; express zone bboxes in lon/lat so exposure.py's ellipse test works unchanged
    for z in zone_feats:
        xs = [p[0] for p in z["geometry"]["coordinates"][0]]
        ys = [p[1] for p in z["geometry"]["coordinates"][0]]
        z["properties"]["bbox_grid"] = [min(xs), min(ys), max(xs), max(ys)]
        z["properties"]["sample_points"] = [rnd(p) for p in zone_cells[z["id"]][::max(1, len(zone_cells[z["id"]]) // 100)]][:100]

    # ---- staging + resources ------------------------------------------------------------
    stg_spec = [("STG-1", "Kurla Fire Station depot", find("Kurla Agnishaman")[1]),
                ("STG-2", "L Ward office depot (S.G. Barve Marg)", [72.8830, 19.0705]),
                ("STG-3", "Tilak Nagar depot", [72.8935, 19.0680]),
                ("STG-4", "Kalina depot", [72.8640, 19.0760]),
                ("STG-5", "LTT / Nehru Nagar depot", find("Lokmanya Tilak Terminus")[1])]
    stg_feats = []
    for sid, name, p in stg_spec:
        nn = nearest_node(p)
        stg_feats.append(feat("Point", rnd(p), {"name": name, "node_id": nn}, sid))
    res_spec = [
        ("RES-RC1", "BMC road clearance team A", "road_clearance_team", "STG-1", 2, 3500, 1.5, 30, 1),
        ("RES-RC2", "BMC road clearance team B", "road_clearance_team", "STG-2", 2, 3500, 1.5, 30, 1),
        ("RES-GEN1", "Portable generator pool (L Ward)", "portable_generator", "STG-2", 3, 4500, 2.0, 20, 1),
        ("RES-GEN2", "Portable generator pool (Tilak Nagar)", "portable_generator", "STG-3", 1, 4500, 2.0, 20, 1),
        ("RES-MED1", "Temporary medical unit", "temporary_medical_unit", "STG-4", 2, 6000, 9.0, 60, 60),
        ("RES-WAT1", "Water tanker / distribution unit", "water_distribution_unit", "STG-5", 2, 6000, 3.5, 45, 1500),
        ("RES-SHL1", "Temporary shelter kit", "temporary_shelter_kit", "STG-3", 2, 6000, 4.0, 50, 250),
    ]
    stg_map = {f["id"]: f for f in stg_feats}
    res_feats = []
    for rid, name, rtype, stg, qty, radius, cost, mins, cap in res_spec:
        res_feats.append(feat("Point", stg_map[stg]["geometry"]["coordinates"], {
            "name": name, "resource_type": rtype, "staging_id": stg, "node_id": stg_map[stg]["properties"]["node_id"],
            "quantity_available": qty, "response_radius": radius, "deployment_cost": cost,
            "deployment_time_minutes": mins, "service_capacity": cap, "source": "modeled"}, rid))

    boundary = feat("Polygon", [[rnd([W, S]), rnd([E, S]), rnd([E, N]), rnd([W, N]), rnd([W, S])]],
                    {"name": "Kurla / Mithi River study area, Mumbai (BMC Ward L)", "notice": NOTICE, "license": LICENSE}, "BOUNDARY")
    river_feat = feat("LineString", [rnd(p) for p in river_in], {"name": "Mithi River", "source": "OpenStreetMap", "osm_way_id": mithi_main["id"]}, "RIVER-1")

    return {
        "roads": fc(road_feats, "roads"), "nodes": fc(node_feats, "nodes"), "facilities": fc(facs, "facilities"),
        "zones": fc(zone_feats, "population_zones"), "hazards": fc(hz_feats, "hazard_zones"),
        "infrastructure": fc(infra_feats, "infrastructure"), "staging": fc(stg_feats, "staging"),
        "resources": fc(res_feats, "resources"), "boundary": fc([boundary], "boundary"), "river": fc([river_feat], "river"),
    }


def main() -> None:
    if "--refresh" in sys.argv:
        refresh_sources()
    OUT.mkdir(parents=True, exist_ok=True)
    data = build()
    for name, coll in data.items():
        (OUT / f"{name}.geojson").write_text(json.dumps(coll, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    osm_ts = json.loads((SRC / "osm_kurla_raw.json").read_text(encoding="utf-8")).get("osm3s", {}).get("timestamp_osm_base")
    manifest = {"dataset_version": DATASET_VERSION, "synthetic": False, "modeled_attributes": True,
                "label": "Kurla / Mithi River, Mumbai - real OpenStreetMap + SRTM geography with modeled planning attributes",
                "study_area_bbox": [W, S, E, N], "osm_snapshot": osm_ts, "license": LICENSE,
                "sources": {"roads_facilities_river_places": "OpenStreetMap (Overpass API), ODbL 1.0",
                            "terrain": "SRTM 30 m via OpenTopoData", "population_density": f"Census 2011 BMC Ward L: {WARD_L_POP:,} people / {WARD_L_KM2} km2"},
                "modeled": ["zone boundaries (Voronoi of OSM neighbourhood points)", "zone populations", "facility capacities",
                            "backup power", "power-dependency links", "3 of 4 power nodes", "5 of 6 drainage pumps",
                            "response resources and costs", "flood susceptibility index"],
                "counts": {k: len(v["features"]) for k, v in data.items()}}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest["counts"]))


if __name__ == "__main__":
    main()
