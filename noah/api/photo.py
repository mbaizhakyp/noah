"""Spec 010: water-on-road check for one traffic-camera snapshot (Azure OpenAI vision).

The model sees the image through its live URL; nothing is downloaded or stored here.
Output buckets are coarse on purpose (02 §5): none | curb | half_tire | door_sill_or_above | cant_tell.
"""

import json
import os

import httpx

BUCKETS = ("none", "curb", "half_tire", "door_sill_or_above", "cant_tell")
WET = ("curb", "half_tire", "door_sill_or_above")
PROMPT = """You check one traffic-camera image for standing or flowing water ON THE ROAD surface.
First find a reference object (curb, tire, car door, lane marking, sign post). Then pick the depth bucket:
- "none": road visible, no standing/flowing water on the travel lanes (wet pavement or rain alone is "none")
- "curb": water reaching the curb or covering part of a lane
- "half_tire": water around half a tire high or covering lanes
- "door_sill_or_above": water at a car's door sill or higher
- "cant_tell": dark, blurry, blocked, no road visible, or no reference object
Rain-wet pavement, shine, and reflections of street lights or headlights are NOT standing water (use "none").
At night or in low light, report water only if you see a clear water surface: an edge where water meets dry road,
ripples, splashing, or a lane visibly covered; otherwise use "none" or "cant_tell".
Only report what is visible. Reply as JSON:
{"bucket": "...", "reference_object": str or null, "confidence": "low|med|high", "note": "max 15 words",
 "label": "the location text printed on the image (e.g. a camera name or street names), copied exactly; null if no text is readable. Never guess a label."}"""


SKEPTIC = """
You are the second reviewer. Another check reported water on this road. Be skeptical: confirm only if the
water surface is unmistakable. If it could just be wet pavement or reflections, answer "none"."""


def classify_url(image_url: str, detail: str = "low", skeptic: bool = False) -> dict:
    """Image URL -> {bucket, reference_object, confidence, note}. Never raises: failures -> cant_tell."""
    try:
        ep = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
        dep = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
        r = httpx.post(
            f"{ep}/openai/deployments/{dep}/chat/completions",
            params={"api-version": "2024-10-21"},
            headers={"api-key": os.environ["AZURE_OPENAI_API_KEY"]},
            timeout=25,
            json={
                "temperature": 0,
                "max_tokens": 120,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": PROMPT + (SKEPTIC if skeptic else "")},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Check this traffic camera image."},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url, "detail": detail},
                            },
                        ],
                    },
                ],
            },
        )
        r.raise_for_status()
        out = json.loads(r.json()["choices"][0]["message"]["content"])
    except Exception as e:  # noqa: BLE001 (a camera must never block the answer)
        return {
            "bucket": "cant_tell",
            "reference_object": None,
            "confidence": "low",
            "note": f"check failed: {type(e).__name__}",
        }
    if out.get("bucket") not in BUCKETS:
        out["bucket"] = "cant_tell"
    if out.get("confidence") not in ("low", "med", "high"):
        out["confidence"] = "low"
    return out


def blank_feed(image_url: str) -> bool:
    """True if the camera image is flat (feed down / placeholder). Checked in memory; nothing is stored."""
    try:
        from io import BytesIO

        from PIL import Image, ImageStat

        img = Image.open(BytesIO(httpx.get(image_url, timeout=10).content)).convert("L")
        return ImageStat.Stat(img).stddev[0] < 4
    except Exception:  # noqa: BLE001 (if we can't tell, let the AI check decide)
        return False


def verified(image_url: str) -> dict:
    """Two-step check. Water must be seen twice (second look: high detail, skeptical) to count as confirmed."""
    if blank_feed(image_url):
        return {
            "bucket": "cant_tell",
            "reference_object": None,
            "confidence": "high",
            "note": "camera feed unavailable (blank image)",
            "label": None,
            "verified": None,
            "blank": True,
        }
    first = classify_url(image_url)
    if first["bucket"] not in WET:
        return {**first, "verified": None}
    second = classify_url(image_url, detail="high", skeptic=True)
    if second["bucket"] in WET:
        order = list(BUCKETS)
        bucket = min(first["bucket"], second["bucket"], key=order.index)  # agree on the lower depth
        return {
            **second,
            "bucket": bucket,
            "verified": True,
            "label": first.get("label") or second.get("label"),
        }
    return {
        **first,
        "verified": False,
        "note": f"possible water, not confirmed on a second look ({second.get('note') or second['bucket']})",
    }


def apply_override(states: dict, seg_ids: list[str], bucket: str) -> dict:
    """Camera water can only upgrade nearby segments to flooded; it never clears a forecast."""
    if bucket in WET:
        for s in seg_ids:
            states[s] = "flooded"
    return states
