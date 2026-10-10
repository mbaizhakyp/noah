# 009 — Web map with time slider

| | |
|---|---|
| Owner | Priyanshu |
| Status | Draft |
| Time box | 3 h |
| Depends on | C5, C6, C7 (fixtures first), C8 (optional panel), `/route` (006) for route display |
| Produces | `web/index.html`, served by GitHub Pages; consumes C10 URL params |

## Goal
The judge-facing visual. Drag an hour slider and watch Georgia roads turn amber, then red, hours before the water reaches them (Helene replay on Peachtree Creek, live Isaias statewide). The same page is the link the agent texts, so it must work on a phone.

## Non-goals
Base-road rendering (the base map already draws roads), user accounts, editing, multiple cycles on screen at once, a build step.

## Inputs
`web/data/cycles.json`, `web/data/flood_<cycle>.geojson`, `web/data/aoi.geojson`, optional `web/data/validation.json`, and URL params per C10.

## Outputs
A single static `web/index.html`.

## Behavior
1. MapLibre GL JS from a CDN, **pinned exact version**. Dark base map, free with no key: OpenFreeMap "dark" style, or the CARTO dark-matter GL style **(verify the URL works without a key)**. Attribution visible.
2. **Scope rule (CC6): the map shows hazards only inside the user's 5 km radius (a `near=lat,lon` URL param, drawn as a circle) and along a searched route's 1 km corridor. No pan-to-load and no statewide browsing.** On load: read C6, choose `cycle` from the URL or `demo_cycle`, fetch C5 for it and filter it to the radius / corridor, and fetch C7 (thin Georgia outline + processed HUC8 outlines, so users can see where road-level timing exists).
3. **Slider** over lead hours 0–18. Hour 0 is labeled **"Now (estimated)"**; others show local time (America/New_York) as a forecast, e.g. "Forecast: Thu Sep 26, 9 PM (+7 h)". Layer filters:
   - red line `#ef4444` (width 4): `t_flood <= t`
   - amber line `#f59e0b` (width 3): `t_uncertain <= t` and not red
   - hidden otherwise.
   Plus a "Play" button that steps through one hour per second.
4. **Legend** with text labels: "Do not cross (forecast flooded)", "Uncertain: treat as impassable". Footer: "Forecast replay of Hurricane Helene, Sep 26–27, 2024. River/creek flooding only. Not a safety guarantee. Emergency: 911."
5. **Route mode:** if `from`, `to` and `api` are in the URL, call `{api}/route?...&depart_h={t}`, draw the cyan `#22d3ee` line with start/end markers, and show minutes plus the count of avoided segments. Show `no_route` and `out_of_coverage` as plain banners using the §5 wording.
6. Click a red or amber segment → popup with the street name, the state from §5, and the local time it enters that state.
7. **Validation panel** (collapsible, if C8 exists): lead time ("NWM-based warning N h before Peachtree Creek reached flood stage") plus `validation.png`.
8. Mobile: full-screen map, the slider docked at the bottom, tap targets ≥ 44 px, no horizontal scroll.
9. **Scenario switch** (spec 011): if C6 has more than one `events` entry, show a small dropdown ("Helene 2024 / Isaias 2026") that reloads with that event's `demo_cycle`. Hidden if there's only one event.
10. **Optional layers** (each only if its source exists; a toggle in the legend; off by default on mobile):
    - Low spots (C11, spec 012): dotted violet `#a78bfa` lines, popup with the §5 low-spot text.
    - Cameras (C12 via `/cameras`, spec 013): small camera markers. The popup shows the frame nearest the slider time, its assessment and time, and the credit "Webcams provided by Windy.com" (image links to its webcam page). Needs `api` in the URL.

## Acceptance criteria
- [ ] Open `web/index.html` via `python -m http.server -d web` → fixture roads change color as the slider moves.
- [ ] With the real C5 for `DEMO_CYCLE`, Peachtree and Nancy Creek roads go amber, then red, as the slider advances. Screenshot in PROGRESS.
- [ ] A C10 URL with `from`, `to` and `api` draws a route from the running API.
- [ ] Works in iPhone Safari (open the link from an actual iMessage) and in the 375 px-wide browser preset.
- [ ] No banned words (§5) anywhere in the page text.

## Test
Manual acceptance checks above. No JS test framework.

## Fallback
If a vector base map fails: use OSM raster tiles with a CSS dark filter on the base layer only.
