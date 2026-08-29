#!/usr/bin/env node

// Native Messaging Host for Open Claude in Chrome extension.
// Launched by Chrome when the extension calls connectNative().
// Bridges between Chrome native messaging (stdin/stdout, 4-byte LE length prefix + JSON)
// and the MCP server (TCP on localhost).

import net from "node:net";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

import {
  getPort,
  getPipePath,
  ensureSocketDir,
  clearStaleSocket
} from "./endpoint.js";

// --- Native messaging protocol (Chrome <-> this process) ---

function readNativeMessage(buffer) {
  const messages = [];
  let offset = 0;
  while (offset + 4 <= buffer.length) {
    const len = buffer.readUInt32LE(offset);
    if (offset + 4 + len > buffer.length) break;
    const json = buffer.subarray(offset + 4, offset + 4 + len).toString("utf-8");
    try {
      messages.push(JSON.parse(json));
    } catch (e) {
      // skip malformed
    }
    offset += 4 + len;
  }
  return { messages, remainder: buffer.subarray(offset) };
}

function writeNativeMessage(obj) {
  const json = JSON.stringify(obj);
  const buf = Buffer.from(json, "utf-8");
  const header = Buffer.alloc(4);
  header.writeUInt32LE(buf.length, 0);
  process.stdout.write(Buffer.concat([header, buf]));
}

// --- Who owns the port ---
//
// Exactly one process has to own :18765, because native messaging gives the
// extension exactly one host, and every Claude Code session on the machine
// has to reach that one browser through it. The only real question is WHICH
// process owns it.
//
// It used to be whichever MCP server bound first — an ordinary Claude Code
// session, picked for no reason except that it booted first, holding the
// browser link on behalf of every other session on the box. That made the
// link's lifetime an accident: it ended when an unrelated session exited, and
// an orphaned server left behind by a session that died days ago was just as
// eligible to win the race as a live one (#36, #41).
//
// This process is the principled owner. Chrome starts it when the extension
// connects and kills it when the extension goes away, so its lifetime already
// IS the browser link's lifetime — and the extension already supervises it,
// reconnecting 250ms after onDisconnect (background.js). Owning the port here
// deletes the election entirely, and demotes an orphaned MCP server to
// harmless: it holds nothing anyone else needs.
//
// The wire protocol is unchanged in both directions, so this rolls out one
// side at a time: a new host serves old client-mode MCP servers, and a new MCP
// server still works against an old primary. When something already holds the
// port we attach to it exactly as before AND ask it to hand over — a new MCP
// server steps aside, an old one ignores the request and we simply stay in the
// legacy role, which is today's behaviour.

const TCP_PORT = getPort();
const PIPE_PATH = getPipePath();

let mode = null; // "hub" once we own the port; "legacy" while someone else does
let lastExtensionTraffic = Date.now();
let heartbeatsSeen = 0;

// Legacy role: we are a TCP client of whichever MCP server owns the port.
let tcpSocket = null;
let tcpBuffer = Buffer.alloc(0);
let reconnectTimer = null;
let upgradeTimer = null;

// Hub role: MCP servers connect to US, and are multiplexed onto the single
// native-messaging channel to the extension.
const clients = new Map(); // clientId -> socket
const clientRequestMap = new Map(); // prefixed id -> { clientId, originalId }
let clientIdCounter = 0;

// When the incumbent rejects us because ANOTHER browser's host already holds
// the native slot, retry slowly (15s) instead of hammering every 1.5s: with
// two browsers running OCIC, the loser otherwise reconnect-spams the owner
// and makes browser selection flap across restarts.
let rejectedByOwner = false;
const RETRY_MS = 1500;
const REJECTED_RETRY_MS = 15000;
// A peer that has connected but not yet said what it is. Only an MCP client
// has anything to send on connect (`client_hello`), so silence past this
// window means a rival browser's host, which we reject.
const CLASSIFY_MS = 500;

// --- Hub role ---

