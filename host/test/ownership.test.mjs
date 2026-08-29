#!/usr/bin/env node
//
// Ownership tests for the browser port.
//
// These run the REAL native-host.js and the REAL tool-runtime.js against a
// fake extension and fake MCP clients, on a scratch port, so the whole
// ownership story can be exercised without Chrome and without disturbing a
// live install on :18765.
//
// The fake extension speaks Chrome's native messaging framing (4-byte LE
// length + JSON) over the host's stdio, which is the only contract the real
// extension has with the host — so a pass here means background.js would be
// equally happy, and no extension reload is involved.
//
// Run: node host/test/ownership.test.mjs

import net from "node:net";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const HOST = path.join(HERE, "..", "native-host.js");
const RUNTIME_HARNESS = path.join(HERE, "runtime-primary.mjs");

let PORT = 18900 + Math.floor(process.uptime() * 1000) % 90;
let PIPE = "";

const pipeFor = (port) =>
  process.platform === "win32"
    ? `\\\\.\\pipe\\ocic-test-${process.pid}-${port}`
    : path.join(process.env.TEMP || "/tmp", `ocic-test-${process.pid}-${port}.sock`);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// --- Fake extension: drives native-host.js exactly as Chrome would ---

function fakeExtension(port, pipe = PIPE) {
  const proc = spawn(process.execPath, [HOST], {
    env: { ...process.env, OCIC_PORT: String(port), OCIC_PIPE: pipe },
    stdio: ["pipe", "pipe", "pipe"]
  });

  const handlers = [];
  const stderr = [];
  let buf = Buffer.alloc(0);

  proc.stdout.on("data", (chunk) => {
    buf = Buffer.concat([buf, chunk]);
    while (buf.length >= 4) {
      const len = buf.readUInt32LE(0);
      if (buf.length < 4 + len) break;
      const msg = JSON.parse(buf.subarray(4, 4 + len).toString("utf-8"));
      buf = buf.subarray(4 + len);
      for (const h of handlers) h(msg);
    }
  });
  proc.stderr.on("data", (c) => stderr.push(c.toString()));

  return {
    proc,
    stderrText: () => stderr.join(""),
    onMessage: (cb) => handlers.push(cb),
    send(msg) {
      const body = Buffer.from(JSON.stringify(msg), "utf-8");
      const header = Buffer.alloc(4);
      header.writeUInt32LE(body.length, 0);
      proc.stdin.write(Buffer.concat([header, body]));
    },
    // Answer every tool_request with a result derived from the request, so a
    // client can prove it got back its OWN response and not someone else's.
    autoRespond(transform = (m) => ({ echo: m.tool, args: m.args })) {
      handlers.push((msg) => {
        if (msg.type === "tool_request") {
          this.send({ id: msg.id, result: transform(msg) });
        }
      });
    },
    kill: () => proc.kill(),
    // Close stdin the way Chrome does when the extension disconnects.
    disconnect: () => proc.stdin.end()
  };
}

// --- Fake MCP client: the wire role tool-runtime.js uses in client mode ---

