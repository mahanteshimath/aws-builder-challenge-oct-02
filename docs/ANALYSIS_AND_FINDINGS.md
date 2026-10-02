# Analysis and findings - Kurla / Mithi River, Mumbai

Every table below is produced by `python scripts/run_analysis.py` on the same deterministic engine that runs the live app (dataset `kurla-mithi-osm-1.0`). Re-running the script reproduces every number exactly. Populations, capacities and infrastructure links are modeled planning assumptions (see `ASSUMPTIONS_AND_LIMITATIONS.md`); geography is real.

## Key findings

1. **Rain alone degrades Kurla long before it cuts it off.** At 100 mm / 6 h ~42,992 residents are in modeled flood-risk pockets and 53 of 150 segments slow down, yet every neighbourhood still reaches a hospital. The tipping point is between 140 and 160 mm with weak drainage: at 160 mm 104,400 residents lose timely hospital access.
2. **One road corridor holds east Kurla together.** Closing any one of the 4 Santa Cruz – Chembur Link Road segments (R-059, R-044, R-048, R-079) under 120 mm leaves 104,400 residents with reduced hospital access; closing the rail over-bridge R-059 leaves Nehru Nagar and Tilak Nagar with no route to any hospital. 132 of 150 segments can close without any extra loss - resilience is concentrated in a handful of links.
3. **Drainage has a tipping point.** At 150 mm, raising drainage effectiveness from 0.2 to 0.3 cuts closed roads from 16 to 5 and residents with reduced access from 206,400 to 0 (section 5) - desilting and pump uptime matter before the monsoon, not during it.
4. **Power failures cascade into flooding.** Losing the Mithi-bank substation P-02 stops pumps D-01, D-04 and closes 6 more roads at 150 mm (section 7).
5. **The right strategy beats a bigger budget.** In the compound emergency, *Maximize population access* clears R-059 and reaches 0 residents with reduced access on just 9.9 lakh, while *Protect critical services* and *Balanced* still leave 104,400 at 30 lakh because they rank generators, water tankers and medical units above clearing the over-bridge; all three converge only at 45 lakh (section 8).
6. **Metrics must credit reconnection.** A naive 'back to baseline' metric scored reopening the over-bridge as zero benefit; severity weighting credits 17,400 person-service equivalents (section 9).

## 1. Study area and data sourcing

Study area: Kurla West / Kurla East / Kalina / Bail Bazar / Tilak Nagar (BMC Ward L), bbox [72.86, 19.0595, 72.899, 19.0905]. OpenStreetMap snapshot `2026-10-02T15:51:21Z`.

| Source | What was extracted | Volume |
|---|---|---|
| OpenStreetMap (Overpass API) | drivable road ways by class | tertiary 376, trunk 183, secondary 175, primary 130, unclassified 23 |
| OpenStreetMap | waterways | Mithi River + 42 drains / nalas / canals |
| OpenStreetMap | facilities and places | 75 hospitals, 16 clinics, 22 schools, 8 police, 2 fire stations, 59 places of worship, 68 neighbourhood names, 1 substation, 2 pumping stations |
| SRTM 30 m (OpenTopoData) | elevation grid | 616 points; min -3 m, median 7 m, max 33 m |
| Census of India 2011 | BMC Ward L density | 892,278 people / 13.46 km2 = 66,291 per km2 |

Modeled population of the 8 neighbourhood zones:

| Zone | Neighbourhood | Modeled population | Vulnerability weight |
|---|---|---|---|
| Z-01 | Kalina | 102,000 | 1.10 |
| Z-05 | Kurla West (LBS Marg) | 85,700 | 1.15 |
| Z-03 | Old Kurla / Kurla Christian Village | 71,800 | 1.05 |
| Z-08 | Vidyavihar West / Kirol | 68,500 | 0.95 |
| Z-07 | Tilak Nagar | 57,000 | 0.90 |
| Z-06 | Nehru Nagar, Kurla East | 47,400 | 1.20 |
| Z-02 | Kismat Nagar (Mithi bank) | 34,700 | 1.35 |
| Z-04 | Bail Bazar / Sahayog Nagar | 15,500 | 1.30 |

Total modeled population: **482,600**.

## 2. Road-network simplification study

Raw OSM ways are split at every shared node, then junction nodes within a merge radius are clustered, parallel carriageways collapse to the best class and pass-through nodes are contracted. The radius trades fidelity against optimizer run time (the optimizer and bottleneck scan re-run Dijkstra for every candidate).

| Merge radius | Road segments | Junctions | Mithi crossings | Flyover segments | Median segment |
|---|---|---|---|---|---|
| 60 m | 205 | 146 | 5 | 17 | 240 m |
| 90 m | 175 | 119 | 5 | 15 | 276 m |
| 120 m | 150 | 105 | 5 | 13 | 296 m |
| 150 m | 139 | 98 | 5 | 12 | 291 m |