function onIncomingConnection(socket) {
  // An accepted socket is unclassified until its first line arrives, and until
  // then nothing downstream has attached an 'error' listener. In Node an
  // unhandled 'error' is a thrown exception, so a peer that vanishes in that
  // window — a client MCP process killed mid-handshake, which is routine —
  // would take the hub down, and with it every session's browser link. This is
  // the same failure that cost the primary its life in c0a09a2.
  socket.on("error", () => socket.destroy());

  let buffer = Buffer.alloc(0);
  let classified = false;

  const rejectAsRival = () => {
    if (classified) return;
    classified = true;
    // Reject with the exact string the losing host's reconnect loop matches on
    // so it drops into the slow lane instead of hammering us every 1.5s.
    try {
      socket.end(
        JSON.stringify({
          type: "error",
          error: "Another browser profile is already connected."
        }) + "\n"
      );
    } catch {}
  };

  const classifyTimer = setTimeout(rejectAsRival, CLASSIFY_MS);
  socket.on("close", () => clearTimeout(classifyTimer));

  socket.on("data", function onEarlyData(chunk) {
    if (classified) return;
    buffer = Buffer.concat([buffer, chunk]);
    const idx = buffer.indexOf(10);
    if (idx === -1) return;

    const firstLine = buffer.subarray(0, idx).toString("utf-8").trim();
    const rest = buffer.subarray(idx + 1);
    let msg = null;
    try {
      msg = JSON.parse(firstLine);
    } catch {}

    classified = true;
    clearTimeout(classifyTimer);
    socket.removeListener("data", onEarlyData);

    if (msg && msg.type === "client_hello") {
      attachClient(socket, rest);
      return;
    }
    // Anything else is another browser's host asking for a slot we hold.
    classified = false;
    rejectAsRival();
  });
}

// The pipe is the real rendezvous; the port is kept only so MCP servers still
// running older code keep working until they restart. Both feed the same
// client table, so a mixed fleet is invisible from here.
const pipeServer = net.createServer(onIncomingConnection);
const hubServer = net.createServer(onIncomingConnection);

// How long we keep probing quickly before settling into the slow lane. This has
// to comfortably exceed background.js's SWITCH_RELEASE_MS (15s): switch_browser
// works by the outgoing browser dropping its host and suspending reconnect for
// that window, and the incoming browser only gets the bridge if it happens to
// probe while the window is open. Backing off to 15s immediately would make a
// hand-off land inside the window mostly by luck.
const FAST_CLAIM_WINDOW_MS = 40_000;
const claimingSince = Date.now();

async function claimPipe() {
  ensureSocketDir();
  await clearStaleSocket(PIPE_PATH);
  const onErr = (err) => {
    if (err.code === "EADDRINUSE") {
      // Another browser's host holds the bridge for this user. Probe often at
      // first so a switch_browser hand-off is picked up promptly, then drop to
      // the slow lane so two idle browsers aren't polling each other forever.
      const fast = Date.now() - claimingSince < FAST_CLAIM_WINDOW_MS;
      setTimeout(claimPipe, fast ? RETRY_MS : REJECTED_RETRY_MS);
      return;
    }
    process.stderr.write(`Pipe listen failed: ${err.message}\n`);
    setTimeout(claimPipe, RETRY_MS);
  };
  pipeServer.once("error", onErr);
  pipeServer.listen(PIPE_PATH, () => {
    pipeServer.removeListener("error", onErr);
    process.stderr.write(`Native host owns the bridge at ${PIPE_PATH}\n`);
  });
}

