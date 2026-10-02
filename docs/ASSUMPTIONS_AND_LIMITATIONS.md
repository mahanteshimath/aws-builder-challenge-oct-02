# Assumptions and limitations

## This is not an operational system
Resilience Simulator is a **comparative planning, tabletop-drill and education tool** built on **real OpenStreetMap geography with modeled attributes**. It is **not** a flood forecast, hydrological or hydraulic model, evacuation planner, or operational emergency-management system. Do not use its outputs to make real-world safety decisions.

## Data
**Real (sourced):** the study area is Kurla / the Mithi River, Mumbai (BMC Ward L; bbox 72.8600-72.8990 E, 19.0595-19.0905 N). Road network (150 simplified segments from OSM `motorway`…`unclassified` ways), Mithi River crossings and flyovers/rail over-bridges, the Mithi River line, 29 facility names and locations (hospitals incl. K.B. Bhabha Municipal General Hospital, police and fire stations, schools, places of worship used as shelter/water sites), the Tata Power Kurla Receiving Station, the BMC Kalina sewage pumping station and the 8 neighbourhood names are from **OpenStreetMap** (© OpenStreetMap contributors, ODbL 1.0; snapshot timestamp in `manifest.json`). Terrain is **SRTM 30 m** (via OpenTopoData). Ward density is **Census of India 2011** (Ward L: 892,278 people on 13.46 km², as listed on Wikipedia's *Administrative divisions of Mumbai*).

**Modeled (assumptions, not official BMC/MCGM data):** zone boundaries (nearest-neighbourhood-point partition of the study area), zone populations (Ward L density × built-up share; total ≈ 482,600), facility capacities and criticality, which buildings act as shelters/water points, backup power and power-dependency links, 3 of 4 power nodes and 5 of 6 drainage pumps (named "(modeled)"), the six hazard pockets, response resources, costs, radii and deployment times.

- The road graph is simplified: junctions within 120 m are merged, parallel carriageways collapse to the best class, and pass-through nodes are contracted. Turn restrictions, one-way streets, traffic, lane counts and vertical separation at grade crossings are not modelled.
- `backend/src/data/build_kurla_dataset.py` rebuilds the GeoJSON deterministically from the cached raw extracts in `backend/data_sources/` (`--refresh` re-downloads them). The original synthetic generator (`generate_demo_data.py`) is kept for reference only.
- Every API response, export and UI surface carries a provenance label ("REAL GEOGRAPHY, MODELED ATTRIBUTES") and OSM attribution.

## Model assumptions
1. Flood risk is a **conceptual index** (rainfall × susceptibility × (1 − drainage) × exposure × gain), monotonic in rainfall, with uncalibrated, configurable thresholds. Susceptibility combines the SRTM elevation rank (smoothed over ~220 m because SRTM is noisy in dense built-up areas) with proximity to the Mithi River and OSM drains/nalas; flyover segments get a reduced susceptibility and a higher closure threshold. It has not been validated against observed 2005/2017 flood extents.
2. Road speeds, penalties (×1.3 degraded, ×2.5 restricted), thresholds (20/25/15 min) and the 25 %/2 min "delay" rule are illustrative.
3. Population is uniformly distributed inside each zone; exposure is an area-share estimate; vulnerability and mobility weights are judgment-based (higher for informal settlements along the Mithi bank). Shelter demand is 15 % of vulnerability-weighted exposure.
4. Power is a one-level dependency model (facility → power node, pump → power node). No real grid topology, load flow, restoration sequencing or fuel logistics. Backup-power multipliers (60 %, 25 %, 85 %) are assumptions.
5. Response resources, costs (illustrative INR lakh), deployment times, capacities and radii are invented; travel from the staging depot uses the disaster-state road graph, and setup time is fixed per resource type.
6. Recovery assumes interventions are complete and effective instantaneously after their deployment time; it does not model worsening or receding floods over time. The T+00…T+90 timeline is a sequence of deterministic states, not a hydrodynamic simulation.
7. Rescue teams, boat/air evacuation, supply-vehicle logistics, communication outages, traffic demand and vehicle-type restrictions are **not** modelled.

## Optimizer limits
Greedy benefit-to-cost selection (not globally optimal). Candidates with no standalone benefit are pruned, so a rare synergy between two individually useless actions can be missed. Benefit weights per strategy are judgment calls and are documented in `SIMULATION_METHODOLOGY.md`.

## AI limits
Amazon Bedrock only rewrites deterministic facts into prose. Output is validated for structure and for cited identifiers but **not** for every numeric statement; small wording errors are possible. The model may paraphrase or omit facts. A rule-based brief is always available, labelled "Rule-based", and is used automatically on any failure.

## Engineering limits
- Single-region, stateless demo: no persistence of scenarios, no authentication (none needed for the public demo; no admin capability or credential is exposed).
- Each API call recomputes the scenario (≈ 0.05-0.3 s compute; cold starts add ~1-2 s). `POST /brief` and `/export` recompute rather than trusting client-supplied results.
- Basemap tiles are off by default. If you enable the optional OpenStreetMap layer, OSM's tile usage policy applies (light demo use only) and attribution is shown.
- Mobile view is a stacked fallback; the full command-center layout targets desktop and tablet.
