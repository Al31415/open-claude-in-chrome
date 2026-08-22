import { createSession, planClick, planHover, planDrag, planScroll, planType, planKey, sampleInBox } from "../extension/humanize/index.js";
let fail = 0;
const ok = (c, m) => { console.log((c ? "  PASS " : "  FAIL ") + m); if (!c) fail++; };

console.log("== INVARIANT: click always lands exactly on target ==");
let landedAll = true, uniquePts = new Set(), pathLens = new Set();
for (let i = 0; i < 300; i++) {
  const s = createSession(i);
  const from = { x: 50 + i, y: 60 }, to = { x: 700, y: 420 };
  const plan = planClick(s, from, to);
  const downs = plan.filter(p => p.k === "down"), ups = plan.filter(p => p.k === "up");
  const moves = plan.filter(p => p.k === "move");
  if (downs[0].x !== to.x || downs[0].y !== to.y) landedAll = false;
  if (ups[0].x !== to.x || ups[0].y !== to.y) landedAll = false;
  if (moves.length) uniquePts.add(moves[Math.floor(moves.length/2)].x + ":" + moves[Math.floor(moves.length/2)].y);
  pathLens.add(moves.length);
}
ok(landedAll, "300 clicks all press+release exactly on the target point");
ok(uniquePts.size > 250, `paths are highly varied (${uniquePts.size}/300 distinct midpoints)`);
ok(pathLens.size > 8, `path length varies (${pathLens.size} distinct point counts)`);

console.log("== movement precedes every click ==");
{ const s = createSession(7); const plan = planClick(s, {x:10,y:10}, {x:400,y:300});
  const firstDown = plan.findIndex(p=>p.k==="down"); const movesBefore = plan.slice(0,firstDown).filter(p=>p.k==="move").length;
  ok(movesBefore >= 5, `${movesBefore} move events dispatched before the press`); }

console.log("== double_click = 2 distinct press/release cycles ==");
{ const s = createSession(3); const plan = planClick(s, {x:0,y:0}, {x:100,y:100}, {clickCount:2});
  ok(plan.filter(p=>p.k==="down").length===2 && plan.filter(p=>p.k==="up").length===2, "two down + two up (not one flagged event)"); }

console.log("== INVARIANT: typed text is EXACTLY the input, once ==");
{ let allExact = true; const samples = ["hello world","OCIC-TEST-DO-NOT-SUBMIT","a@b.co, x!","Ünïcødé 😀 中文"];
  for (const t of samples) for (let i=0;i<40;i++){ const s=createSession(i);
    const out = planType(s,t).filter(p=>p.k==="text").map(p=>p.text).join("");
    if (out !== t) { allExact=false; console.log("   mismatch:", JSON.stringify(out)); } }
  ok(allExact, "text reassembles byte-identical across 160 runs incl. unicode/emoji"); }

console.log("== typing: key events paired, no autoRepeat, dwell under threshold ==");
{ const s = createSession(11); const plan = planType(s, "hello");
  const kd = plan.filter(p=>p.k==="kdown"), ku = plan.filter(p=>p.k==="kup");
  ok(kd.length===ku.length && kd.length===5, `5 keydown + 5 keyup for 5 chars (got ${kd.length}/${ku.length})`);
  ok(!kd.some(p=>p.autoRepeat), "no autoRepeat during normal typing");
  // dwell = sleep between kdown and its kup
  let maxDwell=0; for(let i=0;i<plan.length;i++){ if(plan[i].k==="kdown"){ for(let j=i+1;j<plan.length;j++){ if(plan[j].k==="sleep") maxDwell=Math.max(maxDwell,plan[j].ms); if(plan[j].k==="kup") break; } } }
  ok(maxDwell < s.tm.initialDelayMs, `max key hold ${Math.round(maxDwell)}ms < typematic initial delay ${Math.round(s.tm.initialDelayMs)}ms (so no repeat is FAITHFUL)`);
  ok(kd.every(p=>p.code && p.code.length), "every keydown carries a real code"); }

console.log("== unmappable chars fall back to insertText only ==");
{ const s=createSession(5); const plan=planType(s,"😀中"); ok(plan.filter(p=>p.k==="kdown").length===0 && plan.filter(p=>p.k==="text").length===2, "emoji/CJK: no fabricated keystrokes, text still inserted"); }

console.log("== deliberate long hold renders OS auto-repeat ==");
{ const s=createSession(9); const plan=planKey(s,{key:"Backspace",code:"Backspace",keyCode:8,holdMs:1200});
  const reps=plan.filter(p=>p.k==="kdown"&&p.autoRepeat).length;
  ok(reps>10, `${reps} autoRepeat keydowns emitted for a 1.2s hold`);
  ok(plan.filter(p=>p.k==="kup").length===1, "exactly one keyup closes the hold"); }
{ const s=createSession(9); const plan=planKey(s,{key:"Enter",code:"Enter",keyCode:13});
  ok(plan.filter(p=>p.k==="kdown").length===1 && !plan.some(p=>p.autoRepeat), "a normal press does NOT repeat"); }

console.log("== INVARIANT: scroll total delta is exact ==");
{ let exact=true; for(let i=0;i<200;i++){ const s=createSession(i); const want=[0,300,-500,1000][i%4]; if(!want) continue;
    const sum=planScroll(s,{x:400,y:300},0,want).filter(p=>p.k==="wheel").reduce((a,p)=>a+p.dy,0);
    if(sum!==want) { exact=false; console.log("   got",sum,"want",want); } }
  ok(exact, "wheel deltas always sum to exactly the requested amount");
  const s=createSession(1); ok(planScroll(s,{x:1,y:1},0,300).filter(p=>p.k==="wheel").length>2, "scroll is decomposed into multiple ticks (momentum)"); }

