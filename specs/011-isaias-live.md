# 011 — Hurricane Isaias live run (bonus demo)

| | |
|---|---|
| Owner | Margulan |
| Status | Draft |
| Priority | P1 (after the Sat 14:00 E2E milestone) |
| Time box | 2 h, spread across Sat afternoon and the early hours of Sun |
| Depends on | 001, 003, 004, 005 working on Helene. Nothing new from Priyanshu (map scenario switch is in 009, `NOAH_CYCLE` in 006). |
| Produces | C5 for Isaias cycles, C6 `events.isaias`, `web/data/validation_isaias.json` (C8 schema) |

> **Coverage changed to all of Georgia (Priyanshu, Fri Oct 9 ~22:30 ET; D4 / CC6, Margulan to confirm).** "AOI" in this spec now means **the Georgia HUC8s processed so far** (C6 `hucs`), not the Peachtree Creek HUC10. Peachtree Creek / gauge 02336300 stays the **Helene validation** site. See `01-PROJECT_OVERVIEW.md` §Coverage.

## Goal
Run the same pipeline on this weekend's storm. If it flags roads, the demo gets a "while you were hacking, Noah flagged these roads hours ahead, and here's what the creek actually did" segment. Helene stays the main demo regardless.

## Non-goals
New code paths. Anything Helene doesn't already do. Running continuously during judging.

## Known facts (Oct 9, 2026, 8:45 PM ET)
- Isaias (Cat 3, Gulf). Georgia is out of the cone. NWS flood watch for metro Atlanta, 1.5–5 in of rain, mostly early Sat → Sat night, tapering early Sun.
- NWM cycles reach the GCS bucket ~1 h 45 min after cycle time. The bucket keeps them permanently, **so nothing needs downloading ahead of time.**
- 20261009T22Z forecast at feature 2047989: peak ≈ 30 m³/s (1,061 cfs) at 2026-10-10 13Z. That's well below action (3,630 cfs) and minor (5,700 cfs). Its window ends Sat 16Z, before most of the rain.
- Gauge at 2026-10-09 20:00 EDT: 2.08 ft, 18 cfs. Baseline cycle = `20261009T22Z`.

## Behavior
1. Add `EVENTS["isaias"]` to `config.py` (shared file: heads-up). Give 001/004/005 an `--event` flag that maps to the cycle range, baseline and demo cycle.
2. **Sat 12:00–14:00:** `fetch_nwm --event isaias --gauge-only` for every cycle so far. Print the per-cycle forecast peak at the gauge reach.
3. **Decision at Sat 14:00 (log it in PROGRESS):**
   - **GO** if any cycle forecasts ≥ `ACTION_FLOW_CMS` at the gauge reach **or at any Georgia gauge/reach in a processed HUC8 (e.g. Big Creek APHG1, forecast minor flood Sun 8 PM)**, **or** a full-AOI run of 004 gives ≥ 1 flooded segment. Run full AOI for all cycles, then 004, and add `events.isaias` to C6 with `demo_cycle` = the first cycle that flagged roads.
   - **NO-GO:** Isaias appears only in the pitch hook ("this weekend a hurricane put Atlanta under a flood watch"), plus one honest line: "Noah's forecast showed no creek flooding on Peachtree; the gauge agreed." Use that line only if the gauge actually agreed.
4. **Sun 02:00–05:00 (if GO):** `validate --event isaias` once USGS observations cover the peak. Write `validation_isaias.json`. If the event hasn't peaked or the data is incomplete, say so; don't extrapolate.
5. Re-run 001 + 004 on new cycles as they land until Sun 04:00 (video recording).

## Acceptance criteria
- [ ] The Sat 14:00 go/no-go decision and the cycle-peak table are in PROGRESS.
- [ ] If GO: Isaias C5 files exist, C6 has `events.isaias`, and the map scenario switch (009) shows it.
- [ ] If GO: `validation_isaias.json` is produced by the script, with observed values from USGS, not typed in.
- [ ] Helene outputs are unchanged (re-run `pytest` and spot-check one Helene C5 file's segment count).

## Test
Extend `tests/test_validate.py` with one case: `--event` resolves to the right cycle list and baseline.

## Fallback
NO-GO path in step 3. If time is short, Isaias is pitch-hook only.
