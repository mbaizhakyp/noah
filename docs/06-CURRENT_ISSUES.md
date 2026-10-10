# 06 — Current Issues

_Newest at the top of each table. Tag the owner as M (Margulan) or P (Priyanshu). Times in ET._

## Blockers (stop-the-line)
| # | Opened | Owner | Issue | Next step / fallback |
|---|---|---|---|---|
| B4 | Fri 21:05 | P (or M) | **Camera capture (013 step 1) must be running by Sat 01:00.** GDOT cameras keep no recordings, and Isaias rain begins early Sat. | **BL-7** key check by 23:00 (the key may be instant; the docs mention no review step). No key by 00:00 → J4 chooses option B (gray area) or C (own photos). Cameras are P2, so the demo doesn't depend on them. |
| B1 | Fri 20:30 | M | **Unknown whether NWM short-range forecast Helene well at feature 2047989.** The replay story depends on it. | Spec 001 + gauge plot by 00:00. Fallback: if no cycle before ~21:00 EDT Sep 26 forecasts > 161 m³/s, replay `analysis_assim` (what actually happened). Pitch it as a road-level timing engine; quote lead time only where it exists. |
| B2 | Fri 20:30 | M | FIM bucket `noaa-nws-owp-fim` is **Requester Pays**; anonymous access is denied. It needs an AWS account with a card on file. | Create the AWS account now; egress for one HUC8 costs pennies. Fallback: FIMserv-hosted HAND (github.com/sdmlua/fimserve), or build HAND for the HUC10 from a 3DEP DEM with pysheds/WhiteboxTools plus the USGS rating at the gauge. |
| B3 | Fri 20:30 | P | Photon Spectrum API, account and iMessage line provisioning not yet confirmed. | Go to the Photon booth/mentors first thing. Fallback 1: `imessage-kit` on a team Mac with a spare Apple ID. Fallback 2: Twilio SMS, and drop the Photon challenge (keep Gemini). |

