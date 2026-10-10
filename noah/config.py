"""All Noah constants and paths. Single source of truth (docs/02-ARCHITECTURE.md §7).

Shared file: tell the other person before pushing a change.
"""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_INTERIM = ROOT / "data" / "interim"
WEB_DATA = ROOT / "web" / "data"

# Coverage
AOI_HUC10 = "0313000112"  # Peachtree Creek = Helene validation site (spec 005)
VALIDATION_HUC10 = AOI_HUC10
# Road-level coverage (CC6, decided Fri 23:25): the metro-Atlanta HUC10s of HUC8 03130001.
# The other 8 HUC10s (Lake Lanier, north Georgia mountains) are rural; roadmap.
AOI_HUC10S = [
    "0313000112",  # Peachtree Creek
    "0313000111",  # Sope Creek-Chattahoochee River (Sandy Springs, Marietta, Roswell)
    "0313000110",  # Big Creek (Alpharetta, Roswell): Isaias live story
    "0313000109",  # Suwanee Creek-Chattahoochee River (Johns Creek, Duluth)
]
HUC8 = "03130001"  # Upper Chattahoochee


def wbd_huc10_url(huc10s: list[str]) -> str:
    return (
        "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/5/query"
        "?where=huc10%20IN%20(" + "%2C".join(f"%27{h}%27" for h in huc10s) + ")"
        "&outFields=huc10,name,areasqkm&returnGeometry=true&outSR=4326&f=geojson"
    )


WBD_HUC10_URL = wbd_huc10_url(AOI_HUC10S)

# Spec 016 (approved Sat Oct 10): the first ring of sub-basins around metro on every side.
# Each basin is built on its own (HAND of its HUC8, its own graph + thresholds in data/interim/basins/<name>/)
# so metro's files and numbers stay untouched; the live loop merges every basin into one C5 per cycle.
# HUC8/HUC10 codes verified against the USGS WBD service, Sat 02:40.
BASINS = {
    "north": {"huc8": "03130001", "huc10s": ["0313000108"], "label": "Lake Lanier, Hall, Forsyth"},
    "etowah": {
        "huc8": "03150104",
        "huc10s": ["0315010408", "0315010403", "0315010406"],
        "label": "Cherokee, north Cobb (Etowah, Little River)",
    },
    "west": {
        "huc8": "03130002",
        "huc10s": ["0313000201", "0313000202"],
        "label": "Douglas, Paulding, southwest Atlanta (Sweetwater, Utoy)",
    },
    "flint": {
        "huc8": "03130005",
        "huc10s": ["0313000501", "0313000502"],
        "label": "Clayton, Fayette, south Fulton (Upper Flint, Line Creek)",
    },
    "ocmulgee": {
        "huc8": "03070103",
        "huc10s": ["0307010301", "0307010303", "0307010304", "0307010302", "0307010306"],
        "label": "East DeKalb, Gwinnett, Rockdale, Henry (Yellow and South rivers)",
    },
    "oconee": {
        "huc8": "03070101",
        "huc10s": ["0307010102"],
        "label": "Northeast Gwinnett, Barrow (Mulberry River)",
    },
}
BASINS_DIR = DATA_INTERIM / "basins"
BASINS_GEOJSON = (
    WEB_DATA / "basins.geojson"
)  # C7-shaped, one feature per basin HUC10 (+ basin, huc8)


def basin_dir(name: str) -> Path:
    return BASINS_DIR / name


def fim_base(huc8: str) -> str:
    return f"https://ciroh-owp-hand-fim.s3.amazonaws.com/hand_fim_4_9_9_0/{huc8}"


# Gauge: Peachtree Creek at Atlanta
GAUGE_USGS = "02336300"
GAUGE_NWS_LID = "AANG1"
GAUGE_FEATURE_ID = 2047989  # NWM reach = NHDPlusV2 COMID (NLDI)
THRESHOLDS_FT = {"action": 13, "minor": 17, "moderate": 18, "major": 20}  # NWPS AANG1
THRESHOLDS_CFS = {"action": 3630, "minor": 5700, "moderate": 7000, "major": 7800}  # NWPS AANG1

FT_TO_M = 0.3048
CFS_TO_CMS = 0.0283168
MINOR_FLOOD_CMS = THRESHOLDS_CFS["minor"] * CFS_TO_CMS  # 161.4
ACTION_FLOW_CMS = THRESHOLDS_CFS["action"] * CFS_TO_CMS  # 102.8

USGS_IV_URL = (
    "https://nwis.waterservices.usgs.gov/nwis/iv/?sites={site}&parameterCd=00065,00060"
    "&startDT={start}&endDT={end}&format=json"
)

# NWM (verified Oct 9, 2026)
NWM_BASE = "https://storage.googleapis.com/national-water-model"
NWM_SHORT_RANGE = (
    NWM_BASE + "/nwm.{ymd}/short_range/nwm.t{hh}z.short_range.channel_rt.f{fff}.conus.nc"
)
NWM_ANALYSIS = (
    NWM_BASE + "/nwm.{ymd}/analysis_assim/nwm.t{hh}z.analysis_assim.channel_rt.tm00.conus.nc"
)
MAX_LEAD_H = 18


