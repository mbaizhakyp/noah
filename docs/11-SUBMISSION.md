# 11 — Submission: Devpost text and video script

_Drafted Sat Oct 10, 15:40 ET. Margulan edits, records the video by 04:00 and submits by 07:00 Sunday. Every number here is in the fact sheet in `08-DEMO.md`._

## Devpost

**Name:** Noah
**Tagline:** Know which roads will flood, and when, before the water gets there.
**Track:** Social Good · **Side challenge:** Photon (Agents in iMessage)
**Links:** GitHub https://github.com/mbaizhakyp/noah · Video [link]

### Inspiration
This weekend Hurricane Isaias hit Atlanta, and Peachtree Creek went from 19 to 3,750 cubic feet per second overnight. More than half of flood drownings happen in a car, and some people can't stay home: nurses, delivery drivers, parents picking up kids. They get a county-wide warning and a map app that reroutes only after a road is reported closed. NOAA publishes flood thresholds for major roads, but not for the side streets where people live.

### What it does
Noah forecasts which roads will flood, and when, up to 18 hours ahead, street by street.
- **For everyday drivers (iPad and web map):** save Work, Home and delivery stops. Noah routes around flooded roads, says when to leave, warns when your own street floods first, and finds the best stop order.
- **For anyone, by text (iMessage):** ask "Can I drive home from Midtown at 6 PM?" and get a plain answer with the street and the time. Text `alerts on` and Noah texts first when a road you use is about to flood. No app, no account.
- **For cities and businesses (Noah Operations):** which schools, hospitals and fire stations get cut off from every open road and when; why a road floods (the creek, its threshold, how often it floods); what to fix first; the best hour to send deliveries; how often a candidate site gets cut off.

Noah never says a road is safe. Uncertain counts as impassable, every answer says it is not a safety guarantee, and it points to 911.

### How we built it
- **Forecast:** NOAA's National Water Model short-range forecast for every creek reach, hourly and 18 h ahead, pulled by a live loop every 15 minutes.
- **Road thresholds:** NOAA OWP's flood-inundation thresholds for major roads, plus our own thresholds for 62,202 residential segments computed from NOAA's HAND rasters and rating curves (they match NOAA's where both exist: no bias, correlation 0.74). Four metro Atlanta watersheds, 1,426 km².
- **Routing:** an OpenStreetMap drive graph (OSMnx, NetworkX); flooded and uncertain roads drop out hour by hour.
- **Live checks:** NWS warnings, TomTom incidents, rain gauges and traffic cameras; a camera counts only when water shows in two AI checks.
- **Agent:** FastAPI backend with an Azure OpenAI tool-calling agent (`check_route`, `check_area`, `remember_place`), reached over iMessage through Photon Spectrum with `spectrum-ts`: typing indicator, photos via `attachment()`, unprompted alerts via `space.send`. A route watch compares each new forecast with the last and texts only on change.
- **Front ends:** MapLibre web map, an iPad app, and the Noah Operations console.

### Challenges we ran into
- NOAA's road list skips residential streets, so the Helene streets that flooded weren't in it. We computed residential thresholds ourselves and checked them against NOAA's.
- Camera AI raised two false alarms on Saturday. We now require water in two consecutive checks plus a human confirmation before a camera counts, and we never re-send those alerts.
- A live storm doesn't wait: Noah ran unattended overnight through Isaias while we built, with the demo on a separate pinned server.

### Accomplishments that we're proud of
- **13.2 hours** of warning before Peachtree Creek's flood stage in Helene, and Windsor Parkway flagged for 10 PM; the city closed it about 10:15 PM.
- Live during Isaias: Friday night's run called Saturday's peaks on Peachtree Creek, the Chattahoochee and Nancy Creek within about 10%, 11 to 13 hours ahead. One creek, South Fork Peachtree, was under-forecast (−78%), and we say so.
- Noah texted route warnings on Saturday morning before anyone asked: 9 of 11 watched routes were warned ahead.

### What we learned
Flood forecasts already exist; the gap is the last mile: turning a creek's flow into "your street, at 7 PM, leave by 6:30", and getting it to people who won't open an app.

### What's next
More watersheds (the same pipeline runs basin by basin on NOAA's national model), storm-drain data where cities publish it, and a pilot with an Atlanta delivery business or city department.

### Built with
python, fastapi, typescript, node.js, maplibre, osmnx, networkx, geopandas, rasterio, xarray, azure-openai, photon-spectrum, noaa-national-water-model, usgs, openstreetmap

### Team and credits
Margulan Baizhakyp built Noah's forecast pipeline, live loop, route watch, iMessage agent and Noah Operations. **Priyanshu Sethi** built, during Hacklanta, the web map, the trip planner and routing API, the live-checks engine and the iPad app, and competes separately in the Fintech track.

## Backup video (2:30, record by 04:00)
Record each screen separately (QuickTime screen recording on the laptop; iPhone and iPad screen recording), then cut in order. Voiceover is the pitch, slightly slower.

| Time | Picture | Voiceover |
|---|---|---|
| 0:00–0:15 | Slide 1 (hook) | "This weekend Hurricane Isaias hit Atlanta. Peachtree Creek went from 19 to 3,750 cubic feet per second overnight. More than half of flood drownings happen in a car." |
| 0:15–0:30 | Slide 2 (gap) | "Warnings cover whole counties. Map apps react after a road is closed. NOAA's road data skips the side streets where people live. Noah fills that gap." |
| 0:30–1:15 | iPad: Work, slide to 7 PM; Home; Deliveries | "This is Hurricane Helene, recorded. At 9 AM the roads are open. Leave work at 7 PM and Noah routes around 12 flooded roads, and warns that your own street floods by then. Going home: leave by 7:55 PM. A pharmacy driver: leave by 7:30 PM to reach all 6 stops; a better order saves 7 minutes." |
| 1:15–1:30 | iPhone: the 5:59 AM Saturday alert in the Noah thread (Graves Rd cut from ~4 AM, Northcrest Way from ~1 PM) | "Noah ran live all weekend. At 6 AM Saturday, before anyone asked, it texted me which routes would be cut and when. No app: it's a text." |
| 1:30–1:45 | Laptop: Deliveries tab on Isaias, Saturday 4 AM | "Same forecast, for a pharmacy with 8 stops: two already cut, hold them; Northcrest Way before noon; the other five show no forecast flooding." |
| 1:45–2:05 | Laptop: City tab on Helene, slide to 2 AM, tap a red road (Why card) | "For a city: by 2 AM, 10 schools, a hospital, an urgent care and a police station are cut off from every open road. Why this road? The creek overtops it, and it floods in every storm we recorded: fix it first." |
| 2:05–2:30 | Slide 4 (proof), then slide 5 (close) | "Helene: 13.2 hours of warning; Noah said Windsor Parkway at 10 PM, the city closed it at 10:15. Isaias, live: Friday night's forecast called Saturday's creek peaks within about 10%, 11 to 13 hours ahead. Noah. Know before the water does." |

Rules for the cut: say "recorded" for Helene; show no API keys, `.env` or terminal tokens; no Windy camera frames in the video (they can't be published).
