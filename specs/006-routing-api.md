# 006 — Routing + HTTP API

| | |
|---|---|
| Owner | Priyanshu |
| Status | **Done** (Priyanshu, Fri Oct 9 ~23:55 ET) |
| Time box | 3 h |
| Depends on | C4 + C5 + C6 (use `fixtures/` until real data lands) |
| Produces | C9 endpoints `/health`, `/status`, `/route` (`/chat` is spec 007) |

## Goal
A FastAPI server that answers "what's flooding near here" and "route me from A to B avoiding forecast flooding", using the in-memory graph and flood times.

> **Scope rule (Priyanshu, Fri Oct 9 ~23:15 ET): full checks, only where the user is or is going.** Noah checks hazards in exactly two places, and checks them completely there:
> 1. **A fixed radius around the user** (`ALERT_RADIUS_KM = 5`).
> 2. **The corridor of a route to a destination the user searched** (`CORRIDOR_BUFFER_M = 1000` around the route line).
>
> Nothing outside those areas is loaded or checked: no map panning, no "load more", no statewide hazard browsing. The creek forecast table (C5) is still computed per cycle by the pipeline, because one NWM file covers every creek; the API only *reads* the part inside the radius or corridor. Live layers (NWS warnings, TomTom, cameras + Gemini) will follow the same two-area rule in their own spec.

## Non-goals
Auth, a database, multiple simultaneous cycles per request, turn-by-turn directions, travel-time-aware flooding along the route (`ROUTE_BUFFER_H` covers it).

## Inputs
- C4 `graph.graphml`, C5 `flood_<cycle>.geojson` (newest live cycle), C6 `cycles.json`, C7 `aoi.geojson`.
- Paths from `config.py`, with a `NOAH_DATA=fixtures` env override for fixture mode.
- Active cycle: optional `cycle` query param (the map sends the cycle it shows); else env `NOAH_CYCLE` (testing); else **the newest C6 cycle with `event == "live"`** (`routing.current_cycle()`, Sat 01:30). No live cycle → the §5 error reply.

## Outputs
C9 exactly. `map_url` follows C10.

## Behavior
1. **Startup:** load the graph with `ox.load_graphml`, the flood GeoJSON into a dict `seg_id → (t_uncertain, t_flood, name)`, and C7 (Georgia polygon + processed `hucs` outlines). Keep everything in app state.
2. **State of a segment at lead hour h:** `flooded` if `t_flood <= h`; `uncertain` if `t_uncertain <= h`; otherwise `no_forecast_flooding`.
3. **/status (the radius check):** if the point is outside Georgia (C7 state polygon) → `out_of_coverage`. If it's in Georgia but outside every processed HUC8 (C7 `hucs`) → `no_road_forecast` (CC6). Otherwise find **every** C5 segment within `ALERT_RADIUS_KM` (shapely STRtree over C5 geometries in a metric CRS), state each at `h = hours`, return them all sorted by distance, and return the worst state (flooded > uncertain > no_forecast_flooding). Each segment gets `distance_m`. `eta_utc` = `issue_time + t_* hours`, taken from C6.
4. **/route:** if `depart_h > 18` → `beyond_forecast_window`. If either endpoint is outside Georgia → `out_of_coverage`. If the graph doesn't contain either endpoint (unprocessed HUC8) → `no_road_forecast` (CC6; statewide routing via Valhalla is the R16 fallback, needs its own spec). Otherwise cut the graph to the **trip box** (bbox of origin + destination, expanded by 5 km) with `ox.truncate.truncate_graph_bbox`, snap both points to the nearest nodes (`ox.distance.nearest_nodes`), copy a view of that subgraph without the edges whose `t_uncertain <= depart_h + ROUTE_BUFFER_H`, and run `nx.shortest_path(weight="travel_time")`. No path → `no_route`. Return the LineString (concatenate the edge geometries, falling back to node coords), total minutes, the `avoided` seg_ids on or near the unconstrained shortest path, **`corridor`: every C5 segment within `CORRIDOR_BUFFER_M` of the returned route with its state at `depart_h`** (the full check along the trip), and `map_url`.
   - `# ponytail:` removes edges for the whole trip regardless of when you reach them; time-dependent routing is the upgrade.