Chosen: **120 m** - keeps every Mithi crossing and flyover while staying near the size the engine was designed for. Engine time on the result: see section 10.

## 3. Terrain and flood-susceptibility study

Susceptibility = 0.10 + 0.55 x (1 - SRTM elevation rank) + 0.55 x (0.70 e^(-d_Mithi/420 m) + 0.30 e^(-d_drain/160 m)), clamped 0.03-0.98; flyovers x0.35. Elevation is smoothed over ~220 m because single SRTM cells are noisy in dense built-up areas.

| Road class | Segments | Median susceptibility | Max |
|---|---|---|---|
| arterial | 53 | 0.49 | 0.86 |
| bridge | 8 | 0.84 | 0.98 |
| collector | 22 | 0.47 | 0.86 |
| local | 67 | 0.48 | 0.86 |

Candidate flood pockets (derived from the same index):

| Pocket | Name | Susceptibility |
|---|---|---|
| HZ-01 | Kranti Nagar / Mithi bank (CST Road) | 0.88 |
| HZ-02 | Kismat Nagar - Bail Bazar Mithi bend | 0.96 |
| HZ-03 | Kalina - Vakola nala low ground | 0.41 |
| HZ-04 | Kurla station subway & LBS Marg dip | 0.60 |
| HZ-05 | Jarimari - airport boundary drain | 0.44 |
| HZ-06 | Tilak Nagar - SCLR underpass | 0.56 |

## 4. Rainfall sensitivity (6 h event)

| Rainfall | Drainage | People exposed | Roads affected | Roads closed | Reduced hospital access | Reduced any service | Avg hospital min |
|---|---|---|---|---|---|---|---|
| 0 mm | 0.50 | 0 | 0 | 0 | 0 | 0 | 3.63 |
| 0 mm | 0.35 | 0 | 0 | 0 | 0 | 0 | 3.63 |
| 20 mm | 0.50 | 0 | 0 | 0 | 0 | 0 | 3.63 |
| 20 mm | 0.35 | 0 | 0 | 0 | 0 | 0 | 3.63 |
| 40 mm | 0.50 | 0 | 0 | 0 | 0 | 0 | 3.63 |
| 40 mm | 0.35 | 0 | 1 | 0 | 0 | 0 | 3.63 |
| 60 mm | 0.50 | 0 | 13 | 0 | 0 | 0 | 3.65 |
| 60 mm | 0.35 | 0 | 20 | 0 | 0 | 0 | 3.65 |
| 80 mm | 0.50 | 0 | 32 | 0 | 0 | 0 | 3.70 |
| 80 mm | 0.35 | 42,992 | 45 | 0 | 0 | 0 | 3.93 |
| 100 mm | 0.50 | 42,992 | 53 | 0 | 0 | 0 | 3.93 |
| 100 mm | 0.35 | 42,992 | 67 | 0 | 0 | 0 | 3.94 |
| 120 mm | 0.50 | 42,992 | 73 | 0 | 0 | 0 | 3.99 |
| 120 mm | 0.35 | 54,851 | 88 | 0 | 0 | 0 | 4.11 |
| 140 mm | 0.50 | 42,992 | 89 | 1 | 0 | 0 | 4.12 |
| 140 mm | 0.35 | 84,775 | 102 | 1 | 0 | 0 | 4.16 |
| 160 mm | 0.50 | 54,851 | 100 | 5 | 0 | 0 | 4.12 |
| 160 mm | 0.35 | 84,775 | 117 | 6 | 104,400 | 104,400 | 4.57 |
| 180 mm | 0.50 | 66,251 | 111 | 8 | 57,000 | 57,000 | 4.74 |
| 180 mm | 0.35 | 106,195 | 124 | 27 | 172,900 | 274,900 | 5.44 |
| 200 mm | 0.50 | 106,195 | 122 | 28 | 172,900 | 274,900 | 5.44 |
| 200 mm | 0.35 | 106,195 | 126 | 34 | 172,900 | 360,600 | 5.63 |

## 5. Drainage-effectiveness sensitivity (150 mm / 6 h)

| Drainage effectiveness | People exposed | Roads affected | Roads closed | Reduced any service |
|---|---|---|---|---|
| 0.2 | 106,195 | 121 | 16 | 206,400 |
| 0.3 | 106,195 | 113 | 5 | 0 |
| 0.4 | 84,775 | 102 | 4 | 0 |
| 0.5 | 54,851 | 94 | 1 | 0 |
| 0.6 | 42,992 | 82 | 1 | 0 |
| 0.7 | 0 | 74 | 1 | 0 |

