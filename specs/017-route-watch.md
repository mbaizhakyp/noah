# 017 — Route watch (hours-ahead proof + camera proof + Noah texts first)

| | |
|---|---|
| Owner | Margulan |
| Status | Approved (Margulan, Sat Oct 10 04:00, chat) |
| Time box | 3 h (stop at 4.5 h, log in 06-CURRENT_ISSUES) |
| Depends on | 011 live loop (C5/C6), BL-22 camera monitor, 008 relay, 014 graph helpers |
| Produces | `web/data/watch_routes.json`, `web/data/route_watch.json`, `data/interim/outbox.jsonl` |

## Goal
About a dozen fixed A→B routes that pass traffic cameras next to roads the live Isaias runs flagged. For every hourly
live run, log each route's forecast status, so on Sunday we can say "Noah first warned at X, N hours before the camera
saw water / the road closed". Status changes and confirmed camera water reach Margulan's phone by iMessage (Photon),
with the evidence photo when there is one.

## Non-goals
Per-user saved-route alerts (that's the J18 "Noah texts first" idea; this is the demo-route version). Detours. Any
claim that a camera will see water: cameras are a bonus, not guaranteed.

## Behavior
1. `route_watch --pick` (once): union of roads flagged in all live runs; Windy cameras (BL-22 cache) within 300 m of one;
   greedy one anchor per ~1.2 km cluster, most-often-flagged first, up to 12. For each anchor road segment u→v, pick
   endpoints A (2–6 min drive before u) and B (2–6 min after v), farthest apart, such that the plain fastest A→B path
   drives that segment. Store path seg_ids (+ reverse twins), line, and up to 4 cameras within 150 m of the line.
2. `route_watch --every 300`: for every live cycle not yet logged, each route's status = earliest t_uncertain /
   t_flood among its segments, the street, and when Noah had the run (C5 file mtime). Backfills silently.
3. Newest run vs the previous one: new flag, flag dropped, or the time moved ≥ 1 h → one digest message per run.
4. Camera rows in `camera_checks.jsonl` with `verified` water and an evidence card → one message with the photo, naming
   the route and how long after Noah's first warning it came.
5. Messages go to `data/interim/outbox.jsonl` (+ ntfy). The relay sends new outbox lines to every thread that texted
   "alerts on" ("alerts off" stops). Photos only go to the subscriber's own phone (Windy credit on the card).
6. `camera_watch` adds the route cameras to its watch list and records the evidence path on its check row.

All text uses §5 vocabulary: "Do not cross {road}", "uncertain, treat as impassable", never "safe/clear/passable".

## Acceptance criteria
- [ ] `uv run python -m noah.pipeline.route_watch --pick` writes ~12 routes, each with ≥ 1 camera.
- [ ] `--once` logs every live run so far for every route; `--report` prints first warning per route.
- [ ] "alerts on" from the iPhone, then a test outbox line → arrives as an iMessage (with a photo for a card).
- [ ] `uv run pytest tests/test_route_watch.py` and `npm test` pass.

## Test
`tests/test_route_watch.py`: status from C5 props, change detection (new / dropped / moved ≥ 1 h / unchanged),
digest never banned. `bot/relay.test.ts`: alert command parsing.

## Fallback
iMessage push fails → ntfy push (already on the phone) carries the same text; proof log still works offline.
