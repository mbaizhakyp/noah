"""BL-18: Isaias proof numbers for the pitch. Compares Noah's Friday 10 PM run (20261010T02Z, the first run that saw the
storm's size) with what the USGS gauges then measured, and writes web/data/isaias_validation.json.

Run: uv run python -m noah.pipeline.isaias_proof
"""

import json
import logging

import httpx
import pandas as pd

from noah import config
from noah.pipeline import validate

log = logging.getLogger("isaias_proof")
RUN = "20261010T02Z"
GAUGES = {  # USGS site -> label (the metro creeks with a gauge on the NWM reach)
    "02336300": "Peachtree Creek at Atlanta",
    "02336000": "Chattahoochee River at Atlanta",
    "02336410": "Nancy Creek at West Wesley Rd",
    "02335870": "Sope Creek near Marietta",
    "02336240": "South Fork Peachtree Creek",
    "02335700": "Big Creek near Alpharetta",
}
CFS = 1 / config.CFS_TO_CMS


def peak_error(fc_peak: float, ob_peak: float) -> float:
    return round((fc_peak - ob_peak) / ob_peak * 100)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    issue = pd.Timestamp(config.parse_cycle(RUN))
    had = pd.Timestamp(
        (config.WEB_DATA / "route_watch.json").exists()
        and next(
            r["had_utc"]
            for r in json.loads((config.WEB_DATA / "route_watch.json").read_text())["runs"]
            if r["cycle"] == RUN
        )
    )
    fc = pd.read_parquet(config.DATA_INTERIM / "nwm" / f"{RUN}.parquet")
    now = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%MZ")
    rows = []
    for site, label in GAUGES.items():
        comid = int(
            httpx.get(
                f"https://api.water.usgs.gov/nldi/linked-data/nwissite/USGS-{site}?f=json",
                timeout=30,
            ).json()["features"][0]["properties"]["comid"]
        )
        q = validate.fetch_usgs(site, "2026-10-09T22:00Z", now).q_cfs.dropna()
        f = fc[fc.feature_id == comid].sort_values("lead_h")
        s = pd.Series((f.q_cms * CFS).values, index=issue + pd.to_timedelta(f.lead_h, unit="h"))
        ob_t, fc_t = q.idxmax(), s.idxmax()
        rows.append(
            {
                "gauge": label,
                "usgs": site,
                "observed_peak_cfs": round(float(q.max())),
                "observed_peak_utc": ob_t.strftime("%Y-%m-%dT%H:%MZ"),
                "forecast_peak_cfs": round(float(s.max())),
                "forecast_peak_utc": fc_t.strftime("%Y-%m-%dT%H:%MZ"),
                "peak_error_pct": peak_error(float(s.max()), float(q.max())),
                "timing_error_h": round((fc_t - ob_t).total_seconds() / 3600, 1),
                "hours_ahead": round((ob_t - had).total_seconds() / 3600, 1),
            }
        )
        log.info(
            "%s: observed %s, forecast %s (%+d%%)",
            label,
            rows[-1]["observed_peak_cfs"],
            rows[-1]["forecast_peak_cfs"],
            rows[-1]["peak_error_pct"],
        )
    out = {
        "run": RUN,
        "issued_utc": issue.strftime("%Y-%m-%dT%H:%MZ"),
        "noah_had_utc": had.strftime("%Y-%m-%dT%H:%MZ"),
        "gauges": rows,
        "note": "Gauge-level check of the creek and river forecast Noah used; street-level closures were not reported (TomTom showed no flooding incidents).",
    }
    (config.WEB_DATA / "isaias_validation.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