function attachClient(socket, initialBuffer) {
  const clientId = String(++clientIdCounter);
  clients.set(clientId, socket);
  process.stderr.write(`MCP client ${clientId} attached (${clients.size} total)\n`);
  socket.write(JSON.stringify({ type: "client_ack", clientId }) + "\n");

  let buffer = initialBuffer;

  function pump() {
    let idx;
    while ((idx = buffer.indexOf(10)) !== -1) {
      const line = buffer.subarray(0, idx).toString("utf-8").trim();
      buffer = buffer.subarray(idx + 1);
      if (!line) continue;
      try {
        const msg = JSON.parse(line);
        if (msg.type === "tool_request" && msg.id) {
          // Namespace the id so concurrent sessions can't collide, and so a
          // response can be routed back to the one client that asked.
          const prefixedId = `h${clientId}_${msg.id}`;
          clientRequestMap.set(prefixedId, { clientId, originalId: msg.id });
          writeNativeMessage({ ...msg, id: prefixedId });
        }
      } catch {
        // skip malformed
      }
    }
  }

  pump();
  socket.on("data", (chunk) => {
    buffer = Buffer.concat([buffer, chunk]);
    pump();
  });
  socket.on("close", () => {
    clients.delete(clientId);
    for (const [prefixedId, info] of clientRequestMap) {
      if (info.clientId === clientId) clientRequestMap.delete(prefixedId);
    }
    process.stderr.write(`MCP client ${clientId} detached (${clients.size} left)\n`);
  });
}

// Route one extension-originated message to whoever is waiting for it.
function routeFromExtension(msg) {
  // Liveness ping from the service worker. Nothing downstream needs it, but
  // its rhythm is what the deaf-extension watchdog below keys off.
  if (msg.type === "heartbeat") {
    heartbeatsSeen++;
    return;
  }
  if (msg.type === "recording_complete") {
    // Unsolicited: any attached session may be the one holding the Claude
    // channel, so every client gets a copy.
    const line = JSON.stringify(msg) + "\n";
    for (const socket of clients.values()) {
      try {
        if (!socket.destroyed) socket.write(line);
      } catch {}
    }
    forwardToLegacyOwner(msg);
    return;
  }
  if (msg.id && clientRequestMap.has(msg.id)) {
    const { clientId, originalId } = clientRequestMap.get(msg.id);
    clientRequestMap.delete(msg.id);
    const socket = clients.get(clientId);
    try {
      if (socket && !socket.destroyed) {
        socket.write(JSON.stringify({ ...msg, id: originalId }) + "\n");
      }
    } catch {}
    return;
  }
  // Not an id we issued. During a rollout an older MCP server may still own the
  // port and have its own sessions in flight; those responses are its to route,
  // so hand them on. Ids are namespaced per owner, so this is unambiguous.
  forwardToLegacyOwner(msg);
}

function forwardToLegacyOwner(msg) {
  if (tcpSocket && !tcpSocket.destroyed) {
    try {
      tcpSocket.write(JSON.stringify(msg) + "\n");
    } catch {}
  }
}

// --- Claiming the port ---

function claimPort() {
  const onListenError = (err) => {
    if (err.code === "EADDRINUSE") {
      // Someone holds it. Attach as a legacy client — which keeps us working
      // no matter who they are — and ask them to hand the port over.
      connectTcpLegacy();
      return;
    }
    process.stderr.write(`Hub listen failed: ${err.message}\n`);
    setTimeout(claimPort, RETRY_MS);
  };

  hubServer.once("error", onListenError);
  hubServer.listen(TCP_PORT, "127.0.0.1", () => {
    hubServer.removeListener("error", onListenError);
    mode = "hub";
    if (reconnectTimer) {
      clearInterval(reconnectTimer);
      reconnectTimer = null;
    }
    if (tcpSocket) {
      // We were attached to an incumbent that has now stepped aside.
      const old = tcpSocket;
      tcpSocket = null;
      old.destroy();
    }
    process.stderr.write(`Native host owns the browser port :${TCP_PORT}\n`);
  });
}

// --- Legacy role: client of an MCP server that owns the port ---

