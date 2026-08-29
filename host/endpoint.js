// Where the native host and the MCP servers meet.
//
// There are two rendezvous addresses, and they are not equal.
//
// The PIPE is the real one: a named pipe on Windows, a unix socket on POSIX,
// named deterministically from the username. It is the better address for
// three reasons. There is no number to allocate, so there is no EADDRINUSE
// race and nothing for a stale process to squat. The OS scopes it to the user,
// where a loopback TCP port is reachable by any process any local user is
// running — every tool call in this system drives a real browser holding real
// logged-in sessions, so that is a door worth closing. And it cannot be
// reached from off the machine even by accident.
//
// The PORT is kept only so the switch costs nobody an outage. The host listens
// on both and clients prefer the pipe, so an MCP server still running older
// code keeps working over TCP until it happens to restart. Once nothing old is
// left the port is dead weight and can go.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const DEFAULT_PORT = 18765;

function configFile() {
  try {
    return JSON.parse(
      fs.readFileSync(
        path.join(os.homedir(), ".config", "open-claude-in-chrome", "config.json"),
        "utf-8"
      )
    );
  } catch {
    return {};
  }
}

export function getPort() {
  // Env override first, so a test harness can stand up a whole host + client
  // fleet on a scratch address without disturbing the live one.
  const fromEnv = parseInt(process.env.OCIC_PORT || "", 10);
  if (fromEnv > 0) return fromEnv;
  return configFile().port || DEFAULT_PORT;
}

// os.userInfo() THROWS rather than returning null when the account has no
// passwd entry — routine inside containers — and this runs before anything
// else, so an unhandled throw here would look like the bridge simply not
// existing. Fall back to the environment, then to a constant: a wrong-but-
// stable name still rendezvouses correctly, since both sides compute it the
// same way.
function currentUser() {
  try {
    const { username } = os.userInfo();
    if (username) return username;
  } catch {}
  return process.env.USER || process.env.USERNAME || "default";
}

export function getPipePath() {
  if (process.env.OCIC_PIPE) return process.env.OCIC_PIPE;
  const configured = configFile().pipe;
  if (configured) return configured;
  // Windows pipe names live in a flat namespace and allow almost anything;
  // POSIX socket paths are length-limited (~104 bytes), so keep both short.
  const user = currentUser().replace(/[^\w.-]/g, "_").slice(0, 32);
  if (process.platform === "win32") {
    return `\\\\.\\pipe\\open-claude-in-chrome-${user}`;
  }
  return path.join(socketDir(), "bridge.sock");
}

// POSIX only: a 0700 directory so the socket inside it is unreachable by other
// users regardless of the socket's own mode. Windows named pipes get the
// equivalent from their default ACL.
export function socketDir() {
  let uid;
  try {
    uid = os.userInfo().uid;
  } catch {}
  return path.join(
    os.tmpdir(),
    `open-claude-in-chrome-${uid ?? currentUser().replace(/[^\w.-]/g, "_")}`
  );
}

export function ensureSocketDir() {
  if (process.platform === "win32") return;
  try {
    fs.mkdirSync(socketDir(), { recursive: true, mode: 0o700 });
    fs.chmodSync(socketDir(), 0o700);
  } catch {}
}

// A unix socket file outlives the process that made it, so a host that was
// killed leaves a path that listen() will refuse with EADDRINUSE even though
// nobody is home. Only unlink when a connect attempt proves it is dead —
// unlinking a live socket would silently strand every client on it.
export async function clearStaleSocket(pipePath) {
  if (process.platform === "win32") return; // pipes vanish with their process
  if (!fs.existsSync(pipePath)) return;
  const net = await import("node:net");
  const alive = await new Promise((resolve) => {
    const probe = net.createConnection(pipePath);
    const done = (v) => {
      probe.destroy();
      resolve(v);
    };
    probe.on("connect", () => done(true));
    probe.on("error", () => done(false));
    setTimeout(() => done(false), 500);
  });
  if (!alive) {
    try {
      fs.unlinkSync(pipePath);
    } catch {}
  }
}
