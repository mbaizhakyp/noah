# 08 — Demo Playbook (final, Sunday judging)

_Locked Sat Oct 10, 15:30 ET (J22, J23); **J28 (Sat 18:15): the whole demo runs on the iPad** — one app, four tabs (People, City, Deliveries, Site check), served by the laptop over your iPhone's hotspot. The laptop is the server (and shows the slides); the phone shows Saturday's real alert thread for one beat. Margulan presents alone. Say only numbers in the fact sheet below._

## The one story
**Noah tells you which roads will flood, and when, before the water gets there, street by street, by text.**
Tagline: *Know before the water does.*

Two storms, one honest frame:
- **Hurricane Helene (Sep 26, 2024), recorded:** the day you live through on the iPad's **People** and **City** tabs. It's the run that plays out like a real day (roads open in the morning, cut by evening) and it's validated. **Say "recorded" out loud**; the screens say it too.
- **Hurricane Isaias (this weekend), live:** proof that Noah runs for real: the phone's alert thread and the iPad's **Deliveries** tab (Saturday 4 AM forecast). It forecast the creek peaks 11–13 h ahead and texted unprompted on Saturday.
- **Each console tab offers only its storm's forecasts** (J24): City = Helene runs (opens on Thu 8 AM), Deliveries = Isaias runs (opens on Sat 4 AM), Site check = every recorded storm.

## Before judging (T-30 min)
| # | Step | Command / action |
|---|---|---|
| 1 | Laptop on the charger. Free memory: stop the camera monitor and closures logger tabs (keep the live loop, route watch and relay). | Ctrl-C in those two tabs |
| 2 | Demo server on Helene (iPad + console + demo chat answers) | `caffeinate -i scripts/demo_mode.sh` → `:8100` |
| 3 | iMessage answers from the same storm: restart the relay against the demo server | `cd bot && API_BASE=http://localhost:8100 npm start` |
| 4 | **iPad over your iPhone's hotspot (no tunnel):** turn on Personal Hotspot; join it from the laptop **and** the iPad; on the iPad open `http://Margulans-MacBook-Air.local:8100/ipad/` → Add to Home Screen (the name never changes, so the icon keeps working). Backup: the localhost.run tunnel (its address rotates on its own every so often; current one: `grep -o 'https://[a-z0-9]*\.lhr\.life' data/interim/tunnel.log \| tail -1`). Cloudflare's tunnel is blocked on the venue network. | `scripts/demo_mode.sh` listens on all interfaces |
| 5 | iPad: open the home-screen icon (`http://Margulans-MacBook-Air.local:8100/` → opens on **People**); tap **City**, then **Deliveries**, then back to **People** so every tab is loaded (switches are then instant). Laptop: slides only | — |
| 6 | Phone: Noah thread open, scrolled to Saturday's alerts (don't delete them); "alerts on" already set | — |
| 7 | Check the iPad works on **cellular** (venue Wi-Fi isolates devices) | — |
| 8 | "Text Noah" card printed and its QR tested once with an iPhone camera (opens Messages to Noah with a question typed in) | `docs/text-noah-card.html` → print at 100% |

Fallbacks: hotspot address not loading → the tunnel address above, or show `localhost:8100/ipad/` on the laptop. Wi-Fi down → phone hotspot. Bot slow → read the reply already in the thread. Anything else → backup video.

## 1. Social Good (main track): 3 min pitch + 2 min Q&A
They score: people and places that get overlooked (access, safety, mobility), polish, presentation, use case. Track sponsor: **Cox Automotive** (cars: more than half of flood drownings happen in a vehicle).

