"""Spec 002: HAND + catchment rasters and synthetic rating curves for HUC8 03130001.

Reads:  public CIROH bucket (OWP HAND-FIM v4.9.9.0), WBD HUC10 polygon.
Writes: data/raw/hand/03130001/<bucket files>, data/interim/aoi.geojson,
        C2 data/interim/rating.parquet (hydro_id, feature_id, stage_m, q_cms) for AOI HydroIDs.
"""

import argparse
import json
import logging

import httpx
import numpy as np
import pandas as pd
import rasterio
import shapely
from pyproj import Transformer
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds
from shapely.geometry import mapping, shape

from noah import config

log = logging.getLogger("fetch_hand")
RAW = config.DATA_RAW / "hand" / config.HUC8
DOWNLOAD = ["hand", "catchments", "hydroid_prefix", "hydrotable_huc", "fimpact", "streams"]


def download(name: str, client: httpx.Client) -> None:
    rel = config.FIM_FILES.get(name, name)
    dest = RAW / rel
    url = f"{config.FIM_BASE}/{rel}"
    size = int(client.head(url).raise_for_status().headers["content-length"])
    if dest.exists() and dest.stat().st_size == size:
        log.info("have %s (%.1f MB)", rel, size / 1e6)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    with client.stream("GET", url) as r, open(dest, "wb") as f:
        r.raise_for_status()
        f.writelines(r.iter_bytes(1 << 20))
    log.info("downloaded %s (%.1f MB)", rel, size / 1e6)


def aoi_geometry(client: httpx.Client) -> dict:
    out = config.DATA_INTERIM / "aoi.geojson"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        gj = client.get(config.WBD_HUC10_URL).raise_for_status().json()
        for f in gj["features"]:
            f["properties"]["huc8"] = (
                config.HUC8
            )  # routing.coverage() reads features with huc8 (I13)
        if len(gj["features"]) != len(config.AOI_HUC10S):
            raise SystemExit(
                f"WBD returned {len(gj['features'])} HUC10s, expected {len(config.AOI_HUC10S)}"
            )
        out.write_text(json.dumps(gj))
    return mapping(config.aoi_union(out.read_text()))


def hydroid_prefix() -> int:
    """Catchment rasters store the short ID; HydroID = prefix * 10000 + raster value (FIM convention)."""
    return int((RAW / config.FIM_FILES["hydroid_prefix"]).read_text().strip()) * 10000


def aoi_hydro_ids(aoi_4326: dict) -> np.ndarray:
    """HydroIDs whose catchment pixels fall inside the AOI polygon."""
    with rasterio.open(RAW / config.FIM_FILES["catchments"]) as src:
        to_src = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
        geom = shapely.transform(
            shape(aoi_4326), lambda xy: np.column_stack(to_src.transform(xy[:, 0], xy[:, 1]))
        )
        win = from_bounds(*geom.bounds, transform=src.transform).round_offsets().round_lengths()
        arr = src.read(1, window=win)
        inside = geometry_mask(
            [mapping(geom)], out_shape=arr.shape, transform=src.window_transform(win), invert=True
        )
        vals = arr[inside & (arr != src.nodata) & (arr > 0)]
    return np.unique(vals).astype("int64") + hydroid_prefix()


def clean_rating(ht: pd.DataFrame, hydro_ids: np.ndarray | None = None) -> pd.DataFrame:
    """FIM hydrotable -> C2. Keeps branch 0 (our rasters), optional HydroID filter, monotonic curves only."""
    df = ht.reset_index() if "HydroID" not in ht.columns else ht
    if "branch_id" in df.columns:
        df = df[pd.to_numeric(df.branch_id) == int(config.FIM_BRANCH)]
    out = pd.DataFrame(
        {
            "hydro_id": pd.to_numeric(df.HydroID).astype("int64"),
            "feature_id": pd.to_numeric(df.feature_id).astype("int64"),
            "stage_m": df.stage.astype("float32"),
            "q_cms": df.discharge_cms.astype("float32"),
        }
    )
    if hydro_ids is not None:
        out = out[out.hydro_id.isin(hydro_ids)]
    out = out.sort_values(["hydro_id", "stage_m"], ignore_index=True)
    ok = out.groupby("hydro_id").q_cms.apply(lambda q: bool((q.diff().dropna() >= 0).all()))
    bad = ok.index[~ok]
    if len(bad):
        log.warning("dropping %d non-monotonic rating curves: %s", len(bad), list(bad[:10]))
    return out[out.hydro_id.isin(ok.index[ok])].reset_index(drop=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.parse_args()
    with httpx.Client(timeout=300, follow_redirects=True) as client:
        for name in DOWNLOAD:
            download(name, client)
        for b in config.FIM_BRANCHES[1:]:  # level-path branches for residential thresholds (CC4)
            for rel in config.fim_branch_files(b).values():
                download(rel, client)
        aoi = aoi_geometry(client)

    for name in ("hand", "catchments"):
        with rasterio.open(RAW / config.FIM_FILES[name]) as src:
            log.info(
                "%s: crs=%s res=%s bounds=%s nodata=%s",
                name,
                src.crs,
                src.res,
                src.bounds,
                src.nodata,
            )

    ids = aoi_hydro_ids(aoi)
    ht = pd.read_parquet(RAW / config.FIM_FILES["hydrotable_huc"])
    rating = clean_rating(ht, ids)
    out = config.DATA_INTERIM / "rating.parquet"
    rating.to_parquet(out, index=False)
    missing = sorted(set(ids) - set(rating.hydro_id))
    log.info(
        "AOI HydroIDs in raster: %d; with rating curves: %d (%d missing); reaches: %d; rows: %d",
        len(ids),
        rating.hydro_id.nunique(),
        len(missing),
        rating.feature_id.nunique(),
        len(rating),
    )
    g = rating[rating.feature_id == config.GAUGE_FEATURE_ID]
    for hid, c in g.groupby("hydro_id"):
        pts = c.iloc[:: max(1, len(c) // 6)]
        log.info(
            "gauge reach HydroID %d: %s",
            hid,
            [(round(s, 1), round(q)) for s, q in zip(pts.stage_m, pts.q_cms)],
        )

    fp = pd.read_csv(RAW / config.FIM_FILES["fimpact"], nrows=5)
    log.info("osm_roads_fimpact.csv columns: %s", list(fp.columns))
    print(fp.to_string())


if __name__ == "__main__":
    main()
