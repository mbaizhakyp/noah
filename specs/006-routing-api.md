# 006 — Routing + HTTP API

| | |
|---|---|
| Owner | Priyanshu |
| Status | Draft |
| Time box | 3 h |
| Depends on | C4 + C5 + C6 (use `fixtures/` until real data lands) |
| Produces | C9 endpoints `/health`, `/status`, `/route` (`/chat` is spec 007) |

## Goal
A FastAPI server that answers "what's flooding near here" and "route me from A to B avoiding forecast flooding", using the in-memory graph and flood times.

## Non-goals
Auth, a database, multiple simultaneous cycles per request, turn-by-turn directions, travel-time-aware flooding along the route (`ROUTE_BUFFER_H` covers it).

## Inputs
- C4 `graph.graphml`, C5 `flood_<DEMO_CYCLE>.geojson`, C6 `cycles.json`, C7 `aoi.geojson`.
- Paths from `config.py`, with a `NOAH_DATA=fixtures` env override for fixture mode.

## Outputs
C9 exactly. `map_url` follows C10.

## Behavior
1. **Startup:** load the graph with `ox.load_graphml`, the flood GeoJSON into a dict `seg_id → (t_uncertain, t_flood, name)`, and the AOI polygon. Keep everything in app state.
2. **State of a segment at lead hour h:** `flooded` if `t_flood <= h`; `uncertain` if `t_uncertain <= h`; otherwise `no_forecast_flooding`.
3. **/status:** if the point is outside the AOI → `out_of_coverage`. Otherwise find C5 segments within 300 m (shapely STRtree over C5 geometries in a metric CRS), state each at `h = hours`, and return the worst state (flooded > uncertain > no_forecast_flooding). `eta_utc` = `issue_time + t_* hours`, taken from C6.
4. **/route:** if either endpoint is outside the AOI → `out_of_coverage`. Otherwise snap both points to the nearest nodes (`ox.distance.nearest_nodes`), copy a view of the graph without the edges whose `t_uncertain <= depart_h + ROUTE_BUFFER_H`, and run `nx.shortest_path(weight="travel_time")`. No path → `no_route`. Return the LineString (concatenate the edge geometries, falling back to node coords), total minutes, the `avoided` seg_ids on or near the unconstrained shortest path, and `map_url`.
   - `# ponytail:` removes edges for the whole trip regardless of when you reach them; time-dependent routing is the upgrade.
5. CORS: allow `WEB_BASE` origin only.
6. Every endpoint wraps its logic. On an exception, log the trace server-side and return HTTP 200 with the conservative error state/message from `02-ARCHITECTURE.md` §5.

## Acceptance criteria
- [ ] `uv run uvicorn noah.api.app:app` starts in fixture mode and in real-data mode with no code change (env only).
- [ ] `curl localhost:8000/health` → `{"ok": true, "cycle": ...}`.
- [ ] `curl "localhost:8000/route?from=33.8203,-84.4076&to=33.8490,-84.3730&depart_h=6"` returns `route_found` or `no_route`. The returned geometry avoids every C5 segment with `t_uncertain <= 7`. Prove it with a check printed in the test or a script.
- [ ] A point outside the AOI (e.g., 33.65,-84.42, the airport) → `out_of_coverage` from both endpoints.
- [ ] `uv run pytest tests/test_routing.py` passes.

## Test
`tests/test_routing.py`: a 5-node toy `MultiDiGraph` with a fast edge and a slow detour, and a fake flood dict marking the fast edge `t_uncertain=2`, with `ROUTE_BUFFER_H=1`. Asserts:
- `depart_h=0` → fast path (2 > 0+1);
- `depart_h=1` → detour (2 ≤ 1+1);
- removing the detour too → `no_route`;
- a point outside the toy AOI → `out_of_coverage`.

## Fallback
If graph routing is slow (>2 s), precompute nothing. Instead use `ox.truncate.truncate_graph_bbox` around the two endpoints plus a 3 km margin before routing.
