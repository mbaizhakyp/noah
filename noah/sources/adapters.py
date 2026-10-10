"""Spec 015 adapters. One function per verified source in docs/07 (numbers in comments).

Every adapter: fetch(ctx) -> list[signal]. Times in `detail` are written in America/New_York so
the AI engine can quote them without converting.
"""

import csv
import io
import os
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

from noah.sources import Ctx, adapter, haversine_m, http, signal

ET = ZoneInfo("America/New_York")
KM_PER_MI = 1.609344


def local(iso: str | None) -> str:
    """ISO time -> 'Sat 9:00 PM' in Atlanta time ('' for missing or NOAA's 0001-01-01 placeholder)."""
    if not iso or iso.startswith("0001"):
        return ""
    t = datetime.fromisoformat(iso)
    return t.astimezone(ET).strftime("%a %-I:%M %p")


def now_utc() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------- warnings & reports (NWS)

FLOOD_DANGER = {
    "Flash Flood Warning",
    "Flood Warning",
    "Flash Flood Emergency",
    "Flash Flood Statement",
}
FLOOD_WATCH = {"Flood Watch", "Flash Flood Watch", "Flood Advisory", "Hydrologic Outlook"}


@adapter("NWS alerts", ttl=120)  # docs/07 #21
def nws_alerts(ctx: Ctx) -> list[dict]:
    seen, out = set(), []
    for lat, lon in ctx.points():
        r = http.get(
            "https://api.weather.gov/alerts/active",
            params={"point": f"{lat:.4f},{lon:.4f}"},
            headers={"Accept": "application/geo+json"},
        )
        r.raise_for_status()
        for f in r.json()["features"]:
            p = f["properties"]
            if p["id"] in seen:
                continue
            seen.add(p["id"])
            ev = p["event"]
            sev = (
                "danger"
                if ev in FLOOD_DANGER
                else "watch"
                if ev in FLOOD_WATCH
                else "warning"
                if "Warning" in ev
                else "info"
            )
            out.append(
                signal(
                    "NWS alerts",
                    "forecast",
                    ev,
                    severity=sev,
                    detail=f"{p.get('headline') or ev}. In effect {local(p.get('onset') or p.get('effective'))} to {local(p.get('ends') or p.get('expires'))}.",
                    valid_from=p.get("onset") or p.get("effective"),
                    valid_to=p.get("ends") or p.get("expires"),
                    url=p["id"],
                )
            )
    return out


@adapter("NWS Local Storm Reports (last 24 h)", ttl=300)  # docs/07 #27
def lsr_recent(ctx: Ctx) -> list[dict]:
    r = http.get(
        "https://mesonet.agron.iastate.edu/geojson/lsr.geojson",
        params={"states": "GA", "hours": 24},
    )
    r.raise_for_status()
    out = []
    for f in r.json()["features"]:
        p = f["properties"]
        if not ctx.contains(p["lat"], p["lon"], extra_m=5000):
            continue
        kind = p.get("typetext") or p.get("type") or "report"
        flood = "FLOOD" in str(kind).upper()
        out.append(
            signal(
                "NWS Local Storm Reports",
                "report",
                f"{kind} reported near {p.get('city')}",
                detail=f"{p.get('remark') or ''} ({p.get('source')}, {local(p.get('valid') or '')})".strip(),
                severity="warning" if flood else "info",
                lat=p["lat"],
                lon=p["lon"],
                valid_from=p.get("valid"),
            )
        )
    return out


@adapter("NWS gridpoint rain forecast", ttl=1800)  # docs/07 #13
def nws_qpf(ctx: Ctx) -> list[dict]:
    pts = http.get(f"https://api.weather.gov/points/{ctx.lat:.4f},{ctx.lon:.4f}")
    pts.raise_for_status()
    grid = http.get(pts.json()["properties"]["forecastGridData"])
    grid.raise_for_status()
    g = grid.json()["properties"]
    now = now_utc()

    def total(hours: int) -> float:
        mm = 0.0
        for v in g["quantitativePrecipitation"]["values"]:
            start = datetime.fromisoformat(v["validTime"].split("/")[0])
            if now - timedelta(hours=1) <= start < now + timedelta(hours=hours):
                mm += v["value"] or 0
        return mm / 25.4

    pops = [
        v["value"] or 0
        for v in g["probabilityOfPrecipitation"]["values"]
        if now <= datetime.fromisoformat(v["validTime"].split("/")[0]) < now + timedelta(hours=24)
    ]
    r24, r48 = round(total(24), 2), round(total(48), 2)
    sev = "warning" if r24 >= 2 else "watch" if r24 >= 1 else "info"
    return [
        signal(
            "NWS gridpoint rain forecast",
            "forecast",
            f"{r24} in of rain forecast in the next 24 h",
            detail=f"{r24} in in the next 24 h, {r48} in in the next 48 h; highest chance of rain {max(pops, default=0)}%.",
            value=r24,
            units="in",
            severity=sev,
        )
    ]


