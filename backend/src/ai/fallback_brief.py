"""Deterministic rule-based situation brief (used when Bedrock is unavailable). Evidence-grounded, no AI."""
from __future__ import annotations

from .prompt_templates import SECTION_KEYS


def _fmt(n):
    return "n/a" if n is None else f"{n:,}" if isinstance(n, int) else f"{n:g}"


def fallback_brief(facts: dict) -> dict:
    sc = facts["scenario"]
    d, b = facts["metrics"]["disaster"], facts["metrics"]["baseline"]
    rec = facts["metrics"]["recovery"]
    summary = (f"Scenario '{sc['name']}' (modeled; real Kurla geography, modeled attributes): {sc['rainfall_mm']:g} mm over {sc['duration_hours']:g} h with drainage effectiveness "
               f"{sc['drainage_effectiveness']:g}. Estimated exposure is {_fmt(d['exposed_population'])} people; {d['roads_affected']} road segments are affected "
               f"({d['roads_closed']} closed); {d['facilities_operationally_affected']} facilities run below normal capacity and "
               f"{d['zones_no_feasible_route']} zone(s) have no feasible route to at least one essential service within threshold.")
    impacts = [
        f"Exposure: {_fmt(d['exposed_population'])} people are in potentially affected zones (baseline {_fmt(b['exposed_population'])}); "
        f"vulnerable-population shelter demand is estimated at {_fmt(d['shelter_demand'])} against {_fmt(d['shelter_shortfall'])} shortfall.",
        f"Hospital access: {_fmt(d['pop_reduced_hospital'])} people have reduced hospital accessibility; average modeled hospital travel time is "
        f"{_fmt(d['avg_hospital_time_min'])} min versus {_fmt(b['avg_hospital_time_min'])} min at baseline; {d['hospitals_accessible']} of 4 hospitals remain reachable.",
        f"Network and power: {d['roads_closed']} roads closed, {d['facilities_inaccessible_some_zone']} facilities lose access from at least one zone, "
        f"and {d['electricity_dependent_affected']} electricity-dependent facilities are below normal capacity.",
    ]
    bn = [f"Road {x['road_id']} (score {x['score']}): losing it cuts modeled access for zone(s) {', '.join(x['affected_zone_ids']) or 'none'}"
          f"{' to ' + ', '.join(x['affected_facility_ids'][:4]) if x['affected_facility_ids'] else ''}." for x in facts["critical_bottlenecks"][:3]] \
        or ["No bottleneck roads identified in this scenario."]
    attention = [f"{f['id']} {f['name']}: {f['accessibility_status'].replace('_', ' ')}, {f['operational_status']} - {f['reason']}"
                 for f in facts["affected_facilities"][:6]] or ["No essential service is modeled as affected."]
    imm, fol, trade = [], [], []
    closed = [r for r in facts["affected_roads"] if r["status"] == "closed"]
    explicit = list(sc.get("closed_road_ids") or [])
    closed_ids = explicit + [r["id"] for r in closed if r["id"] not in explicit]  # user-selected closures first
    if closed_ids:
        imm.append(f"Prioritise reopening or bypass planning for closed road(s) {', '.join(closed_ids[:4])}.")
    off = [f for f in facts["affected_facilities"] if f["operational_status"] != "operational"]
    if off:
        imm.append(f"Secure backup power for {', '.join(f['id'] for f in off[:4])}.")
    if facts["critical_bottlenecks"]:
        imm.append(f"Pre-position crews near bottleneck road {facts['critical_bottlenecks'][0]['road_id']}.")
    imm = imm or ["Maintain monitoring; no modeled impact requires immediate action."]
    fol.append("Re-run the scenario with alternative drainage and closure assumptions to test sensitivity.")
    if any(r["id"] for r in facts["affected_roads"]):
        fol.append("Review drainage upgrades for the roads listed as restricted or closed.")
    resp = facts["response"]
    if resp:
        acts = ", ".join(f"{i['type'].replace('_', ' ')} at {i['target_id']}" for i in resp["interventions"][:6]) or "none"
        trade.append(f"Strategy '{resp['strategy']}' deploys {len(resp['interventions'])} action(s): {acts}.")
        trade.append(f"Budget remaining {resp['budget_remaining']:g} of {sc['resource_budget']:g} (illustrative INR lakh); modeled access restored: "
                     f"{_fmt(resp['population_access_restored'])} person-service equivalents; residual reduced-access population {_fmt(rec['pop_reduced_any'])}.")
    else:
        trade.append(f"No response deployed. Budget available: {sc['resource_budget']:g}. Run the optimizer to compare strategies.")
    unc = ["Geography is real (OpenStreetMap) but populations, capacities and infrastructure links are modeled; results are modeled estimates, not forecasts.",
           "Flood thresholds are configurable and uncalibrated; population exposure assumes uniform density within zones."]
    return dict(zip(SECTION_KEYS, [summary, impacts, bn, attention, imm, fol, trade, unc]))
