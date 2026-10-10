"""Spec 015 adapters, tier 2/3: cameras, NOAA flood products, rain totals and guidance, rarity,
dams, insurance history, critical facilities, sewage/CSO, potholes and road condition, news.

Same contract as adapters.py: fetch(ctx) -> list[signal], cached, failures isolated.
"""

import csv
import io
import os
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from functools import lru_cache

import pandas as pd

from noah.api import photo
from noah.sources import Ctx, adapter, haversine_m, http, signal
from noah.sources.adapters import local

NWM = "https://maps.water.noaa.gov/server/rest/services/nwm"
MM_PER_IN = 25.4


def esri_query(url: str, ctx: Ctx | None = None, point=None, fields="*", count=200) -> list[dict]:
    """ArcGIS REST query by the ctx bbox (or a point). Returns attribute dicts."""
    if point:
        geom, gtype = f"{point[1]},{point[0]}", "esriGeometryPoint"
    else:
        x0, y0, x1, y1 = ctx.bbox
        geom, gtype = f"{x0},{y0},{x1},{y1}", "esriGeometryEnvelope"
    r = http.get(
        url,
        params={
            "geometry": geom,
            "geometryType": gtype,
            "inSR": 4326,
            "outSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": fields,
            "returnGeometry": "true" if not point else "false",
            "resultRecordCount": count,
            "f": "json",
        },
    )
    r.raise_for_status()
    d = r.json()
    if "error" in d:
        raise RuntimeError(d["error"].get("message"))
    return d.get("features", [])


def centroid(f: dict) -> tuple[float, float] | None:
    g = f.get("geometry") or {}
    if "x" in g:
        return g["y"], g["x"]
    pts = [p for path in g.get("paths", []) + g.get("rings", []) for p in path]
    if not pts:
        return None
    return sum(p[1] for p in pts) / len(pts), sum(p[0] for p in pts) / len(pts)


def in_ctx(ctx: Ctx, f: dict, extra_m: float = 0) -> bool:
    c = centroid(f)
    return c is None or ctx.contains(c[0], c[1], extra_m)


@lru_cache(maxsize=256)
def county_at(lat: float, lon: float) -> str | None:
    """County name at a point (TIGERweb, docs/07 #81)."""
    r = http.get(
        "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query",
        params={
            "geometry": f"{lon},{lat}",
            "geometryType": "esriGeometryPoint",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "BASENAME,STATE",
            "returnGeometry": "false",
            "f": "json",
        },
    )
    r.raise_for_status()
    f = r.json().get("features") or []
    return f[0]["attributes"]["BASENAME"] if f else None


# ---------------------------------------------------------------- cameras (010 + 013)

_cam_cache: dict = {}


