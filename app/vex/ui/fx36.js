// Vex 3.6 visual layer: glass/extruded panels with edge light, circuit traces to panels, hex-grid overlay,
// holographic glitch on text appear, refined typography, micro-data readouts. All off in low-FX (red/gaming).
(function(){
const st=document.createElement("style");st.textContent=`
:root{--vxE:95,243,255}
.dash.hud .w{background:linear-gradient(155deg,rgba(14,48,66,.46),rgba(4,16,26,.62) 42%,rgba(2,10,18,.72))!important;backdrop-filter:blur(10px) saturate(1.35);-webkit-backdrop-filter:blur(10px) saturate(1.35);
 border:1px solid rgba(var(--vxE),.22)!important;border-radius:10px!important;
 box-shadow:0 1px 0 rgba(var(--vxE),.10),0 2px 0 rgba(6,40,52,.9),0 3px 0 rgba(5,32,42,.9),0 4px 0 rgba(4,26,34,.9),0 5px 0 rgba(3,20,28,.9),0 18px 40px rgba(0,0,0,.55),inset 0 1px 0 rgba(200,255,255,.10),inset 0 0 40px rgba(var(--vxE),.045)!important;
 transform:perspective(1400px) rotateX(1.2deg);transition:transform .6s cubic-bezier(.2,.8,.2,1),box-shadow .6s}
.dash.hud .w:hover{transform:perspective(1400px) rotateX(0deg) translateY(-2px)}
.dash.hud .w:not(.hero)::after{content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;padding:1px;
 background:linear-gradient(var(--vxA,120deg),rgba(var(--vxE),0) 30%,rgba(var(--vxE),.9) 46%,rgba(255,255,255,.95) 50%,rgba(var(--vxE),.9) 54%,rgba(var(--vxE),0) 70%) 0 0/300% 300%;
 -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;animation:vxEdge 7s linear infinite;opacity:.55}
.dash.hud .w:not(.hero)::before{content:"";position:absolute;left:8%;right:8%;top:0;height:1px;background:linear-gradient(90deg,transparent,rgba(220,255,255,.75),transparent);pointer-events:none;box-shadow:0 0 12px rgba(var(--vxE),.8)}
.dash.hud .w.hero{background:none!important;backdrop-filter:none;box-shadow:none!important;border-color:transparent!important;transform:none}
@keyframes vxEdge{0%{background-position:100% 0}100%{background-position:-200% 0}}
.w h4{font-family:VexMono,monospace!important;font-weight:400!important;letter-spacing:.34em!important;font-size:11px!important;color:#8ff5ff!important;text-shadow:0 0 8px rgba(var(--vxE),.55)}
.w h4::after{content:"";flex:1;height:1px;margin-left:10px;background:linear-gradient(90deg,rgba(var(--vxE),.45),transparent)}
#greet{font-weight:300!important;letter-spacing:.06em}
.big,#clk{font-variant-numeric:tabular-nums}
#vxHex{position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.5;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='56' height='97' viewBox='0 0 56 97'%3E%3Cpath d='M28 1 L55 17 L55 49 L28 65 L1 49 L1 17 Z M28 65 L28 97' fill='none' stroke='%235ff3ff' stroke-opacity='.10' stroke-width='1'/%3E%3C/svg%3E");
 -webkit-mask:radial-gradient(ellipse 55% 60% at 50% 45%,transparent 18%,#000 45%,transparent 85%);animation:vxHexD 40s linear infinite}
@keyframes vxHexD{to{background-position:56px 97px}}
#vxTr{position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:0}
#vxTr path{fill:none;stroke:rgba(var(--vxE),.16);stroke-width:1.2}
#vxTr path.f{stroke:rgba(200,255,255,.85);stroke-width:1.6;stroke-dasharray:14 220;animation:vxFlow 3.2s linear infinite;filter:drop-shadow(0 0 4px rgba(var(--vxE),1))}
#vxTr circle{fill:#bff8ff;filter:drop-shadow(0 0 5px rgba(var(--vxE),1))}
@keyframes vxFlow{from{stroke-dashoffset:234}to{stroke-dashoffset:0}}
.vxG{animation:vxGl .55s steps(1) both;position:relative}
@keyframes vxGl{0%{opacity:0;clip-path:inset(40% 0 45% 0);text-shadow:-3px 0 rgba(255,60,120,.8),3px 0 rgba(60,240,255,.8);transform:translateX(-4px)}
 12%{opacity:1;clip-path:inset(10% 0 70% 0);transform:translateX(3px)}24%{clip-path:inset(60% 0 8% 0);transform:translateX(-2px)}36%{opacity:.4;clip-path:inset(0 0 0 0);transform:none}
 48%{opacity:1;text-shadow:-1px 0 rgba(255,60,120,.6),1px 0 rgba(60,240,255,.6)}60%{opacity:.7}72%{opacity:1}100%{opacity:1;clip-path:none;text-shadow:none;transform:none}}
.vxMicro{position:fixed;bottom:10px;z-index:3;font:9.5px/1.45 VexMono,monospace;letter-spacing:.14em;color:rgba(150,245,255,.42);pointer-events:none;white-space:pre;text-shadow:0 0 6px rgba(var(--vxE),.4)}
#vxMicL{left:14px}#vxMicR{right:14px;text-align:right}
#vxTick2{position:fixed;left:0;right:0;bottom:0;height:13px;overflow:hidden;z-index:3;pointer-events:none;border-top:1px solid rgba(var(--vxE),.08);background:linear-gradient(90deg,transparent,rgba(var(--vxE),.03),transparent)}
#vxTick2 span{position:absolute;white-space:nowrap;font:8.5px/13px VexMono,monospace;letter-spacing:.32em;color:rgba(150,245,255,.32);animation:vxTk 70s linear infinite}
@keyframes vxTk{from{transform:translateX(100vw)}to{transform:translateX(-100%)}}
body.lowfx #vxHex,body.lowfx #vxTr,body.lowfx #vxTick2,body.lowfx .dash.hud .w::after{display:none!important}
body.lowfx .dash.hud .w{backdrop-filter:none!important;transform:none!important}
body:not(.aionly) .vxMicro{display:none}
body[data-mode=black] .vxMicro,body[data-mode=black] #vxTick2{opacity:.35}`;
document.head.appendChild(st);
const mk=(t,id,cls)=>{const e=document.createElement(t);e.id=id;if(cls)e.className=cls;document.body.appendChild(e);return e;};
const hex=mk("div","vxHex"),gl=document.getElementById("gl");gl&&gl.after(hex);
const NS="http://www.w3.org/2000/svg",tr=document.createElementNS(NS,"svg");tr.id="vxTr";hex.after(tr);
const mL=mk("div","vxMicL","vxMicro"),mR=mk("div","vxMicR","vxMicro"),tk=mk("div","vxTick2");tk.innerHTML="<span></span>";
// circuit traces: orb -> each visible panel, orthogonal with a 45deg elbow and a node at the panel edge
function traces(){const ai=document.body.classList.contains("aionly"),o=document.getElementById("orb");tr.innerHTML="";if(ai||!o||document.body.classList.contains("lowfx"))return;
 const r=o.getBoundingClientRect();if(!r.width)return;const cx=r.left+r.width/2,cy=r.top+r.height/2,R0=r.width*.42;let h="";
 document.querySelectorAll(".dash.hud .w:not(.hero)").forEach((w,i)=>{const b=w.getBoundingClientRect();if(!b.width||getComputedStyle(w).display=="none")return;
  const left=b.right<cx,ex=left?b.right:b.left,ey=Math.min(b.bottom-24,Math.max(b.top+24,cy+(b.top+b.height/2-cy)*.35)),sx=cx+(left?-R0:R0),sy=cy+(ey-cy)*.25;
  const mx=sx+(ex-sx)*.45,d=`M${sx},${sy} L${mx},${sy} L${mx+(left?-1:1)*Math.abs(ey-sy)*.0+(0)},${sy} L${mx+(left?-1:1)*Math.min(Math.abs(ex-mx)*.5,Math.abs(ey-sy))},${ey} L${ex},${ey}`;
  h+=`<path d="${d}"/><path class="f" d="${d}" style="animation-delay:${-i*.7}s"/><circle cx="${ex}" cy="${ey}" r="2.6"/><circle cx="${sx}" cy="${sy}" r="1.8"/>`;});
 tr.innerHTML=h;}
setInterval(traces,1200);addEventListener("resize",traces);setTimeout(traces,600);
// glitch on text appear/change
const G=el=>{el.classList.remove("vxG");void el.offsetWidth;el.classList.add("vxG");setTimeout(()=>el.classList.remove("vxG"),600);};
const watch=sel=>{const e=document.querySelector(sel);if(!e)return;let last=e.textContent;new MutationObserver(()=>{if(e.textContent!==last){last=e.textContent;G(e);}}).observe(e,{childList:true,characterData:true,subtree:true});};
["#greet","#stateText","#vxModeCard .mt","#wMode .mt"].forEach(s=>setTimeout(()=>watch(s),1500));
setTimeout(()=>{const g=document.getElementById("greet");g&&G(g);},900);
new MutationObserver(()=>{if(document.body.classList.contains("aionly"))return;document.querySelectorAll(".dash.hud .w h4").forEach((h,i)=>setTimeout(()=>{if(h.offsetParent)G(h);},120+i*70));})
 .observe(document.body,{attributes:true,attributeFilter:["class"]});
const dsh=document.querySelector(".dash.hud");dsh&&new MutationObserver(()=>document.querySelectorAll(".dash.hud .w h4").forEach((h,i)=>setTimeout(()=>{if(h.offsetParent)G(h);},80+i*60))).observe(dsh,{attributes:true,attributeFilter:["data-tab"]});
// micro-data readouts (real values where we have them: fps, frame time, resolution, uptime, mode)
let fr=0,fps=0,lt=performance.now();(function c(){fr++;const n=performance.now();if(n-lt>1000){fps=fr;fr=0;lt=n;}requestAnimationFrame(c);})();
const t0=Date.now(),hx=()=>(Math.random()*0xffffff|0).toString(16).toUpperCase().padStart(6,"0");
setInterval(()=>{const up=(Date.now()-t0)/1000|0,md=(document.body.dataset.mode||"blue").toUpperCase();
 mL.textContent=`RENDER  ${String(fps).padStart(3," ")} FPS  ${(1000/Math.max(1,fps)).toFixed(1)} MS\nGRID    ${innerWidth}x${innerHeight}  DPR ${devicePixelRatio||1}\nSESSION ${String(up/3600|0).padStart(2,"0")}:${String(up/60%60|0).padStart(2,"0")}:${String(up%60).padStart(2,"0")}\nFX      ${document.body.classList.contains("lowfx")?"LOW":"BLOOM · CA · GRAIN"}`;
 mR.textContent=`MODE ${md}\nMEM 0x${hx()}\nBUS 0x${hx()}  SYNC OK\nVEX CORE // ${window.__threeOK||"2D"}`;},500);
const tkS=tk.firstChild;const tkF=()=>{tkS.textContent=Array.from({length:14},(_,i)=>["NODE "+hx(),"LAT "+(8+Math.random()*20|0)+"MS","PKT "+(Math.random()*999|0),"CORE "+(90+Math.random()*10|0)+"%","SIG LOCK","CH "+(Math.random()*64|0),"ENC AES","HOLO SYNC"][i%8]).join("   ///   ");};tkF();tkS.addEventListener("animationiteration",tkF);
})();
