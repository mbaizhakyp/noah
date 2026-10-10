# 01 — Project Overview

## One line
**Noah: Waze for floods that warns you before the road goes under, not after.**

## Problem
- Driving into floodwater is a leading cause of US flood deaths.
- Official warnings are county-wide, not street-level.
- Map apps react only after someone reports a closure.
- Small ungauged creeks get the least warning.
- Flooding hits Georgia roads in ordinary storms, not only hurricanes: urban creeks rise within hours of heavy rain.

## What Noah does
1. **Forecasts road flooding.** For every drivable road segment in the coverage area: will it flood in the next 18 h, and from roughly which hour.
2. **Routes around it.** Shortest path with flooded and uncertain segments removed.
3. **Answers by text.** An AI agent (Azure OpenAI `gpt-4.1-mini`) in iMessage (via Photon Spectrum) handles "can I get home tonight?", "is Northside Dr flooding?" and "route me from X to Y".
4. **Shows it.** A web map with a time slider where roads turn amber, then red, as the forecast hours pass.

## Who it's for
People anywhere in Georgia who have to drive during a flood event, especially along small creeks and rivers. These areas get county-wide warnings and no street-level detail. Delivery by text means no app install is needed.

## Coverage: all of Georgia (Priyanshu, Fri Oct 9 ~22:30 ET; replaces the Peachtree-only MVP, Margulan to confirm via CC6)
Noah covers **every road in Georgia's 159 counties** in two layers:
1. **Statewide hazard layer (all of Georgia from day 1).** NWS flood and flash-flood warnings, MRMS flash-flood nowcasts, NWPS river forecasts and flood categories, the NWM per-reach forecast, crowd/NWS storm reports, traffic cameras (Windy, 2,467 in Georgia), live TomTom incidents (closures, flooding category) and Synoptic rain gauges (289 GA stations). 511GA was dropped (not doable). See `07-DATA_SOURCES.md`.
2. **Road-level flood timing (NWM + HAND), rolled out one HUC8 at a time.** HAND data is public and free (CIROH bucket, about 250 MB per HUC8; 53 HUC8s touch Georgia). Order:
   1. `03130001` Upper Chattahoochee (metro Atlanta, already downloading).
   2. The HUC8s covering the Yellow and South rivers (east metro, action stage forecast).
   3. Southwest Georgia basins (frequent river flooding).
   4. The rest of Georgia.
- Peachtree Creek (HUC10 `0313000112`) is no longer the coverage limit.
- Inside Georgia but in a HUC8 not processed yet: Noah still gives the statewide hazards and official warnings, and says plainly that road-level timing isn't available there yet (proposed state `no_road_forecast`, CC6).

## What Noah is not (state these to judges)
- Not a flood *mapping* product. NOAA already publishes inundation maps. Our contribution is road-level timing, predictive routing, and delivery by text.
- Road-level *timing* covers river and creek flooding only. **It does not forecast storm-drain or flash street flooding.** For those, Noah passes on official NWS flash-flood warnings and MRMS nowcasts and doesn't model them itself.
- **Never says a road is safe.** Outputs stay conservative (see `02-ARCHITECTURE.md` §5).
- Not a replacement for official warnings or 911.

## Expanded vision (PROPOSED Oct 9, 2026, not yet agreed by both)
> Status: **proposal**. Nothing below overrides the locked decisions further down until both Margulan and Priyanshu agree. Once they do, update the "Locked decisions" table and "What Noah is not". Then write specs for the pieces we commit to. Anything not committed for the hackathon goes to the parking lot in `06-CURRENT_ISSUES.md`.

**Scope: all of Georgia (Priyanshu, Oct 9).** Coverage is the whole state, not the US and not only Peachtree Creek. See §Coverage.

**Guiding rule: the right data is the most important part.** Each layer below ships only if we have a real, citable source for it. If the source doesn't exist or we can't get it in time, the layer doesn't ship. We never fill gaps with made-up data (see `04-AI_WORKFLOW_RULES.md` rule 7).

### Broader scope: road hazards in rain
Noah grows from creek flooding into a wider road-hazard layer for rain events:
1. **Road flooding forecast.** NWM + HAND for **all of Georgia** (now in scope; see §Coverage).
2. **Potholes.**
   - Show known pothole reports.
   - Let users submit new reports (location only; no photos, see below).
   - Detect potholes from online imagery (street-level imagery, public cameras). **No user photos:** we can't expect people to take photos in the rain (Priyanshu, Oct 9).
