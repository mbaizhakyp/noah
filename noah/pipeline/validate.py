"""Spec 005: did the NWM forecast say Peachtree Creek would flood, and how far ahead?

Reads:  USGS IV (stage + discharge) for the gauge, C1 data/interim/nwm/<cycle>.parquet.
Writes: C8 web/data/validation[_<event>].json, web/data/validation[_<event>].png
Part A (lead time + go/no-go) only; part C (street truth) is added later.
"""

import argparse
import json
import logging

import httpx
import pandas as pd

from noah import config

log = logging.getLogger("validate")
GO_MIN_LEAD_H = 3


def fetch_usgs(site: str, start: str, end: str) -> pd.DataFrame:
    """USGS IV -> DataFrame indexed by UTC time with columns stage_ft, q_cfs (NaN where missing)."""
    url = config.USGS_IV_URL.format(site=site, start=start, end=end)
    data = httpx.get(url, timeout=60, follow_redirects=True).raise_for_status().json()
    cols = {}
    for ts in data["value"]["timeSeries"]:
        code = ts["variable"]["variableCode"][0]["value"]
        name = {"00065": "stage_ft", "00060": "q_cfs"}[code]
        vals = ts["values"][0]["value"]
        s = pd.Series(
            [float(v["value"]) for v in vals],
            index=pd.to_datetime([v["dateTime"] for v in vals], utc=True),
        )
        cols[name] = s[s > -999]  # USGS no-data sentinel
    return pd.DataFrame(cols).sort_index()


def up_crossing(s: pd.Series, threshold: float) -> pd.Timestamp | None:
    """First time s reaches threshold after being below it (s indexed by time)."""
    s = s.dropna()
    above = s >= threshold
    hits = s.index[above & ~above.shift(1, fill_value=True)]
    return hits[0] if len(hits) else None


def cycle_table(nwm: dict[str, pd.DataFrame], threshold_cms: float) -> pd.DataFrame:
    """Per cycle at the gauge reach: forecast peak and the first forecast hour (lead >= 1) at/above threshold."""
    rows = []
    for cycle, df in sorted(nwm.items()):
        g = df[(df.feature_id == config.GAUGE_FEATURE_ID)].sort_values("lead_h")
        fc = g[g.lead_h >= 1]
        peak = fc.loc[fc.q_cms.idxmax()]
        cross = fc[fc.q_cms >= threshold_cms]
        now = g[g.lead_h == 0]
        rows.append(
            {
                "cycle": cycle,
                "issue_time": config.parse_cycle(cycle),
                "now_cms": float(now.q_cms.iloc[0]) if len(now) else None,
                "fcst_peak_cms": float(peak.q_cms),
                "fcst_peak_utc": peak.valid_time,
                "fcst_minor_cross_utc": cross.valid_time.iloc[0] if len(cross) else None,
            }
        )
    return pd.DataFrame(rows)


def lead_time(table: pd.DataFrame, observed_cross: pd.Timestamp) -> tuple[str | None, float | None]:
    """Earliest cycle that forecast the crossing, and hours between its issue time and the observed crossing."""
    warned = table[table.fcst_minor_cross_utc.notna() & (table.issue_time < observed_cross)]
    if warned.empty:
        return None, None
    first = warned.sort_values("issue_time").iloc[0]
    return first.cycle, (observed_cross - first.issue_time).total_seconds() / 3600


