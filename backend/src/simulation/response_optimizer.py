"""Greedy benefit-to-cost response optimizer. Every candidate is scored by RE-RUNNING the simulation engine."""
from __future__ import annotations

from typing import Optional

from ..models.scenario import Intervention, Scenario
from .accessibility import SERVICES
from .interventions import ScenarioError, resolve_interventions, units_available
from .scenario_engine import (CRIT_TYPES, assess, conditions_from, evaluate, get_baseline, run_scenario,
                              validate_scenario_ids)

EPS = 1e-7
STRATEGIES = {
    "protect_critical": {"label": "Protect critical services", "weights": {"crit": 0.55, "cap": 0.20, "pop": 0.15, "time": 0.10}, "weighted_pop": False,
                         "description": "Prioritises hospitals, emergency facilities and critical infrastructure."},
    "maximize_access": {"label": "Maximize population access", "weights": {"pop": 0.65, "cap": 0.15, "time": 0.10, "crit": 0.10}, "weighted_pop": False,
                        "description": "Restores essential-service access for the greatest estimated number of people."},
    "balanced": {"label": "Balanced community response", "weights": {"pop": 0.35, "crit": 0.30, "cap": 0.20, "time": 0.15}, "weighted_pop": True,
                 "description": "Balances facility criticality, vulnerable-population exposure, travel-time gain and cost."},
}
ACTION_LABEL = {"road_clearance_team": "Clear road", "portable_generator": "Deploy generator", "temporary_medical_unit": "Temporary medical unit",
                "water_distribution_unit": "Water distribution unit", "temporary_shelter_kit": "Temporary shelter kit"}


def _reduced_units(ds, block: dict, weighted: bool) -> tuple[float, float]:
    num = den = 0.0
    for z in block["zones"]:
        zz = ds.zones[z["id"]]
        w = zz.vulnerability_weight * zz.mobility_constraint_factor if weighted else 1.0
        num += zz.estimated_population * w * z["reduced_severity"] / 3.0  # reconnecting a cut-off zone earns partial credit
        den += zz.estimated_population * w
    return num, den


def _crit_avail(ds, block: dict) -> float:
    tot = 0.0
    for f in block["facilities"]:
        if f["temporary"] or f["facility_type"] not in CRIT_TYPES:
            continue
        reachable = 1.0 if f["zones_reaching"] else 0.0
        tot += ds.facilities[f["id"]].criticality_score * f["capacity_multiplier"] * reachable
    return tot


def _benefit(ds, strat: dict, cur: dict, new: dict, base: dict) -> tuple[float, dict]:
    w = strat["weights"]
    cu, den = _reduced_units(ds, cur, strat["weighted_pop"])
    nu, _ = _reduced_units(ds, new, strat["weighted_pop"])
    pop_gain = (cu - nu) / max(den, 1.0)
    crit_total = sum(ds.facilities[f["id"]].criticality_score for f in base["facilities"] if f["facility_type"] in CRIT_TYPES)
    crit_gain = (_crit_avail(ds, new) - _crit_avail(ds, cur)) / max(crit_total, 1e-9)
    ct, nt = cur["metrics"]["avg_hospital_time_min"], new["metrics"]["avg_hospital_time_min"]
    time_gain = 0.0 if ct is None or nt is None else max(0.0, (ct - nt) / max(ct, 1.0))
    cap_gain = (new["metrics"]["service_capacity_available"] - cur["metrics"]["service_capacity_available"]) / max(base["metrics"]["service_capacity_available"], 1.0)
    benefit = w["pop"] * pop_gain + w["crit"] * crit_gain + w["time"] * time_gain + w["cap"] * cap_gain
    cu_p, _ = _reduced_units(ds, cur, False)
    nu_p, _ = _reduced_units(ds, new, False)
    parts = {"pop_gain": round(pop_gain, 5), "crit_gain": round(crit_gain, 5), "time_gain": round(time_gain, 5), "cap_gain": round(cap_gain, 5),
             "people_access_gain": int(round(cu_p - nu_p)), "capacity_gain": round(new["metrics"]["service_capacity_available"] - cur["metrics"]["service_capacity_available"], 1)}
    return benefit, parts


def _targets(ds, dis_ev: dict, rtype: str) -> list[str]:
    if rtype == "road_clearance_team":
        return [rid for rid, r in dis_ev["roads"].items() if r["status"] in ("closed", "restricted")]
    if rtype == "portable_generator":
        t = [fid for fid, f in ds.facilities.items() if f.power_dependent and dis_ev["ops"][fid]["multiplier"] < 1.0]
        return t + [d for d, v in dis_ev["drainage"].items() if v["failed"]]
    return list(ds.zones)


