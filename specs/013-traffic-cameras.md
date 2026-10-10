# 013 — Camera snapshot check (Windy Webcams), on demand

| | |
|---|---|
| Owner | Priyanshu |
| Status | Draft |
| Priority | P2. Start after the Sat 14:00 E2E milestone. Not time-critical: nothing runs in the background. |
| Time box | 2 h |
| Depends on | `WINDY_API_KEY` (in `.env`, verified Fri 22:00); 010's `classify()`; 006's `/status` and `/route` |
| Produces | `noah/api/cameras.py`, a `cameras` field in `/status` and `/route`, camera markers on the map (009) |

> **Design (Priyanshu, Fri Oct 9 ~23:59 ET): no 24/7 monitoring.** Cameras are checked **only when a user asks**: when they check their area (`/status`) or search a route (`/route`). Noah takes the snapshot each nearby camera shows *at that moment*, runs it through the water check, and returns the result. No background loop, no recording, no stored images. 511GA was dropped earlier (not doable).

## Goal
When a user checks their 5 km radius or searches a route, show what the nearest public traffic cameras see **right now**: water on the road or not. This gives a live, real observation next to the creek forecast.

## Non-goals
Background capture or monitoring. Recording or storing images. Video. Pothole detection (parking lot). Anything about people or license plates. Cameras outside the user's radius or route corridor.

## Known facts (verified Fri Oct 9, ~22:00–22:45 ET)
- **Coverage:** Windy lists **2,467 Georgia webcams** (`regions=US.GA`): 2,440 traffic, 1,685 in metro Atlanta, 230 in the Peachtree bbox. Nearly all had updated within the last 2 h.
- **API:** `GET https://api.windy.com/webcams/api/v3/webcams?nearby={lat},{lon},{radius_km}&limit=50&include=location,images,urls` with header `x-windy-api-key`. Paging stops at offset 1,000 on the free tier. A radius query never comes near that.
- **Images:** `images.current.preview` (400×224). Free-tier image URLs expire after **10 minutes**.
- **Terms:** show the credit "Webcams provided by Windy.com" with links, link each displayed image to its webcam page, and use images only through API URLs at original size or smaller. Storing images isn't addressed, so we never store them.

## Behavior
1. **`cameras_near(lat, lon, radius_km)`**: one Windy `nearby` call (`include=location,images,urls`). Returns active cameras with `cam_id, name, lat, lon, image_url, page_url` (`page_url` = `urls.detail`). Cache the camera *list* per ~1 km grid cell for 10 minutes; image URLs expire after that anyway.
2. **`check(cam)`**: fetch the current snapshot bytes in memory → `photo.classify(bytes)` (010) → `{bucket, confidence, reference_object}`. Discard the bytes. Cache the *result* per `cam_id` for **10 minutes**, so many users near the same camera cost one Gemini call.
3. **In `/status`**: pick the `MAX_CAMS_STATUS = 5` cameras nearest the user within `ALERT_RADIUS_KM`. Check them in parallel (thread pool, 8 s total timeout) and add `"cameras": [{cam_id, name, lat, lon, distance_m, ts_utc, bucket, confidence, image_url, page_url}]`.
4. **In `/route`**: cameras within `CORRIDOR_BUFFER_M` of the route line, at most `MAX_CAMS_ROUTE = 8`, spread along the route (nearest to evenly spaced points). Same check, same fields, under `"cameras"`.
5. **Override rule:** a `bucket ≥ curb` result upgrades C4/C5 segments within 100 m of that camera to `flooded` **for that response**, and the reply uses the §5 "camera water" wording. Never downgrade: a dry camera never clears a forecast flag.
6. **Failure:** if Windy, the snapshot or Gemini fails or times out, that camera returns `bucket: "cant_tell"` and the response still returns on time. Cameras never block a forecast answer.
7. **Map (009):** camera markers for the cameras in the response only. The popup shows the water result and its time, plus a **"View camera" button that shows the current snapshot only when the user taps it** (still image, no video, no time-lapse player). The snapshot is fetched fresh at tap time (URLs expire in 10 min), links to the camera's Windy page (required by Windy's terms), and carries "Webcams provided by Windy.com".
   - Decided (Priyanshu, Sat 00:05): **snapshots only**. Windy also offers an embeddable 24 h time-lapse player (`player.day`, verified embeddable), but we don't use it. Windy's camera page can't be embedded (`frame-ancestors`), so it opens in a new tab. Windy lists these cameras' provider as `511ga.org`: they're GDOT cameras, used under Windy's terms.
8. **Log** each check (cam_id, time, bucket, confidence; no image) to C12 for the demo stats and backtesting.

## Acceptance criteria
- [ ] `curl "localhost:8000/status?lat=33.84&lon=-84.38"` returns a `cameras` list (≤ 5) with a bucket for each, in under 10 s cold and under 1 s on a repeat within 10 min (cache).
- [ ] `/route` returns ≤ 8 corridor cameras, each within 1 km of the route line (checked by a script).
- [ ] With Windy unreachable (bad key in env), `/status` still returns the forecast answer and cameras show `cant_tell`.
- [ ] No image files anywhere: `find . -name '*.jpg' -o -name '*.png' -newer specs/013-traffic-cameras.md` (excluding `web/` assets) is empty, and nothing camera-related is in git.
- [ ] The map popup shows the result and time. Tapping "View camera" shows the current snapshot with the Windy credit, and the image links to the webcam page.

## Test
`tests/test_cameras.py` (no network):
- Corridor selection keeps cameras within 1 km of a line and caps at 8, spread out.
- The radius pick returns the 5 nearest.
- The result cache returns the cached value inside 10 min and refetches after.
- The override upgrades and never downgrades.

## Fallback
Gemini unavailable or over budget: show the snapshots with "camera view" only, with no assessment and no override.
