# 02 — Architecture

## 1. Shape
Noah splits into an **offline pipeline** that writes files and a **runtime** that reads them. No database. The runtime holds everything in memory.

```
OFFLINE (Python, Margulan)                                RUNTIME (Priyanshu)
                                                          
NWM short_range .nc (GCS) ──► fetch_nwm ──► nwm/<cycle>.parquet ─┐
FIM hydroTable (S3, req-pays) ► fetch_hand ► rating.parquet ─────┼─► flood_times ─► web/data/flood_<cycle>.geojson ──┐
FIM HAND + catchments rasters ─┘                                 │                                                  │
OSM drive network (OSMnx) ──► build_segments ─► graph.graphml ───┼──────────────────────────────────────────────┐   │
                                             └► seg_hand.parquet ┘                                              ▼   ▼
USGS IV + NWS thresholds ──► validate ─► web/data/validation.json          FastAPI (noah/api): /status /route /chat
                                                                                 ▲            │ Gemini agent (tools =
                                                       iMessage ⇄ Photon Spectrum relay (bot/, TS)   plain functions)
                                                                                              ▼
                                                                  Web map (web/index.html, static, MapLibre)
```

## 2. Core algorithm (flood time per road segment)
We deliberately avoid raster thresholding and polygon joins for each forecast hour.

1. **Once:** sample the HAND raster and the catchment (HydroID) raster every ≤10 m along each road segment. Store one row per sample: `(seg_id, hydro_id, hand_m)`. Bridges and tunnels produce no samples.
2. **Per cycle:** for each HydroID, `stage(t) = interp(q(feature_id, t), rating_curve(hydro_id))`.
3. **Channel-pixel filter:** discard samples with `hand_m <= stage_baseline(hydro_id)`, where the baseline is stage at the low-flow cycle (`BASELINE_CYCLE`). These pixels are the stream channel itself, e.g. a culvert crossing burned into the DEM. Dropping them makes a crossing's threshold the elevation of the road approach. Note: `hand_m <= stage` is the same comparison FIM uses to mark a pixel wet.
4. For each segment, `hand_min = min(hand_m)` over the remaining samples, per HydroID.
5. `t_flood` = first lead hour where `stage(t) >= hand_min`. `t_uncertain` = first lead hour where `stage(t) >= hand_min - UNCERTAIN_BAND_M`.
6. **Conservative persistence:** once a segment enters a state it stays there for the rest of the 18 h window. Recession is not modeled.

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
    validate.py            spec 005
  api/                     Priyanshu
    app.py                 spec 006 (FastAPI)
    routing.py             spec 006
    agent.py               spec 007 (Gemini + tools + safety filter)
    photo.py               spec 010 (stretch)
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
Cycle IDs everywhere use the format `YYYYMMDDTHHZ`, e.g. `20240926T18Z`. All times are UTC ISO-8601 with `Z`. Units are SI.

### C1 `data/interim/nwm/<cycle>.parquet` — producer 001
| column | type | notes |
|---|---|---|
| feature_id | int64 | NWM reach = NHDPlusV2 COMID; only AOI reaches |
| lead_h | int8 | 1–18 |
| valid_time | timestamp (UTC) | issue time + lead_h |
| q_cms | float32 | `streamflow`, m³/s |

### C2 `data/interim/rating.parquet` — producer 002
| column | type | notes |
|---|---|---|
| hydro_id | int64 | FIM HydroID |
| feature_id | int64 | NWM reach the HydroID belongs to |
| stage_m | float32 | |
| q_cms | float32 | |
Sorted by `hydro_id, stage_m`. Contains only HydroIDs that intersect the AOI.

### C3 `data/interim/seg_hand.parquet` — producer 003
| column | type | notes |
|---|---|---|
| seg_id | str | `"{u}-{v}-{key}"` from OSMnx |
| hydro_id | int64 | catchment the sample falls in |
| hand_m | float32 | HAND at the sample, metres |
One row per sample point (≤10 m spacing). No rows for `bridge` or `tunnel` segments, or for samples outside the HAND/catchment rasters.

### C4 `data/interim/graph.graphml` — producer 003
OSMnx `network_type="drive"` graph for the AOI buffered by 2 km, EPSG:4326. Every edge carries `seg_id`, `length` (m), `travel_time` (s) from `ox.add_edge_speeds` + `ox.add_edge_travel_times`, plus `name` and `highway` where present.

