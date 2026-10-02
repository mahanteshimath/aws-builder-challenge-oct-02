<#
 Remove everything created by deploy.ps1 (API stack, S3 bucket contents, Amplify app, log groups are deleted with the stack).
 Usage: pwsh scripts/teardown.ps1 -Profile hackathon -Region us-east-1 -AmplifyAppId <id>
#>
param([string]$Profile = "hackathon", [string]$Region = "us-east-1", [string]$StackName = "resilience-simulator", [Parameter(Mandatory)][string]$AmplifyAppId)
$env:AWS_PROFILE = $Profile; $env:AWS_REGION = $Region
$bucket = aws cloudformation describe-stacks --stack-name $StackName --query "Stacks[0].Outputs[?OutputKey=='GeoJsonBucketName'].OutputValue" --output text
if ($bucket) { aws s3 rm "s3://$bucket" --recursive }
aws cloudformation delete-stack --stack-name $StackName; aws cloudformation wait stack-delete-complete --stack-name $StackName
aws amplify delete-app --app-id $AmplifyAppId | Out-Null
Write-Host "Teardown complete. The SAM-managed artifact bucket (aws-sam-cli-managed-default) can be removed separately if unused."