| Time | Beat | Device | Say / do |
|---|---|---|---|
| 0:00–0:20 | Hook | Slide | "This weekend Hurricane Isaias hit Atlanta. Peachtree Creek went from 19 to 3,750 cubic feet per second overnight. More than half of flood drownings happen in a car, and some people can't stay home." |
| 0:20–0:35 | The gap | Slide | "Warnings cover whole counties. Map apps react after a road is reported closed. And NOAA's road data covers major roads only, not the side streets where people live." |
| 0:35–1:30 | **A day in a flood**, judge holds the iPad | iPad · **People** tab (Helene) | "This is Hurricane Helene, recorded, so you can live a whole day of it. It's 9 AM." Tap **Work**, slide *Leaving* to 7 PM: "Route around 12 flooded roads… and your own street floods by then: stop at the corner." Tap **Home**: "Leave by 7:55 PM." Tap **Deliveries**: "Maya delivers for a pharmacy: leave by 7:30 PM to reach all 6 stops, and a better order saves 7 minutes." |
| 1:30–1:50 | **Noah texts first** (Isaias, live) | Phone | "This weekend Noah ran live. At 6 AM Saturday, nobody asked, it texted me:" read the **5:59 AM** alert (Sat 4 AM forecast): *"Mechanicsville: North Shallowford Rd → Graves Rd: now cut from ~Sat 4 AM at Graves Rd … Habersham: I 85 Access Rd → Northcrest Way: now cut from ~Sat 1 PM at Northcrest Way"*. "No app. A text works on any phone, and iMessage even goes via satellite when towers are down." |
| 1:50–2:05 | **Same morning, for a business** | iPad · **Deliveries** tab (Isaias, Sat 4 AM) | "Same forecast, for a pharmacy with 8 stops: two were already cut at 4 AM, so hold them; Northcrest Way has to go before noon; the other five show no forecast flooding." |
| 2:05–2:30 | **For a city** | iPad · **City** tab (Helene) | "And for a city, back to Helene: by 2 AM, 10 schools, a hospital, an urgent care and a police station are cut off from every open road." Tap a red road (or the first *Fix first* card): "Why? The creek overtops it, and it floods in every storm we recorded: fix it first." (Site check and the vulnerable-neighborhoods line are Q&A material.) |
| 2:30–3:00 | **Proof + close** | Slide | "Helene: NOAA's 8 AM forecast gave 13.2 hours of warning before Peachtree Creek hit flood stage; Noah said Windsor Parkway would flood at 10 PM, the city closed it at 10:15. Isaias, live this weekend: Noah's Friday-night forecast called Saturday's peaks on Peachtree Creek, the Chattahoochee and Nancy Creek within about 10%, 11 to 13 hours ahead. Noah. Know before the water does." |

**Q&A**
- *Is this happening now?* "The iPad and console replay Hurricane Helene, recorded, so you see a full day. The live part is Isaias: Noah ran all weekend and texted alerts; the camera frames are today's."
- *How accurate?* Helene: 13.2 h warning, Windsor Pkwy 10 PM vs ~10:15 PM. Isaias: Peachtree −12%, Chattahoochee −8%, Nancy +9%, 11–13 h ahead; one creek (South Fork Peachtree) was under-forecast. Residential thresholds match NOAA's where both exist (no bias, correlation 0.74).
- *Isn't this NOAA's flood map?* NOAA maps where water can reach and has thresholds for major roads. Noah adds **when** for every road (62,202 residential segments NOAA skips), routes around them, and delivers it by text.
- *Storm drains?* Not in public data for Atlanta: Noah models creek and river overflow and says so on screen.
- *Cameras?* They watch flagged roads, but camera AI gave two false alarms Saturday, so a frame counts only when water shows in 2+ checks and a person confirms. Only 4 of 49 flagged streets had a camera nearby: cameras can't see where floods start, which is why we forecast.
- *Proof the forecast came first?* Friday 10 PM's forecast was saved to GitHub at 11:51 PM Friday (commit `eff4481`), 11 h before Peachtree Creek peaked.
- *Why does the iPad say "stop at the corner" and the console "Hold"?* Two views of the same rule: the console is the dispatcher's cautious view (don't send a driver to a stop whose street floods); the iPad shows the driver how close an open road gets them.
- *Who gets hit hardest?* Console City tab: on Helene, 16% of the road segments cut by 8 PM are in the most socially vulnerable quarter of US neighborhoods (CDC SVI), which hold 9% of all roads here; 59,739 people live in the ones affected. "Show vulnerable neighborhoods" draws them.
- *What if it's wrong?* Conservative: uncertain = impassable, never says "safe", every answer says "not a safety guarantee", 911 when there's danger.
- *Scale?* 4 metro watersheds now (1,426 km²); the same pipeline runs basin by basin; NOAA's model covers the whole US.
- *Privacy?* No accounts; the relay logs a hashed sender, length and timing only.

