"""Validation and costing of response interventions. Client-supplied costs are never trusted."""
from __future__ import annotations

import math

from ..models.scenario import Intervention
from .road_network import dijkstra, haversine_m


class ScenarioError(ValueError):
    """Raised for scenario inputs that violate constraints (unknown IDs, budget, capacity)."""


TEMP_FACILITY = {  # resource_type -> (id prefix, facility_type, label)
    "temporary_medical_unit": ("TMU", "hospital", "Temporary medical unit"),
    "water_distribution_unit": ("TWP", "water", "Temporary water distribution"),
    "temporary_shelter_kit": ("TSH", "shelter", "Temporary shelter"),
}


def units_available(res, availability: float) -> int:
    return int(math.floor(res.quantity_available * availability + 1e-9))


def target_position(ds, rtype: str, target_id: str):
    if rtype == "road_clearance_team":
        return ds.roads[target_id].geometry[1]
    if rtype == "portable_generator":
        if target_id in ds.facilities:
            return ds.facilities[target_id].geometry
        return ds.drainage[target_id].geometry
    z = ds.zones[target_id]
    n = ds.nodes[z.anchor_node_id]
    return [n.lon, n.lat]


def resolve_interventions(ds, disaster_ev: dict, ints: list[Intervention], budget: float, availability: float) -> list[dict]:
    """Validate every intervention against resource, radius, target-state and budget constraints."""
    out: list[dict] = []
    used: dict[str, int] = {}
    seen: set[tuple[str, str]] = set()
    dist_cache: dict[str, dict] = {}
    total = 0.0
    for it in ints:
        res = ds.resources.get(it.resource_id)
        if res is None or res.resource_type != it.resource_type:
            raise ScenarioError(f"Unknown or mismatched resource {it.resource_id}")
        key = (it.resource_type, it.target_id)
        if key in seen:
            raise ScenarioError(f"Duplicate intervention {it.resource_type} on {it.target_id}")
        seen.add(key)
        used[res.id] = used.get(res.id, 0) + 1
        if used[res.id] > units_available(res, availability):
            raise ScenarioError(f"Resource {res.id} exceeds available units ({units_available(res, availability)})")

        rt = it.resource_type
        cost = res.deployment_cost
        capacity_added = 0.0
        if rt == "road_clearance_team":
            road = ds.roads.get(it.target_id)
            if road is None:
                raise ScenarioError(f"Unknown road {it.target_id}")
            st = disaster_ev["roads"][road.id]["status"]
            if st not in ("closed", "restricted"):
                raise ScenarioError(f"Road {road.id} is not blocked; nothing to clear")
            cost += road.estimated_repair_cost * (1.0 if st == "closed" else 0.5)
            name = road.name or road.id
        elif rt == "portable_generator":
            if it.target_id in ds.facilities:
                fac = ds.facilities[it.target_id]
                op = disaster_ev["ops"][fac.id]
                if not fac.power_dependent or op["multiplier"] >= 1.0:
                    raise ScenarioError(f"Facility {fac.id} does not need a generator")
                name = fac.name
            elif it.target_id in ds.drainage:
                if not disaster_ev["drainage"][it.target_id]["failed"]:
                    raise ScenarioError(f"Drainage asset {it.target_id} has not failed")
                name = ds.drainage[it.target_id].name
            else:
                raise ScenarioError(f"Unknown generator target {it.target_id}")
        else:
            if it.target_id not in ds.zones:
                raise ScenarioError(f"Unknown zone {it.target_id}")
            name = ds.zones[it.target_id].name
            capacity_added = res.service_capacity

        pos = target_position(ds, rt, it.target_id)
        if haversine_m(res.location, pos) > res.response_radius:
            raise ScenarioError(f"{it.target_id} is outside the response radius of {res.id}")
        if res.node_id not in dist_cache:
            dist_cache[res.node_id] = dijkstra(disaster_ev["adj"], res.node_id)[0]
        dist = dist_cache[res.node_id]
        if rt == "road_clearance_team":
            road = ds.roads[it.target_id]
            ts = [dist[n] for n in (road.start_node_id, road.end_node_id) if n in dist]
        elif rt == "portable_generator":
            node = ds.facilities[it.target_id].node_id if it.target_id in ds.facilities else _nearest_node(ds, pos)
            ts = [dist[node]] if node in dist else []
        else:
            node = ds.zones[it.target_id].anchor_node_id
            ts = [dist[node]] if node in dist else []
        if not ts:
            raise ScenarioError(f"{it.target_id} cannot be reached from staging depot of {res.id} on the disaster road network")
        total += cost
        out.append({"resource_id": res.id, "resource_name": res.name, "resource_type": rt, "target_id": it.target_id,
                    "target_name": name, "cost": round(cost, 2),
                    "deploy_minutes": round(res.deployment_time_minutes + min(ts), 1), "capacity_added": capacity_added})
    if total > budget + 1e-9:
        raise ScenarioError(f"Interventions cost {total:.2f} which exceeds budget {budget:.2f}")
    return out


def _nearest_node(ds, pos):
    return min(ds.nodes.values(), key=lambda n: haversine_m([n.lon, n.lat], pos)).id
