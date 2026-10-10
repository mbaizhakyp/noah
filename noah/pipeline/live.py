"""Spec 015: live forecast loop. Noah is an everyday app, so this keeps C5/C6 on the newest NWM run.

Every pass: find the newest short-range cycle that is fully published on GCS (f018 + analysis),
fetch it for Noah's reaches (spec 001 code), compute road flood times (spec 004 code), write
web/data/flood_<cycle>.geojson and add the cycle to C6 with event "live". Keeps the last
LIVE_KEEP cycles and prunes older live files.

Run: uv run python -m noah.pipeline.live --once        (one pass)
     uv run python -m noah.pipeline.live --every 900   (check every 15 min; new cycles land hourly)
     Saturday (Isaias): add --keep 48 so the morning runs + their C1 inputs aren't pruned (BL-15/16/18)
"""

import argparse
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import httpx
import osmnx as ox
import pandas as pd

from noah import config
from noah.pipeline import fetch_nwm, flood_times

log = logging.getLogger("live")
LIVE_KEEP = 6
LIVE_BASELINE_CYCLE = (
    "20261009T22Z"  # low flow before rain (Peachtree Creek gauge 18 cfs): baseline guard only
)
C6_PATH = config.WEB_DATA / "cycles.json"


def latest_published(
    client: httpx.Client, now: datetime | None = None, look_back_h: int = 6
) -> str | None:
    """Newest cycle whose last forecast hour and analysis file both exist (NWM lands ~1.5-2 h late)."""
    now = (now or datetime.now(UTC)).replace(minute=0, second=0, microsecond=0)
    for back in range(1, look_back_h + 1):
        cycle = config.cycle_id(now - timedelta(hours=back))
        urls = fetch_nwm.file_urls(cycle)
        if all(client.head(urls[k]).status_code == 200 for k in (0, config.MAX_LEAD_H)):
            return cycle
    return None


def load_unit(name: str, c3_path, ht_path, graph_path) -> dict:
    """One processed area (metro, or a spec-016 basin): thresholds + uncertain band + road geometry."""
    c3 = pd.read_parquet(c3_path)
    ht = pd.read_parquet(ht_path)
    c3 = c3.assign(uncertain_q=flood_times.uncertain_q(c3, ht, config.UNCERTAIN_BAND_M))
    edges = ox.graph_to_gdfs(ox.load_graphml(graph_path), nodes=False)
    edges = edges.reset_index(drop=True)[["seg_id", "name", "geometry"]]
    log.info("%s: %d threshold rows, %d road segments", name, len(c3), len(edges))
    return {"name": name, "c3": c3, "edges": edges}


def fetch_with_ids(cycle: str, ids: list[int], pool, client) -> None:
    """fetch_nwm skips cycles already on disk; refetch when a newly built basin added reaches."""
    out = fetch_nwm.OUT_DIR / f"{cycle}.parquet"
    force = False
    if out.exists():
        have = set(pd.read_parquet(out, columns=["feature_id"]).feature_id.unique())
        force = not set(ids) <= have
    fetch_nwm.fetch_cycle(cycle, ids, False, force, pool, client)


def load_inputs(client, pool) -> dict:
    """Thresholds, rating-based uncertain band, baseline flows and road geometry (built once by 002/003),
    for metro plus every spec-016 basin that has been built."""
    units = [
        load_unit(
            "metro",
            config.DATA_INTERIM / "seg_thresholds.parquet",
            config.DATA_RAW / "hand" / config.HUC8 / config.FIM_FILES["hydrotable_huc"],
            config.DATA_INTERIM / "graph.graphml",
        )
    ]
    for name, b in config.BASINS.items():
        d = config.basin_dir(name)
        if (d / "seg_thresholds.parquet").exists() and (d / "graph.graphml").exists():
            units.append(
                load_unit(
                    name,
                    d / "seg_thresholds.parquet",
                    config.DATA_RAW / "hand" / b["huc8"] / config.FIM_FILES["hydrotable_huc"],
                    d / "graph.graphml",
                )
            )
    ids = sorted(
        set().union(*(set(u["c3"].feature_id.astype("int64")) for u in units))
        | {config.GAUGE_FEATURE_ID}
    )
    fetch_with_ids(LIVE_BASELINE_CYCLE, ids, pool, client)
    base = pd.read_parquet(fetch_nwm.OUT_DIR / f"{LIVE_BASELINE_CYCLE}.parquet")
    base_q = base[base.lead_h == 1].set_index("feature_id").q_cms
    log.info(
        "inputs: %d areas (%s), %d reaches",
        len(units),
        ", ".join(u["name"] for u in units),
        len(ids),
    )
    return {"units": units, "ids": ids, "base_q": base_q}


