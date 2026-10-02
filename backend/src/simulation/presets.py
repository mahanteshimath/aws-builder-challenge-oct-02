"""Deterministic demo scenario presets. Expected metrics are NEVER stored - they are computed by the engine."""
from __future__ import annotations

from ..models.scenario import Scenario

# Santa Cruz - Chembur Link Road (SCLR) rail over-bridge across the Central Railway line: the highest-impact single closure
# in the Kurla dataset (measured by sweeping every bridge / arterial closure under 120-150 mm rainfall).
MAJOR_ROAD = "R-059"
# Modeled Mithi-bank distribution substation feeding the real BMC Kalina sewage pumping station (D-01) and Kalina Hospital.
OUTAGE_POWER_NODE = "P-02"


def presets() -> list[dict]:
    items = [
        ("baseline", "Baseline - Kurla on a dry day", "No rainfall, no closures, normal power. Baseline accessibility and travel times.",
         Scenario(id="baseline", name="Baseline - Kurla on a dry day", rainfall_mm=0, drainage_effectiveness=0.5), None),
        ("heavy_rain", "Heavy monsoon rainfall", "100 mm over 6 h with average drainage: Mithi-bank and subway roads degrade, first exposure appears.",
         Scenario(id="heavy_rain", name="Heavy monsoon rainfall", rainfall_mm=100, drainage_effectiveness=0.5), None),
        ("extreme_rain", "Extreme rainfall (2005-type cloudburst, scaled)", "160 mm over 6 h with reduced drainage: Mithi-bank pockets flood, roads restrict or close, zones lose hospital access.",
         Scenario(id="extreme_rain", name="Extreme rainfall (2005-type cloudburst, scaled)", rainfall_mm=160, drainage_effectiveness=0.35), None),
        ("flood_closure", "Flooding + SCLR rail over-bridge closed", "120 mm of rainfall plus the SCLR rail over-bridge (R-059) closed: east-west Kurla is cut at the railway.",
         Scenario(id="flood_closure", name="Flooding + SCLR rail over-bridge closed", rainfall_mm=120, drainage_effectiveness=0.45, closed_road_ids=[MAJOR_ROAD]), None),
        ("compound", "Compound emergency", "150 mm rainfall, SCLR over-bridge (R-059) closed and the Mithi-bank substation (P-02) failed: pump, power and access cascade.",
         Scenario(id="compound", name="Compound emergency", rainfall_mm=150, drainage_effectiveness=0.4, closed_road_ids=[MAJOR_ROAD],
                  affected_power_nodes=[OUTAGE_POWER_NODE]), None),
        ("coordinated_response", "Coordinated emergency response", "Compound emergency plus a 'Maximize population access' response funded from a 30-lakh budget; recovery is a re-run.",
         Scenario(id="coordinated_response", name="Coordinated emergency response", rainfall_mm=150, drainage_effectiveness=0.4,
                  closed_road_ids=[MAJOR_ROAD], affected_power_nodes=[OUTAGE_POWER_NODE], strategy="maximize_access"), "maximize_access"),
    ]
    return [{"id": i, "name": n, "description": d, "scenario": s.model_dump(), "response_strategy": r} for i, n, d, s, r in items]
