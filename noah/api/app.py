"""Spec 006: Noah HTTP API (C9). Run: uv run uvicorn noah.api.app:app --port 8000

Also mounts spec 014's dispatch router (I3) and serves web/ from the same origin (I7).
"""

import logging

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from noah import config
from noah.api import dispatch, routing

log = logging.getLogger("api")
ERROR_MESSAGE = (
    "I can't confirm conditions right now, so treat low roads near creeks as impassable. "
    "In an emergency call 911."
)  # 02-ARCHITECTURE §5

app = FastAPI(title="Noah API")
if config.WEB_BASE:
    app.add_middleware(
        CORSMiddleware, allow_origins=[config.WEB_BASE.rstrip("/")], allow_methods=["GET", "POST"]
    )
app.include_router(dispatch.router)


def parse_latlon(s: str) -> tuple[float, float]:
    lat, lon = (float(x) for x in s.split(","))
    return lat, lon


def failed(what: str) -> dict:
    log.exception("%s failed", what)
    return {"state": "error", "message": ERROR_MESSAGE}


@app.get("/health")
def health() -> dict:
    try:
        return {"ok": True, "cycle": dispatch.active_cycle()}
    except Exception:  # noqa: BLE001 (spec 006: any failure -> conservative reply, never a crash)
        return {"ok": False, **failed("health")}


@app.get("/status")
def status(lat: float, lon: float, hours: int = config.MAX_LEAD_H) -> dict:
    try:
        return routing.status(lat, lon, hours)
    except Exception:  # noqa: BLE001 (spec 006: any failure -> conservative reply, never a crash)
        return failed("status")


@app.get("/route")
def route(from_: str = Query(alias="from"), to: str = Query(), depart_h: int = 0) -> dict:
    try:
        (a_lat, a_lon), (b_lat, b_lon) = parse_latlon(from_), parse_latlon(to)
        return routing.route(a_lat, a_lon, b_lat, b_lon, depart_h)
    except Exception:  # noqa: BLE001 (spec 006: any failure -> conservative reply, never a crash)
        return failed("route")


@app.on_event("startup")
def warm() -> None:
    """Load graph + active cycle once at startup so the first request is fast."""
    try:
        dispatch.graph_state()
        routing.flood_index(dispatch.active_cycle())
        routing.coverage()
    except Exception:
        log.exception("warm-up failed; endpoints will retry on first request")


app.mount("/", StaticFiles(directory=config.ROOT / "web", html=True), name="web")
