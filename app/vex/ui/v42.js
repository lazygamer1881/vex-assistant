/* Vex 4.2 - mic status dot (state + one level number, no waveform), timer chips, "what can you do" help card. Original art. */
(function(){
if(window.__v42)return;window.__v42=1;
const comp=document.body.classList.contains("comp")||/bphud/.test(location.pathname);
const css=`
#v42m{position:fixed;top:22px;right:28px;z-index:60;display:flex;flex-direction:column;align-items:flex-end;gap:8px;pointer-events:none;font:600 11px/1 var(--vx-f-mono,Consolas,monospace);letter-spacing:.18em;color:var(--tc,var(--vx-a,#6fe6ff))}
body:not(.aionly) #v42m{display:none!important}
#v42m .pill{display:flex;align-items:center;gap:10px;padding:7px 12px 7px 10px;border:1px solid rgba(111,230,255,.35);border-radius:999px;background:rgba(4,12,20,.7)}
#v42m .dot{width:9px;height:9px;border-radius:50%;background:currentColor;box-shadow:0 0 0 0 currentColor;transition:background .3s}
#v42m .lbl{opacity:.85}
#v42m.paused{color:#7d8a96}#v42m.error{color:#ff5a6a}#v42m.recovering{color:#ffc44d}
#v42m.error .dot,#v42m.recovering .dot{animation:v42b 1s steps(2) infinite}
@keyframes v42b{50%{opacity:.2}}
#v42m .tm{display:flex;align-items:center;gap:9px;padding:6px 12px 6px 8px;border-radius:999px;background:rgba(4,12,20,.55);border:1px solid rgba(111,230,255,.25);color:var(--vx-ink,#dff6ff)}
#v42m .tm svg{width:18px;height:18px;transform:rotate(-90deg)}
#v42m .tm b{font-weight:700;color:var(--tc,var(--vx-a,#6fe6ff));min-width:44px;text-align:right}
#v42m .tm.end b{color:#ffc44d}
#v42h{position:fixed;inset:0;z-index:2147482000;display:none;align-items:center;justify-content:center;background:rgba(1,6,10,.72);font-family:var(--vx-f-ui,"Segoe UI",sans-serif);color:var(--vx-ink,#e6f7ff)}
#v42h.on{display:flex}
@keyframes v42in{from{opacity:0;transform:scale(1.03)}to{opacity:1;transform:none}}
#v42h .card{--a:var(--tc,var(--vx-a,#6fe6ff));position:relative;width:min(1180px,86vw);padding:38px 44px 30px;background:linear-gradient(160deg,rgba(10,26,40,.88),rgba(3,10,18,.92));border:1px solid rgba(111,230,255,.4)}
#v42h .card:before{content:"";position:absolute;left:0;top:0;width:180px;height:2px;background:var(--a);}
#v42h .hd{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:24px}
#v42h h1{margin:0;font:700 30px/1 var(--vx-f-ui,"Segoe UI",sans-serif);letter-spacing:.06em}
#v42h h1 span{color:var(--a)}
#v42h .sub{font:600 12px/1 var(--vx-f-mono,Consolas,monospace);letter-spacing:.22em;color:var(--a);opacity:.8}
#v42h .g{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
#v42h .t{position:relative;padding:18px 18px 16px;border:1px solid rgba(140,220,255,.14);background:rgba(120,210,255,.035)}
@keyframes v42t{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
#v42h .t i{display:block;width:34px;height:34px;margin-bottom:12px}
#v42h .t h2{margin:0 0 9px;font:700 17px/1.1 var(--vx-f-ui,"Segoe UI",sans-serif);letter-spacing:.03em}
#v42h .t p{margin:0;font:400 14px/1.45 var(--vx-f-ui,"Segoe UI",sans-serif);color:#b9d4e2}
#v42h .t p q{color:#fff;quotes:"\\201C" "\\201D"}
#v42h .ft{display:flex;justify-content:space-between;gap:20px;margin-top:22px;padding-top:16px;border-top:1px solid rgba(140,220,255,.14);font:500 13px/1.4 var(--vx-f-ui,"Segoe UI",sans-serif);color:#a9c6d6}
#v42h .ft b{color:var(--a);font-weight:600}
`;
const st=document.createElement("style");st.textContent=css;document.head.appendChild(st);
/* ---- mic pill + timers (main screen only) */
let M=null,lvl=0,S={mic:"off",timers:[]},tPoll=0;
if(!comp){
 M=document.createElement("div");M.id="v42m";M.innerHTML='<div class="pill"><span class="dot"></span><span class="lbl">MIC</span></div><div id="v42t"></div>';
 document.body.appendChild(M);
}
const ring=(f)=>{const c=2*Math.PI*7;return `<svg viewBox="0 0 18 18"><circle cx="9" cy="9" r="7" fill="none" stroke="rgba(255,255,255,.15)" stroke-width="2"/><circle cx="9" cy="9" r="7" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="${(c*f).toFixed(1)} ${c.toFixed(1)}"/></svg>`;};
const fmt=s=>{s=Math.max(0,s|0);const h=s/3600|0,m=(s%3600)/60|0,x=s%60;return h?`${h}:${String(m).padStart(2,"0")}:${String(x).padStart(2,"0")}`:`${m}:${String(x).padStart(2,"0")}`;};
let tBase=0;
function drawTimers(){
 if(!M)return;const el=M.querySelector("#v42t"),now=performance.now(),d=(now-tBase)/1000;
 el.innerHTML=(S.timers||[]).map(t=>{const left=Math.max(0,t.left-d),f=t.total?left/t.total:1;
  return `<div class="tm${left<30?" end":""}" style="color:var(--tc,var(--vx-a,#6fe6ff))">${ring(Math.max(0,Math.min(1,f)))}<span style="color:var(--vx-ink,#dff6ff)">${String(t.kind=="timer"?t.label:"⏰ "+t.label).toUpperCase().slice(0,22)}</span><b>${t.kind=="timer"?fmt(left):t.due}</b></div>`;}).join("");
}
function poll(){
 const api=window.pywebview&&window.pywebview.api;if(!api||!api.v42_status)return;
 api.v42_status().then(d=>{if(!d)return;S=d;tBase=performance.now();
  if(M){M.className=d.mic=="ok"?"":d.mic;const vs=d.state||window.__vstate||"";
   M.querySelector(".lbl").textContent=d.mic=="ok"?(vs=="listening"?"MIC · LISTENING":vs=="speaking"?"MIC · MUTED WHILE SPEAKING":vs=="thinking"?"MIC · THINKING":"MIC · READY"):d.mic=="paused"?"MIC · PAUSED":d.mic=="recovering"?"MIC · RECONNECTING":d.mic=="error"?"MIC · NOT FOUND":"MIC";}
  drawTimers();}).catch(()=>{});
}
let last=0;
function tick(t){
 requestAnimationFrame(tick);
 if(M){const L=window.__lvl;let v=0;if(L&&L.src=="mic"&&performance.now()-L.t<400)v=Math.min(1,L.v*2.2);
  lvl+=(v-lvl)*0.25;const dot=M.querySelector(".dot");
  if(S.mic=="ok"){dot.style.transform=`scale(${(1+lvl*0.9).toFixed(3)})`;dot.style.boxShadow=`0 0 ${(4+lvl*16).toFixed(1)}px currentColor`;dot.style.opacity=(0.55+lvl*0.45).toFixed(2);}
  else{dot.style.transform="";dot.style.boxShadow="none";dot.style.opacity="";}
  M.style.display=document.body.classList.contains("i41on")?"none":"";}
 if(t-last>1000){last=t;poll();}
 else if(M&&S.timers&&S.timers.length&&((t/250)|0)!=((last/250)|0))drawTimers();
}
requestAnimationFrame(tick);
/* ---- help card */
const ico={
 apps:'<svg viewBox="0 0 34 34" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="4" y="4" width="11" height="11"/><rect x="19" y="4" width="11" height="11"/><rect x="4" y="19" width="11" height="11"/><path d="M24.5 19v11M19 24.5h11"/></svg>',
 timer:'<svg viewBox="0 0 34 34" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="17" cy="19" r="11"/><path d="M17 19V12M13 3h8M27 8l2-2"/></svg>',
 bell:'<svg viewBox="0 0 34 34" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M9 24V15a8 8 0 0116 0v9l3 3H6z"/><path d="M14 29a3 3 0 006 0"/></svg>',
 mem:'<svg viewBox="0 0 34 34" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 6a6 6 0 00-6 6c0 2 1 3 1 4s-2 2-2 5a6 6 0 006 6h1V6zM22 6a6 6 0 016 6c0 2-1 3-1 4s2 2 2 5a6 6 0 01-6 6h-1V6z"/><path d="M12 13h-3M22 13h3M12 20h-4M22 20h4"/></svg>',
 show:'<svg viewBox="0 0 34 34" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="7" width="28" height="19"/><path d="M3 22l8-7 6 5 5-4 9 7"/><circle cx="24" cy="12" r="2"/></svg>',
 pc:'<svg viewBox="0 0 34 34" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="5" width="28" height="18"/><path d="M12 29h10M17 23v6M8 17l4-4 3 3 5-6 4 4"/></svg>',
 ask:'<svg viewBox="0 0 34 34" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M5 7h24v15H14l-6 5v-5H5z"/><path d="M14 12a3 3 0 116 0c0 2-3 2-3 4M17 19v.5"/></svg>',
 mode:'<svg viewBox="0 0 34 34" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="17" cy="17" r="12"/><path d="M17 5a12 12 0 000 24z" fill="currentColor" fill-opacity=".25"/><circle cx="17" cy="17" r="4"/></svg>'};
const TILES=[["apps","Apps & games",'<q>Bring up Minecraft</q> · <q>open Discord</q> - close-enough names work too.'],
 ["timer","Timers",'<q>Set a 10 minute pizza timer</q> · <q>how long left?</q> · <q>cancel the timer</q>'],
 ["bell","Reminders",'<q>Remind me at 5 pm to record</q> · <q>what are my reminders?</q>'],
 ["mem","Memory",'<q>Remember my upload day is Friday</q> · <q>what do you remember about me?</q>'],
 ["show","Show me",'<q>Show me a red panda</q> - pictures, videos and facts on the glass panel.'],
 ["pc","Your PC",'<q>Status report</q> · <q>what\'s my volume?</q> · <q>clean up my disk</q> (asks first)'],
 ["ask","Questions & homework",'<q>Explain photosynthesis</q> · <q>check my math</q> · <q>what\'s new in Minecraft?</q>'],
 ["mode","Modes & view",'<q>Studio mode</q> · <q>open everything</q> · <q>just you</q> · <q>mini orb</q>']];
let H=null,hT=0;
function help(on){
 if(comp)return;
 if(!H){H=document.createElement("div");H.id="v42h";document.body.appendChild(H);
  H.addEventListener("mousedown",()=>help(false));}
 clearTimeout(hT);
 if(!on){H.classList.remove("on");return;}
 H.innerHTML=`<div class="card"><div class="hd"><h1>WHAT I CAN <span>DO</span></h1><div class="sub">VEX 4.2 // JUST ASK</div></div><div class="g">${TILES.map((x,i)=>`<div class="t" style="animation-delay:${(0.05+i*0.05).toFixed(2)}s"><i style="color:var(--a)">${ico[x[0]]}</i><h2>${x[1]}</h2><p>${x[2]}</p></div>`).join("")}</div>
 <div class="ft"><span><b>Follow-ups:</b> keep talking for a few seconds after I answer - no wake word needed.</span><span><b>"Vex stop"</b> cancels anything · risky actions always ask first.</span></div></div>`;
 H.classList.add("on");try{window.vexUiLog&&vexUiLog("help card shown");}catch(e){}hT=setTimeout(()=>help(false),30000);
}
window.v42help=help;
addEventListener("keydown",e=>{if(e.key=="Escape"&&H&&H.classList.contains("on"))help(false);});
const prev=window.vexOn;
window.vexOn=(ev,d)=>{try{if(ev=="help42")help(!!(d&&d.on));}catch(e){}return prev?prev(ev,d):undefined;};
})();
