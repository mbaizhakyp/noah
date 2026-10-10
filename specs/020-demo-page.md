# 020 — /demo: the map on a frozen run with recorded answers

| | |
|---|---|
| Owner | Priyanshu |
| Status | **Approved** (Priyanshu, Sat Oct 10 11:00 ET) |
| Priority | P0 (Sunday judging: no live calls, no surprises) |
| Time box | 3 h |
| Depends on | 009 (map), 015 (live checks), 019 (trips) |
| Produces | `noah/api/demo.py` (build + record), `web/demo/index.html` (generated), `web/demo/snapshot/` (recorded answers, camera snapshots), snapshot mode in `web/index.html` |

## Goal
`/demo/` is the live map, byte for byte except one line, running on one pinned run from `web/data` and answering every API call from files recorded in advance: trips at every departure step, live checks and cameras per leg per hour, the past replay, the Home / Work chips. The page's clock is fixed, every flagged road in scope is drawn on load, and nothing on the page says demo, replay or Helene.

## Decisions
- **Run:** `20240926T22Z` (Helene, issued Thu Sep 26 2024, 6 PM ET): 1,866 flagged segments, 916 forecast flooded, cut hours spread across the window (206 now, 190 in 1–3 h, 402 in 4–8 h, 1,068 later). Clock: issue + 60 min (7 PM).
- **The "Updated" label stays truthful** (the run's issue time). Priyanshu asked for it to read as current; not done: a 2024 forecast stamped as today would mislead judges, and docs/08 (J19) calls for the replay to be labelled. One line in `loadCycle` if the humans decide otherwise.
- Live checks and cameras are today's answers, recorded once; the page shows them as it would live. Camera images are stored locally (`snapshot/img/`), credited to Windy as on the live page.
- The live page (`/`) is unchanged in behaviour: snapshot mode only activates when `window.NOAH_SNAPSHOT` is set, which only the generated `/demo/index.html` does.

## Behavior
1. `demo.py build`: copy `web/index.html` to `web/demo/index.html` injecting `<base href="/">` and `window.NOAH_SNAPSHOT = "demo/snapshot/index.json"`.
2. `demo.py record`: against the running API, for the saved Delivery run: `/trip` at every 5 min from the clock for 6 h then every 30 min to +18 h, for the typed order and for what the plan button produces (best order, dropped stops); `/assess/route` and `/past/route` per leg per hour; Home: `/status`, `/assess`, `/past`; Work: `/route`, `/assess/route`, `/past/route`, `/trip`. Answers are stored by content hash; `image_url`s are downloaded and rewritten. `index.json` = cycle, clock, places, and the list of (path, params, file).
3. Page in snapshot mode: `fetch` is wrapped so API calls resolve to recorded files (match on path + params, numeric-tolerant; a departure time not recorded uses the nearest recorded one). `nowMin()` = the snapshot clock. `loadCycle` pins the snapshot's run (any run on file). No geolocation on landing; instead `showAllRoads()` fills a dimmed layer with every flagged road and fits the map to them. `places` come from the snapshot. The hourly cycle poll is off (pinned).

## Acceptance criteria
- [ ] `/demo/` loads with the network panel showing no `/trip`, `/assess`, `/route`, `/status`, `/past` requests, only `demo/snapshot/...` files.
- [ ] Delivery chip → route, plan card, live checks, cameras with images, past tab, all from the snapshot; the departure slider works at any position.
- [ ] `grep -i "demo\|helene\|replay" web/demo/index.html` shows only the one injected line and code comments; nothing user-facing.

## Fallback
If the snapshot is missing, the page runs live (console warning). If the API is down on Sunday, `/demo/` still works from any static server since every answer is a file.