## 6. Single-point-of-failure study (every road closed in turn, 120 mm rain)

Reference (120 mm, no closure): 0 residents with reduced access. **132 of 150 segments** cause no additional loss when closed; the network's resilience depends on a few links.

| Rank | Road | Name | Class | Extra residents with reduced access | Extra with reduced hospital access | Zones with no route |
|---|---|---|---|---|---|---|
| 1 | R-059 | Santa Cruz – Chembur Link Road | arterial | 104,400 | 104,400 | 2 |
| 2 | R-044 | Santa Cruz – Chembur Link Road | arterial | 104,400 | 104,400 | 0 |
| 3 | R-048 | Santa Cruz – Chembur Link Road | arterial | 104,400 | 104,400 | 0 |
| 4 | R-079 | Santa Cruz – Chembur Link Road | arterial | 104,400 | 104,400 | 0 |
| 5 | R-045 | Santa Cruz – Chembur Link Road | arterial | 102,000 | 0 | 0 |
| 6 | R-012 | Father Peter Periera Road | local | 87,300 | 15,500 | 0 |
| 7 | R-084 | A H Wadia Marg | local | 85,700 | 85,700 | 0 |
| 8 | R-016 | Nathani Road | local | 68,500 | 68,500 | 0 |
| 9 | R-015 | Jugaldas Modi Marg | local | 68,500 | 0 | 0 |
| 10 | R-072 | Unnamed tertiary road near Tilak Nagar | local | 57,000 | 57,000 | 1 |

## 7. Power and pump cascade study (150 mm, drainage 0.40)

| Power node | Name | Facilities below capacity | Pumps lost | Extra roads closed | Reduced any service |
|---|---|---|---|---|---|
| P-01 | Tata Power Kurla Receiving Station | 3 | none | 0 | 0 |
| P-02 | Kalina / Mithi-bank distribution substation (modeled) | 3 | D-01, D-04 | 6 | 102,000 |
| P-03 | Tilak Nagar distribution substation (modeled) | 4 | D-03 | 0 | 212,800 |
| P-04 | Kurla West (LBS Marg) feeder substation (modeled) | 2 | D-05, D-06 | 1 | 235,100 |

## 8. Response-strategy and budget study (compound emergency)

Compound emergency: 150 mm, drainage 0.40, R-059 (Santa Cruz – Chembur Link Road) closed, P-02 failed.

| Budget (lakh) | Strategy | Actions | Spent | Reduced access before | After | Person-service eq. restored | Clears R-059? |
|---|---|---|---|---|---|---|---|
| 10 | Protect critical services | 3 | 9.00 | 206,400 | 206,400 | 0 | no |
| 10 | Maximize population access | 4 | 9.90 | 206,400 | 0 | 51,800 | yes |
| 10 | Balanced community response | 4 | 9.50 | 206,400 | 104,400 | 17,000 | no |
| 20 | Protect critical services | 5 | 20.00 | 206,400 | 104,400 | 17,000 | no |
| 20 | Maximize population access | 6 | 16.90 | 206,400 | 0 | 51,800 | yes |
| 20 | Balanced community response | 5 | 20.00 | 206,400 | 104,400 | 17,000 | no |
| 30 | Protect critical services | 6 | 29.00 | 206,400 | 104,400 | 17,000 | no |
| 30 | Maximize population access | 8 | 29.90 | 206,400 | 0 | 51,800 | yes |
| 30 | Balanced community response | 6 | 29.00 | 206,400 | 104,400 | 17,000 | no |
| 45 | Protect critical services | 10 | 42.90 | 206,400 | 0 | 51,800 | yes |
| 45 | Maximize population access | 10 | 42.90 | 206,400 | 0 | 51,800 | yes |
| 45 | Balanced community response | 10 | 42.90 | 206,400 | 0 | 51,800 | yes |

## 9. Metric-design study: crediting reconnection

A first version of the recovery metric only counted a service as restored when travel time returned to within 25 % of baseline. Testing the extreme-rainfall + R-059 closure case showed that reopening the over-bridge moved Nehru Nagar, Kurla East from *no route* to 9.6 min, Tilak Nagar from *no route* to 11.3 min - a real recovery the metric scored as zero. The metric now uses a per-service severity (cut off = 1, reachable but delayed = 0.5, normal = 0): reopening alone restores **17,400** person-service equivalents.

## 10. Engine performance on the real network

| Operation | Time (this machine) |
|---|---|
| Full scenario incl. bottleneck scan + 6-stage timeline (median of 5) | 0.07 s |
| Optimizer (one strategy) + recovery re-run | 0.49 s |

---
Generated in 12 s by `scripts/run_analysis.py`.
