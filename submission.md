# AWS Builder Center - "Edit project" submission (copy each block into the matching field)

## Title (max 255)
```
Resilience Simulator: stress-test Kurla, Mumbai before the next monsoon
```

## Description (max 512)
```
A flood digital twin of Kurla, Mumbai on real OpenStreetMap roads, Mithi River bridges and hospitals. Add rain, close a bridge or cut a substation and a deterministic engine recomputes who loses access to hospitals, shelters and water; a budget optimizer tests responses and Amazon Bedrock writes a grounded brief. Built and deployed by a coding agent on AWS for local tabletop drills.
```

## Cover image (optional, 1200x675, <2 MB)
Upload `docs/screenshots/cover-1200x675.png` (1200x675, ~370 KB). The same image is served as `og-cover.png` on the live site.

## Tags (max 5) - the first two are REQUIRED by the rules
1. `#social-good` (app category - climate resilience focus area)
2. `#community` (lane)
3. `Amazon Bedrock`
4. `AWS Lambda`
5. `AWS Amplify`

## Links
| Field | Value |
|---|---|
| GitHub or GitLab repository | https://github.com/mahanteshimath/aws-builder-challenge-oct-02 |
| Endpoint or live demo | https://main.dxhzlkmrgksnx.amplifyapp.com |
| Jupyter / SageMaker notebook | Not applicable - leave blank |
| API health (optional, for the body) | https://4wbvz70w98.execute-api.us-east-1.amazonaws.com/api/v1/health |

## Body (paste into the editor, or toggle **Markdown** and paste as-is)

---

# Resilience Simulator - Kurla / Mithi River, Mumbai

**Category:** Social Good (climate resilience) · **Lane:** Community · **Live app (no sign-in):** https://main.dxhzlkmrgksnx.amplifyapp.com

