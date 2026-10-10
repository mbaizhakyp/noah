"""Spec 003: AOI, drivable road graph, per-road flood thresholds (NOAA for major roads, Noah for the rest).

Reads:  WBD HUC10 polygon (via data/interim/aoi.geojson), OSM via OSMnx,
        FIM 4.9 osm_roads_fimpact.csv (per OSM way x HydroID flood thresholds).
Writes: C7 web/data/aoi.geojson, C4 data/interim/graph.graphml,
        C3 data/interim/seg_thresholds.parquet
          (seg_id, hydro_id, feature_id, branch_id, threshold_hand_m, threshold_q_cms, source)
"""

import argparse
import logging
import shutil

import geopandas as gpd
import numpy as np
import osmnx as ox
import pandas as pd
import rasterio
import shapely
from rasterio.windows import from_bounds

from noah import config

log = logging.getLogger("build_segments")
GRAPH = config.DATA_INTERIM / "graph.graphml"
SEG_THRESHOLDS = config.DATA_INTERIM / "seg_thresholds.parquet"
FIXTURE_MAX_MB = 20
HAND_SCALE = (
    0.001  # FIM 4.9 HAND rasters are int16 millimetres (checked against NOAA threshold_hand)
)
MAX_HAND_M = 25.0  # NOAA's own cutoff for road thresholds


def aoi_polygon():
    src = config.DATA_INTERIM / "aoi.geojson"
    if not src.exists():
        raise SystemExit(f"{src} missing: run fetch_hand (spec 002) first, it fetches the HUC10")
    return config.aoi_union(src.read_text())


def truthy_tag(v) -> bool:
    """OSM bridge/tunnel tags from OSMnx can be NaN, a string, or a list of strings."""
    if isinstance(v, list):
        return any(truthy_tag(x) for x in v)
    return isinstance(v, str) and v.strip().lower() not in ("", "no", "nan")


def step1_graph() -> None:
    aoi = aoi_polygon()
    config.WEB_DATA.mkdir(parents=True, exist_ok=True)
    shutil.copy(config.DATA_INTERIM / "aoi.geojson", config.WEB_DATA / "aoi.geojson")
    buffered = gpd.GeoSeries([aoi], crs=4326).to_crs(5070).buffer(2000).to_crs(4326).iloc[0]
    log.info("downloading OSM drive network for AOI + 2 km (Overpass, can take a few minutes)")
    G = ox.graph_from_polygon(buffered, network_type="drive", retain_all=False)
    G = ox.routing.add_edge_speeds(G)
    G = ox.routing.add_edge_travel_times(G)
    for u, v, k, d in G.edges(keys=True, data=True):
        d["seg_id"] = f"{u}-{v}-{k}"
    GRAPH.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(G, GRAPH)
    mb = GRAPH.stat().st_size / 1e6
    log.info("graph: %d nodes, %d edges, %.1f MB -> %s", len(G), G.number_of_edges(), mb, GRAPH)
    if mb < FIXTURE_MAX_MB:
        dest = config.ROOT / "fixtures" / "graph.graphml"
        dest.parent.mkdir(exist_ok=True)
        shutil.copy(GRAPH, dest)
        log.info("copied to %s for Priyanshu", dest)


def edge_thresholds(
    edges: gpd.GeoDataFrame, fimpact: pd.DataFrame, min_hand_m: float
) -> pd.DataFrame:
    """Join OSMnx edges to NOAA road thresholds by OSM way id -> C3 rows.

    edges: columns seg_id, osmid (int or list), bridge, tunnel (optional). Bridges/tunnels are dropped,
    and thresholds below min_hand_m are treated as crossing artifacts (road at channel level).
    """
    e = edges.copy()
    for tag in ("bridge", "tunnel"):
        if tag in e.columns:
            e = e[~e[tag].map(truthy_tag)]
    e = e[["seg_id", "osmid"]].explode("osmid")
    e["osmid"] = pd.to_numeric(e.osmid).astype("int64")
    j = e.merge(fimpact, on="osmid", how="inner")
    j = j[j.threshold_hand >= min_hand_m]
    out = pd.DataFrame(
        {
            "seg_id": j.seg_id.astype(str),
            "hydro_id": pd.to_numeric(j.HydroID).astype("int64"),
            "feature_id": pd.to_numeric(j.feature_id).astype("int64"),
            "branch_id": pd.to_numeric(j.branch).astype("int64"),
            "threshold_hand_m": j.threshold_hand.astype("float32"),
            "threshold_q_cms": j.threshold_discharge.astype("float32"),
        }
    )
    return out.drop_duplicates(ignore_index=True)


