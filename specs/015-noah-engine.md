# 015 — Noah engine: all sources → signals → rules → AI assessment

| | |
|---|---|
| Owner | Priyanshu |
| Status | Approved (Priyanshu, Sat Oct 10 ~02:00 ET: "build the fully functional backend… use all the sourced data and have the AI work as the engine") |
| Priority | P0 |
| Time box | 6 h (adapters in tiers; ship tier by tier) |
| Depends on | 006 (routing), `docs/07-DATA_SOURCES.md` (verified endpoints), keys in `.env` (Windy, TomTom, Synoptic, Census, Azure OpenAI) |
| Produces | `noah/sources/` (one adapter per source), `noah/engine.py`, `noah/pipeline/live.py` (hourly live NWM loop), `GET /assess`, `GET /assess/route` |

## Goal
For a **searched area** (fixed 5 km radius) or a **searched route** (1 km corridor), pull every relevant data source we verified, turn the results into standard signals, apply hard safety rules, and have the AI engine (Azure OpenAI `gpt-4.1-mini`) produce a grounded assessment: **conditions now, the next 18 hours road by road, and the next days**, with reasons that cite their sources and a recommended action. Noah is an everyday app: it always uses the latest data, for any day and any weather.

## Non-goals
Training ML models. Statewide browsing (CC6: area or route only). Storing images. A database (Tiger Data is later, J11). Satellite imagery at request time (2–3 days stale).

## Design
1. **Adapter contract** (`noah/sources/<name>.py`): `fetch(ctx) -> list[Signal]`.
   - `ctx` = `{kind: "area"|"route", lat, lon, radius_km | line, buffer_m, bbox, when}`.
   - `Signal` fields:
     - `source` (a docs/07 name), `kind` (`forecast|observation|report|context`)
     - `title`, `detail`, `value` (+ `units`)
     - `valid_from`, `valid_to` (UTC), `lat`, `lon` (optional)
     - `severity` (`info|watch|warning|danger`), `url`
   - Each adapter has a cache TTL and a timeout. Exceptions become a `source_error` entry, never a crash.
2. **Runner** (`noah/sources/__init__.py`): runs all adapters in a thread pool with a total budget of ~10 s. It returns `signals`, `sources_ok`, `sources_failed`, each with timing.
3. **Hard rules** (`engine.rules()`):
   - Road timing comes from C5 (006).
   - TomTom `iconCategory` 11 (flooding) or 8 (road closed) on a segment within 30 m → that segment is blocked for routing.
   - Camera `bucket ≥ curb` → nearby segments become flooded (013).
   - NWS Flash Flood Warning / Flood Warning covering the point → area state at least `uncertain`.
   - Rules can only make things more cautious.
4. **AI engine** (`engine.assess()`): one Azure OpenAI call with the bundle (rule outputs + signals, trimmed to fit) and a strict system prompt:
   - Use only the provided data.
   - Cite source names.
   - §5 vocabulary only; never "safe", "clear" or "passable".
   - Mention 911 when describing danger.
   
   The output is JSON:
   - `now`, `next_18h`, `next_days`: each `{level: low|elevated|high|severe, summary}`
   - `reasons`: `[{text, sources[]}]`
   - `action`, `confidence`
   
   **Number guard:** every number in the output text must appear in the input bundle, or the reply is regenerated once and then falls back to a template built from the rules. The banned-word filter is applied after.
5. **Live loop** (`noah/pipeline/live.py`): every hour, find the newest NWM short-range cycle on GCS (f018 present) → reuse `fetch_nwm.fetch_cycle` + `flood_times.flood_times` → write C5 + append the C6 cycle with `event: "live"`. Keep the last 6 live cycles and prune older files. `--once` or `--every 3600`.

## Sources wired as adapters (tiered; docs/07 numbers)
**Tier 1 (live hazard core):** NWS alerts (#21) · NWPS gauges + official forecasts (#2) · NWPS reach flows, short + medium blend (#1) · USGS latest values (#22) · Synoptic rain (#24) · TomTom incidents (#30) · NWS Local Storm Reports, last 24 h (#27) · NWS gridpoint QPF (#13) · WPC Excessive Rainfall Outlook D1–3 (#15) · Windy cameras + AI vision (#31, 010/013).

**Tier 2 (future + context):** WPC QPF D1–7 (#16) · Flash Flood Guidance (#17) · NHC storms (#19) · HEFS quantiles (#3) · Open-Meteo hourly precip (#20) · NWM high-flow map service (#6) · FEMA flood zone (#55) · NWS LSR archive near point, "flooded here before" (#27) · SeeClickFix flood/pothole reports (#54) · Atlanta storm inlets (#50) · dams upstream (#57).

**Tier 3 (people + news):** CDC SVI + Census ACS no-vehicle households (#77–78) · critical facilities nearby (#80) · NFIP claims by ZIP (#56) · Bluesky posts (#32) · Google News RSS (#33) · NOAA Atlas 14 rarity (#18).

**Build-time only (not per request):** OSM/Overture/GDOT road data, NHDPlus/WBD, 3DEP, HAND, satellite (Sentinel, OPERA, Landsat, GFM, MODIS, Maxar, NAIP), RDD2022, Mapillary, KartaView, NWM retrospective, Stage IV, NBM, NDFD, MRMS raw grids (heavy GRIB; may join later), Storm Events archive.

## Endpoints (C9 additive, CC7)
- `GET /assess?lat=&lon=&cycle=`: area bundle + assessment: `{state, assessment, signals[], sources_ok[], sources_failed[], segments[], cameras[], cycle}`.
- `GET /assess/route?from=&to=&depart_h=&cycle=`: route (006) + corridor bundle + assessment, in the same shape plus `route`.
- `/status` and `/route` stay fast and AI-free.

## Acceptance criteria
- [ ] `uv run python -m noah.pipeline.live --once` writes a C5 for the newest NWM cycle and a C6 entry with `event: "live"`. `/health` shows that cycle.
- [ ] `/assess` for a metro-Atlanta point returns signals from ≥ 10 distinct sources, with the failing ones listed, in < 15 s cold and < 3 s warm.
- [ ] The assessment cites only sources present in `signals`. The number guard passes, or the fallback is used (logged).
- [ ] A Georgia point outside metro Atlanta still gets statewide signals (alerts, gauges, rain, ERO) + `no_road_forecast` for road timing.
- [ ] Unit tests: the adapter error isolation, the rules (upgrade only), the number guard, the banned-word filter.

## Fallback
- AI unavailable → a rules-only template assessment (labeled).
- Any adapter down → listed in `sources_failed`. The answer still returns.