![Cover](https://main.dxhzlkmrgksnx.amplifyapp.com/og-cover.png)

## The story
On 26 July 2005, 944 mm of rain fell on Mumbai in 24 hours. Kurla, with the Mithi River running down its west side, was among the hardest-hit areas - its BEST bus depot suffered serious damage and was shut for years. Every monsoon since, the same question comes back in residents' groups and volunteer chats: *if the water rises tonight, which road do we lose first, and can people still get to Bhabha Hospital?*

Kurla answers that question in a very particular way. The Mithi cuts it on the west, the Central Railway line splits it east from west, and only a handful of bridges and rail over-bridges hold it together. Resilience Simulator makes that visible: it is a free, browser-based **tabletop-drill tool** for the groups I am part of and work with in Mumbai - tech meetups that run civic-tech sessions, residents' and disaster-volunteer groups in flood-prone wards, and college classes studying urban climate resilience.

## What it does
- **Real map.** 150 road segments, 5 Mithi River crossings, 13 flyover / rail over-bridge segments and 29 named facilities (including K.B. Bhabha Municipal General Hospital, Kalina Hospital, CritiCare Asia, police and fire stations, schools) from **OpenStreetMap**; terrain from **SRTM 30 m**; 8 real neighbourhoods with ~482,600 modeled residents scaled from **Census 2011 Ward L** density.
- **Deterministic simulation.** Rainfall, duration and drainage feed a transparent flood-risk index (SRTM elevation + Mithi / nala proximity). Roads become Open / Degraded / Restricted / Closed and travel times are recomputed with **Dijkstra on the road graph** - closing a road changes routes, not just colours.
- **Cascades.** A substation outage stops the pumps it feeds, which raises flood risk, which closes roads. A facility's *operational status* (power, backup hours) is tracked separately from its *reachability*.
- **Single points of failure.** Every road is removed in turn and scored by population-weighted loss of hospital / shelter / water access, with "sole route" detection.
- **Response optimizer.** Three strategies (Protect critical services, Maximize population access, Balanced) choose road clearance, generators, water tankers, temporary medical units and shelter kits under a budget. Every candidate is scored by **re-running the engine**; recovery is another re-run.
- **AI Situation Brief.** Amazon Bedrock (Nova Lite) turns the computed facts into a brief. The server recomputes the facts, the model only writes prose, and output is rejected - falling back to a labelled rule-based brief - if it cites any road, facility or zone ID that is not in the simulation output.
- Baseline vs Disaster vs Recovery comparison, a 6-stage timeline, JSON / CSV / HTML export, importable scenario files.

## What a drill shows (deterministic, reproducible on the live app)
| Scenario | Modeled result |
|---|---|
| Baseline | 4/4 hospitals reachable, 3.6 min average hospital travel |
| Heavy monsoon rainfall (100 mm / 6 h) | ~43,000 people in modeled flood-risk zones; 53 road segments affected |
| 120 mm + **SCLR rail over-bridge closed** | **104,400** residents of Nehru Nagar and Tilak Nagar lose timely hospital access; 2 neighbourhoods have no route to any hospital |
| Compound emergency (150 mm + over-bridge closed + Mithi-bank substation down) | 206,400 residents with reduced access to an essential service |
| + 30-lakh *Maximize population access* plan | **0** residents with reduced access in the re-run model; 51,800 person-service equivalents restored for 29.9 lakh |

The point is not the exact numbers - they rest on modeled populations - but the structure they reveal: one over-bridge is the difference between east Kurla reaching a hospital or not, and the cheapest high-value action in a crisis is clearing it.

## How I built it with a coding agent connected to AWS
I used **Snowflake Cortex Code** (VS Code) as the coding agent, connected to my AWS account through the **AWS CLI v2 / SAM CLI** with the `hackathon` profile. The agent:
1. checked the identity and region, listed Bedrock models and inference profiles;
2. wrote the engine, 75 backend tests and 47 frontend tests, the SAM template and deploy scripts;
3. created the Amplify app, deployed the SAM stack (API Gateway, two Lambdas, private S3, IAM, CloudWatch), uploaded data and deployed the SPA;
4. ran a 15-check API smoke test and a 14-check Playwright browser test against the **public** URLs - and used those runs to find and fix real bugs (transparent panels, a recovery metric that gave zero credit for reconnecting a cut-off neighbourhood);
5. rebuilt the dataset from OpenStreetMap + SRTM for Kurla, calibrated it by running the engine, and redeployed;
6. shipped the final release with one command (`pwsh scripts/deploy.ps1`: dataset build â†’ tests â†’ SAM deploy â†’ S3 sync â†’ Amplify deployment â†’ smoke test) and re-verified the public URLs.

**Proof of the connection:** every AWS call the agent makes is tagged `AWS_SDK_UA_APP_ID=cortex-code-agent`, so CloudTrail shows `app/cortex-code-agent` on the `CreateChangeSet`, `ExecuteChangeSet`, `UpdateFunctionConfiguration`, `CreateDeployment` and `StartDeployment` events. The masked CloudTrail table, identity and resource list are in [`docs/AWS_AGENT_CONNECTION_PROOF.md`](https://github.com/mahanteshimath/aws-builder-challenge-oct-02/blob/main/docs/AWS_AGENT_CONNECTION_PROOF.md); screenshots of the agent chat running the deploy are attached below.

<!-- Attach 2-3 screenshots here: (1) agent chat running `aws sts get-caller-identity` / `sam deploy`, (2) Amplify deployment job SUCCEED, (3) smoke test ALL PASSED -->

## Architecture
```
Browser -> React + MapLibre SPA (AWS Amplify Hosting, CSP + security headers)
        -> Amazon API Gateway HTTP API (CORS allow-list, throttling, access logs)
        -> AWS Lambda (Python 3.12): simulate / optimize / compare / export / dataset --+
        -> AWS Lambda (Python 3.12): situation brief ----------------------------------+--> shared deterministic engine
                                   |-> Amazon Bedrock (Nova Lite, Converse API)          |-> private Amazon S3 (Kurla GeoJSON)
                                   '-> rule-based fallback on any failure                '-> Amazon CloudWatch Logs
```
Infrastructure as code with **AWS SAM**; IAM least privilege (`bedrock:InvokeModel` on one model + profile, S3 read on one bucket); no database, no always-on compute; Bedrock is called only when the user clicks *Generate*.

## AWS services used
Amazon Bedrock (Runtime, Converse API, Nova Lite inference profile) · AWS Amplify Hosting · Amazon API Gateway (HTTP API) · AWS Lambda · Amazon S3 · Amazon CloudWatch Logs · AWS IAM · AWS CloudFormation / SAM · AWS CloudTrail (agent audit trail).

## What is original
1. A neighbourhood digital twin where every map change is backed by a recomputed road graph, on real OSM geography of a flood-prone Mumbai ward.
2. Bottleneck scoring by exhaustive road removal, which surfaces Kurla's rail over-bridges as its single points of failure.
3. Operational status and reachability modeled separately, including a power → pump → flood-risk cascade.
4. An optimizer that scores every candidate by re-running the simulation, re-validates every intervention server-side, and credits partial recovery when a cut-off neighbourhood is reconnected.
5. Grounded AI: Bedrock explains computed facts and is validated against them, with a deterministic fallback so the tool never depends on AI.

## Impact - measured so far, honestly
- **Measured in the model:** the drill above quantifies which single structure matters most (SCLR over-bridge: 104,400 residents) and what a 30-lakh plan buys (206,400 → 0 residents with reduced access).
- **Not yet measured in the real world:** no group has run a drill with it yet, and populations, capacities, power links and most pumps are modeled, not official BMC data. It is a planning and education tool, not a flood forecast or an operational system.
- **Next 30 days (Community lane plan):** run one 45-minute drill each with a tech meetup, a residents' / volunteer group and a college class; record which bottlenecks and plans they disagree with; replace modeled populations with ward-level figures and validate flood pockets against the 2005 and 2017 flood reports; publish the drill kit so other wards can load their own OSM extract (the builder script already takes any bounding box).

## Verification (actually run against the live deployment)
- 75 backend tests and 47 frontend tests pass; production build succeeds.
- Deployed-API smoke test: 15/15 (health, dataset provenance, CORS, determinism, optimize, compare, live Bedrock brief, fallback path, three export formats, validation errors).
- Browser end-to-end run of the full demo on the public URL: 14/14 checks, zero console errors.
- Final release 2026-10-02 17:35 UTC: CloudFormation `UPDATE_COMPLETE`, Amplify deployment job 7 `SUCCEED`; 22 of 26 CloudTrail events since 17:00 UTC tagged `app/cortex-code-agent`.

## 90-second demo path
Baseline → **3. Extreme rainfall** (timeline plays) → click the pink **SCLR rail over-bridge** and **Close this road** → click **Bhabha Hospital** (zones cut off, baseline vs now) → **Response Strategies → B · Maximize population access → Deploy** → Recovery (104,400 → 0) → **Generate AI Situation Brief** → **Export Results**. Or click preset **6. Coordinated emergency response** for the whole story in one click.

## Data credits and limits
Map data © OpenStreetMap contributors (ODbL 1.0). Terrain SRTM 30 m (public domain). Ward density: Census of India 2011. Modeled: zone populations, capacities, backup power, power links, 3 of 4 power nodes, 5 of 6 pumps, response resources and costs. Conceptual, uncalibrated flood index. Full list: `docs/ASSUMPTIONS_AND_LIMITATIONS.md`.

**Source:** https://github.com/mahanteshimath/aws-builder-challenge-oct-02

---

## Pre-publish checklist
- [x] Live demo URL verified on the Kurla data (final release: Amplify job 7, 2026-10-02 17:35 UTC) and API healthy (`kurla-mithi-osm-1.0`)
- [x] Proof of coding-agent connection documented (`docs/AWS_AGENT_CONNECTION_PROOF.md`, CloudTrail `app/cortex-code-agent`)
- [x] Category tag `#social-good` and lane tag `#community` listed above
- [x] Cover image regenerated for Kurla (1200x675)
- [x] Tests (75 backend / 47 frontend), smoke test (15/15) and end-to-end run (14/14) passing on the deployed system
- [x] Committed and pushed to `main` so the GitHub links resolve to the Kurla version
- [ ] **Attach 2-3 screenshots** of the Cortex Code chat running the AWS deploy (the agent cannot capture your screen)
- [ ] Optional but recommended for storytelling: record the 90-second demo path (`docs/DEMO_SCRIPT.md`) and add the video link
- [ ] Pick the tags in the form; use **Preview** before **Publish**; publish before **Oct 2, 2026, 11:59 PM PT**
