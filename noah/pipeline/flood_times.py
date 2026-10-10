"""Spec 004: when does each road segment enter the uncertain / flooded state, per forecast cycle.

Reads:  C1 data/interim/nwm/<cycle>.parquet, C3 data/interim/seg_thresholds.parquet,
        C4 data/interim/graph.graphml, FIM hydrotable.parquet (all branches, for the uncertain band).
Writes: C5 web/data/flood_<cycle>.geojson, C6 web/data/cycles.json
"""

import argparse
import json
import logging

import numpy as np
import osmnx as ox
import pandas as pd
import shapely

from noah import config

log = logging.getLogger("flood_times")
N_LEADS = config.MAX_LEAD_H + 1  # hour 0 (now) + 18 forecast hours


def uncertain_q(rows: pd.DataFrame, hydrotable: pd.DataFrame, band_m: float) -> np.ndarray:
    """Discharge at stage max(hand - band, hand/2) on each row's (HydroID, branch) curve."""
    ht = hydrotable.reset_index() if "HydroID" not in hydrotable.columns else hydrotable
    ht = ht.assign(hid=pd.to_numeric(ht.HydroID), br=pd.to_numeric(ht.branch_id)).sort_values(
        "stage"
    )
    curves = {
        k: (g.stage.to_numpy(), g.discharge_cms.to_numpy()) for k, g in ht.groupby(["hid", "br"])
    }
    out = rows.threshold_q_cms.to_numpy(dtype="float64").copy()
    missing = 0
    for i, (hid, br, hand) in enumerate(zip(rows.hydro_id, rows.branch_id, rows.threshold_hand_m)):
        c = curves.get((hid, br))
        if c is None:
            missing += 1
            continue
        out[i] = np.interp(max(hand - band_m, 0.5 * hand), *c)
    if missing:
        log.warning("%d rows without a rating curve: no uncertain band for them", missing)
    return np.minimum(out, rows.threshold_q_cms.to_numpy())


def first_crossing(q: np.ndarray, thr: np.ndarray) -> np.ndarray:
    """q: (rows, leads), thr: (rows,) -> first lead index with q >= thr, or -1."""
    hit = q >= thr[:, None]
    return np.where(hit.any(axis=1), hit.argmax(axis=1), -1)


def flood_times(
    c3: pd.DataFrame, flows: pd.DataFrame, base_q: pd.Series | None = None
) -> pd.DataFrame:
    """C3 rows (+ uncertain_q column) and one cycle's C1 -> per segment t_uncertain, t_flood (-1 = never)."""
    rows = c3
    if base_q is not None:
        wet = rows.threshold_q_cms.to_numpy() <= rows.feature_id.map(base_q).fillna(-1).to_numpy()
        if wet.any():
            log.info("baseline guard: dropping %d rows wet at low flow", int(wet.sum()))
        rows = rows[~wet]
    Q = flows.pivot_table(index="feature_id", columns="lead_h", values="q_cms").reindex(
        columns=range(N_LEADS)
    )
    q = Q.reindex(rows.feature_id).to_numpy()
    q = np.nan_to_num(q, nan=-np.inf)
    df = rows[["seg_id", "feature_id", "threshold_hand_m"]].assign(
        t_flood=first_crossing(q, rows.threshold_q_cms.to_numpy()),
        t_uncertain=first_crossing(q, rows.uncertain_q.to_numpy()),
    )
    df = df[df.t_uncertain >= 0]
    if df.empty:
        return pd.DataFrame(
            columns=["seg_id", "t_uncertain", "t_flood", "feature_id", "hand_min_m"]
        )
    df = df.assign(t_flood=df.t_flood.where(df.t_flood >= 0, np.inf))
    first = df.sort_values(["seg_id", "t_uncertain"]).groupby("seg_id").first()
    agg = df.groupby("seg_id").agg(
        t_uncertain=("t_uncertain", "min"),
        t_flood=("t_flood", "min"),
        hand_min_m=("threshold_hand_m", "min"),
    )
    agg["feature_id"] = first.feature_id
    agg["t_flood"] = agg.t_flood.replace(np.inf, -1).astype(int)
    return agg.reset_index()


