"""Simplified, documented power / drainage dependency model (no real grid topology)."""
from __future__ import annotations

from ..models.geography import Facility

GENERATOR_MULTIPLIER = 0.85      # portable generator deployed
BACKUP_MULTIPLIER = 0.60         # on-site backup within its rated duration
BACKUP_EXHAUSTED_MULTIPLIER = 0.25  # backup fuel exhausted (scenario duration > backup hours)


def facility_operation(fac: Facility, failed_power: set[str], failed_facilities: set[str],
                       duration_hours: float, generator_targets: set[str]) -> dict:
    """Return operational status, capacity multiplier and the reason."""
    if fac.temporary:
        return {"status": "operational", "multiplier": 1.0, "reason": "Temporary unit (modeled operational)"}
    if fac.id in failed_facilities:
        if fac.id in generator_targets:
            return {"status": "reduced", "multiplier": GENERATOR_MULTIPLIER, "reason": "Explicit failure; portable generator deployed"}
        return {"status": "offline", "multiplier": 0.0, "reason": "Explicit facility failure selected in scenario"}
    if fac.power_dependent and fac.power_node_id in failed_power:
        if fac.id in generator_targets:
            return {"status": "reduced", "multiplier": GENERATOR_MULTIPLIER,
                    "reason": f"Power node {fac.power_node_id} failed; portable generator deployed"}
        if fac.backup_power_available:
            if duration_hours <= fac.backup_power_hours:
                return {"status": "reduced", "multiplier": BACKUP_MULTIPLIER,
                        "reason": f"Power node {fac.power_node_id} failed; on backup power ({fac.backup_power_hours:g} h rated)"}
            return {"status": "reduced", "multiplier": BACKUP_EXHAUSTED_MULTIPLIER,
                    "reason": f"Power node {fac.power_node_id} failed; backup ({fac.backup_power_hours:g} h) exhausted by {duration_hours:g} h event"}
        return {"status": "offline", "multiplier": 0.0, "reason": f"Power node {fac.power_node_id} failed; no backup power"}
    return {"status": "operational", "multiplier": 1.0, "reason": "Normal operation"}
