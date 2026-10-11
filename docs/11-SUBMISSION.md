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

## Demo video (2:45, record by 04:00)
One person, one forecast, three scales: Maya (a driver) → her pharmacy → her city. Live Isaias opens and frames it; recorded Helene shows a full storm day. Voiceover ≈ 410 words, ~150 per minute.

**1 · Cold open (0:00–0:12)**
Screen: iPhone, Noah thread: the real 5:59 AM Saturday alert slides in; zoom on the two streets and times.
VO: "Saturday, 5:59 AM. Hurricane Isaias is soaking Atlanta. Nobody asked, but Noah texts first: Graves Road is cut from about 4 AM. Northcrest Way, from about 1 PM."

**2 · The gap (0:12–0:36)**
Screen: landing page storm hero (rain, waves, "Noah" breaking through the clouds); stats appear as on-screen text.
VO: "Overnight, Peachtree Creek rose from 19 to 3,750 cubic feet per second. More than half of flood drownings happen in a vehicle. But warnings cover whole counties, map apps reroute only after a road is closed, and NOAA's flood thresholds skip the side streets where people live. Noah tells you which streets will flood, and when, up to 18 hours ahead."

**3 · Maya's day (0:36–1:14)** · lower third: *Recorded: Hurricane Helene, Sep 26, 2024*
Screen: iPad, People tab at 9 AM (roads open). Work → drag Leaving to 7 PM (route bends around red roads). Home → "Leave by 7:55 PM". Deliveries → "Leave by 7:30 PM" and the better-order pop-up.
VO: "Meet Maya. She delivers for a neighborhood pharmacy, so she can't stay home in a storm. To show a full storm day, we replay Hurricane Helene, recorded. It's 9 AM and her roads are open. Driving to work at 7 PM? Noah routes her around 12 flooded roads, and warns that the street she's heading to floods by then: stop at the nearest open corner. Getting home: leave by 7:55 PM. Her six deliveries: leave by 7:30 PM to reach every stop, and a better order saves 7 minutes."

**4 · No app needed (1:14–1:42)**
Screen: iPhone Messages. Type "alerts on" → Noah confirms. Then "Check the traffic cameras around Georgia State and evaluate the risks" → typing dots → photo album (**blurred**) → the 4-line checklist and bottom line.
VO: "She doesn't even need the app. Text 'alerts on', and Noah texts first when a road she uses is about to flood, like that 5:59 AM message. Ask for the cameras near Georgia State, and in seconds Noah sends six live traffic-camera photos, each AI-checked for water, plus a four-point checklist: the photos, official warnings, rain and creek levels, and public flood reports. It never says 'safe'."

**5 · Her pharmacy (1:42–1:58)** · lower third: *Live: Hurricane Isaias, Sat Oct 10, 4 AM forecast*
Screen: iPad, Deliveries tab: two stops held, Northcrest Way flagged before noon.
VO: "Same forecast for Maya's pharmacy, live this weekend at 4 AM Saturday: of 8 stops, two are already cut, so hold them. Northcrest Way has to go before noon. The other five show no forecast flooding."

**6 · Her city (1:58–2:20)** · lower third: *Recorded: Hurricane Helene*
Screen: iPad, City tab: drag the time bar to 2 AM (facilities turn red); tap a red road → the Why card.
VO: "And for her city, back to Helene. By 2 AM, 10 schools, a hospital, an urgent care and a police station are cut off from every open road. Tap any red road to see why: which creek overtops it, when to barricade, and whether it floods every storm, so the city knows what to fix first."

**7 · Proof and close (2:20–2:45)**
Screen: proof slide (three numbers), then the landing hero as the end card: "Noah · Know before the water does".
VO: "Does it work? In Helene, NOAA's forecast gave 13.2 hours of warning before Peachtree Creek hit flood stage, and Noah flagged Windsor Parkway for 10 PM; the city closed it at about 10:15. This weekend, live, Friday night's forecast called Saturday's creek peaks within about 10%, 11 to 13 hours ahead, and Noah warned 9 of 11 watched routes ahead of time. Noah. Know before the water does."

**Recording rules**
- Record each screen on its own (iPad and iPhone screen recording, QuickTime on the laptop), then cut in order and lay the voiceover over it.
- Label every storm on screen: "Recorded: Helene" or "Live: Isaias". Say "recorded" for Helene.
- **Blur the camera photos** in scene 4: Windy frames can't be published. The checklist text is fine.
- Show no API keys, `.env` or terminals.
- iPad: demo server on Helene (`scripts/demo_mode.sh`); Deliveries opens on Isaias by itself. iMessage answers come from today's live forecast, so the checklist may be calm; that's fine and honest.
