# Agent development log

This log describes what the coding agent (Snowflake Cortex Code) actually did in this repository on **2026-10-02**, in two sessions (session 1: model `claude-sonnet-5-5`, synthetic build; session 2: model `claude-opus-5-5`, hackathon review and real-data rebuild). Nothing here is estimated or aspirational. AWS-connection evidence: [AWS_AGENT_CONNECTION_PROOF.md](AWS_AGENT_CONNECTION_PROOF.md).

## Environment inspected
Windows 11, PowerShell 7. Node 24.14, npm 11.9, Python 3.12.10, AWS CLI 2.36.34. **SAM CLI was not installed** - installed with `pip install aws-sam-cli` (see side effects). AWS profiles found: `workshop-profile` and `developer_ai` (expired tokens), `ai-hack` (no credentials), `hackathon` (valid, us-east-1). Repository contained only a README stub. AWS access confirmed with `sts get-caller-identity`; Amplify and Bedrock listing permissions confirmed; `nova` foundation models and `us.amazon.nova-*` inference profiles listed.

## Work completed, in order
1. **Dataset** - wrote `generate_demo_data.py` (fixed seed) producing 91 roads/63 nodes/29 facilities/8 zones/6 hazard areas/10 infrastructure assets/5 depots/7 resource pools. Tuned the road removal rule so the river is a real barrier (few bridges) while keeping the graph connected.
2. **Engine** - implemented flood model, Dijkstra graph, accessibility, exposure, power/pump cascade, bottleneck scan, scenario engine, intervention validation, optimizer, timeline, comparison, export, presets, Pydantic models.
3. **Calibration (iterated by running the engine)** - the first sweep showed 100 mm rainfall producing zero exposure yet 29 affected roads (hazard-zone drainage was too generous), and 170 mm affecting 72 of 91 roads. Changed hazard-zone drainage, `GAIN` 1.8 → 1.5 and the restricted penalty 3.0 → 2.5. Resource quantities/costs were also tightened after the first optimizer run reached 100 % recovery on a 60-lakh budget; default budget set to 30.
4. **Backend tests** - 74 tests. First run: 72 passed, **2 failed because the tests were wrong** (restoring a drainage pump legitimately lowers flood-closed roads; a facility shared a node with a zone anchor so was always reachable from it). Tests were corrected to assert the intended invariants - engine behaviour was not changed.
5. **API + AI** - handlers, local server, Bedrock client, grounded brief generator with ID validation, rule-based fallback. Real Bedrock call verified locally (Nova Lite, ~10 s) before deployment.
6. **AWS** - `template.yaml`, `scripts/build_lambda.py` (Linux wheels; `sam build` on Windows would have bundled Windows binaries). Created Amplify app `dxhzlkmrgksnx`, deployed stack `resilience-simulator` (CREATE_COMPLETE), uploaded GeoJSON, applied Amplify custom headers (CSP etc.).
7. **Frontend** - React/TS/Vite/Tailwind app: map (icons drawn on canvas, pattern fills, data-driven layers), controls, metrics, inspector, timeline, comparison, response, brief, export/import, SVG fallback map, help dialog.
8. **Frontend tests** - 47 Vitest tests. Required a `ResizeObserver` polyfill for Radix sliders in jsdom and a store-state reset between tests (one failure was test leakage, not an app bug).
9. **Verification on the deployed system** - the built-in browser tool was blocked (`ERR_BLOCKED_BY_CLIENT`, even for example.com), so a Playwright script drove the installed Chrome instead (venv under `build/e2e`). Found and fixed: `bg-panel/92` and `/96` are not valid Tailwind opacity steps, so the inspector and legend were transparent; the legend was open by default and covered the map; mobile map height collapsed; metric delta badges overflowed. Also found that the Amplify CSP correctly blocks Playwright's `eval`-based waits (harness now bypasses CSP only when `BYPASS_CSP=1`).
10. **Docs/scripts** - README, docs/*, deploy/teardown/smoke/E2E scripts.

## Results actually observed
| Item | Result |
|---|---|
| `python -m pytest backend` | 74 passed (≈ 5-8 s) |
| `npx vitest run` | 47 passed |
| `npx tsc --noEmit`, `vite build` | clean / succeeded (bundle ≈ 1.69 MB, 475 kB gzip; single chunk, not code-split) |
| `scripts/smoke_api.py` on the deployed API | 15/15 passed; informal single-run latencies: health 1.4 s (cold), simulate 2.2 s, optimize 3.7 s, Bedrock brief 5.1 s, export ≈ 1.1 s |
| `scripts/e2e_flow.py` on the Amplify URL | 14/14 passed, 0 console errors |
| Demo data (deterministic) | baseline: 0 exposed, 4/4 hospitals, 5.69 min avg; Extreme rainfall: 20,426 exposed, 34,600 with reduced hospital access, 61 roads affected / 3 closed, 3/4 hospitals; Extreme rainfall (160 mm, drainage 35 %) + R-019 closed + Balanced response (28.9 of 30 lakh): reduced-access people 62,300 -> 9,800, 22,300 person-service equivalents restored; preset 6 (Compound emergency + Balanced): reduced hospital access 27,400 -> 0, 19,767 restored; see docs/DEMO_SCRIPT.md |

Latencies are single observations, not benchmarks. No load testing was performed.

## Things the agent could not or did not do
- No real users tested the product; no social-impact or adoption data exists.
- Not load-tested; Lambda cold-start/latency numbers above are one-off observations.
- No screen-reader audit; accessibility relies on semantic HTML, labels, keyboard operability of Radix controls, and non-colour status cues, verified only by unit tests and visual inspection.
- The map was verified in desktop Chrome with software WebGL (SwiftShader); other browsers/GPUs were not tested.
- Mobile layout is a stacked fallback and was checked only via screenshots at 390 px.
- Rescue-team/evacuation resource types from the brief were not modelled (documented).

## Environment side effects (user attention)
`pip install aws-sam-cli` (and pydantic/pytest/boto3) was run against the **global** Python 3.12 and upgraded shared packages (`pydantic 2.13.5`, `rich 15.0.0`, `pyyaml 6.0.3`, `watchdog 4.0.2`); pip warned that this now conflicts with pins in `snowflake-cli 3.27.0` (needs `pydantic==2.12.5`, `pyyaml==6.0.2`, `rich==14.0.0`) and `strands-agents*` (`watchdog>=6`). If those tools are used from this interpreter, reinstall the pinned versions or use separate virtualenvs. Playwright was installed only in `build/e2e` (git-ignored). AWS resources created in the hackathon profile's account / us-east-1: CloudFormation stack `resilience-simulator` (HTTP API, 2 Lambdas, 1 S3 bucket, log group, IAM roles), Amplify app `dxhzlkmrgksnx`, and the SAM-managed artifact bucket.

## Session 2 - hackathon review and real-data rebuild (2026-10-02, evening IST)

**Review against the rules.** Verified the ship gate live (Amplify 200, API health 200, GitHub repo 200, stack `CREATE_COMPLETE`). Found two pass/fail gaps in the submission text: no documented proof of the agent's AWS connection, and no category / lane tags. Found two scoring gaps: impact (fictional district, no audience) and storytelling (empty SPA shell for non-JS crawlers, no human story). Builder chose **#social-good** (climate resilience) and the **#community** lane, and asked for real data on **Kurla / Mithi River, Mumbai**.

**Work completed, in order**
1. **Proof of connection** - tagged all agent AWS calls with `AWS_SDK_UA_APP_ID=cortex-code-agent`; wrote `scripts/agent_proof.py` (CloudTrail `LookupEvents`, masked) and `docs/AWS_AGENT_CONNECTION_PROOF.md`.
2. **Real data** - fetched OpenStreetMap (Overpass API: ~1,200 elements incl. 887 road ways, Mithi River, 75 hospitals, substations, pumping stations, 70 place names) and an SRTM 30 m elevation grid (OpenTopoData, 616 points); cached them in `backend/data_sources/`. Census 2011 Ward L density (892,278 / 13.46 kmÂ²) taken from Wikipedia's BMC ward table. Wrote `backend/src/data/build_kurla_dataset.py`: splits OSM ways at junctions, merges junctions within 120 m, keeps the best carriageway per pair, contracts pass-through nodes (812 raw edges â†’ 150 segments, 105 nodes), detects Mithi crossings and flyovers, derives susceptibility from SRTM rank + Mithi / nala proximity, partitions the area into 8 real neighbourhoods, and labels every modeled attribute.
3. **Engine adjustments (backwards compatible)** - exposure sampling accepts explicit sample points for non-rectangular zones; road midpoint uses the middle vertex instead of index 1 (engine, interventions, frontend marker).
4. **Calibration by running the engine** - first build anchored two zones to degree-2 nodes, so dead-end spurs topped the bottleneck list â†’ anchors moved to the nearest junction with >= 3 roads. A sweep of every bridge / arterial closure found the SCLR rail over-bridge (R-059) is the highest-impact single closure (104,400 residents lose timely hospital access), which became the preset closure. With the original resource pools the 30-lakh budget never bound and all strategies chose identical plans â†’ pool sizes raised so trade-offs appear.
5. **Bug found by the live E2E run and fixed** - after deploying, the browser test passed but showed "0 person-service equivalents restored" when the response reopened R-059. Cause: the recovery metric and optimizer only credited a service when it returned to within 25 % of baseline, so reconnecting a completely cut-off zone (no route â†’ reachable but slower) scored zero. Fixed with a per-service severity (cut off = 1, delayed = 0.5, normal = 0) in `scenario_engine.py` and `response_optimizer.py`; added `test_reconnecting_a_cut_off_zone_earns_recovery_credit`; tightened the E2E check to require > 0.
6. **Labels and docs** - replaced every "synthetic / Sahyadri" surface with provenance labels and OSM attribution (API, exports, Bedrock prompt, rule-based brief, UI, map sources); fixed `metrics.py`, which documented road penalties as ×1.4 / ×3.0 while the engine uses ×1.3 / ×2.5; rule-based brief now lists user-selected closures first.
7. **Crawler-readable page** - `index.html` now has a `<noscript>` summary and Open Graph / Twitter tags with a new 1200×675 cover (`og-cover.png`).
8. **Redeploy** - `sam deploy` (twice), S3 sync of the 10 Kurla layers, Amplify deployment job 4, all with the agent UA tag.

**Results actually observed (session 2)**
| Item | Result |
|---|---|
| `python -m pytest backend` | 75 passed |
| `npx vitest run` / `tsc --noEmit` / `vite build` | 47 passed / clean / succeeded |
| `scripts/smoke_api.py` on the deployed API | 15/15, Bedrock brief `provider=bedrock` |
| `scripts/e2e_flow.py` on the Amplify URL | 14/14, 0 console errors, 34,800 person-service equivalents restored in the demo path |
| Engine time on Kurla data | ~0.15 s per scenario; ~1 s per optimizer strategy |

**Not done / limits (session 2)** - no real users or partner organisation have used the tool; no validation against observed 2005 / 2017 flood extents; populations, capacities, power links and most pumps remain modeled; the agent could not take screenshots of the VS Code chat (builder to attach); no demo video was produced.

## Session 2b - final release (2026-10-02, ~23:00 IST)
- Ran the full one-command release `pwsh scripts/deploy.ps1 -AmplifyAppId dxhzlkmrgksnx`: Kurla dataset rebuilt (identical), 75 backend tests passed, Amplify security headers re-applied, SAM stack updated, GeoJSON re-synced to S3, Amplify deployment **job 6** `SUCCEED`, smoke test 15/15 (live Bedrock brief).
- Found that the script's CORS list dropped `http://localhost:4173` (used for `vite preview`) and that it would create a *new* Amplify app when `-AmplifyAppId` was omitted. Fixed both (default app id `dxhzlkmrgksnx`, origin list restored) and re-ran the release: stack `UPDATE_COMPLETE` (17:35 UTC), Amplify **job 7** `SUCCEED`, smoke test 15/15.
- Browser E2E (`scripts/e2e_flow.py`) on the public URL after the release: 14/14, 0 console errors.
- CloudTrail since 17:00 UTC: 22 of 26 management events tagged `app/cortex-code-agent`; added to `AWS_AGENT_CONNECTION_PROOF.md`.
- Commits for this release are authored as `mahanteshimath <mahanteshimath@gmail.com>`, set per command (`git -c user.name=... -c user.email=...`) without changing the repository's git config. The previous commit `80d905c` carries the machine's default identity and was left as is (rewriting pushed history needs a force push).