def optimize(s: Scenario, strategy: str = "balanced", ds=None) -> dict:
    from .dataset import get_dataset
    ds = ds or get_dataset()
    if strategy not in STRATEGIES:
        raise ScenarioError(f"Unknown strategy {strategy}")
    strat = STRATEGIES[strategy]
    validate_scenario_ids(ds, s)
    cond = conditions_from(s)
    base_ev = get_baseline(ds, s)
    base = assess(ds, base_ev, base_ev, with_routes=False)
    dis_ev = evaluate(ds, cond)
    dis = assess(ds, dis_ev, base_ev, with_routes=False)

    pool: list[tuple[str, str]] = []
    for res in ds.resources.values():
        for t in _targets(ds, dis_ev, res.resource_type):
            pool.append((res.id, t))
    # One-time resolve of each (resource, target) pair against the disaster state.
    cands = {}
    for rid, t in pool:
        res = ds.resources[rid]
        if units_available(res, s.resource_availability) <= 0:
            continue
        try:
            r = resolve_interventions(ds, dis_ev, [Intervention(resource_id=rid, resource_type=res.resource_type, target_id=t)], 1e9, 1.0)[0]
        except ScenarioError:
            continue
        cands[(rid, t)] = r

    chosen: list[dict] = []
    used_units: dict[str, int] = {}
    used_targets: set[tuple[str, str]] = set()
    remaining = s.resource_budget
    current = dis
    trace = []
    # Prune to candidates with standalone benefit (documented approximation).
    standalone = {}
    for key, r in cands.items():
        new = assess(ds, evaluate(ds, cond, [r]), base_ev, with_routes=False)
        b, _ = _benefit(ds, strat, dis, new, base)
        if b > EPS:
            standalone[key] = (b, r)
    live = dict(standalone)
    while live:
        best = None
        for key, (_, r) in live.items():
            res = ds.resources[r["resource_id"]]
            if (r["resource_type"], r["target_id"]) in used_targets:
                continue
            if used_units.get(res.id, 0) >= units_available(res, s.resource_availability):
                continue
            if r["cost"] > remaining + 1e-9:
                continue
            new = assess(ds, evaluate(ds, cond, chosen + [r]), base_ev, with_routes=False)
            b, parts = _benefit(ds, strat, current, new, base)
            if b <= EPS:
                continue
            ratio = b / max(r["cost"], 0.1)
            rank = (ratio, -r["deploy_minutes"], r["resource_id"], r["target_id"])
            if best is None or rank > best[0]:
                best = (rank, key, r, b, parts, new)
        if best is None:
            break
        _, key, r, b, parts, new = best
        chosen.append(r)
        used_units[r["resource_id"]] = used_units.get(r["resource_id"], 0) + 1
        used_targets.add((r["resource_type"], r["target_id"]))
        remaining -= r["cost"]
        current = new
        trace.append({**r, "benefit": round(b, 5), "benefit_cost_ratio": round(b / max(r["cost"], 0.1), 5), **parts,
                      "action": ACTION_LABEL[r["resource_type"]],
                      "reasoning": _reason(strat, r, parts)})
        del live[key]

    not_done = []
    for key, (b, r) in sorted(standalone.items(), key=lambda kv: -kv[1][0] / max(kv[1][1]["cost"], 0.1)):
        if (r["resource_type"], r["target_id"]) in used_targets:
            continue
        res = ds.resources[r["resource_id"]]
        if r["cost"] > remaining + 1e-9:
            why = f"Cost {r['cost']:.1f} exceeds remaining budget {remaining:.1f}"
        elif used_units.get(res.id, 0) >= units_available(res, s.resource_availability):
            why = f"No remaining units of {res.name}"
        else:
            why = "No additional modeled benefit after earlier interventions"
        not_done.append({"resource_id": r["resource_id"], "resource_type": r["resource_type"], "target_id": r["target_id"],
                         "target_name": r["target_name"], "cost": r["cost"], "standalone_benefit": round(b, 5), "reason": why})
    out_scn = s.model_copy(update={"strategy": strategy, "deployed_resources": [
        Intervention(resource_id=c["resource_id"], resource_type=c["resource_type"], target_id=c["target_id"]) for c in chosen]})
    resolved = resolve_interventions(ds, dis_ev, out_scn.deployed_resources, s.resource_budget, s.resource_availability) if chosen else []
    by_type: dict[str, int] = {}
    for c in chosen:
        by_type[c["resource_type"]] = by_type.get(c["resource_type"], 0) + 1
    return {"strategy": strategy, "strategy_label": strat["label"], "strategy_description": strat["description"],
            "weights": strat["weights"], "interventions": trace, "resolved": resolved,
            "budget": s.resource_budget, "budget_consumed": round(sum(c["cost"] for c in chosen), 2),
            "budget_remaining": round(remaining, 2), "resources_by_type": by_type, "not_completed": not_done[:8],
            "candidates_evaluated": len(cands), "candidates_with_benefit": len(standalone),
            "scenario": out_scn.model_dump(), "method": "Greedy selection by benefit-to-cost ratio; every candidate is scored by re-running the deterministic engine. Candidates with no standalone modeled benefit are pruned."}


def _reason(strat: dict, r: dict, p: dict) -> str:
    bits = []
    if p["people_access_gain"]:
        bits.append(f"restores modeled service access for ~{p['people_access_gain']:,} people-service units")
    if p["capacity_gain"]:
        bits.append(f"adds {p['capacity_gain']:g} capacity units")
    if p["crit_gain"] > 0:
        bits.append("protects a critical facility")
    if p["time_gain"] > 0:
        bits.append("shortens hospital travel time")
    return f"{ACTION_LABEL[r['resource_type']]} - {r['target_name']}: " + ("; ".join(bits) or "marginal modeled benefit") + f" (cost {r['cost']:.1f}, ready in {r['deploy_minutes']:.0f} min)."


def optimize_and_run(s: Scenario, strategy: str, ds=None) -> dict:
    plan = optimize(s, strategy, ds)
    result = run_scenario(Scenario(**plan["scenario"]), ds)
    return {"plan": plan, "simulation": result}
