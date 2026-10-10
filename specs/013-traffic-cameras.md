# 013 — Public traffic cameras (511GA) during Isaias

| | |
|---|---|
| Owner | Priyanshu |
| Status | Draft |
| Priority | **Step 1 is time-critical (P1): capture must be running by Sat 01:00.** Steps 2–3 are P2, after the Sat 14:00 E2E milestone. |
| Time box | step 1: 45 min · steps 2–3: 2.5 h |
| Depends on | 511GA developer key; 010's `classify()` for step 2; C5 for "near a flagged road" |
| Produces | `data/raw/cctv/` frames, C12, `/cameras` endpoints (C9), camera markers on the map (009) |

## Goal
Capture Georgia DOT traffic-camera snapshots in and around the Peachtree Creek watershed throughout Isaias. Check them for visible water with the same Gemini classifier as 010 and show them on the map. This gives real ground observations next to the forecast. For Helene there's nothing to capture (cameras keep no recordings), so this only applies to Isaias and live use.

## Non-goals
Video. Pothole detection (parking lot). Anything with people or license plates. Cameras outside GDOT 511GA. Committing or publicly hosting images.

## Known facts (verify during step 1)
- 511GA has a REST API with a Cameras resource (`511ga.org/developers/doc`). It needs a free developer key (create an account, then request a key). Rate limit: **10 calls per 60 s**.
- **The cameras don't record.** Any frame we don't capture live is gone, so capture must start before the rain (heaviest Sat early morning through Sat night).
- Coverage is GDOT routes (interstates and state routes such as GA-400, Peachtree Rd, Northside Dr). City side streets aren't covered.
- **Terms for storing and redisplaying snapshots are unverified.** Read them during key signup and note them in "Discovered". Until they're confirmed: frames stay in `data/raw/` (gitignored), are shown only from the laptop during judging with "Image: Georgia DOT / 511GA" attribution, and get deleted after the event.

## Behavior
**Step 1: capture (tonight, before sleeping).**
1. `python -m noah.api.cameras list`: one Cameras API call, filtered to the AOI bbox + 1 km. Write `data/raw/cctv/cameras.json` (C12 camera list). Log the count.
2. `caffeinate -i uv run python -m noah.api.cameras capture --every 300`: every 5 min, fetch each camera's image URL and save `data/raw/cctv/<cam_id>/<YYYYMMDDTHHMMSSZ>.jpg`. Skip a frame if its bytes hash the same as the previous one. Keep total requests within the rate limit (whether image fetches count toward it is **(verify)**; to be safe, space them so total requests stay ≤ 10 per minute). Log failures and keep going. Run on a laptop that stays plugged in and awake from ≤ Sat 01:00 to Sun 06:00.

**Step 2: assess (Sat afternoon, after 010's `classify()` exists).**
3. Sample frames: one per camera every 30 min, plus every frame from cameras within 300 m of any Isaias C5 segment (if 011 is GO). Budget ≤ 500 Gemini calls.
4. Run `photo.classify()` on each and write C12.

**Step 3: serve and show.**
5. Add the `/cameras` and `/cameras/{cam_id}/frames` endpoints (C9) and mount `data/raw/cctv/` as static files.
6. Map (009 optional layer): camera markers; the popup shows the frame nearest the slider time with its assessment and attribution.
7. Override rule (same as 010): a `bucket ≥ curb` assessment can only upgrade C4 segments within 100 m to `flooded` for that time onward. Never downgrade.

## Discovered
_Fill in: API base, key signup and terms text (summary), camera count in the AOI, image URL format, whether image fetches count against the rate limit._

## Acceptance criteria
- [ ] Step 1 is running by Sat 01:00. PROGRESS records the camera count and the frame count at 01:00 and again on waking.
- [ ] By Sun 06:00, ≥ 1 frame per camera per hour across Sat 00:00–Sun 00:00 for most cameras (log coverage per camera).
- [ ] `curl localhost:8000/cameras` returns the list with `latest` assessments.
- [ ] The map shows markers. Clicking one shows a frame + bucket + attribution.
- [ ] No images in git (`git ls-files | grep -i jpg` is empty).

## Test
`tests/test_cameras.py`: the AOI filter keeps an inside camera and drops an outside one; the dedupe skips identical bytes.

## Fallback
- No developer key by 00:00 → decision **J4**:
  - **Option B (gray area):** a person browses the 511ga.org camera map by hand and notes 10–15 AOI camera image IDs. The script fetches only those image URLs (`https://511ga.org/map/Cctv/<id>`), each once per 5 min (~3 req/min), with attribution, kept local and deleted after. `robots.txt` (checked Oct 9) disallows `/list/getdata/` (the camera-list JSON), so **never** call that endpoint. The image path isn't disallowed, but the terms of use are unverified.
  - **Option C (clean):** our own photos/short clips of streets during Isaias, taken from sidewalks only. Never enter water, never film while driving. Same `classify()` pipeline, with "camera" relabeled "team photo".
- Classifier not ready: show raw frames on the map without assessments, labeled "camera view" only.