@adapter("Traffic cameras", ttl=600)  # docs/07 #31 (Windy) + spec 010 AI vision
def cameras(ctx: Ctx) -> list[dict]:
    key = os.environ.get("WINDY_API_KEY")
    if not key:
        raise RuntimeError("WINDY_API_KEY missing")
    cams = {}
    for lat, lon in ctx.points(step_km=8):
        r = http.get(
            "https://api.windy.com/webcams/api/v3/webcams",
            headers={"x-windy-api-key": key},
            params={
                "nearby": f"{lat:.4f},{lon:.4f},{ctx.radius_km if ctx.kind == 'area' else 5}",
                "limit": 50,
                "include": "location,images,urls",
            },
        )
        r.raise_for_status()
        for w in r.json().get("webcams", []):
            if w.get("status") != "active":
                continue
            loc = w["location"]
            d = ctx.distance_m(loc["latitude"], loc["longitude"])
            if ctx.contains(loc["latitude"], loc["longitude"]):
                cams[w["webcamId"]] = (d, w)
    ranked = [w for _, w in sorted(cams.values(), key=lambda x: x[0])]
    if ctx.kind == "route" and len(ranked) > 8:  # spread along the route, not all at one end
        step = len(ranked) / 8
        ranked = [ranked[int(i * step)] for i in range(8)]
    pick = ranked[:5] if ctx.kind == "area" else ranked[:8]

    def check(w):
        cid = w["webcamId"]
        hit = _cam_cache.get(cid)
        if hit and hit[0] > datetime.now(UTC):
            return w, hit[1]
        res = photo.verified(w["images"]["current"]["preview"])
        _cam_cache[cid] = (datetime.now(UTC) + timedelta(minutes=10), res)
        return w, res

    out = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for w, res in pool.map(check, pick):
            loc = w["location"]
            b = res["bucket"]
            if b in photo.WET and res.get("verified") is not True:
                b = "possible_water"  # seen once, not confirmed: caution only, never blocks a road
            sev = {
                "door_sill_or_above": "danger",
                "half_tire": "danger",
                "curb": "warning",
                "possible_water": "watch",
            }.get(b, "info")
            seen = {
                "none": "no water on the road seen",
                "cant_tell": "can't tell from the image",
                "possible_water": "possible water near the road, not confirmed",
            }.get(b, f"water on the road around {b.replace('_', ' ')} level (confirmed twice)")
            out.append(
                signal(
                    "Traffic cameras",
                    "observation",
                    f"Camera {w['title']}: {seen}",
                    detail=f"{res.get('note') or ''} (AI check of the current snapshot, confidence {res['confidence']}). Webcams provided by Windy.com.".strip(),
                    severity=sev,
                    lat=loc["latitude"],
                    lon=loc["longitude"],
                    url=w["urls"]["detail"],
                    extra={
                        "camera": {
                            "cam_id": w["webcamId"],
                            "name": w["title"],
                            "bucket": b,
                            "confidence": res["confidence"],
                            "reference_object": res.get("reference_object"),
                            "image_url": w["images"]["current"]["preview"],
                            "page_url": w["urls"]["detail"],
                            "checked_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "distance_m": round(ctx.distance_m(loc["latitude"], loc["longitude"])),
                        }
                    },
                )
            )
    return out


# ---------------------------------------------------------------- NOAA National Water Model flood products


@adapter("NWM rapid-onset flooding (18 h)", ttl=1800)  # docs/07 #6
def nwm_rapid_onset(ctx: Ctx) -> list[dict]:
    feats = [
        f
        for f in esri_query(f"{NWM}/srf_18hr_rapid_onset_flooding/MapServer/0/query", ctx)
        if in_ctx(ctx, f, 2000)
    ]
    if not feats:
        return []
    a = sorted((f["attributes"] for f in feats), key=lambda a: a["flood_start_hour"])
    names = sorted({x["name"] for x in a if x["name"] != "Unnamed Stream"})[:4]
    first = a[0]
    return [
        signal(
            "NWM rapid-onset flooding (18 h)",
            "forecast",
            f"{len(a)} creek reaches forecast to rise fast and flood in the next 18 h",
            detail=f"Earliest starts {local(first['flood_start_time'].replace(' ', 'T') + 'Z')} (flow up {round(first['flood_percent_increase'])}%). "
            f"Named creeks: {', '.join(names) or 'small unnamed streams'}.",
            value=len(a),
            units="reaches",
            severity="warning",
            url="https://water.noaa.gov/map",
        )
    ]


@adapter("NWM high-water probability (12 h)", ttl=1800)  # docs/07 #6
def nwm_hw_prob(ctx: Ctx) -> list[dict]:
    feats = [
        f
        for f in esri_query(f"{NWM}/srf_12hr_max_high_water_probability/MapServer/0/query", ctx)
        if in_ctx(ctx, f, 2000)
    ]
    if not feats:
        return []
    probs = sorted((f["attributes"]["hw_prob_all"], f["attributes"]["name"]) for f in feats)
    top = probs[-1]
    n50 = sum(p >= 50 for p, _ in probs)
    sev = "warning" if top[0] >= 50 else "watch" if top[0] >= 25 else "info"
    return [
        signal(
            "NWM high-water probability (12 h)",
            "forecast",
            f"Up to {round(top[0])}% chance of high water on nearby creeks in 12 h",
            detail=f"{len(probs)} creek reaches with a high-water chance; {n50} at 50% or more. Highest: {top[1]} {round(top[0])}%.",
            value=round(top[0]),
            units="%",
            severity=sev,
        )
    ]


