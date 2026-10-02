import sys, time
from playwright.sync_api import sync_playwright
URL = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True, args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": 1600, "height": 950})
    logs = []
    pg.on("console", lambda m: logs.append((m.type, m.text[:300])) if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: logs.append(("pageerror", str(e)[:300])))
    pg.on("requestfailed", lambda r: logs.append(("reqfailed", r.url[:120] + " " + str(r.failure))))
    pg.goto(URL, wait_until="networkidle", timeout=60000)
    pg.wait_for_selector("[data-testid=app-shell]", timeout=30000)
    time.sleep(4)
    pg.screenshot(path="build/shot1.png")
    print("title:", pg.title())
    print("logs:", logs[:12])
    b.close()
