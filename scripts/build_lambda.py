"""Build the Lambda deployment folder (build/lambda) with Linux wheels so it works when built from Windows/macOS."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "lambda"
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", str(ROOT / "backend" / "requirements.txt"), "-t", str(OUT),
                       "--platform", "manylinux2014_x86_64", "--implementation", "cp", "--python-version", "3.12",
                       "--only-binary=:all:", "--upgrade"])
shutil.copytree(ROOT / "backend" / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "generate_demo_data.py", "build_kurla_dataset.py", "local_server.py"))
for p in OUT.rglob("*.dist-info"):
    shutil.rmtree(p, ignore_errors=True)
size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file()) / 1e6
print(f"Built {OUT} ({size:.1f} MB)")
