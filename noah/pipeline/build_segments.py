"""Spec 003: AOI, drivable road graph, and NOAA per-road flood thresholds (CC3).

Reads:  WBD HUC10 polygon (via data/interim/aoi.geojson), OSM via OSMnx,
        FIM 4.9 osm_roads_fimpact.csv (per OSM way x HydroID flood thresholds).
Writes: C7 web/data/aoi.geojson, C4 data/interim/graph.graphml,
        C3 data/interim/seg_thresholds.parquet
          (seg_id, hydro_id, feature_id, branch_id, threshold_hand_m, threshold_q_cms)
"""

import argparse
import json
import logging
import shutil

import geopandas as gpd
import osmnx as ox
import pandas as pd
from shapely.geometry import shape

from noah import config

log = logging.getLogger("build_segments")
GRAPH = config.DATA_INTERIM / "graph.graphml"
SEG_THRESHOLDS = config.DATA_INTERIM / "seg_thresholds.parquet"
FIXTURE_MAX_MB = 20


def aoi_polygon():
    src = config.DATA_INTERIM / "aoi.geojson"
    if not src.exists():
        raise SystemExit(f"{src} missing: run fetch_hand (spec 002) first, it fetches the HUC10")
    return shape(json.loads(src.read_text())["features"][0]["geometry"])


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


def step2_thresholds() -> None:
    G = ox.load_graphml(GRAPH)
    edges = ox.graph_to_gdfs(G, nodes=False).reset_index(drop=True)
    in_aoi = edges[edges.intersects(aoi_polygon())]
    n_bridge = int(
        sum(in_aoi[t].map(truthy_tag).sum() for t in ("bridge", "tunnel") if t in in_aoi)
    )
    fimpact = pd.read_csv(config.DATA_RAW / "hand" / config.HUC8 / config.FIM_FILES["fimpact"])
    raw = edge_thresholds(in_aoi, fimpact, min_hand_m=0.0)
    out = edge_thresholds(in_aoi, fimpact, config.MIN_ROAD_HAND_M)
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
        len(raw) - len(out),
        raw.seg_id.nunique() - out.seg_id.nunique(),
        len(out),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--step", choices=["1", "2", "all"], default="all")
    a = p.parse_args()
    if a.step in ("1", "all"):
        step1_graph()
    if a.step in ("2", "all"):
        step2_thresholds()


if __name__ == "__main__":
    main()
