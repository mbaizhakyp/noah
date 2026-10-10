# 010 — Photo check (STRETCH)

| | |
|---|---|
| Owner | Priyanshu |
| Status | Draft (P2: start after the Sat 14:00 E2E milestone; its `classify()` unblocks 013 step 2) |
| Time box | 2 h |
| Depends on | 007 (agent), 008 (image forwarding) |
| Produces | `noah/api/photo.py`, `check_photo` agent tool |

## Goal
A resident texts a street photo. Gemini vision estimates a **coarse water-depth bucket** against a visible reference object. A confirmed-water report can only make that segment's state **more** conservative. Strengthens the Gemini challenge story. (Mercedes CV is dropped, so there's no CV-prize pressure.)

## Non-goals
Depth in centimetres. Downgrading a forecast ("photo shows dry, so it's fine" is **never** allowed). Storing photos. Moderation beyond Gemini's defaults.

## Inputs
`image_b64` from `/chat`, plus a location: the sender's last geocoded place, or ask "where was this taken?".

## Outputs
Tool result `{"bucket": "none|curb|half_tire|door_sill_or_above|cant_tell", "reference_object": str|null, "confidence": "low|med|high", "note": str}` and, if the bucket ≥ `curb`, an in-memory override: nearest C5/C4 segment within 100 m → state `flooded` from now on for this server session.

## Behavior
0. Expose the classifier as a pure-ish function `classify(image_bytes: bytes) -> dict` in `photo.py`. Spec 013 reuses it on traffic-camera frames, so build it once.
1. Gemini call with structured output (JSON schema = the dict above) and a prompt asking for the reference object first (curb, tire, car door, stop-sign post), then the bucket. `cant_tell` is the default when there's no reference object.
2. Override rule: only upgrades (`no_forecast_flooding|uncertain → flooded`). Never downgrades. Log every override.
3. Reply wording: "Thanks. Your photo shows water around {reference} level. I've marked {road} as **do not cross**." For `none` / `cant_tell`: "Thanks. I can't confirm water depth from this photo; my forecast for {road} stays {state}."

## Acceptance criteria
- [ ] Gather 6 test photos with clear licenses (CC / public-domain / our own), listed with sources in `README.md` Disclosures. Each returns a bucket. Print the table in PROGRESS: expected vs got.
- [ ] A `curl /chat` with a flooded-car photo near a forecast-clear segment → that segment shows as flooded in a subsequent `/status`.
- [ ] A dry-road photo near a forecast-flooded segment → the state is **unchanged**.

## Test
`tests/test_photo.py`: the override function upgrades and never downgrades (pure function on a dict).

## Fallback
Cut it. Mention it as "next" in the pitch.
