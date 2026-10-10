"""J21: inputs for Noah Operations, fetched once from OpenStreetMap (Overpass, ODbL: credit "© OpenStreetMap contributors").

- web/data/facilities.geojson: schools, hospitals, clinics, nursing homes, fire stations and police inside the AOI.
- web/data/waterways.geojson: named rivers, creeks and canals, so a flagged road can say which creek overtops it.

Run: uv run python -m noah.pipeline.ops_data
"""

import json
import logging

import httpx
from shapely.geometry import Point, mapping, shape

from noah import config

log = logging.getLogger("ops_data")
OVERPASS = "https://overpass-api.de/api/interpreter"
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


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    aoi = config.aoi_union((config.WEB_DATA / "aoi.geojson").read_text())
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
