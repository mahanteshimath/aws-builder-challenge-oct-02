import json, os, sys, time
from playwright.sync_api import sync_playwright, expect
BASE = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else "build/e2e"
results = []
def check(name, ok, extra=""):
    results.append((name, bool(ok)))
    print(("PASS" if ok else "FAIL"), name, extra)

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True, args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    ctx = b.new_context(viewport={"width": 1600, "height": 950}, accept_downloads=True, bypass_csp=bool(os.environ.get("BYPASS_CSP")))
    pg = ctx.new_page()
    logs = []
    pg.on("console", lambda m: logs.append((m.type, m.text[:300])) if m.type == "error" else None)
    pg.on("pageerror", lambda e: logs.append(("pageerror", str(e)[:300])))
    pg.goto(BASE + "/?e2e=1", wait_until="networkidle", timeout=60000)
    pg.wait_for_selector("[data-testid=app-shell]", timeout=30000)
    pg.wait_for_function("window.__rsMap && window.__rsMap.loaded()", timeout=30000)
    time.sleep(2)
    pg.screenshot(path=f"{OUT}_01_baseline.png")
    check("baseline hospitals 4/4", "4/4" in pg.inner_text("[data-testid=m-hospitals]"))

    # Step 2: extreme rainfall
    pg.get_by_role("radio", name="3. Extreme rainfall").click()
    pg.wait_for_function("document.querySelector('[data-testid=sim-time]') && !document.querySelector('[data-testid=run-sim]').disabled", timeout=30000)
    time.sleep(5.5)  # timeline playback
    pg.screenshot(path=f"{OUT}_02_extreme.png")
    exposed = pg.inner_text("[data-testid=m-exposed]")
    check("extreme shows exposure", "20,426" in exposed or any(d in exposed.split("\n")[1] for d in "123456789"), exposed.replace("\n", " ")[:80])
    feats = pg.evaluate("window.__rsMap.querySourceFeatures('roads').filter(f=>f.properties.status==='closed'||f.properties.status==='restricted').length")
    check("map roads restricted/closed after sim", feats > 0, str(feats))
    hz = pg.evaluate("[...new Set(window.__rsMap.querySourceFeatures('hazards').map(f=>f.properties.cls))]")
    check("hazard zones classified on map", any(c != "normal" for c in hz), str(hz))

    # Step 3: click a road on the map, close it
    px = pg.evaluate("""() => { const m = window.__rsMap; const f = m.querySourceFeatures('roads').find(f=>f.properties.id==='R-019'); const c = f.geometry.coordinates[1]; const p = m.project(c); const r = m.getCanvas().getBoundingClientRect(); return [p.x + r.left, p.y + r.top]; }""")
    pg.mouse.click(px[0], px[1])
    pg.wait_for_selector("[data-testid=road-closure-control]", timeout=5000)
    check("road inspector opens on map click", "R-019" in pg.inner_text("aside[aria-label='Feature inspector']"))
    pg.get_by_role("button", name="Close this road").click()
    pg.wait_for_function("!document.querySelector('[data-testid=run-sim]').disabled", timeout=30000)
    pg.wait_for_timeout(5500)
    closed = pg.evaluate("window.__rsMap.querySourceFeatures('roads').find(f=>f.properties.id==='R-019').properties.status")
    check("R-019 closed on map after click", closed == "closed", closed)
    pg.screenshot(path=f"{OUT}_03_closed.png")

    # Step 4: click hospital H-01
    px = pg.evaluate("""() => { const m = window.__rsMap; const f = m.querySourceFeatures('facilities').find(f=>f.properties.id==='H-02'); const p = m.project(f.geometry.coordinates); const r = m.getCanvas().getBoundingClientRect(); return [p.x + r.left, p.y + r.top]; }""")
    pg.mouse.click(px[0], px[1])
    pg.wait_for_selector("aside[aria-label='Feature inspector']", timeout=5000)
    txt = pg.inner_text("aside[aria-label='Feature inspector']")
    check("facility inspector shows status + travel times", "operation" in txt.lower() and "baseline" in txt.lower(), txt[:70].replace("\n", " "))
    pg.screenshot(path=f"{OUT}_04_inspect.png")
    pg.get_by_role("button", name="Close inspector").click()

    # Step 5: response
    pg.get_by_role("tab", name="Response Strategies").click()
    pg.get_by_role("radio", name="C · Balanced community response").click()
    pg.get_by_test_id("deploy-response").click()
    pg.wait_for_selector("[data-testid=recovery-summary]", timeout=45000)
    pg.wait_for_selector("[data-testid=restored-callout]", timeout=10000)
    check("recovery restores access", "person-service" in pg.inner_text("[data-testid=restored-callout]"), pg.inner_text("[data-testid=restored-callout]").replace("\n", " ")[:80])
    n_resp = pg.evaluate("window.__rsMap.querySourceFeatures('response').length")
    check("response deployments drawn on map", n_resp > 0, str(n_resp))
    pg.screenshot(path=f"{OUT}_05_recovery.png")

    # Step 6: brief
    pg.get_by_role("tab", name="AI Situation Brief").click()
    pg.get_by_test_id("generate-brief").click()
    pg.wait_for_selector("[data-testid=brief-provider]", timeout=45000)
    prov = pg.inner_text("[data-testid=brief-provider]").replace("\n", " ")
    check("brief shows provider indicator", "Amazon Bedrock" in prov or "Rule-based" in prov, prov[:90])
    pg.screenshot(path=f"{OUT}_06_brief.png")

    # Step 7: export
    pg.get_by_test_id("export-menu").click()
    with pg.expect_download(timeout=30000) as dl:
        pg.get_by_role("menuitem", name="Report (JSON)").click()
    data = json.loads(open(dl.value.path(), encoding="utf-8").read())
    check("export JSON valid + labeled synthetic", data.get("synthetic_data") is True and data.get("comparison"), str(list(data)[:4]))

    # timeline controls
    pg.get_by_role("tab", name="Scenario Timeline").click()
    pg.get_by_role("button", name="Step backward").click()
    check("timeline step back changes sim time", "T+" in pg.inner_text("[data-testid=sim-time]"), pg.inner_text("[data-testid=sim-time]"))

    # reset
    pg.get_by_test_id("reset-sim").click()
    pg.wait_for_timeout(2500)
    check("reset returns to baseline", "Baseline" in pg.inner_text("[data-testid=scenario-status]"))
    check("no console errors", not logs, str(logs[:3]))
    b.close()
bad = [n for n, ok in results if not ok]
print("\nFAILED:" if bad else "\nALL PASSED", bad)
sys.exit(1 if bad else 0)



