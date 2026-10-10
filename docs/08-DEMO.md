# 08 — Demo Playbook (final, Sunday judging)

_Locked Sat Oct 10, 15:30 ET (J22, J23). **Margulan presents alone** with three devices: his laptop (Noah Operations), his iPhone (iMessage Noah), Priyanshu's iPad (Noah for iPad). Say only numbers in the fact sheet below._

## The one story
**Noah tells you which roads will flood, and when, before the water gets there, street by street, by text.**
Tagline: *Know before the water does.*

Two storms, one honest frame:
- **Hurricane Helene (Sep 26, 2024), recorded:** the day you live through on the iPad and the laptop. It's the run that plays out like a real day (roads open in the morning, cut by evening) and it's validated. **Say "recorded" out loud**; the screens say it too.
- **Hurricane Isaias (this weekend), live:** proof that Noah runs for real. It forecast the creek peaks 11–13 h ahead and texted unprompted on Saturday.

## Before judging (T-30 min)
| # | Step | Command / action |
|---|---|---|
| 1 | Laptop on the charger. Free memory: stop the camera monitor and closures logger tabs (keep the live loop, route watch and relay). | Ctrl-C in those two tabs |
| 2 | Demo server on Helene (iPad + console + demo chat answers) | `caffeinate -i scripts/demo_mode.sh` → `:8100` |
| 3 | iMessage answers from the same storm: restart the relay against the demo server | `cd bot && API_BASE=http://localhost:8100 npm start` |
| 4 | Tunnel for the iPad, then reopen the home-screen icon (re-add it if the address changed) | `ssh -R 80:localhost:8100 nokey@localhost.run` → `https://….lhr.life/ipad/` |
| 5 | Laptop tabs open: `localhost:8100/dispatch.html?cycle=20240926T12Z` (City), slides | — |
| 6 | Phone: Noah thread open, scrolled to Saturday's alerts (don't delete them); "alerts on" already set | — |
| 7 | Check the iPad works on **cellular** (venue Wi-Fi isolates devices) | — |

Fallbacks: tunnel down → show `localhost:8100/ipad/` on the laptop. Wi-Fi down → phone hotspot. Bot slow → read the reply already in the thread. Anything else → backup video.

## 1. Social Good (main track): 3 min pitch + 2 min Q&A
They score: people and places that get overlooked (access, safety, mobility), polish, presentation, use case. Track sponsor: **Cox Automotive** (cars: more than half of flood drownings happen in a vehicle).

| Time | Beat | Device | Say / do |
|---|---|---|---|
| 0:00–0:20 | Hook | Slide | "This weekend Hurricane Isaias hit Atlanta. Peachtree Creek went from 19 to 3,750 cubic feet per second overnight. More than half of flood drownings happen in a car, and some people can't stay home." |
| 0:20–0:35 | The gap | Slide | "Warnings cover whole counties. Map apps react after a road is reported closed. And NOAA's road data covers major roads only, not the side streets where people live." |
| 0:35–1:30 | **A day in a flood**, judge holds the iPad | iPad | "This is Hurricane Helene, recorded, so you can live a whole day of it. It's 9 AM." Tap **Work**, slide *Leaving* to 7 PM: "Route around 12 flooded roads… and your own street floods by then: stop at the corner." Tap **Home**: "Leave by 7:55 PM." Tap **Deliveries**: "Maya delivers for a pharmacy: leave by 7:30 PM to reach all 6 stops, and a better order saves 7 minutes." |
| 1:30–1:55 | **Noah texts first** | Phone | "This weekend Noah ran live. Saturday morning, nobody asked, it texted me:" read one real alert (e.g. *"Chamblee: … forecast cut by flooding from ~Sat 8 AM at Bradford Square NE (new)"*). "No app. A text works on any phone, and iMessage even goes via satellite when towers are down." |
| 1:55–2:30 | **For cities and businesses** | Laptop | City tab: "Same storm, for a city: by 2 AM, 10 schools, a hospital, an urgent care and a police station are cut off from every open road." Tap a red road: "Why? The creek overtops it, and it floods in every storm we recorded: fix it first." One **Site check** click: "And where a business should open its next branch." |
| 2:30–3:00 | **Proof + close** | Slide | "Helene: NOAA's 8 AM forecast gave 13.2 hours of warning before Peachtree Creek hit flood stage; Noah said Windsor Parkway would flood at 10 PM, the city closed it at 10:15. Isaias, live this weekend: Noah's Friday-night forecast called Saturday's peaks on Peachtree Creek, the Chattahoochee and Nancy Creek within about 10%, 11 to 13 hours ahead. Noah. Know before the water does." |