// `endpoint` is a port number or a pipe/socket path — net.createConnection
// takes either, which is exactly why the pipe was a cheap swap to make.
function fakeClient(endpoint, name) {
  const socket = net.createConnection(endpoint);
  const pending = new Map();
  const received = [];
  let idc = 0;
  let buf = Buffer.alloc(0);
  let closed = false;

  socket.on("error", () => {});
  socket.on("close", () => {
    closed = true;
  });
  socket.on("data", (chunk) => {
    buf = Buffer.concat([buf, chunk]);
    let idx;
    while ((idx = buf.indexOf(10)) !== -1) {
      const line = buf.subarray(0, idx).toString("utf-8").trim();
      buf = buf.subarray(idx + 1);
      if (!line) continue;
      let msg;
      try {
        msg = JSON.parse(line);
      } catch {
        continue;
      }
      received.push(msg);
      if (msg.id && pending.has(msg.id)) {
        const { resolve } = pending.get(msg.id);
        pending.delete(msg.id);
        resolve(msg);
      }
    }
  });

  const ready = new Promise((resolve) => {
    socket.on("connect", () => {
      socket.write(JSON.stringify({ type: "client_hello" }) + "\n");
      resolve();
    });
  });

  return {
    name,
    ready,
    isClosed: () => closed,
    received,
    call(tool, args = {}, timeoutMs = 3000) {
      const id = String(++idc);
      socket.write(
        JSON.stringify({ id, type: "tool_request", tool, args }) + "\n"
      );
      return new Promise((resolve, reject) => {
        pending.set(id, { resolve });
        setTimeout(() => {
          if (pending.has(id)) {
            pending.delete(id);
            reject(new Error(`${name}: ${tool} timed out`));
          }
        }, timeoutMs);
      });
    },
    // Vanish without a FIN, the way a force-killed session's socket does.
    hardKill: () => socket.destroy(),
    close: () => socket.end()
  };
}

function portIsFree(port) {
  return new Promise((resolve) => {
    const s = net.createServer();
    s.once("error", () => resolve(false));
    s.listen(port, "127.0.0.1", () => s.close(() => resolve(true)));
  });
}

async function waitFor(fn, timeoutMs = 5000, label = "condition") {
  const start = Date.now();
  for (;;) {
    if (await fn()) return true;
    if (Date.now() - start > timeoutMs) throw new Error(`timed out: ${label}`);
    await sleep(50);
  }
}

// --- Test registry ---

