# 02 — Architecture

## 1. Shape
Noah splits into an **offline pipeline** that writes files and a **runtime** that reads them. No database. The runtime holds everything in memory.

```
OFFLINE (Python, Margulan)                                RUNTIME (Priyanshu)
                                                          
NWM short_range .nc (GCS) ──► fetch_nwm ──► nwm/<cycle>.parquet ─┐
FIM hydroTable (CIROH S3)     ► fetch_hand ► rating.parquet ─────┼─► flood_times ─► web/data/flood_<cycle>.geojson ──┐
FIM HAND + catchments rasters ─┘                                 │                                                  │
OSM drive network (OSMnx) ──► build_segments ─► graph.graphml ───┼──────────────────────────────────────────────┐   │
  + NOAA fimpact thresholds                   └► seg_thresholds ──┘                                              ▼   ▼
USGS IV + NWS thresholds ──► validate ─► web/data/validation.json          FastAPI (noah/api): /status /route /chat
                                                                                 ▲            │ Gemini agent (tools =
                                                       iMessage ⇄ Photon Spectrum relay (bot/, TS)   plain functions)
                                                                                              ▼
                                                                  Web map (web/index.html, static, MapLibre)
```

## 2. Core algorithm (flood time per road segment) — CC3, approved Oct 9
We use **NOAA OWP FIM 4.9's own per-road flood thresholds** (`osm_roads_fimpact.csv`: per OSM way × HydroID, the HAND height and the discharge at which the road gets wet). We don't sample HAND ourselves. NOAA computes *where / at what flow*; Noah adds *when* (forecast), routing, and delivery.

1. **Once (003), major roads:** join OSMnx drive edges to the thresholds by OSM way id. Drop `bridge`/`tunnel` edges (bare-earth HAND would call every bridge flooded). Drop threshold rows with `threshold_hand < MIN_ROAD_HAND_M` (0.3 m): the road sits at channel level, a culvert/crossing artifact. Result: C3, one row per (segment, HydroID, branch).
   **Residential and other roads NOAA doesn't list (CC4):** same method on the same data. Sample FIM HAND + catchment rasters every 10 m along the edge, for branch 0 **and** the 4 main-stem level-path branches (FIM's composite is the max extent across branches, so main-stem flooding reaches side-creek catchments). Per (segment, HydroID, branch): lowest HAND ≥ 0.3 m and ≤ 25 m → discharge on that curve. Tagged `source = "noah"`. Check vs NOAA on shared roads: median ΔHAND 0.00 m bias, corr 0.74.
