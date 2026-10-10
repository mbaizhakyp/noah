# 01 — Project Overview

## One line
**Noah: Waze for floods that warns you before the road goes under, not after.**

## Problem
- Driving into floodwater is a leading cause of US flood deaths.
- Official warnings are county-wide, not street-level.
- Map apps react only after someone reports a closure.
- Small ungauged creeks get the least warning.
- Local story: Hurricane Helene, Sep 26–27, 2024. Peachtree Creek at Atlanta (USGS 02336300 / NWS AANG1) crossed minor flood stage (17 ft) at **9:15 PM EDT Sep 26** and crested at **23.75 ft at 8:15 AM Sep 27**, nearly 4 ft above major flood stage (20 ft). Source: USGS IV data, pulled Oct 9, 2026.

## What Noah does
1. **Forecasts road flooding.** For every drivable road segment in the coverage area: will it flood in the next 18 h, and from roughly which hour.
2. **Routes around it.** Shortest path with flooded and uncertain segments removed.
3. **Answers by text.** A Gemini agent in iMessage (via Photon Spectrum) handles "can I get home tonight?", "is Northside Dr flooding?" and "route me from X to Y".
4. **Shows it.** A web map with a time slider where roads turn amber, then red, as the forecast hours pass.

## Who it's for
People who have to drive during a flood event in neighborhoods along small urban creeks. These areas get county-wide warnings and no street-level detail. Delivery by text means no app install is needed.

## Coverage
- **MVP:** Peachtree Creek watershed, HUC10 `0313000112` (338 km², north/central Atlanta), inside HUC8 `03130001` (Upper Chattahoochee).
- **Expansion path:** the HAND data we download covers all of HUC8 03130001, so adding more of metro Atlanta means changing only the AOI polygon. Other HUC8s mean another download.

## What Noah is not (state these to judges)
- Not a flood *mapping* product. NOAA already publishes inundation maps. Our contribution is road-level timing, predictive routing, and delivery by text.
- Covers river and creek flooding only. **It does not cover storm-drain or flash street flooding.**
- **Never says a road is safe.** Outputs stay conservative (see `02-ARCHITECTURE.md` §5).
- Not a replacement for official warnings or 911.

## Hackathon frame
- **Event:** Hacklanta 2026, GSU Atlanta. Hacking runs Fri Oct 9, 8:30 PM to **Sun Oct 11, 9:00 AM ET (hard)**.
- **Main track:** Social Good (Cox). The prompt, "people and places that get overlooked: access, safety, mobility", maps to safety (flood deaths), mobility (routing), and overlooked places (ungauged small creeks).
- **Side challenges (2):** Photon: Agents in iMessage (must use Spectrum SDK). MLH: Best Use of Gemini API.
- **Judging:** 3-min pitch + 2-min Q&A with 2 judges. Criteria: fits the prompt, polish, presentation, compelling use case.
- **Submission:** Devpost write-up, public GitHub repo with a useful README, 2–3 min public demo video, demo link or run instructions.

## Team
| Person | Role | Strengths |
|---|---|---|
| Margulan | Hydrology + data pipeline, validation, pitch domain expert | Flood-risk / water-resources research, NWM / NextGen |
| Priyanshu | Runtime: API, routing, agent, iMessage relay, web map | — |

Both build with Claude Code. No lab code is reused; everything is built fresh during the event.

## Locked decisions (Oct 9, 2026)
| # | Decision | Value |
|---|---|---|
| D1 | Team | Margulan + Priyanshu |
| D2 | Side challenges | Photon iMessage + MLH Gemini. Mercedes CV dropped; no Tiger Data. |
| D3 | Name / domain | Noah; no domain purchase |
| D4 | Coverage | Peachtree Creek HUC10 first, expandable within HUC8 03130001 |
| D5 | Replay clock | Demo "now" = NWM short-range cycle **2024-09-26 18Z (2:00 PM EDT)**, provisional. Final rule: the earliest cycle from 12Z Sep 26 onward whose forecast at the gauge reach (feature_id 2047989) exceeds the minor-flood flow (5,700 cfs = 161.4 m³/s). Set by spec 005 after the midnight go/no-go. |
| D6 | Output wording | Four frozen states: **Do not cross / Uncertain: treat as impassable / No forecast flooding (not a safety guarantee) / Outside coverage**. Exact text in `02-ARCHITECTURE.md` §5. |
| D7 | Data store | No database. Parquet + GeoJSON files, loaded into memory by the API. |
| D8 | Hosting | Static map on GitHub Pages (`/web`). API + iMessage relay run on a laptop, exposed with a `cloudflared` quick tunnel during judging. |

## Demo script (target, 3 min)
1. **Hook (20 s).** Helene, Peachtree Creek, Sep 26, 2024. People were driving home that night.
2. **Map replay (60 s).** It's 2:00 PM. Drag the slider and watch roads along Peachtree and Nancy Creek go amber, then red, from about 9 PM, hours before the crest. Show the lead-time number from spec 005 and 2–3 streets confirmed by news photos.
3. **Live iMessage (60 s).** On a real phone: "can I get home to [address] tonight?" Noah answers "Do not cross X; here's a detour" with a map link.
4. **How + limits (30 s).** NWM → rating curves → HAND → roads. River/creek only. Never says safe.
5. **Ask/close (10 s).**
