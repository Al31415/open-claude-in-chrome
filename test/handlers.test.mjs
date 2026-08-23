// Handler-level tests for #28 (no focus stealing) and #35 (set_tab_focus),
// running the SHIPPED handler bodies against a mocked chrome.* API. Covers the
// logic a browser test would cover, minus the browser.
import { extractMethod, extractFunction, compile } from "./_extract.mjs";
let fail=0; const ok=(c,m)=>{console.log((c?"  PASS ":"  FAIL ")+m); if(!c)fail++;};

const api = [];              // every chrome.* call, in order
function mkChrome(state) {
  const rec = (name, arg) => api.push({ name, arg });
  return {
    tabs: {
      create: async (o) => { rec("tabs.create", o); const t={id:999, windowId:o.windowId??state.curWin, active:!!o.active}; state.tabs.push(t); return t; },
      group: async (o) => { rec("tabs.group", o); return state.groupId; },
      query: async (q) => { rec("tabs.query", q); return state.tabs.filter(t=>t.groupId===state.groupId || q.groupId===undefined); },
      get: async (id) => { rec("tabs.get", id); const t=state.tabs.find(t=>t.id===id); if(!t) throw new Error("no tab"); return t; },
      update: async (id, o) => { rec("tabs.update", {id,...o}); const t=state.tabs.find(t=>t.id===id); if(t&&o.active!==undefined)t.active=o.active; return t; }
    },
    windows: { update: async (id,o)=>{ rec("windows.update", {id,...o}); state.focusedWin = o.focused ? id : state.focusedWin; } },
    tabGroups: { update: async ()=>{}, get: async ()=>({id:state.groupId,title:"MCP"}) },
    storage: {
      local: { get: async()=>({}), set: async(v)=>{rec("storage.local.set", Object.keys(v)); Object.assign(state.local,v);} },
      session: { get: async()=>({}), set: async(v)=>{rec("storage.session.set", Object.keys(v)); Object.assign(state.session,v);} }
    }
  };
}

const state = { tabs:[{id:100,windowId:7,active:true,groupId:55}], groupId:55, curWin:1, focusedWin:1, local:{}, session:{} };
globalThis.chrome = mkChrome(state);

// deps the handlers close over
let tabGroupId = 55; let tabGroupTabs = new Set([100]);
const isInGroup = async (id) => state.tabs.some(t=>t.id===id);
const ensureTabGroup = async () => {};
const formatTabContext = (tabs) => ({content:[{type:"text",text:JSON.stringify({availableTabs:tabs.map(t=>({tabId:t.id}))})}]});
const CONFIG_KEY="ocic_config_v1", TAB_CONFIG_KEY="ocic_tab_config_v1";
const CONFIG_SCHEMA={humanize:"drive input like a person"};
let configState={default:{humanize:false,humanize_speed:"fast",humanize_seed:null},byTab:{}};
const configHydrated=Promise.resolve();
// get_config reports the live humanization persona; give the harness one so the
// handler can be exercised the same way the extension runs it.
const humanSessionSeed = 12345;
const humanSession = { persona: { speed: 1.02, steadiness: 0.88, overshoot: 1.10, typeTempo: 0.94 } };

const src = [
  ...["tabs_create_mcp","set_tab_focus","get_config","set_config"].map(
    (m) => `const H_${m} = { ${extractMethod(m)} };`),
  extractFunction("effectiveConfig"),
  extractFunction("writeConfig")
].join("\n\n");
const mk = new Function("chrome","tabGroupId","tabGroupTabs","isInGroup","ensureTabGroup","formatTabContext",
  "CONFIG_KEY","TAB_CONFIG_KEY","CONFIG_SCHEMA","configState","configHydrated","humanSession","humanSessionSeed",
  src + "; return { H_tabs_create_mcp, H_set_tab_focus, H_get_config, H_set_config, effectiveConfig, writeConfig };");