function connectTcpLegacy() {
  if (tcpSocket || mode === "hub") return;
  mode = "legacy";

  tcpSocket = new net.Socket();

  tcpSocket.connect(TCP_PORT, "127.0.0.1", () => {
    if (reconnectTimer) {
      clearInterval(reconnectTimer);
      reconnectTimer = null;
    }
    // Ask the incumbent to hand the port over. A current MCP server closes its
    // listener and rejoins as a client, at which point our retry wins the bind.
    // An older one has no handler for this and ignores it, leaving us in the
    // legacy role — i.e. exactly the behaviour before this change.
    try {
      tcpSocket.write(JSON.stringify({ type: "yield_request" }) + "\n");
    } catch {}
    scheduleUpgrade();
  });

  tcpSocket.on("data", (chunk) => {
    // newline-delimited JSON from the MCP server that owns the port
    tcpBuffer = Buffer.concat([tcpBuffer, chunk]);
    let newlineIdx;
    while ((newlineIdx = tcpBuffer.indexOf(10)) !== -1) {
      const line = tcpBuffer.subarray(0, newlineIdx).toString("utf-8").trim();
      tcpBuffer = tcpBuffer.subarray(newlineIdx + 1);
      if (!line) continue;
      try {
        const msg = JSON.parse(line);
        if (msg.type === "error" && /another browser profile/i.test(msg.error || "")) {
          // The owner already has a browser attached; we are the loser of the
          // slot. Back off hard instead of hammering every 1.5s.
          rejectedByOwner = true;
        }
        // Forward to extension via native messaging
        writeNativeMessage(msg);
      } catch {
        // skip malformed
      }
    }
  });

  tcpSocket.on("error", () => {
    tcpSocket = null;
  });

  tcpSocket.on("close", () => {
    tcpSocket = null;
    // The incumbent may have just yielded, so try to take the port before
    // settling back into the retry loop.
    if (mode !== "hub") claimPort();
    if (!reconnectTimer && mode !== "hub") {
      // Keep retrying indefinitely — do NOT exit when no MCP server is up.
      // The native host also writes recording bundles to disk (save_recording),
      // which must work with no Claude session connected. Lifetime is tied to
      // the extension (stdin), which ends on browser/extension shutdown below.
      // Rejected-by-owner (another browser holds the slot): slow lane, and
      // re-probe occasionally in case the winner's browser goes away.
      const interval = rejectedByOwner ? REJECTED_RETRY_MS : RETRY_MS;
      rejectedByOwner = false;
      reconnectTimer = setInterval(() => {
        if (mode === "hub") return;
        if (!tcpSocket) claimPort();
      }, interval);
    }
  });
}

// While attached to an incumbent, keep trying to take the port. This is what
// converges the machine on host-owned ownership without anyone coordinating:
// the moment the incumbent yields, exits, or is killed, the next attempt wins.
function scheduleUpgrade() {
  if (upgradeTimer || mode === "hub") return;
  upgradeTimer = setTimeout(() => {
    upgradeTimer = null;
    if (mode === "hub") return;
    const onErr = (err) => {
      if (err.code !== "EADDRINUSE") {
        process.stderr.write(`Upgrade attempt failed: ${err.message}\n`);
      }
      scheduleUpgrade(); // still theirs; try again later
    };
    hubServer.once("error", onErr);
    hubServer.listen(TCP_PORT, "127.0.0.1", () => {
      hubServer.removeListener("error", onErr);
      mode = "hub";
      if (tcpSocket) {
        const old = tcpSocket;
        tcpSocket = null;
        old.destroy();
      }
      if (reconnectTimer) {
        clearInterval(reconnectTimer);
        reconnectTimer = null;
      }
      process.stderr.write(
        `Incumbent yielded — native host now owns the browser port :${TCP_PORT}\n`
      );
    });
  }, rejectedByOwner ? REJECTED_RETRY_MS : RETRY_MS);
}

// --- Recording bundle write ---
// The recorder saves the trace to disk here, in the native host, instead of
// via chrome.downloads — the browser download path shows an OS save dialog on
// some setups, and this also lets us write to a stable location the coding
// agent can open. Returns the absolute directory so the extension can notify
// Claude Code with a real path.
function handleSaveRecording(msg) {
  try {
    const dir = path.join(
      os.homedir(),
      ".config",
      "open-claude-in-chrome",
      "recordings",
      String(msg.recording_id || "unknown")
    );
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(
      path.join(dir, "trace.json"),
      JSON.stringify(msg.trace ?? {}, null, 2)
    );
    // Ship the schema descriptor alongside so the agent knows how to read it.
    if (typeof msg.schema_md === "string" && msg.schema_md) {
      fs.writeFileSync(path.join(dir, `SCHEMA_${msg.schema || "v0"}.md`), msg.schema_md);
    }
    writeNativeMessage({
      type: "recording_saved",
      recording_id: msg.recording_id,
      path: dir,
      ok: true
    });
  } catch (e) {
    writeNativeMessage({
      type: "recording_saved",
      recording_id: msg.recording_id,
      ok: false,
      error: String(e && e.message)
    });
  }
}

