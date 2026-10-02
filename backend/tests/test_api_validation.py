import base64
import json

import pytest

from src.ai import bedrock_client
from src.ai.brief_generator import generate_brief, validate_brief
from src.ai.prompt_templates import build_facts
from src.handlers.api import dispatch
from src.models.scenario import Scenario
from src.simulation.compare import compare_scenarios
from src.simulation.presets import MAJOR_ROAD, OUTAGE_POWER_NODE
from src.simulation.scenario_engine import run_scenario

COMPOUND = {"rainfall_mm": 150, "drainage_effectiveness": 0.4, "closed_road_ids": [MAJOR_ROAD], "affected_power_nodes": [OUTAGE_POWER_NODE]}


def call(method, path, body=None, raw=None):
    ev = {"requestContext": {"http": {"method": method}}, "rawPath": path, "body": raw if raw is not None else (json.dumps(body) if body is not None else "")}
    r = dispatch(ev)
    ct = r["headers"]["Content-Type"]
    return r["statusCode"], (json.loads(r["body"]) if ct == "application/json" and r["body"] else r["body"]), r


def test_health():
    s, b, _ = call("GET", "/api/v1/health")
    assert s == 200 and b["status"] == "ok" and b["ai_provider"]["fallback"] == "rule_based" and b["synthetic_data"] is False and "OpenStreetMap" in b["data_label"]


def test_dataset():
    s, b, _ = call("GET", "/api/v1/dataset")
    assert s == 200 and set(b["layers"]) >= {"roads", "facilities", "zones", "hazards"} and len(b["presets"]) >= 4
    assert all(p["scenario"]["id"] for p in b["presets"])


def test_simulate_ok():
    s, b, _ = call("POST", "/api/v1/simulate", {"scenario": COMPOUND})
    assert s == 200 and b["disaster"]["metrics"]["roads_closed"] >= 1 and len(b["timeline"]) == 6


@pytest.mark.parametrize("payload,status,code", [
    ({"scenario": {"rainfall_mm": 500}}, 422, "validation_error"),
    ({"scenario": {"duration_hours": -1}}, 422, "validation_error"),
    ({"scenario": {"closed_road_ids": ["R-999"]}}, 422, "scenario_error"),
    ({"nope": 1}, 422, "validation_error"),
])
def test_simulate_validation(payload, status, code):
    s, b, _ = call("POST", "/api/v1/simulate", payload)
    assert s == status and b["error"]["code"] == code


def test_invalid_json_empty_and_oversize():
    assert call("POST", "/api/v1/simulate", raw="{not json")[0] == 400
    assert call("POST", "/api/v1/simulate", raw="")[0] == 400
    assert call("POST", "/api/v1/simulate", raw="[1]")[0] == 400
    big = json.dumps({"scenario": {"name": "x" * 200000}})
    assert call("POST", "/api/v1/simulate", raw=big)[0] == 413


def test_base64_body_supported():
    ev = {"requestContext": {"http": {"method": "POST"}}, "rawPath": "/api/v1/simulate", "isBase64Encoded": True,
          "body": base64.b64encode(json.dumps({"scenario": {"rainfall_mm": 60}}).encode()).decode()}
    assert dispatch(ev)["statusCode"] == 200


def test_routing_errors_and_consistent_error_format():
    s, b, _ = call("GET", "/api/v1/nope")
    assert s == 404 and set(b["error"]) >= {"code", "message"}
    s, b, _ = call("GET", "/api/v1/simulate")
    assert s == 405 and b["error"]["code"] == "method_not_allowed"


def test_optimize_endpoint():
    s, b, _ = call("POST", "/api/v1/optimize", {"scenario": {**COMPOUND, "resource_budget": 30}, "strategy": "balanced"})
    assert s == 200 and b["plan"]["interventions"] and b["simulation"]["recovery"] is not None
    assert call("POST", "/api/v1/optimize", {"scenario": COMPOUND, "strategy": "bogus"})[0] == 422


def test_compare_endpoint():
    s, b, _ = call("POST", "/api/v1/scenario/compare", {"scenarios": [{"id": "a", "name": "A", "rainfall_mm": 60}, {"id": "b", "name": "B", **COMPOUND}]})
    assert s == 200 and b["metrics"] and b["zone_accessibility"] and len(b["resource_tradeoffs"]) == 2
    assert call("POST", "/api/v1/scenario/compare", {"scenarios": [{"id": "a"}]})[0] == 422


