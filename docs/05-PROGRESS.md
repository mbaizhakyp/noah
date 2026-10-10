# 05 — Progress Tracker

_Last updated: Fri Oct 9, 2026, 9:30 PM ET (challenges final: Photon + Gemini + Replit; B2B + Replit + key-check backlog)_

## Clock (ET)
| When | Milestone | Status |
|---|---|---|
| Fri 20:30 | Hacking starts | ☑ |
| Fri ~22:00 | Accounts ready (no AWS needed: HAND comes from the public CIROH bucket): Gemini key, Photon line, Replit (ask the booth about deploy plan/credits), ~~511GA key check (BL-7)~~ dropped, cameras = Windy (spec 013) | ☐ |
| **Sat 00:00** | **GO/NO-GO:** NWM forecast at gauge reach vs observed (spec 001 + quick 005 plot). Spectrum echo bot works on a real phone (spec 008). | ☑ forecast **GO** (22:08, lead 13.2 h) · echo bot: Priyanshu |
| ~~Sat 01:00~~ | ~~Camera capture running~~ **dropped:** cameras are now checked on demand when a user asks (013 redesign, Priyanshu 23:59). | — |
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
| Data pipeline, validation, live runs, dispatch board, **iMessage relay (008)** | Margulan | `noah/pipeline/`, `web/data/`, `noah/api/dispatch.py`, `web/dispatch.html`, **`bot/`** |
| API, routing, agent, map, camera vision, engine/sources | Priyanshu | `noah/api/` (except dispatch.py), `noah/engine.py`, `noah/sources/`, `web/index.html`, `fixtures/` |
| Pitch, Devpost, video | Both (Margulan leads the hydrology story) | `README.md`, `docs/` |

Lanes are set up so neither person waits on the other. Priyanshu builds against `fixtures/` until real data lands. Margulan's outputs are files with frozen contracts. The only cross-lane hand-offs are files: `graph.graphml` (Sat 03:00), `flood_*.geojson` (Sat 12:00), `lowspots.geojson` (if 012 ships).

## Priorities
- **P0** = the demo core. Without it there's no submission.
- **P1** = what makes it convincing, or can't be done later.
- **P2** = strong extras.
- **P3** = only if ahead of schedule.
Never start a lower priority while a higher one in your lane is unfinished, (013 is no longer time-critical: on-demand checks only).

## Specs
| Spec | Title | Owner | Pri | Time box | Status |
|---|---|---|---|---|---|
| 001 | NWM forecast fetch + subset | Margulan | P0 | 2 h | **Done** (22:08; Helene, 26 cycles × 19 files, 1,895 reaches) |
| 002 | FIM HAND + rating curves fetch | Margulan | P0 | 1 h | **Done** (21:57) |
| 003 | AOI, road graph, per-road thresholds (NOAA major roads + Noah residential, CC3/CC4) | Margulan | P0 | 2.5 h | **Done** (22:38) |
| 004 | Flood times per segment | Margulan | P0 | 1.5 h | **Done** (22:24; 26 Helene cycles) |
| 005 | Validation: lead time + street truth | Margulan | P1 | 3 h | **Part A done: GO** (22:08). Part C (streets) after 004 |
| 011 | ~~Hurricane Isaias live run~~ **retired** into 015 + BL-18/19 (J10) | Margulan | — | — | Retired |
| 012 | Street low spots (storm-drain stand-in) | Margulan | P3 | 2 h | Draft |
| 006 | Routing + HTTP API | Priyanshu | P0 | 3 h | **Done** (23:55) |
| 007 | Gemini agent + safety filter | Priyanshu | P0 | 3 h | Draft |
| 008 | iMessage relay (Photon Spectrum) | **Margulan** (J14) | P0 | 2 h | Draft: Photon booth first (iMessage line), echo bot, then relay to `/chat` |
| 009 | Web map with time slider | Priyanshu | P0 | 3 h | **Functional** (01:00); UI polish later |
| 010 | Camera water classifier `classify()` (user photos removed) | Priyanshu | P2 | 1.5 h | Draft |
| 014 | Dispatch board + barricade list (Replit entry) | Margulan | P1 | 3 h | **Done** (Fri 22:55, standalone; mount = I3) |
| 013 | Camera snapshot check, on demand (Windy) | Priyanshu | P2 | 2 h | Draft |