@adapter("NWM high-flow magnitude (18 h)", ttl=1800)  # docs/07 #6
def nwm_high_flow(ctx: Ctx) -> list[dict]:
    feats = [
        f
        for f in esri_query(f"{NWM}/srf_18hr_max_high_flow_magnitude/MapServer/0/query", ctx)
        if in_ctx(ctx, f, 2000)
    ]
    over = [
        f["attributes"]
        for f in feats
        if f["attributes"]["max_flow"] >= f["attributes"]["high_water_threshold"]
    ]
    if not over:
        return []
    named = sorted({a["name"] for a in over if a["name"] != "Unnamed Stream"})[:4]
    big = max(over, key=lambda a: a["max_flow"])
    rec = {
        ">50": "less than a 2-year flow",
        "2": "about a 2-year flow",
        "5": "about a 5-year flow",
    }.get(str(big["recur_cat"]), f"recurrence {big['recur_cat']}")
    return [
        signal(
            "NWM high-flow magnitude (18 h)",
            "forecast",
            f"{len(over)} creek reaches forecast above their high-water threshold",
            detail=f"Largest: {big['name']} peak {round(big['max_flow'])} cfs vs high-water threshold {round(big['high_water_threshold'])} cfs ({rec}). Named: {', '.join(named) or 'unnamed streams'}.",
            value=len(over),
            units="reaches",
            severity="watch",
        )
    ]


@adapter("NWM 10-day rapid-onset flooding", ttl=3600)  # docs/07 #6 (medium range)
def nwm_rapid_onset_10d(ctx: Ctx) -> list[dict]:
    feats = [
        f
        for f in esri_query(f"{NWM}/mrf_gfs_10day_rapid_onset_flooding/MapServer/0/query", ctx)
        if in_ctx(ctx, f, 2000)
    ]
    if not feats:
        return []
    a = sorted((f["attributes"] for f in feats), key=lambda a: a.get("flood_start_hour", 0))
    return [
        signal(
            "NWM 10-day rapid-onset flooding",
            "forecast",
            f"{len(a)} creek reaches may flood fast in the next 10 days",
            detail=f"Earliest forecast start {local(str(a[0].get('flood_start_time', '')).replace(' ', 'T') + 'Z') or 'in the 10-day window'} (NWM medium range, GFS).",
            value=len(a),
            units="reaches",
            severity="watch",
        )
    ]


# ---------------------------------------------------------------- rain totals, guidance, rarity


@adapter("Flash Flood Guidance", ttl=3600)  # docs/07 #17
def ffg(ctx: Ctx) -> list[dict]:
    """How much rain in 1/3/6 h would cause flash flooding here. Grid values are mm (5 km FFG)."""
    r = http.get(
        "https://mapservices.weather.noaa.gov/raster/rest/services/precip/rfc_gridded_ffg/MapServer/identify",
        params={
            "geometry": f"{ctx.lon},{ctx.lat}",
            "geometryType": "esriGeometryPoint",
            "sr": 4326,
            "layers": "all:3,7,11",
            "tolerance": 1,
            "mapExtent": f"{ctx.lon - 0.5},{ctx.lat - 0.5},{ctx.lon + 0.5},{ctx.lat + 0.5}",
            "imageDisplay": "400,400,96",
            "returnGeometry": "false",
            "f": "json",
        },
    )
    r.raise_for_status()
    vals = {}
    for res in r.json().get("results", []):
        a = res.get("attributes", {})
        v = a.get("Service Pixel Value")
        m = re.search(r"ffg_(\d+)", a.get("name", ""))
        if m and v not in (None, "NoData"):
            vals[int(m.group(1))] = round(float(v) / MM_PER_IN, 2)
    if not vals:
        return []
    txt = ", ".join(f"{v} in in {h} h" for h, v in sorted(vals.items()))
    return [
        signal(
            "Flash Flood Guidance",
            "context",
            f"Flash flooding starts with about {vals.get(1, min(vals.values()))} in of rain in 1 hour here",
            detail=f"Rain needed to cause flash flooding: {txt} (NWS River Forecast Center guidance).",
            value=vals.get(1),
            units="in",
        )
    ]


