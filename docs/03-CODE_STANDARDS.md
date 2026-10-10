# 03 — Code Standards

Guiding rule: **least code that works, and boring code over clever code.** It's a 36-hour build that two humans and two AIs have to understand at 4 AM.

## Python (pipeline + API)
- Python 3.12, managed with **uv** (`uv add <pkg>`, `uv run ...`), with a single `pyproject.toml` at the repo root.
- Baseline dependencies: `xarray`, `h5netcdf`, `h5py` (h5netcdf can't read NWM files without it; verified Oct 9), `pandas`, `pyarrow`, `geopandas`, `shapely`, `rasterio`, `osmnx`, `networkx`, `httpx`, `fastapi`, `uvicorn`, `google-genai`, `python-dotenv`, `pytest`, `ruff`. **A new dependency needs one line of justification in the commit message.** Prefer the stdlib or something already installed.
- Format and lint with `uv run ruff format && uv run ruff check --fix`. Default ruff config, line length 100.
- Write plain module-level functions. Use a class only when state genuinely needs one; FastAPI app state is fine. No abstract base classes, factories or plugin systems.
- Type hints on public functions. Each module's docstring says what it reads and writes, citing contract IDs (C1–C10).
- Every pipeline module has a `main()` with `argparse` and runs as `python -m noah.pipeline.<name>`. Running it twice skips work that is already done, unless `--force` is passed.
- Constants and paths come only from `noah/config.py`. No magic numbers or hardcoded paths elsewhere.
- Logging: `logging.basicConfig(level=INFO)` with one line per major step and counts ("12,431 segments, 3,210 with HAND samples").
- Errors: **the pipeline fails loudly** with a clear message about what is missing and how to get it. **The API fails conservatively**: catch at the endpoint and return the error reply from `02-ARCHITECTURE.md` §5. Never show a stack trace to a user.
- Mark deliberate shortcuts with a `# ponytail:` comment naming the limitation and the upgrade path, e.g. `# ponytail: no recession modeled; add t_clear if judges ask`.

## Geospatial and units
- **Units:** SI internally (m, m³/s). Convert USGS ft and cfs at the edges only, with the factors written out: `1 ft = 0.3048 m`, `1 cfs = 0.0283168 m³/s`.
- **CRS:** EPSG:4326 for all outputs and API traffic. Do raster work in the raster's native CRS (FIM HAND is EPSG:5070; verify with `rasterio`). Reproject the vectors to the raster, never the raster to the vectors.
- **Time:** UTC internally (`datetime` with `tzinfo=UTC`). Convert to America/New_York only in user-facing strings.
- **IDs:** `feature_id` and `hydro_id` are int64. `seg_id` is a string `"{u}-{v}-{key}"`.
- Write GeoJSON for the web with coordinates rounded to 5 dp.

## TypeScript (bot/)
- Node 22 with a single `index.ts` run through `npx tsx`. No build step and no framework beyond the Photon Spectrum SDK.
- Logic stays in Python. The bot only relays messages.

## Web (web/)
- A single `index.html` with inline JS/CSS. MapLibre GL JS is loaded from a CDN at a pinned exact version. No bundler and no framework.
- Dark base map, because it suits the product and reads well at night. Must work on a phone screen, since the map link is opened from iMessage.
- Colors: amber `#f59e0b` = uncertain, red `#ef4444` = flooded, cyan `#22d3ee` = route. Each has a legend label; color is never the only cue.

## Tests
- Each module with real logic gets **one** small `tests/test_<module>.py` that runs offline in under 5 s on tiny fixtures. Required:
  - `test_flood_times.py`: the threshold, band, persistence, and channel-pixel filter.
  - `test_routing.py`: a blocked edge is avoided, `no_route` is returned when the destination is cut off, and out-of-coverage is detected.
  - `test_agent.py`: the banned-word filter catches "safe", "clear", "passable", case-insensitively and as whole words.
- Run with `uv run pytest -q`. No mocks of Gemini or Photon in tests. Test the pure functions around them.

## Git
- **Sync rule (mandatory, humans and AIs).** Two people commit to `main`, so never work on a stale copy:
  1. **Before starting any change:** `git fetch && git status -sb`. If it says `behind`, run `git pull --rebase` first. If the pull touched `docs/`, `specs/` or `noah/config.py`, re-read those files before editing.
  2. **Right before every commit:** run `git fetch && git status -sb` again. If behind: `git stash && git pull --rebase && git stash pop`, re-run the tests, then commit.
  3. **Right after committing:** `git push`. If it's rejected, `git pull --rebase` and push again. Never force-push to `main`.
  4. On a rebase conflict in a file the other person owns, stop and ask them. Don't guess.
- Push straight to `main` in small commits. No long-lived branches; we have no time for PR review.
- Commit message: `[spec-004] flood_times: channel-pixel filter`. Use `[docs]` for docs-only changes.
- Never commit `data/`, `.env`, rasters or NetCDF files. `web/data/*` is committed, under 20 MB per file.
- Shared files (`noah/config.py`, `docs/02-ARCHITECTURE.md`, `pyproject.toml`): tell the other person before pushing a change.

## Secrets
- `.env` holds the actual values and is gitignored. `.env.example` lists the names: `GEMINI_API_KEY`, `GEMINI_MODEL`, `PHOTON_*` (per Photon docs), `GA511_API_KEY`, `API_BASE`, `WEB_BASE`.
- Never print secrets. Never put them in URLs, logs or commit messages.
