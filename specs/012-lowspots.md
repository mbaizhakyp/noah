# 012 — Street low spots (stand-in for storm drains and sewers)

| | |
|---|---|
| Owner | Margulan |
| Status | Draft |
| Priority | P3 stretch. Start only if 004 is done by Sat 12:00 and 005 part C is on track. |
| Time box | 2 h |
| Depends on | C4 (graph), a DEM |
| Produces | C11 `web/data/lowspots.geojson` |

> **Coverage changed to all of Georgia (Priyanshu, Fri Oct 9 ~22:30 ET; D4 / CC6, Margulan to confirm).** "AOI" in this spec now means **the Georgia HUC8s processed so far** (C6 `hucs`), not the Peachtree Creek HUC10. Peachtree Creek / gauge 02336300 stays the **Helene validation** site. See `01-PROJECT_OVERVIEW.md` §Coverage.

## Goal
Answer "you only track creeks; what about storm drains and sewers?" with something real. We can't get Atlanta's storm-drain network in time (no open dataset found; a records request takes ~3 business days). Instead, flag **road segments that sit in terrain depressions**, such as underpasses and street sags. Those are the places water pools when drains are overwhelmed.

## Non-goals
Forecasting storm-drain or sewer flooding. Pipe-network or SWMM modeling. Timing. Changing routing or states (MVP shows this layer for information only).

## Inputs
- DEM: first check whether the FIM HUC8 outputs (002) include a DEM, e.g. `dem_meters_<b>.tif` **(verify)**. Otherwise use USGS 3DEP 1/3 arc-second (~10 m) for the AOI bbox + 500 m via `py3dep` or a TNM download. 3DEP is bare-earth, so bridges are removed and **underpasses show up as depressions**. Underpasses are real flood traps, so keep them.
- C4 edges.

## Outputs
C11 exactly.

## Behavior
1. Clip the DEM to the AOI + 500 m.
2. Fill depressions with whichever installs cleanly: `pysheds` (`fill_pits` + `fill_depressions`) or `whitebox` `FillDepressions`. `depth = filled − dem`.
3. Keep cells with `depth ≥ 0.2 m`. Label connected regions (`scipy.ndimage.label`) and keep regions ≥ 200 m². Polygonize with `rasterio.features.shapes`.
4. Intersect with C4 edges (reprojected to the DEM CRS). Per segment, record `depth_max_m` and `pond_area_m2`.
5. Write C11. Log the segment count and the 10 deepest.
6. `# ponytail:` a 10 m DEM misses curb-scale sags. 3DEP 1 m lidar for Atlanta is the upgrade.

## Acceptance criteria
- [ ] C11 exists, matches the contract, and is under 5 MB.
- [ ] Spot-check: the 3 deepest segments are viewed on satellite imagery and noted in PROGRESS (underpass / sag / artifact).
- [ ] No changes to C5, routing or agent states.

## Test
`tests/test_lowspots.py`: a 5×5 synthetic DEM with a 3×3 pit 0.5 m deep → one region, `depth_max ≈ 0.5`. A line through it is flagged; a line beside it isn't.

## Fallback
Cut it. In Q&A: "storm-drain flooding is the next layer; we tried a terrain low-spot proxy and ran out of time" (only if we actually tried).
