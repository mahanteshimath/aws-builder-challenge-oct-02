"""Scenario report export: JSON, CSV and printable HTML. Never includes environment variables."""
from __future__ import annotations

import csv
import html
import io
import json

from ..simulation.scenario_engine import SYNTHETIC_NOTICE


def export_payload(sim: dict, brief: dict | None = None) -> dict:
    rec = sim["recovery"]
    dis = sim["disaster"]
    return {
        "report_type": "resilience_simulator_scenario_report", "synthetic_data": True, "data_label": SYNTHETIC_NOTICE,
        "generated_at": sim["generated_at"], "simulation_version": sim["simulation_version"], "dataset_version": sim["dataset_version"],
        "scenario": sim["scenario"],
        "comparison": sim["comparison"],
        "affected_services": [
            {"id": f["id"], "name": f["name"], "type": f["facility_type"], "operational_status": f["operational_status"],
             "accessibility_status": f["accessibility_status"], "zones_lost": f["zones_lost"], "reason": f["operational_reason"]}
            for f in dis["facilities"] if f["display_status"] != "accessible"],
        "critical_bottlenecks": sim["bottlenecks"],
        "response_actions": (rec or {}).get("interventions", []),
        "recovery_summary": sim["recovery_summary"],
        "assumptions": sim["assumptions"], "warnings": sim["warnings"],
        "limitations": ["Illustrative synthetic data; not an operational emergency management or flood forecasting system.",
                        "Modeled estimates for comparative planning only."],
        "situation_brief": brief,
    }


def to_csv(payload: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["# Resilience Simulator - synthetic demonstration data; modeled estimates only"])
    w.writerow(["scenario", payload["scenario"]["name"], "simulation_version", payload["simulation_version"], "generated_at", payload["generated_at"]])
    w.writerow(["metric", "unit", "baseline", "disaster", "recovery", "delta_disaster_vs_baseline", "delta_recovery_vs_disaster"])
    for r in payload["comparison"]:
        w.writerow([r["label"], r["unit"], r["baseline"], r["disaster"], r["recovery"], r["delta_disaster"], r["delta_recovery"]])
    w.writerow([])
    w.writerow(["response_action", "resource", "target", "cost_inr_lakh", "deploy_minutes"])
    for i in payload["response_actions"]:
        w.writerow([i["resource_type"], i["resource_name"], f"{i['target_id']} {i['target_name']}", i["cost"], i["deploy_minutes"]])
    return buf.getvalue()


def to_html(payload: dict) -> str:
    e = html.escape
    rows = "".join(f"<tr><td>{e(str(r['label']))}</td><td>{r['baseline']}</td><td>{r['disaster']}</td><td>{'' if r['recovery'] is None else r['recovery']}</td></tr>"
                   for r in payload["comparison"])
    acts = "".join(f"<li>{e(i['resource_name'])} &rarr; {e(i['target_id'])} {e(i['target_name'])} (cost {i['cost']}, {i['deploy_minutes']} min)</li>"
                   for i in payload["response_actions"]) or "<li>None</li>"
    bn = "".join(f"<li>{e(b['road_id'])}: {e(b['explanation'])}</li>" for b in payload["critical_bottlenecks"][:5]) or "<li>None</li>"
    sv = "".join(f"<li>{e(a['id'])} {e(a['name'])}: {e(a['accessibility_status'])} / {e(a['operational_status'])}</li>" for a in payload["affected_services"][:20]) or "<li>None</li>"
    asm = "".join(f"<li>{e(a)}</li>" for a in payload["assumptions"])
    s = payload["scenario"]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Resilience Simulator report</title>
<style>body{{font-family:Inter,Arial,sans-serif;margin:2rem;color:#0b1220}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #9aa7b8;padding:4px 8px;text-align:left;font-size:13px}}
.note{{background:#fff4d6;border:1px solid #d9a400;padding:8px}}</style></head><body>
<h1>Resilience Simulator - Scenario Report</h1>
<p class="note"><strong>{e(payload['data_label'])}</strong></p>
<p>Scenario: <strong>{e(s['name'])}</strong> | Rainfall {s['rainfall_mm']} mm / {s['duration_hours']} h | Drainage {s['drainage_effectiveness']} | Budget {s['resource_budget']} |
Simulation v{e(payload['simulation_version'])} | {e(payload['generated_at'])}</p>
<h2>Baseline vs disaster vs recovery</h2><table><tr><th>Metric</th><th>Baseline</th><th>Disaster</th><th>Recovery</th></tr>{rows}</table>
<h2>Affected services</h2><ul>{sv}</ul><h2>Critical bottlenecks</h2><ul>{bn}</ul><h2>Response actions</h2><ul>{acts}</ul>
<h2>Assumptions &amp; limitations</h2><ul>{asm}</ul><p>Not an operational emergency management or flood forecasting system.</p></body></html>"""


def render(payload: dict, fmt: str) -> tuple[str, str, str]:
    """Return (content, content_type, filename)."""
    if fmt == "csv":
        return to_csv(payload), "text/csv", "resilience-report.csv"
    if fmt == "html":
        return to_html(payload), "text/html", "resilience-report.html"
    return json.dumps(payload, indent=2), "application/json", "resilience-report.json"

