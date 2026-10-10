# 021 — Noah for iPad: one screen, one sentence

| | |
|---|---|
| Owner | Priyanshu |
| Status | **Approved** (Priyanshu, Sat Oct 10 ~1:00 PM ET: "lets start building the ipad demo version") |
| Priority | P1 (Sunday judging: the iPad the judges hold) |
| Time box | 3 h |
| Depends on | 020 (snapshot), 019 (trips), 013/015 (cameras, live checks) |
| Design | `docs/09-IPAD_APP.md` (warm paper, headline banner) |
| Produces | `web/ipad/index.html`, `web/ipad/manifest.webmanifest`, `web/ipad/icon-180.png`, `GET /cam/{cam_id}` in `noah/api/app.py` |

## Goal
A home-screen web app for the iPad that looks and behaves like the live product. It answers from the `/demo` snapshot (Helene run `20240926T22Z`, clock 7:00 PM). Camera frames are fetched live from Windy. One banner sentence per place (Home / Work / Delivery), a map, and a stop/check list.

## Decisions
- **Data:** every forecast, trip, check and past answer comes from `web/demo/snapshot/` through the same lookup as spec 020 (path + params, nearest departure). The only live calls are the static files and `GET /cam/{cam_id}`.
- **Wording:** nothing user-facing says demo, replay, snapshot, locked, Helene or Isaias. The forecast stamp stays the run's real issue time ("Forecast issued Thu 6:00 PM"), as in spec 020. No invented "updated just now" and no today's date on the forecast.
- **Live checks** keep the "Live" label (Priyanshu). Each camera verdict shows its own recorded check time. The frame above it is labeled with the frame's own time from Windy.
- §5 vocabulary only. Stops use dispatch wording: "Go before {t}", "Hold", "No forecast flooding", plus "Not a safety guarantee." in the stop detail.

## Behavior
1. `/ipad/` opens on Delivery: route drawn, banner "Leave by {leave_by} to reach all {n} stops before their streets flood." When the departure is past leave-by: "Leaving at {t}, you reach {k} of {n} stops."
2. "Leaving {t} ▾" opens a slider (clock → +18 h, 5-min steps). The banner, rows and map update from recorded `/trip` answers. A row whose status changed stays highlighted until tapped.
3. Tap a stop row: the map flies to the stop and the row expands with its reason line, arrival time and "Not a safety guarantee."
4. "Best order" (when `best.differs`): re-asks `/trip` in the best order.
5. "● Live" opens a sheet with Cameras (live frame + recorded verdict), Live checks (signals) and Last 18 h (gauges).
6. Home / Work: banner in §5 words from `/status` / `/route`, list = recorded live checks.
7. `GET /cam/{cam_id}` → `{"cam_id", "image_url", "updated_utc", "title"}` from Windy webcams v3, cached 5 min. 404 when the camera is unknown, 502 when Windy fails.

## Acceptance criteria
- [ ] `/ipad/` network panel: only static files, `/demo/snapshot/...` files and `/cam/...` requests.
- [ ] `grep -i -E "demo|replay|snapshot|helene|isaias|locked"` over user-facing strings in `web/ipad/index.html` finds nothing (code identifiers and paths excepted; text inside live signals, e.g. an NHC storm name, is data, not a label).
- [ ] The banned-word list (§5) does not appear in user-facing strings.
- [ ] Add to Home Screen on iPad opens full-screen with the icon. Landscape and portrait both lay out.
- [ ] Departure slider at 7 PM shows "Leave by 3:25 AM … all 6 stops". At 4:00 AM it shows 4 of 6.

## Fallback
If `/cam/{id}` fails, the frame slot says "Camera not responding" and the recorded verdict still shows. Everything else works from files.
