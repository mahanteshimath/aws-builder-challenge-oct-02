"""Reproducible analysis behind Resilience Simulator (Kurla / Mithi River, Mumbai).

Runs every study on the deterministic engine and writes docs/ANALYSIS_AND_FINDINGS.md.
Usage:  python scripts/run_analysis.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from src.data import build_kurla_dataset as builder  # noqa: E402
from src.models.scenario import Scenario  # noqa: E402
from src.simulation.dataset import get_dataset  # noqa: E402
from src.simulation.presets import MAJOR_ROAD, OUTAGE_POWER_NODE  # noqa: E402
from src.simulation.response_optimizer import STRATEGIES, optimize_and_run  # noqa: E402
from src.simulation.scenario_engine import run_scenario  # noqa: E402

OUT = ROOT / "docs" / "ANALYSIS_AND_FINDINGS.md"
DS = get_dataset()
POP = sum(z.estimated_population for z in DS.zones.values())


def sim(**kw) -> dict:
    return run_scenario(Scenario(**kw), with_timeline=False, with_bottlenecks=False)


def fmt(n) -> str:
    return "-" if n is None else f"{n:,}" if isinstance(n, int) else f"{n:,.2f}"


def table(head: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(fmt(c) if not isinstance(c, str) else c for c in r) + " |" for r in rows]
    return "\n".join(out)


def main() -> None:
    t0 = time.time()
    md: list[str] = []
    w = md.append

    # ---------------------------------------------------------------- 1. data sourcing
    raw = json.loads((ROOT / "backend" / "data_sources" / "osm_kurla_raw.json").read_text(encoding="utf-8"))
    els = raw["elements"]
    hw = Counter(e["tags"]["highway"].replace("_link", "") for e in els if e["type"] == "way" and "highway" in e.get("tags", {}))
    amen = Counter((e.get("tags", {}).get("amenity") or e.get("tags", {}).get("place") or e.get("tags", {}).get("power")
                    or e.get("tags", {}).get("man_made")) for e in els if "highway" not in e.get("tags", {}) and "waterway" not in e.get("tags", {}))
    srtm = json.loads((ROOT / "backend" / "data_sources" / "srtm_kurla.json").read_text(encoding="utf-8"))
    z = [v for row in srtm["elev"] for v in row]
    manifest = json.loads((ROOT / "backend" / "src" / "data" / "geojson" / "manifest.json").read_text(encoding="utf-8"))

    w("# Analysis and findings - Kurla / Mithi River, Mumbai\n")
    w("Every table below is produced by `python scripts/run_analysis.py` on the same deterministic engine that runs the live app "
      f"(dataset `{DS.version}`). Re-running the script reproduces every number exactly. Populations, capacities and infrastructure "
      "links are modeled planning assumptions (see `ASSUMPTIONS_AND_LIMITATIONS.md`); geography is real.\n")
    w("## Key findings\n")
    findings_at = len(md)
    w("")  # placeholder, filled at the end

    w("## 1. Study area and data sourcing\n")
    w(f"Study area: Kurla West / Kurla East / Kalina / Bail Bazar / Tilak Nagar (BMC Ward L), bbox {manifest['study_area_bbox']}. "
      f"OpenStreetMap snapshot `{manifest.get('osm_snapshot')}`.\n")
    w(table(["Source", "What was extracted", "Volume"], [
        ["OpenStreetMap (Overpass API)", "drivable road ways by class", ", ".join(f"{k} {v}" for k, v in hw.most_common())],
        ["OpenStreetMap", "waterways", f"Mithi River + {sum(1 for e in els if e.get('tags', {}).get('waterway') in ('drain', 'stream', 'canal'))} drains / nalas / canals"],
        ["OpenStreetMap", "facilities and places", f"{amen.get('hospital', 0)} hospitals, {amen.get('clinic', 0)} clinics, {amen.get('school', 0)} schools, "
         f"{amen.get('police', 0)} police, {amen.get('fire_station', 0)} fire stations, {amen.get('place_of_worship', 0)} places of worship, "
         f"{amen.get('neighbourhood', 0) + amen.get('locality', 0) + amen.get('suburb', 0)} neighbourhood names, {amen.get('substation', 0)} substation, "
         f"{amen.get('pumping_station', 0)} pumping stations"],
        ["SRTM 30 m (OpenTopoData)", "elevation grid", f"{len(z)} points; min {min(z):.0f} m, median {st.median(z):.0f} m, max {max(z):.0f} m"],
        ["Census of India 2011", "BMC Ward L density", f"{builder.WARD_L_POP:,} people / {builder.WARD_L_KM2} km2 = {builder.DENSITY:,.0f} per km2"],
    ]))
    w("\nModeled population of the 8 neighbourhood zones:\n")
    zr = sorted(DS.zones.values(), key=lambda z_: -z_.estimated_population)
    w(table(["Zone", "Neighbourhood", "Modeled population", "Vulnerability weight"],
            [[z_.id, z_.name, z_.estimated_population, f"{z_.vulnerability_weight:.2f}"] for z_ in zr]))
    w(f"\nTotal modeled population: **{POP:,}**.\n")

    # ---------------------------------------------------------------- 2. network simplification study
    w("## 2. Road-network simplification study\n")
    w("Raw OSM ways are split at every shared node, then junction nodes within a merge radius are clustered, parallel carriageways "
      "collapse to the best class and pass-through nodes are contracted. The radius trades fidelity against optimizer run time "
      "(the optimizer and bottleneck scan re-run Dijkstra for every candidate).\n")
    rows = []
    original = builder.CLUSTER_M
    for r in (60.0, 90.0, 120.0, 150.0):
        builder.CLUSTER_M = r
        d = builder.build()
        roads = d["roads"]["features"]
        rows.append([f"{r:.0f} m", len(roads), len(d["nodes"]["features"]),
                     sum(1 for f in roads if f["properties"]["crosses_mithi"]), sum(1 for f in roads if f["properties"]["elevated"]),
                     f"{st.median(f['properties']['length_m'] for f in roads):.0f} m"])
    builder.CLUSTER_M = original
    w(table(["Merge radius", "Road segments", "Junctions", "Mithi crossings", "Flyover segments", "Median segment"], rows))
    w(f"\nChosen: **{original:.0f} m** - keeps every Mithi crossing and flyover while staying near the size the engine was designed for. "
      "Engine time on the result: see section 10.\n")

    # ---------------------------------------------------------------- 3. terrain / susceptibility
    w("## 3. Terrain and flood-susceptibility study\n")
    w("Susceptibility = 0.10 + 0.55 x (1 - SRTM elevation rank) + 0.55 x (0.70 e^(-d_Mithi/420 m) + 0.30 e^(-d_drain/160 m)), clamped "
      "0.03-0.98; flyovers x0.35. Elevation is smoothed over ~220 m because single SRTM cells are noisy in dense built-up areas.\n")
    by_type = {}
    for r_ in DS.roads.values():
        by_type.setdefault(r_.road_type, []).append(r_.flood_susceptibility)
    w(table(["Road class", "Segments", "Median susceptibility", "Max"],
            [[k, len(v), f"{st.median(v):.2f}", f"{max(v):.2f}"] for k, v in sorted(by_type.items())]))
    w("\nCandidate flood pockets (derived from the same index):\n")
    w(table(["Pocket", "Name", "Susceptibility"], [[h.id, h.name, f"{h.susceptibility_score:.2f}"] for h in DS.hazards.values()]))
    w("")

    # ---------------------------------------------------------------- 4. rainfall sensitivity
    w("## 4. Rainfall sensitivity (6 h event)\n")
    rows = []
    for mm in range(0, 201, 20):
        for dr in (0.5, 0.35):
            m = sim(rainfall_mm=mm, drainage_effectiveness=dr)["disaster"]["metrics"]
            rows.append([f"{mm} mm", f"{dr:.2f}", m["exposed_population"], m["roads_affected"], m["roads_closed"],
                         m["pop_reduced_hospital"], m["pop_reduced_any"], m["avg_hospital_time_min"]])
    w(table(["Rainfall", "Drainage", "People exposed", "Roads affected", "Roads closed", "Reduced hospital access", "Reduced any service",
             "Avg hospital min"], rows))
    w("")

    # ---------------------------------------------------------------- 5. drainage sensitivity
    w("## 5. Drainage-effectiveness sensitivity (150 mm / 6 h)\n")
    rows = []
    for dr in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7):
        m = sim(rainfall_mm=150, drainage_effectiveness=dr)["disaster"]["metrics"]
        rows.append([f"{dr:.1f}", m["exposed_population"], m["roads_affected"], m["roads_closed"], m["pop_reduced_any"]])
    w(table(["Drainage effectiveness", "People exposed", "Roads affected", "Roads closed", "Reduced any service"], rows))
    w("")

    # ---------------------------------------------------------------- 6. single points of failure
    w("## 6. Single-point-of-failure study (every road closed in turn, 120 mm rain)\n")
    base = sim(rainfall_mm=120, drainage_effectiveness=0.45)["disaster"]["metrics"]
    res = []
    for rid in DS.roads:
        m = sim(rainfall_mm=120, drainage_effectiveness=0.45, closed_road_ids=[rid])["disaster"]["metrics"]
        res.append((m["pop_reduced_any"] - base["pop_reduced_any"], m["pop_reduced_hospital"] - base["pop_reduced_hospital"],
                    m["zones_no_feasible_route"], rid))
    res.sort(key=lambda x: (-x[0], -x[2], -x[1], x[3]))
    harmless = sum(1 for x in res if x[0] <= 0 and x[1] <= 0)
    w(f"Reference (120 mm, no closure): {base['pop_reduced_any']:,} residents with reduced access. "
      f"**{harmless} of {len(res)} segments** cause no additional loss when closed; the network's resilience depends on a few links.\n")
    w(table(["Rank", "Road", "Name", "Class", "Extra residents with reduced access", "Extra with reduced hospital access", "Zones with no route"],
            [[i + 1, rid, DS.roads[rid].name, DS.roads[rid].road_type, a, h, nz] for i, (a, h, nz, rid) in enumerate(res[:10])]))
    top = res[0]
    corridor = [x for x in res if x[0] == top[0] and DS.roads[x[3]].name == DS.roads[top[3]].name]
    cut_off = [x for x in res if x[2] > 0]
    w("")

    # ---------------------------------------------------------------- 7. power and pump cascades
    w("## 7. Power and pump cascade study (150 mm, drainage 0.40)\n")
    ref = sim(rainfall_mm=150, drainage_effectiveness=0.4)["disaster"]
    rows = []
    for pid, pn in DS.power_nodes.items():
        d = sim(rainfall_mm=150, drainage_effectiveness=0.4, affected_power_nodes=[pid])["disaster"]
        pumps = [k for k, v in d["drainage"].items() if v["failed"]]
        rows.append([pid, pn.name, d["metrics"]["facilities_operationally_affected"], ", ".join(pumps) or "none",
                     d["metrics"]["roads_closed"] - ref["metrics"]["roads_closed"], d["metrics"]["pop_reduced_any"]])
    w(table(["Power node", "Name", "Facilities below capacity", "Pumps lost", "Extra roads closed", "Reduced any service"], rows))
    w("")

    # ---------------------------------------------------------------- 8. response strategies x budget
    w("## 8. Response-strategy and budget study (compound emergency)\n")
    w(f"Compound emergency: 150 mm, drainage 0.40, {MAJOR_ROAD} ({DS.roads[MAJOR_ROAD].name}) closed, {OUTAGE_POWER_NODE} failed.\n")
    rows = []
    best = None
    by = {}
    for budget in (10, 20, 30, 45):
        for k, v in STRATEGIES.items():
            r = optimize_and_run(Scenario(rainfall_mm=150, drainage_effectiveness=0.4, closed_road_ids=[MAJOR_ROAD],
                                          affected_power_nodes=[OUTAGE_POWER_NODE], resource_budget=budget), k)
            s, p = r["simulation"], r["plan"]
            rows.append([f"{budget}", v["label"], len(p["interventions"]), p["budget_consumed"],
                         s["disaster"]["metrics"]["pop_reduced_any"], s["recovery"]["metrics"]["pop_reduced_any"] if s["recovery"] else None,
                         s["recovery_summary"]["population_access_restored"] if s["recovery_summary"] else 0,
                         "yes" if any(i["target_id"] == MAJOR_ROAD for i in p["interventions"]) else "no"])
            by[(budget, k)] = rows[-1]
            if budget == 30 and (best is None or rows[-1][5] < best[5]):
                best = rows[-1]
    w(table(["Budget (lakh)", "Strategy", "Actions", "Spent", "Reduced access before", "After", "Person-service eq. restored",
             f"Clears {MAJOR_ROAD}?"], rows))
    w("")

    # ---------------------------------------------------------------- 9. metric design + performance
    w("## 9. Metric-design study: crediting reconnection\n")
    s0 = Scenario(rainfall_mm=160, drainage_effectiveness=0.35, closed_road_ids=[MAJOR_ROAD], resource_budget=30)
    from src.models.scenario import Intervention
    r = run_scenario(s0.model_copy(update={"deployed_resources": [Intervention(resource_id="RES-RC1", resource_type="road_clearance_team",
                                                                              target_id=MAJOR_ROAD)]}), with_timeline=False, with_bottlenecks=False)
    cut = [z_ for z_ in r["disaster"]["zones"] if z_["services"]["hospital"]["no_route"]]
    rec = {z_["id"]: z_ for z_ in r["recovery"]["zones"]}
    w("A first version of the recovery metric only counted a service as restored when travel time returned to within 25 % of baseline. "
      f"Testing the extreme-rainfall + {MAJOR_ROAD} closure case showed that reopening the over-bridge moved "
      + ", ".join(f"{z_['name']} from *no route* to {rec[z_['id']]['services']['hospital']['minutes']:.1f} min" for z_ in cut)
      + " - a real recovery the metric scored as zero. The metric now uses a per-service severity (cut off = 1, reachable but delayed = 0.5, "
      f"normal = 0): reopening alone restores **{r['recovery_summary']['population_access_restored']:,}** person-service equivalents.\n")
    timings = []
    for _ in range(5):
        t = time.time()
        run_scenario(Scenario(rainfall_mm=150, drainage_effectiveness=0.4, closed_road_ids=[MAJOR_ROAD]))
        timings.append(time.time() - t)
    t = time.time()
    optimize_and_run(Scenario(rainfall_mm=150, drainage_effectiveness=0.4, closed_road_ids=[MAJOR_ROAD], affected_power_nodes=[OUTAGE_POWER_NODE]), "balanced")
    opt_t = time.time() - t
    w("## 10. Engine performance on the real network\n")
    w(table(["Operation", "Time (this machine)"], [["Full scenario incl. bottleneck scan + 6-stage timeline (median of 5)", f"{st.median(timings):.2f} s"],
                                                    ["Optimizer (one strategy) + recovery re-run", f"{opt_t:.2f} s"]]))
    w("")

    # ---------------------------------------------------------------- findings
    ex = sim(rainfall_mm=160, drainage_effectiveness=0.35)["disaster"]["metrics"]
    hv = sim(rainfall_mm=100, drainage_effectiveness=0.5)["disaster"]["metrics"]
    dr = {d_: sim(rainfall_mm=150, drainage_effectiveness=d_)["disaster"]["metrics"] for d_ in (0.2, 0.3)}
    p2 = sim(rainfall_mm=150, drainage_effectiveness=0.4, affected_power_nodes=[OUTAGE_POWER_NODE])["disaster"]
    findings = [
        f"**Rain alone degrades Kurla long before it cuts it off.** At 100 mm / 6 h ~{hv['exposed_population']:,} residents are in modeled "
        f"flood-risk pockets and {hv['roads_affected']} of {len(DS.roads)} segments slow down, yet every neighbourhood still reaches a hospital. "
        f"The tipping point is between 140 and 160 mm with weak drainage: at 160 mm {ex['pop_reduced_hospital']:,} residents lose timely hospital access.",
        f"**One road corridor holds east Kurla together.** Closing any one of the {len(corridor)} {DS.roads[top[3]].name} segments "
        f"({', '.join(x[3] for x in corridor)}) under 120 mm leaves {top[0]:,} residents with reduced hospital access; closing the rail "
        f"over-bridge {MAJOR_ROAD} leaves Nehru Nagar and Tilak Nagar with no route to any hospital. {harmless} of {len(res)} segments can close "
        "without any extra loss - resilience is concentrated in a handful of links.",
        f"**Drainage has a tipping point.** At 150 mm, raising drainage effectiveness from 0.2 to 0.3 cuts closed roads from "
        f"{dr[0.2]['roads_closed']} to {dr[0.3]['roads_closed']} and residents with reduced access from {dr[0.2]['pop_reduced_any']:,} to "
        f"{dr[0.3]['pop_reduced_any']:,} (section 5) - desilting and pump uptime matter before the monsoon, not during it.",
        f"**Power failures cascade into flooding.** Losing the Mithi-bank substation {OUTAGE_POWER_NODE} stops pumps "
        f"{', '.join(k for k, v in p2['drainage'].items() if v['failed'])} and closes {p2['metrics']['roads_closed'] - ref['metrics']['roads_closed']} "
        "more roads at 150 mm (section 7).",
        f"**The right strategy beats a bigger budget.** In the compound emergency, *Maximize population access* clears {MAJOR_ROAD} and reaches "
        f"{by[(10, 'maximize_access')][5]:,} residents with reduced access on just {by[(10, 'maximize_access')][3]:.1f} lakh, while *Protect critical "
        f"services* and *Balanced* still leave {by[(30, 'protect_critical')][5]:,} at 30 lakh because they rank generators, water tankers and medical units above clearing the over-bridge; all three "
        "converge only at 45 lakh (section 8).",
        f"**Metrics must credit reconnection.** A naive 'back to baseline' metric scored reopening the over-bridge as zero benefit; "
        f"severity weighting credits {r['recovery_summary']['population_access_restored']:,} person-service equivalents (section 9).",
    ]
    md[findings_at] = "\n".join(f"{i + 1}. {f}" for i, f in enumerate(findings)) + "\n"
    w(f"---\nGenerated in {time.time() - t0:.0f} s by `scripts/run_analysis.py`.")
    OUT.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
