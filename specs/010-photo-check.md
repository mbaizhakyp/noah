# 010 — Water classifier for camera frames (`classify()`)

| | |
|---|---|
| Owner | Priyanshu |
| Status | Draft (P2: start after the Sat 14:00 E2E milestone; unblocks 013 step 2) |
| Time box | 1.5 h |
| Depends on | Azure OpenAI (`AZURE_OPENAI_*` in `.env`, deployment `gpt-4.1-mini`; image input verified on a live Windy snapshot Sat 01:45). Replaces Gemini (J11). |
| Produces | `noah/api/photo.py` (`classify()`, `apply_override()`) |

> **Scope change (Priyanshu, Fri Oct 9 ~21:45 ET): user-submitted photos are removed.** We can't expect people to take photos in the rain, so there is no `check_photo` agent tool and no photo intake over iMessage. This spec now builds only the classifier, which spec 013 runs on traffic-camera frames. The file name stays `010-photo-check.md` so existing links keep working.

## Goal
Given one image (a traffic-camera frame), Gemini vision estimates a **coarse water-depth bucket** against a visible reference object. A confirmed-water result can only make nearby segments **more** conservative (applied by 013).

## Non-goals
User photos. Depth in centimetres. Downgrading a forecast ("frame shows dry, so it's fine" is **never** allowed). Storing images beyond 013's local capture folder.

## Inputs
`image_bytes: bytes` (JPEG from `data/raw/cctv/`, spec 013).

## Outputs
`{"bucket": "none|curb|half_tire|door_sill_or_above|cant_tell", "reference_object": str|null, "confidence": "low|med|high", "note": str}`

## Behavior
1. `classify(image_bytes: bytes) -> dict` in `photo.py`: one Gemini call with structured output (JSON schema = the dict above). The prompt asks for the reference object first (curb, tire, car door, sign post, lane marking), then the bucket. `cant_tell` is the default when there's no reference object, the frame is dark or the camera is blocked.
2. `apply_override(states: dict, seg_ids: list, bucket: str) -> dict`: pure function. Upgrades `no_forecast_flooding|uncertain → flooded` when `bucket ≥ curb`. Never downgrades. 013 calls it for segments within 100 m of the camera and logs every override.

## Acceptance criteria
- [ ] 6 test images with clear licenses (Windy webcam frames checked live and not stored, or CC / public-domain / our own), sources listed in `README.md` Disclosures. Each returns a valid dict. Print the table in PROGRESS: expected vs got.
- [ ] At least one wet image returns `bucket ≥ curb`, and at least one dry image returns `none` or `cant_tell`.

## Test
`tests/test_photo.py`: `apply_override` upgrades and never downgrades (pure function on a dict).

## Fallback
013 shows raw frames labeled "camera view" without assessments.
