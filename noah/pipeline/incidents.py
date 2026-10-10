"""BL-21 (revised): log TomTom traffic incidents in the AOI during Isaias, for ground-truth matching later.

TomTom incidents are live-only (no archive), so snapshot them while the storm happens. Keeps closures (8),
flooding (11) and dangerous conditions (3); other categories are dropped. One JSON per snapshot.

Reads:  TOMTOM_API_KEY from .env, web/data/aoi.geojson
Writes: data/interim/incidents/<YYYYMMDDTHHMMZ>.json  ([{id, category, description, from, to, coords}])
Run:    uv run python -m noah.pipeline.incidents --every 900     (alongside the live loop on Saturday)
"""

import argparse
import json
import logging
import os
import time
from datetime import UTC, datetime

import httpx
from dotenv import load_dotenv
from shapely.geometry import LineString, Point

from noah import config

log = logging.getLogger("incidents")
OUT = config.DATA_INTERIM / "incidents"
KEEP_CATEGORIES = {3: "dangerous_conditions", 8: "road_closed", 11: "flooding"}
URL = "https://api.tomtom.com/traffic/services/5/incidentDetails"
FIELDS = "{incidents{type,geometry{type,coordinates},properties{id,iconCategory,from,to,events{description,code}}}}"


def keep(incidents: list[dict], aoi) -> list[dict]:
    """TomTom incidents -> the flood-relevant ones that touch the AOI, flattened."""
    out = []
    for inc in incidents:
        p, g = inc.get("properties", {}), inc.get("geometry", {})
        cat = p.get("iconCategory")
        if cat not in KEEP_CATEGORIES or not g.get("coordinates"):
            continue
        geom = Point(g["coordinates"]) if g.get("type") == "Point" else LineString(g["coordinates"])
        if not geom.intersects(aoi):
            continue
        out.append(
            {
                "id": p.get("id"),
                "category": KEEP_CATEGORIES[cat],
                "description": "; ".join(e.get("description", "") for e in p.get("events") or []),
                "from": p.get("from"),
                "to": p.get("to"),
                "coords": g["coordinates"],
            }
        )
    return out


def snapshot(client: httpx.Client, key: str, aoi) -> int:
    minx, miny, maxx, maxy = aoi.bounds
    r = client.get(
        URL,
        params={
            "key": key,
            "bbox": f"{minx},{miny},{maxx},{maxy}",
            "fields": FIELDS,
            "language": "en-US",
            "categoryFilter": ",".join(map(str, KEEP_CATEGORIES)),
        },
    )
    r.raise_for_status()
    rows = keep(r.json().get("incidents", []), aoi)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%MZ")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{ts}.json").write_text(json.dumps(rows))
    counts = {c: sum(1 for x in rows if x["category"] == c) for c in KEEP_CATEGORIES.values()}
    log.info("%s: %s", ts, counts)
    return len(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--once", action="store_true")
    g.add_argument("--every", type=int, help="seconds between snapshots")
    a = p.parse_args()
    load_dotenv(config.ROOT / ".env")
    key = os.environ.get("TOMTOM_API_KEY")
    if not key:
        raise SystemExit("TOMTOM_API_KEY missing in .env")
    aoi = config.aoi_union((config.WEB_DATA / "aoi.geojson").read_text())
    with httpx.Client(timeout=30) as client:
        while True:
            try:
                snapshot(client, key, aoi)
            except Exception:
                log.exception("snapshot failed")
            if a.once:
                return
            time.sleep(a.every)


if __name__ == "__main__":
    main()
