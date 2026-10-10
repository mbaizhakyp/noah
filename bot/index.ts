// Spec 008: Noah's iMessage relay (Photon Spectrum). Text in -> POST /chat -> reply out. No agent logic here.
//
//   npm start         iMessage via Spectrum Cloud (needs PHOTON_PROJECT_ID / PHOTON_PROJECT_SECRET in ../.env)
//   npm run local     terminal chat window for local testing (no iMessage needed)
//
// Env (../.env): PHOTON_PROJECT_ID, PHOTON_PROJECT_SECRET, API_BASE (default http://localhost:8000),
//                BOT_MODE = auto (default: relay to /chat, echo while /chat doesn't exist) | echo | chat
import { config as loadEnv } from "dotenv";
import { Spectrum } from "spectrum-ts";
import { type Mode, replyFor, senderHash, textOf } from "./relay.ts";

loadEnv({ path: new URL("../.env", import.meta.url).pathname, quiet: true });

const local = process.argv.includes("--terminal");
const mode = (process.env.BOT_MODE ?? "auto") as Mode;
const apiBase = process.env.API_BASE || "http://localhost:8000";
const projectId = process.env.PHOTON_PROJECT_ID ?? process.env.PROJECT_ID;
const projectSecret = process.env.PHOTON_PROJECT_SECRET ?? process.env.PROJECT_SECRET;

if (!local && (!projectId || !projectSecret)) {
  console.error("PHOTON_PROJECT_ID / PHOTON_PROJECT_SECRET missing in .env (get them at app.photon.codes), or run: npm run local");
  process.exit(1);
}

const provider = local
  ? (await import("spectrum-ts/providers/terminal")).terminal.config()
  : (await import("spectrum-ts/providers/imessage")).imessage.config();

// The SDK takes both cloud credentials or none (none = local providers only, e.g. the terminal).
const app =
  projectId && projectSecret
    ? await Spectrum({ projectId, projectSecret, providers: [provider] })
    : await Spectrum({ providers: [provider] });
console.error(`noah relay up: ${local ? "terminal" : "iMessage"}, mode=${mode}, api=${apiBase}`);

for await (const [space, message] of app.messages) {
  if (message.direction !== "inbound") continue;
  const text = textOf(message.content as { type: string; text?: string });
  if (!text) continue; // text only (user photos are out of scope, Fri Oct 9)
  const t0 = Date.now();
  const sender = message.sender?.id ?? "unknown";
  const { reply, via } = await space.responding(async () => {
    const r = await replyFor(text, sender, { mode, apiBase });
    await message.reply(r.reply);
    return r;
  });
  // One line per message: sender hash, text length, latency, path. Never the content or the number.
  console.error(`msg from=${senderHash(sender)} len=${text.length} via=${via} ms=${Date.now() - t0} out=${reply.length}`);
}
