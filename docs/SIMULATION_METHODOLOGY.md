# Simulation methodology

**Purpose:** comparative planning exercises on a *synthetic* district. Not calibrated, not a forecast. Simulation version `1.0.0`; dataset `sahyadri-synthetic-1.0`. Identical inputs + version → identical outputs (no randomness anywhere in the engine; the dataset itself is generated with a fixed seed and committed).

## 1. Hazard
Inputs and units: `rainfall_mm` (0-200, total over the window), `duration_hours` (1-72), `drainage_effectiveness` (0-1 global), `susceptibility_preset` (low 0.75 / moderate 1.0 / high 1.25 multiplier).
```
rainfall_intensity_factor = clamp( (rain/200) × clamp(sqrt(6/duration), 0.6, 1.4), 0, 1 )      # monotonic in rain
local_drainage            = clamp( global × road.drainage_score + min(0.4, Σ working_pump.boost × (1 − d/radius)) , 0, 1 )
flood_risk                = clamp( rif × clamp(susceptibility × preset) × (1 − local_drainage) × exposure × 1.5 , 0, 1 )
```
Road and hazard-zone susceptibility derive from an elevation proxy (distance to the fictional river + two basins). Power yards use `local_drainage = 0.7 × global`; hazard zones use `clamp(global × zone.drainage × 1.8 + 0.5 × pump_boost, 0, 0.95)`.

**Classification** (configurable in the scenario `thresholds`): Normal < 0.25 ≤ Watch < 0.50 ≤ Flood risk < 0.75 ≤ Impassable. Road thresholds shift by a type bonus (bridge +0.12, arterial +0.05, local −0.03).

## 2. Road disruption
Watch → **Degraded** (× `degraded_penalty` 1.3); Flood risk → **Restricted** (× 2.5); Impassable or explicit closure → **Closed** (edge removed from the graph). An explicit closure always wins. A road-clearance intervention lowers Closed/Restricted to Degraded (never to Open).

## 3. Network accessibility
Undirected graph of 63 nodes / 91 edges; Dijkstra from each zone's anchor node over travel-time weights (`base_minutes × penalty`). Thresholds: hospital 20 min, shelter 25, water 15 (emergency 15, school 30). Per zone × facility: `inaccessible` (no path or > threshold), `accessible_with_delay` (≥ 25 % and ≥ 2 min slower than baseline), `accessible`. A service is **reduced** for a zone when its best *operating* facility is unreachable, beyond threshold, or materially slower than baseline. Straight-line distance is never used.

## 4. Operational status vs reachability
`facility_operation()`: explicit failure → offline; power-dependent + failed power node → with backup: 60 % capacity within rated hours, 25 % after exhaustion (scenario duration > backup hours); without backup: offline; portable generator: 85 %. A facility can therefore be *operational but unreachable* or *reachable but reduced*; both are reported (`operational_status`, `accessibility_status`, combined `display_status`).

**Cascade:** a power node fails when selected *or* its yard flood risk is Impassable. Drainage pumps on a failed node (without backup) fail → their drainage boost disappears → nearby roads/hazard zones rise in risk.

## 5. Population exposure
Each zone is sampled on a 10×10 grid; a sample is *exposed* if a hazard-zone ellipse covering it is at Watch or above. `exposed_population = pop × exposed_share`; `vulnerability_weighted = exposed × vulnerability × mobility`. This is an area-share estimate - not everyone in a zone is assumed flooded. Shelter demand = 15 % of vulnerability-weighted exposure.

## 6. Critical bottlenecks
For every traversable road: remove it, re-run Dijkstra from every zone, and for each of hospital/shelter/water compute loss = 1 if a reachable-within-threshold service becomes unreachable-within-threshold, else `min(0.5, Δt/threshold)` for delay. `score = Σ_zones pop × mean(loss) / total_pop`. The list also reports affected zones, facilities losing access, and facilities for which the road is the *sole* route. Baseline scores are stored as each road's `criticality_score`.

## 7. Response optimization
Resources: road clearance teams, portable generators, temporary medical units, water distribution units, temporary shelter kits (quantities scaled by `resource_availability`, floored). Candidate actions are enumerated against the *disaster state*: clear a Closed/Restricted road, power a reduced facility or failed pump, or place a temporary unit in a zone. Each is validated for response radius, staging-depot reachability on the disaster network, unit availability and cost (`deployment_cost` + repair cost; cost and deployment minutes are recomputed server-side). Greedy loop: pick the feasible candidate with the highest `benefit / cost`, where benefit is the strategy-weighted sum of *marginal* gains obtained by re-running the engine with the candidate added:

| Strategy | pop | criticality | capacity | travel time |
|---|---|---|---|---|
| A Protect critical | 0.15 | **0.55** | 0.20 | 0.10 |
| B Maximize access | **0.65** | 0.10 | 0.15 | 0.10 |
| C Balanced | 0.35 (vulnerability-weighted) | 0.30 | 0.20 | 0.15 |

`pop` = reduction in reduced-service person-units; `criticality` = Σ facility criticality × capacity multiplier × reachable; `capacity` = Δ reachable service capacity; `time` = relative drop in average hospital time. Candidates without standalone benefit are pruned (documented approximation). Stops when budget/resources are exhausted or no beneficial action remains; leftover beneficial actions are listed as "could not be completed" with the reason. **Recovery metrics are produced by re-running the engine with the chosen interventions.**

## 8. Timeline
T+00 baseline · T+15 (35 % of rainfall) · T+30 (70 %) · T+45 (100 % + explicit closures) · T+60 (+ power/pump/facility failures = full disaster) · T+90 (recovery or unchanged). Each stage is a real engine run - not an animation.

## Metric definitions
Authoritative text lives in `backend/src/simulation/metrics.py` and is returned by every API response (`metric_definitions`) and shown as tooltips. Key ones: *exposed population* (area-share estimate), *reduced hospital/shelter/water access* (zones counted once), *reduced access any service* (union, no double counting), *facilities inaccessible from ≥ 1 zone* (lost vs baseline), *average hospital time* (population-weighted, excludes no-route zones), *zones with no feasible route* (no reachable operating service within threshold), *service capacity available*, *shelter shortfall*, *population access restored* = Σ pop × max(0, Δreduced services)/3.

## Invariants under test
Rainfall monotonicity · closing a road never improves reachability · no facility reachable through a closed edge · resources ≤ availability · spend ≤ budget · duplicate targets rejected · recovery reproduces on independent re-run · identical inputs → identical outputs · baseline ignores disaster inputs · exports/results carry the synthetic-data label.

