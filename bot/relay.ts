// Spec 008: relay logic (pure, testable). The only "logic" allowed in bot/ is this glue + one error string.
import { createHash } from "node:crypto";

// 02-ARCHITECTURE §5 error template (duplicated here on purpose, spec 008).
export const ERROR_REPLY =
  "I can't confirm conditions right now, so treat low roads near creeks as impassable. In an emergency call 911.";

export type Mode = "auto" | "echo" | "chat";

export interface ReplyOptions {
  mode: Mode;
  apiBase: string;
  timeoutMs?: number;
  fetchFn?: typeof fetch;
}

/** Text of an inbound Spectrum message content, or null for non-text (attachments, reactions...). */
export function textOf(content: { type: string; text?: string } | undefined): string | null {
  return content?.type === "text" && typeof content.text === "string" && content.text.trim()
    ? content.text.trim()
    : null;
}

/** Short stable hash of the sender id for logs (never log numbers or message text). */
export function senderHash(id: string | undefined): string {
  return createHash("sha256").update(id ?? "unknown").digest("hex").slice(0, 8);
}

/**
 * Reply for one inbound text.
 * - echo: "echo: <text>" (Phase 0 go/no-go).
 * - chat: POST {apiBase}/chat {sender, text, image_b64: null} -> reply (C9).
 * - auto: chat, but echo while /chat doesn't exist yet (404/405), so the relay switches by itself when 007 lands.
 * Any other failure or a slow agent (> timeout) -> ERROR_REPLY, never silence.
 */
export async function replyFor(
  text: string,
  sender: string,
  { mode, apiBase, timeoutMs = 25_000, fetchFn = fetch }: ReplyOptions,
): Promise<{ reply: string; via: "echo" | "chat" | "error" }> {
  if (mode === "echo") return { reply: `echo: ${text}`, via: "echo" };
  try {
    const res = await fetchFn(`${apiBase.replace(/\/$/, "")}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sender, text, image_b64: null }),
      signal: AbortSignal.timeout(timeoutMs),
    });
    // 404/405: no /chat route yet (app.py mounts static files at "/", so a missing POST route is 405).
    if ((res.status === 404 || res.status === 405) && mode === "auto") return { reply: `echo: ${text}`, via: "echo" };
    if (!res.ok) return { reply: ERROR_REPLY, via: "error" };
    const data = (await res.json()) as { reply?: unknown };
    return typeof data.reply === "string" && data.reply.trim()
      ? { reply: data.reply, via: "chat" }
      : { reply: ERROR_REPLY, via: "error" };
  } catch {
    return { reply: ERROR_REPLY, via: "error" };
  }
}
