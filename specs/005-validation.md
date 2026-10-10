# 005 — Validation: lead time + street truth

| | |
|---|---|
| Owner | Margulan |
| Status | Approved (Margulan, Fri 22:05) |
| Time box | 3 h (part A ≤ 45 min before midnight) |
| Depends on | C1 (gauge-only is enough for part A), C5 for part C |
| Produces | C8 `web/data/validation.json`, `web/data/validation.png`, final `DEMO_CYCLE` (D5) |

## Goal
Produce the one honest number for the pitch: **how many hours before Peachtree Creek reached flood stage did Noah's input forecast say it would.** Then back it with 2–3 real streets.

## Non-goals
Full skill statistics, other gauges, or claims about road flooding we can't cite.

## Inputs
- USGS IV, verified Oct 9, 2026 (follows a redirect to `nwis.waterservices.usgs.gov`): `https://waterservices.usgs.gov/nwis/iv/?sites=02336300&parameterCd=00065,00060&startDT=2024-09-26T00:00-04:00&endDT=2024-09-28T00:00-04:00&format=json`
- NWS thresholds for AANG1 (NWPS `https://api.water.noaa.gov/nwps/v1/gauges/02336300`): action 13 / minor 17 / moderate 18 / major 20 ft = 3630 / 5700 / 7000 / 7800 cfs.
- Known observed values (recomputed by the script, not hardcoded): minor up 2024-09-27 01:15Z, major up 03:45Z, stage peak 23.75 ft at 12:15Z, Q peak 20,000 cfs at 09:45Z.
- C1 at feature 2047989 for all Helene cycles.

## Outputs
C8, a chart PNG, and the final `DEMO_CYCLE` written to `config.py` (shared file: heads-up to Priyanshu).

## Behavior
**Part A (before midnight, go/no-go).**
1. Fetch the IV data and compute the observed threshold crossings (first sample ≥ threshold after one below).
2. For each cycle, compute the forecast peak (q, time) and the first valid time where q ≥ `MINOR_FLOOD_CMS` (or null).
3. `first_warning_cycle` = the earliest cycle with a non-null crossing. `lead_time_h = observed minor_cross_utc − issue_time(first_warning_cycle)`.
4. Chart: observed Q (cfs and m³/s) plus each cycle's forecast trace, with threshold lines. Save the PNG.
5. **Go/no-go rule:** GO if `first_warning_cycle` is issued ≥ 3 h before the observed minor crossing (≤ 2024-09-26T22Z). Otherwise trigger B1's fallback. Set `DEMO_CYCLE` = `first_warning_cycle` (if it is earlier than 18Z, keep 18Z for a cleaner story; log the choice).

**Part C (after 004).**
6. Street truth: find 2–3 streets in HUC10 0313000112 with **citable, dated** public photos or news showing flooding on Sep 27, 2024. For each, record the street, source URL, and whether C5 for `DEMO_CYCLE` flags it and at what hour. **Do not include any street we can't cite.** Add these to C8 under `"streets": [{"name","source_url","flagged":bool,"t_flood_local":str|null}]` (an additive field; announce it in PROGRESS).
7. Write C8.

## Acceptance criteria
- [ ] Part A prints the cycle table + lead time, and the PNG exists. Pasted into PROGRESS **before 00:00 Sat**.
- [ ] C8 validates against the contract. `lead_time_h` comes from the script output, not typed in.
- [ ] Street entries each have a working source URL. Misses are reported honestly too (a miss is a Q&A answer, not something to hide).

## Test
`tests/test_validate.py`: a synthetic 15-min stage series → the crossing function returns the right up-crossing time. A synthetic forecast set → the correct `first_warning_cycle` and `lead_time_h`.

## Fallback
- If NWM never crosses minor flow before the observed crossing: report the lead time for the action threshold, or the peak-timing error, whichever is honest and favorable, and pivot the pitch to "road-level timing engine; skill depends on NWM". If there's no skill at all, run the B1 replay.
- If no citable street truth exists: show the gauge validation only, and say so.
