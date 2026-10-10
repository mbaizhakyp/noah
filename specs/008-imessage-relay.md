# 008 — iMessage relay (Photon Spectrum)

| | |
|---|---|
| Owner | **Margulan** (moved from Priyanshu Sat 01:20, J14) |
| Status | **Done (Sat 04:15): Phase 0 echo + Phase 1 real answers from `/chat` over iMessage, verified on Margulan's iPhone** |
| Time box | 2 h (Fri night, go/no-go at 00:00) |
| Depends on | Photon account + iMessage line (B3); `/chat` (007). An echo works without it. |
| Produces | `bot/index.ts`, `bot/package.json` |

## Goal
A text to Noah's iMessage line reaches `POST /chat`, and the reply comes back to the same conversation. Text only: user photos were removed from scope (Fri Oct 9). Required for the Photon "Agents in iMessage" challenge, which **must use the Spectrum SDK**.

## Non-goals
Any agent logic in TypeScript, group chats, rich cards, other platforms (Spectrum supports them; we don't need them).

## Inputs
- Photon Spectrum SDK (`spectrum-ts`, MIT, TypeScript) plus Photon's docs at photon.codes/docs. **The SDK API is unverified. Read the current docs and quickstart before writing code, and record the exact package name, version and auth setup in this spec's "Discovered" section.**
- Env: `PHOTON_*` credentials (names per their docs) and `API_BASE` (default `http://localhost:8000`).

## Outputs
A running relay: `cd bot && npx tsx index.ts`.

## Behavior
1. **Phase 0: echo (first, before 007 exists).** On an incoming message, reply `"echo: " + text`. Test from a real iPhone. This is the go/no-go.
2. **Phase 1: relay.** On an incoming message, `POST {API_BASE}/chat` with `{sender: <stable sender id from Spectrum>, text, image_b64: null}`. Ignore attachments. Send `reply` back.
3. Timeouts: if `/chat` takes more than 25 s or fails, send the error template from `02-ARCHITECTURE.md` §5 (duplicate that one string in TS; it's the only logic allowed here).
4. Log one line per message: sender hash, text length, latency. Never log message content in full.
5. Prefer Spectrum Cloud's managed iMessage line (no Mac relay needed, reportedly). Use self-hosted `imessage-kit` only if the managed line isn't available (B3).

## Discovered (Sat 02:20)
- Package **`spectrum-ts` 12.10.1** (MIT, photon-hq/spectrum-ts) + `@spectrum-ts/terminal` for local testing. Runs on **Node 22 with `--experimental-strip-types`** (no tsx/build step).
- Credentials: **Spectrum Cloud** project at **app.photon.codes** → `projectId` + `projectSecret` (README: "credentials ready in minutes"). Env names (as Photon's dashboard labels them): **`SPECTRUM_PROJECT_ID`, `SPECTRUM_PROJECT_SECRET`** (also accepts `PHOTON_PROJECT_*` / `PROJECT_*`). The SDK takes both or none; none = local providers only.
- API: `const app = await Spectrum({projectId, projectSecret, providers: [imessage.config()]})`; `for await (const [space, message] of app.messages)`; text = `message.content.text` when `message.content.type === "text"`; sender = `message.sender?.id`; reply = `message.reply(text)` inside `space.responding(...)` (typing indicator).
- `bot/index.ts` + `bot/relay.ts`: `BOT_MODE=auto` (default) relays to `POST {API_BASE}/chat` and **echoes while `/chat` returns 404** (007 not built yet), so it switches by itself when 007 lands; any failure or > 25 s → §5 error template. Logs: sender hash, length, path, latency only.
- Tested: 4 unit tests (`npm test`), type-check clean, SDK imports, missing-creds exit, terminal mode boots ("Spectrum started… providers: terminal").

## Acceptance criteria
- [ ] Phase 0: a screenshot of the echo on a real iPhone, noted in PROGRESS **by 00:00 Sat**.
- [ ] Phase 1: a real text "is Northside Drive flooding?" gets the agent's reply in under 15 s.
- [ ] Killing the API → the user gets the error template, not silence.

## Test
None. It's I/O glue. The manual acceptance checks above are the test.

## Fallback
B3: `imessage-kit` on a team Mac with a spare Apple ID → Twilio SMS (drop the Photon challenge; Gemini stays).