def densify(geoms: np.ndarray, spacing: float) -> tuple[np.ndarray, np.ndarray]:
    """Points every <= spacing along each line (both ends included) -> (edge index per point, points)."""
    lengths = shapely.length(geoms)
    counts = np.maximum(2, np.ceil(lengths / spacing).astype(int) + 1)
    idx = np.repeat(np.arange(len(geoms)), counts)
    frac = np.concatenate([np.linspace(0, 1, c) for c in counts])
    return idx, shapely.line_interpolate_point(geoms[idx], frac, normalized=True)


def min_hand_per_catchment(
    seg_ids, hand_m, hydro_ids, floor_m: float, max_m: float
) -> pd.DataFrame:
    """Samples -> per (seg_id, hydro_id) lowest HAND within [floor, max]. Below floor = channel/crossing."""
    s = pd.DataFrame({"seg_id": seg_ids, "hydro_id": hydro_ids, "hand": hand_m})
    s = s[(s.hand >= floor_m) & (s.hand <= max_m)]
    return s.groupby(["seg_id", "hydro_id"], as_index=False).hand.min()


def noah_thresholds(
    edges_4326: gpd.GeoDataFrame, curves: dict, fid_of: dict, branch: str = config.FIM_BRANCH
) -> pd.DataFrame:
    """CC4: Noah-computed thresholds for edges NOAA doesn't list, from one FIM branch's HAND + catchments."""
    raw = config.DATA_RAW / "hand" / config.HUC8
    files = config.fim_branch_files(branch)
    prefix = int((raw / files["hydroid_prefix"]).read_text().strip()) * 10000
    with (
        rasterio.open(raw / files["hand"]) as hs,
        rasterio.open(raw / files["catchments"]) as cs,
    ):
        e = edges_4326.to_crs(hs.crs)
        win = from_bounds(*e.total_bounds, transform=hs.transform).round_offsets().round_lengths()
        H, C, wt = (
            hs.read(1, window=win, boundless=True, fill_value=hs.nodata),
            cs.read(1, window=win, boundless=True, fill_value=0),
            hs.window_transform(win),
        )
        h_nodata = hs.nodata
    idx, pts = densify(np.asarray(e.geometry.values), config.SAMPLE_SPACING_M)
    rows, cols = rasterio.transform.rowcol(wt, shapely.get_x(pts), shapely.get_y(pts))
    rows, cols = np.asarray(rows), np.asarray(cols)
    ok = (rows >= 0) & (rows < H.shape[0]) & (cols >= 0) & (cols < H.shape[1])
    idx, rows, cols = idx[ok], rows[ok], cols[ok]
    h, c = H[rows, cols], C[rows, cols]
    valid = (h != h_nodata) & (c > 0)
    m = min_hand_per_catchment(
        e.seg_id.to_numpy()[idx[valid]],
        h[valid] * HAND_SCALE,
        c[valid].astype("int64") + prefix,
        config.MIN_ROAD_HAND_M,
        MAX_HAND_M,
    )
    q = []
    for hid, hand in zip(m.hydro_id, m.hand):
        cv = curves.get((hid, int(branch)))
        q.append(np.interp(hand, *cv) if cv is not None and hand <= cv[0][-1] else np.nan)
    m = m.assign(threshold_q_cms=q, feature_id=m.hydro_id.map(fid_of)).dropna(
        subset=["threshold_q_cms", "feature_id"]
    )
    return pd.DataFrame(
        {
            "seg_id": m.seg_id.astype(str),
            "hydro_id": m.hydro_id.astype("int64"),
            "feature_id": m.feature_id.astype("int64"),
            "branch_id": np.int64(int(branch)),
            "threshold_hand_m": m.hand.astype("float32"),
            "threshold_q_cms": m.threshold_q_cms.astype("float32"),
        }
    )


def rating_curves() -> tuple[dict, dict]:
    ht = pd.read_parquet(
        config.DATA_RAW / "hand" / config.HUC8 / config.FIM_FILES["hydrotable_huc"]
    ).reset_index()
    ht = ht.assign(
        hid=pd.to_numeric(ht.HydroID).astype("int64"),
        br=pd.to_numeric(ht.branch_id),
        fid=pd.to_numeric(ht.feature_id).astype("int64"),
    ).sort_values("stage")
    curves = {
        k: (g.stage.to_numpy(), g.discharge_cms.to_numpy()) for k, g in ht.groupby(["hid", "br"])
    }
    return curves, dict(zip(ht.hid, ht.fid))


