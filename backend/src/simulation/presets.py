"""Deterministic demo scenario presets. Expected metrics are NEVER stored - they are computed by the engine."""
from __future__ import annotations

from ..models.scenario import Scenario

MAJOR_ROAD = "R-019"  # Collector bridge with the highest modeled flood-scenario bottleneck score in the synthetic dataset
OUTAGE_POWER_NODE = "P-02"


def presets() -> list[dict]:
    items = [
        ("baseline", "Baseline neighborhood", "Normal rainfall, no closures, normal power. Baseline accessibility and travel times.",
         Scenario(id="baseline", name="Baseline neighborhood", rainfall_mm=0, drainage_effectiveness=0.5), None),
        ("heavy_rain", "Heavy rainfall", "100 mm over 6 h with average drainage: low-lying roads degrade and first exposure appears.",
         Scenario(id="heavy_rain", name="Heavy rainfall", rainfall_mm=100, drainage_effectiveness=0.5), None),
        ("extreme_rain", "Extreme rainfall", "160 mm over 6 h with reduced drainage: flood-risk zones expand, roads restrict or close, zones lose access.",
         Scenario(id="extreme_rain", name="Extreme rainfall", rainfall_mm=160, drainage_effectiveness=0.35), None),
        ("flood_closure", "Flooding + major road closure", "120 mm of rainfall plus the critical collector bridge R-019 closed.",
         Scenario(id="flood_closure", name="Flooding + major road closure", rainfall_mm=120, drainage_effectiveness=0.45, closed_road_ids=[MAJOR_ROAD]), None),
        ("compound", "Compound emergency", "150 mm rainfall, R-019 closed and the Riverside Substation (P-02) failed: cascading power, pumping and access effects.",
         Scenario(id="compound", name="Compound emergency", rainfall_mm=150, drainage_effectiveness=0.4, closed_road_ids=[MAJOR_ROAD],
                  affected_power_nodes=[OUTAGE_POWER_NODE]), None),
        ("coordinated_response", "Coordinated emergency response", "Compound emergency plus a Balanced Community Response funded from the budget; recovery is a re-run.",
         Scenario(id="coordinated_response", name="Coordinated emergency response", rainfall_mm=150, drainage_effectiveness=0.4,
                  closed_road_ids=[MAJOR_ROAD], affected_power_nodes=[OUTAGE_POWER_NODE], strategy="balanced"), "balanced"),
    ]
    return [{"id": i, "name": n, "description": d, "scenario": s.model_dump(), "response_strategy": r} for i, n, d, s, r in items]