**Q&A**
- *Is this happening now?* "The iPad and console replay Hurricane Helene, recorded, so you see a full day. The live part is Isaias: Noah ran all weekend and texted alerts; the camera frames are today's."
- *How accurate?* Helene: 13.2 h warning, Windsor Pkwy 10 PM vs ~10:15 PM. Isaias: Peachtree −12%, Chattahoochee −8%, Nancy +9%, 11–13 h ahead; one creek (South Fork Peachtree) was under-forecast. Residential thresholds match NOAA's where both exist (no bias, correlation 0.74).
- *Isn't this NOAA's flood map?* NOAA maps where water can reach and has thresholds for major roads. Noah adds **when** for every road (62,202 residential segments NOAA skips), routes around them, and delivers it by text.
- *Storm drains?* Not in public data for Atlanta: Noah models creek and river overflow and says so on screen.
- *Cameras?* They watch flagged roads, but camera AI gave two false alarms Saturday, so a frame counts only when water shows in 2+ checks and a person confirms. Only 4 of 49 flagged streets had a camera nearby: cameras can't see where floods start, which is why we forecast.
- *What if it's wrong?* Conservative: uncertain = impassable, never says "safe", every answer says "not a safety guarantee", 911 when there's danger.
- *Scale?* 4 metro watersheds now (1,426 km²); the same pipeline runs basin by basin; NOAA's model covers the whole US.
- *Privacy?* No accounts; the relay logs a hashed sender, length and timing only.

## 2. Photon (Agents in iMessage, Spectrum): about 2 min
1. Hand the judge the "Text Noah" card; they text from **their own phone**: *"Can I drive home from Midtown at 6 PM?"* → typing dots → a plain answer with the street and the time.
2. *"alerts on"* → Noah confirms and sends the current status.
3. Re-send Saturday's latest real alert to their thread, labeled "Re-sent from Sat …": `uv run python -m noah.pipeline.route_watch --resend` → their phone buzzes. (Text only: Saturday's two camera alerts were false alarms, so they are never re-sent.)
4. Guardrail: *"Is it safe to drive on Collier Road?"* → never "safe": the forecast, "never drive into water", 911.
5. One slide: iPhone → Spectrum Cloud iMessage line → `spectrum-ts` relay (typing indicator, photos via `attachment()`, proactive sends via `space.send`) → Noah agent (Azure OpenAI tool calling) → NOAA forecast + live sources. Never silent: on failure it sends the safety message.

## Fact sheet (say only these)
| Fact | Source |
|---|---|
| More than half of flood drownings involve a vehicle | CDC figure used by NWS "Turn Around Don't Drown" |
| Peachtree Creek 19 → 3,750 cfs, Fri 6 PM → Sat 10:45 AM | USGS 02336300 |
| Isaias, run Fri 10 PM (Noah had it 11:50 PM): Peachtree −12% (10.9 h ahead), Chattahoochee −8% (13.2 h), Nancy +9% (10.7 h); South Fork Peachtree missed (−78%) | `web/data/isaias_validation.json` |
| Helene: NOAA's 8 AM run, 13.2 h before Peachtree Creek's flood stage (9:15 PM) | USGS + `web/data/validation.json` |
| Windsor Pkwy: Noah 10 PM, closed ~10:15 PM | Helene 8 AM run; Appen Media / 11Alive |
| Helene 8 AM run: 2,423 road segments flagged by 2 AM; 10 schools, a hospital, an urgent care, a police station cut off (8 PM–2 AM); 21 more with a flooded road at the door (5 fire stations) | `/ops/city?cycle=20240926T12Z` |
| Saturday: 9 of 11 watched routes warned ahead by the run Noah had at 11:50 PM Friday | `web/data/route_watch.json` |
| NOAA road thresholds 15,289 segments; Noah's own 62,202 residential | `seg_thresholds.parquet` |
| Helene: Atlanta's first-ever Flash Flood Emergency; 25 rescued along Peachtree Creek | Fox Weather; Atlanta News First (Sep 27, 2024) |
| Cox Automotive's chief economist: 300k–500k vehicles damaged in Houston by Harvey; CARFAX: ~138,000 flood-damaged by Helene (16,800 in Georgia) | Cox Automotive; Auto Remarketing (CARFAX) |

## Not in the demo
Replit (pinned), Tiger Data (not built), the sensor node / flood simulator / satellite build (pinned for after Hacklanta).

## Credits (Devpost, J23)
Noah is Margulan's entry. Priyanshu Sethi built, during Hacklanta, the web map, the trip planner and routing API, the live-checks engine and the iPad app, and competes separately in Fintech.
