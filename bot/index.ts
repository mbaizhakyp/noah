// Spec 008: Noah's iMessage relay (Photon Spectrum). Text in -> POST /chat -> reply out. No agent logic here.
//
//   npm start         iMessage via Spectrum Cloud (needs SPECTRUM_PROJECT_ID / SPECTRUM_PROJECT_SECRET in ../.env)
//   npm run local     terminal chat window for local testing (no iMessage needed)
//
// Spec 017: "alerts on" / "alerts off" subscribes a thread to route-watch alerts. Python (noah.pipeline.route_watch)
// queues them in data/interim/outbox.jsonl; new lines go to every subscribed thread (photo attached when there is one).
//
// Env (../.env): SPECTRUM_PROJECT_ID, SPECTRUM_PROJECT_SECRET, API_BASE (default http://localhost:8000),
//                BOT_MODE = auto (default: relay to /chat, echo while /chat doesn't exist) | echo | chat
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { basename } from "node:path";
import { fileURLToPath } from "node:url";
import { config as loadEnv } from "dotenv";
import { attachment, group, type Space, Spectrum } from "spectrum-ts";
import { alertCommand, type Mode, type Photo, photoKey, replyFor, senderHash, textOf } from "./relay.ts";

// fileURLToPath, not URL.pathname: the latter keeps %20 for spaces ("Application Support") and misses the file.
loadEnv({ path: fileURLToPath(new URL("../.env", import.meta.url)), quiet: true });

const local = process.argv.includes("--terminal");
const mode = (process.env.BOT_MODE ?? "auto") as Mode;
const apiBase = process.env.API_BASE || "http://localhost:8000";
const env = (...names: string[]) => names.map((n) => process.env[n]?.trim()).find(Boolean);
const projectId = env("SPECTRUM_PROJECT_ID", "PHOTON_PROJECT_ID", "PROJECT_ID");
const projectSecret = env("SPECTRUM_PROJECT_SECRET", "PHOTON_PROJECT_SECRET", "PROJECT_SECRET");

if (!local && (!projectId || !projectSecret)) {
  console.error("SPECTRUM_PROJECT_ID / SPECTRUM_PROJECT_SECRET missing in .env (get them at app.photon.codes), or run: npm run local");
  process.exit(1);
}

const platform = local
  ? (await import("spectrum-ts/providers/terminal")).terminal
  : (await import("spectrum-ts/providers/imessage")).imessage;
const provider = platform.config();

// The SDK takes both cloud credentials or none (none = local providers only, e.g. the terminal).
const app =
  projectId && projectSecret
    ? await Spectrum({ projectId, projectSecret, providers: [provider] })
    : await Spectrum({ providers: [provider] });
console.error(`noah relay up: ${local ? "terminal" : "iMessage"}, mode=${mode}, api=${apiBase}`);

// ---- spec 017: route-watch alerts (Noah texts first) ----
const interim = (f: string) => fileURLToPath(new URL(`../data/interim/${f}`, import.meta.url));
const readText = (f: string) => (existsSync(interim(f)) ? readFileSync(interim(f), "utf8") : "");
const subs = new Set<string>(JSON.parse(readText("alert_spaces.json") || "[]")); // thread ids, survive restarts
const saveSubs = () => writeFileSync(interim("alert_spaces.json"), JSON.stringify([...subs]));
const threads = new Map<string, Space>(); // live handles from inbound messages
const outbox = () => readText("outbox.jsonl").split("\n").filter(Boolean);
let sent = Number(readText("outbox.offset") || outbox().length); // first start: skip the backlog
writeFileSync(interim("outbox.offset"), String(sent));
let flushing = false;

async function threadFor(id: string): Promise<Space | undefined> {
  if (!threads.has(id)) threads.set(id, await platform(app).space.get(id)); // after a restart
  return threads.get(id);
}

async function flushOutbox() {
  if (flushing) return;
  flushing = true;
  try {
    const lines = outbox();
    for (; sent < lines.length; sent++) {
      const item = JSON.parse(lines[sent]) as { text: string; image?: string | null };
      for (const id of subs) {
        try {
          const thread = await threadFor(id);
          if (!thread) continue;
          if (item.image && existsSync(item.image)) {
            const photo = attachment(readFileSync(item.image), { name: basename(item.image), mimeType: "image/png" });
            await thread.send(item.text, photo);
          } else await thread.send(item.text);
          console.error(`alert to=${senderHash(id)} len=${item.text.length} photo=${Boolean(item.image)}`);
        } catch (e) {
          console.error(`alert send failed to=${senderHash(id)}: ${(e as Error).message}`);
        }
      }
      writeFileSync(interim("outbox.offset"), String(sent + 1));
    }
  } finally {
    flushing = false;
  }
}
setInterval(() => void flushOutbox(), 20_000);

// J32: live camera frames as one album, then a numbered key. Held in memory only (Windy frames are never stored).
async function sendPhotos(space: Space, photos: Photo[]) {
  const got: { att: ReturnType<typeof attachment>; caption: string }[] = [];
  for (const [i, p] of photos.entries()) {
    try {
      const res = await fetch(p.url, { signal: AbortSignal.timeout(10_000) });
      if (!res.ok) continue;
      const mimeType = res.headers.get("content-type") ?? "image/jpeg";
      got.push({ att: attachment(Buffer.from(await res.arrayBuffer()), { name: `camera-${i + 1}.jpg`, mimeType }), caption: p.caption });
    } catch {
      // one camera failing must not block the others
    }
  }
  if (!got.length) return;
  try {
    if (got.length >= 2) await space.send(group(...(got.map((g) => g.att) as Parameters<typeof group>)));
    else await space.send(got[0].att);
  } catch (e) {
    console.error(`album send failed, sending one by one: ${(e as Error).message}`);
    for (const g of got) await space.send(g.att);
  }
  await space.send(photoKey(got.map((g) => g.caption)));
}

for await (const [space, message] of app.messages) {
  if (message.direction !== "inbound") continue;
  const text = textOf(message.content as { type: string; text?: string });
  if (!text) continue; // text only (user photos are out of scope, Fri Oct 9)
  const t0 = Date.now();
  const sender = message.sender?.id ?? "unknown";
  threads.set(space.id, space);
  const cmd = alertCommand(text);
  if (cmd) {
    if (cmd === "on") subs.add(space.id);
    else subs.delete(space.id);
    saveSubs();
    const latest = readText("route_watch_latest.txt");
    const reply =
      cmd === "on"
        ? `Route watch alerts on: I'll text you when a watched route's forecast changes or a camera on it sees water. Text "alerts off" to stop.${latest ? `\n\n${latest}` : ""}`
        : "Route watch alerts off.";
    await space.responding(() => message.reply(reply));
    console.error(`alerts ${cmd} from=${senderHash(sender)}`);
    continue;
  }
  const { reply, via, photos } = await space.responding(async () => {
    const r = await replyFor(text, sender, { mode, apiBase });
    await message.reply(r.reply);
    if (r.photos?.length) await sendPhotos(space, r.photos);
    return r;
  });
  // One line per message: sender hash, text length, latency, path. Never the content or the number.
  console.error(`msg from=${senderHash(sender)} len=${text.length} via=${via} ms=${Date.now() - t0} out=${reply.length} photos=${photos?.length ?? 0}`);
}
