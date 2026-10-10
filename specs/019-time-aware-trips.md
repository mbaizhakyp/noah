# 019 — Time-aware trips: instant route, then the forecast, then the order that keeps the most stops

| | |
|---|---|
| Owner | Priyanshu |
| Status | **Done** (Priyanshu, Sat Oct 10 10:50 ET): 5-stop trip 9.3 s cold / 1.4 s warm; verified in Chrome. Approved 10:05. |
| Priority | P0 (demo: Maya's delivery run, Jordan's commute) |
| Time box | 4 h (step 1 → 2 → 3; stop at 1.5×, log in 06) |
| Depends on | 006 (routing, `/route`), 009 (map), 014 (verdict vocabulary), 015 (live checks) |
| Produces | `noah/api/trip.py` (`GET /trip`), time-aware blocking in `routing.route`, page flow in `web/index.html` |

## Goal
A search draws the fastest route and Noah's forecast-aware route within a second, every road on it checked against the hour the driver actually reaches it. For a trip with stops, Noah returns the order that reaches the most stops before their roads are forecast cut, the stops it has to skip (with the hour and the road), and the latest departure that still makes them all. Live checks and cameras overlay afterwards and can re-route.

## Why (measured Sat 09:50)
- `/route` removes a road if it is forecast uncertain by *departure* + 1 h, regardless of when the driver reaches it. Later legs of a tour are routed as if they left at the same time as the first.
- `/plan` is per-stop reachability from the depot, sorted by first cut hour. It never drives between stops, so "reorder" and "leave by" ignore geography.
- The page holds the route up to 8 s for live checks before drawing anything (`CHECK_WAIT_MS`).
- A trip box over six Atlanta points: 37 k nodes, one Dijkstra 0.2 s, only 3 distinct blocked-road sets across 18 h (blocking only grows). A time-aware exact solution is cheap.

## Non-goals
Recession (`t_clear`): the pipeline has no "back below flood level" hour, so Noah never says "leave later" until Margulan adds that additive field (parking lot). Traffic. Re-optimising mid-trip. Replacing the dispatch board (014).

## Behavior
1. **Time-aware blocking** (`trip.td_dijkstra`): an edge is usable only if its forecast uncertain hour is later than `depart_h + (seconds to reach it)/3600 + ROUTE_BUFFER_H`. Blocking is monotone and there is no waiting, so label-setting Dijkstra is exact. Runs on a compact adjacency of the trip box (`trip.Net`, cached per cycle + box). `routing.route` uses it for the detour and for `avoided` (roads on the fastest way that are blocked at the time the fastest way reaches them).
2. **`GET /trip?from=&to=&stops=lat,lon;…&depart_h=<float hours>&cycle=&corridor_m=`** (origin, up to 9 stops, destination last):
   - Travel-time matrix `tt(i, h)` between all points, leaving point i at integer lead hour h, memoised; a stop whose own street is blocked at arrival counts as unreachable.
   - **Current order**: simulate the drive; a stop that cannot be reached in time is skipped (`hold`) and the drive continues to the next. Legs are routed with their real departure time; each leg returns `geometry`, `usual_geometry` (fastest way, when it differs), `avoided`, `corridor`, `minutes`. `route` is the legs joined in the page's `combineLegs` shape.
   - **Best order**: exact search over subsets (≤ 9 stops, destination fixed last). Objective: most stops reached, then least driving time, then fewest swaps from the user's order.
   - **Leave by** for both orders: the latest departure (5 min steps) that still reaches the same stops. Null when leaving now already loses one.
   - Per stop: `state` ∈ {`no_forecast_flooding`, `go_before`, `hold`, `out_of_coverage`} (014 vocabulary), `cut_h`/`cut_utc` (first hour the depot can no longer reach it), `arrive_min`, `reached`.
3. **Page**: with stops, one `/trip` call replaces N `/route` + `/plan`; without stops `/route` + `/trip` (for leave-by). Draw first: usual way, Noah's route, cut labels and flagged roads go on the map as soon as the route call returns. Live checks, cameras and the past replay start at the same time and overlay when they land. The plan card shows "This order reaches X of N; your order reaches Y", the skipped stops with hour and road, and leave-by; the reorder button applies the best order.

## Acceptance criteria
- [ ] `uv run pytest -q tests/test_trip.py`: a road flooding at hour 2 is allowed at minute 30 of a trip leaving at hour 0 and blocked when the same trip leaves at hour 0.6; the best order visits the early-cut stop first; a stop no order can reach is `hold`.
- [ ] `curl "/trip?…5 stops…"` returns in < 6 s cold, < 1 s warm, with `legs`, `order`, `leave_by_min`.
- [ ] On the map, the route is on screen before the live panel finishes (no 8 s hold).
- [ ] No user-facing text says safe / clear / passable.

## Test
`tests/test_trip.py` on a hand-built 6-node graph (no files, no network).

## Fallback
Keep `/route` + `/plan` as they are (both stay served); the page's old per-leg path is one flag away (`USE_TRIP = false`).
