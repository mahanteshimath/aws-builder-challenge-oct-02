# Assumptions and limitations

## This is not an operational system
Resilience Simulator is a **comparative planning and education tool** built on **synthetic, illustrative data**. It is **not** a flood forecast, hydrological or hydraulic model, evacuation planner, or operational emergency-management system. Do not use its outputs to make real-world safety decisions.

## Data
- "Sahyadri Resilience District" is **fictional**. Roads, junctions, buildings, populations (70,100 residents in 8 zones), facilities, capacities, pumps, power nodes and hazard areas were **generated** by `backend/src/data/generate_demo_data.py` (fixed seed `20261002`) and are **not** official municipal data. Every GeoJSON file, API response, report and UI surface carries a synthetic-data label.
- Coordinates are valid WGS84 placed in the Western Ghats foothills of India for context only; the layout does not correspond to any real place.
- The architecture accepts other GeoJSON of the same schema (`dataset.py` validates geometry, ids, references), but no real dataset has been ingested or verified.

## Model assumptions
1. Flood risk is a **conceptual index** (rainfall × susceptibility × (1 − drainage) × exposure × gain), monotonic in rainfall, with uncalibrated, configurable thresholds. Elevation is a proxy derived from distance to a fictional river and two basins.
2. Road speeds, penalties (×1.3 degraded, ×2.5 restricted), thresholds (20/25/15 min) and the 25 %/2 min "delay" rule are illustrative.
3. Population is uniformly distributed inside each zone; exposure is an area-share estimate; vulnerability and mobility weights are invented. Shelter demand is 15 % of vulnerability-weighted exposure.
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
