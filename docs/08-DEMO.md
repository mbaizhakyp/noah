# 08 — Demo Playbook (Sunday judging)

_Written Sat Oct 10, 02:40 ET. Assumes Saturday's plan is done (see "Must be true by Sunday"). Numbers in **[brackets]** get filled from the Saturday-night / Sunday-early validation (BL-18/19); never say a number we didn't produce._

## The one story (every judge hears the same spine)
**Noah tells you which roads will flood, and when, before the water gets there, by text, street by street.**
Tagline: *Know before the water does.*

Three pillars, in this order:
1. **It predicts.** NOAA's National Water Model forecasts every creek 18 h ahead, hourly. Noah turns that into a flood time for every road, using NOAA's thresholds for major roads and its own calculation for the **62,202 residential road segments NOAA's road data leaves out** (4× NOAA's 15,289).
2. **It's proven.** Helene backtest: NOAA's 8 AM forecast gave **13.2 h** of warning before Peachtree Creek hit flood stage; Noah had Windsor Pkwy flooding at **10 PM**, and Sandy Springs closed it at **~10:15 PM**. Isaias, live this weekend: **[N] of [M]** flood closures were roads Noah had flagged, **~[X] h** ahead.
3. **It reaches people where they are.** A text message (iMessage, no app), a dispatch board for small businesses, a barricade list for cities.

