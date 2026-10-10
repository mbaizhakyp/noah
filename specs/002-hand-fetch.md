# 002 — FIM HAND + rating curves fetch

| | |
|---|---|
| Owner | Margulan |
| Status | Draft |
| Time box | 2 h (most of it is download wall time) |
| Depends on | AWS account with credentials (`AWS_PROFILE` in `.env`) |
| Produces | rasters in `data/raw/hand/03130001/`, C2 `data/interim/rating.parquet` |

## Goal
Get the HAND raster, catchment (HydroID) raster and synthetic rating curves for HUC8 03130001, and write the AOI's rating curves as C2.

## Non-goals
Running the FIM inundation pipeline. Merging branches (MVP uses one branch; see R2). Other HUC8s.

## Inputs
- Bucket `s3://noaa-nws-owp-fim/` — **Requester Pays** (verified Oct 9, 2026). Every call needs `--request-payer requester`.
- `data/interim/aoi.geojson` (C7, from 003 step 1) to filter HydroIDs. If 003 hasn't run, fetch the HUC10 polygon directly: `https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/5/query?where=huc10%3D%270313000112%27&outFields=huc10,name&returnGeometry=true&outSR=4326&f=geojson`.

## Outputs
- `data/raw/hand/03130001/<branch>/` containing the HAND raster, catchment raster and hydroTable CSV, exactly as named in the bucket.
- C2.
- **Update this spec's "Discovered layout" section** with the real paths and the version used.

## Behavior
1. Discover the layout (layout is **(verify)**: expected `hand_fim/fim_4_x_x_x/<HUC8>/branches/<branch_id>/`):
   `aws s3 ls --request-payer requester s3://noaa-nws-owp-fim/hand_fim/` → choose the latest `fim_4_*` → `.../03130001/branches/`.
2. Choose the branch: **branch `0`** for MVP, which in FIM4 should carry the full HUC stream network **(verify by checking that its catchment raster covers Peachtree and Nancy Creek)**. If branch 0 doesn't cover the small creeks, use the level-path branch(es) that do and log it in R2.
3. Download only three files: `rem_zeroed_masked_<b>.tif` (HAND, metres), `gw_catchments_reaches_filtered_addedAttributes_<b>.tif` (HydroID per pixel), `hydroTable_<b>.csv`. Names are **(verify)**.
4. Rating table: read the CSV and keep `HydroID, feature_id, stage, discharge_cms` (names **(verify)**; FIM has had `discharge_cms` vs calibrated columns. Use the column FIM itself uses for inundation and note which). Filter to HydroIDs whose catchment pixels intersect the AOI (rasterize a mask or `rasterio.features.shapes`; a bbox prefilter is fine). Rename to C2 and sort.
5. Check: each HydroID has a monotonic `stage_m` vs `q_cms` curve. Log any HydroIDs dropped for being non-monotonic.

## Discovered layout
_Fill in after step 1: version, exact keys, file sizes, CRS, resolution._

## Acceptance criteria
- [ ] The three files exist locally. `rasterio` opens both rasters, and the CRS/resolution are printed and recorded above.
- [ ] `rating.parquet` matches C2. It includes HydroIDs whose `feature_id` = 2047989. Row count logged.
- [ ] A quick plot or print of the rating curve at the gauge reach looks physically sane (stage rising with q), pasted into `05-PROGRESS.md`.

## Test
`tests/test_fetch_hand.py`: a tiny hydroTable DataFrame (two HydroIDs, one non-monotonic) → the cleaning function returns C2 columns and dtypes and drops the bad curve.

## Fallback
- Requester-pays blocked → FIMserv (`github.com/sdmlua/fimserve`) hosted HAND for FIM 4.5/4.8 **(verify access)**.
- Nothing usable by Sat 04:00 → build HAND for the HUC10 from a USGS 3DEP 10 m DEM with `pysheds` (fill → flowdir → accumulation → stream threshold → HAND), one "catchment" per NHD reach, and a single rating curve at the gauge from USGS measurements. Record this as a major deviation in docs.