## Decisions needed (both humans)
| # | Opened | Decision | Recommendation | Decide by |
|---|---|---|---|---|
| J1 | Fri 21:05 | **Priyanshu's expanded-vision proposal** (`01-PROJECT_OVERVIEW.md`, pushed 19:51 CT): US-wide coverage, potholes, sewer overflow, satellite, CCTV, 3 user types, a database. | Accept the proposal's own "hackathon reality check". **Ship:** the MVP + Isaias bonus (011) + cameras (013) + low spots (012, stretch). **Roadmap slide:** US-wide, business/fleet, county dashboard, satellite, sewer-overflow prediction, potholes (no open Atlanta data found). Keep D4 (Peachtree), D7 (no DB) and D8 (laptop + tunnel) for the hackathon. Once agreed, move the proposal under a "Roadmap" heading in 01. | Sat 00:00 (at the go/no-go) |
| J2 | Fri 21:05 | Saved routes + Google/Apple Maps hand-off (BL-3), county stats view (BL-4) | BL-3 is cheap and makes a good demo moment, but only after 14:00 E2E. BL-4 goes to the roadmap. | Sat 14:00 |
| J4 | Fri 21:30 | **Camera fallback if no 511GA key by 00:00:** B = fetch 10–15 hand-picked public image URLs (allowed by robots.txt, terms unverified) vs C = our own sidewalk photos during Isaias vs cut. | C, or B if both are comfortable with the gray area. Never call `/list/getdata/`. | Sat 00:00 |
| J5 | Fri 21:30 | **B2B scope + owner:** BL-8 (dispatch board + barricade list) owned by Margulan Sat afternoon; move 012 (low spots) to the roadmap to make room. | Yes. It's the Replit Small Business entry and the "who pays" answer. | Sat 00:00 (so spec 014 can be written tonight) |
| J6 | Fri 21:30 | **Hosting:** Replit hosts API + map + dispatch board (BL-9, Priyanshu) instead of laptop + tunnel + GitHub Pages (changes D8). Where the iMessage relay runs depends on Photon: Spectrum Cloud → Replit is fine; `imessage-kit` → must stay on a Mac. | Yes, if the Replit booth confirms the deploy plan/credits tonight. Keep laptop + `cloudflared` as the fallback. | Sat 00:00 |
| J7 | Fri 21:30 | **Live demo setup:** a fixed demo "home" address in the AOI (not anyone's real home), demo origin/destination pairs, which phone texts Noah on stage, which Apple ID/line Noah uses. | Pick 2 addresses along Peachtree Creek that Helene flooded (from 005 street truth) + 1 dry control. Use Priyanshu's or Margulan's phone as the sender. | Sat 14:00 (E2E test uses them) |
| J8 | Fri 21:30 | **Roles for judging:** who gives the 3-min pitch, who drives the demo (phone + map), who records/edits the video. | Margulan pitches the problem + hydrology; Priyanshu drives the live demo; record together at Sun 02:00. | Sat 20:00 |

## Open risks and unknowns
| # | Opened | Owner | Issue | Plan |
|---|---|---|---|---|
| R14 | Fri 21:05 | Both | **Potholes:** no open ATL311 pothole dataset found (raw 311 data appears to come only through open-records requests to OpenRecords-311@atlantaga.gov, ~3 business days). Potholes also barely change flood estimates. | BL-2 research (30 min). Default: roadmap. |
| R13 | Fri 21:05 | M | **Storm drains / sewers:** no open Atlanta storm-inlet or pipe layer found. Records requests take ~3 business days. Real sewer-overflow feeds exist only for some utilities. | Build 012 (terrain low spots) as the honest stand-in. BL-1 research. Keep "storm-drain flooding is not forecast" in the limits. |
| R12 | Fri 21:05 | P | **511GA terms** for storing/redisplaying snapshots unverified. Cameras cover GDOT routes only. API limit 10 calls / 60 s. | Read the terms at key signup and record them in spec 013. Frames stay local (gitignored), attributed, deleted after the event. |
| R11 | Fri 21:05 | M | **Isaias may not flood Peachtree Creek.** The 22Z Oct 9 forecast peaks at ~1,061 cfs, below action stage. Most rain falls after that forecast's window. | Spec 011 decision at Sat 14:00. Helene remains the main demo either way. |
| R1 | Fri 20:30 | M | Exact FIM4 S3 layout and file names (version folder, branch IDs, `rem_zeroed_masked_<branch>.tif`, catchment raster, `hydroTable_<branch>.csv` columns) are unverified. | Spec 002 starts with `aws s3 ls --request-payer requester`. Record the real paths in spec 002. |
| R2 | Fri 20:30 | M | FIM4 uses multiple branches (branch 0 + level-path branches). MVP uses one branch per spec 002. | Log which branch was used. Taking the max across branches is the upgrade path. |
| R3 | Fri 20:30 | M | Culvert crossings: HAND ≈ 0 where streams are burned through road embankments. | Handled by the channel-pixel filter (`02-ARCHITECTURE.md` §2.3). Spot-check 3 crossings on the map. |
| R4 | Fri 20:30 | M | HAND + synthetic rating curves are weak on small urban creeks. `UNCERTAIN_BAND_M = 0.5` is a heuristic, not calibrated. | State it in Q&A. The uncertain band and "treat as impassable" wording are the mitigation. |
| R5 | Fri 20:30 | M | Need 2–3 streets with dated public photos or news showing flooding on Sep 27, 2024 in the Peachtree Creek HUC10 (e.g., Buckhead along Peachtree Creek). | Spec 005. Use only sources we can cite. No invented examples. |
| R6 | Fri 20:30 | P | Current Gemini model ID unknown (Oct 2026). | Check ai.google.dev/gemini-api/docs/models and set `GEMINI_MODEL` in `.env`. |
| R7 | Fri 20:30 | P | Nominatim usage policy: 1 req/s, needs a real User-Agent, no bulk use. | Cache every lookup, restrict to the AOI viewbox, set the User-Agent to `noah-hacklanta/0.1 (contact: team email)`. |
| R8 | Fri 20:30 | P | Map on GitHub Pages (HTTPS) calling the laptop API needs an HTTPS tunnel and CORS. | Use a `cloudflared` HTTPS URL; FastAPI CORSMiddleware allowing the Pages origin only. |
| R9 | Fri 20:30 | Both | Out of scope by design: storm-drain and flash street flooding (012 is info only), recession timing. | Say it in the pitch "limits" beat. Never imply otherwise. |
| R10 | Fri 20:30 | Both | Q&A prep: "isn't this just NOAA FIM?"; "how accurate?"; the name collides with Noah-MP (the land-surface model inside NWM) and Project NOAH (Philippines). | Margulan owns these answers. Name collision one-liner: "named for the flood story; unrelated to Noah-MP, which ironically sits inside the model we use." |

## Before we start building (checklist, both)
- [ ] Each person approves their own specs (`Status: Draft → Approved`): M 001–005, 011 (012 if kept) · P 006–010, 013.
- [ ] Priyanshu confirms or objects to CC1 (the additive contracts).
- [ ] Decide J1, J4, J5, J6 (or explicitly defer them to their "decide by" time).
- [ ] Accounts: AWS (M), Gemini (P), Photon (P), Replit (P), 511GA (BL-7).
- [ ] Specs 014 (BL-8) and 015 (BL-9) written + approved before anyone codes them.

## Contract change proposals
| # | Opened | Proposer | Change | Agreed by both? |
|---|---|---|---|---|
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
| J3 | Fri 21:30 | Mercedes CV stays dropped. **FINAL:** main track Social Good; side challenges Photon + Gemini + Replit (Margulan, D2). |