3. **Sewage overflow prediction.** Forecast combined/sanitary sewer overflows caused by heavy rain.
4. **Satellite flood detection.** Use satellite imagery to confirm flooding on or near streets.
5. **Public CCTV / traffic cameras.** Live or recent street images to check for flooding (and potholes).

### Three user types
| User | What they get |
|---|---|
| **Individual** | "Waze for floods and rain." Save routes and destinations. Use Noah through the website or iMessage. See a **time-based route** that changes with the forecast hour. The route shows on our dashboard, with a one-tap link to start driving in **Google Maps** or **Apple Maps**. |
| **Business** | Fleet and logistics tracking: see delivery vehicles' routes against current and forecast hazards. An always-on logistics view with warnings when a planned or active route hits a hazard. |
| **County / city** | Dashboards and stats: forecast flooded road miles, hazard counts by area, pothole reports, sewer overflow risk, and trends over time. |

### Candidate data sources (ALL UNVERIFIED: check access, coverage, license and freshness before any spec relies on them)
| Layer | Candidates to check | Known concerns |
|---|---|---|
| Flood forecast, Georgia-wide | NOAA National Water Model (CONUS), NOAA OWP FIM / HAND (per-HUC8 downloads), USGS gauges, NWS alerts (`api.weather.gov`) | Going statewide means more HAND data (one download per HUC8 that covers Georgia, requester-pays bucket, see B2). Probably needs per-region processing, not all of Georgia in memory at once. |
| Rainfall | NOAA MRMS radar precip, NWS forecasts | Needed for the pothole and sewer layers, which follow rain rather than creeks. |
| Satellite flooding | Sentinel-1 SAR (free, Copernicus), NASA OPERA surface-water products, Landsat/Sentinel-2 optical | Resolution is roughly 10–30 m and revisits are every few days, so it mostly confirms past flooding at area level rather than single streets in real time. Clouds block optical. |
| Traffic / CCTV cameras | Windy Webcams (verified: 2,467 in Georgia). ~~GDOT 511GA~~ dropped (key under manual review) | Terms of use vary by state. Many forbid scraping or redistribution. Need a flood/pothole image classifier. |
| Known potholes | City 311 / Open311 open-data portals (many cities publish pothole requests), SeeClickFix | No national dataset; patchy city by city. |
| Pothole detection | Street-level imagery (e.g., Mapillary), traffic-camera frames + a vision model (Azure OpenAI) | Detection accuracy needs to be shown, not claimed. |
| Sewage overflow | EPA data on combined sewer systems, utility/state overflow notification feeds, rainfall thresholds | Real-time public overflow data exists only for some utilities. "Prediction" will likely start as a rain-threshold heuristic, and we have to label it that way. |
| Routing, Georgia-wide | OpenStreetMap + a routing engine (OSRM / Valhalla / GraphHopper) | Our current plan loads one watershed graph into memory (D7). That won't scale to the whole state. |
| Hand-off to navigation | Google Maps and Apple Maps URL links with waypoints | We need to check how many detour waypoints each one accepts. The external app may re-route through a flooded road; say this to users. |

### What this changes (decisions to revisit together)
- **D4 Coverage**: Peachtree Creek → all of Georgia (**changed**, see §Coverage).
- **D7 Data store**: no database → saved routes, user/business/county accounts, pothole submissions and fleet tracking need a database.
- **D8 Hosting**: a laptop + tunnel may not be enough for business/county users.
- **"What Noah is not"**: drop "does not cover storm-drain or flash street flooding" only if the sewer/rain layers actually ship. Otherwise keep it.
- **Wording (D6)**: pothole, sewer and camera layers need their own frozen states in `02-ARCHITECTURE.md` §5. The rule "never say a road is safe" still applies.

### Hackathon reality check
About 36 hours remain before the 7:00 AM Sunday internal deadline. Proposed split:
- **Ship for judging:** the current MVP (forecast → route → iMessage → map) plus pieces that reuse it cheaply. Candidates: saved routes + Google/Apple Maps links for individuals, a county stats view built on the same flood data, and 311 pothole reports for one city that publishes them.
- **Pitch as roadmap:** fleet tracking, CCTV/satellite detection, sewer overflow prediction, unless real data for one of them turns out to be quick to get.

