# Demo script (about 90 seconds)

Open https://main.dxhzlkmrgksnx.amplifyapp.com (no sign-in). The banner, badges and footer state that all data is synthetic.

| Time | Action | What to say / what appears |
|---|---|---|
| 0:00 | Land on the app | "This is the fictional Sahyadri Resilience District: roads, hospitals, shelters, water points, power and pumps. Baseline: 4/4 hospitals reachable, 5.7 min average hospital travel, zero exposure." |
| 0:10 | Click preset **2. Heavy rainfall** (100 mm) - or drag rainfall and press **Run Simulation**; then try **3. Extreme rainfall** (160 mm, drainage 35 %) | The timeline auto-plays T+00 → T+60: flood-risk zones appear (dotted / hatched patterns), roads turn amber → dashed orange → dotted red. Heavy: ~4,700 people potentially exposed, 14 roads affected. Extreme: ~20,400 exposed, hospital access reduced for ~34,600, one zone with no feasible route. (Reset to **Heavy rainfall** before the next step - its closure effect is the easiest to read.) |
| 0:30 | Click the pink-glow **critical road R-019** on the map → **Close this road** (under Heavy rainfall) | The engine re-runs. "Closing it is not a recolor - routes are recomputed on the graph." Reduced water-point access goes from 0 to 13,500 people and one more facility is cut off from a zone; hospitals are unaffected (4/4) in this scenario. The bottleneck list re-ranks (R-021 becomes #1). Under Extreme rainfall the closure adds a closed road and keeps the 3/4 hospital reachability already lost to flooding. |
| 0:42 | Click hospital **H-02** on the map | Inspector: operational status, reachability, baseline vs now travel time from every zone, zones cut off (✕), cyan modeled route vs dotted-grey baseline route. |
| 0:55 | Open **Response Strategies**, choose **C · Balanced community response**, **Deploy response** | Optimizer picks ~8 actions within budget (generators, water units, temporary shelter/medical units). Green rings mark deployments. Metrics switch to **Recovery**: under Extreme rainfall + R-019 closed, reduced-access people fall from ~62,300 to ~9,800 and "Modeled access restored" appears - computed by re-running the engine. |
| 1:10 | Open **AI Situation Brief → Generate AI Situation Brief** | Provider chip shows **Amazon Bedrock** (or **Rule-based (not AI)** if Bedrock is unavailable, with the reason). Every road/facility/zone ID cited exists in the simulation output. |
| 1:20 | **Export Results → Report (JSON)**; mention CSV/HTML and importable scenario config | "Exports carry the scenario, baseline/disaster/recovery metrics, response actions, assumptions and the synthetic-data notice." |
| 1:30 | Optional: **Scenario Timeline → Back / Replay / Jump to recovery** | Step through states; sim time in the top bar follows. |

Backup path if the network is slow: pick **6. Coordinated emergency response** - it runs the compound emergency and the Balanced strategy in one click.

Numbers above were read from the deployed build on 2026-10-02. The engine is deterministic, so the same preset and inputs reproduce them exactly; the UI always shows live values.