### C5 `web/data/flood_<cycle>.geojson` — producer 004
FeatureCollection, EPSG:4326, coordinates rounded to 5 dp. **Contains only segments with a non-null `t_uncertain`.**
| property | type | notes |
|---|---|---|
| seg_id | str | joins to C3/C4 |
| name | str \| null | OSM street name |
| t_uncertain | int | first lead hour (1–18) in the uncertain band |
| t_flood | int \| null | first lead hour forecast flooded |
| feature_id | int | controlling reach |
| hand_min_m | float | 2 dp |

### C6 `web/data/cycles.json` — producer 004
```json
{"demo_cycle": "20240926T18Z",
 "cycles": [{"cycle": "20240926T18Z", "issue_time": "2024-09-26T18:00:00Z",
             "valid_times": ["2024-09-26T19:00:00Z", "...18 entries"]}]}
```

### C7 `web/data/aoi.geojson` — producer 003
The AOI polygon (HUC10 0313000112), EPSG:4326.

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
| `GET /health` | — | `{"ok": true, "cycle": "20240926T18Z"}` |
| `GET /status` | `lat, lon, hours=18` | `{"state": STATE, "segments": [{"seg_id","name","state","eta_utc"}], "cycle"}`: worst state within 300 m and within `hours` |
| `GET /route` | `from=lat,lon&to=lat,lon&depart_h=0` | `{"state": "route_found"\|"no_route"\|"out_of_coverage", "geometry": GeoJSON LineString\|null, "minutes": float\|null, "avoided": [seg_id], "map_url": str}` |
| `POST /chat` | `{"sender": str, "text": str, "image_b64": str\|null}` | `{"reply": str}` |
`STATE` ∈ `flooded | uncertain | no_forecast_flooding | out_of_coverage`.
"Now" = lead hour 0 of `demo_cycle` in replay mode. A route removes every edge whose `t_uncertain <= depart_h + ROUTE_BUFFER_H`.

### C10 Map URL — producer 009, consumed by 006/007
`{WEB_BASE}/?cycle=20240926T18Z&t=3&from=lat,lon&to=lat,lon&api={API_BASE}`. All parameters are optional. With `from`, `to` and `api` set, the map calls `/route` and draws the result.

## 5. User-facing state vocabulary (FROZEN)
Every reply from the agent, the API and the map uses exactly these meanings. Wording can be shortened but must keep its meaning.

| state | message template |
|---|---|
| `flooded` | **Do not cross {road}.** Forecast shows water reaching it around {time}. |
| `uncertain` | **{road}: uncertain, treat as impassable** from around {time}. |
| `no_forecast_flooding` | No flooding is forecast on this route through {end_time}. **This is not a safety guarantee.** Conditions change fast; never drive into water. *Turn Around Don't Drown.* |
| `out_of_coverage` | That's outside Noah's coverage (Peachtree Creek watershed, Atlanta). Check local official warnings. |

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
| AOI_HUC10 | `"0313000112"` | WBD |
| HUC8 | `"03130001"` | WBD |
| GAUGE_USGS / GAUGE_NWS_LID / GAUGE_FEATURE_ID | `"02336300"` / `"AANG1"` / `2047989` | NLDI, NWPS |
| MINOR_FLOOD_CMS | `161.4` (5,700 cfs) | NWPS AANG1 |
| HELENE_CYCLES | hourly `20240926T12Z` … `20240927T12Z` | — |
| BASELINE_CYCLE | `20240926T16Z` (gauge at low flow, 4.4 ft) | USGS IV |
| DEMO_CYCLE | `20240926T18Z` (provisional, D5) | — |
| UNCERTAIN_BAND_M | `0.5` | heuristic, see issues |
| ROUTE_BUFFER_H | `1` | — |
| SAMPLE_SPACING_M | `10` | — |
| NWM_URL | `https://storage.googleapis.com/national-water-model/nwm.{YYYYMMDD}/short_range/nwm.t{HH}z.short_range.channel_rt.f{FFF}.conus.nc` | verified Oct 9, 2026 |
| GEMINI_MODEL | from env `GEMINI_MODEL` | check ai.google.dev for the current Flash model |
| API_BASE, WEB_BASE | from env | — |
| paths | `DATA_RAW`, `DATA_INTERIM`, `WEB_DATA` (pathlib, repo-relative) | — |
