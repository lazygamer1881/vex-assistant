// Vex 3.8 blueprint layout for the expanded Home view (original art): navy blueprint grid, targeting ring around the core,
// title bar with tabs, dense data column, big clock + radar, centred readout card, coordinates + icons, thin footer.
(function(){
const A=()=>window.pywebview&&window.pywebview.api,NS="http://www.w3.org/2000/svg",E=s=>String(s==null?"":s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const st=document.createElement("style");st.textContent=`
#bpGrid,#bpRing,.bpP{display:none}
body.bp #bpGrid{display:block;position:fixed;inset:0;z-index:0;pointer-events:none;
 background:linear-gradient(rgba(120,190,255,.07) 1px,transparent 1px) 0 0/24px 24px,linear-gradient(90deg,rgba(120,190,255,.07) 1px,transparent 1px) 0 0/24px 24px,
 linear-gradient(rgba(120,190,255,.13) 1px,transparent 1px) 0 0/120px 120px,linear-gradient(90deg,rgba(120,190,255,.13) 1px,transparent 1px) 0 0/120px 120px,
 radial-gradient(ellipse at 50% 40%,rgba(30,90,200,.18),transparent 70%)}
body.bp #bpRing{display:block;position:fixed;inset:0;width:100vw;height:100vh;z-index:2;pointer-events:none}
body.bp .bpP{display:block;position:fixed;z-index:4;font:11px/1.55 VexMono,monospace;color:#a9d6ff;letter-spacing:.08em;text-shadow:0 0 6px rgba(80,160,255,.45)}
body.bp .dash.hud .w:not(.hero),body.bp #vxJ,body.bp #vxTr,body.bp #vxTick2,body.bp header,body.bp #greet,body.bp #hint,body.bp #ticker,body.bp .readout,body.bp #radial,body.bp #dtabs,body.bp #vxHex,body.bp #vxModeTag{display:none!important}
body.bp #stateText{position:fixed!important;left:-9999px}
body.bp .inputbar{position:fixed!important;left:50%!important;transform:translateX(-50%)!important;bottom:30px;width:min(560px,34vw)!important;z-index:5;background:rgba(4,22,52,.85)!important;border:1px solid rgba(120,190,255,.35)!important;clip-path:none!important;border-radius:2px!important}
.bpP h6{margin:0 0 6px;font:400 10px VexMono,monospace;letter-spacing:.38em;color:#6fb4ff;border-bottom:1px solid rgba(120,190,255,.25);padding-bottom:4px}
.bpP .r{display:flex;gap:6px;white-space:nowrap}.bpP .r b{font-weight:400;color:#78aee6}.bpP .r i{flex:1;border-bottom:1px dotted rgba(120,190,255,.25);margin-bottom:4px}.bpP .r span{color:#eaf6ff}
.bpP .bar{height:3px;background:rgba(120,190,255,.15);margin:1px 0 5px}.bpP .bar u{display:block;height:100%;background:#7cc4ff;box-shadow:0 0 6px #4aa8ff}
#bpTitle{left:62px;top:12px;right:34vw;display:flex;align-items:center;gap:14px;border:1px solid rgba(120,190,255,.3);padding:5px 10px;background:rgba(4,22,52,.55)}
#bpTitle .t{letter-spacing:.42em;color:#eaf6ff;font-size:11.5px}#bpTitle .s{color:#6fb4ff;font-size:10px;letter-spacing:.2em;flex:1}
#bpTitle button{font:10px VexMono,monospace;letter-spacing:.24em;color:#a9d6ff;background:transparent;border:1px solid rgba(120,190,255,.35);padding:3px 9px;cursor:pointer;pointer-events:auto}
#bpTitle button.on,#bpTitle button:hover{background:rgba(80,160,255,.18);color:#fff;border-color:#7cc4ff}
#bpL{left:62px;top:56px;width:min(360px,21vw)}
#bpL .cols{display:grid;grid-template-columns:1fr 1fr;gap:0 14px}
#bpR{right:28px;top:14px;width:min(320px,19vw);text-align:right}
#bpR .clk{font-size:clamp(34px,3vw,60px);letter-spacing:.06em;color:#eaf6ff;line-height:1;text-shadow:0 0 14px rgba(80,160,255,.8)}
#bpR .dt{font-size:10.5px;letter-spacing:.32em;color:#6fb4ff;margin:4px 0 10px}
#bpR svg{width:118px;height:118px;display:block;margin:0 0 8px auto}
#bpR .r{text-align:left}
#bpRad{transform-origin:59px 59px;animation:bpSw 4s linear infinite}@keyframes bpSw{to{transform:rotate(360deg)}}
#bpCard{min-width:360px;transform:translateX(-50%);border:1px solid rgba(124,196,255,.75);background:linear-gradient(180deg,rgba(14,52,110,.7),rgba(4,22,52,.82));padding:10px 16px 12px;box-shadow:0 0 22px rgba(60,140,255,.35),inset 0 0 18px rgba(60,140,255,.18)}
#bpCard .lab{font-size:10px;letter-spacing:.4em;color:#7cc4ff}#bpCard .big{font-size:clamp(30px,2.6vw,50px);color:#fff;letter-spacing:.04em;line-height:1.1;text-shadow:0 0 16px rgba(80,160,255,.9)}
#bpCard .big small{font-size:.38em;color:#9fd0ff;letter-spacing:.2em;margin-left:8px}
#bpCard .subs{display:flex;gap:18px;margin-top:6px;border-top:1px solid rgba(124,196,255,.3);padding-top:6px}#bpCard .subs div{display:flex;flex-direction:column}#bpCard .subs b{font-weight:400;font-size:9.5px;letter-spacing:.3em;color:#6fb4ff}#bpCard .subs span{color:#eaf6ff;font-size:15px}
#bpBL{left:62px;bottom:30px;width:min(360px,22vw)}
#bpBL .ic{display:flex;gap:8px;margin-bottom:6px}#bpBL .ic svg{width:22px;height:22px;stroke:#7cc4ff;fill:none;stroke-width:1.2;border:1px solid rgba(120,190,255,.3);padding:3px}
#bpF{left:0;right:0;bottom:0;height:18px;border-top:1px solid rgba(120,190,255,.25);background:rgba(4,22,52,.7);display:flex!important;justify-content:space-between;padding:0 14px;font-size:9.5px;line-height:18px;letter-spacing:.3em;color:#6fb4ff}
body:not(.bp) #bpF{display:none!important}
#bpRing .c{fill:none;stroke:#8cc8ff;stroke-width:1;opacity:.75}#bpRing .c2{fill:none;stroke:#8cc8ff;stroke-width:1;opacity:.3}#bpRing .tk{stroke:#8cc8ff;stroke-width:1;opacity:.55}
#bpRing .x{stroke:#8cc8ff;stroke-width:1;opacity:.45}#bpRing text{fill:#7cc4ff;font:9px VexMono,monospace;letter-spacing:.2em}
#bpRing .rot{animation:bpR 80s linear infinite}@keyframes bpR{to{transform:rotate(360deg)}}
body.lowfx #bpRing .rot,body.lowfx #bpRad{animation:none}`;
document.head.appendChild(st);
const mk=(id,cls,html)=>{const e=document.createElement("div");e.id=id;if(cls)e.className=cls;if(html)e.innerHTML=html;document.body.appendChild(e);return e;};
const grid=mk("bpGrid","thgrid");document.body.classList.add("main");const gl=document.getElementById("gl");gl&&gl.after(grid);
const ring=document.createElementNS(NS,"svg");ring.id="bpRing";document.body.appendChild(ring);
const TABS=[["home","HOME"],["system","SYSTEM"],["activity","ACTIVITY"],["memory","MEMORY"]];
const title=mk("bpTitle","bpP",`<span class="t">V.E.X</span><span class="s">// HOLOGRAPHIC INTELLIGENCE SYSTEM · LOCAL CORE</span>`+TABS.map(t=>`<button data-t="${t[0]}">${t[1]}</button>`).join("")+`<button data-x="1">EXIT FULL</button>`);
title.querySelectorAll("button[data-t]").forEach(b=>b.onclick=()=>{const x=document.querySelector(`#dtabs button[data-t="${b.dataset.t}"]`);x&&x.click();});
title.querySelector("[data-x]").onclick=()=>{const h=[...document.querySelectorAll("header *")].find(e=>/fullscreen/i.test(e.textContent||"")&&e.children.length==0);h&&h.click();};
const L=mk("bpL","bpP"),R=mk("bpR","bpP"),C=mk("bpCard","bpP"),BL=mk("bpBL","bpP"),F=mk("bpF","bpP");
const row=(k,v)=>`<div class="r"><b>${E(k)}</b><i></i><span>${E(v)}</span></div>`,bar=p=>`<div class="bar"><u style="width:${Math.max(0,Math.min(100,+p||0))}%"></u></div>`;
const ICONS=['<path d="M4 12h16M12 4v16"/><circle cx="12" cy="12" r="7"/>','<rect x="4" y="6" width="16" height="12"/><path d="M4 10h16"/>','<path d="M4 18l5-6 4 3 7-9"/>','<circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>','<path d="M6 4h12v16H6zM9 8h6M9 12h6M9 16h4"/>'];
let D={},geo="",t0=Date.now();
function active(){const ai=document.body.classList.contains("aionly"),tab=(document.querySelector(".dash.hud")||{dataset:{}}).dataset.tab||"home";return !ai&&tab=="home";}
function ringBuild(){const o=document.getElementById("orb");if(!o)return;const r=o.getBoundingClientRect();if(!r.width)return;const cx=r.left+r.width/2,cy=r.top+r.height/2,R0=Math.min(r.width*0.5,innerHeight*0.30);
 const key=[innerWidth,innerHeight,cx|0,cy|0,R0|0].join();if(key==geo)return;geo=key;let tk="";for(let i=0;i<120;i++){const a=i*3*Math.PI/180,L=i%10==0?12:(i%5==0?7:4);tk+=`M${cx+Math.cos(a)*R0},${cy+Math.sin(a)*R0}L${cx+Math.cos(a)*(R0+L)},${cy+Math.sin(a)*(R0+L)}`;}
 const X=(x1,y1,x2,y2)=>`<line class="x" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`,g=R0*0.18,ext=R0*1.45;
 ring.setAttribute("viewBox",`0 0 ${innerWidth} ${innerHeight}`);
 ring.innerHTML=`<circle class="c" cx="${cx}" cy="${cy}" r="${R0}"/><circle class="c2" cx="${cx}" cy="${cy}" r="${R0*1.12}" stroke-dasharray="2 6"/><circle class="c2" cx="${cx}" cy="${cy}" r="${R0*0.72}"/>
  <g class="rot" style="transform-origin:${cx}px ${cy}px"><path class="tk" d="${tk}"/></g>
  ${X(cx-ext,cy,cx-R0-g,cy)}${X(cx+R0+g,cy,cx+ext,cy)}${X(cx,cy-ext*0.9,cx,cy-R0-g)}${X(cx,cy+R0+g,cx,cy+R0*1.25)}
  ${X(cx-R0*0.2,cy,cx-R0*0.08,cy)}${X(cx+R0*0.08,cy,cx+R0*0.2,cy)}${X(cx,cy-R0*0.2,cx,cy-R0*0.08)}${X(cx,cy+R0*0.08,cx,cy+R0*0.2)}
  <text x="${cx+R0+8}" y="${cy-6}">090</text><text x="${cx-R0-34}" y="${cy-6}">270</text><text x="${cx+6}" y="${cy-R0-8}">000</text>
  <text x="${cx-ext}" y="${cy+14}">X ${(cx|0).toString().padStart(4,"0")}</text><text x="${cx+ext-58}" y="${cy+14}">Y ${(cy|0).toString().padStart(4,"0")}</text>`;
 C.style.left=cx+"px";C.style.top=(cy+R0*1.18)+"px";}
function fmtUp(s){s=+s||0;return `${String(s/86400|0)}D ${String(s/3600%24|0).padStart(2,"0")}:${String(s/60%60|0).padStart(2,"0")}`;}
function fill(){const s=D.st||{},w=D.wx||{},chan=D.chan||"";const m=chan.match(/([\d.,]+\s*[KkMm]?)\s*subs?.*?([\d,]+)\s*videos?/i);
 L.innerHTML=`<h6>SYSTEM TELEMETRY</h6><div class="cols"><div>${row("CPU",(s.cpu??"--")+"%")}${bar(s.cpu)}${row("RAM",(s.ram??"--")+"%")}${bar(s.ram)}${row("GPU",(s.gpu??"--")+"%")}${bar(s.gpu)}</div><div>${row("VRAM",(s.vram??"--")+"%")}${bar(s.vram)}${row("TEMP",s.gpu_temp!=null?s.gpu_temp+"°C":"--")}${bar(s.gpu_temp)}${row("DISK",(s.disk_pct??"--")+"%")}${bar(s.disk_pct)}</div></div>
  <h6 style="margin-top:8px">CORE STATUS</h6>${row("MODE",String(D.mode||"blue").toUpperCase())}${row("BRAIN",String(D.llm||"--").toUpperCase())}${row("SPEECH",String(D.stt||"--").toUpperCase())}${row("MIC",String(D.mic||"--").toUpperCase())}${row("NET ↓ / ↑",(s.net_down??"--")+" / "+(s.net_up??"--"))}${row("RAM INSTALLED",(s.ram_total??"--")+" GB")}${row("DISK FREE",(s.disk_free??"--")+" GB")}${row("PC UPTIME",fmtUp(D.up))}
  <h6 style="margin-top:8px">TASK QUEUE</h6>${(D.todos||[]).length?(D.todos||[]).map((t,i)=>row(String(i+1).padStart(2,"0"),t.slice(0,30))).join(""):row("--","NO OPEN TASKS")}`;
 const rr=document.getElementById("bpRList");if(rr)rr.innerHTML=`${row("WEATHER",w.temp!=null?Math.round(w.temp)+"°"+String(w.unit||"F").replace("°","")+" "+String(w.desc||"").toUpperCase():"--")}${row("HI / LO",w.hi!=null?Math.round(w.hi)+"° / "+Math.round(w.lo)+"°":"--")}${row("WIND",w.wind!=null?w.wind+"":"--")}${(D.rem||[]).slice(0,2).map(x=>row("REMIND",x.slice(0,22))).join("")||row("REMIND","NONE")}`;
 const cpu=+s.cpu||0,ram=+s.ram||0,gpu=+s.gpu||0,hl=Math.max(0,Math.min(100,Math.round(100-0.22*cpu-0.22*ram-0.12*gpu-((+s.gpu_temp||0)>80?15:0))));
 C.innerHTML=`<div class="lab">SYSTEM HEALTH</div><div class="big">${hl}%<small>ALL SYSTEMS</small></div><div class="subs"><div><b>TASKS</b><span>${(D.todos||[]).length}</span></div><div><b>CPU</b><span>${s.cpu??"--"}%</span></div><div><b>SESSION</b><span>${fmtUp((Date.now()-t0)/1000)}</span></div><div><b>MODE</b><span>${E(String(D.mode||"blue").toUpperCase())}</span></div></div>`;
 title.querySelectorAll("button[data-t]").forEach(b=>b.classList.toggle("on",b.dataset.t=="home"));window.vexTheme&&vexTheme(D);}
R.innerHTML=`<div class="clk" id="bpClk">--:--:--</div><div class="dt" id="bpDt">--</div><svg viewBox="0 0 118 118"><circle cx="59" cy="59" r="56" fill="none" stroke="#7cc4ff" stroke-opacity=".6"/><circle cx="59" cy="59" r="38" fill="none" stroke="#7cc4ff" stroke-opacity=".3"/><circle cx="59" cy="59" r="20" fill="none" stroke="#7cc4ff" stroke-opacity=".3"/>
 <path d="M59 3V115M3 59H115" stroke="#7cc4ff" stroke-opacity=".3"/><text x="55" y="12" fill="#7cc4ff" font-size="8">N</text><g id="bpRad"><path d="M59 59 L59 3 A56 56 0 0 1 98 19 Z" fill="url(#bpG)"/></g>
 <defs><linearGradient id="bpG" x1="0" x2="1"><stop offset="0" stop-color="#4aa8ff" stop-opacity=".0"/><stop offset="1" stop-color="#4aa8ff" stop-opacity=".45"/></linearGradient></defs>
 <circle cx="80" cy="40" r="2" fill="#bfe3ff"/><circle cx="40" cy="78" r="1.6" fill="#bfe3ff"/><circle cx="70" cy="86" r="1.4" fill="#bfe3ff"/></svg><div id="bpRList"></div>`;
BL.innerHTML=`<div class="ic">${ICONS.map(p=>`<svg viewBox="0 0 24 24">${p}</svg>`).join("")}</div><div id="bpCo"></div>`;
F.innerHTML=`<span>VEX CORE // BLUEPRINT VIEW</span><span id="bpFm">LINK SECURE · LOCAL ONLY</span><span id="bpFv">BUILD --</span>`;
function tick(){const on=active();document.body.classList.toggle("bp",on);window.__bp=on;if(!on){geo="";window.vexTheme&&vexTheme({mode:"blue"});return;}ringBuild();const d=new Date();
 document.getElementById("bpClk").textContent=d.toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:false});
 document.getElementById("bpDt").textContent=d.toLocaleDateString([],{weekday:"short",day:"2-digit",month:"short",year:"numeric"}).toUpperCase();
 const m=window.__mouse||{x:0,y:0};document.getElementById("bpCo").innerHTML=row("CURSOR",`X ${((m.x+1)/2*innerWidth|0).toString().padStart(4,"0")} · Y ${((m.y+1)/2*innerHeight|0).toString().padStart(4,"0")}`)+row("CORE SECTOR","B-07 · GRID 24")+row("FRAME",`${innerWidth}×${innerHeight}`)+row("RENDER",window.__threeOK||"2D");
 const v=document.querySelector("#roBR");document.getElementById("bpFv").textContent="BUILD "+((v&&v.textContent)||"").replace(/^v/,"");}
async function poll(){if(!active())return;try{D=await A().jhud();fill();}catch(e){}}
setInterval(tick,1000);setInterval(poll,2500);setTimeout(()=>{tick();poll();},700);addEventListener("resize",()=>geo="");
})();
