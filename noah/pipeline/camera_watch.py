"""BL-22: camera bonus. Watch traffic cameras next to forecast-flagged roads and creek crossings during Isaias.

Every pass: build the watch list (Windy cameras within 150 m of a road in the newest live C5, or within 100 m
of a creek), run Priyanshu's two-look AI water check (photo.verified) on each current snapshot, and log the
verdict (never the image) to data/interim/camera_checks.jsonl. When water is confirmed, compose an
"evidence card" PNG (camera image + Windy credit + Noah's forecast for that road + AI verdict) in
data/interim/evidence/ for the demo video and slides only (not published), and send a desktop notification.

Run: caffeinate -i uv run python -m noah.pipeline.camera_watch --every 1500
     uv run python -m noah.pipeline.camera_watch --test-card   (render one card from a live camera now)
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from io import BytesIO

import geopandas as gpd
import httpx
import pandas as pd
from dotenv import load_dotenv
from shapely.geometry import Point

from noah import config
from noah.pipeline.route_watch import ROUTES

log = logging.getLogger("camera_watch")
WINDY = "https://api.windy.com/webcams/api/v3/webcams"
CAMS_CACHE = config.DATA_INTERIM / "cameras_aoi.json"
CHECKS = config.DATA_INTERIM / "camera_checks.jsonl"
EVIDENCE = config.DATA_INTERIM / "evidence"
NEAR_ROAD_M, NEAR_CREEK_M, REALERT_H = 150, 100, 2
ET = "America/New_York"


# ---------- pure helpers ----------


def segment_state(
    props: dict, issue: pd.Timestamp, now: pd.Timestamp
) -> tuple[str, pd.Timestamp | None]:
    """Forecast state of a C5 segment at `now`, and when it floods (or turns uncertain)."""
    h = (now - issue).total_seconds() / 3600
    tf, tu = props.get("t_flood"), props.get("t_uncertain")
    when = issue + pd.Timedelta(hours=tf if tf is not None else tu)
    if tf is not None and tf <= h:
        return "flooded", when
    if tu is not None and tu <= h:
        return "uncertain", when
    return "forecast later" if tu is not None else "no forecast flooding", when


def due_alert(last: dict, cam_id: str, now: datetime, hours: int = REALERT_H) -> bool:
    t = last.get(cam_id)
    return t is None or now - t >= timedelta(hours=hours)


def watch_list(
    cams: gpd.GeoDataFrame, c5: gpd.GeoDataFrame, streams: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """Cameras near a flagged road (with that road's props) or near a creek. All inputs EPSG:5070."""
    near = gpd.sjoin_nearest(cams, c5, max_distance=NEAR_ROAD_M, how="left", distance_col="road_m")
    near = near[~near.index.duplicated()]
    creek = cams.geometry.apply(lambda p: streams.distance(p).min() <= NEAR_CREEK_M)
    return near[near.road_m.notna() | creek]


# ---------- I/O ----------


def list_cameras(client: httpx.Client, key: str, aoi) -> list[dict]:
    """All Windy cameras inside the AOI (cached 6 h)."""
    if CAMS_CACHE.exists() and time.time() - CAMS_CACHE.stat().st_mtime < 6 * 3600:
        return json.loads(CAMS_CACHE.read_text())
    minx, miny, maxx, maxy = aoi.bounds
    out, off = [], 0
    while off < 1000:
        r = client.get(
            WINDY,
            headers={"x-windy-api-key": key},
            params={
                "bbox": f"{maxy},{maxx},{miny},{minx}",
                "limit": 50,
                "offset": off,
                "include": "location",
            },
        )
        r.raise_for_status()
        batch = r.json().get("webcams", [])
        out += [
            {
                "id": w["webcamId"],
                "title": w.get("title", ""),
                "lon": w["location"]["longitude"],
                "lat": w["location"]["latitude"],
            }
            for w in batch
            if aoi.contains(Point(w["location"]["longitude"], w["location"]["latitude"]))
        ]
        if len(batch) < 50:
            break
        off += 50
        time.sleep(1)
    CAMS_CACHE.write_text(json.dumps(out))
    return out


def fresh_images(client: httpx.Client, key: str, ids: list) -> dict:
    """cam id -> {preview, page}; image URLs expire in ~10 min, so fetch right before checking."""
    out = {}
    for i in range(0, len(ids), 50):
        r = client.get(
            WINDY,
            headers={"x-windy-api-key": key},
            params={
                "webcamIds": ",".join(map(str, ids[i : i + 50])),
                "include": "images,urls",
                "limit": 50,
            },
        )
        r.raise_for_status()
        for w in r.json().get("webcams", []):
            img = (w.get("images") or {}).get("current") or {}
            out[w["webcamId"]] = {
                "preview": img.get("preview"),
                "page": (w.get("urls") or {}).get("detail"),
            }
        time.sleep(1)
    return out


def newest_live_c5() -> tuple[str, pd.Timestamp, gpd.GeoDataFrame]:
    c6 = json.loads((config.WEB_DATA / "cycles.json").read_text())
    live = sorted(c["cycle"] for c in c6["cycles"] if c.get("event") == "live")
    if not live:
        raise SystemExit("no live cycle in cycles.json: run the live loop first")
    cyc = live[-1]
    c5 = gpd.read_file(config.WEB_DATA / f"flood_{cyc}.geojson").to_crs(5070)
    return cyc, pd.Timestamp(config.parse_cycle(cyc)), c5


def evidence_card(image_url: str, cam: dict, verdict: dict, road: str, now: pd.Timestamp) -> str:
    """Compose the demo evidence PNG (image + Windy credit + forecast vs camera). Returns the path."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(BytesIO(httpx.get(image_url, timeout=15).content)).convert("RGB")
    img = img.resize((800, int(img.height * 800 / img.width)))
    card = Image.new("RGB", (840, img.height + 230), "#0b0f14")
    card.paste(img, (20, 20))
    d = ImageDraw.Draw(card)
    try:
        big, small = ImageFont.load_default(size=22), ImageFont.load_default(size=16)
    except TypeError:  # older Pillow
        big = small = ImageFont.load_default()
    y = img.height + 32
    lines = [
        (
            f"Camera: {cam['title'] or cam['id']}  ·  {now.tz_convert(ET):%a %b %d, %I:%M %p} ET",
            big,
            "#e6edf3",
        ),
        (
            (
                f"AI check (two looks): water at {verdict['bucket'].replace('_', ' ')} level, "
                f"confidence {verdict['confidence']}. {verdict.get('note') or ''}"
            ),
            small,
            "#22d3ee",
        ),
        (road, small, "#f59e0b"),
        (
            "Webcams provided by Windy.com  ·  Noah demo evidence (not for publication)",
            small,
            "#8b9bb0",
        ),
    ]
    for text, font, color in lines:
        d.text((24, y), text[:110], font=font, fill=color)
        y += 40
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / f"{now:%Y%m%dT%H%MZ}_{cam['id']}.png"
    card.save(path)
    return str(path)


def notify(title: str, msg: str) -> None:
    subprocess.run(
        [
            "osascript",
            "-e",
            f"display notification {json.dumps(msg)} with title {json.dumps(title)}",
        ],
        check=False,
        capture_output=True,
    )
    topic = os.environ.get("NTFY_TOPIC")  # optional phone push (ntfy app), off unless set in .env
    if topic:
        httpx.post(
            f"https://ntfy.sh/{topic}", content=msg.encode(), headers={"Title": title}, timeout=10
        )


def run_pass(client, key: str, aoi, last_alert: dict, force_card: bool = False) -> None:
    from noah.api.photo import verified  # Priyanshu's two-look check (spec 010)

    cyc, issue, c5 = newest_live_c5()
    cams = list_cameras(client, key, aoi)
    cg = gpd.GeoDataFrame(
        cams, geometry=[Point(c["lon"], c["lat"]) for c in cams], crs=4326
    ).to_crs(5070)
    streams = gpd.read_file(config.WEB_DATA / "streams.geojson").to_crs(5070)
    w = watch_list(cg, c5[["seg_id", "name", "t_flood", "t_uncertain", "geometry"]], streams)
    if ROUTES.exists():  # spec 017: route-watch cameras are always watched
        rc = {c["id"] for r in json.loads(ROUTES.read_text())["routes"] for c in r["cams"]}
        w = pd.concat([w, cg[cg.id.isin(rc) & ~cg.id.isin(w.id)]])
    if force_card:
        w = cg.head(1).assign(road_m=None, name=None, t_flood=None, t_uncertain=None)
    imgs = fresh_images(client, key, list(w["id"]))
    now = pd.Timestamp.now(tz=UTC)
    log.info("cycle %s: %d cameras in AOI, watching %d", cyc, len(cg), len(w))
    with open(CHECKS, "a") as fh:
        for r in w.itertuples():
            url = (imgs.get(r.id) or {}).get("preview")
            if not url:
                continue
            v = (
                {"bucket": "none", "confidence": "high", "verified": True, "note": "TEST CARD"}
                if force_card
                else verified(url)
            )
            road = "No forecast-flagged road within 150 m of this camera."
            if isinstance(r.name, str) or pd.notna(r.road_m):
                state, when = segment_state(
                    {
                        "t_flood": None if pd.isna(r.t_flood) else int(r.t_flood),
                        "t_uncertain": int(r.t_uncertain),
                    },
                    issue,
                    now,
                )
                road = (
                    f"Noah forecast (run issued {issue.tz_convert(ET):%a %I %p}): {r.name or 'road'} "
                    f"{int(r.road_m)} m away is '{state}', flooding from ~{when.tz_convert(ET):%a %I %p}."
                )
            path = None
            if v.get("verified") and (
                force_card or due_alert(last_alert, r.id, now.to_pydatetime())
            ):
                path = evidence_card(url, {"id": r.id, "title": r.title}, v, road, now)
                last_alert[r.id] = now.to_pydatetime()
                notify(
                    "Noah camera: water seen" if not force_card else "Noah camera: test card",
                    f"{r.title or r.id}: {v['bucket'].replace('_', ' ')}. Saved {os.path.basename(path)}",
                )
                log.info("EVIDENCE %s -> %s", r.id, path)
            fh.write(
                json.dumps(
                    {
                        "ts": now.isoformat(),
                        "cam_id": r.id,
                        "title": r.title,
                        "lat": r.lat,
                        "lon": r.lon,
                        "cycle": cyc,
                        "road": road,
                        **{k: v.get(k) for k in ("bucket", "confidence", "verified", "note")},
                        "evidence": path,  # spec 017: route_watch sends this card by iMessage
                    }
                )
                + "\n"
            )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--once", action="store_true")
    g.add_argument("--every", type=int, help="seconds between passes (e.g. 1500 = 25 min)")
    g.add_argument(
        "--test-card", action="store_true", help="render one evidence card from a live camera now"
    )
    a = p.parse_args()
    load_dotenv(config.ROOT / ".env")
    key = os.environ.get("WINDY_API_KEY") or sys.exit("WINDY_API_KEY missing in .env")
    aoi = config.aoi_union((config.WEB_DATA / "aoi.geojson").read_text())
    last: dict = {}
    with httpx.Client(timeout=30) as client:
        while True:
            try:
                run_pass(client, key, aoi, last, force_card=a.test_card)
            except Exception:
                log.exception("camera pass failed")
            if a.once or a.test_card:
                return
            time.sleep(a.every)


if __name__ == "__main__":
    main()
