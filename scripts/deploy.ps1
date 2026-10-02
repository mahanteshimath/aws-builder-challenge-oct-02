<#
 End-to-end deployment: backend (SAM) + GeoJSON to S3 + frontend (AWS Amplify Hosting).
 Usage:  pwsh scripts/deploy.ps1 -Profile hackathon -Region us-east-1 [-AmplifyAppId <id> | -AmplifyAppId ""] [-EnableBedrock true]
         Defaults to the existing Amplify app dxhzlkmrgksnx; pass -AmplifyAppId "" to create a new app.
 Requires: AWS CLI v2, SAM CLI, Python 3.12, Node 18+.  Uses IAM credentials from the named profile (no keys in code).
#>
param(
  [string]$Profile = "hackathon", [string]$Region = "us-east-1", [string]$StackName = "resilience-simulator",
  [string]$AmplifyAppId = "dxhzlkmrgksnx", [string]$EnableBedrock = "true", [string]$BedrockModelId = "us.amazon.nova-lite-v1:0",
  [string]$BedrockBaseModelId = "amazon.nova-lite-v1:0"
)
$ErrorActionPreference = "Stop"
# Tag every AWS CLI / SAM call so the release is identifiable in CloudTrail (userAgent contains app/cortex-code-agent)
if (-not $env:AWS_SDK_UA_APP_ID) { $env:AWS_SDK_UA_APP_ID = "cortex-code-agent" }
$env:AWS_PROFILE = $Profile; $env:AWS_REGION = $Region; $env:SAM_CLI_TELEMETRY = "0"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "1/6 Identity"; aws sts get-caller-identity --query Arn --output text
Write-Host "2/6 Build deterministic Kurla dataset (cached OSM + SRTM) + tests"; python backend/src/data/build_kurla_dataset.py; python -m pytest backend -q
Write-Host "3/6 Amplify app"
if (-not $AmplifyAppId) { $AmplifyAppId = aws amplify create-app --name resilience-simulator --platform WEB --query app.appId --output text; aws amplify create-branch --app-id $AmplifyAppId --branch-name main --stage PRODUCTION | Out-Null }
$origin = "https://main.$AmplifyAppId.amplifyapp.com"
aws amplify update-app --app-id $AmplifyAppId --custom-headers file://infra/amplify-custom-headers.yml | Out-Null
Write-Host "4/6 Build + deploy API (CORS allows $origin)"
python scripts/build_lambda.py
sam deploy --stack-name $StackName --region $Region --resolve-s3 --capabilities CAPABILITY_IAM --no-confirm-changeset --no-fail-on-empty-changeset `
  --parameter-overrides "AllowedOrigins=$origin,http://localhost:5173,http://localhost:4173" "EnableBedrock=$EnableBedrock" "BedrockModelId=$BedrockModelId" "BedrockBaseModelId=$BedrockBaseModelId"
$api = aws cloudformation describe-stacks --stack-name $StackName --query "Stacks[0].Outputs[?OutputKey=='ApiBaseUrl'].OutputValue" --output text
$bucket = aws cloudformation describe-stacks --stack-name $StackName --query "Stacks[0].Outputs[?OutputKey=='GeoJsonBucketName'].OutputValue" --output text
Write-Host "5/6 Upload GeoJSON to private S3 bucket $bucket"
aws s3 sync backend/src/data/geojson "s3://$bucket/geojson/" --exclude "manifest.json" --only-show-errors
Write-Host "6/6 Build + deploy frontend to Amplify"
$env:AMPLIFY_APP_ID = $AmplifyAppId; $env:API_BASE_URL = $api
python scripts/deploy_frontend.py
Write-Host "API:      $api"; Write-Host "Frontend: $origin"
python scripts/smoke_api.py $api $origin
