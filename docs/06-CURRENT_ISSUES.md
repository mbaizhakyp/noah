# 06 — Current Issues

_Newest at the top of each table. Tag the owner as M (Margulan) or P (Priyanshu). Times in ET._

## Blockers (stop-the-line)
| # | Opened | Owner | Issue | Next step / fallback |
|---|---|---|---|---|
| B1 | Fri 20:30 | M | **Unknown whether NWM short-range forecast Helene well at feature 2047989.** The replay story depends on it. | Spec 001 + gauge plot by 00:00. Fallback: if no cycle before ~21:00 EDT Sep 26 forecasts > 161 m³/s, replay `analysis_assim` (what actually happened). Pitch it as a road-level timing engine; quote lead time only where it exists. |
| B2 | Fri 20:30 | M | FIM bucket `noaa-nws-owp-fim` is **Requester Pays**; anonymous access is denied. It needs an AWS account with a card on file. | Create the AWS account now; egress for one HUC8 costs pennies. Fallback: FIMserv-hosted HAND (github.com/sdmlua/fimserve), or build HAND for the HUC10 from a 3DEP DEM with pysheds/WhiteboxTools plus the USGS rating at the gauge. |
| B3 | Fri 20:30 | P | Photon Spectrum API, account and iMessage line provisioning not yet confirmed. | Go to the Photon booth/mentors first thing. Fallback 1: `imessage-kit` on a team Mac with a spare Apple ID. Fallback 2: Twilio SMS, and drop the Photon challenge (keep Gemini). |

## Open risks and unknowns
| # | Opened | Owner | Issue | Plan |
|---|---|---|---|---|
| R1 | Fri 20:30 | M | Exact FIM4 S3 layout and file names (version folder, branch IDs, `rem_zeroed_masked_<branch>.tif`, catchment raster, `hydroTable_<branch>.csv` columns) are unverified. | Spec 002 starts with `aws s3 ls --request-payer requester`. Record the real paths in spec 002. |
| R2 | Fri 20:30 | M | FIM4 uses multiple branches (branch 0 + level-path branches). MVP uses one branch per spec 002. | Log which branch was used. Taking the max across branches is the upgrade path. |
| R3 | Fri 20:30 | M | Culvert crossings: HAND ≈ 0 where streams are burned through road embankments. | Handled by the channel-pixel filter (`02-ARCHITECTURE.md` §2.3). Spot-check 3 crossings on the map. |
| R4 | Fri 20:30 | M | HAND + synthetic rating curves are weak on small urban creeks. `UNCERTAIN_BAND_M = 0.5` is a heuristic, not calibrated. | State it in Q&A. The uncertain band and "treat as impassable" wording are the mitigation. |
| R5 | Fri 20:30 | M | Need 2–3 streets with dated public photos or news showing flooding on Sep 27, 2024 in the Peachtree Creek HUC10 (e.g., Buckhead along Peachtree Creek). | Spec 005. Use only sources we can cite. No invented examples. |
| R6 | Fri 20:30 | P | Current Gemini model ID unknown (Oct 2026). | Check ai.google.dev/gemini-api/docs/models and set `GEMINI_MODEL` in `.env`. |
| R7 | Fri 20:30 | P | Nominatim usage policy: 1 req/s, needs a real User-Agent, no bulk use. | Cache every lookup, restrict to the AOI viewbox, set the User-Agent to `noah-hacklanta/0.1 (contact: team email)`. |
| R8 | Fri 20:30 | P | Map on GitHub Pages (HTTPS) calling the laptop API needs an HTTPS tunnel and CORS. | Use a `cloudflared` HTTPS URL; FastAPI CORSMiddleware allowing the Pages origin only. |
| R9 | Fri 20:30 | Both | Out of scope by design: storm-drain and flash street flooding, recession timing. | Say it in the pitch "limits" beat. Never imply otherwise. |
| R10 | Fri 20:30 | Both | Q&A prep: "isn't this just NOAA FIM?"; "how accurate?"; the name collides with Noah-MP (the land-surface model inside NWM) and Project NOAH (Philippines). | Margulan owns these answers. Name collision one-liner: "named for the flood story; unrelated to Noah-MP, which ironically sits inside the model we use." |

## Contract change proposals
| # | Opened | Proposer | Change | Agreed by both? |
|---|---|---|---|---|
| — | | | | |

## Parking lot (good ideas, not now)
- Live mode on today's NWM cycle (the code path is the same; flip `DEMO_CYCLE` to latest).
- Recession (`t_clear`) so roads reopen on the map.
- Max across FIM branches; expand AOI to all of HUC8 03130001; South River (HUC8 03070103).
- Push alerts: text subscribers when their saved route gets a new `flooded` segment.
- Photo check (spec 010) could feed a "reported" layer on the map.

## Resolved
| # | Resolved | How |
|---|---|---|
| — | | |
