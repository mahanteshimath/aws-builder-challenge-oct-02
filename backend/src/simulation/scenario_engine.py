"""Deterministic scenario engine: hazard -> road disruption -> network accessibility -> exposure -> comparison.

Identical inputs + identical SIMULATION_VERSION always produce identical outputs (no randomness anywhere).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ..models.geography import Dataset, Facility
from ..models.scenario import SIMULATION_VERSION, Scenario, Thresholds
from .accessibility import SERVICE_THRESHOLD, SERVICES, best_service, pair_status, service_reduced
from .exposure import zone_exposure, zone_sample_cover
from .flood_model import (ROAD_STATUS_FOR_CLASS, SUSCEPTIBILITY_MULTIPLIER, clamp, classify, flood_risk,
                          rainfall_intensity_factor)
from .infrastructure import facility_operation
from .interventions import TEMP_FACILITY, ScenarioError, resolve_interventions
from .metrics import ASSUMPTIONS, METRIC_DEFINITIONS
from .road_network import build_adjacency, dijkstra, haversine_m, path_roads

SYNTHETIC_NOTICE = ("SYNTHETIC DEMONSTRATION DATA - fictional 'Sahyadri Resilience District'. Illustrative comparative "
                    "planning model only; not official data, not a flood forecast, not an operational emergency system.")
STATUS_PENALTY_KEY = {"open": None, "degraded": "degraded_penalty", "restricted": "restricted_penalty"}
SERVICE_TYPES = ("hospital", "shelter", "water")
CRIT_TYPES = ("hospital", "shelter", "water", "emergency")


# --------------------------------------------------------------------------------------- conditions
@dataclass(frozen=True)
class Conditions:
    rainfall_mm: float
    duration_hours: float
    drainage_effectiveness: float
    susceptibility_preset: str
    closed_roads: frozenset
    failed_power: frozenset
    failed_drainage: frozenset
    failed_facilities: frozenset
    th: Thresholds


def conditions_from(s: Scenario, rain_scale: float = 1.0, closures: bool = True, failures: bool = True) -> Conditions:
    return Conditions(s.rainfall_mm * rain_scale, s.duration_hours, s.drainage_effectiveness, s.susceptibility_preset,
                      frozenset(s.closed_road_ids) if closures else frozenset(),
                      frozenset(s.affected_power_nodes) if failures else frozenset(),
                      frozenset(s.failed_drainage_ids) if failures else frozenset(),
                      frozenset(s.failed_facility_ids) if failures else frozenset(), s.thresholds)


def baseline_conditions(s: Optional[Scenario] = None) -> Conditions:
    th = s.thresholds if s else Thresholds()
    return Conditions(0.0, s.duration_hours if s else 6.0, s.drainage_effectiveness if s else 0.5,
                      s.susceptibility_preset if s else "moderate", frozenset(), frozenset(), frozenset(), frozenset(), th)


def validate_scenario_ids(ds: Dataset, s: Scenario) -> None:
    for label, ids, known in (("road", s.closed_road_ids, ds.roads), ("power node", s.affected_power_nodes, ds.power_nodes),
                              ("drainage asset", s.failed_drainage_ids, ds.drainage),
                              ("facility", s.failed_facility_ids, ds.facilities)):
        bad = [i for i in ids if i not in known]
        if bad:
            raise ScenarioError(f"Unknown {label} id(s): {', '.join(bad[:5])}")


# --------------------------------------------------------------------------------------- static geometry cache
_STATIC: dict[int, dict] = {}
_BASE_CACHE: dict[tuple, dict] = {}


def static(ds: Dataset) -> dict:
    key = id(ds)
    if key in _STATIC:
        return _STATIC[key]
    road_assets, hazard_assets = {}, {}
    for rid, r in ds.roads.items():
        road_assets[rid] = _asset_weights(ds, r.geometry[1])
    hcent = {}
    for hid, h in ds.hazards.items():
        ring = h.geometry[:-1]
        hcent[hid] = [sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)]
        hazard_assets[hid] = _asset_weights(ds, hcent[hid])
    cover = {zid: zone_sample_cover(z, ds.hazards) for zid, z in ds.zones.items()}
    _STATIC[key] = {"road_assets": road_assets, "hazard_assets": hazard_assets, "cover": cover}
    return _STATIC[key]


def _asset_weights(ds: Dataset, pos: list[float]) -> list[tuple[str, float]]:
    out = []
    for did, d in ds.drainage.items():
        dist = haversine_m(pos, d.geometry)
        if dist < d.effectiveness_radius_m:
            out.append((did, 1.0 - dist / d.effectiveness_radius_m))
    return out


# --------------------------------------------------------------------------------------- evaluation
def evaluate(ds: Dataset, cond: Conditions, ints: Optional[list[dict]] = None) -> dict:
    ints = ints or []
    st = static(ds)
    th = cond.th
    rif = rainfall_intensity_factor(cond.rainfall_mm, cond.duration_hours)
    pm = SUSCEPTIBILITY_MULTIPLIER[cond.susceptibility_preset]
    g = cond.drainage_effectiveness
    reopened = {i["target_id"] for i in ints if i["resource_type"] == "road_clearance_team"}
    gens = {i["target_id"] for i in ints if i["resource_type"] == "portable_generator"}

    power = {}
    for pid, pn in ds.power_nodes.items():
        risk = flood_risk(rif, pn.flood_susceptibility, clamp(g * 0.7), 1.0, pm)
        cls = classify(risk, th)
        if pid in cond.failed_power:
            power[pid] = {"risk": risk, "hazard_class": cls, "failed": True, "reason": "Selected as failed in scenario"}
        elif cls == "impassable":
            power[pid] = {"risk": risk, "hazard_class": cls, "failed": True, "reason": f"Substation flooding (risk {risk:.2f})"}
        else:
            power[pid] = {"risk": risk, "hazard_class": cls, "failed": False, "reason": "Operating"}

    drainage = {}
    for did, d in ds.drainage.items():
        failed, reason = False, "Operating"
        if did in cond.failed_drainage:
            failed, reason = True, "Selected as failed in scenario"
        elif power[d.power_node_id]["failed"] and not d.backup_power_available:
            failed, reason = True, f"Pump lost power ({d.power_node_id})"
        if failed and did in gens:
            failed, reason = False, "Portable generator deployed"
        drainage[did] = {"failed": failed, "reason": reason}

    def boost(weights):
        return min(0.4, sum(ds.drainage[d].drainage_boost * w for d, w in weights if not drainage[d]["failed"]))

    roads, travel = {}, {}
    for rid, r in ds.roads.items():
        eff = clamp(g * r.drainage_score + boost(st["road_assets"][rid]))
        risk = flood_risk(rif, r.flood_susceptibility, eff, 1.0, pm)
        cls = classify(risk, th, r.threshold_bonus)
        status = ROAD_STATUS_FOR_CLASS[cls]
        reason = None if cls == "normal" else f"Modeled flood risk {risk:.2f} ({cls.replace('_', ' ')})"
        if rid in cond.closed_roads:
            status, reason = "closed", "Explicit closure"
        if rid in reopened and status in ("closed", "restricted"):
            status, reason = "degraded", "Reopened by road clearance team (reduced speed)"
        key = STATUS_PENALTY_KEY.get(status)
        penalty = None if status == "closed" else (1.0 if key is None else getattr(th, key))
        tt = None if penalty is None else r.base_travel_time_minutes * penalty
        travel[rid] = tt
        roads[rid] = {"risk": risk, "hazard_class": cls, "status": status, "travel_minutes": tt,
                      "base_minutes": r.base_travel_time_minutes, "reason": reason}

    hazards = {}
    for hid, h in ds.hazards.items():
        eff = clamp(g * h.drainage_effectiveness * 1.8 + 0.5 * boost(st["hazard_assets"][hid]), 0.0, 0.95)
        risk = flood_risk(rif, h.susceptibility_score, eff, h.exposure_factor, pm)
        hazards[hid] = {"risk": risk, "hazard_class": classify(risk, th)}

    fac_map: dict[str, Facility] = dict(ds.facilities)
    for i in ints:
        if i["resource_type"] in TEMP_FACILITY:
            prefix, ftype, label = TEMP_FACILITY[i["resource_type"]]
            z = ds.zones[i["target_id"]]
            n = ds.nodes[z.anchor_node_id]
            fid = f"{prefix}-{z.id}"
            fac_map[fid] = Facility(id=fid, name=f"{label} ({z.name})", facility_type=ftype, geometry=[n.lon + 0.0008, n.lat - 0.0008],
                                    capacity=i["capacity_added"], node_id=z.anchor_node_id, minimum_accessibility_requirement=SERVICE_THRESHOLD[ftype],
                                    criticality_score=0.6, temporary=True)
    failed_power_ids = {pid for pid, p in power.items() if p["failed"]}
    ops = {fid: facility_operation(f, failed_power_ids, set(cond.failed_facilities), cond.duration_hours, gens) for fid, f in fac_map.items()}
    mults = {fid: o["multiplier"] for fid, o in ops.items()}
    fac_by_type: dict[str, list[str]] = {}
    for fid, f in fac_map.items():
        fac_by_type.setdefault(f.facility_type, []).append(fid)

    adj = build_adjacency(ds.roads, ds.nodes.keys(), travel)
    dist, prev, times = {}, {}, {}
    for zid, z in ds.zones.items():
        d, p = dijkstra(adj, z.anchor_node_id)
        dist[zid], prev[zid] = d, p
        times[zid] = {fid: d.get(f.node_id) for fid, f in fac_map.items()}

    expo = {zid: zone_exposure(z, st["cover"][zid], {h: v["risk"] for h, v in hazards.items()}, th.watch)
            for zid, z in ds.zones.items()}
    return {"cond": cond, "rif": rif, "power": power, "drainage": drainage, "roads": roads, "hazards": hazards, "ops": ops,
            "mults": mults, "fac_map": fac_map, "fac_by_type": fac_by_type, "adj": adj, "dist": dist, "prev": prev,
            "times": times, "exposure": expo, "ints": ints}


def get_baseline(ds: Dataset, s: Optional[Scenario] = None) -> dict:
    th = s.thresholds if s else Thresholds()
    key = (id(ds), th.model_dump_json())
    if key not in _BASE_CACHE:
        _BASE_CACHE[key] = evaluate(ds, baseline_conditions(s))
    return _BASE_CACHE[key]


# --------------------------------------------------------------------------------------- assessment
def assess(ds: Dataset, ev: dict, base: dict, with_routes: bool = True) -> dict:
    th = ev["cond"].th
    mults, bmults = ev["mults"], base["mults"]
    total_pop = sum(z.estimated_population for z in ds.zones.values())

    zones_out, reduced_any_pop, reduced_pop = [], 0, {s: 0 for s in SERVICES}
    access_units = 0.0
    no_route_zones, hosp_time_num, hosp_time_den = [], 0.0, 0
    reduced_count_by_zone = {}
    reach_by_zone = {}
    for zid, z in ds.zones.items():
        tz, bz = ev["times"][zid], base["times"][zid]
        services, reduced_n, no_feasible = {}, 0, False
        reach_by_zone[zid] = {}
        for s in SERVICES:
            thr = SERVICE_THRESHOLD[s]
            fid, t = best_service(tz, ev["fac_by_type"][s], mults)
            bfid, bt = best_service(bz, base["fac_by_type"][s], bmults)
            red = service_reduced(t, bt, thr, th.delay_ratio)
            in_range = [f for f in ev["fac_by_type"][s] if tz.get(f) is not None and tz[f] <= thr and mults[f] > 0]
            reach_by_zone[zid][s] = in_range
            if not in_range:
                no_feasible = True
            if red:
                reduced_n += 1
                reduced_pop[s] += z.estimated_population
            services[s] = {"best_facility_id": fid, "minutes": None if t is None else round(t, 2),
                           "baseline_facility_id": bfid, "baseline_minutes": None if bt is None else round(bt, 2),
                           "threshold_minutes": thr, "reduced": red, "no_route": t is None,
                           "reachable_count": len(in_range)}
        if services["hospital"]["minutes"] is not None:
            hosp_time_num += z.estimated_population * services["hospital"]["minutes"]
            hosp_time_den += z.estimated_population
        if reduced_n:
            reduced_any_pop += z.estimated_population
        if no_feasible:
            no_route_zones.append(zid)
        reduced_count_by_zone[zid] = reduced_n
        ex = ev["exposure"][zid]
        status = "isolated" if no_feasible else "reduced_access" if reduced_n else "exposed" if ex["exposed_fraction"] > 0 else "normal"
        zones_out.append({"id": zid, "name": z.name, "population": z.estimated_population, **ex, "status": status,
                          "services": services, "reduced_service_count": reduced_n})

    facs_out, lost_facs, op_affected, elec_affected = [], [], 0, 0
    cap_avail = shelter_cap = 0.0
    acc_counts = {s: 0 for s in SERVICES}
    inaccessible_ids = []
    for fid, f in ev["fac_map"].items():
        op = ev["ops"][fid]
        thr = SERVICE_THRESHOLD[f.facility_type]
        reach, lost, delayed = [], [], []
        for zid in ds.zones:
            t, bt = ev["times"][zid].get(fid), base["times"][zid].get(fid)
            ps = pair_status(t, bt, thr, th.delay_ratio)
            if ps != "inaccessible":
                reach.append(zid)
                if ps == "accessible_with_delay":
                    delayed.append(zid)
            elif bt is not None and bt <= thr:
                lost.append(zid)
        if not reach:
            acc = "inaccessible"
        elif lost or delayed:
            acc = "accessible_with_delay"
        else:
            acc = "accessible"
        display = ("inaccessible" if acc == "inaccessible" else "operationally_affected" if op["status"] != "operational"
                   else "accessible_with_delay" if acc == "accessible_with_delay" else "accessible")
        if op["status"] != "operational":
            op_affected += 1
            if f.power_dependent and f.power_node_id in ev["power"] and ev["power"][f.power_node_id]["failed"]:
                elec_affected += 1
        if lost:
            lost_facs.append(fid)
        if acc == "inaccessible" and (f.facility_type in CRIT_TYPES):
            inaccessible_ids.append(fid)
        cap_eff = f.capacity * op["multiplier"]
        if f.facility_type in SERVICE_TYPES and reach and op["multiplier"] > 0:
            cap_avail += cap_eff
            acc_counts[f.facility_type] += 1
            if f.facility_type == "shelter":
                shelter_cap += cap_eff
        facs_out.append({"id": fid, "name": f.name, "facility_type": f.facility_type, "capacity": f.capacity,
                         "operational_status": op["status"], "capacity_multiplier": op["multiplier"],
                         "capacity_available": round(cap_eff, 1), "operational_reason": op["reason"],
                         "power_dependent": f.power_dependent, "temporary": f.temporary,
                         "accessibility_status": acc, "display_status": display, "zones_reaching": reach,
                         "zones_lost": lost, "zones_delayed": delayed,
                         "minutes_from_zone": {z: (None if ev["times"][z].get(fid) is None else round(ev["times"][z][fid], 2)) for z in ds.zones}})

    exposed = sum(e["exposed_population"] for e in ev["exposure"].values())
    vw = sum(e["vulnerability_weighted_exposure"] for e in ev["exposure"].values())
    demand = int(round(0.15 * vw))
    roads = ev["roads"]
    counts = {k: sum(1 for r in roads.values() if r["status"] == k) for k in ("degraded", "restricted", "closed")}
    metrics = {
        "population_total": total_pop, "exposed_population": exposed, "vulnerability_weighted_exposure": vw,
        "pop_reduced_hospital": reduced_pop["hospital"], "pop_reduced_shelter": reduced_pop["shelter"],
        "pop_reduced_water": reduced_pop["water"], "pop_reduced_any": reduced_any_pop,
        "roads_total": len(roads), "roads_affected": sum(counts.values()), "roads_degraded": counts["degraded"],
        "roads_restricted": counts["restricted"], "roads_closed": counts["closed"],
        "facilities_operationally_affected": op_affected, "facilities_inaccessible_some_zone": len(lost_facs),
        "avg_hospital_time_min": round(hosp_time_num / hosp_time_den, 2) if hosp_time_den else None,
        "zones_no_feasible_route": len(no_route_zones), "service_capacity_available": round(cap_avail, 1),
        "shelter_capacity_available": round(shelter_cap, 1), "shelter_demand": demand,
        "shelter_shortfall": int(max(0, round(demand - shelter_cap))),
        "hospitals_accessible": acc_counts["hospital"], "shelters_accessible": acc_counts["shelter"],
        "water_points_accessible": acc_counts["water"], "electricity_dependent_affected": elec_affected,
        "resources_deployed": len(ev["ints"]), "budget_consumed": round(sum(i["cost"] for i in ev["ints"]), 2),
    }
    affected_zone_ids = [z["id"] for z in zones_out if z["status"] != "normal"]
    block = {
        "metrics": metrics,
        "roads": {rid: {"status": r["status"], "risk": round(r["risk"], 4), "hazard_class": r["hazard_class"],
                        "travel_minutes": None if r["travel_minutes"] is None else round(r["travel_minutes"], 3),
                        "base_minutes": round(r["base_minutes"], 3), "reason": r["reason"]} for rid, r in roads.items()},
        "hazards": {h: {"risk": round(v["risk"], 4), "hazard_class": v["hazard_class"]} for h, v in ev["hazards"].items()},
        "power": {p: {**v, "risk": round(v["risk"], 4)} for p, v in ev["power"].items()},
        "drainage": ev["drainage"],
        "zones": zones_out, "facilities": facs_out,
        "affected_road_ids": [rid for rid, r in roads.items() if r["status"] != "open"],
        "flooded_road_ids": [rid for rid, r in roads.items() if r["hazard_class"] != "normal"],
        "inaccessible_facility_ids": inaccessible_ids, "facilities_lost_access_ids": lost_facs,
        "affected_zone_ids": affected_zone_ids, "impacted_population_estimate": exposed,
        "affected_service_capacity": round(sum(f["capacity"] - f["capacity_available"] for f in facs_out if f["facility_type"] in SERVICE_TYPES), 1),
        "reachable_facilities_by_zone": reach_by_zone,
        "interventions": ev["ints"],
        "estimated_restore_hours": _restore_hours(ev, metrics),
        "temporary_facilities": [f for f in facs_out if f["temporary"]],
        "map_state": {
            "roads": {rid: [r["status"], round(r["risk"], 3)] for rid, r in roads.items()},
            "hazards": {h: [v["hazard_class"], round(v["risk"], 3)] for h, v in ev["hazards"].items()},
            "facilities": {f["id"]: f["display_status"] for f in facs_out},
            "zones": {z["id"]: z["status"] for z in zones_out},
            "power": {p: v["failed"] for p, v in ev["power"].items()},
            "drainage": {d: v["failed"] for d, v in ev["drainage"].items()},
        },
        "_reduced_count_by_zone": reduced_count_by_zone,
    }
    if with_routes:
        block["routes"], block["alternative_routes"] = _routes(ds, ev, base)
    return block


def _restore_hours(ev: dict, m: dict) -> float:
    if ev["ints"]:
        return round(max(i["deploy_minutes"] for i in ev["ints"]) / 60.0, 1)
    if m["roads_affected"] == 0 and m["facilities_operationally_affected"] == 0:
        return 0.0
    max_risk = max((r["risk"] for r in ev["roads"].values()), default=0.0)
    manual = 3.0 if ev["cond"].closed_roads else 0.0
    return round(0.5 * ev["cond"].duration_hours + 10.0 * max_risk + manual, 1)


def _routes(ds: Dataset, ev: dict, base: dict):
    routes, alts = {}, []
    for zid, z in ds.zones.items():
        routes[zid] = {}
        for ftype in SERVICE_TYPES:
            for fid in ev["fac_by_type"][ftype]:
                f = ev["fac_map"][fid]
                t = ev["times"][zid].get(fid)
                if t is None:
                    continue
                roads = path_roads(ev["prev"][zid], f.node_id, z.anchor_node_id)
                routes[zid][fid] = {"minutes": round(t, 2), "roads": roads}
                bt = base["times"][zid].get(fid)
                if bt is not None and fid in base["fac_map"]:
                    broads = path_roads(base["prev"][zid], f.node_id, z.anchor_node_id)
                    if broads != roads:
                        alts.append({"zone_id": zid, "facility_id": fid, "facility_type": ftype, "baseline_minutes": round(bt, 2),
                                     "baseline_roads": broads, "scenario_minutes": round(t, 2), "scenario_roads": roads,
                                     "status": "rerouted", "delay_minutes": round(t - bt, 2)})
            # facilities that lost all routes
        for ftype in SERVICE_TYPES:
            for fid in base["fac_by_type"][ftype]:
                if ev["times"][zid].get(fid) is None and base["times"][zid].get(fid) is not None:
                    f = base["fac_map"][fid]
                    alts.append({"zone_id": zid, "facility_id": fid, "facility_type": ftype,
                                 "baseline_minutes": round(base["times"][zid][fid], 2),
                                 "baseline_roads": path_roads(base["prev"][zid], f.node_id, z.anchor_node_id),
                                 "scenario_minutes": None, "scenario_roads": [], "status": "no_route", "delay_minutes": None})
    alts.sort(key=lambda a: (a["status"] != "no_route", -(a["delay_minutes"] or 0), a["zone_id"], a["facility_id"]))
    return routes, alts[:40]


# --------------------------------------------------------------------------------------- bottlenecks
def _bottleneck_scan(ds: Dataset, ev: dict) -> list[dict]:
    total_pop = sum(z.estimated_population for z in ds.zones.values())
    mults = ev["mults"]
    cur_best = {}
    for zid in ds.zones:
        for s in SERVICES:
            cur_best[(zid, s)] = best_service(ev["times"][zid], ev["fac_by_type"][s], mults)[1]
    out = []
    for rid, r in ev["roads"].items():
        if r["status"] == "closed":
            continue
        impact, zones_hit, lost_facs, sole = 0.0, [], set(), set()
        for zid, z in ds.zones.items():
            d2, _ = dijkstra(ev["adj"], z.anchor_node_id, exclude_road=rid)
            zone_loss = 0.0
            for s in SERVICES:
                thr = SERVICE_THRESHOLD[s]
                t0 = cur_best[(zid, s)]
                t1 = None
                for fid in ev["fac_by_type"][s]:
                    if mults[fid] <= 0:
                        continue
                    t = d2.get(ev["fac_map"][fid].node_id)
                    if t is not None and (t1 is None or t < t1):
                        t1 = t
                    t_old = ev["times"][zid].get(fid)
                    if t_old is not None and t_old <= thr and (t is None or t > thr):
                        lost_facs.add(fid)
                        if t is None:
                            sole.add(fid)
                if t0 is not None and t0 <= thr and (t1 is None or t1 > thr):
                    zone_loss += 1.0
                elif t0 is not None and t1 is not None and t1 > t0 + 1e-9:
                    zone_loss += min(0.5, (t1 - t0) / thr)
                elif t0 is not None and t1 is None:
                    zone_loss += 0.5
            if zone_loss > 0:
                zones_hit.append(zid)
                impact += z.estimated_population * zone_loss / 3.0
        if impact > 0:
            out.append({"road_id": rid, "score": round(impact / total_pop, 4), "population_affected": sum(ds.zones[z].estimated_population for z in zones_hit),
                        "affected_zone_ids": zones_hit, "affected_facility_ids": sorted(lost_facs), "sole_route_facility_ids": sorted(sole),
                        "status": r["status"]})
    out.sort(key=lambda b: (-b["score"], b["road_id"]))
    return out


def annotate_baseline_criticality(ds: Dataset) -> None:
    scan = _bottleneck_scan(ds, get_baseline(ds))
    mx = scan[0]["score"] if scan else 1.0
    for b in scan:
        ds.roads[b["road_id"]].criticality_score = round(b["score"] / mx, 3)


def _describe_bottleneck(ds: Dataset, b: dict) -> dict:
    road = ds.roads[b["road_id"]]
    zn = ", ".join(b["affected_zone_ids"][:4])
    fac = ", ".join(b["affected_facility_ids"][:4]) or "none within threshold"
    b["name"] = road.name or road.id
    b["road_type"] = road.road_type
    b["baseline_criticality"] = road.criticality_score
    b["explanation"] = (f"Losing {road.id} ({road.road_type}) reduces modeled service access for zone(s) {zn}; "
                        f"facilities losing threshold access: {fac}.")
    return b


# --------------------------------------------------------------------------------------- comparison
COMPARE_KEYS = ["exposed_population", "pop_reduced_hospital", "pop_reduced_shelter", "pop_reduced_water", "pop_reduced_any",
                "roads_affected", "roads_closed", "facilities_operationally_affected", "facilities_inaccessible_some_zone",
                "avg_hospital_time_min", "zones_no_feasible_route", "service_capacity_available", "hospitals_accessible",
                "shelters_accessible", "water_points_accessible", "shelter_shortfall", "electricity_dependent_affected",
                "resources_deployed", "budget_consumed"]


def build_comparison(base: dict, dis: dict, rec: Optional[dict]) -> list[dict]:
    rows = []
    for k in COMPARE_KEYS:
        d = METRIC_DEFINITIONS.get(k, {})
        b, x = base["metrics"][k], dis["metrics"][k]
        r = rec["metrics"][k] if rec else None
        rows.append({"key": k, "label": d.get("label", k), "unit": d.get("unit", ""), "better": d.get("better", "neutral"),
                     "baseline": b, "disaster": x, "recovery": r,
                     "delta_disaster": None if (b is None or x is None) else round(x - b, 2),
                     "delta_recovery": None if (r is None or x is None) else round(r - x, 2)})
    return rows


def recovery_summary(ds: Dataset, dis: dict, rec: dict, budget: float) -> dict:
    restored = 0.0
    for z in ds.zones.values():
        delta = dis["_reduced_count_by_zone"][z.id] - rec["_reduced_count_by_zone"][z.id]
        restored += z.estimated_population * max(0, delta) / 3.0
    fac_before = {f["id"]: f["display_status"] for f in dis["facilities"]}
    restored_f = [f["id"] for f in rec["facilities"] if fac_before.get(f["id"]) in ("inaccessible", "operationally_affected")
                  and f["display_status"] in ("accessible", "accessible_with_delay")]
    spent = rec["metrics"]["budget_consumed"]
    return {"population_access_restored": int(round(restored)),
            "facilities_restored_or_protected": restored_f,
            "budget": budget, "budget_consumed": spent, "budget_remaining": round(budget - spent, 2),
            "capacity_recovered": round(rec["metrics"]["service_capacity_available"] - dis["metrics"]["service_capacity_available"], 1),
            "estimated_restore_hours": rec["estimated_restore_hours"]}


# --------------------------------------------------------------------------------------- top-level run
STAGES = [(0, "Baseline", "Normal conditions before the event.", 0.0, False, False),
          (15, "Rainfall intensifies", "Rainfall at 35% of the scenario total; drainage begins to load.", 0.35, False, False),
          (30, "Susceptibility thresholds crossed", "Rainfall at 70%; low-lying roads and hazard zones cross Watch/Flood-risk thresholds.", 0.7, False, False),
          (45, "Road disruption", "Full rainfall; explicit road closures take effect.", 1.0, True, False),
          (60, "Service accessibility reassessed", "Power / infrastructure failures applied; accessibility recomputed on the disrupted network.", 1.0, True, True)]


def build_timeline(ds: Dataset, s: Scenario, base: dict, dis: dict, rec: Optional[dict], base_ev: dict) -> list[dict]:
    keys = ["exposed_population", "roads_affected", "roads_closed", "pop_reduced_hospital", "avg_hospital_time_min",
            "facilities_inaccessible_some_zone", "service_capacity_available"]
    tl = []
    for t, label, desc, scale, clos, fail in STAGES:
        if t == 0:
            blk = base
        elif t == 60:
            blk = dis
        else:
            blk = assess(ds, evaluate(ds, conditions_from(s, scale, clos, fail)), base_ev, with_routes=False)
        tl.append({"t_minutes": t, "label": label, "description": desc, "rainfall_mm": round(s.rainfall_mm * scale, 1),
                   "metrics": {k: blk["metrics"][k] for k in keys}, "map_state": blk["map_state"], "phase": "baseline" if t == 0 else "disaster"})
    final = rec or dis
    tl.append({"t_minutes": 90, "label": "Emergency response deployed" if rec else "No response deployed",
               "description": "Interventions applied and the model re-run." if rec else "No interventions selected; state unchanged from T+60.",
               "rainfall_mm": s.rainfall_mm, "metrics": {k: final["metrics"][k] for k in keys}, "map_state": final["map_state"],
               "phase": "recovery" if rec else "disaster"})
    return tl


def _strip(block: Optional[dict]) -> Optional[dict]:
    if block is None:
        return None
    return {k: v for k, v in block.items() if not k.startswith("_")}


def run_scenario(s: Scenario, ds: Optional[Dataset] = None, with_timeline: bool = True, with_bottlenecks: bool = True) -> dict:
    from .dataset import get_dataset
    ds = ds or get_dataset()
    validate_scenario_ids(ds, s)
    base_ev = get_baseline(ds, s)
    base = assess(ds, base_ev, base_ev)
    dis_ev = evaluate(ds, conditions_from(s))
    dis = assess(ds, dis_ev, base_ev)
    rec = rec_summary = None
    if s.deployed_resources:
        ints = resolve_interventions(ds, dis_ev, s.deployed_resources, s.resource_budget, s.resource_availability)
        rec_ev = evaluate(ds, conditions_from(s), ints)
        rec = assess(ds, rec_ev, base_ev)
        rec_summary = recovery_summary(ds, dis, rec, s.resource_budget)
    bottlenecks = []
    if with_bottlenecks:
        bottlenecks = [_describe_bottleneck(ds, b) for b in _bottleneck_scan(ds, dis_ev)[:10]]
    timeline = build_timeline(ds, s, base, dis, rec, base_ev) if with_timeline else []
    warnings = _warnings(s, base, dis, rec)
    return {
        "simulation_version": SIMULATION_VERSION, "dataset_version": ds.version, "synthetic_data": True,
        "data_label": SYNTHETIC_NOTICE, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scenario": s.model_dump(), "baseline": _strip(base), "disaster": _strip(dis), "recovery": _strip(rec),
        "comparison": build_comparison(base, dis, rec), "recovery_summary": rec_summary, "timeline": timeline,
        "bottlenecks": bottlenecks,
        "metric_definitions": METRIC_DEFINITIONS, "assumptions": ASSUMPTIONS, "warnings": warnings,
    }


def _warnings(s: Scenario, base: dict, dis: dict, rec: Optional[dict]) -> list[str]:
    w = ["Modeled estimates for comparative planning only; synthetic data; not a forecast."]
    if base["metrics"]["pop_reduced_any"] > 0:
        w.append(f"{base['metrics']['pop_reduced_any']:,} residents are already beyond an accessibility threshold at baseline (structural service gap in the synthetic district).")
    if s.rainfall_mm == 0 and not s.closed_road_ids and not s.affected_power_nodes and not s.failed_facility_ids and not s.failed_drainage_ids:
        w.append("No hazard or failure inputs selected: disaster state equals baseline.")
    if s.rainfall_mm > 150:
        w.append("Rainfall above 150 mm is at the extreme end of the model range.")
    if rec and s.resource_budget - rec["metrics"]["budget_consumed"] > 0.5 * s.resource_budget:
        w.append("More than half of the response budget is unspent; remaining interventions may offer no modeled benefit.")
    return w