## Hackathon frame
- **Event:** Hacklanta 2026, GSU Atlanta. Hacking runs Fri Oct 9, 8:30 PM to **Sun Oct 11, 9:00 AM ET (hard)**.
- **Main track:** Social Good (Cox). The prompt, "people and places that get overlooked: access, safety, mobility", maps to safety (flood deaths), mobility (routing), and overlooked places (ungauged small creeks).
- **Side challenges (CHANGED Sat Oct 10, Priyanshu; Margulan to confirm, J11):** **MLH Best Use of Tiger Data (main side challenge)**, Photon: Agents in iMessage (Spectrum SDK), Replit: Small Business. MLH Gemini dropped: the AI runs on Azure OpenAI.
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
| D2 | Track + side challenges | **CHANGED (Priyanshu, Sat Oct 10 ~01:50 ET; Margulan to confirm, J11):** main track **Social Good**. Side challenges (max 3): **MLH Tiger Data (main) + Photon iMessage + Replit Small Business.** Gemini dropped (AI = Azure OpenAI `gpt-4.1-mini`). Tiger Data replaces Gemini in the max-3. |
| D3 | Name / domain | Noah; no domain purchase |
| D4 | Coverage | **DECIDED (Margulan, Fri Oct 9 23:25; CC6 narrowed).** Road-level flood timing (NWM + HAND) covers **HUC8 03130001, Upper Chattahoochee** (metro Atlanta, incl. Big Creek at Alpharetta). Elsewhere in Georgia: `no_road_forecast` + official warnings (statewide warning layer = Priyanshu, after the Sat 14:00 E2E). All of Georgia, basin by basin, is the roadmap (13 GB of HAND + a statewide graph won't fit this weekend). Checks only within 5 km of the user / 1 km of a searched route (CC6 #2). |
| D5 | Forecast clock + demo event | **DECIDED (Margulan + Priyanshu, Sat Oct 10 ~00:45 ET; J10).** Noah is an everyday **live** app: "now" = the newest live NWM cycle (C6 `event: "live"`), refreshed hourly by the live loop (spec 015). **Demo event = Hurricane Isaias, Saturday Oct 10**, shown on Sunday as **the storm unfolding run by run from Friday evening** (first live run: Fri 6 PM, nothing forecast → Fri 10 PM, ~100 roads flagged for Sat morning → Saturday's runs), "and here's what happened" (pin a Saturday cycle with `?cycle=`). **Helene stays as backup only:** offline evidence for Devpost and Q&A (13.2 h lead, Windsor Pkwy 10 PM vs 10:15 PM closure), and the fallback demo if Isaias doesn't flood metro roads. Final call on the demo event: **Sat 14:00**. |
| D6 | Output wording | Four frozen states: **Do not cross / Uncertain: treat as impassable / No forecast flooding (not a safety guarantee) / Outside coverage** (now = outside Georgia; CC6 proposes adding **No road-level forecast here yet**). Exact text in `02-ARCHITECTURE.md` §5. |
| D7 | Data store | **CHANGING with J11:** routing still runs from files held in memory (fast, no DB in the request path). **Tiger Data (hosted time-series Postgres)** stores the time series: every live forecast run per road segment, the present-conditions observations (rain, gauges, incidents, warnings, camera checks), and the history behind county dashboards and trends. ~~No database.~~ |
| D10 | Forecast vs real-time | **Forecast first (Margulan, Oct 9).** The product predicts which roads flood in the next 18 h. "Now" is hour 0 of the same map, from NWM's current-conditions analysis: same pipeline, one extra file per cycle. Observed real-time data (gauge, team photos, cameras) is a **confirmation layer**, never the core. Runs on the newest live cycle every hour (D5, Sat 01:30); no event replays in the product. |
| D8 | Hosting | Static map on GitHub Pages (`/web`). API + iMessage relay run on a laptop, exposed with a `cloudflared` quick tunnel during judging. |

## Demo script (target, 3 min): live, any day
1. **Hook (20 s).** Map apps tell you a road is flooded after someone reports it. Noah tells you hours before, for your street and your drive, every day.
2. **Present (40 s).** Open Noah, tap **Use my location** (or type a Georgia address) → **Check my area**: what's happening within 5 km *right now* (forecast hour 0, live NWS warnings, rain, closures, cameras near you).
3. **Future (40 s).** Drag the time bar or press Play: roads within 5 km turn amber, then red, across the next 18 hours from the latest NOAA forecast. Show the days-ahead outlook for the area.
4. **Route (40 s).** Search a destination → Noah's route around forecast-flooded roads, the hazards along it, then **Start in Google Maps / Apple Maps**.
5. **Text (20 s).** Same answer by text: "can I get to work at 8?" → plain-language reply + map link.
6. **How + limits (20 s).** NOAA forecast → road thresholds → routing, plus live statewide feeds. Road timing = creek/river flooding in metro Atlanta for now. Never says a road is safe.
