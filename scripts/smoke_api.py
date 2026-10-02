"""Post-deployment smoke test for every API endpoint. Usage: python scripts/smoke_api.py https://<api-id>.execute-api.<region>.amazonaws.com [origin]"""
import json, sys, time, urllib.request, urllib.error

BASE = sys.argv[1].rstrip("/") + "/api/v1"
ORIGIN = sys.argv[2] if len(sys.argv) > 2 else None
ok_all = True

def call(method, path, body=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"content-type": "application/json", **({"Origin": ORIGIN} if ORIGIN else {})})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            txt = r.read().decode(); return r.status, (txt if raw else json.loads(txt)), time.time() - t, dict(r.headers)
    except urllib.error.HTTPError as e:
        txt = e.read().decode(); return e.code, json.loads(txt) if txt.startswith("{") else txt, time.time() - t, dict(e.headers)

def check(name, cond, extra=""):
    global ok_all
    ok_all &= bool(cond); print(("PASS" if cond else "FAIL"), name, extra)

COMPOUND = {"id": "compound", "name": "Compound emergency", "rainfall_mm": 150, "drainage_effectiveness": 0.4, "closed_road_ids": ["R-019"], "affected_power_nodes": ["P-02"]}
s, b, t, h = call("GET", "/health"); check("health", s == 200 and b["status"] == "ok", f"{t:.2f}s bedrock_enabled={b['ai_provider']['bedrock_enabled']}")
s, b, t, h = call("GET", "/dataset"); check("dataset", s == 200 and len(b["layers"]["roads"]["features"]) >= 80 and b["synthetic_data"], f"{t:.2f}s roads={len(b['layers']['roads']['features'])}")
if ORIGIN: check("CORS allow-origin header", h.get("access-control-allow-origin") == ORIGIN or h.get("Access-Control-Allow-Origin") == ORIGIN)
s, b, t, _ = call("POST", "/simulate", {"scenario": COMPOUND}); check("simulate", s == 200 and b["disaster"]["metrics"]["roads_closed"] >= 1, f"{t:.2f}s")
s, b1, _, _ = call("POST", "/simulate", {"scenario": COMPOUND}); b["generated_at"] = b1["generated_at"] = ""; check("simulate deterministic", json.dumps(b, sort_keys=True) == json.dumps(b1, sort_keys=True))
s, b, t, _ = call("POST", "/optimize", {"scenario": {**COMPOUND, "resource_budget": 30}, "strategy": "balanced"}); check("optimize", s == 200 and b["simulation"]["recovery"] is not None and b["plan"]["budget_consumed"] <= 30, f"{t:.2f}s actions={len(b['plan']['interventions'])}")
s, b, t, _ = call("POST", "/scenario/compare", {"scenarios": [{"id": "a", "name": "A", "rainfall_mm": 60}, COMPOUND]}); check("compare", s == 200 and len(b["resource_tradeoffs"]) == 2, f"{t:.2f}s")
s, b, t, _ = call("POST", "/brief", {"scenario": COMPOUND}); check("brief (Bedrock if enabled)", s == 200 and b["provider"] in ("bedrock", "rule_based"), f"{t:.2f}s provider={b['provider']} reason={b['fallback_reason']}")
s, b, t, _ = call("POST", "/brief", {"scenario": COMPOUND, "allow_ai": False}); check("brief fallback path", s == 200 and b["provider"] == "rule_based" and "Rule-based" in b["provider_label"], f"{t:.2f}s")
for fmt in ("json", "csv", "html"):
    s, b, t, _ = call("POST", "/export", {"scenario": COMPOUND, "format": fmt}, raw=True); check(f"export {fmt}", s == 200 and ("ynthetic" in b or "SYNTHETIC" in b), f"{t:.2f}s")
s, b, _, _ = call("POST", "/simulate", {"scenario": {"rainfall_mm": 500}}); check("validation 422", s == 422 and b["error"]["code"] == "validation_error")
s, b, _, _ = call("POST", "/simulate", {"scenario": {"closed_road_ids": ["R-999"]}}); check("unknown id 422", s == 422 and b["error"]["code"] == "scenario_error")
s, b, _, _ = call("GET", "/nope"); check("unknown route 404", s == 404)
print("\nALL PASSED" if ok_all else "\nSOME FAILED"); sys.exit(0 if ok_all else 1)
