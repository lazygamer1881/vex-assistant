// Vex 3.5 purpose modes: panel that changes with the colour protocol (full view + AI-only card), stealth privacy, chill ambience.
(function(){
const A=()=>window.pywebview&&window.pywebview.api,E=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const st=document.createElement("style");st.textContent=`
#wMode{grid-area:rem;display:none!important}
body[data-mode]:not([data-mode=blue]) .dash.hud[data-tab=home] #wMode{display:block!important}
body[data-mode]:not([data-mode=blue]) .dash.hud[data-tab=home] #wRem{display:none!important}
#vxModeCard{position:fixed;left:3vw;top:50%;transform:translateY(-50%) translateX(-20px);width:clamp(260px,19vw,380px);z-index:40;opacity:0;pointer-events:none;transition:opacity .7s,transform .7s;
 font-family:VexMono,monospace;color:#bff8ff;background:linear-gradient(160deg,rgba(6,30,40,.72),rgba(2,10,16,.55));border:1px solid #19d8ff44;box-shadow:0 0 30px #19d8ff22 inset,0 0 24px #0008;padding:18px 20px;
 clip-path:polygon(0 0,calc(100% - 18px) 0,100% 18px,100% 100%,18px 100%,0 calc(100% - 18px))}
body.aionly[data-mode]:not([data-mode=blue]) #vxModeCard{opacity:1;transform:translateY(-50%);pointer-events:auto}
.vxm h5{margin:0 0 4px;font-weight:400;letter-spacing:.42em;font-size:11px;color:#5ff3ff}
.vxm .mt{font-size:clamp(18px,1.4vw,26px);letter-spacing:.18em;color:#e8fdff;text-shadow:0 0 12px #19d8ff;margin-bottom:10px}
.vxm .r{display:flex;justify-content:space-between;gap:10px;padding:5px 0;border-bottom:1px dashed #19d8ff22;font-size:12.5px}
.vxm .r b{font-weight:400;color:#7fdcec;letter-spacing:.12em}.vxm .r span{color:#effdff;text-align:right}
.vxm .tag{display:inline-block;margin:6px 6px 0 0;padding:3px 8px;border:1px solid #19d8ff55;font-size:10.5px;letter-spacing:.18em;color:#9ff6ff}
.vxm .bt{display:inline-block;margin:8px 6px 0 0;padding:6px 11px;border:1px solid #5ff3ff88;background:#062a36aa;color:#dffcff;font:11px VexMono,monospace;letter-spacing:.14em;cursor:pointer}
.vxm .bt:hover{background:#0b4656}
.vxm .bar{height:6px;background:#0b2a36;margin:3px 0 8px;position:relative;overflow:hidden}.vxm .bar i{position:absolute;left:0;top:0;bottom:0;background:#5ff3ff;box-shadow:0 0 10px #19d8ff}
.vxm .big{font-size:clamp(30px,2.6vw,52px);letter-spacing:.08em;color:#effdff;text-shadow:0 0 18px #19d8ff;margin:4px 0}
.vxm .ck{display:flex;gap:8px;align-items:center;font-size:12.5px;padding:3px 0;cursor:pointer}.vxm .ck i{width:11px;height:11px;border:1px solid #5ff3ff;display:inline-block}.vxm .ck.on i{background:#5ff3ff;box-shadow:0 0 8px #19d8ff}.vxm .ck.on{opacity:.6;text-decoration:line-through}
.vxm .sub{font-size:11px;color:#7fbfcc;letter-spacing:.08em;margin-top:6px}
body[data-mode=black] #wx,body[data-mode=black] #wWx,body[data-mode=black] #todo,body[data-mode=black] #rem,body[data-mode=black] #log,body[data-mode=black] #recent,body[data-mode=black] #mem2,body[data-mode=black] #notes,body[data-mode=black] #vxTerm,body[data-mode=black] .live .txt{filter:blur(9px)!important;user-select:none}
body[data-mode=black] #orb{opacity:.6}
#vxAmb{position:fixed;inset:-10%;pointer-events:none;z-index:1;opacity:0;transition:opacity 2s;background:
 radial-gradient(40% 30% at 20% 30%,#19d8ff22,transparent 70%),radial-gradient(35% 35% at 80% 70%,#8b5cf622,transparent 70%),radial-gradient(30% 25% at 60% 20%,#22d3ee1a,transparent 70%);animation:vxAmb 24s ease-in-out infinite alternate}
body[data-mode=pink] #vxAmb{opacity:1}
@keyframes vxAmb{0%{transform:translate(0,0) rotate(0)}50%{transform:translate(3%,-2%) rotate(6deg)}100%{transform:translate(-3%,2%) rotate(-5deg)}}
#vxModeTag{position:fixed;top:10px;right:16px;z-index:45;font:10px VexMono,monospace;letter-spacing:.4em;color:#5ff3ffcc;pointer-events:none}`;
document.head.appendChild(st);
const card=document.createElement("div");card.id="vxModeCard";card.className="vxm";document.body.appendChild(card);
const amb=document.createElement("div");amb.id="vxAmb";document.body.appendChild(amb);
const tag=document.createElement("div");tag.id="vxModeTag";document.body.appendChild(tag);
let w=null;function ensureW(){if(w&&document.body.contains(w))return w;const d=document.querySelector(".dash");if(!d)return null;w=document.createElement("div");w.className="w vxm";w.id="wMode";w.dataset.t="home";
 const rem=document.getElementById("wRem");rem?rem.after(w):d.appendChild(w);return w;}
const CK=["Mic + game audio levels","Quest charged","OBS scene + output folder","Disk space OK","Notifications muted","Hook for first 10 seconds"];
let ck=JSON.parse(localStorage.vxCk||"[]");
const row=(k,v)=>`<div class="r"><b>${E(k)}</b><span>${E(v)}</span></div>`,bar=p=>`<div class="bar"><i style="width:${Math.max(0,Math.min(100,+p||0))}%"></i></div>`;
const fmt=s=>String(s/60|0).padStart(2,"0")+":"+String(s%60|0).padStart(2,"0");
const name0=()=>"";let last=null,focusEnd=0;
function render(d){const m=d.mode;let h=`<h5>MODE // ${E(m.toUpperCase())}</h5><div class="mt">${E(d.name.toUpperCase())}</div>`;
 if(m=="red"){const s=d.stats||{};h+=row("GPU LOAD",(s.gpu??"--")+"%")+bar(s.gpu)+row("GPU TEMP",s.gpu_temp!=null?s.gpu_temp+"°C":"--")+bar(s.gpu_temp)+row("VRAM",(s.vram??"--")+"%")+bar(s.vram)+row("CPU",(s.cpu??"--")+"%")+row("FPS","Steam overlay · Shift+Tab")
  +`<div><span class="tag">FX PAUSED</span><span class="tag">ALERTS MUTED</span><span class="tag">AI ON CPU</span></div><div><span class="bt" data-o="gorilla tag">LAUNCH GORILLA TAG</span><span class="bt" data-o="steam">STEAM</span></div>`;}
 else if(m=="green"){const f=d.focus||{};focusEnd=f.left?Date.now()+f.left*1000:0;h+=`<div class="big" id="vxFocus">${f.left?fmt(f.left):"--:--"}</div><div class="sub">${f.left?"FOCUS · "+f.mins+" MIN SESSION":'SAY "FOCUS 25 MINUTES"'}</div>`
  +`<h5 style="margin-top:12px">STUDY NOTES</h5>`+((d.notes||[]).length?(d.notes||[]).slice(0,4).map(n=>row("›",n)).join(""):`<div class="sub">Say "study" and a topic.</div>`)
  +`<h5 style="margin-top:12px">HOMEWORK HELP</h5><div class="sub">"Explain step by step…" · "Quiz me on…" · "Check my answer…"</div><div class="sub">Distractions get a reminder, never closed.</div>`;}
 else if(m=="purple"){h+=`<div><span class="tag">OBS · CAPCUT · STUDIO ON YOUR COMMAND</span></div>`
  +`<h5 style="margin-top:12px">VIDEO CHECKLIST</h5>`+CK.map((c,i)=>`<div class="ck ${ck[i]?"on":""}" data-c="${i}"><i></i>${E(c)}</div>`).join("");}
 else if(m=="gold"){
  h+=`<h5 style="margin-top:12px">GOALS</h5>`+((d.goals||[]).length?(d.goals||[]).slice(-6).map(x=>`<div class="ck ${x.done?"on":""}"><i></i>${E(x.text)}</div>`).join(""):`<div class="sub">Say "add goal finish my next video".</div>`);}
 else if(m=="pink"){const p=d.playing||{};h+=`<h5>NOW PLAYING</h5><div class="big" style="font-size:clamp(18px,1.5vw,28px)">${E(p.title||"Nothing playing")}</div><div class="sub">${E(p.artist||"")}</div><div><span class="bt" data-o="spotify">SPOTIFY</span></div><div class="sub" style="margin-top:12px">Ambient visuals on. Say "blue mode" to return.</div>`;}
 else if(m=="white"){h+=`<div class="sub">Full diagnostic runs when this mode starts.</div><div><span class="bt" data-s="1">RUN SCAN AGAIN</span></div>`;}
 else if(m=="black"){h+=`<div class="big" id="vxBlk">${E(new Date().toLocaleTimeString([],{hour:"numeric",minute:"2-digit"}))}</div><div><span class="tag">VOICE LOW</span><span class="tag">ALERTS MUTED</span><span class="tag">INFO HIDDEN</span><span class="tag">SFX OFF</span></div><div class="sub" style="margin-top:10px">Say "goodnight" for tomorrow's rundown.</div>`;}
 return h;}
function bind(el){el.querySelectorAll("[data-o]").forEach(b=>b.onclick=()=>A().mode_open(b.dataset.o));el.querySelectorAll("[data-s]").forEach(b=>b.onclick=()=>A().mode_scan());
 el.querySelectorAll("[data-c]").forEach(b=>b.onclick=()=>{const i=+b.dataset.c;ck[i]=!ck[i];localStorage.vxCk=JSON.stringify(ck);b.classList.toggle("on");});}
let greetName="";
async function poll(){try{const d=await A().mode_panel();document.body.dataset.mode=d.mode;tag.textContent=d.mode=="blue"?"":"◆ "+d.name.toUpperCase()+" MODE";
 const key=JSON.stringify(d);if(key!==last){last=key;const h=render(d);card.innerHTML=h;bind(card);const ww=ensureW();if(ww){ww.innerHTML=h;bind(ww);}}
 const g=document.getElementById("greet");if(g){if(d.mode=="black"){if(/,\s*\S/.test(g.textContent)){greetName=g.textContent;g.textContent=g.textContent.replace(/,\s*[^,]+$/,"");}}else if(greetName&&!/,/.test(g.textContent)){g.textContent=greetName;greetName="";}}
}catch(e){}}
setInterval(poll,2500);setTimeout(poll,800);
setInterval(()=>{document.querySelectorAll("#vxFocus").forEach(x=>{if(focusEnd){const s=Math.max(0,(focusEnd-Date.now())/1000);x.textContent=fmt(s);}});},1000);
})();
