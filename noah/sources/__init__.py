"""Spec 015: source adapters. Each adapter turns one data source into standard signals for an
area (fixed radius around the user) or a route corridor. Adapters run in parallel with a time
budget; a slow or failing source is reported, never fatal.
"""

import itertools
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass, field

import httpx
from shapely.geometry import LineString, Point

from noah import config

log = logging.getLogger("sources")
UA = {"User-Agent": "noah-hacklanta/0.1 (Hacklanta 2026 flood-road app)"}
http = httpx.Client(timeout=8, headers=UA, follow_redirects=True)
ADAPTERS: list[tuple[str, int, object]] = []  # (name, ttl_s, fn)
_cache: dict = {}


@dataclass
class Ctx:
    """Where to look: an area (radius) or a route corridor (line + buffer)."""

    kind: str  # "area" | "route"
    lat: float  # area centre, or route midpoint
    lon: float
    radius_km: float = config.ALERT_RADIUS_KM
    line: LineString | None = None  # lon/lat
    buffer_m: float = config.CORRIDOR_BUFFER_M
    extra: dict = field(default_factory=dict)  # e.g. segments from 006 for reach lookups

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """(min_lon, min_lat, max_lon, max_lat) covering the area / corridor."""
        pad_km = self.radius_km if self.kind == "area" else self.buffer_m / 1000
        dlat = pad_km / 110.54
        dlon = pad_km / (111.32 * math.cos(math.radians(self.lat)))
        if self.line is not None:
            x0, y0, x1, y1 = self.line.bounds
        else:
            x0 = x1 = self.lon
            y0 = y1 = self.lat
        return (x0 - dlon, y0 - dlat, x1 + dlon, y1 + dlat)

    def points(self, step_km: float = 10) -> list[tuple[float, float]]:
        """(lat, lon) sample points: the centre for an area, start/every step_km/end for a route."""
        if self.line is None:
            return [(self.lat, self.lon)]
        n = max(2, int(route_km(self.line) / step_km) + 1)
        pts = [self.line.interpolate(i / (n - 1), normalized=True) for i in range(n)]
        return [(p.y, p.x) for p in pts]

    def distance_m(self, lat: float, lon: float) -> float:
        """Distance from the centre (area) or from the route line (route)."""
        if self.line is None:
            return haversine_m(self.lat, self.lon, lat, lon)
        k = 111320 * math.cos(math.radians(self.lat))
        line_m = LineString(
            [((x - self.lon) * k, (y - self.lat) * 110540) for x, y in self.line.coords]
        )
        return line_m.distance(Point((lon - self.lon) * k, (lat - self.lat) * 110540))

    def contains(self, lat: float, lon: float, extra_m: float = 0) -> bool:
        limit = (self.radius_km * 1000 if self.kind == "area" else self.buffer_m) + extra_m
        return self.distance_m(lat, lon) <= limit

    def key(self) -> tuple:
        if self.line is None:
            return ("area", round(self.lat, 3), round(self.lon, 3))
        return (
            "route",
            tuple(
                (round(x, 3), round(y, 3))
                for x, y in self.line.coords[:: max(1, len(self.line.coords) // 20)]
            ),
        )


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371000 * math.asin(math.sqrt(a))


def route_km(line: LineString) -> float:
    c = list(line.coords)
    return sum(haversine_m(a[1], a[0], b[1], b[0]) for a, b in itertools.pairwise(c)) / 1000


def signal(
    source: str,
    kind: str,
    title: str,
    *,
    detail: str = "",
    value=None,
    units=None,
    severity: str = "info",
    valid_from=None,
    valid_to=None,
    lat=None,
    lon=None,
    url=None,
) -> dict:
    """One standard signal. kind: forecast | observation | report | context."""
    return {
        k: v
        for k, v in {
            "source": source,
            "kind": kind,
            "title": title,
            "detail": detail,
            "value": value,
            "units": units,
            "severity": severity,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "lat": lat,
            "lon": lon,
            "url": url,
        }.items()
        if v not in (None, "")
    }


def adapter(name: str, ttl: int = 600):
    """Register fn(ctx) -> list[signal] under a docs/07 source name, cached for ttl seconds."""

    def wrap(fn):
        ADAPTERS.append((name, ttl, fn))
        return fn

    return wrap


def _call(name: str, ttl: int, fn, ctx: Ctx):
    k = (name, ctx.key())
    hit = _cache.get(k)
    if hit and hit[0] > time.time():
        return hit[1], True
    out = fn(ctx)
    _cache[k] = (time.time() + ttl, out)
    return out, False


def run(ctx: Ctx, budget_s: float = 12, only: set[str] | None = None) -> dict:
    """Run every adapter in parallel. Returns signals plus which sources answered or failed."""
    from noah.sources import adapters  # noqa: F401  (registers adapters)

    todo = [a for a in ADAPTERS if only is None or a[0] in only]
    ok, failed, signals = [], [], []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=min(16, len(todo) or 1)) as pool:
        futs = {pool.submit(_call, n, ttl, fn, ctx): n for n, ttl, fn in todo}
        done, pending = wait(futs, timeout=budget_s)
        for f in done:
            name = futs[f]
            try:
                out, cached = f.result()
                signals.extend(out)
                ok.append({"source": name, "signals": len(out), "cached": cached})
            except Exception as e:  # noqa: BLE001 (one source failing must not sink the answer)
                log.warning("source %s failed: %s", name, e)
                failed.append({"source": name, "error": f"{type(e).__name__}: {str(e)[:120]}"})
        for f in pending:
            failed.append({"source": futs[f], "error": f"timeout after {budget_s:.0f} s"})
    order = {"danger": 0, "warning": 1, "watch": 2, "info": 3}
    signals.sort(key=lambda s: order.get(s.get("severity"), 4))
    return {
        "signals": signals,
        "sources_ok": sorted(ok, key=lambda x: x["source"]),
        "sources_failed": failed,
        "took_s": round(time.time() - t0, 2),
    }
