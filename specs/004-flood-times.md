# 004 — Flood times per segment

| | |
|---|---|
| Owner | Margulan |
| Status | Approved (Margulan, Fri 22:15; rewritten for CC3) |
| Time box | 1.5 h |
| Depends on | C1 (001), C3 + C4 (003), FIM `hydrotable.parquet` (002) |
| Produces | C5 `web/data/flood_<cycle>.geojson`, C6 `web/data/cycles.json` |

## Goal
For each forecast cycle, compute when each road segment enters the uncertain and flooded states, and write map- and API-ready files.

## Non-goals
Recession / reopening (parking lot). Water depth on the road. Storm-drain flooding.

## Inputs
C1 per cycle, C3, C4 (geometry and names), `hydrotable.parquet` (all branches, for the uncertain band), `config.BASELINE_CYCLE`, `UNCERTAIN_BAND_M`.

## Outputs
C5 per cycle in the event, plus C6 with `demo_cycle = config.DEMO_CYCLE` (`20240926T12Z`).

## Behavior
Exactly `docs/02-ARCHITECTURE.md` §2:
1. Per C3 row: `uncertain_q = interp(max(threshold_hand − band, 0.5·threshold_hand), curve.stage → curve.q)` on that row's (HydroID, branch) curve. If the curve is missing, `uncertain_q = threshold_q` (no band) and log the count.
2. Baseline guard: drop rows whose `threshold_q ≤ q(feature_id, BASELINE_CYCLE, lead 1)`. Log the count.
3. Per cycle: build Q[feature_id, lead 0–18]. For each row, `t_flood` = first lead with `q ≥ threshold_q` and `t_uncertain` = first lead with `q ≥ uncertain_q`, vectorized. Per segment, take the minimum over rows. `feature_id` = the row that set `t_uncertain`. `hand_min_m` = min `threshold_hand`.
4. Keep segments with non-null `t_uncertain`. Join geometry + `name` from C4 edges. Round coords to 5 dp and write C5.
5. Write C6: every processed cycle with 19 `valid_times` (index = lead_h), `demo_cycle`, and `events.helene`.
6. Log per cycle: n uncertain, n flooded, earliest `t_flood`.

## Acceptance criteria
- [ ] `uv run pytest tests/test_flood_times.py` passes.
- [ ] C5 exists for every Helene cycle and matches the contract (print property names/types for one feature).
- [ ] `BASELINE_CYCLE` gives ~0 flooded segments. Print the count.
- [ ] The demo cycle's flooded segments sit along Peachtree / Nancy Creek. Check with a quick plot or the map; screenshot in PROGRESS.
- [ ] Each C5 file is under 20 MB.

## Test
`tests/test_flood_times.py`: 2 reaches, 3 C3 rows, a 19-hour flow series. Asserts:
- a row crossed at hour 5 gives `t_flood = 5`;
- the uncertain band gives `t_uncertain < t_flood`;
- a never-reached segment is absent;
- a row wet at baseline flow is dropped;
- the per-segment minimum across rows.

## Fallback
If C3 is late: thresholds for gauge-reach roads only, from fimpact directly (feature_id 2047989) → partial C5 for the demo neighborhood.