# ---------------------------------------------------------------- rivers & creeks


@adapter("NWPS river gauges", ttl=600)  # docs/07 #2
def nwps_gauges(ctx: Ctx) -> list[dict]:
    x0, y0, x1, y1 = ctx.bbox
    pad = 0.05  # gauges just outside the corridor still describe the same creeks
    r = http.get(
        "https://api.water.noaa.gov/nwps/v1/gauges",
        params={
            "bbox.xmin": x0 - pad,
            "bbox.ymin": y0 - pad,
            "bbox.xmax": x1 + pad,
            "bbox.ymax": y1 + pad,
            "srid": "EPSG_4326",
        },
    )
    r.raise_for_status()
    out = []
    for g in r.json()["gauges"]:
        st = g.get("status") or {}
        obs, fc = st.get("observed") or {}, st.get("forecast") or {}
        cat = obs.get("floodCategory") or "unknown"
        fcat = fc.get("floodCategory") or ""
        flooding = cat not in ("no_flooding", "not_defined", "obs_not_current", "unknown")
        fc_flood = fcat not in ("", "no_flooding", "not_defined", "fcst_not_current")
        sev = (
            "danger"
            if cat in ("moderate", "major")
            else "warning"
            if flooding or fc_flood
            else "info"
        )
        detail = f"Now {obs.get('primary')} {obs.get('primaryUnit')} ({cat.replace('_', ' ')}) at {local(obs.get('validTime'))}."
        if fc.get("primary", -999) != -999:
            detail += f" Official forecast {fc.get('primary')} {fc.get('primaryUnit')} ({fcat.replace('_', ' ')}) by {local(fc.get('validTime'))}."
        out.append(
            signal(
                "NWPS river gauges",
                "observation",
                f"{g['name']} ({g['lid']})",
                detail=detail,
                value=obs.get("primary"),
                units=obs.get("primaryUnit"),
                severity=sev,
                lat=g["latitude"],
                lon=g["longitude"],
                url=f"https://water.noaa.gov/gauges/{g['lid'].lower()}",
            )
        )
    return out


@adapter("NWPS reach flow forecast (NWM)", ttl=1800)  # docs/07 #1
def nwps_reaches(ctx: Ctx) -> list[dict]:
    """Short-range (18 h) + medium-range blend (10 days) for the creeks under the flagged roads."""
    fids = [f for f in ctx.extra.get("feature_ids", []) if f][:4]
    out = []
    for fid in fids:
        r = http.get(
            f"https://api.water.noaa.gov/nwps/v1/reaches/{fid}/streamflow",
            params={"series": "medium_range_blend"},
        )
        r.raise_for_status()
        d = r.json()
        name = (d.get("reach") or {}).get("name") or f"reach {fid}"
        series = ((d.get("mediumRangeBlend") or {}).get("series") or {}).get("data") or []
        if not series:
            continue
        now_q = series[0]["flow"]
        peak = max(series, key=lambda x: x["flow"])
        ratio = peak["flow"] / now_q if now_q else None
        sev = "warning" if ratio and ratio >= 10 else "watch" if ratio and ratio >= 3 else "info"
        out.append(
            signal(
                "NWPS reach flow forecast (NWM)",
                "forecast",
                f"{name}: flow forecast to peak {local(peak['validTime'])}",
                detail=f"10-day NWM blend: {round(now_q)} cfs now, peak {round(peak['flow'])} cfs around {local(peak['validTime'])}.",
                value=round(peak["flow"]),
                units="cfs",
                severity=sev,
                valid_from=peak["validTime"],
            )
        )
    return out


