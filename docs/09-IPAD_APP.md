# 09 — Noah for iPad: design plan

_Draft, Sat Oct 10 2026, 12:45 PM ET (Priyanshu + Claude). This is the design brief, not a spec: code waits for spec 021 with `Status: Approved`._

Reference sketch (the chosen composition): `.impeccable/mocks/decision/ipad-headline.html` (1180 × 820, warm paper).
Rejected along the way (too hard to read): calendar day view, departure dial, cut-off chart, transit-line strip, sidebar split. **Lesson: one plain sentence beats any chart.**

## 1. Job and audience
- **What it is:** a home-screen web app on the iPad. It runs the same frozen-run data as `/demo`, with one screen that answers one question per place.
- **Who holds it:** judges on Sunday, either handed the iPad or watching Priyanshu drive it. They get no explanation and have a few seconds.
- **Mode:** Operate. Legibility, big targets, and nothing to decode.
- **Success:** within 5 seconds a judge can repeat back *"Leave by 3:25 AM to reach all 6 stops before their streets flood"* and name the stop that goes first (Woodward Way, 2 AM).

## 2. Data truth
| What | Source | Shown as |
|---|---|---|
| Roads, trips, leave-by, stop states, past 18 h | `/demo` snapshot (`web/demo/snapshot/`, run `20240926T22Z`, clock 7:00 PM) | The app's normal state. Nothing labels it as frozen. |
| Live checks (signals, sources, AI assessment) | Recorded snapshot answers | Labeled **Live**, per Priyanshu's call |
| Camera frames | **Fetched live** from Windy at view time | "Live" with the fetch time |
| Camera AI verdict | Recorded check | Shown **with its own check time**, never as a verdict on the live frame |

**Hard rules**
- No user-facing "demo", "replay", "locked", "snapshot", "Helene" or "Isaias". `grep -i` the built page as in spec 020.
- The **forecast issue time stays truthful**: "Forecast issued Thu 6:00 PM" (spec 020 decision). Never stamp it as today.
- §5 vocabulary only, with no banned words. "Go before" carries "Not a safety guarantee." in the stop detail. Any danger text carries *Turn Around Don't Drown* and 911.
- "Webcams provided by Windy.com" sits on every camera view. Base-map attribution stays visible.

## 3. Visual world: warm paper
| Token | Value | Job |
|---|---|---|
| `--paper` | `#faf7f2` | App ground, top bar, stop list |
| `--sand` | `#efe8dc` | Map land, pressed rows |
| `--line` | `#e7dfd2` | Hairlines between rows |
| `--ink` | `#1c1a17` | Text, **banner**, **route line**, stop number discs |
| `--ink-2` / `--ink-3` | `#4f4a42` / `#857d70` | Secondary and tertiary text |
| `--accent` | `#c2410c` burnt orange | **Controls only:** "Leaving …" button, selected states, the Noah word mark, depot pin |
| `--flood` | `#d92d20` | Do not cross (roads, pills) |
| `--amber` / `--amber-ink` | `#f2a100` / `#8a5100` | Uncertain roads / "Go before …" text |
| water | `#bfd3d6` | Creeks on the map |

- **Orange never marks a road or a stop state.** It sits next to amber, so it's kept off anything that means danger.
- Hazards always pair color with words (and dashes for uncertain map lines). Never color alone.
- **Type:** Overpass, the existing map font and a highway-sign face. Banner 58/900, tight tracking. Stop names 19/800. Status 18/900. Body 18/600. Meta 14/600. Tabular numerals on every time.
- **Shape:** 12–16 px radii, flat surfaces, one soft shadow for floating map chips only.
- **Map:** MapLibre with a warm custom style (sand land, muted water, white streets, peach arterials). Route in ink with a paper casing. Numbered ink stop discs. Red and amber flagged roads.

