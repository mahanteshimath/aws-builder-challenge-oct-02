# Hackathon submission draft

**Project name:** Resilience Simulator
**Tagline:** Stress-test a neighborhood before disaster strikes.
**Public application URL (verified 2026-10-02):** https://main.dxhzlkmrgksnx.amplifyapp.com
**Public API health endpoint (verified):** https://4wbvz70w98.execute-api.us-east-1.amazonaws.com/api/v1/health
**Source:** this repository (README.md). **Demo video / pitch deck:** _[placeholder - not yet produced]_

## Problem
Neighborhood emergencies are cascades - a flooded bridge isolates a clinic, a substation outage stops the pump that kept a road dry, shelter capacity ends up on the wrong side of a river. Local planners and community resilience groups rarely have an affordable, explorable way to ask "what breaks first, who loses access to care, and where does the next unit of response help most?" before an event.

## Solution
An interactive neighborhood-scale **climate-emergency digital twin**. Users set rainfall, drainage, road closures and power/pump failures on a live map; a **deterministic engine** recomputes flood risk, road states, network travel times to hospitals/shelters/water, population exposure and the criticality of every road. A **budget-constrained optimizer** chooses response actions under three strategies and the engine **re-runs** to measure the modeled recovery. **Amazon Bedrock** turns the computed facts into a grounded situation brief - with a clearly labelled rule-based fallback.

## Architecture
React + MapLibre SPA on **AWS Amplify Hosting** → **API Gateway HTTP API** (CORS allow-list, throttling) → two **Python 3.12 Lambda** functions sharing one engine → private **S3** GeoJSON, **Amazon Bedrock Runtime** (brief only, on demand), **CloudWatch Logs**. Infrastructure as code with **AWS SAM**. Diagram: README / docs/ARCHITECTURE.md.

## AWS services used (all verified in the deployed account)
Amazon Bedrock (Runtime `Converse`, Nova Lite inference profile `us.amazon.nova-lite-v1:0`) · AWS Amplify Hosting · Amazon API Gateway (HTTP API) · AWS Lambda · Amazon S3 · Amazon CloudWatch Logs · AWS IAM · AWS CloudFormation (via SAM).

## What is original
- A transparent, explainable **flood → road graph → service-accessibility → criticality** pipeline where every map change is backed by a recomputed graph, not a recolor.
- **Bottleneck analysis** by exhaustive single-road removal weighted by population and three essential services, with "sole route to facility" detection.
- **Operational status and reachability modelled separately**, including a **power → pump → flood-risk cascade**.
- An optimizer whose candidates are scored by **re-running the simulation**, with server-side re-costing/validation of every intervention, three genuinely different strategies, and a "beneficial actions that could not be completed" report.
- **Grounded AI**: the server recomputes the facts, Bedrock only writes prose, and output is rejected (→ deterministic fallback) if it cites any road/facility/zone ID absent from the facts.
- Reproducible, teardown-able serverless deployment with no database and no always-on compute.

## Demo flow
Baseline → Extreme rainfall (timeline plays) → click a critical road and close it → inspect a hospital (baseline vs now, alternative route) → deploy Balanced response → Recovery comparison → Generate AI brief → export report. Script: docs/DEMO_SCRIPT.md.

## Social benefit (intended)
A low-cost way for municipal teams, NGOs and students in flood-prone regions to rehearse compound failures, identify single points of failure in access to care, and compare response options. **No real-world adoption, user testing or impact has occurred yet** - this submission makes no such claim.

## Verification evidence
- Backend unit/integration tests: 74 passed. Frontend tests: 47 passed. Production build succeeds.
- Deployed API smoke test: 15/15. Browser end-to-end run of the full demo on the public URL: 14/14, 0 console errors.
- Amazon Bedrock verified live (`provider: bedrock`); fallback path verified live (`allow_ai=false`) and by unit tests simulating throttling, access denial, model-unavailable, timeout and invalid output.

## Current limitations
Synthetic, fictional district; conceptual uncalibrated flood index; simplified power model; no evacuation/rescue modelling; greedy (non-optimal) optimizer; stateless demo with no scenario persistence; desktop/tablet-first layout. See docs/ASSUMPTIONS_AND_LIMITATIONS.md.

## Roadmap (not implemented)
Ingest verified open datasets (OSM roads, elevation/DEM, census) through the existing GeoJSON schema; calibrate thresholds with a hydrological partner; persist and share scenarios; evacuation and rescue-team modelling; multi-hazard (heat, cyclone).
