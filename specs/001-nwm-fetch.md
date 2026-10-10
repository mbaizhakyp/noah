# 001 — NWM forecast fetch + subset

| | |
|---|---|
| Owner | Margulan |
| Status | Draft |
| Time box | 2 h |
| Depends on | — (AOI reach list improves once 002 lands; the gauge reach alone is enough for the go/no-go) |
| Produces | C1 `data/interim/nwm/<cycle>.parquet` |

## Goal
Get NWM short-range streamflow for the Helene cycles, cut to AOI reaches, so we can (a) make the midnight go/no-go call at the gauge reach and (b) feed spec 004.

## Non-goals
Other NWM products (medium-range; `analysis_assim` beyond the hour-0 file) unless B1's fallback is triggered. Forcing data. Running any model.

## Inputs
- `config.NWM_URL` (verified Oct 9, 2026): `https://storage.googleapis.com/national-water-model/nwm.{YYYYMMDD}/short_range/nwm.t{HH}z.short_range.channel_rt.f{FFF}.conus.nc`, FFF = 001–018, about 12.7 MB each (CONUS, ~2.7 M reaches).
- Reach list: `config.GAUGE_FEATURE_ID` (2047989) ∪ the distinct `feature_id` in C2 if it exists. CLI flag `--feature-ids-from rating` vs `--gauge-only`.
- Cycles: `config.HELENE_CYCLES`, plus `config.BASELINE_CYCLE` f001 (needed by 004).
- **Hour 0 (now):** for each cycle also fetch `nwm.{YYYYMMDD}/analysis_assim/nwm.t{HH}z.analysis_assim.channel_rt.tm00.conus.nc` (~12.6 MB; verified to exist for 20240926 and 20261009). It becomes `lead_h = 0` (D10).

## Outputs
- C1, one parquet per cycle. Raw `.nc` files go in `data/raw/nwm/` and **are deleted after subsetting** unless `--keep-raw` is passed (25 cycles × 19 files × ~12.7 MB ≈ 6 GB).

## Behavior
1. CLI: `python -m noah.pipeline.fetch_nwm [--cycles 20240926T12Z..20240927T12Z] [--gauge-only] [--keep-raw] [--force]`.
2. For each cycle and lead, download with `httpx` (streamed, 3 retries, up to 8 concurrent downloads via a thread pool).
3. Open with `xarray.open_dataset(path, engine="h5netcdf")`, select `streamflow` where `feature_id` is in the reach list (`ds.sel(feature_id=ids)`; **(verify)** that `feature_id` is an indexed coordinate). Read `time` for `valid_time`.
4. Concatenate hour 0 + the 18 leads into long format matching C1 and write parquet. Skip cycles whose parquet already exists.
5. Log: cycle, leads fetched, n reaches, max q at the gauge reach.

## Acceptance criteria
- [ ] `--gauge-only` for all `HELENE_CYCLES` finishes and writes 25 parquet files, each with **19 rows** (lead 0 from analysis + 18 forecast) for feature 2047989.
- [ ] A short printout (or notebook cell) shows, per cycle, forecast peak q at 2047989 and its valid time next to the observed peak (20,000 cfs = 566 m³/s at 2024-09-27 09:45Z; stage peak 12:15Z). This is the **go/no-go evidence**, pasted into `05-PROGRESS.md`.
- [ ] Running the full-AOI version after 002 adds every C2 `feature_id`.

## Test
`tests/test_fetch_nwm.py`: builds a tiny in-memory `xarray.Dataset` shaped like a channel_rt file, runs the subset/reshape function, and asserts C1 columns, dtypes and `lead_h` 0–18 ordering. No network.

## Fallback
- If GCS is slow: gauge-only first, which alone settles the go/no-go.
- B1 (poor forecast skill): the same script with `--product analysis_assim` (path `analysis_assim/nwm.tHHz.analysis_assim.channel_rt.tm00.conus.nc`, **(verify)**) writes a pseudo-forecast where lead_h = hours after the start cycle. Record this clearly as an observed-flow replay in the docs.