@adapter("WPC rain forecast (days 1-3)", ttl=3600)  # docs/07 #16
def wpc_qpf(ctx: Ctx) -> list[dict]:
    base = "https://mapservices.weather.noaa.gov/vector/rest/services/precip/wpc_qpf/MapServer"
    vals = {}
    for layer, label in ((1, "day 1"), (2, "day 2"), (3, "day 3"), (9, "72 h")):
        feats = esri_query(
            f"{base}/{layer}/query", point=(ctx.lat, ctx.lon), fields="qpf,valid_time"
        )
        if feats:
            vals[label] = max(f["attributes"]["qpf"] for f in feats)
    if not vals:
        return []
    tot = vals.get("72 h", sum(v for k, v in vals.items() if k.startswith("day")))
    sev = "warning" if tot >= 3 else "watch" if tot >= 1.5 else "info"
    return [
        signal(
            "WPC rain forecast (days 1-3)",
            "forecast",
            f"{tot} in of rain forecast over 3 days",
            detail="; ".join(f"{k}: {v} in" for k, v in vals.items())
            + " (NOAA Weather Prediction Center).",
            value=tot,
            units="in",
            severity=sev,
        )
    ]


@adapter("Open-Meteo rain forecast", ttl=1800)  # docs/07 #20 (HRRR/GFS second opinion)
def open_meteo(ctx: Ctx) -> list[dict]:
    r = http.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": ctx.lat,
            "longitude": ctx.lon,
            "hourly": "precipitation",
            "forecast_days": 3,
            "timezone": "UTC",
        },
    )
    r.raise_for_status()
    h = r.json()["hourly"]
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:00")
    i0 = next((i for i, t in enumerate(h["time"]) if t >= now), 0)
    p = [x or 0 for x in h["precipitation"][i0:]]
    r24, r72 = round(sum(p[:24]) / MM_PER_IN, 2), round(sum(p[:72]) / MM_PER_IN, 2)
    peak = round(max(p[:24], default=0) / MM_PER_IN, 2)
    return [
        signal(
            "Open-Meteo rain forecast",
            "forecast",
            f"{r24} in of rain in the next 24 h (model blend)",
            detail=f"{r24} in next 24 h, {r72} in next 72 h; heaviest hour {peak} in.",
            value=r24,
            units="in",
        )
    ]


@adapter("NOAA Atlas 14 rainfall rarity", ttl=86400)  # docs/07 #18
def atlas14(ctx: Ctx) -> list[dict]:
    r = http.get(
        "https://hdsc.nws.noaa.gov/cgi-bin/new/fe_text_mean.csv",
        params={
            "lat": round(ctx.lat, 3),
            "lon": round(ctx.lon, 3),
            "data": "depth",
            "units": "english",
            "series": "pds",
        },
    )
    r.raise_for_status()
    rows = {}
    for line in r.text.splitlines():
        m = re.match(r"^(60-min|24-hr):,\s*(.*)$", line)
        if m:
            rows[m.group(1)] = [float(x) for x in m.group(2).split(",")[:3]]  # 1-, 2-, 5-year
    if not rows:
        return []
    h1, d1 = rows.get("60-min"), rows.get("24-hr")
    return [
        signal(
            "NOAA Atlas 14 rainfall rarity",
            "context",
            "How rare a given rainfall is here",
            detail=(
                f"1 hour: {h1[0]} in happens about once a year, {h1[2]} in about once in 5 years. "
                if h1
                else ""
            )
            + (f"24 hours: {d1[0]} in once a year, {d1[2]} in once in 5 years." if d1 else ""),
        )
    ]