Status flow: `Draft → Approved (human) → In progress → Done (acceptance criteria shown passing)`.

## Backlog (not yet specs)
Each research item has a 30-min time box and produces a written finding in `06-CURRENT_ISSUES.md`: source URL, license, coverage, freshness, and a verdict of spec / parking lot. **No spec gets written for a layer until a real, citable source is confirmed** (Priyanshu's "right data first" rule in `01-PROJECT_OVERVIEW.md`).

| ID | Item | Owner | Pri | When | Notes |
|---|---|---|---|---|---|
| BL-1 | **Research: storm-drain / sewer data for Atlanta.** DWM GIS, Atlanta open-data hub (ArcGIS), EPA combined-sewer data, Georgia EPD spill notifications. | Margulan | P3 | Sat afternoon, only if 005 is on track | Quick search found no open inlet layer; the records route takes ~3 business days. 012 (low spots) is the stand-in we can actually build. |
| BL-2 | **Research: pothole data for Atlanta.** Atlanta open-data hub for ATL311 requests; ATLDOT. | Priyanshu | P3 | Sat evening, only if ahead | No open ATL311 dataset found yet (records requests only). A pothole layer from another city wouldn't match the Atlanta flood demo. Default: roadmap slide. |
| BL-7 | **DROPPED (Priyanshu, Fri 23:00): 511GA not doable; cameras use Windy (spec 013).** ~~✅ **Requested Fri ~21:27 ET by Margulan → "Pending Approval"** (confirmation email: "we will process your request shortly"). Check email Sat morning; a key by Sat noon still catches the heaviest rain (Sat afternoon–night). Until then option C (own photos) is the plan. · **511GA developer key check.** Create a 511ga.org account → request a key at `511ga.org/developers/doc` → note whether it's issued instantly or goes to review, and copy the terms shown at signup into spec 013 "Discovered". Put the key in `.env` as `GA511_API_KEY`. | **Priyanshu (or Margulan, whoever is free first)** | **P1** | **Tonight, by 23:00** | Instant key → 013 option A. No key by 00:00 → decision J4 picks option B or C. 10 min of work. |
| BL-10 | **DROPPED with 511GA (Fri 23:00).** ~~Check email for the 511GA key approval and act on it.** Approved → put `GA511_API_KEY` in `.env`, tell Priyanshu, start 013 step 1 capture right away (option A). Still pending at noon → stay on option C (own photos) for the rest of Isaias and say so in PROGRESS. | Margulan (the email is Margulan's) | P1 | Sat morning, **decide by Sat 12:00** | Approval email comes from notifications@511ga.org. Record any terms it contains in spec 013 "Discovered". |
| BL-15 | **Backfilled from Fri 18:00 EDT (20261009T22Z) on Sat 01:05** with `live --backfill 20261009T22Z --keep 48`, so the demo can show the storm building run by run from Friday evening. Then: **Live loop running before Sat 08:00** (spec 015): `caffeinate -i uv run python -m noah.pipeline.live --every 900` on a laptop that stays plugged in. Check `data/interim/live.log` shows a new cycle each hour. | Margulan | **P0** | **Sat ≤ 08:00** (start tonight is fine) | NWM runs land ~1 h 45 min after the cycle hour (the 8 AM run ≈ 9:45 AM). |
| BL-16 | **Sat ~10:00 check-in:** the 8 AM (12Z) run is published, the map shows it, the numbers look sane. **Commit a snapshot** (`web/data/flood_20261010T12Z.geojson` + `cycles.json`) as timestamped evidence that Noah produced it live. | Margulan | P0 | Sat ~10:00 | Regenerable anytime (NOAA keeps every run), but the live commit is the proof of "Noah warned at 8 AM". |
| BL-17 | **Sat 14:00 decision J13:** present Isaias or the Helene backup. Bring: flagged-road counts per run since 8 AM, Peachtree + Big Creek forecast peaks, any reported closures so far. | Both | P0 | Sat 14:00 | Rides on the E2E milestone. |
| BL-18 | **Sat evening (~20:00–22:00) re-run + interim validation:** `validate --event isaias` against USGS (Peachtree 02336300 + Big Creek) and news closures; refresh the dispatch sample to Isaias-flagged streets. | Margulan | P1 | Sat 20:00–22:00 | Heavy rain is Sat afternoon–night, so this is the first real check. |
| BL-19 | **Sun ~02:00–04:00 final validation** before the 04:00 video: final lead-time numbers + street truth for Isaias; update README/Devpost. Peaks that happen after the Sun 09:00 deadline (e.g. Big Creek's forecast Sun 20:00 crest) **can't be validated, so say so**, don't extrapolate. | Margulan | P0 | Sun 02:00–04:00 | |
| BL-21 | **Isaias ground truth (REVISED Sat 01:50 after measuring camera coverage).** Camera sweep **dropped**: only 10 of 573 AOI cameras sit within 150 m of a road flagged by the Isaias Fri 10 PM run (5 near residential roads; 39 even for Helene-scale flooding), too few for a meaningful number. Keep Priyanshu's on-demand camera check as a demo visual. **Instead:** `uv run python -m noah.pipeline.incidents --every 900` logs TomTom closures / flooding / dangerous-conditions incidents in the AOI every 15 min (live-only, so run it Saturday next to the live loop; first snapshot 00:33: 55 pre-storm closures = baseline to exclude). Sunday: match flood-related closures + NWS storm reports + news to flagged roads → "of N roads reported closed by flooding, Noah forecast M, ~X h ahead", split NOAA major vs Noah residential. | Margulan | P1 | Logger from Sat morning; match at BL-18/19 | Keys verified Sat 01:45: Windy, Azure, TomTom all live. |
| BL-20 | **Helene backup kept ready:** Helene C5 files + validation stay in `web/data`; one hidden "Helene backup" option on the dispatch board; Devpost + Q&A line. Swap the demo to Helene only if J13 says so. | Margulan | P1 | — | |
| BL-8 | **B2B: small-business dispatch board + agency barricade list** (our Replit Small Business entry). Dispatch: paste depot + stops (+ time windows) → per stop "no forecast flooding on the route if you leave before ~X (not a safety guarantee)" / "hold: route cut X–Y" / "outside coverage", plus a map. One route search per forecast hour from the depot covers all stops. Barricade list: C5 segments sorted by `t_flood`, with street names, CSV export. No accounts, no DB. | Margulan (**J5 approved Fri 22:58, option A**) | P1 | **Fri night (ahead of schedule)** | **Spec 014 approved.** New files only: `noah/api/dispatch.py`, `web/dispatch.html`, so nothing overlaps Priyanshu's files. Folds in BL-4 (county stats). |
| BL-9 | **Replit deployment** of the runtime (FastAPI + map + dispatch board) for the Replit challenge and an always-on demo link | Priyanshu (proposed, J6) | P1 | Booth question tonight; deploy Sat 15:00–17:00 | **Spec 015 to write + approve.** Runtime-only deps (fastapi, uvicorn, networkx, osmnx, shapely, google-genai). Pipeline stays on the laptop. Fallback: laptop + `cloudflared` (D8). |
| BL-3 | Saved routes + "open in Google/Apple Maps" link from the route view | Priyanshu | P3 | Only if ahead | From Priyanshu's proposal. Cheap on top of 006/009. **Needs joint OK** (J2). |
| BL-6 | ~~Georgia-wide coverage~~ (now in scope, CC6), fleet/business view, satellite flood detection, sewer overflow prediction | — | Roadmap | — | From Priyanshu's proposal. Pitch as roadmap unless real data turns out to be quick to get. |

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
- **Fri 20:30–00:00 (done):** data sources verified (82, `docs/07`), keys in `.env` (Windy, Census, Mapillary, Synoptic, TomTom), CC6 written, **006 routing + API done** on real Helene data. Photon (008) moved later.
- **Sat 00:00–05:00:** **009** map on the real C5 + `/route` (5 km radius + route corridor, CC6).
- **Sat 05:00–09:00:** sleep. Nothing needs to run overnight (cameras are on demand).
- **Sat 09:00–14:00:** **007** Gemini agent on 006 → **E2E at 14:00** (web chat first; iMessage via 008 when Photon is set up).
- **Sat 14:00–20:00:** **010** `classify()` → **013** on-demand camera checks in `/status` + `/route` → 008 Photon relay → BL-9 Replit deploy if time.
- **Sat 20:00–Sun 00:00:** README run instructions, test the map on a phone.
- **Sun 00:00–05:00:** video capture, submit prep.

## Log
_Append-only. Format: `HH:MM Name — what was done — how verified (command)`._

### Margulan
- 20:18 — Pulled USGS IV for 02336300, Sep 26–28, 2024. Minor (17 ft) up at 2024-09-26 21:15 EDT; major (20 ft) up at 23:45 EDT; peak 23.75 ft at 2024-09-27 08:15 EDT; peak Q 20,000 cfs at 05:45 EDT. — `nwis.waterservices.usgs.gov/nwis/iv/?sites=02336300&parameterCd=00065,00060&startDT=2024-09-26T00:00-04:00&endDT=2024-09-28T00:00-04:00&format=json`
- 20:18 — Verified the NWM archive exists: `gs://national-water-model/nwm.20240927/short_range/...channel_rt.f001.conus.nc` (12.7 MB, anonymous HTTPS). AWS `noaa-nwm-pds` has no 2024 data.
- 20:18 — Verified AOI and IDs: HUC10 0313000112 "Peachtree Creek" (338.49 km²), HUC8 03130001; NLDI comid for the gauge = 2047989; NWPS AANG1 thresholds (action 13 / minor 17 / moderate 18 / major 20 ft; 3630 / 5700 / 7000 / 7800 cfs).
- 20:45 — Live NWM latency measured: cycle t22z (Oct 9) f018 landed in GCS at 23:48Z (~1 h 45 min). — GCS JSON API listing, prefix `nwm.20261009/short_range/nwm.t22z...f018`
- 20:45 — Isaias check: 20261009T22Z forecast at 2047989 = 1.1 / 1.6 / 4.1 / 17.5 / 30.0 / 25.5 m³/s at f003/6/9/12/15/18 (peak ≈ 1,061 cfs, below action 3,630). Observed 2026-10-09 20:00 EDT: 2.08 ft, 18 cfs. Reading NWM needed `h5py` alongside `h5netcdf`. — `uv run --with xarray --with h5netcdf --with h5py`, `xr.open_dataset(..., engine="h5netcdf")["streamflow"].sel(feature_id=2047989)`
- 21:45 — HAND data found in a public bucket, no AWS account needed: `s3://ciroh-owp-hand-fim/hand_fim_4_9_9_0/03130001/` (OWP HAND-FIM v4.9.9.0, 461 files, 0.79 GB). Branch 0: HAND 106 MB, catchments 3.7 MB, hydroTable 110.6 MB; HUC-level `hydrotable.parquet` 3.3 MB. — anonymous S3 ListObjectsV2 over HTTPS
- 01:15 — **Backfilled the Isaias story from Friday evening** (`live --backfill 20261009T22Z --keep 48`; new `--backfill` option): Fri 6 PM run 77 flagged / 40 flooded (Peachtree fcst peak 1,071 cfs) → 8 PM 104 / 48 (1,472) → 9 PM 205 / 62 (2,408) → 10 PM 313 / 97 (3,290 cfs; action 3,630). The 7 PM (23Z) run was never published by NOAA (404 on GCS); skipped. J11 accepted with condition; J14 proposed (008 → Margulan).
- 00:55 — **Demo event = Isaias (D5/J10 decided), Helene = backup.** Reviewed Priyanshu's live loop (`noah/pipeline/live.py`): correct; added `--keep` (pruning would have deleted the 8 AM run). First live pass on the metro data: **20261010T02Z (10 PM Fri) → 313 segments flagged, 97 flooded**; Peachtree forecast peak rising run over run: 1,061 → 2,408 → 3,291 cfs (action 3,630). Dispatch board defaults to the newest live run (Helene in a "Backup" group); `dispatch.active_cycle()` prefers live. Live run already shows Collier Rd impassable ~6 AM Sat. Saturday check-ins: BL-15…BL-20.
- 23:50 — **Coverage expanded (CC6 narrowed): metro Atlanta = 4 HUC10s of HUC8 03130001** (Peachtree, Sope Creek, Big Creek, Suwanee Creek; 1,426 km², ~4×). No new downloads of NWM/HAND (already HUC8-wide). Graph 68,533 nodes / 154,988 edges (112.5 MB; `fixtures/graph.graphml.gz` 15.0 MB). Rating: 931 HydroIDs / 562 reaches. C3: 135,289 rows (NOAA 15,305 segments + Noah 62,202). Streams: 940 reaches. **8 AM run: 1,300 segments flooded, 2,423 uncertain, first flood +9 h (5 PM).** Validation unchanged (GO, 13.2 h; Windsor Pkwy + Woodward Way flagged 10 PM). New artifact found and fixed: **Riverwalk Dr (Roswell) by the regulated Chattahoochee** showed flooded at hour 0 (threshold 132.7 vs normal flow 130 m³/s), so the baseline guard is now `BASELINE_GUARD_FACTOR = 1.5` (drops 54 of 77,491 segments). Dispatch on the big graph: 3.5 s per check (trip box), graph load 8.5 s, **peak RAM ~1.8 GB** (R20). C7 `aoi.geojson` now has 4 features with `huc8` (I13).
- 23:35 — **Map made intuitive (Margulan's feedback on the dispatch map).** Blue creeks (C14), delivery routes drawn from the depot, colored by status *if a driver leaves at the slider time*: green = open, amber = open but closing later, red dashed = cut, with a ✕ at the street where it breaks ("Collier Road · impassable ~7 PM", labels de-overlapped). Numbered pins match the list; a time slider with a plain-language caption ("If a driver leaves at Thu 6:00 PM: 1 route cut…") and Play button; roads turn red/amber only once forecast underwater by that time. API adds `route`, `cut_at`, `cut_h` per stop. Verified in the browser at 6 PM / 10 PM and phone width.
- 22:55 — **Spec 014 done (standalone).** `noah/api/dispatch.py` (router: `POST /dispatch`, `GET /barricades`) + `web/dispatch.html` + `web/data/dispatch_sample.json` (Peachtree Corner Pharmacy sample: depot on Peachtree Rd + 10 stops on public streets). Stops snap to the nearest road segment (an address sits on a street), so a stop is cut if its own street floods. 9 stops in ~3 s (first call incl. graph load), <1 s after. Verdicts: **8 AM run** → Collier Rd go before ~6 PM, Woodward Way / Windsor Pkwy before ~8 PM, Hanover W / Bohler before ~10 PM, 3 upland stops no forecast flooding, airport outside coverage; **10 PM run** → 5 holds. Barricade list: 155 streets for the 8 AM run (Valley Rd NW, Graves Rd... from 6 PM), CSV export. Checked in the browser (desktop + 375 px phone), no console errors, no banned words. Run: `uv run python -m noah.api.dispatch --serve` → http://localhost:8001/dispatch.html. Also fixed: `cycles.json` listed the baseline run twice; now 25 runs, chronological.
- 22:40 — **CC4 done: residential streets.** NOAA's list has no residential roads, so Noah computes thresholds from FIM HAND (int16 mm, verified vs NOAA: bias 0.00 m, corr 0.74) for the 15,698 AOI segments NOAA omits, across branch 0 + level paths 3286000029/31/33/35 (23 MB extra). C3 now 42,086 rows (noaa + noah). **8 AM demo run: 705 segments flooded, 1,093 uncertain, first flood +9 h (5 PM).** Street truth now: ✅ Windsor Pkwy flooded 10 PM (closed ~10:15 PM), ✅ **Woodward Way flooded 10 PM** (was a miss). Also flagged (sources to verify before citing): Hanover W 11 PM, Bohler Rd and Peachtree Battle Ave midnight, Sagamore Dr 1 AM, consistent with pre-dawn Friday rescues in the Peachtree Battle area. Fallback: `build_segments --noaa-only` + `flood_times`. — `uv run python -m noah.pipeline.build_segments --step 2 && uv run python -m noah.pipeline.flood_times && uv run python -m noah.pipeline.validate`
- 22:50 — **Spec 005 part C (street truth), honest scorecard for the 8 AM demo run:** ✅ **Windsor Pkwy at Nancy Creek**: forecast flooded from **10 PM Thu** (uncertain from 8 PM); actually closed ~10:15 PM Thu (Appen Media, 11Alive). ❌ **Woodward Way at Bobby Jones** (flooded per Rough Draft Atlanta): not flagged; NOAA ties it to a small tributary reach (2044831) whose forecast stayed low. ❌ **Sagamore Dr / Bohler Rd / Hanover W** (reported closed; source to verify): **not in NOAA's road list at all**, which covers only motorway–tertiary, **no residential streets** (70% of our edges). Northside Dr NW: flagged from midnight, but no verified source showing the road flooded ("water approaching the Northside Drive bridge" only), so left out. Streets live in `noah/pipeline/street_truth.json` → `validation.json["streets"]`. Proposal CC4 (residential thresholds) logged. — `uv run python -m noah.pipeline.validate --event helene`
- 22:24 — **Spec 004 done.** 26 C5 files + `cycles.json` in `web/data/` (2.3 MB total). **Demo run 20240926T12Z (8 AM EDT): 425 segments uncertain, 251 forecast flooded, first flood at +10 h (6 PM EDT).** Baseline run 16Z: nothing flagged at hours 0–1 (first flood +12 h). Earliest named streets: Graves Rd (+10), Buford Hwy / Lake Forrest Dr NE (+11), Moores Mill Rd / McLendon Dr (+13), Northside Dr NW / Paces Ferry Rd NW (+16), Collier Rd NW / Defoor Ave NW (+17). Flags cluster along Nancy Creek and the North/South Forks of Peachtree Creek. — `uv run python -m noah.pipeline.flood_times --event helene`
- 22:23 — **Spec 003 done (CC3).** Graph: 21,178 nodes, 51,277 edges (AOI + 2 km), 36.3 MB → `fixtures/graph.graphml.gz` (4.8 MB; `gunzip -k` it). AOI edges 34,891 (626 bridge/tunnel dropped); 5,070 segments carry NOAA thresholds (101 reaches, 16,176 rows). 93% of NOAA's 3,216 AOI road ways are in our graph; NOAA lists only roads ≤ 25 m above a creek, so the rest can't creek-flood. 1 segment dropped as a crossing artifact (< 0.3 m). — `uv run python -m noah.pipeline.build_segments`
- 22:08 — **GO/NO-GO = GO.** Observed (USGS 02336300): action 13 ft up 2024-09-26 04:30Z (first rise), **minor 17 ft up 2024-09-27 01:15Z (9:15 PM EDT)**, moderate 01:45Z, major 03:45Z, peak 23.75 ft at 12:15Z. **Every** short-range cycle from 20240926T12Z on forecast the gauge reach (2047989) above minor flood flow (161.4 m³/s). **First warning: 20240926T12Z (8 AM EDT) → lead time 13.2 h.** Honest caveats: the 12Z run timed the crossing well (02:00Z, 45 min late) and overshot the peak (680 vs 566 m³/s observed); the 14Z–21Z runs forecast the crossing 3–11 h late and under-forecast the peak (190–440 m³/s); runs from 22Z on are closer. Chart: `web/data/validation.png`, data: `web/data/validation.json`. — `uv run python -m noah.pipeline.validate --event helene`
- 21:57 — **Spec 002 done.** HAND + catchments (EPSG:5070, 10 m, bounds 1042230,1247150 – 1147330,1385760; HAND nodata 32767, catchments nodata 0) and `hydrotable.parquet` from the public CIROH bucket. Catchment rasters store short IDs: **HydroID = 1274·10000 + raster value** (`branches/0/hydroid_prefix.txt`). C2 written: 190 AOI HydroIDs, 187 with monotonic curves (3 missing), 107 reaches, 15,708 rows. Gauge HydroID 12740437: (stage m, q m³/s) = (4.3, 218), (8.5, 795), (12.8, 2052). — `uv run python -m noah.pipeline.fetch_hand`
- 21:57 — **R15 finding:** `osm_roads_fimpact.csv` has, per OSM way × HydroID, `threshold_hand` (m) and `threshold_discharge` (m³/s), i.e. the flow at which that road gets wet. 23,835 rows, 11,534 OSM ways, 37 branches. Northside Dr NW at the gauge reach: 277 m³/s (9,792 cfs) on the level-path branch, 367 m³/s on branch 0. Helene's observed peak was 566 m³/s. See R15 for the proposal.
- 21:52 — Spec 001 running: `fetch_nwm --event helene --huc8` (all 1,895 HUC8 reaches, a superset of the AOI, so one 6 GB pass covers 004 too; raw files deleted per lead because only 7 GB of disk is free). Deviation from spec 001's reach list, logged here.

### Priyanshu
- _(Priyanshu's section: only Priyanshu or Priyanshu's agent edits it)_
- 22:45 — Data sources verified: 82 working sources in `docs/07-DATA_SOURCES.md`. Keys in `.env`: Windy, Census, Mapillary, Synoptic, TomTom. — curl tests per source (counts recorded in 07)
- 23:55 — **Spec 006 done.** `noah/api/app.py` + `routing.py`. `/health`, `/status` (5 km radius), `/route` (trip box + 1 km corridor). Dispatch router mounted, `web/` served at `/`. Real Helene data, cycle 20240926T12Z:
  - `/status` at the gauge: 378 segments, matches an independent check.
  - Peachtree Battle → Northside detours around 3 flagged segments at +16 h.
  - Chattanooga → `out_of_coverage`; Albany → `no_road_forecast`; +19 h → `beyond_forecast_window`.
  - All responses < 0.05 s.
  — `uv run pytest -q` (18 passed), `ruff check` clean, acceptance script against `uvicorn --port 8010`.
- 01:00 — **Spec 009 functional.** `web/index.html` (served by the API at `/`, links to `dispatch.html`).
  - Nothing loads until asked: "Use my location" or a typed place (Photon, Georgia bbox) → "Check my area" (5 km); destination search → route + 1 km corridor.
  - Time slider 0–18 h with Play. Google/Apple Maps hand-off (3 waypoints from Noah's route). Validation panel (13.2 h). Camera markers render if `/status` / `/route` return `cameras`.
  - Verified in Chrome on real Helene data: Peachtree Battle → Northside at +16 h goes around 3 flooded segments; Bobby Jones Golf Club 5 km check = 140 streets; 390 px phone width has no sideways scroll and 44 px tap targets. No banned words in visible text.
  - UI polish deferred (map-first layout on phones is in the CSS but not re-checked).

- 02:45 — **Spec 015 engine + live loop working on live data.**
  - `noah/pipeline/live.py` (reuses 001/004 code) published NWM `20261010T01Z`: 602 reaches, 205 segments flagged (62 flooded), 17 s. It runs `--every 900`.
  - Pipeline inputs rebuilt locally (002/003): 68,533 nodes, 154,988 edges, 135,289 threshold rows.
  - `noah/sources/` has 14 adapters: NWS alerts, LSR 24 h, NWS QPF, NWPS gauges, NWPS reach blend, USGS, Synoptic, WPC ERO, TomTom, FEMA zone, LSR history, CDC SVI, SeeClickFix, NHC.
  - `noah/engine.py`: rules + Azure OpenAI assessment, number guard + banned-word filter + rules fallback.
  - `/assess` (Peachtree Creek) returned 14/14 sources, 48 signals, AI assessment, ~8 s. `/assess/route` and Albany (`no_road_forecast` + statewide signals) were verified too.
  — `uv run pytest -q` (23 passed), `ruff` clean
- 03:45 — **Backend complete for flood hazards (spec 015 done).**
  - 33 sources live per area/route: warnings, gauges, creek flows, rapid-onset flooding, high-water probability, rain now/forecast/guidance/rarity, outlooks, storms, TomTom, cameras (AI, two-step verified), flood zones, past floods, insurance claims, dams, storm drains, CSO + sewage spills, road roughness/potholes, vulnerability, facilities, news, Bluesky.
  - Live hazards re-route (a camera at Northside/Peachtree Battle + a Rockingham Dr closure blocked 4 segments in a test).
  - Exact-number guard.
  — `uv run pytest -q` (25 passed), `ruff` clean, live `/assess` 33/33 sources.
- 04:45 — **Past mode.**
  - The slider runs −18 h … +18 h. Past hours show each hourly NWM run's hour-0 estimate (dashed lines), from `GET /past` and `/past/route`.
  - A "Last 18 hours" panel shows USGS stage history per gauge (sparklines) + NWS storm reports from the last 24 h.
  - Live loop backfilled 09Z–02Z with `--backfill … --keep 48` (the 23Z run is missing on GCS).
  - The AI assessment panel (now / next 18 h / next days) is on the map.
  — `uv run pytest -q` (27 passed), JS parse check, no banned words..