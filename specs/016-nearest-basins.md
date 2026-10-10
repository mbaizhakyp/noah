# 016 — Road-level timing for the basins around metro Atlanta (then on demand)

| | |
|---|---|
| Owner | Margulan (pipeline, parts A–B) · Priyanshu (API + map, part C) |
| Status | **Approved** (Margulan, Sat Oct 10 ~02:40 ET, relayed by Priyanshu). **A + C done Sat 02:45** on Priyanshu's machine: 6 basins built (`north, ocmulgee, flint, west, etowah, oconee`, defined as HUC10 lists in `config.BASINS`), live loop merges them, per-basin routing. Margulan reviews the pipeline diff. **B (on demand) not started.** |
| Time box | A: 1 h plumbing + overnight compute · B: 30 min · C: 2 h (stop at 1.5×, log in 06) |
| Depends on | 002, 003, 004, 015 (all done for HUC8 03130001); R18 in `06-CURRENT_ISSUES.md` |
| Produces | C5 `flood_<cycle>.geojson` and C7 `aoi.geojson` covering several HUC8s; C4 graphs per HUC8; no contract changes |

## Goal
Road-by-road flood timing (Do not cross / Uncertain from ~hour) for the river basins that touch the metro Atlanta counties, not only the four Upper Chattahoochee sub-basins, refreshed hourly by the live loop like metro is today. Then let any other Georgia basin build itself the first time someone asks for it. The demo needs it because "Noah covers Georgia" currently means statewide hazards everywhere but road timing only inside one basin; a judge who types Conyers, Peachtree City or Woodstock gets `no_road_forecast`.

## Non-goals
Statewide routing in one graph (R18: won't fit in 16 GB). Recession. Changing any C-contract. Processing all 53 HUC8s before the freeze (that is the on-demand path, part B, not a batch).

## Inputs
- Public CIROH HAND bucket, per HUC8 (spec 002 file list, ~115–140 MB per basin).
- WBD HUC8/HUC10 polygons (`hydro.nationalmap.gov` WBD MapServer, as in 002).
- OSM roads: **(verify)** switch from per-basin Overpass pulls to one Geofabrik `georgia-latest.osm.pbf` (~300 MB) read with `pyrosm` or `osmnx.graph_from_xml`, to avoid Overpass rate limits across many basins.
- NWM short-range files already fetched hourly by the live loop (CONUS-wide, nothing new).
- `noah/config.py`: `HUC8`, `AOI_HUC10S`, `FIM_BASE` (currently single-valued).

## Outputs
- `data/raw/hand/<huc8>/…` per basin; `data/interim/<huc8>/{graph.graphml, rating.parquet, seg_thresholds.parquet}` per basin **(verify** layout with Margulan; today these files sit unprefixed in `data/interim/`).
- C7 `web/data/aoi.geojson`: one feature per processed HUC8 (`huc8` property), which `routing.coverage()` already unions to decide `no_road_forecast`.
- C5 per cycle: one `flood_<cycle>.geojson` covering all processed basins (or one per basin merged by the loop; keep the contract).
- Part C: `/status` and `/route` answers inside any processed basin; `/route` loads the basin graph on demand.

## Behavior
**A. Nearest basins first (Margulan).** Rollout order, nearest to the demo area first; HUC8 codes **(verify each against WBD before downloading)**:
1. The remaining 8 HUC10s of **03130001 Upper Chattahoochee** (north metro: Lake Lanier, Forsyth, Hall).
2. **03070103 Upper Ocmulgee** — Yellow and South rivers: east DeKalb, south Gwinnett, Rockdale, Henry, Clayton. Already #2 in `01` §Coverage; action-stage forecast for Isaias.
3. **03130005 Upper Flint** — south Fulton, Clayton, Fayette, Peachtree City.
4. **03150104 Etowah** — Cherokee, north Cobb, Woodstock.
5. **03070101 Upper Oconee** — northeast Gwinnett, Athens side.
6. **03130002 Middle Chattahoochee–Lake Harding** — Douglas, Coweta, Carroll.
Steps per basin, reusing the existing modules with `HUC8` made a parameter: `fetch_hand` → `build_segments` (graph + thresholds, incl. CC4 residential branches) → `flood_times` for the newest cycle → append the basin to C7. Then the live loop (015) runs `flood_times` for every processed basin each hour. Run 2–3 basins in parallel; metro peaked at ~1.8 GB RAM, so three at once fit alongside the API and loop on a 16 GB machine.

**B. On demand with a cache (Margulan + Priyanshu).** A `/status` or `/route` call inside Georgia but outside C7 enqueues that HUC8 (one worker, one basin at a time, same steps as A). The response stays `no_road_forecast` and adds `building: {huc8, eta_min}` **(contract addition: needs both humans, CC proposal in 06)**; the map and agent say "Building the road-by-road forecast for this basin, about N min." When the job finishes, the basin joins C7 and the loop. Pre-warm every basin used on stage.

**C. API + map (Priyanshu).** `routing.py` keeps one in-memory graph per basin behind a small LRU (2 graphs) and picks the basin by the request point; trips that cross basins route in the basin holding the origin and say so. The map's `no_road_forecast` branch shows the `building` notice when present.

## Acceptance criteria
- [ ] `uv run python -m noah.pipeline.fetch_hand --huc8 03070103` downloads the basin and writes its rating curves (prints row counts).
- [ ] `uv run python -m noah.pipeline.build_segments --huc8 03070103` writes the basin graph and thresholds; log node/edge/segment counts in 05.
- [ ] `uv run python -m noah.pipeline.flood_times` writes C5 for the newest cycle covering every basin in C7.
- [ ] `curl "$API/status?lat=33.667&lon=-84.017"` (Conyers, Upper Ocmulgee) returns `state` ≠ `no_road_forecast` with segments.
- [ ] `uv run pytest -q` passes; the metro numbers for the current cycle do not change.
- [ ] Peak RAM during the live loop stays under ~6 GB with the API running (`/usr/bin/time -l`).

## Test
`tests/test_basins.py`: with two tiny fixture basins in C7, `routing.coverage()` unions both; `flood_index(cycle)` includes segments from both; `/status` on a point in the second basin returns its segments.

## Fallback
Ship part A for Upper Ocmulgee only (the Isaias rain target) and keep `no_road_forecast` elsewhere. If OSM-from-PBF fails, use Overpass per basin with a sleep between calls. If RAM is the limit, process basins sequentially and keep only the metro graph loaded for routing.