@adapter("CoCoRaHS volunteer rain reports", ttl=3600)  # docs/07 #26
def cocorahs(ctx: Ctx) -> list[dict]:
    day = (datetime.now(UTC) - timedelta(hours=5)).strftime("%m/%d/%Y")
    r = http.get(
        "https://data.cocorahs.org/export/exportreports.aspx",
        params={
            "ReportType": "Daily",
            "Format": "CSV",
            "State": "GA",
            "ReportDateType": "reportdate",
            "StartDate": day,
            "EndDate": day,
        },
    )
    r.raise_for_status()
    near = []
    for row in csv.DictReader(io.StringIO(r.text)):
        try:
            lat, lon, amt = (
                float(row["Latitude"]),
                float(row[" Longitude"] if " Longitude" in row else row["Longitude"]),
                row.get("TotalPrecipAmt") or row.get(" TotalPrecipAmt"),
            )
            amt = float(str(amt).strip()) if str(amt).strip() not in ("T", "NA", "") else 0.0
        except (KeyError, ValueError):
            continue
        if ctx.contains(lat, lon, extra_m=10000):
            near.append((amt, row.get("StationName") or row.get(" StationName")))
    if not near:
        return []
    top = max(near)
    return [
        signal(
            "CoCoRaHS volunteer rain reports",
            "observation",
            f"Volunteer gauges: up to {top[0]} in in the latest 24 h report",
            detail=f"{len(near)} reports nearby; wettest {top[0]} in at {str(top[1]).strip()}.",
            value=top[0],
            units="in",
        )
    ]


# ---------------------------------------------------------------- infrastructure, history, people


@adapter("National Inventory of Dams", ttl=86400)  # docs/07 #57
def dams(ctx: Ctx) -> list[dict]:
    miles = (ctx.radius_km if ctx.kind == "area" else 3) / 1.609
    r = http.get(
        "https://nid.sec.usace.army.mil/api/query",
        params={"nr": f"{ctx.lon},{ctx.lat},{miles:.1f}"},
    )
    r.raise_for_status()
    ds = [
        d
        for d in r.json()
        if ctx.contains(float(d["latitude"]), float(d["longitude"]), extra_m=2000)
    ]
    if not ds:
        return []
    names = ", ".join(d["name"] for d in ds[:4])
    return [
        signal(
            "National Inventory of Dams",
            "context",
            f"{len(ds)} dams in or near the area",
            detail=f"Including {names}. Dams can raise or release water during heavy rain.",
            value=len(ds),
            units="dams",
        )
    ]


@adapter("FEMA flood insurance claims", ttl=86400)  # docs/07 #56
def nfip(ctx: Ctx) -> list[dict]:
    lat, lon = round(ctx.lat, 1), round(ctx.lon, 1)
    r = http.get(
        "https://www.fema.gov/api/open/v3/NfipClaims",
        params={
            "$filter": f"latitude eq {lat} and longitude eq {lon}",
            "$top": 1000,
            "$select": "dateOfLoss",
            "$orderby": "dateOfLoss desc",
            "$inlinecount": "allpages",
        },
        timeout=20,
    )
    r.raise_for_status()
    d = r.json()
    n = d.get("metadata", {}).get("count") or len(d.get("NfipClaims", []))
    if not n:
        return []
    years = pd.Series([c["dateOfLoss"][:4] for c in d.get("NfipClaims", [])]).value_counts().head(3)
    top = ", ".join(f"{y} ({c})" for y, c in years.items())
    return [
        signal(
            "FEMA flood insurance claims",
            "context",
            f"{n} flood insurance claims in this ~10 km grid cell since records began",
            detail=f"Busiest years: {top}. Shows the area has flooded homes before (FEMA NFIP).",
            value=n,
            units="claims",
            severity="watch" if n >= 100 else "info",
        )
    ]