def cycle_id(t: datetime) -> str:
    """datetime (UTC) -> '20240926T18Z'."""
    return t.strftime("%Y%m%dT%HZ")


def parse_cycle(c: str) -> datetime:
    """'20240926T18Z' -> datetime (UTC)."""
    return datetime.strptime(c, "%Y%m%dT%HZ").replace(tzinfo=UTC)


def cycle_range(first: str, last: str) -> list[str]:
    """Hourly cycle IDs from first to last, inclusive."""
    t, end = parse_cycle(first), parse_cycle(last)
    out = []
    while t <= end:
        out.append(cycle_id(t))
        t += timedelta(hours=1)
    return out


EVENTS = {
    "helene": {
        "label": "Hurricane Helene, Sep 26–27, 2024",
        "cycles": cycle_range("20240926T12Z", "20240927T12Z"),
        "baseline": "20240926T16Z",  # gauge at low flow (4.4 ft)
        "demo": "20240926T12Z",  # D5 final (Margulan, Oct 9): earliest + most skillful run, 13.2 h lead
        "usgs_window": ("2024-09-26T00:00-04:00", "2024-09-28T00:00-04:00"),
    },
    "isaias": {
        "label": "Hurricane Isaias, Oct 10, 2026",
        "cycles": cycle_range("20261010T00Z", "20261011T06Z"),  # trimmed to what exists at run time
        "baseline": "20261009T22Z",
        "demo": None,  # set by spec 011
        "usgs_window": ("2026-10-09T20:00-04:00", "2026-10-11T12:00-04:00"),
    },
}
HELENE_CYCLES = EVENTS["helene"]["cycles"]
BASELINE_CYCLE = EVENTS["helene"]["baseline"]
DEMO_CYCLE = EVENTS["helene"]["demo"]

# HAND / FIM (public CIROH bucket, OWP HAND-FIM v4.9.9.0; verified Oct 9, 2026)
FIM_BASE = f"https://ciroh-owp-hand-fim.s3.amazonaws.com/hand_fim_4_9_9_0/{HUC8}"
FIM_BRANCH = "0"
# Branch 0 = all streams; level-path branches = main stems (FIM takes max extent across branches).
# These 4 level paths carry AOI roads in osm_roads_fimpact.csv (checked Oct 9).
FIM_BRANCHES = ["0", "3286000029", "3286000031", "3286000033", "3286000035"]


def fim_branch_files(b: str) -> dict[str, str]:
    return {
        "hand": f"branches/{b}/rem_zeroed_masked_{b}.tif",
        "catchments": f"branches/{b}/gw_catchments_reaches_filtered_addedAttributes_{b}.tif",
        "hydroid_prefix": f"branches/{b}/hydroid_prefix.txt",
    }


FIM_FILES = {
    "hand": f"branches/{FIM_BRANCH}/rem_zeroed_masked_{FIM_BRANCH}.tif",
    "catchments": f"branches/{FIM_BRANCH}/gw_catchments_reaches_filtered_addedAttributes_{FIM_BRANCH}.tif",
    "hydrotable": f"branches/{FIM_BRANCH}/hydroTable_{FIM_BRANCH}.csv",
    "hydroid_prefix": f"branches/{FIM_BRANCH}/hydroid_prefix.txt",
    "hydrotable_huc": "hydrotable.parquet",
    "fimpact": "osm_roads_fimpact.csv",
    "streams": "nwm_subset_streams.gpkg",
}

# Flood logic
UNCERTAIN_BAND_M = 0.5  # heuristic, see 06-CURRENT_ISSUES R4
BASELINE_GUARD_FACTOR = (
    1.5  # roads wet within 1.5x low flow = artifact (regulated Chattahoochee), R19
)
MIN_ROAD_HAND_M = (
    0.3  # NOAA thresholds below this = road at channel level (culvert/crossing artifact), R3
)
ROUTE_BUFFER_H = 1
SAMPLE_SPACING_M = 10

# Runtime scope (CC6): hazards are checked only around the user and along a searched route
GEORGIA_GEOJSON = ROOT / "fixtures" / "georgia.geojson"  # TIGERweb State 13, simplified
ALERT_RADIUS_KM = 5  # /status: every flagged segment within this radius
CORRIDOR_BUFFER_M = 1000  # /route: every flagged segment within this distance of the route
TRIP_BOX_MARGIN_KM = 5  # /route searches a bbox around origin + destination plus this margin
TRIP_BOX_RETRY_KM = 15  # one retry with a wider box before answering no_route
METRIC_CRS = "EPSG:5070"  # CONUS Albers, metres


def aoi_union(geojson_text: str):
    """Union of all AOI features (one per HUC10) as a shapely geometry."""
    import json

    import shapely
    from shapely.geometry import shape

    return shapely.union_all([shape(f["geometry"]) for f in json.loads(geojson_text)["features"]])


# Runtime (env)
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "")
API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
WEB_BASE = os.environ.get("WEB_BASE", "")
