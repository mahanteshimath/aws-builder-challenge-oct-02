"""Primary API Lambda: health, dataset, simulate, optimize, compare, export (+ brief when run locally)."""
from __future__ import annotations

import copy
import json
import logging
import os

from ..models.scenario import (SIMULATION_VERSION, BriefRequest, CompareRequest, ExportRequest, OptimizeRequest,
                               SimulateRequest, Thresholds)
from ..report.report import export_payload, render
from ..simulation.accessibility import SERVICE_THRESHOLD
from ..simulation.compare import compare_scenarios
from ..simulation.dataset import get_dataset
from ..simulation.presets import presets
from ..simulation.response_optimizer import STRATEGIES, optimize_and_run
from ..simulation.scenario_engine import SYNTHETIC_NOTICE, run_scenario
from .common import ApiError, error_response, parse_body, response, route_of, safe, validate

log = logging.getLogger()
log.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

PREFIX = "/api/v1"


def h_health(event):
    from ..ai.bedrock_client import bedrock_enabled, model_id
    ds = get_dataset()
    return response(200, {"status": "ok", "simulation_version": SIMULATION_VERSION, "dataset_version": ds.version,
                          "synthetic_data": True, "ai_provider": {"bedrock_enabled": bedrock_enabled(),
                                                                  "model_id": model_id() if bedrock_enabled() else None,
                                                                  "fallback": "rule_based"}})


def h_dataset(event):
    ds = get_dataset()
    layers = copy.deepcopy(ds.raw)
    for f in layers["roads"]["features"]:
        f["properties"]["criticality_score"] = ds.roads[f["id"]].criticality_score
    resources = [r.model_dump() for r in ds.resources.values()]
    return response(200, {
        "dataset_version": ds.version, "simulation_version": SIMULATION_VERSION, "synthetic_data": True, "data_label": SYNTHETIC_NOTICE,
        "layers": layers, "presets": presets(),
        "strategies": [{"id": k, "label": v["label"], "description": v["description"], "weights": v["weights"]} for k, v in STRATEGIES.items()],
        "resources": resources, "default_thresholds": Thresholds().model_dump(), "service_thresholds_minutes": SERVICE_THRESHOLD,
        "catalog": {"power_nodes": [{"id": p.id, "name": p.name} for p in ds.power_nodes.values()],
                    "drainage": [{"id": d.id, "name": d.name, "power_node_id": d.power_node_id} for d in ds.drainage.values()],
                    "facilities": [{"id": f.id, "name": f.name, "facility_type": f.facility_type, "power_dependent": f.power_dependent}
                                   for f in ds.facilities.values()]}})


def h_simulate(event):
    req = validate(SimulateRequest, parse_body(event))
    return response(200, safe(run_scenario, req.scenario, None, req.include_timeline))


def h_optimize(event):
    req = validate(OptimizeRequest, parse_body(event))
    out = safe(optimize_and_run, req.scenario, req.strategy)
    return response(200, out)


def h_compare(event):
    req = validate(CompareRequest, parse_body(event))
    return response(200, safe(compare_scenarios, req.scenarios))


def h_export(event):
    req = validate(ExportRequest, parse_body(event))
    sim = safe(run_scenario, req.scenario, None, False, True)
    payload = export_payload(sim)
    content, ctype, filename = render(payload, req.format)
    return response(200, content, ctype, {"Content-Disposition": f'attachment; filename="{filename}"'})


def h_brief(event):
    from ..ai.brief_generator import generate_brief
    req = validate(BriefRequest, parse_body(event))
    sim = safe(run_scenario, req.scenario, None, False, True)
    return response(200, generate_brief(sim, req.brief_type, req.allow_ai))


ROUTES = {("GET", PREFIX + "/health"): h_health, ("GET", PREFIX + "/dataset"): h_dataset,
          ("POST", PREFIX + "/simulate"): h_simulate, ("POST", PREFIX + "/optimize"): h_optimize,
          ("POST", PREFIX + "/scenario/compare"): h_compare, ("POST", PREFIX + "/export"): h_export,
          ("POST", PREFIX + "/brief"): h_brief}


def dispatch(event: dict, routes: dict = ROUTES) -> dict:
    method, path = route_of(event)
    if method == "OPTIONS":
        return response(204, "")
    fn = routes.get((method, path))
    try:
        if fn is None:
            if any(p == path for (_, p) in routes):
                raise ApiError(405, "method_not_allowed", f"{method} not allowed on {path}")
            raise ApiError(404, "not_found", f"No route {method} {path}")
        return fn(event)
    except ApiError as err:
        return error_response(err)
    except Exception:  # never leak internals or payloads
        log.exception("Unhandled error on %s %s", method, path)
        return error_response(ApiError(500, "internal_error", "Unexpected server error"))


def handler(event, context=None):
    return dispatch(event)