def step2_thresholds(noaa_only: bool = False) -> None:
    G = ox.load_graphml(GRAPH)
    edges = ox.graph_to_gdfs(G, nodes=False).reset_index(drop=True)
    in_aoi = edges[edges.intersects(aoi_polygon())]
    n_bridge = int(
        sum(in_aoi[t].map(truthy_tag).sum() for t in ("bridge", "tunnel") if t in in_aoi)
    )
    fimpact = pd.read_csv(config.DATA_RAW / "hand" / config.HUC8 / config.FIM_FILES["fimpact"])
    raw = edge_thresholds(in_aoi, fimpact, min_hand_m=0.0)
    out = edge_thresholds(in_aoi, fimpact, config.MIN_ROAD_HAND_M).assign(source="noaa")
    n_noaa_rows, n_noaa_segs = len(out), out.seg_id.nunique()
    if not noaa_only:
        curves, fid_of = rating_curves()
        bridge = pd.Series(False, index=in_aoi.index)
        for tag in ("bridge", "tunnel"):
            if tag in in_aoi:
                bridge |= in_aoi[tag].map(truthy_tag)
        eligible_edges = in_aoi[~bridge]
        ours = pd.concat(
            [noah_thresholds(eligible_edges, curves, fid_of, b) for b in config.FIM_BRANCHES],
            ignore_index=True,
        )
        # consistency check on roads NOAA also covers: same method + data should give similar HAND
        both = ours.merge(out, on=["seg_id", "hydro_id"], suffixes=("_noah", "_noaa"))
        if len(both):
            d = (both.threshold_hand_m_noah - both.threshold_hand_m_noaa).abs()
            log.info(
                "check vs NOAA on %d shared (seg, HydroID): median |dHAND| %.2f m, within 0.5 m: %.0f%%",
                len(both),
                d.median(),
                100 * (d <= 0.5).mean(),
            )
        extra = ours[~ours.seg_id.isin(set(out.seg_id))].assign(source="noah")
        log.info(
            "Noah thresholds for %d segments NOAA doesn't list (%d rows)",
            extra.seg_id.nunique(),
            len(extra),
        )
        out = pd.concat([out, extra], ignore_index=True)
    out.to_parquet(SEG_THRESHOLDS, index=False)
    eligible = len(in_aoi) - n_bridge
    log.info(
        "AOI edges %d (bridge/tunnel %d); with NOAA threshold %d (%.0f%% of eligible); "
        "crossing artifacts dropped (hand < %.1f m): %d rows / %d segments; C3 rows %d",
        len(in_aoi),
        n_bridge,
        raw.seg_id.nunique(),
        100 * raw.seg_id.nunique() / max(1, eligible),
        config.MIN_ROAD_HAND_M,
        len(raw) - n_noaa_rows,
        raw.seg_id.nunique() - n_noaa_segs,
        len(out),
    )


def write_streams() -> None:
    """C14 web/data/streams.geojson: NWM creeks/rivers in the AOI + 2 km (map context: red roads next to blue water)."""
    s = gpd.read_file(config.DATA_RAW / "hand" / config.HUC8 / config.FIM_FILES["streams"])
    area = gpd.GeoSeries([aoi_polygon()], crs=4326).to_crs(s.crs).buffer(2000).iloc[0]
    s = s[s.intersects(area)].copy()
    s["geometry"] = s.geometry.intersection(area).simplify(10)
    s = s[~s.geometry.is_empty]
    out = gpd.GeoDataFrame(
        {"feature_id": s.ID.astype("int64"), "order": s.order_.astype(int)},
        geometry=s.geometry,
        crs=s.crs,
    ).to_crs(4326)
    out["geometry"] = shapely.set_precision(out.geometry.values, 1e-5)
    (config.WEB_DATA / "streams.geojson").write_text(out.to_json(drop_id=True))
    log.info("streams: %d reaches -> web/data/streams.geojson", len(out))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--step", choices=["1", "2", "streams", "all"], default="all")
    p.add_argument(
        "--noaa-only", action="store_true", help="fallback: skip Noah residential thresholds (CC4)"
    )
    a = p.parse_args()
    if a.step in ("1", "all"):
        step1_graph()
    if a.step in ("2", "all"):
        step2_thresholds(a.noaa_only)
    if a.step in ("streams", "all"):
        write_streams()


if __name__ == "__main__":
    main()