const results = [];
async function test(name, fn) {
  PORT += 1; // every test gets its own address pair; no cross-test interference
  PIPE = pipeFor(PORT);
  const started = Date.now();
  try {
    await fn(PORT, PIPE);
    results.push({ name, ok: true, ms: Date.now() - started });
    console.log(`  PASS  ${name}  (${Date.now() - started}ms)`);
  } catch (err) {
    results.push({ name, ok: false, ms: Date.now() - started, err: err.message });
    console.log(`  FAIL  ${name}  — ${err.message}`);
  }
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

// ---------------------------------------------------------------------------

console.log("\nBrowser-port ownership\n");

await test("host claims a free port and reports itself as owner", async (port) => {
  const ext = fakeExtension(port);
  await waitFor(
    async () => /owns the browser port/.test(ext.stderrText()),
    5000,
    "host announces ownership"
  );
  assert(!(await portIsFree(port)), "port should be held by the host");
  ext.kill();
});

await test("a client's request reaches the extension and the reply comes back", async (port) => {
  const ext = fakeExtension(port);
  ext.autoRespond();
  await waitFor(async () => !(await portIsFree(port)), 5000, "host binds");

  const c = fakeClient(port, "c1");
  await c.ready;
  const reply = await c.call("navigate", { url: "https://example.com" });
  assert(reply.result?.echo === "navigate", `unexpected reply ${JSON.stringify(reply)}`);
  assert(reply.id === "1", `id should be de-prefixed back to the client's own, got ${reply.id}`);
  c.close();
  ext.kill();
});

await test("concurrent clients each get only their own responses", async (port) => {
  const ext = fakeExtension(port);
  // Echo the tool name back so a crossed wire is detectable.
  ext.autoRespond((m) => ({ forTool: m.tool }));
  await waitFor(async () => !(await portIsFree(port)), 5000, "host binds");

  const clients = [];
  for (let i = 0; i < 8; i++) clients.push(fakeClient(port, `c${i}`));
  await Promise.all(clients.map((c) => c.ready));

  const replies = await Promise.all(
    clients.map((c, i) => c.call(`tool_${i}`, { n: i }))
  );
  replies.forEach((r, i) => {
    assert(
      r.result?.forTool === `tool_${i}`,
      `client ${i} got a response meant for ${r.result?.forTool}`
    );
  });
  clients.forEach((c) => c.close());
  ext.kill();
});

await test("a client that vanishes mid-request does not take the hub down", async (port) => {
  const ext = fakeExtension(port);
  await waitFor(async () => !(await portIsFree(port)), 5000, "host binds");

  const survivor = fakeClient(port, "survivor");
  await survivor.ready;

  // 20 clients that connect and are destroyed without a clean close — the
  // exact shape that killed the old primary with an unhandled ECONNRESET.
  for (let i = 0; i < 20; i++) {
    const doomed = fakeClient(port, `doomed${i}`);
    doomed.call("computer", {}).catch(() => {});
    doomed.hardKill();
  }
  // Also connect-and-die without ever saying hello, inside the classify window.
  for (let i = 0; i < 20; i++) {
    const silent = net.createConnection(port, "127.0.0.1");
    silent.on("error", () => {});
    silent.on("connect", () => silent.destroy());
  }

  await sleep(400);
  assert(ext.proc.exitCode === null, "host process died");
  assert(!survivor.isClosed(), "survivor lost its connection");

  ext.autoRespond();
  const reply = await survivor.call("still_alive");
  assert(reply.result?.echo === "still_alive", "hub stopped serving after the churn");
  survivor.close();
  ext.kill();
});

await test("orphaned clients cannot block a fresh host from owning the port", async (port) => {
  // The #41 scenario: sessions died long ago but their MCP processes live on.
  // Under host-owned ownership they are only clients, so they hold nothing.
  const ext = fakeExtension(port);
  await waitFor(async () => !(await portIsFree(port)), 5000, "host binds");
  const orphans = [];
  for (let i = 0; i < 30; i++) orphans.push(fakeClient(port, `orphan${i}`));
  await Promise.all(orphans.map((o) => o.ready));

  // Browser restarts: old host goes away, a new one starts with the orphans
  // still attached and still holding their sockets open.
  ext.disconnect();
  await waitFor(async () => await portIsFree(port), 5000, "old host releases port");

  const ext2 = fakeExtension(port);
  ext2.autoRespond();
  await waitFor(
    async () => /owns the browser port/.test(ext2.stderrText()),
    5000,
    "new host claims the port despite 30 orphans"
  );

  const fresh = fakeClient(port, "fresh");
  await fresh.ready;
  const reply = await fresh.call("navigate");
  assert(reply.result?.echo === "navigate", "new host not serving");
  fresh.close();
  ext2.kill();
});

await test("host releases the port the moment the extension disconnects", async (port) => {
  const ext = fakeExtension(port);
  await waitFor(async () => !(await portIsFree(port)), 5000, "host binds");
  ext.disconnect();
  await waitFor(async () => await portIsFree(port), 5000, "port freed on disconnect");
});

await test("recording_complete fans out to every attached client", async (port) => {
  const ext = fakeExtension(port);
  await waitFor(async () => !(await portIsFree(port)), 5000, "host binds");
  const clients = [fakeClient(port, "a"), fakeClient(port, "b"), fakeClient(port, "c")];
  await Promise.all(clients.map((c) => c.ready));
  await sleep(100);

  ext.send({ type: "recording_complete", recording_id: "r1", path: "/tmp/r1" });
  await sleep(300);
  for (const c of clients) {
    assert(
      c.received.some((m) => m.type === "recording_complete" && m.recording_id === "r1"),
      `${c.name} never saw the recording event`
    );
  }
  clients.forEach((c) => c.close());
  ext.kill();
});

await test("clients are served over the pipe", async (port, pipe) => {
  const ext = fakeExtension(port);
  ext.autoRespond();
  await waitFor(
    async () => /owns the bridge at/.test(ext.stderrText()),
    5000,
    "host announces the pipe"
  );
  const c = fakeClient(pipe, "pipe-client");
  await c.ready;
  const reply = await c.call("navigate", { url: "https://example.com" });
  assert(reply.result?.echo === "navigate", "pipe client got no usable reply");
  assert(reply.id === "1", "id was not de-prefixed on the pipe path");
  c.close();
  ext.kill();
});

await test("a squatted port cannot keep sessions off the bridge", async (port, pipe) => {
  // The #41 shape at its worst: a stale process holds the port and, being old
  // code, will never yield it. Under the old design that stranded the machine.
  // The pipe is a separate address it has no claim on.
  const squatter = net.createServer((s) => s.on("error", () => {}));
  await new Promise((r) => squatter.listen(port, "127.0.0.1", r));

  const ext = fakeExtension(port);
  ext.autoRespond();
  await waitFor(
    async () => /owns the bridge at/.test(ext.stderrText()),
    5000,
    "host owns the pipe despite the squatter"
  );

  const c = fakeClient(pipe, "unblocked");
  await c.ready;
  const reply = await c.call("get_page_text");
  assert(reply.result?.echo === "get_page_text", "squatter still blocked the bridge");
  c.close();
  ext.kill();
  await new Promise((r) => squatter.close(r));
});

await test("a session starting against a live host never binds the port", async (port, pipe) => {
  // The churn test. With a host already serving, a new MCP server must join it
  // rather than grab the port and force a handover.
  const ext = fakeExtension(port);
  ext.autoRespond();
  await waitFor(
    async () => /owns the bridge at/.test(ext.stderrText()),
    5000,
    "host serving"
  );
  // Free the legacy port so binding it would actually be possible.
  await waitFor(async () => !(await portIsFree(port)), 5000, "host also holds the legacy port");

  const session = spawn(process.execPath, [RUNTIME_HARNESS], {
    env: { ...process.env, OCIC_PORT: String(port), OCIC_PIPE: pipe },
    stdio: ["ignore", "pipe", "pipe"]
  });
  const err = [];
  session.stderr.on("data", (c) => err.push(c.toString()));
  await waitFor(
    async () => /Connected to browser bridge via/.test(err.join("")),
    8000,
    "session joins the bridge"
  );
  assert(
    !/Primary MCP server listening/.test(err.join("")),
    "session bound the port instead of joining the host"
  );
  assert(
    !/yielding/.test(err.join("")),
    "a handover happened; there should have been nothing to hand over"
  );
  session.kill();
  ext.kill();
});

await test("host takes the port from an incumbent MCP primary, which rejoins as a client", async (port) => {
  // Boot order the old way round: a Claude session starts while the browser is
  // down, binds the port, and is still holding it when the browser comes up.
  const primary = spawn(process.execPath, [RUNTIME_HARNESS], {
    env: { ...process.env, OCIC_PORT: String(port) },
    stdio: ["ignore", "pipe", "pipe"]
  });
  const primaryErr = [];
  primary.stderr.on("data", (c) => primaryErr.push(c.toString()));
  await waitFor(
    async () => /Primary MCP server listening/.test(primaryErr.join("")),
    5000,
    "incumbent binds first"
  );

  const ext = fakeExtension(port);
  ext.autoRespond();

  await waitFor(
    async () => /yielding, it is the better owner/.test(primaryErr.join("")),
    8000,
    "incumbent yields"
  );
  await waitFor(
    async () => /owns the browser port|now owns the browser port/.test(ext.stderrText()),
    8000,
    "host takes over"
  );
  await waitFor(
    async () => /Connected to browser bridge via/.test(primaryErr.join("")),
    8000,
    "ex-incumbent rejoins as a client"
  );

  // And the handover left a working system.
  const c = fakeClient(port, "after-handover");
  await c.ready;
  const reply = await c.call("navigate");
  assert(reply.result?.echo === "navigate", "hub not serving after handover");
  c.close();
  ext.kill();
  primary.kill();
});

// ---------------------------------------------------------------------------

const failed = results.filter((r) => !r.ok);
console.log(
  `\n${results.length - failed.length}/${results.length} passed` +
    (failed.length ? `\n\nFailures:\n${failed.map((f) => `  - ${f.name}: ${f.err}`).join("\n")}` : "") +
    "\n"
);
process.exit(failed.length ? 1 : 0);