## 4. The screen (landscape 1180 × 820 first, scales to 1366 × 1024)
```
┌ top bar 76 ───────────────────────────────────────────────────────────┐
│ Noah   [ Home | Work | Delivery ]                    ● Live · 3 cameras │
├ banner 150 (ink) ─────────────────────────────────────────────────────┤
│ Leave by 3:25 AM   to reach all 6 stops before         [Leaving 7:00 PM ▾] │
│                    their streets flood.                                 │
├ map 60% ─────────────────────────────┬ stops 40% ──────────────────────┤
│ route, numbered stops, flagged roads │ YOUR STOPS                         │
│                                      │ ① Woodward Way NW   Go before 2 AM │
│                                      │ ② Hanover West Ct   Go before 7 AM │
│ [Forecast issued Thu 6:00 PM]        │ … 80 px rows                       │
└──────────────────────────────────────┴───────────────────────────────────┘
```
- **Portrait** (820 × 1180): banner, then the map (45% height), then the stop list below it. Same order, same parts.
- **The banner is the product.** It's always one sentence built from the API answer, never a number on its own.
  - Delivery: "Leave by {leave_by} to reach all {n} stops before their streets flood."
  - Partial: "Leaving at {t}, you reach {k} of {n} stops." and the "Best order" action appears in the list header.
  - Home: area status in §5 words ("Do not cross {road} from {time}." plus a count of the rest), built from the recorded `/status` + `/assess` answers. Wording is settled at build time from real answers, never invented.
  - Work: the route sentence, built from `/route` + `/trip`.
- **Stop list** (by stop number, matching the map discs): number disc, street, status word on the right. Statuses: `Go before {t}` (amber-ink), `Do not cross` (red pill, when already cut at arrival), `No forecast flooding` (ink-2). A stop that can't be reached shows a red ✕ disc and "Can't reach before its street floods."

## 5. Interactions
1. **Place switch** (segmented, top bar): swaps banner, map and list with one crossfade (200 ms). The map flies to the new extent.
2. **"Leaving 7:00 PM ▾"**: opens a popover anchored to the button: one large slider (7 PM → 1 PM, 5-min steps, 44 px thumb), hour ticks, and a "Now" reset. Dragging updates the banner and rows live from recorded `/trip` answers (nearest step). **Signature move:** a row whose status changes keeps an orange-edged highlight until it's tapped, and rows never reorder. You see what changed, in place.
3. **Tap a stop row**: the map flies to that stop, and the row expands in place. It shows the reason line ("Street may flood at 2 AM, do not cross from 3 AM"), arrival time, "Not a safety guarantee." and the nearest camera thumbnail if there is one.
4. **Tap a map road**: popover with the §5 line for that road and its time.
5. **"● Live · 3 cameras"**: a right-side sheet (420 px) with tabs **Cameras / Live checks / Last 18 h**.
   - Cameras: large live frame, name, "Live · fetched 12:41 PM", then the recorded AI check line with its own time and the Windy credit.
   - Live checks: sources with their findings, as on the map's Sources tab.
   - Last 18 h: past replay for the current place.
6. **Best order** (Delivery, when it helps): a text button in the list header, "Best order: leave by 3:35 AM". Tapping it renumbers the stops and the map.

## 6. States
| State | What the screen does |
|---|---|
| Launch | Opens straight on **Delivery** (the story) with the route drawn. No location prompt. |
| Loading a place | Banner keeps its height and reads "Checking roads…". List rows show as quiet bars, never spinners. |
| Departure not recorded | The nearest recorded step answers, as `/demo` does now (`snapLookup`). |
| Camera frame fails | Frame slot says "Camera not responding". Its recorded check still shows with its time. |
| Offline | Everything except camera frames still works (all files). Cameras show the failure state above. |
| Fewer / more stops | 1–9 stops. Past 6, the list scrolls inside its column and the banner never moves. |

## 7. Build constraints
- **Delivery:** `web/ipad/index.html`, served by FastAPI at `/ipad/`, one static file like the map. MapLibre via pinned CDN, no build step. Reuses the snapshot `fetch` wrapper and clock from `web/index.html` (spec 020).
- **Home-screen app:** `manifest.webmanifest` (`display: standalone`, landscape orientation, warm-paper `theme_color`), `apple-mobile-web-app-capable`, status-bar style `default`, 180 px icon (ink "N" on paper). Viewport `viewport-fit=cover` with safe-area padding.
- **Live cameras:** a small endpoint returns a fresh Windy image URL per `cam_id` (key stays server-side). It's the only live call the app makes besides the static files.
- **Reach on Sunday:** the iPad must reach the server. Use the laptop's LAN IP on the same Wi-Fi, or a tunnel. Decide before Sat 22:00.
- **Touch:** every target ≥ 56 px. No hover-only affordances. No text under 14 px.
- **Owner:** Priyanshu (`web/`, `noah/api/`). Feature freeze Sun 00:00.

## 8. Open decisions (humans, not the builder)
- Spec 021 to write and approve (scope = this doc). Time box suggestion: 3 h.
- Should the "Live" label on recorded checks also show each check's recorded time? This plan already shows it for camera verdicts. Doing the same for checks is the conservative choice.
- Network path for Sunday: LAN IP vs tunnel.
