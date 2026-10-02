"""Collect CloudTrail evidence of the development environment's AWS connection (see docs/AWS_AGENT_CONNECTION_PROOF.md).

Every AWS CLI / SAM call made by the release script sets AWS_SDK_UA_APP_ID=cortex-code-agent, so CloudTrail
records `app/cortex-code-agent` in the userAgent of each event. This script queries CloudTrail (management events,
90-day history) and prints a Markdown table. Account IDs and source IPs are partially masked.

Usage:  python scripts/agent_proof.py [--profile hackathon] [--region us-east-1] [--since 2026-10-02T00:00:00Z]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import Counter

EVENTS = ["CreateApp", "UpdateApp", "CreateBranch", "CreateDeployment", "StartDeployment", "CreateChangeSet", "ExecuteChangeSet",
          "DescribeStacks", "UpdateFunctionCode20150331v2", "UpdateFunctionConfiguration20150331v2", "GetInferenceProfile",
          "ListFoundationModels", "PutBucketPolicy", "CreateBucket"]


def aws(args: list[str], profile: str, region: str) -> dict:
    env = {**os.environ, "AWS_SDK_UA_APP_ID": "cortex-code-agent"}
    out = subprocess.check_output(["aws", *args, "--profile", profile, "--region", region, "--output", "json"], env=env)
    return json.loads(out or b"{}")


def mask_account(text: str) -> str:
    return re.sub(r"\b(\d{4})\d{4}(\d{4})\b", r"\1****\2", text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="hackathon")
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--since", default="2026-10-02T00:00:00Z")
    a = ap.parse_args()

    ident = aws(["sts", "get-caller-identity"], a.profile, a.region)
    print("## Caller identity\n")
    print(f"- Account: `{mask_account(ident['Account'])}`  \n- Principal: `{mask_account(ident['Arn'])}`\n")

    rows, tagged = [], Counter()
    for name in EVENTS:
        res = aws(["cloudtrail", "lookup-events", "--lookup-attributes", f"AttributeKey=EventName,AttributeValue={name}",
                   "--start-time", a.since, "--max-results", "50"], a.profile, a.region)
        for e in res.get("Events", []):
            c = json.loads(e["CloudTrailEvent"])
            ua = c.get("userAgent", "")
            app = (re.search(r"app/(\S+)", ua) or [None, ""])[1]
            tool = (re.search(r"(aws-cli/\S+|SAM CLI|Boto3/\S+|aws-sam-cli/\S+)", ua) or [None, ""])[0]
            if app:
                tagged[app] += 1
            ip = re.sub(r"\.\d+\.\d+$", ".x.x", str(c.get("sourceIPAddress", "")))
            rows.append((c["eventTime"], name, c["eventSource"].split(".")[0], e.get("Username", ""), tool, app or "-", ip))
    rows.sort()
    print(f"## CloudTrail management events since {a.since}\n")
    print(f"{len(rows)} events found; tagged with an app id: {dict(tagged) or 'none'}\n")
    print("| Time (UTC) | Event | Service | IAM user | Tool | App tag | Source IP |\n|---|---|---|---|---|---|---|")
    for r in rows[-60:]:
        print("| " + " | ".join(str(x) for x in r) + " |")


if __name__ == "__main__":
    main()
