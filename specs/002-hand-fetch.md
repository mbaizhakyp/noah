# 002 — FIM HAND + rating curves fetch

| | |
|---|---|
| Owner | Margulan |
| Status | Draft |
| Time box | 1 h (about 250 MB of downloads) |
| Depends on | — (public bucket, **no AWS account needed**) |
| Produces | rasters in `data/raw/hand/03130001/`, C2 `data/interim/rating.parquet` |

## Goal
Get the HAND raster, catchment (HydroID) raster and synthetic rating curves for HUC8 03130001, and write the AOI's rating curves as C2.

## Non-goals
Running the FIM inundation pipeline. Merging branches (MVP uses branch 0; see R2). Other HUC8s. Using FIMserv's code: we download its **public data only**.

## Inputs
- **Public CIROH bucket, OWP HAND-FIM v4.9.9.0** (hosted by the FIMserv project, github.com/sdmlua/fimserve). Anonymous access, verified Oct 9, 2026:
  - S3: `s3://ciroh-owp-hand-fim/hand_fim_4_9_9_0/03130001/` (`aws s3 sync ... --no-sign-request` works without an account)
  - HTTPS: `https://ciroh-owp-hand-fim.s3.amazonaws.com/hand_fim_4_9_9_0/03130001/<file>`. Plain `httpx` is enough; no AWS CLI needed.
- `data/interim/aoi.geojson` (C7, from 003 step 1) to filter HydroIDs. If 003 hasn't run, fetch the HUC10 polygon directly: `https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/5/query?where=huc10%3D%270313000112%27&outFields=huc10,name&returnGeometry=true&outSR=4326&f=geojson`.

## Outputs
- `data/raw/hand/03130001/` containing the files below, with their bucket names kept.
- C2.

## Discovered layout (Oct 9, 2026, listed anonymously)
HUC 03130001 has 461 files, 0.79 GB in total. Download only these:

| File (relative to `hand_fim_4_9_9_0/03130001/`) | Size | Use |
|---|---|---|
| `branches/0/rem_zeroed_masked_0.tif` | 106.0 MB | HAND raster (metres) |
| `branches/0/gw_catchments_reaches_filtered_addedAttributes_0.tif` | 3.7 MB | HydroID per pixel |
| `branches/0/hydroTable_0.csv` | 110.6 MB | rating curves for branch 0 |
| `hydrotable.parquet` | 3.3 MB | HUC-level table, probably merged across branches **(verify its columns and whether it covers branch 0's HydroIDs; if so, prefer it over the 110 MB CSV)** |
| `osm_bridge_centroids.gpkg` | 1.4 MB | optional: cross-check our OSM bridge filter (003) |

Also present, not needed for the MVP: `osm_roads_fimpact.csv` / `osm_roads_subset.gpkg`. FIM 4.9 appears to compute road impacts itself. **Inspect `osm_roads_fimpact.csv` (columns + 5 rows) and note in R15 what it contains.** It affects how we describe our contribution, not the build.

## Behavior
1. Download the files above with `httpx` (streamed, resume-safe: skip a file if it exists with the right size). Log sizes.
2. Open both rasters with `rasterio`. Record CRS, resolution and bounds in PROGRESS (expected EPSG:5070, ~10 m, **(verify)**). Check that the catchment raster covers Peachtree and Nancy Creek inside the AOI. If branch 0 doesn't cover the small creeks, log it in R2 and add the covering branch.
3. Rating table: read `hydrotable.parquet` (or `hydroTable_0.csv`). Keep `HydroID, feature_id, stage, discharge_cms`; column names are **(verify)**. If both raw and calibrated discharge columns exist, use the one FIM itself uses for inundation and note which. Filter to HydroIDs whose catchment pixels intersect the AOI (a bbox prefilter, then rasterized mask). Rename to C2 and sort.
4. Check each HydroID's curve is monotonic (stage vs q). Log any dropped.

## Acceptance criteria
- [ ] The files exist locally. CRS/resolution/bounds of both rasters are printed and recorded in PROGRESS.
- [ ] `rating.parquet` matches C2, includes HydroIDs whose `feature_id` = 2047989, and its row count is logged.
- [ ] A print or plot of the rating curve at the gauge reach looks physically sane (stage rising with q), pasted into PROGRESS.
- [ ] `osm_roads_fimpact.csv` columns + 5 rows noted in R15.

## Test
`tests/test_fetch_hand.py`: a tiny hydroTable DataFrame (two HydroIDs, one non-monotonic) → the cleaning function returns C2 columns and dtypes and drops the bad curve.

## Fallback
- CIROH bucket unavailable → NOAA's own bucket `s3://noaa-nws-owp-fim/hand_fim/` (**Requester Pays**: needs an AWS account with a card, `--request-payer requester`).
- Nothing usable by Sat 04:00 → build HAND for the HUC10 from a USGS 3DEP 10 m DEM with `pysheds` plus a single rating curve at the gauge from USGS measurements. Record this as a major deviation.
