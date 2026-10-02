"""Transparent, configurable conceptual flood model (comparative planning only - NOT a hydrological forecast).

flood_risk = clamp( rainfall_intensity_factor * susceptibility * (1 - drainage_effectiveness)
                    * exposure_factor * GAIN, 0, 1 )

Units: rainfall_mm = total rainfall over `duration_hours`; all other inputs are dimensionless 0..1.
"""
from __future__ import annotations

import math

from ..models.scenario import Thresholds

GAIN = 1.5
SUSCEPTIBILITY_MULTIPLIER = {"low": 0.75, "moderate": 1.0, "high": 1.25}
MAX_RAINFALL_MM = 200.0
REFERENCE_DURATION_H = 6.0

HAZARD_CLASSES = ("normal", "watch", "flood_risk", "impassable")
ROAD_STATUS_FOR_CLASS = {"normal": "open", "watch": "degraded", "flood_risk": "restricted", "impassable": "closed"}


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def rainfall_intensity_factor(rainfall_mm: float, duration_hours: float) -> float:
    """0..1. Monotonic non-decreasing in rainfall; shorter duration = more intense for equal totals."""
    base = clamp(rainfall_mm / MAX_RAINFALL_MM)
    duration_factor = clamp(math.sqrt(REFERENCE_DURATION_H / max(duration_hours, 1e-6)), 0.6, 1.4)
    return clamp(base * duration_factor)


def flood_risk(rif: float, susceptibility: float, drainage_effectiveness: float,
               exposure_factor: float = 1.0, preset_multiplier: float = 1.0) -> float:
    susc = clamp(susceptibility * preset_multiplier)
    return clamp(rif * susc * (1.0 - clamp(drainage_effectiveness)) * exposure_factor * GAIN)


def classify(risk: float, th: Thresholds, bonus: float = 0.0) -> str:
    """`bonus` raises thresholds for elevated roads (bridges) or lowers them for low-lying local roads."""
    if risk >= th.impassable + bonus:
        return "impassable"
    if risk >= th.flood_risk + bonus:
        return "flood_risk"
    if risk >= th.watch + bonus:
        return "watch"
    return "normal"