@adapter("USGS water data", ttl=600)  # docs/07 #22
def usgs_latest(ctx: Ctx) -> list[dict]:
    x0, y0, x1, y1 = ctx.bbox
    r = http.get(
        "https://api.waterdata.usgs.gov/ogcapi/v0/collections/latest-continuous/items",
        params={"bbox": f"{x0},{y0},{x1},{y1}", "f": "json", "limit": 200},
    )
    r.raise_for_status()
    names = {"00065": ("stage", "ft"), "00060": ("flow", "cfs"), "00045": ("rain (15 min)", "in")}
    out = []
    for f in r.json().get("features", []):
        p = f["properties"]
        if p["parameter_code"] not in names:
            continue
        what, unit = names[p["parameter_code"]]
        lon, lat = (f.get("geometry") or {}).get("coordinates", [None, None])[:2]
        out.append(
            signal(
                "USGS water data",
                "observation",
                f"{p['monitoring_location_id']} {what}",
                detail=f"{what} {p['value']} {unit} at {local(p['time'])}.",
                value=float(p["value"]) if p["value"] not in (None, "") else None,
                units=unit,
                lat=lat,
                lon=lon,
                url=f"https://waterdata.usgs.gov/monitoring-location/{p['monitoring_location_id'].split('-')[-1]}/",
            )
        )
    return out


# ---------------------------------------------------------------- rain now & rain risk


@adapter("Synoptic rain gauges", ttl=600)  # docs/07 #24
def synoptic_rain(ctx: Ctx) -> list[dict]:
    tok = os.environ.get("SYNOPTIC_TOKEN")
    if not tok:
        raise RuntimeError("SYNOPTIC_TOKEN missing")
    params = {
        "token": tok,
        "vars": "precip_accum_one_hour,precip_accum_24_hour,precip_accum_since_local_midnight",
        "within": 120,
        "units": "english",
        "status": "active",
    }
    if ctx.kind == "area":
        params["radius"] = f"{ctx.lat},{ctx.lon},{ctx.radius_km / KM_PER_MI:.1f}"
    else:
        x0, y0, x1, y1 = ctx.bbox
        params["bbox"] = f"{x0},{y0},{x1},{y1}"
    r = http.get("https://api.synopticdata.com/v2/stations/latest", params=params)
    r.raise_for_status()
    st = r.json().get("STATION", [])
    one, day = [], []
    for s in st:
        for k, v in s.get("OBSERVATIONS", {}).items():
            if v.get("value") is None:
                continue
            (one if "one_hour" in k else day).append((v["value"], s["NAME"].strip()))
    if not st:
        return []
    m1 = max(one, default=(0, ""))
    m24 = max(day, default=(0, ""))
    sev = (
        "warning"
        if m1[0] >= 1 or m24[0] >= 3
        else "watch"
        if m1[0] >= 0.5 or m24[0] >= 1.5
        else "info"
    )
    return [
        signal(
            "Synoptic rain gauges",
            "observation",
            f"Rain measured by {len(st)} nearby gauges",
            detail=f"Wettest last hour: {m1[0]} in ({m1[1]}). Wettest last 24 h / since midnight: {m24[0]} in ({m24[1]}).",
            value=m1[0],
            units="in/h",
            severity=sev,
        )
    ]


@adapter("WPC Excessive Rainfall Outlook", ttl=1800)  # docs/07 #15
def wpc_ero(ctx: Ctx) -> list[dict]:
    out = []
    for layer, day in ((0, "Day 1"), (1, "Day 2"), (2, "Day 3")):
        best = None
        for lat, lon in ctx.points(step_km=25):
            r = http.get(
                f"https://mapservices.weather.noaa.gov/vector/rest/services/hazards/wpc_precip_hazards/MapServer/{layer}/query",
                params={
                    "geometry": f"{lon},{lat}",
                    "geometryType": "esriGeometryPoint",
                    "inSR": 4326,
                    "spatialRel": "esriSpatialRelIntersects",
                    "outFields": "outlook,valid_time,issue_time",
                    "returnGeometry": "false",
                    "f": "json",
                },
            )
            r.raise_for_status()
            for f in r.json().get("features", []):
                a = f["attributes"]
                rank = ["Marginal", "Slight", "Moderate", "High"]
                lvl = next((i for i, w in enumerate(rank) if a["outlook"].startswith(w)), -1)
                if best is None or lvl > best[0]:
                    best = (lvl, a)
        if best:
            lvl, a = best
            sev = ["info", "watch", "warning", "danger"][max(lvl, 0)]
            out.append(
                signal(
                    "WPC Excessive Rainfall Outlook",
                    "forecast",
                    f"{day}: {a['outlook']} risk of flash flooding",
                    detail=f"{day} ({a['valid_time']} UTC): {a['outlook']} chance that rain exceeds flash-flood guidance nearby.",
                    severity=sev,
                    url="https://www.wpc.ncep.noaa.gov/qpf/excessive_rainfall_outlook_ero.php",
                )
            )
    return out


