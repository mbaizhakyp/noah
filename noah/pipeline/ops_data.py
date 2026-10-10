"""J21: inputs for Noah Operations, fetched once from OpenStreetMap (Overpass, ODbL: credit "© OpenStreetMap contributors").

- web/data/facilities.geojson: schools, hospitals, clinics, nursing homes, fire stations and police inside the AOI.
- web/data/waterways.geojson: named rivers, creeks and canals, so a flagged road can say which creek overtops it.
- web/data/svi_tracts.geojson: census tracts touching the AOI with CDC/ATSDR Social Vulnerability Index 2022 (RPL_THEMES =
  national percentile, 1 = most vulnerable), population and households without a vehicle (public domain, CDC).

Run: uv run python -m noah.pipeline.ops_data          (all)
     uv run python -m noah.pipeline.ops_data svi      (SVI tracts only)
"""

import json
import logging
import sys

import httpx
from shapely.geometry import Point, mapping, shape

from noah import config

log = logging.getLogger("ops_data")
OVERPASS = "https://overpass-api.de/api/interpreter"
SVI_URL = "https://onemap.cdc.gov/onemapservices/rest/services/SVI/CDC_ATSDR_Social_Vulnerability_Index_2022_USA/FeatureServer/2/query"
UA = {"User-Agent": "noah-hacklanta/0.1 (+https://github.com/mbaizhakyp/noah)"}
KINDS = {
    "hospital": "Hospital",
    "clinic": "Clinic",
    "nursing_home": "Nursing home",
    "school": "School",
    "fire_station": "Fire station",
    "police": "Police",
}


def overpass(query: str) -> list[dict]:
    r = httpx.post(OVERPASS, data={"data": query}, headers=UA, timeout=180)
    r.raise_for_status()
    return r.json()["elements"]


def svi_tracts(aoi) -> None:
    w, s, e, n = aoi.bounds
    feats, offset = [], 0
    while True:
        r = httpx.get(
            SVI_URL,
            params={
                "geometry": f"{w},{s},{e},{n}",
                "geometryType": "esriGeometryEnvelope",
                "inSR": 4326,
                "outSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "FIPS,LOCATION,RPL_THEMES,E_TOTPOP,E_NOVEH",
                "resultOffset": offset,
                "f": "geojson",
            },
            headers=UA,
            timeout=120,
        )
        r.raise_for_status()
        page = r.json()
        feats += page["features"]
        offset += len(page["features"])
        if not page.get("properties", {}).get("exceededTransferLimit") or not page["features"]:
            break
    out = []
    for f in feats:
        g, p = shape(f["geometry"]), f["properties"]
        rpl = p.get("RPL_THEMES")
        if g.intersects(aoi) and rpl is not None and rpl >= 0:  # -999 = no estimate
            out.append(
                {
                    "type": "Feature",
                    "geometry": mapping(g.simplify(0.0002)),
                    "properties": {
                        "fips": p["FIPS"],
                        "name": p["LOCATION"],
                        "rpl": round(rpl, 3),
                        "pop": p["E_TOTPOP"],
                        "no_vehicle_hh": p["E_NOVEH"],
                    },
                }
            )
    (config.WEB_DATA / "svi_tracts.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": out})
    )
    log.info("svi: %d tracts touch the AOI", len(out))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    aoi = config.aoi_union((config.WEB_DATA / "aoi.geojson").read_text())
    svi_tracts(aoi)
    if sys.argv[1:] == ["svi"]:
        return
    w, s, e, n = aoi.bounds
    bbox = f"{s},{w},{n},{e}"
    kinds = "|".join(KINDS)
    els = overpass(f'[out:json][timeout:120];nwr["amenity"~"^({kinds})$"]({bbox});out center tags;')
    feats = []
    for el in els:
        lat, lon = (
            (el["lat"], el["lon"]) if "lat" in el else (el["center"]["lat"], el["center"]["lon"])
        )
        tags = el.get("tags", {})
        if not tags.get("name") or not aoi.contains(Point(lon, lat)):
            continue
        feats.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
                "properties": {
                    "id": f"{el['type'][0]}{el['id']}",
                    "name": tags["name"],
                    "kind": KINDS[tags["amenity"]],
                },
            }
        )
    (config.WEB_DATA / "facilities.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats})
    )
    log.info("facilities: %d named inside the AOI", len(feats))

    els = overpass(
        f'[out:json][timeout:180];way["waterway"~"^(river|stream|canal)$"]["name"]({bbox});out geom tags;'
    )
    ways = []
    for el in els:
        g = shape(
            {
                "type": "LineString",
                "coordinates": [[p["lon"], p["lat"]] for p in el.get("geometry", [])],
            }
        )
        if g.length and g.intersects(aoi):
            ways.append(
                {
                    "type": "Feature",
                    "geometry": mapping(g.simplify(0.00005)),
                    "properties": {"name": el["tags"]["name"], "kind": el["tags"]["waterway"]},
                }
            )
    (config.WEB_DATA / "waterways.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": ways})
    )
    log.info("waterways: %d named ways", len(ways))


if __name__ == "__main__":
    main()
