# Noah

**Know before the water does.**

Noah tells you which roads will flood, and when, before the water gets there: street by street, up to 18 hours ahead, by text. It routes you around flooded roads, tells you when to leave, and texts you first when a road you use is about to go under. Cities and businesses get the same forecast as an operations board: who gets cut off, why a road floods, what to fix first.

> Built at Hacklanta 2026 (Oct 9–11, Georgia State University) · Track: **Social Good** · Side challenge: **Photon (Agents in iMessage)**

## Why
More than half of flood drownings happen in a vehicle (CDC figure used by NWS "Turn Around Don't Drown"). Flood warnings cover whole counties. Map apps reroute only after a road is reported closed. NOAA's road flood thresholds cover 15,289 major-road segments in our area, not the side streets where people live.

## What it does
| Screen | For | What they get |
|---|---|---|
| **iPad** (`/ipad/`) | Everyday drivers | Work, home, deliveries: a route around flooded roads, "leave by" times, the best stop order |
| **iMessage** | Anyone, no app | "Can I drive home from Midtown at 6 PM?" in plain language; `alerts on` for unprompted warnings on watched routes |
| **Noah Operations** (`web/dispatch.html`) | Cities and businesses | City: facilities cut off from every open road, "Why" a road floods, what to fix first. Deliveries: best departure hour. Site check: how often a location gets cut off |

Noah never says a road is "safe", "clear" or "passable". Uncertain counts as impassable, every answer says it is not a safety guarantee, and it points to 911.

## Proof
- **Hurricane Helene (Sep 26, 2024), recorded:** NOAA's 8 AM forecast gave **13.2 h** of warning before Peachtree Creek reached flood stage (9:15 PM). Noah flagged Windsor Parkway from 10 PM; the city closed it about 10:15 PM (Appen Media, 11Alive).
- **Hurricane Isaias (Oct 9–10, 2026), live:** Noah ran all weekend. The run it had at 11:50 PM Friday called Saturday's peaks on Peachtree Creek (−12%, 10.9 h ahead), the Chattahoochee (−8%, 13.2 h) and Nancy Creek (+9%, 10.7 h). South Fork Peachtree Creek was under-forecast (−78%). 9 of 11 watched routes were warned ahead. Data: `web/data/isaias_validation.json`, `web/data/route_watch.json`.

## How it works
1. **Forecast:** NOAA National Water Model short-range streamflow for every creek reach, hourly, 18 h ahead (public GCS bucket), refreshed by a live loop.
2. **Road thresholds:** NOAA OWP FIM per-road thresholds for major roads, plus Noah's own thresholds for 62,202 residential segments computed from FIM HAND rasters and rating curves (checked against NOAA where both exist: no bias, correlation 0.74). Road-level timing covers 4 metro Atlanta watersheds (1,426 km²).
3. **Timing:** a segment is "uncertain" when the forecast flow nears its threshold and "flooded" when it passes it; the first hour of each is stored per segment (`web/data/flood_<cycle>.geojson`).
4. **Routing:** OpenStreetMap drive network (OSMnx); flooded and uncertain segments are removed hour by hour.
5. **Live checks:** NWS warnings, traffic incidents, rain gauges and traffic cameras (a camera counts only when water shows in two AI checks).
6. **Delivery:** an Azure OpenAI tool-calling agent (`check_route`, `check_area`, `remember_place`) behind `POST /chat`, reached over iMessage through Photon Spectrum (`bot/`, `spectrum-ts`). A route watch texts on change.

Details: `docs/02-ARCHITECTURE.md`.

## Run it
```bash
uv sync
cp .env.example .env                                         # add your own keys
uv run uvicorn noah.api.app:app --port 8000                  # API + web pages
uv run python -m noah.pipeline.live --every 900 --keep 48    # live forecast loop
uv run python -m noah.pipeline.route_watch --every 300       # route alerts
cd bot && npm install && npm start                           # iMessage relay
scripts/demo_mode.sh                                         # Helene replay on :8100
uv run pytest && (cd bot && npm test)                        # tests
```
Pages: `/` opens Noah Operations (`/dispatch.html`); `/ipad/` is the iPad app (needs the snapshot from release `demo-snapshot-20240926T12Z`, see `docs/10-IPAD_DEMO_SETUP.md`). One-time data build: `fetch_hand` → `build_segments` → `flood_times` → `validate` (`docs/05-PROGRESS.md`).

## Team
- **Margulan Baizhakyp:** forecast pipeline (NWM, HAND thresholds, residential roads, validation), live loop, route watch and alerts, iMessage agent and relay, Noah Operations console.
- **Priyanshu Sethi:** web map, trip planner and routing API, live-checks engine, iPad app. Priyanshu competes separately in the Fintech track with another project.

## Disclosures
- The repository started at Hacklanta on Fri Oct 9, 2026, 8:34 PM ET.
- Data: NOAA National Water Model; NOAA OWP FIM HAND rasters, rating curves and road thresholds (CIROH bucket); USGS water data and NLDI; NWS; OpenStreetMap via OSMnx and Overpass; Windy Webcams; TomTom Traffic; Synoptic.
- Libraries: FastAPI, GeoPandas, OSMnx, NetworkX, rasterio, xarray, pandas, MapLibre GL, Lucide, spectrum-ts.
- AI: Azure OpenAI (`gpt-4.1-mini`) at runtime for the agent and camera checks; Claude Code as a coding assistant.
- Camera images are fetched live and never stored in the repo.
- Noah models creek and river overflow, not storm drains. It is not a replacement for official warnings or 911.
