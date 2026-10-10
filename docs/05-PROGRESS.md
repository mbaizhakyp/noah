# 05 — Progress Tracker

_Last updated: Fri Oct 9, 2026, 8:30 PM ET (initial)_

## Clock (ET)
| When | Milestone | Status |
|---|---|---|
| Fri 20:30 | Hacking starts | ☐ |
| Fri ~22:00 | Accounts ready: AWS (requester pays), Gemini key, Photon line | ☐ |
| **Sat 00:00** | **GO/NO-GO:** NWM forecast at gauge reach vs observed (spec 001 + quick 005 plot). Spectrum echo bot works on a real phone (spec 008). | ☐ |
| Sat 03:00 | `graph.graphml` + `aoi.geojson` pushed (003 step 1). Map shows fixture flood roads. | ☐ |
| Sat 09:00 | `seg_hand.parquet` + `rating.parquet` exist | ☐ |
| Sat 12:00 | First real `flood_<cycle>.geojson` on the map | ☐ |
| **Sat 14:00** | **E2E:** text to iMessage → agent → real flood data → reply + detour + map link | ☐ |
| Sat 20:00 | Lead-time number + 2–3 street confirmations in `validation.json` / docs | ☐ |
| **Sun 00:00** | **FEATURE FREEZE.** README, Devpost draft, pitch script. | ☐ |
| Sun 04:00 | Demo video recorded (2–3 min, real phone + real map) | ☐ |
| **Sun 07:00** | **Devpost submitted** (internal deadline) | ☐ |
| Sun 09:00 | Hard deadline. Then pitch rehearsal and judging. | — |

## Owners
| Area | Owner | Directories |
|---|---|---|
| Data pipeline, validation | Margulan | `noah/pipeline/`, `web/data/` |
| API, routing, agent, relay, map | Priyanshu | `noah/api/`, `bot/`, `web/index.html`, `fixtures/` |
| Pitch, Devpost, video | Both (Margulan leads the hydrology story) | `README.md`, `docs/` |

## Specs
| Spec | Title | Owner | Time box | Status |
|---|---|---|---|---|
| 001 | NWM forecast fetch + subset | Margulan | 2 h | Draft |
| 002 | FIM HAND + rating curves fetch | Margulan | 2 h | Draft |
| 003 | AOI, road graph, HAND sampling | Margulan | 3 h | Draft |
| 004 | Flood times per segment | Margulan | 2 h | Draft |
| 005 | Validation: lead time + street truth | Margulan | 3 h | Draft |
| 006 | Routing + HTTP API | Priyanshu | 3 h | Draft |
| 007 | Gemini agent + safety filter | Priyanshu | 3 h | Draft |
| 008 | iMessage relay (Photon Spectrum) | Priyanshu | 2 h | Draft |
| 009 | Web map with time slider | Priyanshu | 3 h | Draft |
| 010 | Photo check (stretch) | Priyanshu | 2 h | Draft (stretch: only after 14:00 E2E) |

Status flow: `Draft → Approved (human) → In progress → Done (acceptance criteria shown passing)`.

## Plan by person
### Margulan
- Fri 20:30–00:00: approve 001/002/003 → **001** (Helene cycles) → quick gauge plot (first half of 005) → **GO/NO-GO**. Start 002's downloads in the background once AWS is ready.
- Sat 00:00–04:00: **003** step 1 (AOI + graph, push early for Priyanshu) → 002 finish → 003 HAND sampling.
- Sat 04:00–08:00: sleep.
- Sat 08:00–14:00: **004** → real `web/data/` pushed → join the E2E test.
- Sat 14:00–20:00: **005** full: lead time, chart, 2–3 confirmed streets.
- Sat 20:00 onward: README hydrology section, pitch, video, submit.

### Priyanshu
- Fri 20:30–00:00: accounts (Gemini, Photon at their booth) → approve 006–009 → **008** echo bot on a real phone → **fixtures/** per contracts C4–C6.
- Sat 00:00–05:00: **009** map on fixtures → **006** routing + API on fixtures (switch to real `graph.graphml` as soon as it's pushed).
- Sat 05:00–09:00: sleep.
- Sat 09:00–14:00: **007** agent wired to 006 + 008 → **E2E 14:00**.
- Sat 14:00–20:00: polish the map on a phone, test the map link from iMessage, run the tunnel. 010 only if E2E is solid.
- Sat 20:00 onward: README run instructions, video capture, submit.

## Log
_Append-only. Format: `HH:MM Name — what was done — how verified (command)`._

### Margulan
- 20:18 — Pulled USGS IV for 02336300, Sep 26–28, 2024. Minor (17 ft) up at 2024-09-26 21:15 EDT; major (20 ft) up at 23:45 EDT; peak 23.75 ft at 2024-09-27 08:15 EDT; peak Q 20,000 cfs at 05:45 EDT. — `nwis.waterservices.usgs.gov/nwis/iv/?sites=02336300&parameterCd=00065,00060&startDT=2024-09-26T00:00-04:00&endDT=2024-09-28T00:00-04:00&format=json`
- 20:18 — Verified the NWM archive exists: `gs://national-water-model/nwm.20240927/short_range/...channel_rt.f001.conus.nc` (12.7 MB, anonymous HTTPS). AWS `noaa-nwm-pds` has no 2024 data.
- 20:18 — Verified AOI and IDs: HUC10 0313000112 "Peachtree Creek" (338.49 km²), HUC8 03130001; NLDI comid for the gauge = 2047989; NWPS AANG1 thresholds (action 13 / minor 17 / moderate 18 / major 20 ft; 3630 / 5700 / 7000 / 7800 cfs).

### Priyanshu
- _(nothing yet)_
