// Vex 4.2 dashboard tabs: every tab gets its own content + layout, a clear active-tab bar and a short transition.
// Home = reactor HUD. System = gauges, top processes, drives, network. Activity = timeline. Memory = searchable list.
// Works by mouse, hand (palm swipe / pinch-click) and voice ("show system tab"). Original art, no sounds.
(function(){
const A=()=>window.pywebview&&window.pywebview.api,$=s=>document.querySelector(s);
const E=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const LOG=m=>{try{window.vexUiLog&&vexUiLog(m)}catch(e){}};
const TABS=[["home","Home"],["system","System"],["activity","Activity"],["memory","Memory"]];
const dash=$(".dash.hud");if(!dash)return;
const st=document.createElement("style");st.textContent=`
#t42{position:fixed;top:clamp(46px,5.2vh,78px);left:50%;transform:translateX(-50%);z-index:30;display:none;gap:4px;padding:4px;border:1px solid rgba(95,243,255,.22);background:rgba(3,12,22,.82);border-radius:3px}
body:not(.aionly):not(.bp) #t42{display:flex}
#t42 button{position:relative;font:400 clamp(12px,.8rem,18px) VexMono,ui-monospace,monospace;letter-spacing:.28em;text-transform:uppercase;color:#8fb8c8;background:transparent;border:0;padding:.55em 1.5em .65em;cursor:pointer;transition:color .2s,background .2s}
#t42 button:hover{color:#e6fbff;background:rgba(95,243,255,.06)}
#t42 button.on{color:#fff;background:rgba(95,243,255,.13);text-shadow:0 0 8px var(--vx-a,#5fd4ff)}
#t42 .ink{position:absolute;bottom:2px;height:2px;background:var(--vx-a,#5fd4ff);box-shadow:0 0 8px var(--vx-a,#5fd4ff);transition:left .3s cubic-bezier(.2,.8,.2,1),width .3s cubic-bezier(.2,.8,.2,1);pointer-events:none}
body.lowfx #t42 .ink{transition:none}
/* non-home tabs: the reactor/3D core step back, panels get solid glass so the content reads clearly */
body:not([data-tab42=home]) #vxJ{display:none!important}
body:not(.aionly):not([data-tab42=home]) #gl{opacity:.16!important;transition:opacity .4s}
body:not(.aionly) .dash.hud:not([data-tab=home]){padding-top:clamp(64px,8vh,120px)!important}
body:not(.aionly) .dash.hud:not([data-tab=home]) .w{background:linear-gradient(180deg,rgba(6,22,36,.92),rgba(3,13,23,.92))!important;border:1px solid rgba(95,243,255,.16)!important;border-radius:4px!important}
.dash.hud[data-tab=system]{grid-template-columns:minmax(0,1.15fr) minmax(0,1fr) minmax(0,1fr)!important;grid-template-rows:minmax(0,1.15fr) minmax(0,1fr) minmax(0,.62fr)!important;
 grid-template-areas:"gau gau proc" "drv net proc" "sys idx home"!important}
.dash.hud[data-tab=activity]{grid-template-columns:minmax(0,1.5fr) minmax(0,1fr)!important;grid-template-rows:auto minmax(0,1fr) minmax(0,1fr) minmax(0,.8fr)!important;
 grid-template-areas:"sum sum" "tl feed" "tl log" "tl recent"!important}
.dash.hud[data-tab=memory]{grid-template-columns:minmax(0,1.7fr) minmax(0,1fr)!important;grid-template-rows:minmax(0,1fr)!important;grid-template-areas:"mem notes"!important}
#w42g{grid-area:gau}#w42p{grid-area:proc}#w42d{grid-area:drv}#w42n{grid-area:net}#w42s{grid-area:sum}#w42t{grid-area:tl}#w42m{grid-area:mem}
.dash.hud[data-tab=activity] #wLog{grid-area:log}
body:not(.unfolding) .dash.hud.t42 .w:not(.hero){animation:t42in .42s cubic-bezier(.2,.8,.2,1) backwards!important}
body:not(.unfolding) .dash.hud.t42 .w:nth-child(3n+1){animation-delay:.04s!important}body:not(.unfolding) .dash.hud.t42 .w:nth-child(3n+2){animation-delay:.09s!important}body:not(.unfolding) .dash.hud.t42 .w:nth-child(3n){animation-delay:.14s!important}
@keyframes t42in{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
body.lowfx:not(.unfolding) .dash.hud.t42 .w:not(.hero){animation:t42f .25s ease-out backwards!important}@keyframes t42f{from{opacity:0}to{opacity:1}}
.w42 h4 small{float:right;letter-spacing:.12em;color:#6f93a3;text-transform:none;font-size:.85em}
.g42{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:clamp(6px,.8vw,18px);align-items:center;flex:1;min-height:0}
.g42 .gg{display:flex;flex-direction:column;align-items:center;min-width:0}
.g42 svg{width:100%;max-width:150px;aspect-ratio:1}
.g42 .tr{fill:none;stroke:rgba(95,243,255,.12);stroke-width:9}
.g42 .vl{fill:none;stroke:var(--vx-a,#5fd4ff);stroke-width:9;stroke-linecap:butt;transition:stroke-dasharray .9s cubic-bezier(.2,.8,.2,1);filter:drop-shadow(0 0 4px var(--vx-a,#5fd4ff))}
.g42 .vl.hot{stroke:#ffb340;filter:drop-shadow(0 0 4px #ff9a1a)}
.g42 text{fill:#eafcff;font:400 20px VexMono,monospace;text-anchor:middle}
.g42 .gl{font:400 clamp(11px,.75rem,16px) VexMono,monospace;letter-spacing:.3em;color:#7fd8ea;margin-top:4px}
.g42 .gs{font-size:.8rem;color:#7d9aa8;min-height:1.2em}
.i42{display:flex;flex-wrap:wrap;gap:6px 18px;margin-top:10px;font-size:.9rem;color:#9cc3d1}.i42 b{color:#eafcff;font-weight:400}
.t42tb{width:100%;border-collapse:collapse;font-size:.92rem}.t42tb td{padding:.36em .3em;border-bottom:1px solid rgba(95,243,255,.07);white-space:nowrap}
.t42tb td:first-child{max-width:0;width:55%;overflow:hidden;text-overflow:ellipsis;color:#e6fbff}.t42tb td.n{text-align:right;color:#9cc3d1;font-family:VexMono,monospace}
.t42tb .mb{display:inline-block;width:52px;height:4px;background:rgba(95,243,255,.12);vertical-align:middle;margin-left:6px}.t42tb .mb i{display:block;height:100%;background:var(--vx-a,#5fd4ff)}
.d42{margin-bottom:.9em}.d42 .h{display:flex;justify-content:space-between;font-size:.92rem;color:#e6fbff}.d42 .h span{color:#8fb0be}
.d42 .b{height:7px;background:rgba(95,243,255,.1);margin-top:5px}.d42 .b i{display:block;height:100%;background:var(--vx-a,#5fd4ff);box-shadow:0 0 6px var(--vx-a,#5fd4ff)}.d42 .b i.hot{background:#ffb340;box-shadow:0 0 6px #ff9a1a}
.n42{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px}.n42 div{border:1px solid rgba(95,243,255,.14);padding:.5em .7em}.n42 b{display:block;font:400 1.5rem VexMono,monospace;color:#eafcff}.n42 span{font-size:.75rem;letter-spacing:.25em;color:#7fd8ea}
.s42{display:flex;gap:clamp(8px,1vw,22px)}.s42 div{flex:1;border-left:2px solid var(--vx-a,#5fd4ff);padding:.2em .8em}.s42 b{display:block;font:400 1.7rem VexMono,monospace;color:#eafcff}.s42 span{font-size:.75rem;letter-spacing:.25em;color:#7fd8ea}
.tl42{position:relative;overflow:auto;flex:1;min-height:0;padding-left:16px}
.tl42:before{content:"";position:absolute;left:5px;top:4px;bottom:4px;width:1px;background:rgba(95,243,255,.25)}
.tl42 .it{position:relative;padding:.25em 0 .7em .9em}.tl42 .it:before{content:"";position:absolute;left:-15px;top:.55em;width:9px;height:9px;border-radius:50%;background:#071a28;border:2px solid var(--vx-a,#5fd4ff)}
.tl42 .it.task:before{border-color:#7ee0a0}.tl42 .it.fail:before{border-color:#ff7b7b}
.tl42 .tm{font:400 .8rem VexMono,monospace;color:#7fd8ea;letter-spacing:.12em}.tl42 .tx{color:#e6fbff;font-size:.95rem;line-height:1.4}
.tl42 .k{font-size:.7rem;letter-spacing:.2em;color:#6f93a3;margin-left:8px;text-transform:uppercase}
.m42bar{display:flex;gap:8px;margin-bottom:10px}.m42bar input{flex:1;min-width:0;background:rgba(95,243,255,.05);border:1px solid rgba(95,243,255,.22);color:#eafcff;padding:.55em .8em;font:inherit;font-size:.95rem;border-radius:3px}
.m42bar button,.m42 .x,.m42 .y,.m42 .n{background:rgba(95,243,255,.08);border:1px solid rgba(95,243,255,.3);color:#dffaff;padding:.45em .9em;cursor:pointer;font:inherit;font-size:.85rem;border-radius:3px}
.m42l{overflow:auto;flex:1;min-height:0}.m42{display:flex;align-items:center;gap:10px;padding:.55em .2em;border-bottom:1px solid rgba(95,243,255,.08)}
.m42 .tx{flex:1;color:#e6fbff;font-size:.98rem;line-height:1.35}.m42 .tx mark{background:rgba(95,243,255,.25);color:#fff}
.m42 .x{opacity:.65}.m42:hover .x{opacity:1}.m42 .x:hover{border-color:#ff7b7b;color:#ffd0d0}.m42 .y{border-color:#ff7b7b;color:#ffd0d0}.m42 .q{font-size:.85rem;color:#ffd0d0}
.m42c{font-size:.8rem;color:#7d9aa8;letter-spacing:.1em;margin-bottom:6px}`;
document.head.appendChild(st);
// ---- panels
const mkw=(id,tab,html)=>{const w=document.createElement("div");w.className="w w42";w.id=id;w.dataset.t=tab;w.innerHTML=html;dash.appendChild(w);return w;};
["wStats","wMem"].forEach(id=>{const w=document.getElementById(id);if(w)w.dataset.t="off";});
mkw("w42g","system",`<h4>System gauges <small id="g42u"></small></h4><div class="g42" id="g42"></div><div class="i42" id="g42i"></div>`);
mkw("w42p","system",`<h4>Top processes <small id="p42c"></small></h4><div style="overflow:auto;flex:1;min-height:0"><table class="t42tb" id="p42"></table></div>`);
mkw("w42d","system",`<h4>Drives</h4><div id="d42" style="overflow:auto;flex:1;min-height:0"></div>`);
mkw("w42n","system",`<h4>Network</h4><div class="n42"><div><span>DOWN</span><b id="n42d">--</b></div><div><span>UP</span><b id="n42u">--</b></div></div><table class="t42tb" id="n42"></table>`);
mkw("w42s","activity",`<div class="s42" id="s42"></div>`);
mkw("w42t","activity",`<h4>Timeline <small>what I did · newest first</small></h4><div class="tl42" id="tl42"></div>`);
mkw("w42m","memory",`<h4>Things I remember <small id="m42n"></small></h4><div class="m42bar"><input id="m42q" placeholder="Search memories…"><input id="m42a" placeholder="Add: e.g. my favourite game is…"><button id="m42add">Add</button></div><div class="m42c" id="m42c"></div><div class="m42l" id="m42l"></div>`);
// ---- tab bar with sliding highlight
const bar=document.createElement("div");bar.id="t42";bar.innerHTML=TABS.map(t=>`<button data-t="${t[0]}">${t[1]}</button>`).join("")+`<span class="ink"></span>`;document.body.appendChild(bar);
const ink=bar.querySelector(".ink");
function inkTo(){const b=bar.querySelector("button.on");if(!b||!bar.offsetWidth)return;ink.style.left=b.offsetLeft+"px";ink.style.width=b.offsetWidth+"px";}
bar.querySelectorAll("button").forEach(b=>b.onclick=()=>vexTab(b.dataset.t,"click"));
let cur=dash.dataset.tab||"home";document.body.dataset.tab42=cur;
function hl(t){
 document.querySelectorAll("#dtabs button,#t42 button,#bpTitle button[data-t],#radial button[data-t],#vxJ .mi").forEach(b=>b.classList.toggle("on",b.dataset.t==t));inkTo();}
window.vexTab=function(t,src){t=TABS.some(x=>x[0]==t)?t:"home";const same=t==cur;cur=t;
 if(!same){dash.classList.remove("t42");void dash.offsetWidth;dash.dataset.tab=t;dash.classList.add("t42");}
 document.body.dataset.tab42=t;hl(t);if(!same)LOG("tab -> "+t+" ("+(src||"")+")");refresh();
 try{dispatchEvent(new Event("resize"));}catch(e){}};
// all existing tab UIs (hidden #dtabs used by the blueprint title, reactor menu, radial menu and palm swipe) go through vexTab
document.querySelectorAll("#dtabs button").forEach(b=>b.onclick=()=>vexTab(b.dataset.t,"menu"));
new MutationObserver(()=>{const t=dash.dataset.tab;if(t&&t!=cur)vexTab(t,"sync");}).observe(dash,{attributes:true,attributeFilter:["data-tab"]});
setInterval(()=>{hl(cur);},1500);addEventListener("resize",inkTo);
// ---- System
const gauge=(lab,v,sub,hot)=>{const p=Math.max(0,Math.min(100,+v||0)),C=2*Math.PI*44,on=v!=null&&v!=="";return `<div class="gg"><svg viewBox="0 0 110 110"><circle class="tr" cx="55" cy="55" r="44"/><circle class="vl${hot?" hot":""}" cx="55" cy="55" r="44" transform="rotate(-90 55 55)" stroke-dasharray="${(on?p:0)/100*C} ${C}"/><text x="55" y="62">${on?Math.round(+v)+(lab=="TEMP"?"°":"%"):"--"}</text></svg><div class="gl">${lab}</div><div class="gs">${E(sub||"")}</div></div>`;};
const kb=v=>v==null?"--":(v>=1024?(v/1024).toFixed(1)+" MB/s":Math.round(v)+" KB/s");
const up=s=>{s=+s||0;const d=s/86400|0,h=s/3600%24|0,m=s/60%60|0;return (d?d+"d ":"")+h+"h "+m+"m";};
function drawSystem(d){const s=d.stats||{};
 $("#g42").innerHTML=gauge("CPU",s.cpu,d.ghz?d.ghz+" GHz":"",s.cpu>90)+gauge("RAM",s.ram,s.ram_total?s.ram_total+" GB":"",s.ram>90)+gauge("GPU",s.gpu,"",s.gpu>95)+gauge("VRAM",s.vram,"",s.vram>92)+gauge("TEMP",s.gpu_temp,"GPU",s.gpu_temp>83)+gauge("DISK",s.disk_pct,s.disk_free!=null?s.disk_free+" GB free":"",s.disk_pct>92);
 $("#g42u").textContent=d.uptime?"up "+up(d.uptime):"";
 $("#g42i").innerHTML=`<span>Cores <b>${d.cores||"--"}</b> / threads <b>${d.threads||"--"}</b></span><span>Processes <b>${d.nproc||"--"}</b></span><span>Net <b>↓ ${kb(s.net_down)}</b> <b>↑ ${kb(s.net_up)}</b></span>`;
 const P=d.procs||[],mx=Math.max(1,...P.map(p=>p.mem||0));$("#p42c").textContent="by CPU";
 $("#p42").innerHTML=`<tr><td style="color:#6f93a3">NAME</td><td class="n">CPU</td><td class="n">RAM</td></tr>`+(P.length?P.map(p=>`<tr><td>${E(p.name)}${p.n>1?` <span style="color:#6f93a3">×${p.n}</span>`:""}</td><td class="n">${p.cpu.toFixed(1)}%</td><td class="n">${p.mem>=1024?(p.mem/1024).toFixed(1)+" GB":p.mem+" MB"}<span class="mb"><i style="width:${(p.mem/mx*100).toFixed(0)}%"></i></span></td></tr>`).join(""):`<tr><td>Reading…</td><td></td><td></td></tr>`);
 $("#d42").innerHTML=(d.drives||[]).map(x=>`<div class="d42"><div class="h">${E(x.mount)} <span>${x.used} / ${x.total} GB · ${x.free} GB free</span></div><div class="b"><i class="${x.pct>90?"hot":""}" style="width:${x.pct}%"></i></div></div>`).join("")||"No drives found.";
 const N=d.net||[],td=N.reduce((a,x)=>a+x.down,0),tu=N.reduce((a,x)=>a+x.up,0);$("#n42d").textContent=kb(td);$("#n42u").textContent=kb(tu);
 $("#n42").innerHTML=N.map(x=>`<tr><td>${E(x.name)}</td><td class="n">↓ ${kb(x.down)}</td><td class="n">↑ ${kb(x.up)}</td></tr>`).join("")+(N[0]?`<tr><td style="color:#6f93a3">Since boot</td><td class="n">${N[0].recv} GB</td><td class="n">${N[0].sent} GB</td></tr>`:"");}
// ---- Activity
function drawActivity(d){
 $("#s42").innerHTML=[["REPLIES",d.replies],["TASKS",d.tasks],["ALERTS",d.alerts],["TIMERS",d.timers]].map(x=>`<div><b>${x[1]||0}</b><span>${x[0]}</span></div>`).join("");
 const I=d.items||[];$("#tl42").innerHTML=I.length?I.map(x=>`<div class="it ${E(x.kind)}"><div class="tm">${E(x.t)}<span class="k">${x.kind=="vex"?"reply":E(x.kind)}</span></div><div class="tx">${E(x.text)}</div></div>`).join(""):`<div class="tx" style="color:#7d9aa8">Nothing yet this session. Ask me something and it shows up here.</div>`;}
// ---- Memory (search, add, delete with a yes)
let MEM=[],ask="";
function drawMemory(){const q=($("#m42q").value||"").trim().toLowerCase(),L=MEM.slice().reverse().filter(m=>!q||String(m.text).toLowerCase().includes(q));
 $("#m42n").textContent=MEM.length+" saved";$("#m42c").textContent=q?`${L.length} match${L.length==1?"":"es"} for “${q}”`:"Newest first · saved only on this PC";
 const hi=t=>{const s=E(t);if(!q)return s;const i=s.toLowerCase().indexOf(E(q));return i<0?s:s.slice(0,i)+"<mark>"+s.slice(i,i+E(q).length)+"</mark>"+s.slice(i+E(q).length);};
 $("#m42l").innerHTML=L.length?L.map(m=>`<div class="m42" data-id="${E(m.id)}"><div class="tx">${hi(m.text)}</div>${ask==m.id?`<span class="q">Delete this?</span><button class="y">Yes, delete</button><button class="n">No</button>`:`<button class="x">Delete</button>`}</div>`).join(""):`<div class="tx" style="color:#7d9aa8;padding:.6em 0">${q?"No memories match.":"Nothing saved yet. Say “remember that …” or add one above."}</div>`;}
$("#m42l").addEventListener("click",async e=>{const r=e.target.closest(".m42");if(!r)return;const id=r.dataset.id;
 if(e.target.classList.contains("x")){ask=id;drawMemory();}
 else if(e.target.classList.contains("n")){ask="";drawMemory();}
 else if(e.target.classList.contains("y")){ask="";try{MEM=await A().memory_delete(id);LOG("memory deleted from Memory tab");}catch(err){}drawMemory();}});
$("#m42q").addEventListener("input",drawMemory);
const addM=async()=>{const v=$("#m42a").value.trim();if(!v)return;try{MEM=await A().memory_add(v);}catch(e){}$("#m42a").value="";drawMemory();};
$("#m42add").onclick=addM;$("#m42a").addEventListener("keydown",e=>{if(e.key=="Enter")addM();});
// ---- data refresh for the visible tab only
let busy=false;
async function refresh(){if(busy||document.body.classList.contains("aionly"))return;const a=A();if(!a)return;busy=true;
 try{if(cur=="system"&&a.v42_tab)drawSystem(await a.v42_tab("system"));
  else if(cur=="activity"&&a.v42_tab)drawActivity(await a.v42_tab("activity"));
  else if(cur=="memory"&&a.memory_list){const m=await a.memory_list();if(!ask)MEM=m||[];drawMemory();}}catch(e){}busy=false;}
setInterval(()=>{if(cur!="home"&&cur!="memory")refresh();},2000);setInterval(()=>{if(cur=="memory")refresh();},8000);
// ---- voice: "show system tab" (Python sends tab42 after opening the full view)
const prev=window.vexOn;
window.vexOn=(ev,d)=>{try{if(ev=="tab42"&&d){const go=()=>{window.goPage&&goPage("home");vexTab(d.tab,"voice");};if(document.body.classList.contains("aionly")){window.vexView&&vexView("full","voice");setTimeout(go,600);}else go();}}catch(e){}return prev?prev(ev,d):undefined;};
setTimeout(()=>{hl(cur);inkTo();},800);setTimeout(()=>dash.classList.add("t42"),2500);
})();
