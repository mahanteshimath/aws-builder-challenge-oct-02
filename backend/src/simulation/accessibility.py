"""Service accessibility helpers (network travel time, not straight-line distance)."""
from __future__ import annotations

from typing import Optional

SERVICES = ("hospital", "shelter", "water")
SERVICE_THRESHOLD = {"hospital": 20.0, "shelter": 25.0, "water": 15.0, "emergency": 15.0, "school": 30.0}  # minutes


def pair_status(t: Optional[float], base_t: Optional[float], threshold: float, delay_ratio: float) -> str:
    """accessible | accessible_with_delay | inaccessible for one zone -> facility pair."""
    if t is None or t > threshold:
        return "inaccessible"
    if base_t is not None and t > base_t * delay_ratio and (t - base_t) >= 2.0:
        return "accessible_with_delay"
    return "accessible"


def service_reduced(t: Optional[float], base_t: Optional[float], threshold: float, delay_ratio: float) -> bool:
    """True when the best operating facility is unreachable, beyond threshold, or materially slower than baseline."""
    if t is None or t > threshold:
        return True
    return base_t is not None and t > base_t * delay_ratio and (t - base_t) >= 2.0


def best_service(times: dict[str, Optional[float]], fac_ids: list[str], mults: dict[str, float]):
    """Best (facility_id, minutes) among operating facilities; (None, None) if none reachable."""
    best = (None, None)
    for fid in fac_ids:
        t = times.get(fid)
        if t is None or mults.get(fid, 1.0) <= 0:
            continue
        if best[1] is None or t < best[1] - 1e-12:
            best = (fid, t)
    return best