# ---------------------------------------------------------------- roads

TOMTOM_CAT = {
    11: ("Flooding", "danger"),
    8: ("Road closed", "warning"),
    4: ("Rain", "watch"),
    3: ("Dangerous conditions", "watch"),
    7: ("Lane closed", "info"),
    1: ("Accident", "info"),
}


@adapter("TomTom traffic incidents", ttl=300)  # docs/07 #30
def tomtom(ctx: Ctx) -> list[dict]:
    key = os.environ.get("TOMTOM_API_KEY")
    if not key:
        raise RuntimeError("TOMTOM_API_KEY missing")
    x0, y0, x1, y1 = ctx.bbox
    r = http.get(
        "https://api.tomtom.com/traffic/services/5/incidentDetails",
        params={
            "key": key,
            "bbox": f"{x0},{y0},{x1},{y1}",
            "language": "en-US",
            "fields": "{incidents{type,geometry{type,coordinates},properties{iconCategory,events{description},from,to,roadNumbers,startTime}}}",
        },
    )
    r.raise_for_status()
    out = []
    for inc in r.json().get("incidents", []):
        p = inc["properties"]
        cat = p.get("iconCategory")
        if cat not in TOMTOM_CAT:
            continue
        coords = inc["geometry"]["coordinates"]
        lon, lat = (coords[0] if isinstance(coords[0], list) else coords)[:2]
        if not ctx.contains(lat, lon, extra_m=200):
            continue
        label, sev = TOMTOM_CAT[cat]
        desc = ", ".join(e["description"] for e in p.get("events") or [])
        out.append(
            signal(
                "TomTom traffic incidents",
                "observation",
                f"{label}: {p.get('from') or ''} → {p.get('to') or ''}".strip(),
                detail=f"{desc} (since {local(p.get('startTime'))}).",
                severity=sev,
                lat=lat,
                lon=lon,
                value=cat,
                units="tomtom_category",
            )
        )
    return out


# ---------------------------------------------------------------- context: past floods, flood zones, people


@adapter("FEMA flood zones", ttl=86400)  # docs/07 #55
def fema_zone(ctx: Ctx) -> list[dict]:
    out = []
    for lat, lon in ctx.points(step_km=3)[:8]:
        r = http.get(
            "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query",
            params={
                "geometry": f"{lon},{lat}",
                "geometryType": "esriGeometryPoint",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "FLD_ZONE,ZONE_SUBTY",
                "returnGeometry": "false",
                "f": "json",
            },
        )
        r.raise_for_status()
        for f in r.json().get("features", [])[:1]:
            z = f["attributes"]["FLD_ZONE"]
            if z in ("A", "AE", "AH", "AO", "VE") or "FLOODWAY" in str(
                f["attributes"].get("ZONE_SUBTY") or ""
            ):
                out.append(
                    signal(
                        "FEMA flood zones",
                        "context",
                        f"In FEMA flood zone {z}",
                        detail=f"FEMA zone {z} ({f['attributes'].get('ZONE_SUBTY') or '1% annual chance floodplain'}) at {lat:.4f}, {lon:.4f}.",
                        severity="watch",
                        lat=lat,
                        lon=lon,
                    )
                )
    return out


@lru_cache(maxsize=1)
def _ga_lsr_floods(day: str) -> list[dict]:
    """All Georgia flood-related Local Storm Reports since 2005 (CSV, so nothing is truncated). One fetch per day."""
    r = http.get(
        "https://mesonet.agron.iastate.edu/cgi-bin/request/gis/lsr.py",
        timeout=60,
        params={"state": "GA", "sts": "2005-01-01T00:00Z", "ets": f"{day}T00:00Z", "fmt": "csv"},
    )
    r.raise_for_status()
    rows = []
    for row in csv.DictReader(io.StringIO(r.text)):
        kind, remark = row.get("TYPETEXT", ""), row.get("REMARK", "")
        if "FLOOD" in kind.upper() or "flood" in remark.lower():
            try:
                rows.append(
                    {
                        "lat": float(row["LAT"]),
                        "lon": float(row["LON"]),
                        "valid": row.get("VALID", ""),
                        "type": kind,
                        "remark": remark,
                        "city": row.get("CITY", ""),
                    }
                )
            except (KeyError, ValueError):
                continue
    return rows


