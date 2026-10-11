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
- **For everyday drivers (iPad app):** save Work, Home and delivery stops. Noah routes around flooded roads, says when to leave, warns when your own street floods first, and finds the best stop order.
- **For anyone, by text (iMessage):** ask "Can I drive home from Midtown at 6 PM?" and get a plain answer with the street and the time. Text `alerts on` and Noah texts first when a road you use is about to flood. No app, no account.
- **For cities and businesses (Noah Operations):** which schools, hospitals and fire stations get cut off from every open road and when; why a road floods (the creek, its threshold, how often it floods); what to fix first; the best hour to send deliveries; how often a candidate site gets cut off.

Noah never says a road is safe. Uncertain counts as impassable, every answer says it is not a safety guarantee, and it points to 911.

### How we built it
- **Forecast:** NOAA's National Water Model short-range forecast for every creek reach, hourly and 18 h ahead, pulled by a live loop every 15 minutes.
- **Road thresholds:** NOAA OWP's flood-inundation thresholds for major roads, plus our own thresholds for 62,202 residential segments computed from NOAA's HAND rasters and rating curves (they match NOAA's where both exist: no bias, correlation 0.74). Four metro Atlanta watersheds, 1,426 km².
- **Routing:** an OpenStreetMap drive graph (OSMnx, NetworkX); flooded and uncertain roads drop out hour by hour.
- **Live checks:** NWS warnings, TomTom incidents, rain gauges and traffic cameras; a camera counts only when water shows in two AI checks.
- **Agent:** FastAPI backend with an Azure OpenAI tool-calling agent (`check_route`, `check_area`, `remember_place`), reached over iMessage through Photon Spectrum with `spectrum-ts`: typing indicator, photos via `attachment()`, unprompted alerts via `space.send`. A route watch compares each new forecast with the last and texts only on change.
- **Front ends:** an iPad app for everyday drivers and the Noah Operations console for cities and businesses (both MapLibre).

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

## Demo video (2:40, J39; replaces the 2:30 draft)
Record each segment as its own clip and narrate while you record; redo a clip, never the whole video. ~400 words at a calm pace = 2:40. If a number on screen differs from the script, say the screen's number.

**1. Hook (0:00–0:12) · Laptop, landing page `http://localhost:8100/`, hold on the storm.**
"This weekend, Hurricane Isaias hit Atlanta. Overnight, Peachtree Creek went from 19 to 3,750 cubic feet per second. And more than half of flood drownings happen in a car."

**2. The gap (0:12–0:30) · Scroll slowly to the Analyze / Monitor / Predict cards.**
"Warnings cover whole counties. Map apps reroute only after a road is closed. NOAA's road flood data covers major roads, not the side streets where people live. Noah fills that gap: it predicts which streets will flood, and when, up to 18 hours ahead."

**3. People (0:30–1:05) · iPad, People tab (Helene). Work route, drag the time bar to 7 PM; Home; Deliveries.**
"This is Hurricane Helene, recorded, so you can live through a whole day of it. At 9 AM the roads are open. Slide to 7 PM: leaving work, Noah routes around 12 flooded roads and warns that my own street floods by then. Going home, leave by 7:55. A pharmacy driver with six stops: leave by 7:30, and a better order saves seven minutes."

**4. iMessage (1:05–1:35) · iPhone, Noah thread. Scroll up to Saturday's 5:59 AM alert, then send: "Give me CCTV images of a 5-mile radius from Georgia State University and evaluate risks." Crop or blur the photo album; keep the checklist.**
"You don't need the app. Noah lives in iMessage, through Photon Spectrum. It ran live all weekend through Isaias, and at 6 AM Saturday, before I asked, it texted me which of my routes would be cut, and when: 9 of 11 watched routes were warned ahead. Ask for traffic cameras, and it pulls six live cameras, checks each for water with AI, and builds a risk checklist from official warnings, rain and creek levels, and public reports. It never calls a road safe."

**5. Deliveries (1:35–1:50) · iPad, Deliveries tab (Isaias, Sat 4 AM).**
"The same live forecast, for a business: at 4 AM Saturday, a pharmacy with eight stops sees two already cut. Hold those, and finish Northcrest Way before noon."

**6. City (1:50–2:20) · iPad, City tab (Helene). At 8 PM tap "Show vulnerable neighborhoods"; slide to 2 AM; tap a red road for its card.**
"For a city, Helene again: by 8 PM, 16 percent of the cut roads are in the most vulnerable neighborhoods, which hold only 9 percent of the roads. By 2 AM, 10 schools, a hospital, an urgent care and a police station are cut off from every open road. Tap a road to see why: which creek overtops it, at what flow, and how often it floods, so crews know where to barricade first."

**7. Proof and close (2:20–2:40) · Landing page cards or deck slide 4, then an end card: "Noah · Margulan Baizhakyp · with Priyanshu Sethi (iPad app, routing, live checks) · Hacklanta 2026".**
"Does it work? In Helene, NOAA's forecast gave 13.2 hours of warning before Peachtree Creek reached flood stage, and Noah flagged Windsor Parkway for 10 PM. The city closed it at about 10:15. This weekend, live, Friday night's run called Saturday's peaks on three creeks within 12 percent, 11 to 13 hours ahead. One creek was under-forecast, and we show that too. Noah: know before the water does."

**Recording rules**
- Never on screen: Windy camera photos (crop to the checklist or blur them), the terminal, `.env` or keys, other people's names or numbers in Messages.
- Say "recorded" for Helene. Never say safe, clear or passable.
- Overnight, don't ask "drive home at 6 PM" live: there is no saved home, and the model's evening-time math is off before dawn. Use Saturday's real alert plus the camera question.
- iPad: Control Center → Screen Recording, open Noah from the home-screen icon (hotspot on). iPhone: Do Not Disturb on. Laptop: QuickTime → File → New Screen Recording.