5. CORS: allow `WEB_BASE` origin only.
6. Every endpoint wraps its logic. On an exception, log the trace server-side and return HTTP 200 with the conservative error state/message from `02-ARCHITECTURE.md` §5.

## Discovered (Fri Oct 9, ~23:55 ET)
- **Shared state (I4/I5/I6):** `routing.py` reuses `dispatch.graph_state()`, `flood_state()`, `active_cycle()` and `blocked_weight()`, so the graph is loaded once and both endpoints use the identical blocking rule. `app.py` mounts the dispatch router (I3) and serves `web/` at `/` (I7).
- **Georgia outline:** `fixtures/georgia.geojson` (TIGERweb State 13, simplified, 20 KB). Processed area = C7: HUC8 outline features once CC6 lands, else C7's single polygon (today the Peachtree HUC10).
- **Error replies** use `{"state": "error", "message": <§5 error template>}`. `error` isn't in the C9 state list; consumers (007, 009) should show `message`.
- **Port 8000 was taken** on Priyanshu's laptop by another app, so testing used `--port 8010` with `API_BASE=http://localhost:8010`.
- **Real-data results** (cycle `20240926T12Z`):
  - `/status` at the gauge returned 378 flagged segments within 5 km, matching an independent check exactly. The nearest was Woodward Way NW, flooded from 04Z.
  - `/route` Peachtree Battle → Northside/I-75 at `depart_h=16` detours around 3 flagged segments (4.0 → 4.6 min).
  - `/route` from the gauge → Buckhead becomes `no_route` from `depart_h=16`.
  - Every response took < 0.05 s.

## Acceptance criteria
- [x] `uv run uvicorn noah.api.app:app` starts on real data (graph from `data/interim` or the committed fixture) with no code change.
- [x] `curl localhost:8000/health` → `{"ok": true, "cycle": ...}` (got `20240926T12Z`).
- [x] `curl "localhost:8000/route?from=33.8203,-84.4076&to=33.8490,-84.3730&depart_h=6"` returns `route_found` or `no_route`. The returned geometry avoids every C5 segment with `t_uncertain <= 7`. Prove it with a check printed in the test or a script.
- [x] A point outside Georgia (e.g., 35.05,-85.31, Chattanooga TN) → `out_of_coverage` from both endpoints. A Georgia point in an unprocessed HUC8 (e.g., 31.58,-84.16, Albany GA, unless that HUC8 is processed) → `no_road_forecast`.
- [x] `/status` near the gauge (33.8203,-84.4076) returns every flagged C5 segment within 5 km, and none farther (checked by a script).
- [x] `/route` returns a `corridor` list, and every listed segment is within 1 km of the route line (checked by a script).
- [x] `uv run pytest tests/test_routing.py` passes (5 tests; full suite 18 passed).

## Test
`tests/test_routing.py`: a 5-node toy `MultiDiGraph` with a fast edge and a slow detour, and a fake flood dict marking the fast edge `t_uncertain=2`, with `ROUTE_BUFFER_H=1`. Asserts:
- `depart_h=0` → fast path (2 > 0+1);
- `depart_h=1` → detour (2 ≤ 1+1);
- removing the detour too → `no_route`;
- a point outside the toy Georgia polygon → `out_of_coverage`; inside it but outside the toy `hucs` → `no_road_forecast`.

## Fallback
If routing in the trip box is still slow (>2 s), shrink the margin from 5 km to 3 km and log it. If the route leaves the trip box (no path inside it), retry once with a 15 km margin before returning `no_route`.
