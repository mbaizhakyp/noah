# 05 — Progress Tracker

_Last updated: Fri Oct 9, 2026, 9:30 PM ET (challenges final: Photon + Gemini + Replit; B2B + Replit + key-check backlog)_

## Clock (ET)
| When | Milestone | Status |
|---|---|---|
| Fri 20:30 | Hacking starts | ☑ |
| Fri ~22:00 | Accounts ready (no AWS needed: HAND comes from the public CIROH bucket): Gemini key, Photon line, Replit (ask the booth about deploy plan/credits), **511GA key check (BL-7)** | ☐ |
| **Sat 00:00** | **GO/NO-GO:** NWM forecast at gauge reach vs observed (spec 001 + quick 005 plot). Spectrum echo bot works on a real phone (spec 008). | ☑ forecast **GO** (22:08, lead 13.2 h) · echo bot: Priyanshu |
| **Sat 01:00** | **Camera capture running** (013 step 1). Cameras keep no recordings, so Isaias rain starting early Sat is lost if this slips. | ☐ |
| Sat 03:00 | `graph.graphml` + `aoi.geojson` pushed (003 step 1). Map shows fixture flood roads. | ☑ graph pushed Fri 22:30 as `fixtures/graph.graphml.gz` |
| Sat 09:00 | `seg_thresholds.parquet` + `rating.parquet` exist | ☑ Fri 22:23 |
| Sat 12:00 | First real `flood_<cycle>.geojson` on the map | ☑ files in `web/data/` Fri 22:24 (map is 009) |
| **Sat 14:00** | **E2E:** text to iMessage → agent → real flood data → reply + detour + map link. **Isaias go/no-go (011).** | ☐ |
| Sat 20:00 | Helene lead-time number + 2–3 street confirmations. Camera assessments on the map (if 013 is on track). | ☐ |
| **Sun 00:00** | **FEATURE FREEZE.** README, Devpost draft, pitch script. | ☐ |
| Sun 02:00–04:00 | Isaias validation, if GO (011). Demo video recorded by 04:00. | ☐ |
| **Sun 07:00** | **Devpost submitted** (internal deadline) | ☐ |
| Sun 09:00 | Hard deadline. Then pitch rehearsal and judging. | — |

## Owners
| Area | Owner | Directories |
|---|---|---|
| Data pipeline, validation, Isaias run, low spots | Margulan | `noah/pipeline/`, `web/data/` |
| API, routing, agent, relay, map, photo + camera vision | Priyanshu | `noah/api/`, `bot/`, `web/index.html`, `fixtures/` |
| Pitch, Devpost, video | Both (Margulan leads the hydrology story) | `README.md`, `docs/` |

Lanes are set up so neither person waits on the other. Priyanshu builds against `fixtures/` until real data lands. Margulan's outputs are files with frozen contracts. The only cross-lane hand-offs are files: `graph.graphml` (Sat 03:00), `flood_*.geojson` (Sat 12:00), `lowspots.geojson` (if 012 ships).

## Priorities
- **P0** = the demo core. Without it there's no submission.
- **P1** = what makes it convincing, or can't be done later.
- **P2** = strong extras.
- **P3** = only if ahead of schedule.
Never start a lower priority while a higher one in your lane is unfinished, **except** 013 step 1, which is time-critical.

## Specs
| Spec | Title | Owner | Pri | Time box | Status |
|---|---|---|---|---|---|
| 001 | NWM forecast fetch + subset | Margulan | P0 | 2 h | **Done** (22:08; Helene, 26 cycles × 19 files, 1,895 reaches) |
| 002 | FIM HAND + rating curves fetch | Margulan | P0 | 1 h | **Done** (21:57) |
| 003 | AOI, road graph, NOAA per-road thresholds (CC3) | Margulan | P0 | 1.5 h | **Done** (22:23) |
| 004 | Flood times per segment | Margulan | P0 | 1.5 h | **Done** (22:24; 26 Helene cycles) |
| 005 | Validation: lead time + street truth | Margulan | P1 | 3 h | **Part A done: GO** (22:08). Part C (streets) after 004 |
| 011 | Hurricane Isaias live run (bonus demo) | Margulan | P1 | 2 h | Draft |
| 012 | Street low spots (storm-drain stand-in) | Margulan | P3 | 2 h | Draft |
| 006 | Routing + HTTP API | Priyanshu | P0 | 3 h | Draft |
| 007 | Gemini agent + safety filter | Priyanshu | P0 | 3 h | Draft |
| 008 | iMessage relay (Photon Spectrum) | Priyanshu | P0 | 2 h | Draft |
| 009 | Web map with time slider | Priyanshu | P0 | 3 h | Draft |
| 013 | Traffic cameras: step 1 capture | Priyanshu | **P1 (by 01:00)** | 45 min | Draft |
| 010 | Photo check / `classify()` | Priyanshu | P2 | 2 h | Draft |
| 013 | Traffic cameras: steps 2–3 assess + show | Priyanshu | P2 | 2.5 h | Draft |

