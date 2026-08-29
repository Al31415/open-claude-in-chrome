#!/usr/bin/env node
//
// A bare tool-runtime process, used by ownership.test.mjs to stand in for a
// Claude Code session that started while the browser was down and therefore
// ended up owning the port. It does nothing but init() and stay alive, so the
// test can watch it hand the port over when the native host turns up.

import { init } from "../tool-runtime.js";

await init();
setInterval(() => {}, 1 << 30);