const H = mk(globalThis.chrome, tabGroupId, tabGroupTabs, isInGroup, ensureTabGroup, formatTabContext,
  CONFIG_KEY, TAB_CONFIG_KEY, CONFIG_SCHEMA, configState, configHydrated, humanSession, humanSessionSeed);

console.log("== #28: creating a tab must not select it or steal focus ==");
api.length=0;
await H.H_tabs_create_mcp.tabs_create_mcp({});
const create = api.find(c=>c.name==="tabs.create");
ok(create && create.arg.active===false, `tabs.create called with active:false (got ${JSON.stringify(create&&create.arg)})`);
ok(create && create.arg.windowId===7, "new tab created in the MCP group's OWN window, not the operator's focused window");
ok(!api.some(c=>c.name==="windows.update"), "no windows.update — never raises a window");
ok(!api.some(c=>c.name==="tabs.update" && c.arg.active===true), "no tabs.update({active:true}) — never selects the new tab");

console.log("== #35: set_tab_focus selects the tab ==");
api.length=0;
const r1 = await H.H_set_tab_focus.set_tab_focus({tabId:100});
ok(api.some(c=>c.name==="tabs.update" && c.arg.active===true), "selects the tab in its window");
ok(!api.some(c=>c.name==="windows.update"), "does NOT raise the window when focus_window is omitted (quiet by default)");
ok(/active tab/.test(r1.content[0].text), `result explains what happened: "${r1.content[0].text}"`);

console.log("== #35: focus_window:true also raises the window ==");
api.length=0;
const r2 = await H.H_set_tab_focus.set_tab_focus({tabId:100, focus_window:true});
const wu = api.find(c=>c.name==="windows.update");
ok(wu && wu.arg.focused===true, "windows.update({focused:true}) issued");
ok(wu && wu.arg.id===7, "raises the tab's OWN window (id 7)");
ok(/front/.test(r2.content[0].text), `result mentions raising the window: "${r2.content[0].text}"`);

console.log("== #35: refuses tabs outside the MCP group ==");
const r3 = await H.H_set_tab_focus.set_tab_focus({tabId:4242});
ok(/not in the MCP group/.test(r3.content[0].text), "out-of-group tab rejected");

console.log("== config: default vs per-tab layering ==");
ok(H.effectiveConfig(100).humanize===false, "default humanize is false (opt-in)");
await H.writeConfig("humanize", true, undefined);
ok(H.effectiveConfig(100).humanize===true, "setting the default applies to a tab");
await H.writeConfig("humanize", false, 100);
ok(H.effectiveConfig(100).humanize===false && H.effectiveConfig(200).humanize===true,
   "per-tab override wins for tab 100 while tab 200 keeps the default");
await H.writeConfig("humanize", null, 100);
ok(H.effectiveConfig(100).humanize===true, "clearing the per-tab override falls back to the default");

console.log("== config: storage scoping ==");
api.length=0; await H.writeConfig("humanize", true, undefined);
ok(api.some(c=>c.name==="storage.local.set"), "default persists to LOCAL storage (survives restart)");
api.length=0; await H.writeConfig("humanize", true, 100);
ok(api.some(c=>c.name==="storage.session.set"), "per-tab override persists to SESSION storage (dies with the browser)");

console.log("== get_config reports the schema ==");
const g = JSON.parse((await H.H_get_config.get_config({tabId:100})).content[0].text);
ok(!!g.recognizedKeys && !!g.recognizedKeys.humanize, "recognizedKeys catalog returned");
ok(!!g.effectiveForTab && g.effectiveForTab.tabId===100, "effective config reported for the requested tab");
ok(!!g.activeHand && g.activeHand.seed===12345 && typeof g.activeHand.typeTempo==="number",
   "the live humanization hand is reported, so a study can prove it was held constant");

console.log("== set_config flags unknown keys instead of silently accepting ==");
const sc = await H.H_set_config.set_config({key:"nonsense", value:1});
ok(/not a recognized setting/.test(sc.content[0].text), "unknown key is called out");

console.log(fail===0?"\nALL HANDLER TESTS PASSED":`\n${fail} FAILED`);
process.exit(fail?1:0);