Status flow: `Draft → Approved (human) → In progress → Done (acceptance criteria shown passing)`.

## Backlog (not yet specs)
Each research item has a 30-min time box and produces a written finding in `06-CURRENT_ISSUES.md`: source URL, license, coverage, freshness, and a verdict of spec / parking lot. **No spec gets written for a layer until a real, citable source is confirmed** (Priyanshu's "right data first" rule in `01-PROJECT_OVERVIEW.md`).

| ID | Item | Owner | Pri | When | Notes |
|---|---|---|---|---|---|
| BL-1 | **Research: storm-drain / sewer data for Atlanta.** DWM GIS, Atlanta open-data hub (ArcGIS), EPA combined-sewer data, Georgia EPD spill notifications. | Margulan | P3 | Sat afternoon, only if 005 is on track | Quick search found no open inlet layer; the records route takes ~3 business days. 012 (low spots) is the stand-in we can actually build. |
| BL-2 | **Research: pothole data for Atlanta.** Atlanta open-data hub for ATL311 requests; ATLDOT. | Priyanshu | P3 | Sat evening, only if ahead | No open ATL311 dataset found yet (records requests only). A pothole layer from another city wouldn't match the Atlanta flood demo. Default: roadmap slide. |
| BL-7 | ✅ **Requested Fri ~21:27 ET by Margulan → "Pending Approval"** (confirmation email: "we will process your request shortly"). Check email Sat morning; a key by Sat noon still catches the heaviest rain (Sat afternoon–night). Until then option C (own photos) is the plan. · **511GA developer key check.** Create a 511ga.org account → request a key at `511ga.org/developers/doc` → note whether it's issued instantly or goes to review, and copy the terms shown at signup into spec 013 "Discovered". Put the key in `.env` as `GA511_API_KEY`. | **Priyanshu (or Margulan, whoever is free first)** | **P1** | **Tonight, by 23:00** | Instant key → 013 option A. No key by 00:00 → decision J4 picks option B or C. 10 min of work. |
| BL-10 | **Check email for the 511GA key approval and act on it.** Approved → put `GA511_API_KEY` in `.env`, tell Priyanshu, start 013 step 1 capture right away (option A). Still pending at noon → stay on option C (own photos) for the rest of Isaias and say so in PROGRESS. | Margulan (the email is Margulan's) | P1 | Sat morning, **decide by Sat 12:00** | Approval email comes from notifications@511ga.org. Record any terms it contains in spec 013 "Discovered". |
| BL-8 | **B2B: small-business dispatch board + agency barricade list** (our Replit Small Business entry). Dispatch: paste depot + stops (+ time windows) → per stop "no forecast flooding on the route if you leave before ~X (not a safety guarantee)" / "hold: route cut X–Y" / "outside coverage", plus a map. One route search per forecast hour from the depot covers all stops. Barricade list: C5 segments sorted by `t_flood`, with street names, CSV export. No accounts, no DB. | Margulan (proposed, J5) | P1 | Sat 14:00–19:00 | **Spec 014 to write + approve** before coding. New files only: `noah/api/dispatch.py`, `web/dispatch.html`, so nothing overlaps Priyanshu's files. Folds in BL-4 (county stats). |
| BL-9 | **Replit deployment** of the runtime (FastAPI + map + dispatch board) for the Replit challenge and an always-on demo link | Priyanshu (proposed, J6) | P1 | Booth question tonight; deploy Sat 15:00–17:00 | **Spec 015 to write + approve.** Runtime-only deps (fastapi, uvicorn, networkx, osmnx, shapely, google-genai). Pipeline stays on the laptop. Fallback: laptop + `cloudflared` (D8). |
| BL-3 | Saved routes + "open in Google/Apple Maps" link from the route view | Priyanshu | P3 | Only if ahead | From Priyanshu's proposal. Cheap on top of 006/009. **Needs joint OK** (J2). |
| BL-6 | US-wide coverage, fleet/business view, satellite flood detection, sewer overflow prediction | — | Roadmap | — | From Priyanshu's proposal. Pitch as roadmap unless real data turns out to be quick to get. |

## Plan by person
### Margulan
- **Fri 20:30–00:00:** approve 001/002/003/005 → **001** (Helene cycles) → quick gauge plot (005 part A) → **GO/NO-GO**. Start 002's downloads (~250 MB, public bucket) in the background.
- **Sat 00:00–04:00:** **003** step 1 (AOI + graph, push early for Priyanshu) → 002 finish → 003 HAND sampling.
- **Sat 04:00–08:00:** sleep.
- **Sat 08:00–12:00:** **004** → real `web/data/` pushed.
- **Sat 12:00–14:00:** E2E support + **011** gauge-only Isaias run → **Isaias go/no-go at 14:00**.
- **Sat 14:00–20:00:** **005** full (Helene lead time + streets) → **BL-8 dispatch board + barricade list** (if J5 agreed) → 011 full-AOI if GO. 012 / BL-1 only if ahead (proposed: 012 → roadmap, J5).
- **Sat 20:00–Sun 00:00:** README hydrology section, pitch script.
- **Sun 00:00–05:00:** 011 Isaias validation if GO, final re-runs, video.

### Priyanshu
- **Fri 20:30–00:00:** accounts (Gemini, Photon at their booth, Replit booth: deploy plan/credits) → **BL-7 key check** → approve 006–010, 013 → **008** echo bot on a real phone → **013 step 1 capture running by 01:00** if J4 allows (`caffeinate`, laptop plugged in) → **fixtures/** per contracts C4–C6.
- **Sat 00:00–05:00:** **009** map on fixtures → **006** routing + API (switch to the real `graph.graphml` when it's pushed). Check the capture is still running before sleeping.
- **Sat 05:00–09:00:** sleep (capture keeps running).
- **Sat 09:00–14:00:** **007** agent wired to 006 + 008 → **E2E at 14:00**.
- **Sat 14:00–20:00:** **BL-9 Replit deploy** (if J6 agreed) → **010** `classify()` → **013** steps 2–3 (assess frames or our own storm photos, `/cameras`, map markers) → 009 scenario switch + optional layers → BL-2/BL-3 only if ahead.
- **Sat 20:00–Sun 00:00:** README run instructions, test the map on a phone from iMessage.
- **Sun 00:00–05:00:** video capture, tunnel test, submit prep.

## Log
_Append-only. Format: `HH:MM Name — what was done — how verified (command)`._

### Margulan
- 20:18 — Pulled USGS IV for 02336300, Sep 26–28, 2024. Minor (17 ft) up at 2024-09-26 21:15 EDT; major (20 ft) up at 23:45 EDT; peak 23.75 ft at 2024-09-27 08:15 EDT; peak Q 20,000 cfs at 05:45 EDT. — `nwis.waterservices.usgs.gov/nwis/iv/?sites=02336300&parameterCd=00065,00060&startDT=2024-09-26T00:00-04:00&endDT=2024-09-28T00:00-04:00&format=json`
- 20:18 — Verified the NWM archive exists: `gs://national-water-model/nwm.20240927/short_range/...channel_rt.f001.conus.nc` (12.7 MB, anonymous HTTPS). AWS `noaa-nwm-pds` has no 2024 data.
- 20:18 — Verified AOI and IDs: HUC10 0313000112 "Peachtree Creek" (338.49 km²), HUC8 03130001; NLDI comid for the gauge = 2047989; NWPS AANG1 thresholds (action 13 / minor 17 / moderate 18 / major 20 ft; 3630 / 5700 / 7000 / 7800 cfs).
- 20:45 — Live NWM latency measured: cycle t22z (Oct 9) f018 landed in GCS at 23:48Z (~1 h 45 min). — GCS JSON API listing, prefix `nwm.20261009/short_range/nwm.t22z...f018`
- 20:45 — Isaias check: 20261009T22Z forecast at 2047989 = 1.1 / 1.6 / 4.1 / 17.5 / 30.0 / 25.5 m³/s at f003/6/9/12/15/18 (peak ≈ 1,061 cfs, below action 3,630). Observed 2026-10-09 20:00 EDT: 2.08 ft, 18 cfs. Reading NWM needed `h5py` alongside `h5netcdf`. — `uv run --with xarray --with h5netcdf --with h5py`, `xr.open_dataset(..., engine="h5netcdf")["streamflow"].sel(feature_id=2047989)`
- 21:45 — HAND data found in a public bucket, no AWS account needed: `s3://ciroh-owp-hand-fim/hand_fim_4_9_9_0/03130001/` (OWP HAND-FIM v4.9.9.0, 461 files, 0.79 GB). Branch 0: HAND 106 MB, catchments 3.7 MB, hydroTable 110.6 MB; HUC-level `hydrotable.parquet` 3.3 MB. — anonymous S3 ListObjectsV2 over HTTPS
- 22:50 — **Spec 005 part C (street truth), honest scorecard for the 8 AM demo run:** ✅ **Windsor Pkwy at Nancy Creek**: forecast flooded from **10 PM Thu** (uncertain from 8 PM); actually closed ~10:15 PM Thu (Appen Media, 11Alive). ❌ **Woodward Way at Bobby Jones** (flooded per Rough Draft Atlanta): not flagged; NOAA ties it to a small tributary reach (2044831) whose forecast stayed low. ❌ **Sagamore Dr / Bohler Rd / Hanover W** (reported closed; source to verify): **not in NOAA's road list at all**, which covers only motorway–tertiary, **no residential streets** (70% of our edges). Northside Dr NW: flagged from midnight, but no verified source showing the road flooded ("water approaching the Northside Drive bridge" only), so left out. Streets live in `noah/pipeline/street_truth.json` → `validation.json["streets"]`. Proposal CC4 (residential thresholds) logged. — `uv run python -m noah.pipeline.validate --event helene`
- 22:24 — **Spec 004 done.** 26 C5 files + `cycles.json` in `web/data/` (2.3 MB total). **Demo run 20240926T12Z (8 AM EDT): 425 segments uncertain, 251 forecast flooded, first flood at +10 h (6 PM EDT).** Baseline run 16Z: nothing flagged at hours 0–1 (first flood +12 h). Earliest named streets: Graves Rd (+10), Buford Hwy / Lake Forrest Dr NE (+11), Moores Mill Rd / McLendon Dr (+13), Northside Dr NW / Paces Ferry Rd NW (+16), Collier Rd NW / Defoor Ave NW (+17). Flags cluster along Nancy Creek and the North/South Forks of Peachtree Creek. — `uv run python -m noah.pipeline.flood_times --event helene`
- 22:23 — **Spec 003 done (CC3).** Graph: 21,178 nodes, 51,277 edges (AOI + 2 km), 36.3 MB → `fixtures/graph.graphml.gz` (4.8 MB; `gunzip -k` it). AOI edges 34,891 (626 bridge/tunnel dropped); 5,070 segments carry NOAA thresholds (101 reaches, 16,176 rows). 93% of NOAA's 3,216 AOI road ways are in our graph; NOAA lists only roads ≤ 25 m above a creek, so the rest can't creek-flood. 1 segment dropped as a crossing artifact (< 0.3 m). — `uv run python -m noah.pipeline.build_segments`
- 22:08 — **GO/NO-GO = GO.** Observed (USGS 02336300): action 13 ft up 2024-09-26 04:30Z (first rise), **minor 17 ft up 2024-09-27 01:15Z (9:15 PM EDT)**, moderate 01:45Z, major 03:45Z, peak 23.75 ft at 12:15Z. **Every** short-range cycle from 20240926T12Z on forecast the gauge reach (2047989) above minor flood flow (161.4 m³/s). **First warning: 20240926T12Z (8 AM EDT) → lead time 13.2 h.** Honest caveats: the 12Z run timed the crossing well (02:00Z, 45 min late) and overshot the peak (680 vs 566 m³/s observed); the 14Z–21Z runs forecast the crossing 3–11 h late and under-forecast the peak (190–440 m³/s); runs from 22Z on are closer. Chart: `web/data/validation.png`, data: `web/data/validation.json`. — `uv run python -m noah.pipeline.validate --event helene`
- 21:57 — **Spec 002 done.** HAND + catchments (EPSG:5070, 10 m, bounds 1042230,1247150 – 1147330,1385760; HAND nodata 32767, catchments nodata 0) and `hydrotable.parquet` from the public CIROH bucket. Catchment rasters store short IDs: **HydroID = 1274·10000 + raster value** (`branches/0/hydroid_prefix.txt`). C2 written: 190 AOI HydroIDs, 187 with monotonic curves (3 missing), 107 reaches, 15,708 rows. Gauge HydroID 12740437: (stage m, q m³/s) = (4.3, 218), (8.5, 795), (12.8, 2052). — `uv run python -m noah.pipeline.fetch_hand`
- 21:57 — **R15 finding:** `osm_roads_fimpact.csv` has, per OSM way × HydroID, `threshold_hand` (m) and `threshold_discharge` (m³/s), i.e. the flow at which that road gets wet. 23,835 rows, 11,534 OSM ways, 37 branches. Northside Dr NW at the gauge reach: 277 m³/s (9,792 cfs) on the level-path branch, 367 m³/s on branch 0. Helene's observed peak was 566 m³/s. See R15 for the proposal.
- 21:52 — Spec 001 running: `fetch_nwm --event helene --huc8` (all 1,895 HUC8 reaches, a superset of the AOI, so one 6 GB pass covers 004 too; raw files deleted per lead because only 7 GB of disk is free). Deviation from spec 001's reach list, logged here.

### Priyanshu
- _(Priyanshu's section: only Priyanshu or Priyanshu's agent edits it)_
