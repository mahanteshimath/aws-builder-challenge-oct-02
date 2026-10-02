"""Compact, grounded fact packets and prompt templates for the situation brief."""
from __future__ import annotations

import json
import re

SECTION_KEYS = ["situation_summary", "top_impacts", "critical_bottlenecks", "services_requiring_attention",
                "immediate_actions", "followup_actions", "resource_tradeoffs", "uncertainties"]
LIST_KEYS = set(SECTION_KEYS) - {"situation_summary"}
ID_PATTERN = re.compile(r"\b(?:R-\d{3}|H-\d{2}|S-\d{2}|W-\d{2}|E-\d{2}|SC-\d{2}|Z-\d{2}|P-\d{2}|D-\d{2}|HZ-\d{2}|T(?:MU|WP|SH)-Z-\d{2})\b")

METRIC_KEYS = ["exposed_population", "pop_reduced_hospital", "pop_reduced_shelter", "pop_reduced_water", "pop_reduced_any",
               "roads_affected", "roads_closed", "facilities_operationally_affected", "facilities_inaccessible_some_zone",
               "avg_hospital_time_min", "zones_no_feasible_route", "service_capacity_available", "hospitals_accessible",
               "shelters_accessible", "water_points_accessible", "shelter_demand", "shelter_shortfall",
               "electricity_dependent_affected", "resources_deployed", "budget_consumed"]

SYSTEM_PROMPT = (
    "You are a disaster-resilience analyst writing a brief for emergency planners. You explain the output of a deterministic "
    "simulation of Kurla / Mithi River, Mumbai: real OpenStreetMap geography with MODELED populations, capacities and infrastructure links. Rules: (1) Use ONLY the JSON facts provided; never invent roads, facilities, "
    "zones, numbers or events. (2) Cite specific identifiers (e.g. R-059, H-01, Z-02) and metrics from the facts. (3) Call figures "
    "'modeled estimates'; never present them as real-world impacts or forecasts. (4) Do not claim a road or facility is affected "
    "unless the facts show it. (5) Be concise. Respond with ONE JSON object only (no markdown) with exactly these keys: "
    "situation_summary (string), top_impacts (array of exactly 3 strings), critical_bottlenecks (array of strings), "
    "services_requiring_attention (array of strings), immediate_actions (array of strings), followup_actions (array of strings), "
    "resource_tradeoffs (array of strings), uncertainties (array of strings).")


def _m(block: dict | None) -> dict | None:
    return None if block is None else {k: block["metrics"].get(k) for k in METRIC_KEYS}


def build_facts(sim: dict) -> dict:
    dis, rec, s = sim["disaster"], sim["recovery"], sim["scenario"]
    sev = {"closed": 0, "restricted": 1, "degraded": 2}
    roads = sorted(((rid, r) for rid, r in dis["roads"].items() if r["status"] != "open"),
                   key=lambda kv: (sev[kv[1]["status"]], -kv[1]["risk"], kv[0]))[:15]
    facs = [f for f in dis["facilities"] if f["display_status"] != "accessible"]
    facs.sort(key=lambda f: (f["display_status"] != "inaccessible", f["id"]))
    zones = [{"id": z["id"], "name": z["name"], "population": z["population"], "exposed_population": z["exposed_population"],
              "status": z["status"], "hospital_minutes": z["services"]["hospital"]["minutes"],
              "baseline_hospital_minutes": z["services"]["hospital"]["baseline_minutes"]} for z in dis["zones"]]
    facts = {
        "simulation_version": sim["simulation_version"], "dataset_version": sim["dataset_version"], "synthetic_data": sim.get("synthetic_data", False),
        "scenario": {k: s[k] for k in ("name", "rainfall_mm", "duration_hours", "drainage_effectiveness", "closed_road_ids",
                                       "affected_power_nodes", "failed_drainage_ids", "failed_facility_ids", "resource_budget", "strategy")},
        "metrics": {"baseline": _m(sim["baseline"]), "disaster": _m(dis), "recovery": _m(rec)},
        "affected_roads": [{"id": rid, "status": r["status"], "risk": r["risk"], "reason": r["reason"]} for rid, r in roads],
        "affected_facilities": [{"id": f["id"], "name": f["name"], "type": f["facility_type"], "operational_status": f["operational_status"],
                                 "accessibility_status": f["accessibility_status"], "zones_lost": f["zones_lost"],
                                 "reason": f["operational_reason"]} for f in facs[:14]],
        "zones": zones,
        "critical_bottlenecks": [{"road_id": b["road_id"], "score": b["score"], "affected_zone_ids": b["affected_zone_ids"],
                                  "affected_facility_ids": b["affected_facility_ids"]} for b in sim["bottlenecks"][:5]],
        "response": None if not rec else {
            "strategy": s.get("strategy"),
            "interventions": [{"resource": i["resource_name"], "type": i["resource_type"], "target_id": i["target_id"],
                               "cost": i["cost"], "deploy_minutes": i["deploy_minutes"]} for i in rec["interventions"]],
            "budget_remaining": sim["recovery_summary"]["budget_remaining"],
            "population_access_restored": sim["recovery_summary"]["population_access_restored"]},
        "assumptions": sim["assumptions"][:6],
        "limitations": ["Real geography but modeled populations, capacities and infrastructure links", "Not a flood forecast", "Modeled estimates for comparative planning only"],
    }
    return facts


def allowed_ids(facts: dict) -> set[str]:
    return set(ID_PATTERN.findall(json.dumps(facts)))


def user_prompt(facts: dict, brief_type: str) -> str:
    style = "executive (short, decision-oriented)" if brief_type == "executive" else "situation (detailed, evidence-cited)"
    return f"Write a {style} brief as the specified JSON object.\nFACTS:\n{json.dumps(facts, separators=(',', ':'))}"
