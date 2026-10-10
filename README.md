# Noah

**Waze for floods that warns you before the road goes under, not after.**

Noah forecasts which road segments will flood in the next 18 hours and roughly when. It routes you around them and answers plain questions over iMessage ("can I get home tonight?").

> Built at Hacklanta 2026 (Oct 9–11, Georgia State University) · Track: Social Good · Side challenges: Photon (Agents in iMessage), MLH Best Use of Gemini API.

**Status:** in progress. This README becomes the Devpost-ready version at feature freeze (Sun 00:00).

## How it works (one paragraph)
We pull NOAA National Water Model short-range streamflow forecasts for every creek reach, hourly and 18 hours ahead. NOAA's synthetic rating curves turn each forecast flow into a water level. We compare that level against the Height Above Nearest Drainage (HAND) elevation of every OpenStreetMap road in the Peachtree Creek watershed (Atlanta). A road is flagged when the forecast water would reach it. Routing removes flagged roads, and a Gemini agent reached through iMessage answers in plain language. Noah never says a road is safe.

## Run it
_TBD at freeze. See `docs/02-ARCHITECTURE.md` §6._

## Docs for contributors (and their AI agents)
`CLAUDE.md` → `docs/01`–`06` → `specs/`.

## Disclosures
_TBD. List every pre-existing asset, dataset and library used._