@adapter("NWS flood reports here before (2005-2026)", ttl=86400)  # docs/07 #27 archive
def lsr_history(ctx: Ctx) -> list[dict]:
    hits = [
        p
        for p in _ga_lsr_floods(now_utc().strftime("%Y-%m-%d"))
        if ctx.contains(p["lat"], p["lon"])
    ]
    if not hits:
        return []
    hits.sort(key=lambda p: p["valid"], reverse=True)
    eg = "; ".join(
        f"{(p['remark'] or p['type'])[:90]} ({p['valid'][:4]}-{p['valid'][4:6]}-{p['valid'][6:8]})"
        for p in hits[:3]
    )
    return [
        signal(
            "NWS flood reports here before",
            "context",
            f"{len(hits)} past flood reports in this area since 2005",
            detail=f"Most recent: {eg}.",
            value=len(hits),
            units="reports",
            severity="watch" if len(hits) >= 3 else "info",
        )
    ]


@adapter("CDC Social Vulnerability Index", ttl=86400)  # docs/07 #78
def svi(ctx: Ctx) -> list[dict]:
    r = http.get(
        "https://onemap.cdc.gov/onemapservices/rest/services/SVI/CDC_ATSDR_Social_Vulnerability_Index_2022_USA/FeatureServer/2/query",
        params={
            "geometry": f"{ctx.lon},{ctx.lat}",
            "geometryType": "esriGeometryPoint",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "LOCATION,RPL_THEMES,E_NOVEH,E_HH",
            "returnGeometry": "false",
            "f": "json",
        },
    )
    r.raise_for_status()
    f = (r.json().get("features") or [None])[0]
    if not f:
        return []
    a = f["attributes"]
    pct = round(a["RPL_THEMES"] * 100) if a.get("RPL_THEMES") not in (None, -999) else None
    return [
        signal(
            "CDC Social Vulnerability Index",
            "context",
            "Social vulnerability: "
            + (
                "lower than 99% of US census tracts"
                if pct == 0
                else f"higher than {pct}% of US census tracts"
                if pct is not None
                else "unknown"
            ),
            detail=f"{a.get('LOCATION')}: {a.get('E_NOVEH')} of {a.get('E_HH')} households have no vehicle.",
            value=pct,
            units="percentile",
        )
    ]


@adapter("SeeClickFix reports", ttl=1800)  # docs/07 #54
def seeclickfix(ctx: Ctx) -> list[dict]:
    x0, y0, x1, y1 = ctx.bbox
    out = []
    for q in ("flood", "pothole"):
        r = http.get(
            "https://seeclickfix.com/api/v2/issues",
            params={
                "min_lat": y0,
                "min_lng": x0,
                "max_lat": y1,
                "max_lng": x1,
                "search": q,
                "per_page": 50,
                "sort": "updated_at",
            },
        )
        r.raise_for_status()
        issues = [i for i in r.json().get("issues", []) if ctx.contains(i["lat"], i["lng"])]
        open_ = [i for i in issues if i.get("status") in ("Open", "Acknowledged")]
        if issues:
            out.append(
                signal(
                    "SeeClickFix reports",
                    "report",
                    f"{len(open_)} open {q} reports nearby ({len(issues)} total)",
                    detail="; ".join(
                        f"{i['summary']} ({i['created_at'][:10]}, {i['status']})"
                        for i in issues[:3]
                    ),
                    value=len(open_),
                    units="open reports",
                    severity="info",
                )
            )
    return out


@adapter("NHC tropical storms", ttl=900)  # docs/07 #19
def nhc(ctx: Ctx) -> list[dict]:
    r = http.get("https://www.nhc.noaa.gov/CurrentStorms.json")
    r.raise_for_status()
    out = []
    for s in r.json().get("activeStorms", []):
        lat, lon = float(s["latitudeNumeric"]), float(s["longitudeNumeric"])
        km = haversine_m(ctx.lat, ctx.lon, lat, lon) / 1000
        if km > 800:
            continue
        out.append(
            signal(
                "NHC tropical storms",
                "forecast",
                f"{s['classification']} {s['name']} is {round(km)} km away",
                detail=f"{s['name']}: {s.get('intensity')} kt winds, {s.get('pressure')} mb, moving {s.get('movementDir')}° at {s.get('movementSpeed')} mph (NHC, {local(s.get('lastUpdate'))}).",
                value=round(km),
                units="km",
                severity="warning" if km < 300 else "watch",
                lat=lat,
                lon=lon,
                url=s.get("publicAdvisory", {}).get("url"),
            )
        )
    return out
