# 003 — AOI, road graph, NOAA per-road thresholds

| | |
|---|---|
| Owner | Margulan |
| Status | Approved (Margulan, Fri 22:15; step 2 rewritten for CC3) |
| Time box | 1.5 h (step 1 ≤ 45 min, pushed immediately) |
| Depends on | step 1: `data/interim/aoi.geojson` (fetched by 002) · step 2: 002's `osm_roads_fimpact.csv` |
| Produces | C7 `web/data/aoi.geojson`, C4 `data/interim/graph.graphml`, C3 `data/interim/seg_thresholds.parquet` |

## Goal
Build the drivable road network for the Peachtree Creek watershed and attach NOAA's flow threshold for each road segment, i.e. the flow at which it gets wet.

## Non-goals
Per-hour flood logic (004). Routing (006). Our own HAND sampling (replaced by CC3; NOAA's thresholds come from the same HAND data).

## Inputs
- AOI polygon (HUC10 0313000112) from `data/interim/aoi.geojson`.
- OSM via `osmnx` 2.x.
- `data/raw/hand/03130001/osm_roads_fimpact.csv`: columns `osmid, highway, name, huc8, osmid_catchid, HydroID, feature_id, order_, branch, threshold_hand, threshold_discharge, threshold_hand_ft, threshold_discharge_cfs` (verified Oct 9).

## Outputs
C7, C4, C3, exactly as specified in `docs/02-ARCHITECTURE.md` §4.

## Behavior
**Step 1: AOI + graph (push immediately; Priyanshu needs it).**
1. Copy the AOI to C7.
2. `ox.graph_from_polygon(aoi buffered 2 km in EPSG:5070, network_type="drive", retain_all=False)`.
3. `ox.routing.add_edge_speeds`, `ox.routing.add_edge_travel_times`. Set the `seg_id` edge attribute = `f"{u}-{v}-{k}"`.
4. `ox.save_graphml` to C4. If it's under 20 MB, also copy to `fixtures/graph.graphml` and push for Priyanshu.

**Step 2: thresholds (CC3).**
5. Edges → GeoDataFrame. Keep edges intersecting the unbuffered AOI. Buffer edges stay in the graph for routing but never flood.
6. Drop edges whose `bridge` or `tunnel` tag is truthy (a str other than "no", or a list containing one).
7. Explode `osmid` lists. Inner-join to fimpact on `osmid`.
8. Drop rows with `threshold_hand < MIN_ROAD_HAND_M` (0.3 m): road at channel level, a crossing artifact. Log the count.
9. Write C3. Log: AOI edges, bridges/tunnels, segments with a threshold (match rate), artifacts dropped.

**Step 3: residential streets (CC4, approved by Margulan Fri 22:55 "if it adds meaningfully"; done 22:38).**
NOAA's list covers only motorway/trunk/primary/secondary/tertiary. Residential streets (70% of our edges) are missing, and they're where Helene flooded homes (Sagamore Dr, Bohler Rd, Peachtree Battle area). Compute thresholds for them ourselves, the same way NOAA does for major roads:
10. AOI edges with no NOAA row, no bridge/tunnel tag → densify every `SAMPLE_SPACING_M` (10 m) → sample each branch's HAND (int16 **mm**) and catchment rasters, for branch 0 + the 4 AOI level-path branches in `config.FIM_BRANCHES` (HydroID = branch prefix·10000 + value).
11. Per (segment, HydroID): `threshold_hand` = min HAND over samples ≥ `MIN_ROAD_HAND_M` (same crossing floor as NOAA rows). Skip if > 25 m (NOAA's own cutoff).
12. `threshold_q` = discharge at `threshold_hand` on that HydroID's branch-0 curve. Skip if above the curve's range.
13. Append to C3 with `branch_id = 0` and a new column `source = "noah"` (NOAA rows get `source = "noaa"`; additive, CC4). Log counts by source.
Time box 1 h. Test: densify spacing + a 3-sample toy segment → threshold = min HAND above the floor.

## Acceptance criteria
- [ ] Step 1: `graph.graphml` loads with `ox.load_graphml`. Every edge has `seg_id`, `length`, `travel_time`. Node/edge counts in PROGRESS.
- [ ] C3 written with the logged counts. The match rate (AOI non-bridge edges with ≥1 threshold) is in PROGRESS. If it's below 50%, open an issue (OSM way ids may have changed since FIM was built; fallback below).
- [ ] Spot-check: Northside Dr NW near the gauge (33.8203, -84.4076) has a threshold of roughly 277–367 m³/s.

## Test
`tests/test_build_segments.py`: the bridge tag filter handles str/list/NaN. `edge_thresholds()` drops bridge edges, explodes osmid lists, joins thresholds, and drops rows below the floor.

## Fallback
- Overpass slow or rate-limited → reduce the buffer to 500 m, or use a Geofabrik Georgia extract.
- Low osmid match rate → spatial join of unmatched edges to `osm_roads_subset.gpkg` (same bucket folder) within 5 m.