// Write one slice of a recording's audio into audio/NNN.webm. Arrives in
// ~768KB slices (base64 over native messaging) with append=false on the first
// slice of each segment. This is the artifact that makes a failed transcript
// recoverable, so it is written before transcription is even attempted.
function handleSaveAudio(msg) {
  try {
    const rel = String(msg.name || "").replace(/\\/g, "/");
    // Contain the write to the bundle: no absolute paths, no traversal.
    if (rel.startsWith("/") || rel.split("/").includes("..")) return;
    const base = path.join(
      os.homedir(),
      ".config",
      "open-claude-in-chrome",
      "recordings",
      String(msg.recording_id || "unknown")
    );
    const file = path.join(base, rel);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    const buf = Buffer.from(String(msg.b64 || ""), "base64");
    if (msg.append) fs.appendFileSync(file, buf);
    else fs.writeFileSync(file, buf);
  } catch {
    // best-effort: the trace is already on disk
  }
}

// Write one 240p frame into the recording's images/ dir. Fire-and-forget:
// the reference is already in the trace, so a dropped frame just means the
// agent finds no file at that ref.
function handleSaveScreenshot(msg) {
  try {
    const dir = path.join(
      os.homedir(),
      ".config",
      "open-claude-in-chrome",
      "recordings",
      String(msg.recording_id || "unknown"),
      "images"
    );
    fs.mkdirSync(dir, { recursive: true });
    const b64 = String(msg.dataUrl || "").replace(/^data:image\/\w+;base64,/, "");
    if (b64) fs.writeFileSync(path.join(dir, String(msg.name)), Buffer.from(b64, "base64"));
  } catch {
    // best-effort
  }
}

// Write a full screenshot to a stable, user-visible location
// (~/.config/open-claude-in-chrome/screenshots/<timestamp>.jpg) so Claude Code
// can open the absolute path. Unlike save_screenshot (fire-and-forget), this
// replies with the written path so the caller can report it to the agent.
function handleSaveScreenshotToDisk(msg) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const dir = path.join(
    os.homedir(),
    ".config",
    "open-claude-in-chrome",
    "screenshots"
  );
  try {
    fs.mkdirSync(dir, { recursive: true });
    const b64 = String(msg.dataUrl || "").replace(/^data:image\/\w+;base64,/, "");
    if (!b64 || !/^[A-Za-z0-9+/]+={0,2}$/.test(b64)) throw new Error("empty or malformed image data");
    const file = path.join(dir, `${timestamp}.jpg`);
    fs.writeFileSync(file, Buffer.from(b64, "base64"));
    writeNativeMessage({ type: "screenshot_saved", id: msg.id, path: file, ok: true });
  } catch (e) {
    writeNativeMessage({ type: "screenshot_saved", id: msg.id, ok: false, error: String(e && e.message) });
  }
}