console.log("== sampleInBox stays inside the element ==");
{ let inside=true; const s=createSession(2); const rect={x:100,y:200,width:60,height:24};
  const pts=new Set();
  for(let i=0;i<500;i++){ const p=sampleInBox(rect,s.rng,s.persona); pts.add(p.x+":"+p.y);
    if(p.x<rect.x||p.x>rect.x+rect.width||p.y<rect.y||p.y>rect.y+rect.height) inside=false; }
  ok(inside, "500 samples all inside the box (never misses the target)");
  ok(pts.size>40, `landing point varies (${pts.size} distinct points, not dead-centre every time)`); }

console.log("== tiny target still safe ==");
{ let inside=true; const s=createSession(4); const rect={x:10,y:10,width:8,height:8};
  for(let i=0;i<300;i++){ const p=sampleInBox(rect,s.rng,s.persona);
    if(p.x<rect.x||p.x>rect.x+rect.width||p.y<rect.y||p.y>rect.y+rect.height) inside=false; }
  ok(inside, "8x8px target: 300 samples all inside"); }

console.log("== drag: press at start, release at end, curve between ==");
{ const s=createSession(6); const plan=planDrag(s,{x:0,y:0},{x:100,y:100},{x:400,y:250});
  const d=plan.find(p=>p.k==="down"), u=plan.find(p=>p.k==="up");
  ok(d.x===100&&d.y===100, "press exactly at start");
  ok(u.x===400&&u.y===250, "release exactly at end");
  const movesBetween = plan.slice(plan.indexOf(d), plan.indexOf(u)).filter(p=>p.k==="move").length;
  ok(movesBetween>5, `${movesBetween} intermediate moves (not a straight 10-step line)`); }

console.log("== sessions differ from one another (persona) ==");
{ const a=createSession(), b=createSession();
  ok(a.persona.speed!==b.persona.speed || a.persona.typeTempo!==b.persona.typeTempo, "two sessions get different personas"); }



// ---- speed tiers -----------------------------------------------------------
{
  const { createSession: mk, TEMPOS } = await import("../extension/humanize/index.js");
  console.log("== speed tiers trade time for detail, never correctness ==");
  const dur = (plan) => plan.filter(p => p.k === "sleep").reduce((a, p) => a + p.ms, 0);
  const moves = (plan) => plan.filter(p => p.k === "move").length;
  const from = { x: 20, y: 20 }, to = { x: 640, y: 400 };
  const rows = ["fastest", "fast", "natural", "relaxed"].map((tier) => {
    const s = mk(7, tier);
    const p = planClick(s, from, to);
    const d = p.filter(x => x.k === "down"), u = p.filter(x => x.k === "up");
    return { tier, ms: dur(p), moves: moves(p), landsOn: d[0].x === to.x && d[0].y === to.y && u[0].x === to.x };
  });
  for (const r of rows) console.log(`     ${r.tier.padEnd(11)} ${String(r.ms).padStart(5)}ms  ${String(r.moves).padStart(3)} moves`);
  const monotonic = rows.every((r, i) => i === 0 || rows[i - 1].ms < r.ms);
  ok(monotonic, "duration increases strictly across the four tiers, fastest -> relaxed");
  const movesMonotonic = rows.every((r, i) => i === 0 || rows[i - 1].moves <= r.moves);
  ok(movesMonotonic, "path sample count is non-decreasing across the tiers");
  ok(rows.every(r => r.moves >= 3), `even the fastest tier MOVES before clicking (min ${Math.min(...rows.map(r=>r.moves))} samples, not zero)`);
  ok(rows.every(r => r.landsOn), "every tier still lands exactly on the target");

  // typing text must stay byte-identical at every tier
  const txt = "user@example.com";
  ok(["fastest","fast","natural","relaxed"].every(tier =>
      planType(mk(3, tier), txt).filter(p=>p.k==="text").map(p=>p.text).join("") === txt),
     "typed text is byte-identical at every speed tier");
  // and key hold must stay under the typematic threshold even when slowed down
  const sd = mk(3, "relaxed");
  const planD = planType(sd, "ab");
  let maxHold = 0;
  for (let i=0;i<planD.length;i++) if (planD[i].k==="kdown")
    for (let j=i+1;j<planD.length;j++){ if(planD[j].k==="sleep") maxHold=Math.max(maxHold,planD[j].ms); if(planD[j].k==="kup") break; }
  ok(maxHold < sd.tm.initialDelayMs, `slowest tier still holds keys under the typematic delay (${Math.round(maxHold)}ms < ${Math.round(sd.tm.initialDelayMs)}ms) — no accidental auto-repeat`);
  ok(Object.keys(TEMPOS).length === 4, "four tiers exposed");
  // A default that costs a lot is a default nobody keeps.
  const { DEFAULT_TEMPO } = await import("../extension/humanize/index.js");
  ok(DEFAULT_TEMPO === "fast", "the cheaper tier is the default");
}

console.log(fail===0 ? "\nALL HUMANIZE UNIT TESTS PASSED" : `\n${fail} TEST(S) FAILED`);
process.exit(fail?1:0);
