"""Spec 001: fetch NWM streamflow per cycle and cut it to Noah's reaches.

Reads:  NWM short_range f001-f018 + analysis_assim tm00 (hour 0) from the public GCS bucket.
        C2 data/interim/rating.parquet for the reach list (unless --gauge-only).
Writes: C1 data/interim/nwm/<cycle>.parquet  (feature_id, lead_h 0-18, valid_time, q_cms)
"""

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor

import httpx
import numpy as np
import pandas as pd
import xarray as xr

from noah import config

log = logging.getLogger("fetch_nwm")
OUT_DIR = config.DATA_INTERIM / "nwm"
RAW_DIR = config.DATA_RAW / "nwm"


def file_urls(cycle: str) -> dict[int, str]:
    """lead_h -> URL. Hour 0 is the analysis (estimated now), 1-18 the forecast."""
    t = config.parse_cycle(cycle)
    ymd, hh = t.strftime("%Y%m%d"), t.strftime("%H")
    urls = {0: config.NWM_ANALYSIS.format(ymd=ymd, hh=hh)}
    for lead in range(1, config.MAX_LEAD_H + 1):
        urls[lead] = config.NWM_SHORT_RANGE.format(ymd=ymd, hh=hh, fff=f"{lead:03d}")
    return urls


def subset(ds: xr.Dataset, feature_ids: list[int], lead_h: int) -> pd.DataFrame:
    """One channel_rt file -> C1 rows for the requested reaches (missing reaches are skipped)."""
    present = np.intersect1d(ds["feature_id"].values, np.asarray(feature_ids, dtype="int64"))
    q = ds["streamflow"].sel(feature_id=present).values.reshape(-1)
    valid = pd.Timestamp(ds["time"].values[0]).tz_localize("UTC")
    return pd.DataFrame(
        {
            "feature_id": present.astype("int64"),
            "lead_h": np.full(len(present), lead_h, dtype="int8"),
            "valid_time": valid,
            "q_cms": q.astype("float32"),
        }
    )


def download(url: str, dest, client: httpx.Client, tries: int = 3) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    for attempt in range(1, tries + 1):
        try:
            with client.stream("GET", url) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    f.writelines(r.iter_bytes(1 << 20))
            tmp.rename(dest)
            return
        except httpx.HTTPError as e:
            log.warning("download failed (%d/%d) %s: %s", attempt, tries, url, e)
    raise RuntimeError(f"could not download {url}")


def fetch_lead(
    cycle: str, lead: int, url: str, ids: list[int], keep_raw: bool, client
) -> pd.DataFrame:
    dest = RAW_DIR / cycle / url.rsplit("/", 1)[1]
    download(url, dest, client)
    with xr.open_dataset(dest, engine="h5netcdf") as ds:
        df = subset(ds, ids, lead)
    if not keep_raw:
        dest.unlink()
    return df


def fetch_cycle(cycle: str, ids: list[int], keep_raw: bool, force: bool, pool, client) -> None:
    out = OUT_DIR / f"{cycle}.parquet"
    if out.exists() and not force:
        log.info("%s exists, skipping", out.name)
        return
    jobs = [
        pool.submit(fetch_lead, cycle, lead, url, ids, keep_raw, client)
        for lead, url in file_urls(cycle).items()
    ]
    df = pd.concat([j.result() for j in jobs]).sort_values(
        ["feature_id", "lead_h"], ignore_index=True
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    g = df[df.feature_id == config.GAUGE_FEATURE_ID]
    peak = g.loc[g.q_cms.idxmax()] if len(g) else None
    log.info(
        "%s: %d leads, %d reaches, gauge peak %s",
        cycle,
        df.lead_h.nunique(),
        df.feature_id.nunique(),
        f"{peak.q_cms:.1f} m3/s at +{peak.lead_h}h" if peak is not None else "n/a",
    )


def reach_ids(gauge_only: bool, huc8: bool = False) -> list[int]:
    ids = {config.GAUGE_FEATURE_ID}
    rating = config.DATA_INTERIM / "rating.parquet"
    if huc8:
        # Superset: every reach in the HUC8 hydrotable, so one download pass covers the AOI too.
        ht = config.DATA_RAW / "hand" / config.HUC8 / config.FIM_FILES["hydrotable_huc"]
        if not ht.exists():
            raise SystemExit(f"{ht} missing: download it first (spec 002)")
        fids = pd.read_parquet(ht).reset_index()["feature_id"]
        return sorted(ids | set(pd.to_numeric(fids).astype("int64")))
    if not gauge_only:
        if not rating.exists():
            raise SystemExit(
                f"{rating} missing: run spec 002 (fetch_hand) first, or pass --gauge-only"
            )
        ids |= set(pd.read_parquet(rating, columns=["feature_id"]).feature_id.astype("int64"))
    return sorted(ids)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--event", default="helene", choices=sorted(config.EVENTS))
    p.add_argument("--cycles", help="override, e.g. 20240926T12Z..20240927T12Z")
    p.add_argument("--gauge-only", action="store_true")
    p.add_argument(
        "--huc8", action="store_true", help="all HUC8 hydrotable reaches (superset of the AOI)"
    )
    p.add_argument("--keep-raw", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--workers", type=int, default=8)
    a = p.parse_args()

    ev = config.EVENTS[a.event]
    cycles = config.cycle_range(*a.cycles.split("..")) if a.cycles else list(ev["cycles"])
    if ev["baseline"] not in cycles:
        cycles = [ev["baseline"], *cycles]
    ids = reach_ids(a.gauge_only, a.huc8)
    log.info("%d cycles, %d reaches", len(cycles), len(ids))
    with (
        httpx.Client(timeout=120, follow_redirects=True) as client,
        ThreadPoolExecutor(a.workers) as pool,
    ):
        for c in cycles:
            fetch_cycle(c, ids, a.keep_raw, a.force, pool, client)


if __name__ == "__main__":
    main()
