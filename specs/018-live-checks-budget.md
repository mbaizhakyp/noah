# 018 — Live checks: a real 12 s budget, cameras off the request path

| | |
|---|---|
| Owner | Priyanshu |
| Status | **Done** (Priyanshu, Sat Oct 10 09:35 ET). Measured after: cold `/assess` 7.7 s (was 31 s), five concurrent legs 7–13 s with 0 failures (was 17–25 s, 2–4 "timeout" each). Approved 09:20. |
| Priority | P1 (demo polish: the live panel looked broken "most of the time") |
| Time box | 1.5 h |
| Depends on | 015 (source runner, `/assess`), 013 (cameras), 009 (web map) |
| Produces | changes to `noah/sources/__init__.py`, `noah/sources/more.py` (cameras), `web/index.html` (assess flow) |

## Goal
A search shows the live panel within 12 s, every source at least starts, and a slow source is reported as *still checking* (its answer lands on the next search) instead of *timeout*. Camera AI verdicts no longer hold the request.

## Why
Measured Sat 09:05: every adapter answers alone in ≤ 6 s, yet one `/assess` took 31 s and five concurrent legs showed 2–4 "timeout after 12 s" each. Causes (all in our code): the pool had 16 workers for 29 adapters so the last 13 queued behind slow ones and were labelled timeout without running; leaving the `with ThreadPoolExecutor` block waited for every straggler, so the response took as long as the slowest adapter while still calling it a timeout; the camera adapter ran two Gemini looks per camera (25 s timeout each) inside the request; the page fired one `/assess/route` per leg and never cancelled stale ones.

## Non-goals
Changing which sources run, the signal contract, scoring or assessment text. One corridor per trip instead of one per leg (parking lot). Reusing `camera_watch` verdicts (parking lot).

## Behavior
1. **Runner** (`sources.run`): one worker per adapter; `wait(budget_s)`; `shutdown(wait=False)`. Stragglers finish in the background and land in the cache. Reported as `{"source", "error": "still checking", "pending": true}` in `sources_failed` (shape unchanged; `pending` is additive). A second search while a source is still running for the same context key reuses the in-flight call (no pile-up). Log one `warning` per straggler and one `info` per adapter slower than 5 s.
2. **Cameras**: Windy listing as before. Verdicts come from the 10 min cache; a missing verdict starts (or reuses) a background AI check in a 4-thread pool and the adapter waits at most 6 s for it. Cameras still unchecked are returned with bucket `checking` (severity info, never blocks a road).
3. **Page**: `runAssess` aborts the previous assess fetches (AbortController, like `/route`). `sources_failed[].pending` rows render amber "still checking", counted separately from "unavailable". `CAM_LABEL.checking` = "AI check still running".

## Acceptance criteria
- [ ] `uv run pytest -q tests/test_engine.py`: budget test returns in < 1.5 s with the slow source pending, then cached on the second call; camera test returns `checking` first and the verdict after.
- [ ] `curl /assess` on a cold cache returns in ≤ 13 s (`took_s`).
- [ ] Five concurrent `/assess/route` legs: no "timeout" strings; only "still checking".

## Test
`tests/test_engine.py`: `test_budget_is_enforced_and_slow_sources_are_pending`, `test_camera_ai_check_runs_in_the_background`.

## Fallback
Revert `run()` to the previous shape (still returns, just slower). Cameras: set `CAM_WAIT_S` high to restore the old inline behaviour.
