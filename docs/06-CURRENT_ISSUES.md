# 06 — Current Issues

_Newest at the top of each table. Tag the owner as M (Margulan) or P (Priyanshu). Times in ET._

## Blockers (stop-the-line)
| # | Opened | Owner | Issue | Next step / fallback |
|---|---|---|---|---|
| B4 | Fri 21:05 | P (or M) | **Camera capture (013 step 1) must be running by Sat 01:00.** GDOT cameras keep no recordings, and Isaias rain begins early Sat. **Key requested Fri ~21:27 ET → Pending Approval (manual review).** Plan: option C (own sidewalk photos during Isaias, J4). If the key arrives, switch to option A and start capture right away; a key by Sat noon still catches the heaviest rain. Cameras are P2, so the demo doesn't depend on them. |
| B3 | Fri 20:30 | P | Photon Spectrum API, account and iMessage line provisioning not yet confirmed. | Go to the Photon booth/mentors first thing. Fallback 1: `imessage-kit` on a team Mac with a spare Apple ID. Fallback 2: Twilio SMS, and drop the Photon challenge (keep Gemini). |

## Decisions needed (both humans)
| # | Opened | Decision | Recommendation | Decide by |
|---|---|---|---|---|
| J1 | Fri 21:05 | **Priyanshu's expanded-vision proposal** (`01-PROJECT_OVERVIEW.md`, pushed 19:51 CT): US-wide coverage, potholes, sewer overflow, satellite, CCTV, 3 user types, a database. | Accept the proposal's own "hackathon reality check". **Ship:** the MVP + Isaias bonus (011) + cameras (013) + low spots (012, stretch). **Roadmap slide:** US-wide, business/fleet, county dashboard, satellite, sewer-overflow prediction, potholes (no open Atlanta data found). Keep D4 (Peachtree) and D7 (no DB) for the hackathon. Once agreed, move the proposal under a "Roadmap" heading in 01. | **Last** (Margulan, Oct 9): before the pitch script, Sat 20:00 |
| J2 | Fri 21:05 | Saved routes + Google/Apple Maps hand-off (BL-3), county stats view (BL-4) | BL-3 is cheap and makes a good demo moment, but only after 14:00 E2E. BL-4 goes to the roadmap. | Sat 14:00 |
| J9 | Fri 21:50 | **Tiger Data (MLH) suggested by Priyanshu.** It's a hosted time-series Postgres, *not* a replacement for AWS (AWS was only a download step and is no longer needed). It would be a 4th side challenge, which breaks the max-3 rule, so it reopens D2 only by **replacing Replit**. It also adds a database the plan avoids (D7). | Don't add it. Keep Replit (the dispatch board + hosting fit better). Tiger Data goes on the roadmap (hourly forecasts per road segment are a natural time-series store). | Not critical now (Margulan). Decide with J1 at the end. Anything later than Sat 12:00 effectively means no. |
| J5 | Fri 21:30 | **B2B scope + owner:** BL-8 (dispatch board + barricade list) owned by Margulan Sat afternoon; move 012 (low spots) to the roadmap to make room. | Yes. It's the Replit Small Business entry and the "who pays" answer. | **Sat 12:00** (deferred by Margulan). Spec 014 must be written + approved before the Sat 14:00 build block. Without BL-8 the Replit entry is only "hosted on Replit". |
| J6 | Fri 21:30 | **Hosting:** Replit hosts API + map + dispatch board (BL-9, Priyanshu) instead of laptop + tunnel + GitHub Pages (changes D8). Where the iMessage relay runs depends on Photon: Spectrum Cloud → Replit is fine; `imessage-kit` → must stay on a Mac. | **Agreed (Margulan, Oct 9)**, pending the Replit booth answers below. Keep laptop + `cloudflared` as the fallback. | Booth answers tonight |
| J7 | Fri 21:30 | **Live demo setup:** a fixed demo "home" address in the AOI (not anyone's real home), demo origin/destination pairs, which phone texts Noah on stage, which Apple ID/line Noah uses. | Pick 2 addresses along Peachtree Creek that Helene flooded (from 005 street truth) + 1 dry control. Use Priyanshu's or Margulan's phone as the sender. | Sat 14:00 (E2E test uses them) |
| J8 | Fri 21:30 | **Roles for judging:** who gives the 3-min pitch, who drives the demo (phone + map), who records/edits the video. | Margulan pitches the problem + hydrology; Priyanshu drives the live demo; record together at Sun 02:00. | Sat 20:00 |

## Open risks and unknowns
| # | Opened | Owner | Issue | Plan |
|---|---|---|---|---|
| R17 | Fri 22:30 | M | **Long simplified edges:** OSMnx merges road stretches between intersections, so some flagged segments are long (up to ~1 km) and the whole edge shows red although only part floods. A freeway (Horace E Tate Fwy) is flagged at +11 h, probably a culvert crossing not tagged as a bridge. | Spot-check the top 10 flagged segments on satellite imagery (005 part C). Upgrade: split edges at NOAA's per-catchment road pieces (`osmid_catchid`). Raise `MIN_ROAD_HAND_M` per artifact if needed. Routing stays conservative either way. |
| R16 | Fri 22:10 | M | **Forecast timing bias:** the 14Z–21Z Helene runs forecast flood flow 3–11 h late and 35–65% low. Roads flagged from those runs would flag late or not at all. | Demo from the most skillful early run (proposal: `DEMO_CYCLE = 20240926T12Z`, needs Margulan's OK since spec 005's rule said keep 18Z). Q&A: state it plainly; the uncertain band + "re-check before you leave" wording are the mitigation; it's NWM skill, not Noah's logic. |
| R14 | Fri 21:05 | Both | **Potholes:** no open ATL311 pothole dataset found (raw 311 data appears to come only through open-records requests to OpenRecords-311@atlantaga.gov, ~3 business days). Potholes also barely change flood estimates. | BL-2 research (30 min). Default: roadmap. |
| R13 | Fri 21:05 | M | **Storm drains / sewers:** no open Atlanta storm-inlet or pipe layer found. Records requests take ~3 business days. Real sewer-overflow feeds exist only for some utilities. | Build 012 (terrain low spots) as the honest stand-in. BL-1 research. Keep "storm-drain flooding is not forecast" in the limits. |
| R12 | Fri 21:05 | P | **511GA terms** for storing/redisplaying snapshots unverified. Cameras cover GDOT routes only. API limit 10 calls / 60 s. | Read the terms at key signup and record them in spec 013. Frames stay local (gitignored), attributed, deleted after the event. |
| R11 | Fri 21:05 | M | **Isaias may not flood Peachtree Creek.** The 22Z Oct 9 forecast peaks at ~1,061 cfs, below action stage. Most rain falls after that forecast's window. | Spec 011 decision at Sat 14:00. Helene remains the main demo either way. |
| R1 | Fri 20:30 | M | FIM layout: **resolved for v4.9** (see spec 002 "Discovered layout"). Still verify `hydrotable.parquet` columns and whether it covers branch 0. | Spec 002 step 3. |
| R2 | Fri 20:30 | M | FIM4 uses multiple branches (branch 0 + level-path branches). MVP uses one branch per spec 002. | Log which branch was used. Taking the max across branches is the upgrade path. |
| R3 | Fri 20:30 | M | Culvert crossings: NOAA thresholds can sit at channel level where a road crosses a creek on a culvert. | Rows with `threshold_hand < MIN_ROAD_HAND_M` (0.3 m) dropped + baseline guard (CC3). Known false-negative risk at real low-water crossings; see R17 for false positives. |
| R4 | Fri 20:30 | M | HAND + synthetic rating curves are weak on small urban creeks. `UNCERTAIN_BAND_M = 0.5` is a heuristic, not calibrated. | State it in Q&A. The uncertain band and "treat as impassable" wording are the mitigation. |
| R5 | Fri 20:30 | M | Need 2–3 streets with dated public photos or news showing flooding on Sep 27, 2024 in the Peachtree Creek HUC10 (e.g., Buckhead along Peachtree Creek). | Spec 005. Use only sources we can cite. No invented examples. |
| R6 | Fri 20:30 | P | Current Gemini model ID unknown (Oct 2026). | Check ai.google.dev/gemini-api/docs/models and set `GEMINI_MODEL` in `.env`. |
| R7 | Fri 20:30 | P | Nominatim usage policy: 1 req/s, needs a real User-Agent, no bulk use. | Cache every lookup, restrict to the AOI viewbox, set the User-Agent to `noah-hacklanta/0.1 (contact: team email)`. |
| R8 | Fri 20:30 | P | Map on GitHub Pages (HTTPS) calling the laptop API needs an HTTPS tunnel and CORS. | Use a `cloudflared` HTTPS URL; FastAPI CORSMiddleware allowing the Pages origin only. |
| R9 | Fri 20:30 | Both | Out of scope by design: storm-drain and flash street flooding (012 is info only), recession timing. | Say it in the pitch "limits" beat. Never imply otherwise. |
| R10 | Fri 20:30 | Both | Q&A prep: "isn't this just NOAA FIM?"; "how accurate?"; the name collides with Noah-MP (the land-surface model inside NWM) and Project NOAH (Philippines). | Margulan owns these answers. Name collision one-liner: "named for the flood story; unrelated to Noah-MP, which ironically sits inside the model we use." |

### J6: questions for the Replit booth (tonight)
1. **Eligibility:** what counts as "built with Replit"? Is importing our GitHub repo and deploying on Replit enough, or do judges expect Replit Agent / workspace use? Anything specific to show in the demo or Devpost?
2. **Credits:** any hackathon credits, Core trial or promo code this weekend? How much?
3. **Deploy type:** an always-on Python FastAPI that loads ~100–300 MB of data into memory at startup. Reserved VM or Autoscale? How slow is an Autoscale cold start after 15 min idle?
4. **Limits:** RAM/disk on the smallest VM; max file/repo size (graph file maybe 50–150 MB); data files in the deployment or Object Storage?
5. **Packages:** do `osmnx`/`shapely`/`networkx` install cleanly? Is `uv` supported?
6. **Long-lived connections:** can a Reserved VM keep a persistent outbound gRPC stream (Photon Spectrum relay) running next to the web server?
7. **Team access:** can both of us edit/deploy the same project on free/Core, or does that need Teams?
8. **After the event:** does the deployed URL need to stay up for Devpost judging, and for how long?

### J6: cost estimate if not free (Replit pricing per third-party guides, Aug–Sep 2026; confirm on replit.com)
| Scenario | Out of pocket |
|---|---|
| Booth gives credits / promo | $0 |
| Core for 1 month ($25, includes $25 credits) + Reserved VM shared 0.5 vCPU / 2 GB ($15/mo, ~$1.50 for 3 days, paid from credits) | **$25** |
| Same, but 1 vCPU / 4 GB VM if 2 GB is too small ($35/mo, ~$3.50 for 3 days, from credits) | **$25** |
| Keep the demo link up for a month after judging (VM from credits) | still **$25**, then cancel |
| Autoscale instead ($2 base + usage) | cheaper, but cold starts after 15 min idle; risky during judging |
| Using Replit Agent heavily to build (burns credits) | $10–50+ overage. **Avoid:** build with Claude Code locally, push to GitHub, deploy on Replit. |

## Before we start building (checklist, both)
- [ ] Each person approves their own specs (`Status: Draft → Approved`): M 001–005, 011 (012 if kept) · P 006–010, 013.
- [ ] Priyanshu confirms or objects to CC1 (the additive contracts).
- [ ] J6: ask the Replit booth the questions above (Priyanshu). J5 by Sat 12:00. J1 last.
- [ ] Accounts: Gemini (P), Photon (P), Replit (P), 511GA (BL-7, pending). No AWS needed.
- [ ] Specs 014 (BL-8) and 015 (BL-9) written + approved before anyone codes them.

## Contract change proposals
| # | Opened | Proposer | Change | Agreed by both? |
|---|---|---|---|---|
| CC2 | Fri 22:00 | M | C1/C5 lead hours extend from 1–18 to **0–18**: hour 0 = NWM `analysis_assim` (estimated now). Consumers: the slider already starts at 0 (009); routing/status treat 0 like any hour. No renames. | M ☑ · P ☐ |
| CC1 | Fri 21:05 | M | Additive: C6 `events` + `cycles[].event`; C9 `NOAH_CYCLE`, `beyond_forecast_window` state, `/cameras` endpoints; new C11 (low spots), C12 (camera assessments); §5 rows for low spot, camera water, beyond window. Already written into `02-ARCHITECTURE.md`. Nothing existing was renamed or removed. | M ☑ · P ☐ (Priyanshu: confirm or object before building 006/009) |

## Parking lot (good ideas, not now)
- Live mode on today's NWM cycle beyond the Isaias bonus (the code path is the same; set `NOAH_CYCLE` to latest).
- Recession (`t_clear`) so roads reopen on the map.
- Max across FIM branches; expand AOI to all of HUC8 03130001; South River (HUC8 03070103).
- Push alerts: text subscribers when their saved route gets a new `flooded` segment.
- Low spots (C11) feeding the agent/routing as `uncertain` during heavy forecast rain (needs a rainfall forecast, e.g., NWM forcing or MRMS).
- Pothole detection from camera frames or user photos (needs an accuracy test, not a claim).
- Everything in BL-6 (Priyanshu's roadmap items).

## Resolved
| # | Resolved | How |
|---|---|---|
| R15 / CC3 | Fri 22:15 | Margulan approved using NOAA FIM 4.9 per-road thresholds (`osm_roads_fimpact.csv`) instead of our own HAND sampling. Implemented in 003/004; C3 is now `seg_thresholds.parquet`; C5 unchanged. Pitch: NOAA computes where/at what flow; Noah adds when, routing and text delivery. |
| D5 | Fri 22:15 | Demo cycle = `20240926T12Z` (8 AM EDT), final. |
| B1 | Fri 22:08 | **GO.** NWM short-range forecast Peachtree Creek above minor flood flow in every cycle from 20240926T12Z; first warning 13.2 h before the observed crossing. Mid-day runs were late and low (see PROGRESS 22:08). |
| B2 | Fri 21:45 | No AWS needed. The same OWP HAND-FIM data (v4.9.9.0) is in the public CIROH bucket `ciroh-owp-hand-fim` (anonymous). NOAA's requester-pays bucket is now only the fallback in spec 002. Disclose the data source (FIMserv / CIROH) in the README. |
| J4 | Fri 21:45 | Camera fallback if no 511GA key by 00:00 = **option C** (our own sidewalk photos during Isaias). Option B (hand-picked public image URLs) only if both explicitly agree later. Never call `/list/getdata/`. (Margulan) |
| J3 | Fri 21:30 | Mercedes CV stays dropped. **FINAL:** main track Social Good; side challenges Photon + Gemini + Replit (Margulan, D2). |
