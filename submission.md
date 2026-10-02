# AWS Builder Center - "Edit project" submission (copy each block into the matching field)

## Title (max 255)
```
Resilience Simulator: stress-test a neighborhood before disaster strikes
```

## Description (max 512)
```
An interactive climate-emergency digital twin of a fictional Indian neighborhood: change rainfall, close roads or cut power, and a deterministic engine recomputes who loses access to hospitals, shelters and water. A budget-constrained optimizer tests response strategies, and Amazon Bedrock writes a grounded situation brief with a rule-based fallback.
```

## Cover image (optional, 1200x675, <2 MB)
Upload `docs/screenshots/cover-1200x675.png` (1200x675, ~247 KB).

## Tags (max 5)
`Amazon Bedrock` · `AWS Lambda` · `AWS Amplify` · `Climate and Sustainability` · `Serverless`
(use the closest available options in the tag picker)

## Links
| Field | Value |
|---|---|
| GitHub or GitLab repository | https://github.com/mahanteshimath/aws-builder-challenge-oct-02 (**push the local commits first - nothing has been committed or pushed yet**) |
| Endpoint or live demo | https://main.dxhzlkmrgksnx.amplifyapp.com |
| Jupyter / SageMaker notebook | Not applicable - leave blank |
| API health (optional, for the body) | https://4wbvz70w98.execute-api.us-east-1.amazonaws.com/api/v1/health |

## Body (paste into the editor, or toggle **Markdown** and paste as-is)

---

# Resilience Simulator

**Stress-test a neighborhood before disaster strikes.**

> The "Sahyadri Resilience District" is **fictional**. All roads, people, facilities and hazards are **synthetic, illustrative data**. Results are modeled estimates for comparative planning - **not** a flood forecast and **not** an operational emergency-management system.

**Try it (no sign-in): https://main.dxhzlkmrgksnx.amplifyapp.com**

## The problem
Neighborhood emergencies fail through cascades: a flooded bridge cuts the only route to a clinic, a substation outage stops the pump that kept a road dry, and shelter capacity sits on the wrong side of the river. Planners and community groups rarely have an affordable, explorable way to ask *what breaks first, who loses access to care, and where does the next unit of response help most* - before an event.

## What it does
- **Live map** (MapLibre) of roads, flood-risk zones, population zones, hospitals, shelters, schools, water points, power and drainage assets.
- **Deterministic simulation**: rainfall, duration, drainage and susceptibility feed a transparent flood-risk index. Roads become Open / Degraded / Restricted / Closed and travel times are recomputed with **Dijkstra on the road graph** - closing a road changes routes, not just colors.
- **Click-to-close roads**, power-outage and pump-failure toggles, with live re-simulation.
- **Service accessibility**: travel time from every population zone to hospitals, shelters and water points; a facility's *operational status* (power, backup) is tracked separately from its *reachability*. A power outage can stop a pump and raise flood risk nearby.
- **Critical bottlenecks**: every road is removed in turn and scored by population-weighted loss of service access, with "sole route to facility" detection.
- **Response optimizer**: three strategies (Protect critical services, Maximize population access, Balanced community response) pick actions under a budget. Every candidate is scored by **re-running the simulation**, and the recovery result is another re-run - not a paragraph of advice.
- **Baseline vs Disaster vs Recovery** comparison, a 6-stage timeline (T+00 to T+90), charts, and JSON / CSV / HTML export plus an importable scenario file.
- **AI Situation Brief** with Amazon Bedrock. The server recomputes the facts, the model only writes prose, and output is rejected - falling back to a clearly labelled *Rule-based* brief - if it cites any road, facility or zone ID that is not in the simulation output.

## Measured example (deterministic, synthetic data)
| Scenario | Result |
|---|---|
| Baseline | 0 people exposed, 4/4 hospitals reachable, 5.7 min average hospital travel |
| Extreme rainfall (160 mm, drainage 35%) | 20,426 people potentially exposed, 34,600 with reduced hospital access, 3/4 hospitals reachable |
| Compound emergency + Balanced response (30 lakh budget) | reduced hospital access 27,400 -> 0; ~19,800 person-service equivalents of access restored |

## Architecture
```
Browser -> React + MapLibre SPA (AWS Amplify Hosting)
        -> API Gateway HTTP API (CORS allow-list, throttling)
        -> Lambda (Python 3.12): simulate / optimize / compare / export / dataset  --+
        -> Lambda (Python 3.12): situation brief --------------------------------+--> shared deterministic engine
                                   |-> Amazon Bedrock (Nova Lite, Converse API)        |-> private S3 (GeoJSON)
                                   '-> rule-based fallback on any failure              '-> CloudWatch Logs
```
Infrastructure is defined with **AWS SAM** and deploys with one script. No database, no always-on compute; Bedrock is called only when the user clicks *Generate*.

## AWS services used
Amazon Bedrock (Runtime, Converse API, Nova Lite inference profile) - AWS Amplify Hosting - Amazon API Gateway (HTTP API) - AWS Lambda - Amazon S3 - Amazon CloudWatch Logs - AWS IAM - AWS CloudFormation / SAM.

## What is original
1. A map where every change is backed by a recomputed road graph, with bottleneck scoring by exhaustive road removal.
2. Operational status and reachability modeled separately, including a power -> pump -> flood-risk cascade.
3. An optimizer that scores candidates by re-running the simulation, re-validates every intervention server-side (budget, units, radius, reachability), and reports beneficial actions it could not fund.
4. Grounded AI: the model explains computed facts and is validated against them, with a deterministic fallback so the app never depends on AI.

## Verification (actually run)
- 74 backend tests and 47 frontend tests pass; production build succeeds.
- Deployed-API smoke test: 15/15 (health, dataset, CORS, determinism, optimize, compare, Bedrock brief, fallback path, three export formats, validation errors).
- Browser end-to-end run of the full demo on the public URL: 14/14 checks, zero console errors.

## 90-second demo path
Baseline -> **Extreme rainfall** (timeline plays) -> click a pink critical road and **Close this road** -> click a hospital (baseline vs now, alternative route) -> **Response Strategies -> Balanced -> Deploy** -> Recovery comparison -> **Generate AI Situation Brief** -> **Export Results**. Or click preset **6. Coordinated emergency response** for the whole story in one click.

## Honest limitations
Synthetic, fictional district; conceptual uncalibrated flood index; simplified power model; no evacuation or rescue-team modeling; greedy (non-optimal) optimizer; stateless demo without saved scenarios; desktop and tablet first. No real-world user testing or adoption has occurred. Details: `docs/ASSUMPTIONS_AND_LIMITATIONS.md`.

## Roadmap
Ingest verified open data (OSM roads, elevation, census) through the existing GeoJSON schema, calibrate thresholds with a hydrological partner, persist and share scenarios, add evacuation modeling.

**Source:** https://github.com/mahanteshimath/aws-builder-challenge-oct-02 - see `README.md` and `docs/`.

---

## Pre-publish checklist
- [x] Live demo URL verified (Amplify, 2026-10-02) and API healthy
- [x] Cover image generated (1200x675)
- [x] Tests, smoke test and end-to-end run passing
- [ ] **Commit and push the repository** so the GitHub link resolves (not yet done)
- [ ] Optional: add a short screen recording of the 90-second path (none exists yet; do not claim one)
- [ ] Pick tags in the form; use **Preview** before **Publish**