@adapter("Critical facilities", ttl=86400)  # docs/07 #80
def facilities(ctx: Ctx) -> list[dict]:
    base = "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer"
    out = []
    for layer, what in ((14, "hospitals"), (16, "fire/EMS stations")):
        feats = [
            f for f in esri_query(f"{base}/{layer}/query", ctx, fields="NAME") if in_ctx(ctx, f)
        ]
        if feats:
            out.append(
                signal(
                    "Critical facilities",
                    "context",
                    f"{len(feats)} {what} in the area",
                    detail=", ".join(f["attributes"].get("NAME", "?").title() for f in feats[:4]),
                    value=len(feats),
                    units=what,
                )
            )
    return out


@adapter("Atlanta storm drains", ttl=86400)  # docs/07 #50
def storm_inlets(ctx: Ctx) -> list[dict]:
    x0, y0, x1, y1 = ctx.bbox
    if not (-84.56 <= ctx.lon <= -84.28 and 33.64 <= ctx.lat <= 33.89):  # City of Atlanta data only
        return []
    r = http.get(
        "https://egis.atlantaga.gov/arc/rest/services/MapWF/StormWater1/MapServer/3/query",
        params={
            "geometry": f"{x0},{y0},{x1},{y1}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "returnCountOnly": "true",
            "f": "json",
        },
    )
    r.raise_for_status()
    n = r.json().get("count", 0)
    return (
        [
            signal(
                "Atlanta storm drains",
                "context",
                f"{n} city storm inlets in the area",
                detail="Storm drains can back up in heavy rain and pond water on streets (City of Atlanta DWM).",
                value=n,
                units="inlets",
            )
        ]
        if n
        else []
    )


# ---------------------------------------------------------------- sewage overflows


@adapter("EPA combined sewer overflow facilities", ttl=86400)  # docs/07 #52
def cso(ctx: Ctx) -> list[dict]:
    q = http.get(
        "https://echodata.epa.gov/echo/cwa_rest_services.get_facilities",
        params={"output": "JSON", "p_st": "GA", "p_fn": "CSO"},
    ).json()
    r = http.get(
        "https://echodata.epa.gov/echo/cwa_rest_services.get_qid",
        params={"output": "JSON", "qid": q["Results"]["QueryID"], "qcolumns": "1,3,26,27,53"},
    )
    r.raise_for_status()
    near = []
    for f in r.json()["Results"].get("Facilities", []):
        try:
            lat, lon = float(f["FacLat"]), float(f["FacLong"])
        except (TypeError, ValueError, KeyError):
            continue
        if (
            f.get("CWPPermitStatusDesc") != "Terminated"
            and haversine_m(ctx.lat, ctx.lon, lat, lon) <= 15000
        ):
            near.append(f["CWPName"])
    if not near:
        return []
    return [
        signal(
            "EPA combined sewer overflow facilities",
            "context",
            f"{len(set(near))} combined-sewer overflow facilities within 15 km",
            detail=f"{', '.join(sorted(set(near))[:3])}. In heavy rain, combined sewers can overflow into nearby creeks (EPA ECHO). Avoid contact with floodwater.",
            value=len(set(near)),
            units="facilities",
            severity="watch",
        )
    ]


@adapter("Georgia EPD sewage spills (30 days)", ttl=21600)  # docs/07 #53
def ga_spills(ctx: Ctx) -> list[dict]:
    page = http.get(
        "https://epd.georgia.gov/watershed-protection-branch/wastewater/sewage-spills-report"
    )
    page.raise_for_status()
    m = re.search(r'href="([^"]*sewagespillsreport[^"]*/download)"', page.text)
    if not m:
        raise RuntimeError("spills report link not found")
    url = m.group(1) if m.group(1).startswith("http") else "https://epd.georgia.gov" + m.group(1)
    x = pd.read_excel(io.BytesIO(http.get(url).content), header=None)
    hdr = x.index[x.iloc[:, 0].astype(str).str.upper().eq("FACILITY_NAME")][0]
    df = x.iloc[hdr + 1 :].set_axis(x.iloc[hdr].tolist(), axis=1).dropna(subset=["FACILITY_NAME"])
    county = county_at(round(ctx.lat, 3), round(ctx.lon, 3))
    if not county:
        return []
    mine = df[df["COUNTY"].astype(str).str.strip().str.lower() == county.lower()]
    if mine.empty:
        return []
    gal = pd.to_numeric(mine["QUANTITY_GALLONS"], errors="coerce").sum()
    eg = "; ".join(
        f"{r.OVERFLOW_LOCATION} ({str(r.BEGIN_DATE)[:10]})" for r in mine.head(2).itertuples()
    )
    return [
        signal(
            "Georgia EPD sewage spills (30 days)",
            "report",
            f"{len(mine)} sewage spills reported in {county} County in the last 30 days",
            detail=f"{int(gal) if gal else 'unknown'} gallons reported in total. Recent: {eg}.",
            value=len(mine),
            units="spills",
            severity="watch" if len(mine) >= 3 else "info",
        )
    ]