@pytest.mark.parametrize("fmt,ctype", [("json", "application/json"), ("csv", "text/csv"), ("html", "text/html")])
def test_export_formats(fmt, ctype):
    s, b, r = call("POST", "/api/v1/export", {"scenario": COMPOUND, "format": fmt})
    assert s == 200 and r["headers"]["Content-Type"] == ctype
    body = r["body"]
    assert "OpenStreetMap" in body and ("modeled" in body.lower())
    assert "AWS_" not in body and "SECRET" not in body.upper()
    if fmt == "json":
        p = json.loads(body)
        assert p["synthetic_data"] is False and p["simulation_version"] and p["assumptions"] and p["comparison"]


def test_brief_fallback_when_bedrock_disabled():
    s, b, _ = call("POST", "/api/v1/brief", {"scenario": COMPOUND})
    assert s == 200 and b["provider"] == "rule_based" and "Rule-based" in b["provider_label"]
    assert set(b["sections"]) == {"situation_summary", "top_impacts", "critical_bottlenecks", "services_requiring_attention",
                                  "immediate_actions", "followup_actions", "resource_tradeoffs", "uncertainties"}
    assert len(b["sections"]["top_impacts"]) == 3


class FakeClient:
    def __init__(self, text=None, exc=None):
        self.text, self.exc = text, exc

    def converse(self, **kw):
        if self.exc:
            raise self.exc
        return {"output": {"message": {"content": [{"text": self.text}]}}}


def sim():
    return run_scenario(Scenario(**COMPOUND), with_timeline=False)


def good_json(facts):
    rid = facts["critical_bottlenecks"][0]["road_id"]
    return json.dumps({"situation_summary": f"Modeled: road {rid} matters.", "top_impacts": ["a", "b", "c"], "critical_bottlenecks": [f"{rid} bottleneck"],
                       "services_requiring_attention": ["x"], "immediate_actions": ["y"], "followup_actions": ["z"],
                       "resource_tradeoffs": ["t"], "uncertainties": ["u"]})


def test_bedrock_success_path_with_mock(monkeypatch):
    monkeypatch.setenv("ENABLE_BEDROCK", "true")
    sm = sim()
    out = generate_brief(sm, client=FakeClient(text=good_json(build_facts(sm))))
    assert out["provider"] == "bedrock" and out["fallback_reason"] is None


@pytest.mark.parametrize("name,exc_code", [("ThrottlingException", "throttled"), ("AccessDeniedException", "access_denied"),
                                           ("ResourceNotFoundException", "model_unavailable")])
def test_bedrock_errors_fall_back(monkeypatch, name, exc_code):
    monkeypatch.setenv("ENABLE_BEDROCK", "true")
    from botocore.exceptions import ClientError
    err = ClientError({"Error": {"Code": name, "Message": "x"}}, "Converse")
    out = generate_brief(sim(), client=FakeClient(exc=err))
    assert out["provider"] == "rule_based" and out["fallback_reason"] == exc_code


def test_bedrock_timeout_falls_back(monkeypatch):
    monkeypatch.setenv("ENABLE_BEDROCK", "true")

    class ReadTimeoutError(Exception):
        pass
    out = generate_brief(sim(), client=FakeClient(exc=ReadTimeoutError("timed out")))
    assert out["provider"] == "rule_based" and out["fallback_reason"] == "timeout"


def test_ungrounded_or_malformed_ai_output_rejected(monkeypatch):
    monkeypatch.setenv("ENABLE_BEDROCK", "true")
    sm = sim()
    facts = build_facts(sm)
    bad = json.loads(good_json(facts))
    bad["situation_summary"] = "Road R-098 is closed and Hospital H-09 is flooded."
    out = generate_brief(sm, client=FakeClient(text=json.dumps(bad)))
    assert out["provider"] == "rule_based" and out["fallback_reason"] == "invalid_model_output"
    assert generate_brief(sm, client=FakeClient(text="not json"))["fallback_reason"] == "invalid_model_output"
    with pytest.raises(ValueError):
        validate_brief({"situation_summary": "x"}, facts)


def test_allow_ai_false_never_calls_bedrock(monkeypatch):
    monkeypatch.setenv("ENABLE_BEDROCK", "true")
    out = generate_brief(sim(), allow_ai=False, client=FakeClient(exc=RuntimeError("must not be called")))
    assert out["provider"] == "rule_based" and out["fallback_reason"] == "ai_not_requested"


def test_fallback_brief_cites_actual_identifiers():
    out = generate_brief(sim())
    text = json.dumps(out["sections"])
    assert MAJOR_ROAD in text and out["synthetic_data"] is False


def test_facts_do_not_contain_secrets():
    text = json.dumps(build_facts(sim())).lower()
    assert "secret" not in text and "aws_" not in text