2. **Uncertain band:** per row, `uncertain_q` = discharge on that HydroID/branch rating curve at stage `max(threshold_hand − UNCERTAIN_BAND_M, 0.5 · threshold_hand)`.
3. **Baseline guard:** drop rows whose `threshold_q` ≤ the reach's flow in `BASELINE_CYCLE` (wet at low flow = artifact).
4. **Per cycle (004):** lead hour 0 = **now** (NWM analysis), 1–18 = forecast. `t_flood` = first lead with `q(feature_id) ≥ threshold_q`; `t_uncertain` = first lead with `q ≥ uncertain_q`. Per segment, take the minimum over its rows (conservative; equals FIM's max-extent composite across branches).
5. **Conservative persistence:** once a segment enters a state it stays there for the rest of the 18 h window. Recession is not modeled.

## 3. Repo layout
```
CLAUDE.md                  AI entry point
README.md                  Devpost-facing README (finalized at freeze)
pyproject.toml             one Python project (uv); created by the first spec that needs it
.env.example               names of required secrets, no values
noah/                      Python package
  config.py                ALL constants and paths (see §7). Shared file: change with a heads-up.
  pipeline/                Margulan
    fetch_nwm.py           spec 001
    fetch_hand.py          spec 002
    build_segments.py      spec 003
    flood_times.py         spec 004
    validate.py            spec 005 (also run per event, spec 011)
    lowspots.py            spec 012 (terrain low spots on roads)
  api/                     Priyanshu
    app.py                 spec 006 (FastAPI)
    routing.py             spec 006
    agent.py               spec 007 (Gemini + tools + safety filter)
    photo.py               spec 010 (water-depth classifier, shared with 013)
    cameras.py             spec 013 (on-demand Windy snapshot checks for /status and /route)
    dispatch.py            spec 014 (Margulan: dispatch board + barricade list, FastAPI router)
tests/                     one small test file per module with real logic
fixtures/                  tiny hand-made files that follow the §4 contracts (for Priyanshu before real data lands)
bot/                       Priyanshu — spec 008 (TypeScript, Photon Spectrum relay)
web/                       Priyanshu — spec 009 (single index.html, no build step)
  data/                    pipeline outputs the map needs (committed; keep each file < 20 MB)
data/                      gitignored: raw downloads + interim tables
  raw/  interim/
docs/                      the six context files
specs/                     one spec per unit of work
```

## 4. Data contracts (FROZEN — change only with both humans' agreement)
Cycle IDs everywhere use the format `YYYYMMDDTHHZ`, e.g. `20240926T12Z`. All times are UTC ISO-8601 with `Z`. Units are SI.

### C1 `data/interim/nwm/<cycle>.parquet` — producer 001
| column | type | notes |
|---|---|---|
| feature_id | int64 | NWM reach = NHDPlusV2 COMID; only reaches in processed HUC8s (CC6) |
| lead_h | int8 | **0–18**: 0 = `analysis_assim` tm00 at the issue time (model estimate of *now*); 1–18 = `short_range` forecast |
| valid_time | timestamp (UTC) | issue time + lead_h |
| q_cms | float32 | `streamflow`, m³/s |

### C2 `data/interim/rating.parquet` — producer 002
| column | type | notes |
|---|---|---|
| hydro_id | int64 | FIM HydroID |
| feature_id | int64 | NWM reach the HydroID belongs to |
| stage_m | float32 | |
| q_cms | float32 | |
Sorted by `hydro_id, stage_m`. Contains only HydroIDs in the processed Georgia HUC8s (CC6).

### C3 `data/interim/seg_thresholds.parquet` — producer 003, consumer 004 (CC3)
| column | type | notes |
|---|---|---|
| seg_id | str | `"{u}-{v}-{key}"` from OSMnx |
| hydro_id | int64 | FIM HydroID the threshold belongs to |
| feature_id | int64 | NWM reach of that HydroID |
| branch_id | int64 | FIM branch (0 or a level path) |
| threshold_hand_m | float32 | NOAA `threshold_hand` (m) |
| threshold_q_cms | float32 | flow (m³/s) at which the road gets wet |
| source | str | `noaa` (FIM 4.9 fimpact, major roads) or `noah` (computed from FIM HAND, other roads; CC4) |
Only AOI edges, no bridges/tunnels, no rows below `MIN_ROAD_HAND_M`. Fallback: `build_segments --noaa-only` writes NOAA rows only.

### C4 `data/interim/graph.graphml` — producer 003
OSMnx `network_type="drive"` graph for the processed HUC8s (clipped to Georgia) buffered by 2 km (CC6), EPSG:4326. Every edge carries `seg_id`, `length` (m), `travel_time` (s) from `ox.add_edge_speeds` + `ox.add_edge_travel_times`, plus `name` and `highway` where present.

### C5 `web/data/flood_<cycle>.geojson` — producer 004
FeatureCollection, EPSG:4326, coordinates rounded to 5 dp. **Contains only segments with a non-null `t_uncertain`.**
| property | type | notes |
|---|---|---|
| seg_id | str | joins to C3/C4 |
| name | str \| null | OSM street name |
| t_uncertain | int | first lead hour (0–18) in the uncertain band; 0 = already estimated now |
| t_flood | int \| null | first lead hour (0–18) forecast flooded |
| feature_id | int | controlling reach |
| hand_min_m | float | lowest NOAA `threshold_hand` among the segment's rows, 2 dp |

### C6 `web/data/cycles.json` — producer 004
```json
{"demo_cycle": "20240926T12Z",
 "events": {"helene": {"label": "Hurricane Helene, Sep 26–27, 2024", "demo_cycle": "20240926T12Z"},
            "isaias": {"label": "Hurricane Isaias, Oct 10, 2026", "demo_cycle": "20261010T06Z"}},
 "cycles": [{"cycle": "20240926T12Z", "event": "helene", "issue_time": "2024-09-26T18:00:00Z",
             "valid_times": ["2024-09-26T18:00:00Z", "...19 entries, index = lead_h 0–18"]}]}
```
`events` and `cycles[].event` were added Oct 9 for spec 011. The top-level `demo_cycle` stays as the default scenario. An event appears only once its C5 files exist.

### C7 `web/data/aoi.geojson` — producer 003
**Coverage polygon = the State of Georgia** (TIGER, FIPS 13), EPSG:4326 (CC6). Feature property `hucs`: list of HUC8s with road-level timing, and their outlines as extra features with `{"huc8": "..."}`. ~~The AOI polygon (HUC10 0313000112)~~

### C8 `web/data/validation.json` — producer 005
```json
{"gauge": {"usgs": "02336300", "nws_lid": "AANG1", "feature_id": 2047989},
 "thresholds_ft": {"action": 13, "minor": 17, "moderate": 18, "major": 20},
 "thresholds_cfs": {"action": 3630, "minor": 5700, "moderate": 7000, "major": 7800},
 "observed": {"minor_cross_utc": "...", "peak_stage_ft": 23.75, "peak_utc": "..."},
 "cycles": [{"cycle": "...", "fcst_peak_cms": 0.0, "fcst_peak_utc": "...", "fcst_minor_cross_utc": null}],
 "first_warning_cycle": "...", "lead_time_h": 0.0}
```

### C9 HTTP API — producer 006/007, base `http://localhost:8000`
| method + path | request | response |
|---|---|---|
| `GET /health` | — | `{"ok": true, "cycle": "20240926T12Z"}` |
| `GET /status` | `lat, lon, hours=18` | `{"state": STATE, "segments": [{"seg_id","name","state","eta_utc","distance_m"}], "cycle"}`: **every** segment within `ALERT_RADIUS_KM` (5 km) and within `hours`, nearest first; `state` = worst (CC6) |
| `GET /route` | `from=lat,lon&to=lat,lon&depart_h=0` | `{"state": "route_found"\|"no_route"\|"out_of_coverage"\|"beyond_forecast_window", "geometry": GeoJSON LineString\|null, "minutes": float\|null, "avoided": [seg_id], "corridor": [{"seg_id","name","state","eta_utc"}], "map_url": str}`. `corridor` = every segment within `CORRIDOR_BUFFER_M` (1 km) of the route (CC6) |
| `POST /chat` | `{"sender": str, "text": str, "image_b64": str\|null}` | `{"reply": str}` |
| (spec 013, CC6) | — | **No separate camera endpoints.** `/status` and `/route` gain `"cameras": [{"cam_id","name","lat","lon","distance_m","ts_utc","bucket","confidence","image_url","page_url"}]`, checked on demand (≤5 in the radius, ≤8 along the route). `image_url` = fresh Windy URL (expires in 10 min); nothing stored. |
`STATE` ∈ `flooded | uncertain | no_forecast_flooding | out_of_coverage`.
"Now" = lead hour 0 of the active cycle in replay mode. The active cycle is env `NOAH_CYCLE` if set, otherwise C6 `demo_cycle`. A route removes every edge whose `t_uncertain <= depart_h + ROUTE_BUFFER_H`. A `depart_h` > 18 is outside the forecast window: `/route` returns `state: "beyond_forecast_window"` and the agent says so instead of guessing.

### C10 Map URL — producer 009, consumed by 006/007
`{WEB_BASE}/?cycle=20240926T12Z&t=3&from=lat,lon&to=lat,lon&api={API_BASE}`. All parameters are optional. With `from`, `to` and `api` set, the map calls `/route` and draws the result.

### C13 Dispatch + barricades API — producer 014 (Margulan), mounted by 006's `app.py` (Priyanshu)
| method + path | request | response |
|---|---|---|
| `POST /dispatch` | `{"cycle"?, "depot": {"label","lat","lon"}, "stops": [{"id","label","lat","lon"}]}` | `{"cycle","issue_time","valid_until","depot","stops": [{"id","label","state","go_before_utc"\|null,"minutes"\|null}]}` |
| `GET /barricades` | `cycle` (optional) | `[{"street","segments","length_m","first_flood_utc","state"}]` |
Dispatch `state` ∈ `go_before | hold | no_forecast_flooding | out_of_coverage`. Same edge-blocking rule as `/route`.

### C11 `web/data/lowspots.geojson` — producer 012, consumer 009
FeatureCollection, EPSG:4326, coordinates at 5 dp. One LineString per road segment that crosses a terrain depression.
| property | type | notes |
|---|---|---|
| seg_id | str | joins to C4 |
| name | str \| null | |
| depth_max_m | float | deepest fill depth under the segment, 2 dp |
| pond_area_m2 | int | area of the depression it sits in |
Static: it doesn't change by forecast hour and **doesn't affect routing or states** in the MVP.

### C12 `data/interim/cctv_assessments.parquet` — producer + consumer 013 (Priyanshu only)
| column | type | notes |
|---|---|---|
| cam_id | str | Windy webcam id (CC6: 511GA removed) |
| ts_utc | timestamp (UTC) | capture time |
| frame_path | str \| null | null: frames aren't stored (Windy terms, CC6) |
| bucket | str | `none\|curb\|half_tire\|door_sill_or_above\|cant_tell` (same as 010) |
| confidence | str | `low\|med\|high` |
| reference_object | str \| null | |
C12 is a log of on-demand checks only (no images, no background capture; CC6).

## 5. User-facing state vocabulary (FROZEN)
Every reply from the agent, the API and the map uses exactly these meanings. Wording can be shortened but must keep its meaning.

| state | message template |
|---|---|
| `flooded` | **Do not cross {road}.** Forecast shows water reaching it around {time}. |
| `uncertain` | **{road}: uncertain, treat as impassable** from around {time}. |
| `no_forecast_flooding` | No flooding is forecast on this route through {end_time}. **This is not a safety guarantee.** Conditions change fast; never drive into water. *Turn Around Don't Drown.* |
| `out_of_coverage` | That's outside Noah's coverage (Georgia). Check local official warnings. |
| `no_road_forecast` (CC6, proposed) | Noah doesn't have road-level forecasts for this part of Georgia yet. {official_alerts_or_none}. Treat any water on a road as impassable. |
| `beyond_forecast_window` | That's more than 18 hours out, past Noah's forecast window. Ask again closer to the time. |
| dispatch `go_before` (014) | **Go before ~{time}.** No forecast flooding on this route if you leave before then. Not a safety guarantee. |
| dispatch `hold` (014) | **Hold this delivery.** The route is forecast cut by flooding from ~{time}. |
| dispatch `no_forecast_flooding` (014) | No forecast flooding on this route through {end_time}. Not a safety guarantee. |
| low spot (C11, informational) | **Low spot:** water can pool here in heavy rain when storm drains back up. Not part of the creek forecast. |
| camera water (013) | **Camera on {road} shows water** around {reference} level at {time}. Treat nearby roads as impassable. (Webcams provided by Windy.com) |
A camera or photo report can only move a road to a **more** conservative state. Never use one to say water is gone.

- Times are shown in America/New_York, e.g. "around 9 PM".
- Always say "forecast". Mention 911 for emergencies whenever a message describes danger.
- **Banned in any output:** "safe", "safely", "clear", "passable", "you're fine", "no risk". `agent.py` enforces this with a filter applied to every outgoing message (spec 007).
- On any internal error, the reply is: "I can't confirm conditions right now, so treat low roads near creeks as impassable. In an emergency call 911."

## 6. Runtime and deployment
- **Pipeline:** `uv run python -m noah.pipeline.<module> [args]`, run on Margulan's laptop. Its outputs are committed to `web/data/`.
- **API:** `uv run uvicorn noah.api.app:app --port 8000`. It loads C3, C4, C5 and C6 into memory at startup.
- **Relay:** `cd bot && npx tsx index.ts`. It forwards messages to `POST /chat`.
- **Map:** GitHub Pages serving `/web`.
- **Tunnel for judging:** `cloudflared tunnel --url http://localhost:8000`. Put the tunnel URL in `API_BASE`.

## 7. `noah/config.py` (single source of constants)
| name | value | source |
|---|---|---|
| COVERAGE | State of Georgia (FIPS `13`) | TIGER (CC6) |
| VALIDATION_HUC10 | `"0313000112"` (Peachtree Creek, Helene validation only) | WBD |
| HUC8S | `["03130001", ...]` processed in rollout order (01 §Coverage). 53 HUC8s touch Georgia | WBD, CIROH |
| GAUGE_USGS / GAUGE_NWS_LID / GAUGE_FEATURE_ID | `"02336300"` / `"AANG1"` / `2047989` | NLDI, NWPS |
| MINOR_FLOOD_CMS | `161.4` (5,700 cfs) | NWPS AANG1 |
| HELENE_CYCLES | hourly `20240926T12Z` … `20240927T12Z` | — |
| BASELINE_CYCLE | `20240926T16Z` (gauge at low flow, 4.4 ft) | USGS IV |
| DEMO_CYCLE | `20240926T12Z` (D5 final: 8 AM EDT run, earliest + most skillful, 13.2 h lead) | spec 005 |
| EVENTS | `{"helene": {cycles 20240926T12Z…20240927T12Z, baseline 20240926T16Z, demo 20240926T12Z}, "isaias": {cycles 20261010T00Z…(latest), baseline 20261009T22Z, demo set by spec 011}}`. Pipeline CLIs take `--event`. | spec 011 |
| NWM_LATENCY | ~1 h 45 min from cycle time to f018 in the bucket (t22z on Oct 9 landed 23:48Z) | measured Oct 9, 2026 |
| ACTION_FLOW_CMS | `102.8` (3,630 cfs) | NWPS AANG1 |
| UNCERTAIN_BAND_M | `0.5` | heuristic, see issues |
| ROUTE_BUFFER_H | `1` | — |
| ALERT_RADIUS_KM | `5` (fixed radius around the user; CC6) | Priyanshu |
| CORRIDOR_BUFFER_M | `1000` (hazard check along a searched route; CC6) | Priyanshu |
| MIN_ROAD_HAND_M | `0.3` (crossing-artifact floor for NOAA thresholds) | CC3, R3 |
| NWM_URL | `https://storage.googleapis.com/national-water-model/nwm.{YYYYMMDD}/short_range/nwm.t{HH}z.short_range.channel_rt.f{FFF}.conus.nc` | verified Oct 9, 2026 |
| GEMINI_MODEL | from env `GEMINI_MODEL` | check ai.google.dev for the current Flash model |
| API_BASE, WEB_BASE | from env | — |
| paths | `DATA_RAW`, `DATA_INTERIM`, `WEB_DATA` (pathlib, repo-relative) | — |