def to_geojson(segs: pd.DataFrame, edges) -> dict:
    g = edges.set_index("seg_id").loc[segs.seg_id]
    feats = []
    for s, geom, name in zip(
        segs.itertuples(), g.geometry, g["name"] if "name" in g else [None] * len(g)
    ):
        name = name[0] if isinstance(name, list) else (name if isinstance(name, str) else None)
        geom = shapely.set_precision(geom, 1e-5)
        feats.append(
            {
                "type": "Feature",
                "geometry": shapely.geometry.mapping(geom),
                "properties": {
                    "seg_id": s.seg_id,
                    "name": name,
                    "t_uncertain": int(s.t_uncertain),
                    "t_flood": None if s.t_flood < 0 else int(s.t_flood),
                    "feature_id": int(s.feature_id),
                    "hand_min_m": round(float(s.hand_min_m), 2),
                },
            }
        )
    return {"type": "FeatureCollection", "features": feats}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--event", default="helene", choices=sorted(config.EVENTS))
    a = p.parse_args()
    ev = config.EVENTS[a.event]

    c3 = pd.read_parquet(config.DATA_INTERIM / "seg_thresholds.parquet")
    ht = pd.read_parquet(
        config.DATA_RAW / "hand" / config.HUC8 / config.FIM_FILES["hydrotable_huc"]
    )
    c3 = c3.assign(uncertain_q=uncertain_q(c3, ht, config.UNCERTAIN_BAND_M))
    base = pd.read_parquet(config.DATA_INTERIM / "nwm" / f"{ev['baseline']}.parquet")
    base_q = base[base.lead_h == 1].set_index("feature_id").q_cms
    edges = ox.graph_to_gdfs(ox.load_graphml(config.DATA_INTERIM / "graph.graphml"), nodes=False)
    edges = edges.reset_index(drop=True)[["seg_id", "name", "geometry"]]

    cycles_meta, written = [], 0
    for cycle in dict.fromkeys([ev["baseline"], *ev["cycles"]]):  # baseline may also be a cycle
        f = config.DATA_INTERIM / "nwm" / f"{cycle}.parquet"
        if not f.exists():
            log.warning("missing C1 for %s, skipping", cycle)
            continue
        segs = flood_times(c3, pd.read_parquet(f), base_q)
        fl = segs[segs.t_flood >= 0]
        log.info(
            "%s: %d uncertain, %d flooded, earliest flood +%s h",
            cycle,
            len(segs),
            len(fl),
            fl.t_flood.min() if len(fl) else "-",
        )
        if cycle == ev["baseline"] and cycle not in ev["cycles"]:
            continue  # sanity only
        out = config.WEB_DATA / f"flood_{cycle}.geojson"
        out.write_text(json.dumps(to_geojson(segs, edges), separators=(",", ":")))
        written += 1
        t0 = config.parse_cycle(cycle)
        cycles_meta.append(
            {
                "cycle": cycle,
                "event": a.event,
                "issue_time": t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "valid_times": [
                    (t0 + pd.Timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")
                    for h in range(N_LEADS)
                ],
            }
        )

    c6_path = config.WEB_DATA / "cycles.json"
    c6 = json.loads(c6_path.read_text()) if c6_path.exists() else {"events": {}, "cycles": []}
    c6["cycles"] = sorted(
        [c for c in c6["cycles"] if c.get("event") != a.event] + cycles_meta,
        key=lambda c: c["cycle"],
    )
    c6["events"][a.event] = {"label": ev["label"], "demo_cycle": ev["demo"]}
    c6["demo_cycle"] = config.DEMO_CYCLE
    c6_path.write_text(json.dumps(c6, indent=1))
    log.info("wrote %d C5 files and %s", written, c6_path)


if __name__ == "__main__":
    main()