def cycle_entry(cycle: str) -> dict:
    t0 = config.parse_cycle(cycle)
    return {
        "cycle": cycle,
        "event": "live",
        "issue_time": t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "valid_times": [
            (t0 + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")
            for h in range(config.MAX_LEAD_H + 1)
        ],
    }


def update_c6(c6: dict, cycle: str, keep: int = LIVE_KEEP) -> tuple[dict, list[str]]:
    """Add the cycle as live, keep the newest `keep` live cycles. Returns (c6, dropped cycles)."""
    live = [c for c in c6.get("cycles", []) if c.get("event") == "live" and c["cycle"] != cycle]
    live = sorted([*live, cycle_entry(cycle)], key=lambda c: c["cycle"])
    dropped = [c["cycle"] for c in live[:-keep]]
    others = [c for c in c6.get("cycles", []) if c.get("event") != "live"]
    c6 = {**c6, "cycles": sorted(others + live[-keep:], key=lambda c: c["cycle"])}
    c6.setdefault("events", {})["live"] = {"label": "Live NWM forecast", "demo_cycle": cycle}
    return c6, dropped


def write_json_atomic(path, obj, **kw) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, **kw))
    os.replace(tmp, path)


def run_once(
    client,
    pool,
    inputs: dict,
    keep: int = LIVE_KEEP,
    cycle: str | None = None,
    refresh: bool = False,
) -> str | None:
    cycle = cycle or latest_published(client)
    if not cycle:
        log.warning("no fully published NWM cycle in the last 6 h")
        return None
    c6 = json.loads(C6_PATH.read_text()) if C6_PATH.exists() else {"events": {}, "cycles": []}
    out = config.WEB_DATA / f"flood_{cycle}.geojson"
    done = out.exists() and any(
        c["cycle"] == cycle and c.get("event") == "live" for c in c6["cycles"]
    )
    if done and not refresh:
        log.info("%s already live, nothing to do", cycle)
        return cycle
    t = time.time()
    fetch_with_ids(cycle, inputs["ids"], pool, client)
    flows = pd.read_parquet(fetch_nwm.OUT_DIR / f"{cycle}.parquet")
    features, counts = [], []
    for u in inputs[
        "units"
    ]:  # one C5 per cycle, metro + every built basin (seg_ids are OSM node ids: unique)
        segs = flood_times.flood_times(u["c3"], flows, inputs["base_q"])
        features += flood_times.to_geojson(segs, u["edges"])["features"]
        counts.append(f"{u['name']} {len(segs)}/{int((segs.t_flood >= 0).sum())}")
    write_json_atomic(
        out, {"type": "FeatureCollection", "features": features}, separators=(",", ":")
    )
    c6, dropped = update_c6(c6, cycle, keep)
    write_json_atomic(C6_PATH, c6, indent=1)
    for old in dropped:
        for f in (config.WEB_DATA / f"flood_{old}.geojson", fetch_nwm.OUT_DIR / f"{old}.parquet"):
            f.unlink(missing_ok=True)
    log.info(
        "%s live: %d segments flagged (flagged/flooded per area: %s), %.0f s; pruned %s",
        cycle,
        len(features),
        "; ".join(counts),
        time.time() - t,
        dropped or "nothing",
    )
    return cycle


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--once", action="store_true")
    g.add_argument("--every", type=int, help="seconds between checks")
    g.add_argument(
        "--backfill",
        metavar="FROM_CYCLE",
        help="process every hourly cycle from FROM_CYCLE (e.g. 20261009T22Z) to the newest published, then exit",
    )
    p.add_argument(
        "--keep",
        type=int,
        default=LIVE_KEEP,
        help="live cycles to keep (Isaias Saturday: 48, so the 8 AM run + validation inputs survive; BL-15)",
    )
    p.add_argument(
        "--refresh",
        action="store_true",
        help="recompute the newest cycle even if it is already live (after a new basin is built, spec 016)",
    )
    a = p.parse_args()
    with httpx.Client(timeout=120, follow_redirects=True) as client, ThreadPoolExecutor(8) as pool:
        inputs = load_inputs(client, pool)
        if a.backfill:  # show how the forecast evolved run by run (e.g. Isaias from Friday evening)
            newest = latest_published(client)
            for c in config.cycle_range(a.backfill, newest) if newest else []:
                try:
                    run_once(client, pool, inputs, max(a.keep, 48), cycle=c, refresh=a.refresh)
                except Exception:
                    log.exception("backfill %s failed", c)
            return
        while True:
            try:
                run_once(client, pool, inputs, a.keep, refresh=a.refresh and a.once)
            except Exception:
                log.exception("live pass failed")
            if a.once:
                return
            time.sleep(a.every)


if __name__ == "__main__":
    main()
