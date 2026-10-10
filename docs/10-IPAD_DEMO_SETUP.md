# 10 — iPad demo setup (for Margulan)

How to get the recorded snapshot onto your laptop and run Noah for iPad (spec 021) on your iPad.
The snapshot is gitignored (`web/demo/snapshot/`), so `git pull` alone doesn't bring it. Priyanshu uploaded his copy to a private GitHub release.

## 1. Get the snapshot (2 min)

Download the recorded snapshot instead of re-recording it (re-recording takes about 40 min):

```bash
git fetch && git pull --rebase
gh release download demo-snapshot-20240926T12Z -R mbaizhakyp/noah -D /tmp
shasum -a 256 /tmp/noah-demo-snapshot-20240926T12Z.tar.gz
# expect 2cdc502445aa1e847b7fbd8b9b9c5162c5ba35bd8d94ac1f8e1e0bbe7d3a607a
rm -rf web/demo/snapshot && tar -xzf /tmp/noah-demo-snapshot-20240926T12Z.tar.gz -C web/demo
```

Check: `web/demo/snapshot/index.json` says `"cycle": "20240926T12Z"`, and `web/demo/snapshot/r/` has about 2,145 files.
The release page is https://github.com/mbaizhakyp/noah/releases/tag/demo-snapshot-20240926T12Z (57 MB; about 430 MB unpacked).

**Fallback: rebuild it yourself** if the download fails or the recording needs to change (for example, a new `CYCLE` or new saved places in `noah/api/demo.py`). Start the API (step 2), then run `uv run python -m noah.api.demo all` (about 40 min). To rebuild only the iPad plans file, run `uv run python -m noah.api.demo ipad`.

## 2. Run the API (on the laptop)

```bash
uv run uvicorn noah.api.app:app --host 0.0.0.0 --port 8010
```

Open `http://localhost:8010/ipad/` on the laptop first and confirm the Deliveries chip shows a leave-by.

What the API needs beyond the snapshot. You already have all of it from the pipeline:
- `web/data/flood_20240926T12Z.geojson` (committed).
- The road graph and thresholds under `data/interim/` (yours; gitignored). Home / Work and any typed route are answered live by the API on run `20240926T12Z`, so they need these files.
- `WINDY_API_KEY` in `.env` for live camera frames (`GET /cam/{id}`). Without it the rest of the page still works.

## 3. Reach it from the iPad

Location (the blue dot) needs **https**, so a plain LAN address shows the map without your position.

- **Venue Wi-Fi (Fortinet):** it blocks trycloudflare and isolates devices on the LAN. What works is a localhost.run SSH tunnel:
  ```bash
  ssh -R 80:localhost:8010 localhost.run
  ```
  It prints an `https://….lhr.life` address. Open `<that address>/ipad/` in Safari on the iPad. The address can change when the tunnel reconnects, so re-check it before you demo. A free anonymous tunnel is enough. Priyanshu's run used his own key (`-i ~/.ssh/id_ed25519`); you don't need it.
- **Home or hotspot Wi-Fi (same network as the laptop):** `http://<laptop LAN IP>:8010/ipad/` also works, but without location. Get the IP with `ipconfig getifaddr en0`.

## 4. Put it on the iPad home screen

In Safari, open `/ipad/`, tap Share, then **Add to Home Screen**. It opens full screen like an app (manifest and icon are in `web/ipad/`).
After the tunnel address changes, delete the home-screen icon and add it again from the new address.

## 5. Before the demo, check

- [ ] The laptop is plugged in, and the API is running under `caffeinate -i`.
- [ ] The tunnel is up and `/ipad/` loads on the iPad over **cellular or venue Wi-Fi**, not only at home.
- [ ] Deliveries: leave by 7:30 PM. Home: leave by 7:55 PM. Work: leaving 7 PM routes around 12 flooded roads (spec 021 acceptance).
- [ ] A camera row opens a live frame (Windy key OK).
- [ ] Nothing on screen says demo, replay, snapshot, Helene or Isaias (spec 021 wording rule).

## Pointers

Spec: `specs/021-ipad-app.md`. Design: `docs/09-IPAD_APP.md`. Page: `web/ipad/index.html` (one file, no build). Recording: `noah/api/demo.py` (`CYCLE`, `NOW_MIN`, saved places). Open decisions: `docs/05-PROGRESS.md`, 14:00 handoff entry.
