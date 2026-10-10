# 06 — Current Issues

_Newest at the top of each table. Tag the owner as M (Margulan) or P (Priyanshu). Times in ET._

## Blockers (stop-the-line)
| # | Opened | Owner | Issue | Next step / fallback |
|---|---|---|---|---|
| B4 | Fri 21:05 | P (or M) | **RESOLVED Fri 23:59: no capture needed. Cameras are checked on demand when a user asks (013 redesign).** ~~Camera capture (013 step 1) must be running by Sat 01:00.~~ GDOT cameras keep no recordings, and Isaias rain begins early Sat. **Key requested Fri ~21:27 ET → Pending Approval (manual review).** Plan: option C (own sidewalk photos during Isaias, J4). If the key arrives, switch to option A and start capture right away; a key by Sat noon still catches the heaviest rain. Cameras are P2, so the demo doesn't depend on them. **Alt (Fri 23:05):** Windy webcams API, 2,467 GA cameras (`07-DATA_SOURCES.md` #31). Check key/terms and whether any cover the AOI before J4's fallback. |

## Decisions needed (both humans)
| # | Opened | Decision | Recommendation | Decide by |
|---|---|---|---|---|
| J12 | Sat 02:45 | **Heads-up to Margulan: Priyanshu took over the live loop (J10).** New `noah/pipeline/live.py` (your directory) only *calls* `fetch_nwm.fetch_cycle` + `flood_times.flood_times/uncertain_q/to_geojson`, with no edits to your files. It writes live C5 + C6 entries (`event: "live"`, keeps 6). `pyproject.toml` gained `python-dotenv`. New CC7: `/assess` + `/assess/route` (spec 015). Live C5/C6 files are not committed (they change hourly). | Confirm, or say if you'd rather own `live.py`. | Sat 09:00 **Margulan's review (Sat 00:55, via Claude): accepted.** Correct reuse of 001/004. One fix: the loop kept only 6 runs and would have deleted the Saturday 8 AM run (demo evidence) and the validation inputs by ~2 PM, so `--keep N` was added (default 6; **Saturday: `--keep 48`**, BL-15). Tested: run 20261010T02Z → 313 segments flagged, 97 flooded. |
| J16 | Sat 02:30 | **Spec 016: road-level timing for the basins around metro Atlanta, then on demand.** **Approved by Margulan Sat ~02:40 (relayed by Priyanshu); A + C built and live by 02:45** (see 05 log). Priyanshu edited Margulan's pipeline modules (`fetch_hand`, `build_segments`, `live`, `config`) with an additive `--basin` switch: **Margulan, please review that diff** (commit `[spec-016]`). Open: **(B) on demand** for the rest of Georgia (needs the `building:` contract addition, CC proposal); **R22** threshold-check quality outside metro; `web/data/basins.geojson` must ship with the API (it decides coverage). Ops note: after `live --once --refresh` the API drops its C5 cache by file mtime, no restart needed; after building a *new* basin, restart the live loop (it loads inputs once). | Margulan reviews the pipeline diff Sat morning; B after the 14:00 E2E. | Sat 09:00 (review), Sat 14:00 (B) |
| J18 | Sat 03:50 | **Social Good demo: hero = Maya, a delivery driver (Margulan).** Residents covered in passing. **City story (barricades + hospital access cut-off + "fix first" list) and the City view are PINNED**: brainstormed, not to be built until Margulan says so. Candidate build for the driver journey: drivers text their remaining stops → chatbot tool reusing the dispatch engine (~1 h). | Decide whether to build the driver-stops tool. | Sat (after the 10 AM check-in) |
| J17 | Sat 02:50 | **Replit "Best Small Business App built with Replit": keep or drop? POSTPONED to Saturday (Margulan).** Claude's read: "small business app" = an app *for* small businesses, which Noah Dispatch is; the real question is whether deploying our GitHub-built app on Replit counts as "built with Replit". | Ask the Replit booth Saturday morning. Yes → keep (the deploy is needed anyway for public map links). They want real Replit development → build one small dispatch feature in Replit (~1 h, e.g. CSV upload of stops). No / no time → drop; swap to MLH Best Domain Name (~15 min). | **Sat 12:00** (after the booth) |
| J13 | Sat 00:45 | **Which event do we present:** Isaias (Saturday's live forecasts + validation) or the Helene backup? | Isaias if Saturday's runs flag meaningful metro roads *and* the evening check shows the forecast held up; else Helene. | **Sat 14:00** (re-confirm after the Sun ~03:00 validation) |
| J1 | Fri 21:05 | **Priyanshu's expanded-vision proposal** (`01-PROJECT_OVERVIEW.md`, pushed 19:51 CT): ~~US-wide~~ **Georgia-wide** coverage (scope narrowed to Georgia by Priyanshu, Fri 21:30), potholes, sewer overflow, satellite, CCTV, 3 user types, a database. | Accept the proposal's own "hackathon reality check". **Ship:** the MVP + Isaias bonus (011) + cameras (013) + low spots (012, stretch). **Roadmap slide:** Georgia-wide, business/fleet, county dashboard, satellite, sewer-overflow prediction, potholes (no open Atlanta data found). Keep D4 (Peachtree) and D7 (no DB) for the hackathon. Once agreed, move the proposal under a "Roadmap" heading in 01. | **Last** (Margulan, Oct 9): before the pitch script, Sat 20:00 |
| J2 | Fri 21:05 | Saved routes + Google/Apple Maps hand-off (BL-3), county stats view (BL-4) | BL-3 is cheap and makes a good demo moment, but only after 14:00 E2E. BL-4 goes to the roadmap. | Sat 14:00 |
| J9 | Fri 21:50 | **Superseded by J11 (Sat 01:50).** ~~**Tiger Data (MLH) suggested by Priyanshu.** It's a hosted time-series Postgres, *not* a replacement for AWS (AWS was only a download step and is no longer needed). It would be a 4th side challenge, which breaks the max-3 rule, so it reopens D2 only by **replacing Replit**. It also adds a database the plan avoids (D7). | Don't add it. Keep Replit (the dispatch board + hosting fit better). Tiger Data goes on the roadmap (hourly forecasts per road segment are a natural time-series store). | Not critical now (Margulan). Decide with J1 at the end. Anything later than Sat 12:00 effectively means no. |
| J6 | Fri 21:30 | **Hosting:** Replit hosts API + map + dispatch board (BL-9, Priyanshu) instead of laptop + tunnel + GitHub Pages (changes D8). Where the iMessage relay runs depends on Photon: Spectrum Cloud → Replit is fine; `imessage-kit` → must stay on a Mac. | **Agreed (Margulan, Oct 9)**, pending the Replit booth answers below. Keep laptop + `cloudflared` as the fallback. | Booth answers tonight |
| J7 | Fri 21:30 | **Live demo setup:** a fixed demo "home" address in the AOI (not anyone's real home), demo origin/destination pairs, which phone texts Noah on stage, which Apple ID/line Noah uses. | Pick 2 addresses along Peachtree Creek that Helene flooded (from 005 street truth) + 1 dry control. Use Priyanshu's or Margulan's phone as the sender. | Sat 14:00 (E2E test uses them) |
| J8 | Fri 21:30 | **Roles for judging:** who gives the 3-min pitch, who drives the demo (phone + map), who records/edits the video. | Margulan pitches the problem + hydrology; Priyanshu drives the live demo; record together at Sun 02:00. | Sat 20:00 |

## Open risks and unknowns
| # | Opened | Owner | Issue | Plan |
|---|---|---|---|---|
| R20 | Fri 23:50 | Both | **Runtime memory ~1.8 GB** with the metro graph (dispatch alone: graph + edge GeoDataFrame + STRtree + flood dicts). A 2 GB Replit VM is tight once routing's FloodIndex and the agent are loaded too. | Use the 1 vCPU / 4 GB VM (~$3.50 for the weekend, inside Core credits), or slim `graph_state()` (keep only arrays + tree, drop the GeoDataFrame). Decide at the Replit deploy (I10). |
| R19 | Fri 23:50 | M | **Big regulated river:** synthetic rating curves on the Chattahoochee mainstem (Buford Dam releases) put some riverside roads barely above normal flow (Riverwalk Dr, Roswell, flagged at hour 0). | `BASELINE_GUARD_FACTOR = 1.5`: rows wet within 1.5× low flow are dropped as artifacts (54 segments). Mention in Q&A: mainstem Chattahoochee is dam-controlled; Noah targets creeks. |
| R18 | Fri 22:30 | Both | **Statewide compute.** HAND is ~250 MB per HUC8 × 53 Georgia HUC8s (~13 GB if all). A statewide OSM drive graph may not fit in memory with OSMnx/NetworkX. | Roll out HUC8s in order (01 §Coverage) and process what fits by the freeze. Statewide routing fallback: Valhalla `exclude_polygons` with hazard polygons (07 §4). Log which HUC8s are done in PROGRESS. |
| R17 | Fri 22:30 | M | **Long simplified edges:** OSMnx merges road stretches between intersections, so some flagged segments are long (up to ~1 km) and the whole edge shows red although only part floods. A freeway (Horace E Tate Fwy) is flagged at +11 h, probably a culvert crossing not tagged as a bridge. | Spot-check the top 10 flagged segments on satellite imagery (005 part C). Upgrade: split edges at NOAA's per-catchment road pieces (`osmid_catchid`). Raise `MIN_ROAD_HAND_M` per artifact if needed. Routing stays conservative either way. |
| R16 | Fri 22:10 | M | **Forecast timing bias:** the 14Z–21Z Helene runs forecast flood flow 3–11 h late and 35–65% low. Roads flagged from those runs would flag late or not at all. | Demo from the most skillful early run (proposal: `DEMO_CYCLE = 20240926T12Z`, needs Margulan's OK since spec 005's rule said keep 18Z). Q&A: state it plainly; the uncertain band + "re-check before you leave" wording are the mitigation; it's NWM skill, not Noah's logic. |
| R14 | Fri 21:05 | Both | **Potholes: UPDATED Fri 23:05.** SeeClickFix API has flooding + pothole reports (`07-DATA_SOURCES.md` #54). | BL-2: a "recent reports" layer is possible; still roadmap unless ahead after E2E. |
| R13 | Fri 21:05 | M | **Storm drains / sewers: UPDATED Fri 23:05.** Priyanshu verified an open **Atlanta storm sewer GIS** (40,698 inlets, pipes, culverts) and wastewater GIS (`docs/07-DATA_SOURCES.md` #50–51). My earlier "no open data" was wrong. | BL-1 now has real data. Cheapest uses: (a) the **culvert layer to fix crossing artifacts (R3/R17)**; (b) inlets as a low-spot/ponding hint (012). Still not a sewer-flow forecast. Decide after E2E. |
| R12 | Fri 21:05 | P | **Dropped with 511GA (Fri 23:00).** ~~**511GA terms** for storing/redisplaying snapshots unverified. Cameras cover GDOT routes only. API limit 10 calls / 60 s. | Read the terms at key signup and record them in spec 013. Frames stay local (gitignored), attributed, deleted after the event. |
| R11 | Fri 21:05 | M | **Isaias may not flood Peachtree Creek.** The 22Z Oct 9 forecast peaks at ~1,061 cfs, below action stage. Most rain falls after that forecast's window. | Spec 011 decision at Sat 14:00. Helene remains the main demo either way. |
| R1 | Fri 20:30 | M | FIM layout: **resolved for v4.9** (see spec 002 "Discovered layout"). Still verify `hydrotable.parquet` columns and whether it covers branch 0. | Spec 002 step 3. |
| R3 | Fri 20:30 | M | Culvert crossings: NOAA thresholds can sit at channel level where a road crosses a creek on a culvert. | Rows with `threshold_hand < MIN_ROAD_HAND_M` (0.3 m) dropped + baseline guard (CC3). Known false-negative risk at real low-water crossings; see R17 for false positives. |
| R4 | Fri 20:30 | M | HAND + synthetic rating curves are weak on small urban creeks. `UNCERTAIN_BAND_M = 0.5` is a heuristic, not calibrated. | State it in Q&A. The uncertain band and "treat as impassable" wording are the mitigation. |
| R5 | Fri 20:30 | M | Need 2–3 streets with dated public photos or news showing flooding on Sep 27, 2024 in the Peachtree Creek HUC10 (e.g., Buckhead along Peachtree Creek). | Spec 005. Use only sources we can cite. No invented examples. |
| R6 | Fri 20:30 | P | **Resolved Sat 01:45:** the AI provider is Azure OpenAI, deployment `gpt-4.1-mini` (eastus2), in `.env`. ~~Current Gemini model ID unknown.~~ | — |
| R7 | Fri 20:30 | P | Nominatim usage policy: 1 req/s, needs a real User-Agent, no bulk use. | Cache every lookup, restrict to the Georgia viewbox, set the User-Agent to `noah-hacklanta/0.1 (contact: team email)`. |
| R8 | Fri 20:30 | P | Map on GitHub Pages (HTTPS) calling the laptop API needs an HTTPS tunnel and CORS. | Use a `cloudflared` HTTPS URL; FastAPI CORSMiddleware allowing the Pages origin only. |
| R9 | Fri 20:30 | Both | Out of scope by design: storm-drain and flash street flooding (012 is info only), recession timing. | Say it in the pitch "limits" beat. Never imply otherwise. |
| R10 | Fri 20:30 | Both | Q&A prep: "isn't this just NOAA FIM?"; "how accurate?"; the name collides with Noah-MP (the land-surface model inside NWM) and Project NOAH (Philippines). | Margulan owns these answers. Name collision one-liner: "named for the flood story; unrelated to Noah-MP, which ironically sits inside the model we use." |

### J6: questions for the Replit booth (tonight)
1. **Eligibility:** what counts as "built with Replit"? Is importing our GitHub repo and deploying on Replit enough, or do judges expect Replit Agent / workspace use? Anything specific to show in the demo or Devpost?
2. **Credits:** any hackathon credits, Core trial or promo code this weekend? How much?
3. **Deploy type:** an always-on Python FastAPI that loads ~100–300 MB of data into memory at startup. Reserved VM or Autoscale? How slow is an Autoscale cold start after 15 min idle?
4. **Limits:** RAM/disk on the smallest VM; max file/repo size (graph file maybe 50–150 MB); data files in the deployment or Object Storage?
5. **Packages:** do `osmnx`/`shapely`/`networkx` install cleanly? Is `uv` supported?
6. **Long-lived connections:** can a Reserved VM keep a persistent outbound gRPC stream (Photon Spectrum relay) running next to the web server?
7. **Team access:** can both of us edit/deploy the same project on free/Core, or does that need Teams?
8. **After the event:** does the deployed URL need to stay up for Devpost judging, and for how long?

### J6: cost estimate if not free (Replit pricing per third-party guides, Aug–Sep 2026; confirm on replit.com)
| Scenario | Out of pocket |
|---|---|
| Booth gives credits / promo | $0 |
| Core for 1 month ($25, includes $25 credits) + Reserved VM shared 0.5 vCPU / 2 GB ($15/mo, ~$1.50 for 3 days, paid from credits) | **$25** |
| Same, but 1 vCPU / 4 GB VM if 2 GB is too small ($35/mo, ~$3.50 for 3 days, from credits) | **$25** |
| Keep the demo link up for a month after judging (VM from credits) | still **$25**, then cancel |
| Autoscale instead ($2 base + usage) | cheaper, but cold starts after 15 min idle; risky during judging |
| Using Replit Agent heavily to build (burns credits) | $10–50+ overage. **Avoid:** build with Claude Code locally, push to GitHub, deploy on Replit. |

## Before we start building (checklist, both)
- [ ] Each person approves their own specs (`Status: Draft → Approved`): M 001–005, 011 (012 if kept) · P 006–010, 013.
- [ ] Priyanshu confirms or objects to CC1 (the additive contracts).
- [ ] J6: ask the Replit booth the questions above (Priyanshu). J5 by Sat 12:00. J1 last.
- [ ] Accounts: ~~Gemini~~ Azure OpenAI ✅ (P), **Tiger Cloud (P, J11)**, Photon (P), Replit (P). ~~511GA~~ dropped (Priyanshu, Fri 23:00). Windy, Census, Mapillary, Synoptic, TomTom keys done (P). No AWS needed.
- [ ] Specs 014 (BL-8) and 015 (BL-9) written + approved before anyone codes them.

## Integration checklist (Margulan ↔ Priyanshu): run through this together before the E2E test
Every point where the two lanes must connect. Tick each item and note the commit. Add new items as they appear.

| # | Item | Owner | Status |
|---|---|---|---|
| I1 | **Graph file:** Priyanshu's routing loads `data/interim/graph.graphml` if present, else gunzips `fixtures/graph.graphml.gz` (36 MB unzipped). `data/` is gitignored, so Replit/teammates use the fixture. | P (M ships the fixture ✅) | ✅ 006 uses `dispatch.load_graph()` |
| I2 | **Flood files:** `web/data/flood_<cycle>.geojson` (C5, lead hours **0–18**, CC2) + `cycles.json` (C6, with `events`, CC1). Real Helene data is committed; demo cycle `20240926T12Z`. Fixtures are no longer needed for flood data. | P consumes | ✅ 006 reads C5/C6, hours 0–18 |
| I3 | **Mount dispatch:** in `noah/api/app.py` add `from noah.api import dispatch` + `app.include_router(dispatch.router)` (CC5). | P | ✅ done in 006 |
| I4 | **One graph in memory:** `dispatch.py` and `routing.py` must share one loaded graph + flood dict (36 MB graphml ≈ several hundred MB in RAM; two copies may not fit a 2 GB Replit VM). Agree on one loader, e.g. `routing.load_state()` that `dispatch` imports, or the reverse. | Both | ✅ routing.py imports dispatch.graph_state() / flood_state() (one copy) |
| I5 | **Same blocking rule:** `t_uncertain <= depart_h + ROUTE_BUFFER_H` in both `/route` and `/dispatch`. Reuse one helper (`dispatch.blocked_weight()` or Priyanshu's equivalent). | Both | ✅ /route uses dispatch.blocked_weight() |
| I6 | **Active cycle:** both honor env `NOAH_CYCLE`, else C6 `demo_cycle`. | Both | ✅ both use dispatch.active_cycle() |
| I7 | **Static pages:** `web/index.html` (009, P) and `web/dispatch.html` (014, M) are served from the same origin (FastAPI `StaticFiles` on Replit) or GitHub Pages with `?api=`. Link the two pages to each other. | Both | ✅ `app.py` serves `web/` via StaticFiles; link index.html ↔ dispatch.html still to do |
| I8 | **Dependencies:** M added `fastapi`, `uvicorn` (and the pipeline deps) to `pyproject.toml`/`uv.lock`. P: `uv sync` after pulling. If you add deps, commit the lock file. | Both | ☐ |
| I9 | **Contract confirmations:** P to confirm CC1, CC2, CC5; **M to confirm CC6** (table below). | P + M | ☐ |
| I10 | **Replit (J6/BL-9):** run command + data loading (I1) + secrets; Margulan does the account/import/billing steps in the browser (Claude can't). | M (browser), P (config) | ☐ |
| I12 | **Same visual language on both maps:** creeks in blue, plain-language caption over the time slider ("Roads forecast underwater by …"), numbered pins matching the list, routes drawn with a ✕ where they get cut. Built first in `dispatch.html` (Fri 23:30); reuse in `index.html` (009). | P (009) | ☐ |
| I13 | **C7 for HUC8 coverage:** `routing.coverage()` reads features with a `huc8` property from `web/data/aoi.geojson`. Margulan's HUC8 expansion writes them (CC6). | M | ✅ Fri 23:50: 4 HUC10 features, each with `huc8: "03130001"` and `huc10` |
| I14 | **Relay ↔ agent:** Margulan's relay (`bot/`, 008) calls Priyanshu's `POST /chat` `{"sender", "text", "image_b64": null}` → `{"reply"}` (C9). Until 007 exists, the relay runs in echo mode. Agree the `API_BASE` (laptop tunnel or Replit URL) before the 14:00 E2E. | M (relay) + P (agent) | ✅ Sat 02:08: `/chat` exists (agent.py); relay auto mode now relays |
| I15 | **`app.py` touched by Margulan:** `from noah.api import agent`, `app.include_router(agent.router)`, `agent.warm()` in `warm()`. Priyanshu: keep these when editing app.py. | P (ack) | ☐ |
| I16 | **Spec 017 route watch (Margulan):** `camera_watch` watch list now = flagged-road/creek cameras **plus the route cameras** in `web/data/watch_routes.json`; its check rows gain an `evidence` field. New files Priyanshu can draw on the map if useful: `web/data/watch_routes.json` (11 routes: label, line, cameras) and `web/data/route_watch.json` (per live run, per route: cut-from time + street). The relay answers "alerts on/off" itself (never reaches `/chat`). | P (ack) | ☐ |
| I11 | **Wording:** agent replies, map labels and dispatch badges all use the §5 vocabulary; run the banned-word check over everything user-facing. | Both | ☐ |

## Contract change proposals
| # | Opened | Proposer | Change | Agreed by both? |
|---|---|---|---|---|
| CC8 | Sat 03:10 | P | Additive, C9 `/route`: optional query `corridor_m` (500–5000; default unchanged = CC6's 1 km) and response fields `usual_geometry` (fastest way when the route detours, else null) + `corridor_m`. Map uses 3 km. No existing field changes. | Margulan to ack |
| CC5 | Fri 22:58 | M | Additive: C13 `POST /dispatch` + `GET /barricades` (spec 014) as a FastAPI `router` in `noah/api/dispatch.py`, mounted by one line in Priyanshu's `app.py`; §5 rows for dispatch states. No existing contract changed. | M ☑ · P ☐ |
| CC2 | Fri 22:00 | M | C1/C5 lead hours extend from 1–18 to **0–18**: hour 0 = NWM `analysis_assim` (estimated now). Consumers: the slider already starts at 0 (009); routing/status treat 0 like any hour. No renames. | M ☑ · P ☐ |
| CC1 | Fri 21:05 | M | Additive: C6 `events` + `cycles[].event`; C9 `NOAH_CYCLE`, `beyond_forecast_window` state, `/cameras` endpoints; new C11 (low spots), C12 (camera assessments); §5 rows for low spot, camera water, beyond window. Already written into `02-ARCHITECTURE.md`. Nothing existing was renamed or removed. | M ☑ · P ☐ (Priyanshu: confirm or object before building 006/009) |

## Parking lot (good ideas, not now)
- (spec 018) One `/assess/route` per trip corridor instead of one per leg; the page currently fans out N legs at once and merges.
- (spec 018) Serve `camera_watch` / `route_watch` verdicts to the camera adapter so a cold search never shows "AI check still running".
- Live mode on today's NWM cycle beyond the Isaias bonus (the code path is the same; set `NOAH_CYCLE` to latest).
- Recession (`t_clear`) so roads reopen on the map.
- Max across FIM branches. (AOI expansion is no longer parked: coverage is all of Georgia, CC6.)
- Push alerts: text subscribers when their saved route gets a new `flooded` segment.
- Low spots (C11) feeding the agent/routing as `uncertain` during heavy forecast rain (needs a rainfall forecast, e.g., NWM forcing or MRMS).
- Pothole detection from camera frames (needs an accuracy test, not a claim). User photos are out of scope.
- Everything in BL-6 (Priyanshu's roadmap items).
- **Statewide routing + road timing** (Sat 02:30, Priyanshu): outside HUC8 03130001, `/route` and `/past` return `no_road_forecast` (no graph, no HAND). The map now still runs `/assess` + `/assess/route` there (33 live sources, cameras, risk score, Google/Apple hand-off without Noah waypoints), so every Georgia address gets an answer. Road-by-road timing and detours statewide need more HUC8s processed (R18) and a statewide graph or Valhalla fallback.
- **More per-request sources** (Sat 02:30): the engine queries 33 live adapters per check (`noah/sources/`); the other sources in `docs/07` are pipeline inputs. If a bigger "sources checked" number matters for the pitch, wire more of 07's feeds as adapters; never inflate the count.
- **Risk score weights** (`web/index.html` `riskScore()`): a transparent weighted sum over the live signals (road forecast, NWS alerts, NWM rapid-onset, rain, WPC ERO, gauges, incidents, cameras, AI level, area history), capped at 100, bands Low/Elevated/High/Severe. Weights are hand-set; it is labelled "scored by Noah's rules", never as a trained model. Calibrating against Helene/Isaias outcomes is a roadmap item.

## Resolved
| # | Resolved | How |
|---|---|---|
| J15 | Sat ~02:00 | **007 chat agent moved to Margulan** (Margulan's call; Priyanshu please ack). Built on Priyanshu's routing + engine; `app.py` gains `include_router(agent.router)` + `agent.warm()` (two lines in Priyanshu's file, I15). |
| B3 | Sat 01:53 | Photon Spectrum Cloud project + iMessage line work: real echo round trip from Margulan's iPhone (spec 008 Phase 0). |
| J14 | Sat 01:20 | **008 (iMessage relay + Photon) moved to Margulan** (Margulan's call; Priyanshu: please ack in PROGRESS). Priyanshu keeps 007 (agent behind `POST /chat`). Contract between them = C9 `/chat` (see I14). |
| J11 | Sat 01:05 | **Accepted with a condition (Margulan: "sounds good" to Claude's recommendation):** side challenges = Tiger Data + Photon + Replit; AI on Azure OpenAI (Gemini dropped). **Condition:** Tiger Data stays small (store live forecast runs per segment + 1 dashboard query) and starts **after** the 007 agent + 008 iMessage relay work end to end (Sat 14:00 E2E). |
| J10 | Sat 00:45 | **Agreed with two conditions (Margulan):** (1) the demo needs proof, so Isaias forecasts are validated against USGS gauges + reported closures Sat night / Sun early; (2) Helene is kept as backup (Devpost, Q&A, fallback demo), not in the main UI/pitch. Product = live by default (spec 015 live loop, Margulan). Spec 011 retired into 015 + the Sat-night validation. Demo-event final call Sat 14:00 (J13). First data point: the 9 PM Fri run already forecasts 62 metro segments flooded / 205 uncertain by 5–7 AM Sat. |
| CC6 | Fri 23:25 | **Margulan accepted Claude's narrowed version:** (1) road-level timing = all of HUC8 03130001 (Margulan builds it, spec 003/004 rerun), not all of Georgia; statewide = official warnings + `no_road_forecast`, Priyanshu's, after E2E; all-Georgia = roadmap; (2) 5 km radius + 1 km route corridor ✅; (3) 511GA dropped, cameras = Windy ✅ (BL-7/BL-10 closed); (4) no user photos ✅. |
| J5 | Fri 22:58 | Option A: Margulan builds the dispatch board + barricade list now (spec 014), new files only, mounted by Priyanshu later (I3). 012 low spots stays P3 / roadmap. |
| CC4 | Fri 22:38 | Residential streets covered: Noah computes thresholds from FIM HAND for roads NOAA's list omits (motorway–tertiary only), across branch 0 + 4 level paths; `source` column added to C3. Result: all reported Buckhead streets flagged (Woodward Way, Hanover W, Bohler, Peachtree Battle, Sagamore). `--noaa-only` fallback kept. C5 unchanged, so Priyanshu is not affected. |
| R2 | Fri 22:38 | Level-path branches used for residential thresholds (min across branches = FIM max-extent composite). |
| R15 / CC3 | Fri 22:15 | Margulan approved using NOAA FIM 4.9 per-road thresholds (`osm_roads_fimpact.csv`) instead of our own HAND sampling. Implemented in 003/004; C3 is now `seg_thresholds.parquet`; C5 unchanged. Pitch: NOAA computes where/at what flow; Noah adds when, routing and text delivery. |
| D5 | Fri 22:15 | Demo cycle = `20240926T12Z` (8 AM EDT), final. |
| B1 | Fri 22:08 | **GO.** NWM short-range forecast Peachtree Creek above minor flood flow in every cycle from 20240926T12Z; first warning 13.2 h before the observed crossing. Mid-day runs were late and low (see PROGRESS 22:08). |
| B2 | Fri 21:45 | No AWS needed. The same OWP HAND-FIM data (v4.9.9.0) is in the public CIROH bucket `ciroh-owp-hand-fim` (anonymous). NOAA's requester-pays bucket is now only the fallback in spec 002. Disclose the data source (FIMserv / CIROH) in the README. |
| J4 | Fri 21:45 | **Superseded Fri 23:00 (Priyanshu): 511GA dropped; cameras = Windy Webcams (spec 013), Margulan to confirm.** ~~Camera fallback if no 511GA key by 00:00 = **option C** (our own sidewalk photos during Isaias). Option B (hand-picked public image URLs) only if both explicitly agree later. Never call `/list/getdata/`. (Margulan) |
| J3 | Fri 21:30 | Mercedes CV stays dropped. **FINAL:** main track Social Good; side challenges Photon + Gemini + Replit (Margulan, D2). |
