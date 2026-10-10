"""Spec 006: Noah HTTP API (C9). Run: uv run uvicorn noah.api.app:app --port 8000

Also mounts spec 014's dispatch router (I3) and serves web/ from the same origin (I7).
"""

import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")  # keys before anything reads os.environ

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from noah import (
    config,
    engine,
)
from noah.api import agent, dispatch, past, routing

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
app.include_router(agent.router)  # spec 007 POST /chat (Margulan, J15)


def parse_latlon(s: str) -> tuple[float, float]:
    lat, lon = (float(x) for x in s.split(","))
    return lat, lon


def failed(what: str) -> dict:
    log.exception("%s failed", what)
    return {"state": "error", "message": ERROR_MESSAGE}


@app.get("/health")
def health() -> dict:
    try:
        return {"ok": True, "cycle": routing.current_cycle()}
    except Exception:  # noqa: BLE001 (spec 006: any failure -> conservative reply, never a crash)
        return {"ok": False, **failed("health")}


@app.get("/status")
def status(
    lat: float, lon: float, hours: int = config.MAX_LEAD_H, cycle: str | None = None
) -> dict:
    try:
        return routing.status(lat, lon, hours, cycle)
    except Exception:  # noqa: BLE001 (spec 006: any failure -> conservative reply, never a crash)
        return failed("status")


@app.get("/route")
def route(
    from_: str = Query(alias="from"), to: str = Query(), depart_h: int = 0, cycle: str | None = None
) -> dict:
    try:
        (a_lat, a_lon), (b_lat, b_lon) = parse_latlon(from_), parse_latlon(to)
        return routing.route(a_lat, a_lon, b_lat, b_lon, depart_h, cycle)
    except Exception:  # noqa: BLE001 (spec 006: any failure -> conservative reply, never a crash)
        return failed("route")


@app.get("/assess")
def assess_area(lat: float, lon: float, cycle: str | None = None) -> dict:
    """Spec 015: every source for the 5 km area + AI assessment (now / next 18 h / next days)."""
    try:
        return engine.area(lat, lon, cycle)
    except Exception:  # noqa: BLE001 (spec 006/015: any failure -> conservative reply, never a crash)
        return failed("assess")


@app.get("/assess/route")
def assess_route(
    from_: str = Query(alias="from"), to: str = Query(), depart_h: int = 0, cycle: str | None = None
) -> dict:
    """Spec 015: route around forecast flooding + every source along the 1 km corridor + AI assessment."""
    try:
        (a_lat, a_lon), (b_lat, b_lon) = parse_latlon(from_), parse_latlon(to)
        return engine.route(a_lat, a_lon, b_lat, b_lon, depart_h, cycle)
    except Exception:  # noqa: BLE001
        return failed("assess/route")


@app.get("/past")
def past_area(lat: float, lon: float, cycle: str | None = None) -> dict:
    """Past mode: hour-by-hour NOAA estimate for the last 18 h in the 5 km area + gauge readings + storm reports."""
    try:
        return past.area(lat, lon, cycle)
    except Exception:  # noqa: BLE001
        return failed("past")


@app.get("/past/route")
def past_route(
    from_: str = Query(alias="from"), to: str = Query(), cycle: str | None = None
) -> dict:
    """Past mode along a route's 1 km corridor."""
    try:
        (a_lat, a_lon), (b_lat, b_lon) = parse_latlon(from_), parse_latlon(to)
        return past.route(a_lat, a_lon, b_lat, b_lon, cycle)
    except Exception:  # noqa: BLE001
        return failed("past/route")


@app.on_event("startup")
def warm() -> None:
    """Load graph + active cycle once at startup so the first request is fast."""
    try:
        dispatch.graph_state()
        agent.warm()  # street index for the chat agent (007)
        routing.flood_index(routing.current_cycle())
        routing.coverage()
        # 21 years of Georgia flood reports is a large download: fetch it once in the background
        import threading

        from noah.sources.adapters import _ga_lsr_floods, now_utc

        threading.Thread(
            target=_ga_lsr_floods, args=(now_utc().strftime("%Y-%m-%d"),), daemon=True
        ).start()
    except Exception:
        log.exception("warm-up failed; endpoints will retry on first request")


app.mount("/", StaticFiles(directory=config.ROOT / "web", html=True), name="web")