// Stage an in-memory screenshot as a real temp file so the extension can
// attach it to a file input via CDP DOM.setFileInputFiles. The extension holds
// screenshots as base64 in a Map (never on disk), but setFileInputFiles needs
// a path, so we materialize the bytes here and return the absolute path.
// Reply is keyed by msg.id so the extension can correlate it to its request.
function handleWriteTempFile(msg) {
  const reply = (payload) => writeNativeMessage({ id: msg.id, type: "temp_file_written", ...payload });
  try {
    const dir = path.join(os.homedir(), ".config", "open-claude-in-chrome", "tmp");
    fs.mkdirSync(dir, { recursive: true });
    // Sanitize the requested name: no path separators, no traversal.
    const name = String(msg.filename || "upload.png").replace(/[^\w.\-]/g, "_");
    const file = path.join(dir, `${Date.now()}_${name}`);
    const b64 = String(msg.dataUrl || "").replace(/^data:[^;]+;base64,/, "");
    if (!b64) return reply({ ok: false, error: "no data" });
    fs.writeFileSync(file, Buffer.from(b64, "base64"));
    // Best-effort GC: staged uploads have a "<epoch>_<name>" prefix; prune only
    // files WE staged (that prefix) and only those older than a day, so we never
    // delete anything another process put in the shared tmp dir. Cap the scan
    // so a giant directory can't stall this request.
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    try {
      let scanned = 0;
      for (const f of fs.readdirSync(dir)) {
        if (!/^\d+_/.test(f)) continue; // not ours
        if (++scanned > 200) break; // bound the sync scan
        const p = path.join(dir, f);
        if (fs.statSync(p).mtimeMs < cutoff) fs.unlinkSync(p);
      }
    } catch { /* best-effort */ }
    reply({ ok: true, result: file });
  } catch (e) {
    reply({ ok: false, error: String(e && e.message) });
  }
}

// --- Main: bridge stdin (from extension) <-> TCP (to MCP server) ---

let stdinBuffer = Buffer.alloc(0);

process.stdin.on("data", (chunk) => {
  lastExtensionTraffic = Date.now();
  stdinBuffer = Buffer.concat([stdinBuffer, chunk]);
  const { messages, remainder } = readNativeMessage(stdinBuffer);
  stdinBuffer = remainder;

  for (const msg of messages) {
    // Handle recording saves locally (write to disk + reply); don't forward.
    if (msg && msg.type === "save_recording") {
      handleSaveRecording(msg);
      continue;
    }
    if (msg && msg.type === "save_screenshot") {
      handleSaveScreenshot(msg);
      continue;
    }
    if (msg && msg.type === "save_screenshot_to_disk") {
      handleSaveScreenshotToDisk(msg);
      continue;
    }
    if (msg && msg.type === "save_audio") {
      handleSaveAudio(msg);
      continue;
    }
    if (msg && msg.type === "write_temp_file") {
      handleWriteTempFile(msg);
      continue;
    }
    // Everything else is for a waiting MCP server. Route by id rather than by
    // role: ours go to the client that asked, anything else belongs to an
    // older MCP server that still owns the port.
    routeFromExtension(msg);
  }
});

process.stdin.on("end", () => {
  // Extension disconnected. Drop the port immediately rather than lingering:
  // with no extension there is no browser link to own, and holding :18765
  // would block the host Chrome spawns next from claiming it.
  if (tcpSocket) tcpSocket.destroy();
  for (const socket of clients.values()) {
    try {
      socket.destroy();
    } catch {}
  }
  try {
    hubServer.close();
  } catch {}
  try {
    pipeServer.close();
  } catch {}
  process.exit(0);
});

// --- Deaf-extension watchdog ---
//
// The worst failure this bridge has is not dying, it is going deaf: still
// holding the rendezvous, still accepting connections, never answering. Nothing
// recovers from that on its own, because every mechanism we have keys off the
// owner being GONE. Dying is the recoverable state — Chrome notices, respawns
// us, and clients reconnect — so if we cannot reach the extension any more, the
// useful thing to do is stop existing.
//
// The signal is already there: background.js posts a heartbeat every ~15s. Long
// silence means the service worker is wedged or gone.
//
// Armed only after we have actually seen heartbeats. An extension too old to
// send them would otherwise look permanently deaf, and we would exit-loop —
// which is why this is safe to ship ahead of any extension change.
const SILENCE_LIMIT_MS = 60_000;

setInterval(() => {
  if (heartbeatsSeen < 2) return; // never saw a heartbeat: not our signal to use
  const silentFor = Date.now() - lastExtensionTraffic;
  if (silentFor < SILENCE_LIMIT_MS) return;
  process.stderr.write(
    `No word from the extension for ${Math.round(silentFor / 1000)}s — exiting so ` +
      `a fresh host can take the bridge.\n`
  );
  process.exit(0);
}, 15_000).unref();

// Own the bridge; and take the legacy port too, or attach to whoever has it.
claimPipe();
claimPort();
