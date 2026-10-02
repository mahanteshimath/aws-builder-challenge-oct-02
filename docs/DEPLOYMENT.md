# Deployment

Verified deployment target: **us-east-1**, AWS CLI profile **`hackathon`** (IAM user with AdministratorAccess), SAM CLI 1.166.2, AWS CLI 2.36, Python 3.12, Node 24.

## Prerequisites
- AWS CLI v2 configured with a profile (`aws configure --profile hackathon`); confirm with `aws sts get-caller-identity --profile hackathon`.
- SAM CLI (`pip install aws-sam-cli`), Python 3.12, Node 18+.
- Amazon Bedrock model access for the chosen model in the deployment region (Nova models are enabled by default for most accounts; otherwise request access in the Bedrock console). If unavailable, deploy with `EnableBedrock=false` - the app runs on the rule-based brief.

## One command
```powershell
pwsh scripts/deploy.ps1 -Profile hackathon -Region us-east-1
```
Steps performed: generate dataset → backend tests → create Amplify app/branch (first run) → set security headers → `python scripts/build_lambda.py` (Linux wheels into `build/lambda`) → `sam deploy` (CORS = Amplify URL + localhost) → `aws s3 sync` GeoJSON → `npm run build` with `VITE_API_BASE_URL` → zip + Amplify manual deployment → `scripts/smoke_api.py`.

## Manual steps
```powershell
$env:AWS_PROFILE="hackathon"; $env:AWS_REGION="us-east-1"
python scripts/build_lambda.py
sam validate --lint
sam deploy --stack-name resilience-simulator --resolve-s3 --capabilities CAPABILITY_IAM --no-confirm-changeset `
  --parameter-overrides "AllowedOrigins=https://main.<appId>.amplifyapp.com,http://localhost:5173" EnableBedrock=true
aws s3 sync backend/src/data/geojson s3://<GeoJsonBucketName>/geojson/ --exclude manifest.json
$env:AMPLIFY_APP_ID="<appId>"; $env:API_BASE_URL="<ApiBaseUrl output>"; python scripts/deploy_frontend.py
python scripts/smoke_api.py <ApiBaseUrl> https://main.<appId>.amplifyapp.com
```

## Template parameters
| Parameter | Default | Purpose |
|---|---|---|
| `AllowedOrigins` | `http://localhost:5173` | Comma list of browser origins allowed by CORS (no wildcard) |
| `EnableBedrock` | `true` | `false` forces the rule-based brief |
| `BedrockModelId` | `us.amazon.nova-lite-v1:0` | Model / inference profile id for `Converse` |
| `BedrockBaseModelId` | `amazon.nova-lite-v1:0` | Foundation model behind the profile (scopes IAM) |
| `LogLevel` | `INFO` | Lambda log level |

Stack outputs: `ApiBaseUrl`, `GeoJsonBucketName`.

## Configuration reference
Frontend (`frontend/.env.example`): `VITE_API_BASE_URL`, `VITE_MAP_STYLE_URL` (optional MapLibre style), `VITE_APP_VERSION`. Backend (`backend/.env.example` / template env): `AWS_REGION`, `GEOJSON_BUCKET`, `GEOJSON_PREFIX`, `BEDROCK_MODEL_ID`, `ENABLE_BEDROCK`, `ALLOWED_ORIGINS` (template param), `LOG_LEVEL`, `SIMULATION_VERSION`, `MAX_SIMULATION_INPUT_SIZE`. No secrets are needed; `.env*` files are git-ignored.

## Verification performed (2026-10-02)
| Check | Result |
|---|---|
| `sam validate --lint` | valid |
| CloudFormation stack `resilience-simulator` | `CREATE_COMPLETE` |
| `scripts/smoke_api.py` against the deployed API with the Amplify origin | 15/15 passed (health, dataset, CORS header, simulate, determinism, optimize, compare, Bedrock brief, fallback path, 3 export formats, 422 validation, 422 unknown id, 404) |
| CORS preflight from an unlisted origin | no `Access-Control-Allow-Origin` header returned |
| `scripts/e2e_flow.py` (Chrome via Playwright) against the Amplify URL | 14/14 passed, 0 console errors (test harness bypasses CSP only for its own `eval`-based waits; a separate CSP-enforced load showed no violations) |
| Bedrock | live brief returned `provider: bedrock`, model `us.amazon.nova-lite-v1:0`, IDs validated against the facts |

## Updating
Backend code change → `python scripts/build_lambda.py; sam deploy ...`. Frontend change → `python scripts/deploy_frontend.py`. Dataset change → regenerate, re-sync to S3 and redeploy the Lambda bundle (bundled copy is the fallback).

## Teardown
`pwsh scripts/teardown.ps1 -Profile hackathon -AmplifyAppId <id>` (empties/deletes the bucket via the stack, deletes the stack and Amplify app). Afterwards optionally delete leftover `/aws/lambda/resilience-simulator-*` log groups and the SAM artifact bucket.
