# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
- **Primary design target: hackathon judges on a laptop** (Hacklanta 2026, 3-min pitch + 2-min Q&A, likely projected). They watch the live demo of `web/index.html`: check an area, scrub the 18-hour forecast, route around flooded roads, hand off to Google/Apple Maps.
- **The audience the product serves: people anywhere in Georgia who have to drive during heavy rain or a flood event**, especially along small creeks and rivers that get only county-wide warnings. They reach the map through a link the iMessage agent texts them, so the page must still work on a phone (spec 009), even though the laptop demo is optimized first.
- Small-business dispatchers (`web/dispatch.html`, spec 014) are a separate audience owned by Margulan and out of scope for design work from this seat unless both owners agree.

## Product Purpose
Noah forecasts which drivable road segments will flood in the next 18 hours and roughly from which hour, routes around them, and answers plain questions by text. It exists because driving into floodwater is a leading cause of US flood deaths, official warnings are county-wide, and map apps react only after a closure is reported. Success: a driver (and a judge) sees, before leaving, which roads near them or on their route are forecast to go under and when, from the latest live NOAA run.

## Positioning
Road-level flood **timing** before the water arrives, not after a report: NOAA National Water Model streamflow forecasts × HAND elevation per OpenStreetMap road, refreshed every hourly cycle, delivered as a route and a text reply. It is not a flood-mapping product (NOAA already publishes inundation maps) and not a replacement for official warnings or 911.

## Operating Context
- Everyday, always-live app: "now" is the newest live NWM cycle, refreshed hourly. Not framed around any single storm; past storms are validation only.
- On demand only: the map is empty until the user taps **Use my location** / types a place (5 km area check) or searches a destination (route + 1 km corridor). No statewide browsing.
- Time slider over lead hours 0–18 ("Now (estimated)" at hour 0) with Play; past mode back to −18 h.
- Confirmation layers around the forecast: NWS warnings, MRMS, river forecasts, rain gauges, TomTom incidents, Windy traffic cameras, an AI assessment panel with cited sources.
- Hand-off buttons to Google Maps and Apple Maps, with a note that those apps choose their own roads between waypoints.

## Capabilities and Constraints
- Stack (existing): single static HTML pages, MapLibre GL JS from a CDN with pinned exact versions, free keyless dark base map, no build step, served by the FastAPI app on the same origin.
- Coverage: road-level timing only in HUC8 03130001 (Upper Chattahoochee, metro Atlanta); elsewhere in Georgia, statewide hazards plus "no road-level forecast here yet"; outside Georgia, out of coverage.
- Road timing covers creek/river flooding only; it does not forecast storm-drain or flash street flooding.
- **Frozen user-facing vocabulary** (`docs/02-ARCHITECTURE.md` §5): Do not cross / Uncertain: treat as impassable / No forecast flooding (not a safety guarantee) / Outside coverage, plus the dispatch, low-spot and camera templates. Always say "forecast"; times in America/New_York.
- **Banned in any output:** "safe", "safely", "clear", "passable", "you're fine", "no risk".
- Map line semantics from spec 009: red `#ef4444` = forecast flooded, amber `#f59e0b` = uncertain.
- Hard deadline: features freeze Sun Oct 11 2026 00:00 ET; internal submission 07:00 ET.
- Design work from this seat touches `web/index.html` only (owner rule, `docs/05-PROGRESS.md`).

## Brand Commitments
- Name: **Noah**. Line: "Waze for floods that warns you before the road goes under, not after."
- Voice: **calm, plain, serious**, like a good emergency broadcaster. Short and direct; no jokes near danger. Any personality lives only in non-hazard moments. Hazard copy uses the frozen vocabulary verbatim in meaning.
- "Turn Around Don't Drown." and a 911 mention whenever a message describes danger.
- Required attributions: "Webcams provided by Windy.com", base-map attribution visible.

## Evidence on Hand
- Live NWM cycles and flood GeoJSON in `web/data/` (`cycles.json`, `flood_<cycle>.geojson`, `aoi.geojson`), produced by the pipeline.
- Helene backtest (validation only): 13.2 h lead, Windsor Pkwy forecast 10 PM vs 10:15 PM actual closure.
- Data sources: 82 verified sources in `docs/07-DATA_SOURCES.md`.
- **Absent, never fabricate:** user testimonials, adoption numbers, accuracy percentages beyond what validation code produced, partner logos, user photos.

## Product Principles
1. **Never imply safety.** Absence of a forecast is never a green light; the most conservative reading wins, and cameras or reports may only make a road more conservative.
2. **Before, not after.** The time dimension (when the water arrives) is the product; every surface should make lead time legible.
3. **Real data or nothing.** If code didn't produce the number, it doesn't appear. Every claim is traceable to a cited source.
4. **Local and on demand.** Show the user's area or route, not the state; quiet until asked.
5. **Honest limits.** Say plainly where road-level timing doesn't exist yet and what Noah does not model.

## Accessibility & Inclusion
- Red/amber hazard states must never rely on color alone (pair with labels or line style), since the audience includes color-blind drivers and a projector washes out color.
- Must work one-handed on a phone from a texted link (44 px targets already used in the code), and stay readable on a projected laptop screen.
