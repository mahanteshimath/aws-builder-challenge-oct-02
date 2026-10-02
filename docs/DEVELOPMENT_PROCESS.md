# Development process

How Resilience Simulator was designed, studied and shipped on 2026-10-02. Numbers are taken from test, deployment and analysis runs; the reproducible analysis is in [ANALYSIS_AND_FINDINGS.md](ANALYSIS_AND_FINDINGS.md).

## 1. Problem framing
Neighbourhood floods fail through cascades - a flooded bridge cuts the only route to a clinic, a substation outage stops the pump that kept a road dry. The goal was a free, explorable tool that answers three questions for a community drill: *what breaks first, who loses access to care, and which response helps most for the money?* Design constraints chosen up front:
- **Deterministic and explainable** - every number comes from a transparent engine; AI may only explain results, never produce them.
- **Network-based, not distance-based** - accessibility is travel time on a road graph, so closing a road changes routes, not colours.
- **Serverless and cheap** - no database, no always-on compute, AI called only on demand.

## 2. Engine design (version 1, prototype district)
The engine was first built and calibrated on a seeded prototype grid so behaviour could be tested in isolation:
- flood-risk index (rainfall intensity x susceptibility x (1 - drainage) x exposure), road states, Dijkstra re-routing, service accessibility, area-share exposure, power -> pump -> flood cascade, exhaustive bottleneck scan, greedy benefit/cost optimizer, 6-stage timeline;
- **calibration sweeps** showed 100 mm producing zero exposure while 29 roads were affected (hazard drainage too generous) and 170 mm affecting 72 of 91 roads - gain was lowered 1.8 -> 1.5 and the restricted penalty 3.0 -> 2.5; resource pools were tightened after the first optimizer run recovered 100 % on a 60-lakh budget;
- 74 backend and 47 frontend tests encode the invariants (rainfall monotonicity, closures never improve reachability, budget and unit limits, recovery reproducible on re-run, identical inputs -> identical outputs).

## 3. Choosing a real place: Kurla / Mithi River
Kurla (BMC Ward L, Mumbai) was chosen because its structure makes cascades visible: the Mithi River on the west, the Central Railway line splitting east from west, a few bridges and rail over-bridges in between, and a documented history of severe flooding (26 July 2005, 944 mm in 24 h). Candidate areas reviewed: Sangli (Krishna), Kolhapur (Panchganga), Chennai (Velachery), Mumbai (Kurla / Mithi).

## 4. Data study
| Step | Method | Outcome |
|---|---|---|
| Roads, river, facilities, places | OpenStreetMap via Overpass API (cached in `backend/data_sources/`) | 887 drivable ways, Mithi River + 42 drains/nalas, 75 hospitals, 22 schools, 8 police and 2 fire stations, 68 neighbourhood names, Tata Power Kurla Receiving Station, 2 BMC pumping stations |
| Terrain | SRTM 30 m via OpenTopoData, 22 x 28 grid | elevation -3 to 33 m, median 7 m; smoothed over ~220 m because single cells are noisy in dense built-up areas |
| Population | Census 2011 BMC Ward L (892,278 people / 13.46 km2) x built-up share from OSM land use | 8 neighbourhood zones, ~482,600 modeled residents |
| Graph simplification | split ways at shared nodes, merge junctions within a radius, keep best carriageway, contract pass-through nodes | radius study 60-150 m (ANALYSIS section 2); 120 m chosen -> 812 raw edges reduced to 150 segments on 105 junctions, all 5 Mithi crossings and 13 flyover segments kept |
| Susceptibility | SRTM elevation rank + Mithi and drain proximity; flyovers discounted | bridge segments median 0.84, other classes ~0.48 (ANALYSIS section 3) |

Every modeled attribute (populations, capacities, backup power, power links, 3 of 4 power nodes, 5 of 6 pumps, resources) is labelled `modeled` in the data and in the UI.

## 5. Analysis on the real network - what changed because of it
1. **Zone anchors.** The first build anchored two zones to dead-end nodes, so cul-de-sac spurs topped the bottleneck list. Anchors moved to the nearest junction with >= 3 roads; the bottleneck ranking then surfaced the real structure.
2. **Single-point-of-failure sweep.** Closing each of the 150 segments in turn showed that 132 can close with no extra loss, while the four Santa Cruz - Chembur Link Road segments each cut hospital access for 104,400 residents of Nehru Nagar and Tilak Nagar. The rail over-bridge R-059 became the preset closure.
3. **Budget never bound.** With the first resource pools, a 30-lakh budget bought everything and all strategies chose the same plan. Pools were enlarged until the budget forced real trade-offs (full set costs 42.9 lakh).
4. **Metric that ignored reconnection.** The live browser test showed "0 restored" when a plan reopened R-059. Root cause: a service only counted as restored when travel returned to within 25 % of baseline, so going from *no route* to *reachable but slower* scored zero. The metric now uses per-service severity (cut off 1 / delayed 0.5 / normal 0); a regression test guards it.
5. **Strategy study.** Under the compound emergency, *Maximize population access* clears R-059 and reaches 0 residents with reduced access on 9.9 lakh, while the other strategies leave 104,400 even at 30 lakh (ANALYSIS section 8).

## 6. Product and storytelling decisions
- Category **Social Good** (climate resilience), lane **Community** - a tabletop-drill tool for Mumbai tech meetups, residents' and volunteer groups, and college classes.
- Static `<noscript>` summary and Open Graph image so the project is readable without JavaScript.
- Provenance on every surface: "real map, modeled data", OpenStreetMap ODbL attribution, "not a flood forecast".

## 7. Build, deployment and verification
| Item | Result |
|---|---|
| Backend tests (`python -m pytest backend`) | 75 passed |
| Frontend tests / type check / build | 47 passed / clean / succeeded |
| Release (`pwsh scripts/deploy.ps1`) | dataset build -> tests -> Amplify headers -> SAM deploy -> S3 sync -> Amplify deployment -> smoke test; final release 2026-10-02 17:35 UTC, stack `UPDATE_COMPLETE`, Amplify jobs 7-8 `SUCCEED` |
| API smoke test on the live API | 15/15 incl. live Amazon Bedrock brief and fallback path |
| Browser end-to-end on the public URL | 14/14, 0 console errors (extreme rain -> close R-059 -> Bhabha Hospital inspector -> Maximize-access response: 34,800 person-service equivalents restored -> Bedrock brief -> export) |
| Engine time on the real network | ~0.1 s per scenario, ~0.5 s per optimizer run |

Development tooling and AWS connection evidence: [AWS_AGENT_CONNECTION_PROOF.md](AWS_AGENT_CONNECTION_PROOF.md).

## 8. Known gaps
No community group has run a drill yet; the flood index is not validated against observed 2005 / 2017 extents; populations, capacities and infrastructure links are modeled; no demo video yet. See [ASSUMPTIONS_AND_LIMITATIONS.md](ASSUMPTIONS_AND_LIMITATIONS.md).
