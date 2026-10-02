import os, shutil, subprocess, sys, zipfile, urllib.request, json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
FE = ROOT / "frontend"
APP_ID = os.environ["AMPLIFY_APP_ID"]; API = os.environ["API_BASE_URL"]; BRANCH = os.environ.get("AMPLIFY_BRANCH", "main")
env = {**os.environ, "VITE_API_BASE_URL": API}
npm = shutil.which("npm") or "npm"
subprocess.check_call([npm, "run", "build"], cwd=FE, env=env, shell=(os.name == "nt"))
zp = ROOT / "build" / "frontend.zip"; zp.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for f in (FE / "dist").rglob("*"):
        if f.is_file(): z.write(f, f.relative_to(FE / "dist").as_posix())
aws = shutil.which("aws") or "aws"
out = json.loads(subprocess.check_output([aws, "amplify", "create-deployment", "--app-id", APP_ID, "--branch-name", BRANCH, "--output", "json"]))
req = urllib.request.Request(out["zipUploadUrl"], data=zp.read_bytes(), method="PUT", headers={"Content-Type": "application/zip"})
urllib.request.urlopen(req).read()
subprocess.check_call([aws, "amplify", "start-deployment", "--app-id", APP_ID, "--branch-name", BRANCH, "--job-id", out["jobId"], "--output", "json"])
for _ in range(60):
    st = json.loads(subprocess.check_output([aws, "amplify", "get-job", "--app-id", APP_ID, "--branch-name", BRANCH, "--job-id", out["jobId"], "--output", "json"]))["job"]["summary"]["status"]
    print("amplify job", out["jobId"], st)
    if st in ("SUCCEED", "FAILED", "CANCELLED"): break
    time.sleep(4)
sys.exit(0 if st == "SUCCEED" else 1)