## 2. Photon (Agents in iMessage, Spectrum): about 2 min
1. Hand the judge the "Text Noah" card (+1 (646) 579-2868; the QR opens Messages to Noah with the first question typed in; iPhone/iMessage only). They text from **their own phone**: *"Can I drive home from Midtown at 6 PM?"* → typing dots → a plain answer with the street and the time.
2. *"alerts on"* → Noah confirms and sends the current status.
3. Re-send Saturday's latest real alert to their thread, labeled "Re-sent from Sat …": `uv run python -m noah.pipeline.route_watch --resend` → their phone buzzes. (Text only: Saturday's two camera alerts were false alarms, so they are never re-sent.)
4. **Live cameras (J32):** *"Give me CCTV images of a 5-mile radius from Georgia State University and evaluate risks."* → in ~10 s: an album of 6 live traffic-camera photos spread across the area, each AI-checked for water, a numbered key, and a **risk checklist** (J33): 🟩/🟨/🟥 photos · official warnings · rain and water levels · public flood reports, then a one-line bottom line (never "safe"; ends with "not a safety guarantee").
5. Guardrail: *"Is it safe to drive on Collier Road?"* → never "safe": the forecast, "never drive into water", 911.
6. One slide: iPhone → Spectrum Cloud iMessage line → `spectrum-ts` relay (typing indicator, photos via `attachment()`, proactive sends via `space.send`) → Noah agent (Azure OpenAI tool calling) → NOAA forecast + live sources. Never silent: on failure it sends the safety message.

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
| Isaias street level: **no street-level confirmation.** TomTom logged 0 flood-related closures in our area Sat 12:33 AM–11:49 PM; 83 new closures gave no cause (1 within 150 m of a flagged road, on a different street). Don't claim a confirmed street. | `data/interim/incidents/` (TomTom, 82 snapshots) |
| Friday 10 PM forecast saved to GitHub 11:51 PM Fri (commit `eff4481`); Peachtree Creek peaked 10:45 AM Sat | git log; `isaias_validation.json` |
| Helene 8 AM run: 16% of segments cut by 8 PM (11% by 2 AM) are in high-vulnerability tracts (CDC SVI ≥ 0.75), vs 9% of all roads; 59,739 people in affected high-SVI tracts by 8 PM, 88,467 by 2 AM | `/ops/city?cycle=20240926T12Z` → `vulnerability` |
| NOAA road thresholds 15,289 segments; Noah's own 62,202 residential | `seg_thresholds.parquet` |
| Helene: Atlanta's first-ever Flash Flood Emergency; 25 rescued along Peachtree Creek | Fox Weather; Atlanta News First (Sep 27, 2024) |
| Cox Automotive's chief economist: 300k–500k vehicles damaged in Houston by Harvey; CARFAX: ~138,000 flood-damaged by Helene (16,800 in Georgia) | Cox Automotive; Auto Remarketing (CARFAX) |

## Not in the demo
Replit (pinned), Tiger Data (not built), the sensor node / flood simulator / satellite build (pinned for after Hacklanta).

## Credits (Devpost, J23)
Noah is Margulan's entry. Priyanshu Sethi built, during Hacklanta, the web map, the trip planner and routing API, the live-checks engine and the iPad app, and competes separately in Fintech.
