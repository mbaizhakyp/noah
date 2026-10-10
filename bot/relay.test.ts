import assert from "node:assert/strict";
import { test } from "node:test";
import { ERROR_REPLY, replyFor, senderHash, textOf } from "./relay.ts";

const fakeFetch = (status: number, body: unknown, delayMs = 0) =>
  (async (_url: string, init?: RequestInit) => {
    await new Promise((r, j) => {
      const t = setTimeout(r, delayMs);
      init?.signal?.addEventListener("abort", () => (clearTimeout(t), j(new Error("aborted"))));
    });
    return new Response(JSON.stringify(body), { status });
  }) as unknown as typeof fetch;

test("echo mode", async () => {
  assert.deepEqual(await replyFor("hi", "u", { mode: "echo", apiBase: "x" }), { reply: "echo: hi", via: "echo" });
});

test("auto: relays to /chat when it exists, echoes on 404", async () => {
  const ok = await replyFor("is Northside flooding?", "u", { mode: "auto", apiBase: "http://a", fetchFn: fakeFetch(200, { reply: "Do not cross Northside Dr." }) });
  assert.deepEqual(ok, { reply: "Do not cross Northside Dr.", via: "chat" });
  for (const status of [404, 405]) {
    const missing = await replyFor("hi", "u", { mode: "auto", apiBase: "http://a", fetchFn: fakeFetch(status, {}) });
    assert.deepEqual(missing, { reply: "echo: hi", via: "echo" });
  }
});

test("failures and slow agent -> error template, never silence", async () => {
  for (const f of [fakeFetch(500, {}), fakeFetch(200, { reply: "" }), fakeFetch(404, {})]) {
    const r = await replyFor("hi", "u", { mode: "chat", apiBase: "http://a", fetchFn: f });
    assert.equal(r.reply, ERROR_REPLY);
  }
  const slow = await replyFor("hi", "u", { mode: "chat", apiBase: "http://a", timeoutMs: 50, fetchFn: fakeFetch(200, { reply: "late" }, 500) });
  assert.equal(slow.reply, ERROR_REPLY);
});

test("textOf and senderHash", () => {
  assert.equal(textOf({ type: "text", text: "  hello " }), "hello");
  assert.equal(textOf({ type: "attachment" }), null);
  assert.equal(textOf({ type: "text", text: "   " }), null);
  assert.equal(senderHash("+14045551234").length, 8);
  assert.notEqual(senderHash("a"), senderHash("b"));
});