**Social Good hero (J18, Sat 03:50): Maya, a delivery driver** (an overlooked worker who can't stay home in a storm; residents covered in passing). City story pinned.

Personas below are **examples** (not real people): Jordan, a nurse who works at Emory and lives near Peachtree Creek; Peachtree Corner Pharmacy (sample business); a city public-works crew lead.

## What we demo on Sunday (assets)
| Asset | What it shows | Status needed |
|---|---|---|
| **iMessage Noah** on a real iPhone (mirrored to the laptop) | Ask in plain English; get the street, the time, a detour, a map link | Live (008 + 007 done Sat 02:23) |
| **Live map** (Priyanshu's `web/index.html`) | Departure-time picker, roads turning red by forecast hour, route around them, camera snapshots, risk score | Public URL via Replit (BL-9) |
| **Isaias, run by run** | Fri 6 PM forecast: 77 roads flagged → Fri 10 PM: 313 → Saturday morning runs [..] | Live loop running; 8 AM run committed (BL-16) |
| **Validation** | Isaias closures vs Noah's flags [N/M, ~X h]; Helene 13.2 h + Windsor Pkwy + 5 Buckhead streets | BL-18/19 |
| **Camera evidence card** (if captured) | Real traffic-camera frame with water next to a road Noah turned red, AI-checked twice | Camera monitor running (BL-22) |
| **Dispatch board + barricade list** (Replit) | Pharmacy deliveries: go before / hold / no forecast flooding; CSV for city crews | Deployed on Replit (BL-9) |
| **Tiger Data** (if built) | Every hourly forecast stored as time series; "how the forecast evolved" query | J11: after E2E |
| **Backup video** (2–3 min) | Everything above, recorded | Sun 04:00 |

**Which storm leads (J13, Sat 14:00):** Variant A = Isaias leads, Helene is the backtest line. Variant B (Isaias didn't flood metro roads) = Helene leads the proof; Isaias = "Noah ran live all weekend and correctly showed limited flooding" only if the gauges agree.

---

## 1. Social Good (main track) — 3 min pitch + 2 min Q&A
**They score:** fit with "people and places that get overlooked: access, safety, mobility" · polish · presentation · compelling use case.
**Angle:** safety + overlooked places (residential streets, small creeks, people without apps).

| Time | Beat | What's on screen | Say (key lines) |
|---|---|---|---|
| 0:00–0:20 | Hook | Title + one photo-free fact card | "More than half of flood drownings happen in a car. Two years ago Helene put Atlanta under its first-ever Flash Flood Emergency; firefighters rescued 25 people along Peachtree Creek. Yesterday, Hurricane Isaias hit Georgia." |
| 0:20–0:40 | The gap | Map: county-wide warning vs streets | "Warnings are county-wide. Map apps react after a road is reported closed. And NOAA's road-level data covers major roads only; the residential streets where people actually live are left out." |
| 0:40–1:50 | **Live demo: Jordan's commute** | iPhone (mirrored) → map | Text Noah: *"Can I drive home from work at 6 PM?"* (home/work saved earlier) → Noah: the street, the time, the detour, map link → tap → map at 6 PM: roads near creeks red, route around them, a camera snapshot nearby. "Noah never says a road is safe; it says when it floods and what to avoid." |
| 1:50–2:35 | **Proof** | Validation card (+ evidence card) | Variant A: "Saturday at 8 AM Noah flagged [N] roads. Of the [M] roads reported closed by flooding later that day, Noah had flagged [K], about [X] hours ahead." Helene: "13.2 hours of warning; Windsor Parkway: Noah said 10 PM, the city closed it at 10:15." |
| 2:35–2:55 | Who it serves | Three icons: resident / business / city | "No app; a text works for anyone. Free for residents. It covers the neighborhoods official data skips. Dispatch boards for small businesses and barricade lists for cities pay for it." |
| 2:55–3:00 | Close | Tagline | "Noah. Know before the water does." |

**Q&A answers (2 min)**
- *How accurate?* Gauge level: 13.2 h warning on Helene; street level: Windsor Pkwy 10 PM vs 10:15 PM closure; Isaias: [N/M]. Residential thresholds match NOAA's where both exist (no bias, correlation 0.74).
- *Isn't this just NOAA's flood map?* NOAA maps where water can reach and has thresholds for major roads. Noah adds **when** for every road, residential streets included, routes around them, and delivers it by text.
- *Storm drains / flash street flooding?* Not forecast; creek and river flooding only. Noah passes on NWS flash-flood warnings and live camera/closure signals instead. Said up front.
- *What if it's wrong?* It's conservative: an "uncertain" band treated as impassable, never "safe", every no-flood answer says "not a safety guarantee", 911 when there's danger.
- *Scale?* Metro Atlanta now (4 watersheds, 1,426 km²); the same pipeline runs basin by basin; NOAA data covers the whole US.
- *Privacy?* No accounts. The iMessage relay logs only a hashed sender, length and timing; places are kept in memory only.

---

## 2. Photon — Agents in iMessage (must use Spectrum)
**They care about:** a real agent that lives in iMessage, built on Spectrum, that feels natural and useful.
**Angle:** in an emergency you won't download an app; you'll text. The agent is where people already are.

**Demo (≈2 min, real phone, mirrored):**
1. *"hi"* → Noah explains itself in one text.
2. *"My home is Woodward Way NW, Atlanta and I work at Emory University"* → remembers both (per-person memory).
3. *"Can I drive home from work at 6 PM?"* → typing indicator → route answer with the street and time (tool use: geocoding, forecast, routing, live sources).
4. *"Is Northside Drive near Peachtree Creek going to flood?"* → understands "street near landmark"; separates the street from nearby roads with distances; names a traffic camera that saw water (AI-checked twice).
5. *"Is it safe to drive on Collier Road?"* → guardrail: never says "safe"; gives the forecast, "never drive into water", 911.
6. (If built Saturday) **Noah texts first:** when a saved route gets cut in a new hourly forecast, Noah sends the alert unprompted.

**Under the hood (one slide):** iPhone → Spectrum Cloud iMessage line → `spectrum-ts` relay (open source, TypeScript, typing indicator via `space.responding`) → Noah agent (Azure OpenAI tool calling) → NOAA forecast + 33 live sources. Never silent: if anything fails or takes > 45 s, Noah sends the safety message. Privacy: no message content logged.
**Close:** "The agent lives where people already are, and it speaks up before the water does."

---

## 3. Replit — Small Business
**They score:** the best small-business app built with Replit; working and creative over technical complexity.
**Angle:** a local pharmacy, restaurant or florist with 1–5 drivers has no enterprise routing. On storm days they guess, and drivers and deliveries get stuck. For a pharmacy, a missed delivery can mean a homebound patient without medication.

**Demo (≈2 min, on the Replit-hosted URL):**
1. Open **Noah Dispatch** (show it's running on Replit).
2. Peachtree Corner Pharmacy (sample) has 9 stops today. Click *Check deliveries* (latest live forecast).
3. Verdicts per stop: *go before ~6 PM*, *hold*, *no forecast flooding*, *outside coverage*.
4. Drag the slider: "if a driver leaves at 6 PM": routes go green → amber → red dashed, with a ✕ at the street that floods ("Collier Road · impassable ~7 PM").
5. The plan writes itself: deliver Collier Rd first, hold the Buckhead stops, everything else as usual.
6. Barricade list tab → CSV: the same forecast as a ranked list for the city.

**Business value lines:** answers in seconds; no setup (paste addresses); no accounts; protects drivers and keeps promises to customers. Business model: free for residents; a subscription per location for businesses; cities pay for the barricade feed (no prices claimed).
**Close:** "A dispatcher's flood plan in one click, built and hosted on Replit."

---

## 4. Tiger Data (MLH) — only if built Saturday (J11)
**Angle:** flood risk is a time series. Every hour NOAA issues a new 18-h forecast for every creek; Noah turns it into a flood time for every road.
**Demo:** forecast runs stored as a hypertable (run × road segment × forecast hour) → a `time_bucket` query: "roads flagged per hour across Isaias" and "how Collier Road's forecast changed run by run"; join with observed gauge readings for validation. Don't claim it unless the query runs live.

---

## Must be true by Sunday (Saturday checklist)
| # | Item | Owner | By |
|---|---|---|---|
| 1 | Replit deploy + public URL, `WEB_BASE` set so iMessage answers include map links (BL-9) | Priyanshu (+ Margulan: account/secrets in browser) | Sat 18:00 |
| 2 | 8 AM forecast run committed as evidence (BL-16) | Margulan | Sat ~10:00 |
| 3 | Decide which storm leads (J13) | Both | Sat 14:00 |
| 4 | Isaias validation: closures + gauges vs flags, counts (BL-18/19) | Margulan | Sat 22:00, final Sun 03:00 |
| 5 | Camera evidence card (auto, BL-22) → pick the best one | Margulan | Sun 03:00 |
| 6 | Tiger Data minimal store + one query (J11) | Priyanshu | after E2E |
| 7 | Optional: Noah texts first on a newly cut saved route (Photon wow) | Margulan | only if 1–4 are done |
| 8 | Demo phone: Noah thread pre-seeded (home/work), QuickTime screen mirroring tested | Margulan | Sun 07:00 |
| 9 | Roles (J8): Margulan tells the story + takes hydrology Q&A; Priyanshu drives the map/dispatch | Both | Sat 20:00 |
| 10 | Backup video recorded; Devpost + README final | Both | Sun 04:00 / 07:00 |

**Fallbacks on stage:** Wi-Fi down → phone hotspot, then the video. Bot slow → read the reply already in the pre-seeded thread. Map won't load → screenshots in the slides.

## Fact sheet (say only these)
| Fact | Source |
|---|---|
| Over half of flood-related drownings involve a vehicle driven into floodwater | CDC figure used by the NWS "Turn Around Don't Drown" campaign (e.g. Kentucky Emergency Management) |
| Helene: Atlanta's first-ever Flash Flood Emergency | Fox Weather, Sep 27, 2024 |
| 25 people rescued in the Peachtree Creek / Peachtree Battle area | Atlanta News First, Sep 27, 2024 |
| 37 deaths in Georgia from Helene | Wikipedia, "Effects of Hurricane Helene in Georgia" |
| Peachtree Creek crossed flood stage 9:15 PM Sep 26; NOAA's 8 AM run forecast it → 13.2 h | USGS 02336300 + our validation (`web/data/validation.json`) |
| Windsor Pkwy: Noah 10 PM, closed ~10:15 PM | Our 8 AM Helene run; Appen Media / 11Alive |
| NOAA road thresholds: 15,289 segments; Noah's own: 62,202 (residential) | `seg_thresholds.parquet` |
| Coverage: 4 metro Atlanta watersheds, 1,426 km² | WBD HUC10s |
| Isaias: Fri 6 PM 77 roads flagged → Fri 10 PM 313 | live runs in `web/data/` |
| Isaias validation [N/M, ~X h] | BL-18/19 (fill) |
