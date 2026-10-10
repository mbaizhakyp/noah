# 003 — AOI, road graph, HAND sampling

| | |
|---|---|
| Owner | Margulan |
| Status | Draft |
| Time box | 3 h (step 1 ≤ 45 min, pushed immediately) |
| Depends on | step 1: none · step 2: 002 rasters |
| Produces | C7 `web/data/aoi.geojson`, C4 `data/interim/graph.graphml`, C3 `data/interim/seg_hand.parquet` |

## Goal
Build the drivable road network for the Peachtree Creek watershed and record the HAND values and catchments each road segment passes through.

## Non-goals
Per-hour flood logic (004). Routing (006). Lane-level or elevation-of-bridge-deck modeling.

## Inputs
- WBD HUC10 query (see 002 Inputs) for `0313000112`.
- OSM via `osmnx`.
- 002 rasters: HAND + catchments.

## Outputs
C7, C4, C3, exactly as specified in `docs/02-ARCHITECTURE.md` §4. Also copy `aoi.geojson` to `data/interim/`.

## Behavior
**Step 1: AOI + graph (push immediately; Priyanshu needs it).**
1. Fetch the HUC10 polygon and write C7.
2. `G = ox.graph_from_polygon(aoi_buffered_2km, network_type="drive", retain_all=False)`. Buffer in a metric CRS (EPSG:5070), then return to 4326.
3. `ox.add_edge_speeds(G)`, `ox.add_edge_travel_times(G)`. Set the `seg_id` edge attribute = `f"{u}-{v}-{k}"`.
4. `ox.save_graphml(G, DATA_INTERIM/"graph.graphml")`. Log node and edge counts. `data/` is gitignored, so **if graphml is under 20 MB, copy it to `fixtures/graph.graphml` and push** for Priyanshu. Otherwise share it directly (AirDrop / Drive) and note in PROGRESS.

**Step 2: HAND sampling.**
5. Edges → GeoDataFrame (`ox.graph_to_gdfs(G, nodes=False)`), reprojected to the HAND raster CRS.
6. Drop edges where `bridge` or `tunnel` is truthy. OSMnx values can be a str, a list or NaN; treat any non-null value other than `"no"` as truthy. Log the count dropped.
7. Keep only edges intersecting the AOI (unbuffered). Edges in the buffer stay in the graph for routing but never flood (no HAND rows).
8. Densify: points every `SAMPLE_SPACING_M` along each line, including endpoints (`shapely` `line.interpolate`).
9. Sample both rasters at all points with `rasterio`'s `sample()` (or windowed read + index). Drop nodata samples.
10. Write C3: one row per valid sample `(seg_id, hydro_id, hand_m)`.

## Acceptance criteria
- [ ] Step 1: `graph.graphml` loads with `ox.load_graphml`. Every edge has `seg_id`, `length`, `travel_time`. Node and edge counts logged in PROGRESS.
- [ ] C3 written. Logged: segments in AOI, segments with ≥1 sample, bridges/tunnels excluded, total samples.
- [ ] Spot-check: Northside Dr NW where it meets Peachtree Creek (near the gauge, 33.8203, -84.4076) has samples with low HAND on the approaches. Print them.

## Test
`tests/test_build_segments.py`: a two-edge toy GeoDataFrame (one with `bridge="yes"`, one with `bridge=["yes","no"]`) → the bridge filter drops both bridge edges. The densify function returns points ≤ 10 m apart including both endpoints.

## Fallback
- OSMnx Overpass slow or rate-limited → reduce the buffer to 500 m, or download a Geofabrik Georgia extract and clip.
- Sampling slow → sample only edges within 500 m of a stream (catchment raster pixels with HAND < 10 m). Log it.
