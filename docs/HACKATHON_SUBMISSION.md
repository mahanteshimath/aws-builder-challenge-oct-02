# Hackathon submission summary

The copy-paste text for the AWS Builder Center form (title, description, tags, links, body) is in [`../submission.md`](../submission.md). This page is the one-screen summary.

| Field | Value |
|---|---|
| Project | Resilience Simulator - Kurla / Mithi River, Mumbai |
| Tagline | Stress-test a neighborhood before disaster strikes. |
| App category tag | `#social-good` (climate resilience) |
| Lane tag | `#community` |
| Live app | https://main.dxhzlkmrgksnx.amplifyapp.com |
| Live API health | https://4wbvz70w98.execute-api.us-east-1.amazonaws.com/api/v1/health (`dataset_version: kurla-mithi-osm-1.0`) |
| Source | https://github.com/mahanteshimath/aws-builder-challenge-oct-02 |
| Development environment | VS Code with Snowflake Cortex Code, AWS CLI v2 / SAM CLI, profile `hackathon` |
| AWS connection evidence | [AWS_AGENT_CONNECTION_PROOF.md](AWS_AGENT_CONNECTION_PROOF.md) - CloudTrail events tagged `app/cortex-code-agent`; regenerate with `scripts/agent_proof.py` |
| Development process | [DEVELOPMENT_PROCESS.md](DEVELOPMENT_PROCESS.md) |
| Analysis and findings | [ANALYSIS_AND_FINDINGS.md](ANALYSIS_AND_FINDINGS.md) - reproducible with `scripts/run_analysis.py` |
| Final release | 2026-10-02 17:35 UTC - CloudFormation `UPDATE_COMPLETE`, Amplify jobs 7-8 `SUCCEED`, smoke 15/15, browser E2E 14/14 |
| AWS services | Amazon Bedrock (Nova Lite, Converse) · AWS Amplify Hosting · Amazon API Gateway HTTP API · AWS Lambda · Amazon S3 · Amazon CloudWatch Logs · AWS IAM · AWS CloudFormation / SAM · AWS CloudTrail |
| Data | OpenStreetMap (ODbL) roads, bridges, river, facilities; SRTM 30 m terrain; Census 2011 Ward L density; modeled populations, capacities, power links, pumps, resources |
| Demo | [DEMO_SCRIPT.md](DEMO_SCRIPT.md) (90 s) · screenshots in `docs/screenshots/` · demo video: not yet recorded |

## Headline result (deterministic, reproducible on the live app)
Closing the SCLR rail over-bridge under 120 mm of rain leaves 104,400 modeled residents of Nehru Nagar and Tilak Nagar with no route to any hospital. In the compound emergency (150 mm + over-bridge closed + Mithi-bank substation down) 206,400 residents have reduced access to an essential service; a 30-lakh *Maximize population access* plan brings that to 0 in the re-run model (51,800 person-service equivalents restored).

## What has not happened yet
No community group has run a drill with the tool; no validation against observed flood extents; populations and infrastructure links are modeled. The submission makes no real-world impact claim.
