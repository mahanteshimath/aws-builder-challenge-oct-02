"""Scenario comparison across two or more scenario configurations."""
from __future__ import annotations

from ..models.scenario import Scenario
from .scenario_engine import COMPARE_KEYS, run_scenario
from .metrics import METRIC_DEFINITIONS


def compare_scenarios(scenarios: list[Scenario], ds=None) -> dict:
    sims = [run_scenario(s, ds, with_timeline=False, with_bottlenecks=False) for s in scenarios]
    rows = []
    for k in COMPARE_KEYS:
        d = METRIC_DEFINITIONS.get(k, {})
        vals = []
        for sim in sims:
            final = sim["recovery"] or sim["disaster"]
            vals.append({"scenario_id": sim["scenario"]["id"], "scenario_name": sim["scenario"]["name"],
                         "disaster": sim["disaster"]["metrics"][k], "final": final["metrics"][k], "has_recovery": sim["recovery"] is not None})
        first = vals[0]["final"]
        for v in vals:
            v["delta_vs_first"] = None if (v["final"] is None or first is None) else round(v["final"] - first, 2)
        rows.append({"key": k, "label": d.get("label", k), "unit": d.get("unit", ""), "better": d.get("better", "neutral"), "values": vals})
    zones = []
    for z in sims[0]["disaster"]["zones"]:
        entry = {"zone_id": z["id"], "zone_name": z["name"], "scenarios": []}
        for sim in sims:
            blk = sim["recovery"] or sim["disaster"]
            zz = next(x for x in blk["zones"] if x["id"] == z["id"])
            entry["scenarios"].append({"scenario_id": sim["scenario"]["id"], "status": zz["status"],
                                       "hospital_minutes": zz["services"]["hospital"]["minutes"],
                                       "reduced_service_count": zz["reduced_service_count"]})
        zones.append(entry)
    trade = [{"scenario_id": s["scenario"]["id"], "scenario_name": s["scenario"]["name"],
              "budget": s["scenario"]["resource_budget"],
              "budget_consumed": (s["recovery"] or s["disaster"])["metrics"]["budget_consumed"],
              "resources_deployed": (s["recovery"] or s["disaster"])["metrics"]["resources_deployed"],
              "population_access_restored": (s["recovery_summary"] or {}).get("population_access_restored", 0)} for s in sims]
    return {"simulation_version": sims[0]["simulation_version"], "synthetic_data": sims[0]["synthetic_data"], "data_label": sims[0]["data_label"],
            "metrics": rows, "zone_accessibility": zones, "resource_tradeoffs": trade}
