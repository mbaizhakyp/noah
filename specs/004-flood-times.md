# 004 — Flood times per segment

| | |
|---|---|
| Owner | Margulan |
| Status | Draft |
| Time box | 2 h |
| Depends on | C1 (001), C2 (002), C3 + C4 (003) |
| Produces | C5 `web/data/flood_<cycle>.geojson`, C6 `web/data/cycles.json` |

## Goal
For each forecast cycle, compute when each road segment enters the uncertain and flooded states. Write map- and API-ready files.

## Non-goals
Recession / reopening (parking lot). Depth on the road (we only flag "water reaches it"). Storm-drain flooding.

## Inputs
C1 per cycle, C2, C3, C4 (for geometry and names), `config.BASELINE_CYCLE`, `config.UNCERTAIN_BAND_M`.

## Outputs
C5 per cycle in `HELENE_CYCLES`, plus C6 with `demo_cycle = config.DEMO_CYCLE`.

## Behavior
Algorithm exactly as in `docs/02-ARCHITECTURE.md` §2:
1. `stage(hydro_id, t)`: for each HydroID, `numpy.interp(q, curve.q_cms, curve.stage_m)` using the HydroID's `feature_id` flow from C1. Flow above the curve's max → clamp to the max stage and **log a warning with the count**. (`# ponytail:` clamping understates extreme stage; extrapolating linearly is the upgrade.)
2. Baseline stage per HydroID from `BASELINE_CYCLE` lead 1.
3. Channel-pixel filter: drop C3 samples with `hand_m <= baseline_stage(hydro_id)`.
4. `hand_min[seg_id, hydro_id] = min(hand_m)` over the remaining samples.
5. Per (seg, hydro), over lead_h 0–18 (0 = now): `t_flood` = first lead_h with `stage >= hand_min`; `t_uncertain` = first lead_h with `stage >= hand_min - UNCERTAIN_BAND_M`. Per segment, take the minimum across its HydroIDs. `feature_id` = the reach of the HydroID that set `t_uncertain`.
6. Persistence is implied: we only store first-entry hours, and consumers treat states as sticky.
7. Join geometry and `name` from C4 edges. Keep only segments with non-null `t_uncertain`. Round coords to 5 dp, `hand_min_m` to 2 dp, and write C5.
8. Write or update C6 with all processed cycles and their 19 `valid_times` (index = lead_h, 0–18).
9. Log per cycle: n uncertain, n flooded, earliest `t_flood`.

## Acceptance criteria
- [ ] `uv run pytest tests/test_flood_times.py` passes.
- [ ] C5 exists for every Helene cycle and validates against the contract (a small check prints property names and types for one feature).
- [ ] Sanity: the low-flow cycle `BASELINE_CYCLE` produces ~0 flooded segments (expected after the channel filter). Print the count.
- [ ] Sanity: the demo cycle produces flooded segments clustered along Peachtree and Nancy Creek, viewed on the map (009) or a quick `geopandas.plot`. Screenshot goes in PROGRESS.
- [ ] Each C5 file is under 20 MB.

## Test
`tests/test_flood_times.py` with a hand-built 2-HydroID rating table, 3 segments and an 18-hour flow series. Asserts:
- a segment whose hand_min is crossed at hour 5 gets `t_flood=5`;
- a segment within the band gets `t_uncertain` < `t_flood`;
- a segment never reached is absent;
- a channel sample (hand ≤ baseline stage) is ignored, so a culvert segment uses its approach elevation.

## Fallback
If C2 or C3 are late, run with only the gauge reach and its HydroIDs to produce a partial C5 for the demo neighborhood. Note it in PROGRESS.