# ---------------------------------------------------------------- potholes / road condition


@adapter("Road roughness (FHWA HPMS)", ttl=86400)  # docs/07 #41
def roughness(ctx: Ctx) -> list[dict]:
    feats = esri_query(
        "https://geo.dot.gov/server/rest/services/Hosted/Georgia_2018_PR/FeatureServer/0/query",
        ctx,
        fields="route_name,iri",
        count=500,
    )
    feats = [f for f in feats if f["attributes"].get("iri") and in_ctx(ctx, f)]
    poor = [
        f["attributes"] for f in feats if f["attributes"]["iri"] > 170
    ]  # FHWA: IRI > 170 in/mi = poor
    if not feats:
        return []
    names = sorted({str(a.get("route_name") or "").strip() for a in poor if a.get("route_name")})[
        :4
    ]
    return [
        signal(
            "Road roughness (FHWA HPMS)",
            "context",
            f"{len(poor)} of {len(feats)} measured road sections rated poor (pothole-prone)",
            detail=f"Rough sections (IRI over 170 in/mi, 2018 survey): {', '.join(names) or 'unnamed'}. Potholes fill with water and hide depth.",
            value=len(poor),
            units="sections",
            severity="info",
        )
    ]


# ---------------------------------------------------------------- news and social


def place_query(ctx: Ctx) -> str:
    c = county_at(round(ctx.lat, 3), round(ctx.lon, 3)) or "Georgia"
    return "Atlanta" if c in ("Fulton", "DeKalb") else f"{c} County Georgia"


@adapter("Local news", ttl=1800)  # docs/07 #33
def news(ctx: Ctx) -> list[dict]:
    q = f'{place_query(ctx)} (flood OR flooding OR "flash flood" OR "road closed") when:1d'
    r = http.get(
        "https://news.google.com/rss/search",
        params={"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"},
    )
    r.raise_for_status()
    items = ET.fromstring(r.text).findall(".//item")[:5]
    out = []
    for i in items[:3]:
        when = (
            parsedate_to_datetime(i.findtext("pubDate"))
            .astimezone(UTC)
            .strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        out.append(
            signal(
                "Local news",
                "report",
                i.findtext("title"),
                detail=f"Published {local(when)}.",
                url=i.findtext("link"),
            )
        )
    return out


@adapter("Bluesky posts", ttl=900)  # docs/07 #32
def bluesky(ctx: Ctx) -> list[dict]:
    r = http.get(
        "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts",
        params={
            "q": f"{place_query(ctx).split(' County')[0]} flooding",
            "limit": 10,
            "sort": "latest",
            "since": (datetime.now(UTC) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    r.raise_for_status()
    posts = r.json().get("posts", [])
    if not posts:
        return []
    eg = " | ".join(p["record"]["text"][:100].replace("\n", " ") for p in posts[:2])
    return [
        signal(
            "Bluesky posts",
            "report",
            f"{len(posts)} public posts about flooding nearby in the last 24 h",
            detail=f"Unverified public posts. Examples: {eg}",
            value=len(posts),
            units="posts",
        )
    ]