def plot(obs: pd.DataFrame, nwm: dict[str, pd.DataFrame], table, obs_cross, out_png, title) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=130)
    cmap = plt.get_cmap("viridis")
    cycles = sorted(nwm)
    for i, c in enumerate(cycles):
        g = nwm[c][nwm[c].feature_id == config.GAUGE_FEATURE_ID].sort_values("lead_h")
        ax.plot(g.valid_time, g.q_cms, color=cmap(i / max(1, len(cycles) - 1)), lw=0.9, alpha=0.8)
    ax.plot(
        obs.index, obs.q_cfs * config.CFS_TO_CMS, color="black", lw=2.2, label="Observed (USGS)"
    )
    ax.axhline(
        config.MINOR_FLOOD_CMS, color="#ef4444", ls="--", lw=1.2, label="Minor flood flow (NWS)"
    )
    if obs_cross is not None:
        ax.axvline(obs_cross, color="#ef4444", lw=1, alpha=0.6, label="Observed minor flood stage")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, len(cycles) - 1))
    cb = fig.colorbar(sm, ax=ax, pad=0.01)
    ticks = list(range(0, len(cycles), max(1, len(cycles) // 6)))
    cb.set_ticks(ticks)
    cb.set_ticklabels([cycles[i] for i in ticks])
    cb.set_label("NWM forecast issued (UTC)")
    ax.set_ylabel("Streamflow (m³/s)")
    ax.set_xlabel("Time (UTC)")
    ax.set_title(title)
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--event", default="helene", choices=sorted(config.EVENTS))
    a = p.parse_args()
    ev = config.EVENTS[a.event]
    suffix = "" if a.event == "helene" else f"_{a.event}"

    obs = fetch_usgs(config.GAUGE_USGS, *ev["usgs_window"])
    crossings = {k: up_crossing(obs.stage_ft, v) for k, v in config.THRESHOLDS_FT.items()}
    peak_t = obs.stage_ft.idxmax()
    log.info("observed crossings: %s", {k: str(v) for k, v in crossings.items()})
    log.info("observed peak %.2f ft at %s", obs.stage_ft.max(), peak_t)

    files = {
        f.stem: pd.read_parquet(f)
        for f in sorted((config.DATA_INTERIM / "nwm").glob("*.parquet"))
        if f.stem in ev["cycles"]
    }
    if not files:
        raise SystemExit("no C1 files for this event: run fetch_nwm first")
    table = cycle_table(files, config.MINOR_FLOOD_CMS)
    obs_cross = crossings["minor"]
    first, lead = lead_time(table, obs_cross) if obs_cross is not None else (None, None)

    show = table.assign(
        hours_before_obs=((obs_cross - table.issue_time).dt.total_seconds() / 3600)
        if obs_cross is not None
        else None
    )
    print(show.to_string(index=False, float_format=lambda x: f"{x:.1f}"))
    go = lead is not None and lead >= GO_MIN_LEAD_H
    print(f"\nobserved minor flood stage (17 ft): {obs_cross}")
    print(f"first warning cycle: {first}  lead time: {lead if lead is None else round(lead, 1)} h")
    print(f"GO/NO-GO (>= {GO_MIN_LEAD_H} h): {'GO' if go else 'NO-GO'}")

    out = config.WEB_DATA / f"validation{suffix}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    iso = lambda t: (
        None if t is None or pd.isna(t) else pd.Timestamp(t).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    out.write_text(
        json.dumps(
            {
                "gauge": {
                    "usgs": config.GAUGE_USGS,
                    "nws_lid": config.GAUGE_NWS_LID,
                    "feature_id": config.GAUGE_FEATURE_ID,
                },
                "thresholds_ft": config.THRESHOLDS_FT,
                "thresholds_cfs": config.THRESHOLDS_CFS,
                "observed": {
                    "minor_cross_utc": iso(obs_cross),
                    "peak_stage_ft": float(obs.stage_ft.max()),
                    "peak_utc": iso(peak_t),
                },
                "cycles": [
                    {
                        "cycle": r.cycle,
                        "fcst_peak_cms": round(r.fcst_peak_cms, 1),
                        "fcst_peak_utc": iso(r.fcst_peak_utc),
                        "fcst_minor_cross_utc": iso(r.fcst_minor_cross_utc),
                    }
                    for r in table.itertuples()
                ],
                "first_warning_cycle": first,
                "lead_time_h": None if lead is None else round(lead, 1),
            },
            indent=1,
        )
    )
    plot(obs, files, table, obs_cross, config.WEB_DATA / f"validation{suffix}.png", ev["label"])
    log.info("wrote %s and the PNG", out)


if __name__ == "__main__":
    main()
