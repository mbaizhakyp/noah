# 013 — Public traffic cameras (Windy Webcams) during Isaias

| | |
|---|---|
| Owner | Priyanshu |
| Status | Draft |
| Priority | **Step 1 is time-critical (P1): the camera list + assessment loop must run before the heavy rain (Sat morning).** Steps 2–3 are P2, after the Sat 14:00 E2E milestone. |
| Time box | step 1: 45 min · steps 2–3: 2.5 h |
| Depends on | `WINDY_API_KEY` (in `.env`, verified Fri 22:00); 010's `classify()` for step 2; C5 for "near a flagged road" |
| Produces | `data/raw/cctv/cameras.json`, C12, `/cameras` endpoints (C9), camera markers on the map (009) |

> **511GA removed (Priyanshu, Fri Oct 9 ~23:00 ET): not doable this weekend** (developer key under manual review, terms unknown). Windy Webcams is the only camera source. J4's options B/C are superseded.

## Goal
Check public traffic cameras across Georgia for visible water during Isaias, using the same Gemini classifier as 010, and show the results on the map. This gives real ground observations next to the forecast. Helene has nothing to check (no archived frames), so this only applies to Isaias and live use.

## Non-goals
Video. Pothole detection (parking lot). Anything with people or license plates. Committing, re-hosting or redistributing images.

## Known facts (verified Fri Oct 9, ~22:00–22:45 ET)
- **Coverage:** `regions=US.GA` lists **2,467 Georgia webcams** in 462 places. 2,452 are active, 2,440 tagged `traffic`, 1,685 in metro Atlanta, 230 in the Peachtree bbox. Nearly all had updated within the last 2 h.
- **API:** `GET https://api.windy.com/webcams/api/v3/webcams?regions=US.GA&bbox=N,E,S,W&limit=50&offset=N&include=location,categories,images,urls` with header `x-windy-api-key`. The free tier caps `offset` at 1,000, so list Georgia in bbox tiles (quad-split any tile with total > 1,000).
- **Images:** `images.current.preview` (400×224). Free-tier image URLs **expire after 10 minutes**. Fetch fresh URLs each time; never store URLs for later.
- **Terms** (`api.windy.com/webcams/terms`):
  - Show the credit "Webcams provided by Windy.com" with links to windy.com and the add-a-webcam page.
  - Link every displayed image to its webcam page (`urls`) or player.
  - Use images only through API URLs, at original size or smaller.
  - Storing images and automated analysis aren't addressed. **Default: keep only our assessment (C12), never the image.**
- Free-tier request limits aren't published. Pace calls (≤1 req/s) and log any 429s.

## Behavior
**Step 1: list + capture loop (before the heavy rain).**
1. `python -m noah.api.cameras list`: tile Georgia, write `data/raw/cctv/cameras.json` as `[{"cam_id","name","lat","lon","page_url"}]`, and log the count.
2. `caffeinate -i uv run python -m noah.api.cameras watch --every 900`. Every 15 min:
   1. Pick the **watch set**: cameras within 2 km of an active NWS Flood or Flash Flood Warning polygon (07 §2) or of a C5 segment flagged within the next 6 h. Cap the set at 150 cameras per round.
   2. For each camera in the set, fetch a fresh image URL and get the bytes in memory.
   3. Skip the camera if the bytes hash the same as its last round.
   4. Otherwise pass the bytes to step 2's assessment (or queue them in memory until 010 exists) and **discard the bytes**.
   5. Log failures and keep going.

**Step 2: assess (once 010's `classify()` exists).**
3. Run `photo.classify()` on each new frame in the watch set and append to C12 (with `frame_path = null`). Budget: ≤ 500 Gemini calls per day. Log the count.

**Step 3: serve and show.**
4. `/cameras` returns the list with `latest` assessments. `/cameras/{cam_id}/frames` returns assessment history. Each item's `image_url` is a **freshly fetched** Windy URL for the current image only (it expires in 10 min).
5. Map (009 optional layer): camera markers. The popup shows the current image (linked to the webcam page), the latest assessment with its time, and the credit "Webcams provided by Windy.com".
6. Override rule (same as 010): a `bucket ≥ curb` assessment can only upgrade C4 segments within 100 m to `flooded` from that time onward. Never downgrade.

## Discovered
- Fri Oct 9, 22:00–22:45 ET: Windy key works.
  - Georgia counts are as above.
  - Image fetch returned 200, PNG, about 118 KB.
  - Paging past offset 1,000 returns 400 "Offset is over API tier limit 1000!".
  - The `region=` parameter is ignored. Use `regions=`.

## Acceptance criteria
- [ ] Step 1 is running before Sat 08:00. PROGRESS records the Georgia camera count and the watch-set size each round.
- [ ] Across Sat 08:00–Sun 00:00, the watch loop completes ≥ 1 round per hour (log round timestamps).
- [ ] `curl localhost:8000/cameras` returns the list with `latest` assessments.
- [ ] The map shows markers. Clicking one shows the current image + bucket + time + Windy credit, and the image links to its webcam page.
- [ ] No images on disk or in git (`find data/raw/cctv -name '*.jpg' -o -name '*.png'` and `git ls-files | grep -iE 'jpg|png'` are empty for camera frames).

## Test
`tests/test_cameras.py`:
- The Georgia filter keeps an inside camera and drops an outside one.
- The bbox quad-split stops at ≤ 1,000 per tile (pure function on counts).
- The dedupe skips identical bytes.
- The watch-set selector picks cameras within 2 km of a polygon.

## Fallback
- Windy rate-limits us: shrink the watch set to cameras within 1 km of active warnings only.
- Classifier not ready: show current images on the map without assessments, labeled "camera view" only.
