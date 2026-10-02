# Demo script (about 90 seconds)

Open https://main.dxhzlkmrgksnx.amplifyapp.com (no sign-in). The top bar reads **Kurla / Mithi River, Mumbai · real map · modeled data**; the map footer credits OpenStreetMap (ODbL) and SRTM.

| Time | Action | What to say / what appears |
|---|---|---|
| 0:00 | Land on the app | "This is Kurla, BMC Ward L, Mumbai - the real road network, the Mithi River, the Central Railway line, Bhabha Hospital and 28 other named facilities from OpenStreetMap. ~482,600 modeled residents in 8 neighbourhoods. Baseline: 4/4 hospitals reachable, 3.6 min average modeled hospital travel." |
| 0:10 | Click preset **2. Heavy monsoon rainfall** (100 mm / 6 h), then **3. Extreme rainfall** (160 mm, drainage 35 %) | The timeline auto-plays T+00 → T+60: Mithi-bank pockets (Kranti Nagar, Kismat Nagar bend) turn to flood-risk patterns; roads go amber → dashed orange → dotted red. Heavy: ~43,000 people in modeled flood-risk zones, 53 roads affected. Extreme: ~84,800 exposed, 117 roads affected, 6 closed, and **104,400 residents of Nehru Nagar and Tilak Nagar (east of the railway) lose timely hospital access**. |
| 0:30 | Click the pink-glow **SCLR rail over-bridge (R-059, Santa Cruz - Chembur Link Road)** → **Close this road** | The engine re-runs. "Closing it is not a recolor - routes are recomputed on the graph." Inspector shows it is a critical bottleneck for Z-06/Z-07 and hospitals H-01…H-04. After closure: Nehru Nagar and Tilak Nagar have **no route to any hospital** (2 zones with no feasible route; 29 facilities lose access from at least one zone). |
| 0:42 | Click **H-01 K.B. Bhabha Municipal General Hospital** | Inspector: operational status vs reachability, baseline-vs-now travel time from every zone, zones cut off (✕: Z-06, Z-07), modeled route vs baseline route. |
| 0:55 | **Response Strategies → B · Maximize population access → Deploy response** (30-lakh budget) | Optimizer picks 5 actions for 28.9 lakh: **clear R-059**, water tankers for Tilak Nagar and Nehru Nagar, temporary medical units in Kismat Nagar and Vidyavihar. Metrics switch to **Recovery**: reduced-access residents **104,400 → 0**, **34,800 person-service equivalents** restored - computed by re-running the engine. Switch to **C · Balanced** to show a different trade-off. |
| 1:10 | **AI Situation Brief → Generate** | Provider chip shows **Amazon Bedrock** (Nova Lite) - or **Rule-based (not AI)** with the reason if Bedrock is unavailable. Every road/facility/zone ID it cites is validated against the simulation output. |
| 1:20 | **Export Results → Report (JSON)**; mention CSV/HTML and the importable scenario file | "Exports carry the scenario, baseline/disaster/recovery metrics, response actions, assumptions and the data-provenance notice (OpenStreetMap + modeled attributes)." |
| 1:30 | Optional: **Scenario Timeline → Back / Replay / Jump** | Step through states; the sim time in the top bar follows. |

Backup path if the network is slow: preset **6. Coordinated emergency response** - compound emergency (150 mm + R-059 closed + Mithi-bank substation P-02 down: 206,400 residents with reduced access) plus a Maximize-access plan in one click → **0** residual reduced access, **51,800** person-service equivalents restored for 29.9 of 30 lakh.

Numbers above were computed by the deployed engine on 2026-10-02 (dataset `kurla-mithi-osm-1.0`, simulation `1.0.0`) and verified by `scripts/e2e_flow.py` against the public URL. The engine is deterministic, so the same inputs reproduce them exactly; the UI always shows live values.
