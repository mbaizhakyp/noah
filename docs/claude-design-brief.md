# Noah: design brief (paste into Claude Design)

## The product
Noah is a street-level flood forecast for metro Atlanta. Every hour NOAA's National Water Model forecasts every creek 18 hours ahead; Noah turns that into a time for every road ("Bradford Square NE: uncertain, treat as impassable from around 8 AM"), routes around those roads, and answers by text message. Built at Hacklanta 2026 during Hurricane Isaias (Sat Oct 10, 2026).

## Who and where it is seen
- **User:** Maya, a delivery driver for a small pharmacy (example persona). She can't stay home in a storm. Her question: *which of today's deliveries can I make, which do I hold, and when must I leave?*
- **Audience:** Social Good judges, 3-minute pitch. Shown on a **laptop mirrored to a projector, 1280×720, at 125% browser zoom**, plus an iPhone mirrored for the text messages. It has to read from the back of a room in about 10 seconds.
- **Mode on stage:** a replay of Saturday's 8:00 AM forecast. A visible label must say so.

## Screens to design
1. **Trip plan, desktop (hero).** Left panel (~380 px) + full-height map. Panel, top to bottom:
   - Header: "Noah", "Saturday 8:00 AM forecast · replayed" banner.
   - Saved-place chips: Home · Work · Delivery route.
   - Trip list with lettered pins: A depot, B–F stops, back to depot. "Add stop", "Swap".
   - Departure time control ("Leave 8:30 AM") + primary button "Find route".
   - **Result card, the most important element.** Example (8 AM forecast): **"Hold 2 deliveries: Kingsport Dr NE and McLendon Dr are forecast cut by flooding since 8 AM. Make the other 3 in this order: Hammond Dr → Northcrest Way → Graves Rd."** Then "Not a safety guarantee. Never drive into water."
   - Stop list, one row per stop with a state chip: `Reachable` / `Go before 1 PM` / `Hold: cut since 8 AM`, and arrival time ("~9 min").
   - Secondary tabs: Roads to avoid (count) · Live checks · Last 18 h · Sources.
   Map: Noah's route (blue), roads forecast to flood (red, solid), uncertain roads (amber, dashed), the usual route where Noah avoids it (grey, dashed), **each held stop in frame with a red ✕ and a label "Cut since 8 AM"**, cut markers with the hour, traffic cameras as small dots.
2. **The same screen in its other states:** loading ("Checking roads…"); every stop reachable; one stop "Go before 1 PM" (from the 4 AM forecast: Kingsport Dr NE); outside coverage ("Noah doesn't have road-level forecasts for this part of Georgia yet").
3. **Phone, iMessage thread** (Noah texts first). Real messages from Saturday:
   - Noah, unprompted: "Noah route watch, NOAA forecast issued Sat 8 AM (Noah had it Sat 9:58 AM): • Chamblee: Lavista Rd → Sidney Marcus Blvd NE: forecast cut by flooding from ~Sat 8 AM at Bradford Square NE (new). 7 of 11 watched routes forecast cut now. Never drive into water; call 911 if anyone is in danger. This is not a safety guarantee."
   - Then Maya asks one question and gets a short answer with a map link.
4. **Proof card (slide, 16:9).** Timeline: "Fri 11:50 PM Noah flags the road → [time] the creek crosses / the road closes: [N] hours of warning". Second line: "Helene 2024 backtest: 13.2 hours of warning; Windsor Pkwy forecast 10 PM, closed ~10:15 PM." Keep the bracketed values as visible placeholders.

## Real data to use (don't invent other numbers)
- Depot: Maya's pharmacy (example), Chamblee. Stops: Northcrest Way (Doraville), Graves Rd (Norcross), Kingsport Dr NE (Sandy Springs), McLendon Dr (Clarkston), Hammond Dr (Dunwoody).
- 8 AM forecast: 243 road segments flagged across metro, 73 forecast to flood. Route summary style: "13 min · goes around 12 road segments forecast to flood".
- Roads-to-avoid row style: "Do not cross Woodside Way. Forecast shows water reaching it around Sat 8:00 AM."

## Rules (non-negotiable)
- **Never** use "safe", "safely", "clear", "passable", "you're fine", "no risk", or reassurance like "won't flood". Use: "Do not cross {road}", "{road}: uncertain, treat as impassable from around {time}", "No flooding is forecast on this route through {time}. This is not a safety guarantee."
- Mention 911 wherever a message describes danger.
- **Never encode state by color alone:** red solid + "Do not cross", amber **dashed** + "Uncertain", ✕ icon + text for held stops.
- Times in Eastern time, clock style ("8:00 AM", "Sat 1 PM").
- Credits stay visible: "© CARTO, © OpenStreetMap contributors"; on camera images "Webcams provided by Windy.com".
- No accounts, logins, prices or ratings. Nothing that implies a road is open.

## Visual direction
- Map-first, calm, civic and trustworthy: a public-safety tool, not a consumer app. One accent (Noah's blue route). Red and amber are reserved for flood states.
- Light theme first (projectors wash out dark UIs); a dark variant is a bonus.
- Projector legibility: body at least 15 px, the result card's headline 22–28 px, chips 13 px+ with strong contrast. Hierarchy: result card > stop list > everything else.
- The current build is plain HTML/CSS + MapLibre GL on a CARTO light basemap with Lucide icons. Designs must be implementable without a framework.

## What I want back
1. Hi-fi mockups of screens 1–4 at their real sizes, with the states from screen 2.
2. A small token sheet: color tokens (light + dark), type scale, spacing, radii, chip and card specs.
3. Short annotations on anything interactive (what a click does).

## Design references
[Paste or attach references here.]
