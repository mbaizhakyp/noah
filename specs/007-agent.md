# 007 — Gemini agent + safety filter

| | |
|---|---|
| Owner | Priyanshu |
| Status | Draft |
| Time box | 3 h |
| Depends on | 006 functions (call them in-process, not over HTTP); `GEMINI_API_KEY`, `GEMINI_MODEL` |
| Produces | C9 `POST /chat` |

## Goal
Answer plain-language questions ("can I get home tonight?", "is Northside Drive flooding?", "route me from Emory to Atlantic Station") with short, conservative, correct replies built from tool results. This is the core of both side challenges (Gemini + Photon).

## Non-goals
Long conversations, general chit-chat, any answer not grounded in a tool result, and persistence across server restarts.

## Inputs
`POST /chat {"sender","text","image_b64"}`.

## Outputs
`{"reply": str}`. Plain text, ≤ 480 characters, at most one URL (the map link).

## Behavior
1. **SDK:** `google-genai` (`from google import genai`), with the client created once. Model from `GEMINI_MODEL` (R6). Use the SDK's function calling with plain Python functions as tools (automatic function calling, **(verify)** in the installed SDK version).
2. **Tools** (thin wrappers over 006 logic):
   - `geocode(place: str) -> {lat, lon, display_name} | {error}`: Nominatim, Georgia viewbox + `bounded=1`, cached in a dict, User-Agent per R7, 1 req/s.
   - `flood_status(lat: float, lon: float, hours: int = 18)` → same as `/status`.
   - `route(from_lat, from_lon, to_lat, to_lon, depart_in_hours: int = 0)` → same as `/route`.
   - `set_home(place: str)` / `get_home()`: a per-sender in-memory dict.
3. **Session:** a per-sender chat history in memory (last 10 turns).
4. **System prompt** (keep it in `agent.py` as one constant). It must include:
   - You are Noah, a flood-road forecast assistant for the State of Georgia. Road-level timing exists only in processed basins; elsewhere in Georgia, relay official alerts and use the `no_road_forecast` wording (CC6). Replay date context: "now" is `issue_time(DEMO_CYCLE)` in America/New_York.
   - Always call tools; never guess road conditions. If home is unknown and the user asks about going home, ask for the address once and call `set_home`.
   - Use only the four states and their meaning from `docs/02-ARCHITECTURE.md` §5 (paste that table into the prompt).
   - Never say a road or route is safe, clear or passable. Prefer the more conservative state. Mention 911 when describing danger.
   - Max 480 characters, plain text, include `map_url` when a route exists.
5. **Safety filter** `enforce_safety(text) -> str`, applied to **every** outgoing reply:
   - Case-insensitive whole-word regex `\b(safe|safely|clear|passable|you're fine|no risk)\b`. If it matches, regenerate once with a correction note. If it still matches, replace the whole reply with the conservative template for the last tool state (or the error template).
   - Whole-word matching means "safety" (in the frozen "not a safety guarantee") and "unclear" pass, which is intended.
   - `# ponytail:` regex filter, not a classifier; good enough because the vocabulary is closed.
6. Any exception → the error template from §5.

## Acceptance criteria
- [ ] `curl -XPOST localhost:8000/chat -d '{"sender":"t","text":"is Northside Drive near Peachtree Creek flooding tonight?"}'` returns a reply that uses one of the four states and mentions a time.
- [ ] "my home is 1600 Peachtree Battle Ave NW, can I get home from Emory at 10pm?" → calls `set_home` + `route`. The reply contains a C10 map link or a `no_route` explanation.
- [ ] "is it safe to drive on Peachtree Rd?" → the reply never says safe or clear (filter verified).
- [ ] An address outside Georgia → the out-of-coverage message. A Georgia address in an unprocessed basin → the `no_road_forecast` message.
- [ ] "can I get from Emory to Buckhead tomorrow at this time?" (more than 18 h out) → the `beyond_forecast_window` message, with no guess.
- [ ] `uv run pytest tests/test_agent.py` passes.

## Test
`tests/test_agent.py` covers the detection part of `enforce_safety` (pure function, no Gemini call). It flags "Safe to go", "road is CLEAR", "passable."; it does not flag "This is not a safety guarantee" or "conditions are unclear".

## Fallback
If tool calling is flaky: route intent by keywords (`route`/`home`/`get to` → geocode + route; otherwise geocode + status), fill the §5 template directly, and use Gemini only to phrase the reply (then run the filter). This keeps the Gemini challenge eligible and the demo reliable.
