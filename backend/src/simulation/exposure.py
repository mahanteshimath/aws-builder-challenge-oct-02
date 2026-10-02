"""Population exposure: share of each zone's area covered by hazard zones at or above the Watch level."""
from __future__ import annotations

SAMPLES_PER_AXIS = 10


def _sample_points(zone) -> list[tuple[float, float]]:
    """Explicit sample points (real-geography zones) or a regular grid over the zone's bbox (rectangular zones)."""
    if zone.sample_points:
        return [(p[0], p[1]) for p in zone.sample_points]
    c0, r0, c1, r1 = zone.bbox_grid
    return [(c0 + 0.03 + (c1 - c0 - 0.06) * (i + 0.5) / SAMPLES_PER_AXIS, r0 + 0.03 + (r1 - r0 - 0.06) * (j + 0.5) / SAMPLES_PER_AXIS)
            for i in range(SAMPLES_PER_AXIS) for j in range(SAMPLES_PER_AXIS)]


def zone_sample_cover(zone, hazards) -> list[list[str]]:
    """Static geometry: for each sample point in a zone, the hazard zones (ellipses) covering it."""
    out = []
    for x, y in _sample_points(zone):
        cover = []
        for h in hazards.values():
            cx, cy = h.center_grid
            rx, ry = h.radii_grid
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                cover.append(h.id)
        out.append(cover)
    return out


def zone_exposure(zone, cover: list[list[str]], hazard_risk: dict[str, float], watch: float) -> dict:
    n = len(cover)
    score = 0.0
    exposed = 0
    for hids in cover:
        if not hids:
            continue
        risk = max(hazard_risk[h] for h in hids)
        score += risk
        if risk >= watch:
            exposed += 1
    frac = exposed / n
    pop = zone.estimated_population
    return {
        "exposure_score": round(score / n, 4),
        "exposed_fraction": round(frac, 4),
        "exposed_population": int(round(pop * frac)),
        # person-equivalents weighted by vulnerability and mobility constraints
        "vulnerability_weighted_exposure": int(round(pop * frac * zone.vulnerability_weight * zone.mobility_constraint_factor)),
    }
