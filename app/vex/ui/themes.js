// Vex 3.9 per-mode aesthetics (original art, no sounds). Shared by the main window (blueprint view) and the companion HUD.
// Each mode changes background pattern, fonts, panel shape, decorations and a mode feature card, not just the colour.
(function(){
const E=s=>String(s==null?"":s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const css=`
#thX,#thF{display:none}
body.th #thX{display:block;position:fixed;inset:0;pointer-events:none;z-index:3;overflow:hidden}
body.th #thF{display:block;position:fixed;z-index:6;pointer-events:none;padding:12px 16px;border:1px solid var(--tc);background:var(--tp);color:var(--tt);font-family:var(--tf)}
body.th.main #thF{right:28px;bottom:42px;width:min(340px,19vw)}
body.comp #thF{display:none!important}body.comp.th-pink .sun{display:none} /* 4.1: mode details only on the main screen */
#thF .k{font-size:10px;letter-spacing:.35em;opacity:.8}#thF .n{font-size:40px;line-height:1.1;color:#fff}#thF .s{font-size:11px;letter-spacing:.12em;opacity:.85;margin-top:4px}
body.comp #thF .k{font-size:.62vw}body.comp #thF .n{font-size:3.6vw}body.comp #thF .s{font-size:.75vw}
.thG{position:absolute;inset:0}
/* ---------- RED combat: tactical targeting, hazard stripes, angular */
body.th-red{--tc:#ff3046;--tp:rgba(30,2,6,.86);--tt:#ffc9cf;--tf:Bahnschrift,"Arial Narrow",sans-serif}
body.th-red .thgrid{background:linear-gradient(rgba(255,40,60,.07) 1px,transparent 1px) 0 0/40px 40px,linear-gradient(90deg,rgba(255,40,60,.07) 1px,transparent 1px) 0 0/40px 40px,radial-gradient(ellipse at 50% 45%,#2a0309,#0b0103 70%)!important}
body.th-red .hz{position:absolute;left:0;right:0;height:14px;background:repeating-linear-gradient(-45deg,#ff3046 0 14px,transparent 14px 28px);opacity:.55}
body.th-red .bpP,body.th-red .p{font-family:Bahnschrift,"Arial Narrow",sans-serif!important;clip-path:polygon(0 0,calc(100% - 16px) 0,100% 16px,100% 100%,16px 100%,0 calc(100% - 16px));letter-spacing:.06em}
body.th-red .xh{position:absolute;left:50%;top:44%;width:44vh;height:44vh;transform:translate(-50%,-50%)}
/* ---------- GREEN study: calm, organic, rounded, focus timer first */
body.th-green{--tc:rgba(120,230,160,.6);--tp:rgba(4,26,16,.8);--tt:#d4f5df;--tf:"Segoe UI Light","Segoe UI",sans-serif}
body.th-green .thgrid{background:radial-gradient(ellipse at 30% 30%,#0b3a24,transparent 60%),radial-gradient(ellipse at 75% 70%,#08301f,transparent 60%),#03140d!important}
body.th-green .bpP,body.th-green .p,body.th-green #bpCard{border-radius:16px!important;font-family:"Segoe UI Light","Segoe UI",sans-serif!important;letter-spacing:.03em!important}
body.th-green #thF{border-radius:22px;text-align:center}
body.th-green.main #thF{left:50%;right:auto;top:64px;bottom:auto;transform:translateX(-50%);width:min(380px,24vw)}
body.th-green #thF .n{font-size:64px;font-weight:200}body.th-green.comp #thF .n{font-size:9vw}
body.th-green .wv path{fill:none;stroke:rgba(120,230,160,.18);stroke-width:1.5}
body.th-green .wv{animation:thDrift 30s ease-in-out infinite alternate}
@keyframes thDrift{to{transform:translateX(-4%)}}
/* ---------- PURPLE creator: studio / broadcast, safe frames, waveform */
body.th-purple{--tc:#b46cff;--tp:rgba(18,6,34,.85);--tt:#ead9ff;--tf:"Segoe UI Semibold","Segoe UI",sans-serif}
body.th-purple .thgrid{background:radial-gradient(ellipse at 50% 40%,#2a0d4d,#0b0316 70%)!important}
body.th-purple .rf{position:absolute;inset:4.5%;border:1px dashed rgba(200,150,255,.25)}
body.th-purple .rf i{position:absolute;width:44px;height:44px;border:3px solid #c88cff}
body.th-purple .rf i:nth-child(1){left:-2px;top:-2px;border-right:0;border-bottom:0}body.th-purple .rf i:nth-child(2){right:-2px;top:-2px;border-left:0;border-bottom:0}
body.th-purple .rf i:nth-child(3){left:-2px;bottom:-2px;border-right:0;border-top:0}body.th-purple .rf i:nth-child(4){right:-2px;bottom:-2px;border-left:0;border-top:0}
body.th-purple .tc{position:absolute;right:6%;top:6%;font:14px VexMono,monospace;color:#d9b8ff;letter-spacing:.2em}
.wf{display:flex;align-items:center;gap:3px;height:46px;margin-top:6px}.wf u{flex:1;background:var(--tc);animation:thWf 1.4s ease-in-out infinite alternate}
@keyframes thWf{from{transform:scaleY(.15)}to{transform:scaleY(1)}}
/* ---------- GOLD business: luxury finance terminal, ticker tape */
body.th-gold{--tc:#e8b84a;--tp:rgba(18,13,3,.88);--tt:#f6e3b4;--tf:Georgia,"Times New Roman",serif}
body.th-gold .thgrid{background:repeating-linear-gradient(135deg,rgba(232,184,74,.04) 0 1px,transparent 1px 22px),radial-gradient(ellipse at 50% 40%,#1c1505,#070502 70%)!important}
body.th-gold .bpP h6,body.th-gold .h,body.th-gold #big,body.th-gold #bpCard .big,body.th-gold #clk,body.th-gold #bpR .clk{font-family:Georgia,serif!important}
body.th-gold .tk{position:absolute;left:0;right:0;top:46px;height:24px;border-top:1px solid rgba(232,184,74,.4);border-bottom:1px solid rgba(232,184,74,.4);background:rgba(10,7,1,.8);overflow:hidden;white-space:nowrap;font:12px VexMono,monospace;line-height:24px;color:#f1d48a}
body.comp.th-gold .tk{top:3.4vw}
body.th-gold .tk div{display:inline-block;padding-left:100%;animation:thTk 40s linear infinite}@keyframes thTk{to{transform:translateX(-100%)}}
body.th-gold .tk b{color:#7be38f;font-weight:400}
/* ---------- PINK chill: dreamy synthwave, sun, slow particles, music card */
body.th-pink{--tc:#ff5fc8;--tp:rgba(30,6,34,.78);--tt:#ffd9f2;--tf:"Segoe UI","Trebuchet MS",sans-serif}
body.th-pink .thgrid{background:linear-gradient(180deg,#12052e 0,#3a0b4a 48%,#16031e 62%,#07010c 100%)!important}
body.th-pink .sun{position:absolute;left:50%;top:30%;width:34vh;height:34vh;transform:translateX(-50%);border-radius:50%;background:linear-gradient(#ffd36e,#ff4fa8);opacity:.35;
 -webkit-mask:repeating-linear-gradient(180deg,#000 0 14px,transparent 14px 20px)}
body.th-pink .fl{position:absolute;left:-50%;right:-50%;bottom:0;height:38%;background:linear-gradient(rgba(255,95,200,.35) 2px,transparent 2px) 0 0/100% 34px,linear-gradient(90deg,rgba(255,95,200,.35) 2px,transparent 2px) 0 0/60px 100%;transform:perspective(300px) rotateX(62deg);transform-origin:50% 100%;opacity:.5}
body.th-pink .pt{position:absolute;width:3px;height:3px;border-radius:50%;background:#ffc2ea;opacity:.6;animation:thUp linear infinite}
@keyframes thUp{from{transform:translateY(0)}to{transform:translateY(-110vh)}}
body.th-pink .bpP,body.th-pink .p{border-radius:10px!important;box-shadow:0 0 18px rgba(255,95,200,.25)}
/* ---------- WHITE diagnostics: clean lab scan, scanlines, ECG */
body.th-white{--tc:#e9f3ff;--tp:rgba(14,18,22,.9);--tt:#e9f3ff;--tf:"Segoe UI",Arial,sans-serif}
body.th-white .thgrid{background:repeating-linear-gradient(0deg,rgba(255,255,255,.035) 0 1px,transparent 1px 4px),linear-gradient(rgba(233,243,255,.07) 1px,transparent 1px) 0 0/60px 60px,linear-gradient(90deg,rgba(233,243,255,.07) 1px,transparent 1px) 0 0/60px 60px,#0c1014!important}
body.th-white .sc{position:absolute;left:0;right:0;height:120px;background:linear-gradient(transparent,rgba(233,243,255,.12),transparent);animation:thSc 6s linear infinite}
@keyframes thSc{from{top:-120px}to{top:100%}}
body.th-white .ecg path{fill:none;stroke:#e9f3ff;stroke-width:1.5;stroke-dasharray:1200;animation:thEcg 3s linear infinite}@keyframes thEcg{from{stroke-dashoffset:1200}to{stroke-dashoffset:0}}
/* ---------- BLACK stealth: near-dark, dim red text, privacy blur */
body.th-black{--tc:rgba(170,40,40,.5);--tp:rgba(4,2,2,.9);--tt:#8a2a2a;--tf:VexMono,monospace}
body.th-black .thgrid{background:#020203!important}
body.th-black .bpP,body.th-black .p,body.th-black #bpCard{color:#7a2424!important;border-color:rgba(120,30,30,.35)!important;background:rgba(3,1,1,.85)!important;text-shadow:none!important;box-shadow:none!important}
body.th-black .bpP *,body.th-black .p *{color:#8a2a2a!important;border-color:rgba(120,30,30,.3)!important}
body.th-black #bpRList,body.th-black #bpL .cols~*,body.th-black #wx,body.th-black #todo,body.th-black #rem,body.th-black #feed{filter:blur(6px)}
body.th-black #bpRing,body.th-black #g,body.th-black .fr{opacity:.25}
body.th-black #bpCard .big,body.th-black #big{color:#9a2b2b!important;text-shadow:none!important}
/* recolour blue-tinted blueprint pieces in the main window per mode */
body.th-red #bpRing,body.th-red .bpP{filter:hue-rotate(145deg) saturate(1.6)}
body.th-green #bpRing,body.th-green .bpP{filter:hue-rotate(-75deg) saturate(.8)}
body.th-purple #bpRing,body.th-purple .bpP{filter:hue-rotate(55deg)}
body.th-gold #bpRing,body.th-gold .bpP{filter:hue-rotate(185deg) saturate(1.2)}
body.th-pink #bpRing,body.th-pink .bpP{filter:hue-rotate(110deg) saturate(1.5)}
body.th-white #bpRing,body.th-white .bpP{filter:grayscale(1) brightness(1.25)}
body.th-red #thF,body.th-green #thF,body.th-purple #thF,body.th-gold #thF,body.th-pink #thF,body.th-white #thF{filter:none}
body.main.th #bpGrid{mix-blend-mode:screen;opacity:.8}
body.main.th #thX{mix-blend-mode:screen}
body.comp #thX{z-index:0}body.comp .p,body.comp #top,body.comp #msg,body.comp #thF{z-index:2}
body.lowfx #thX *,body.low #thX *{animation:none!important}
`;
const st=document.createElement("style");st.textContent=css;document.head.appendChild(st);
const X=document.createElement("div");X.id="thX";const F=document.createElement("div");F.id="thF";
document.body.appendChild(X);document.body.appendChild(F);
const DECOR={
 red:()=>`<div class="hz" style="top:0"></div><div class="hz" style="bottom:0"></div>
  <svg class="xh" viewBox="0 0 200 200"><g fill="none" stroke="#ff3046" stroke-opacity=".55"><path d="M100 0V70M100 130V200M0 100H70M130 100H200"/><path d="M40 40l14 0M40 40l0 14M160 40l-14 0M160 40l0 14M40 160l14 0M40 160l0-14M160 160l-14 0M160 160l0-14" stroke-width="2"/><circle cx="100" cy="100" r="4"/></g>
  <text x="104" y="66" fill="#ff6b7a" font-size="6" font-family="monospace" letter-spacing="1">TGT LOCK</text></svg>`,
 green:()=>`<svg class="thG wv" viewBox="0 0 1200 700" preserveAspectRatio="none">${[0,1,2,3,4,5,6].map(i=>`<path d="M-50 ${150+i*80} C 200 ${90+i*80}, 400 ${230+i*80}, 650 ${150+i*80} S 1050 ${80+i*80}, 1300 ${160+i*80}"/>`).join("")}
  <g stroke="rgba(120,230,160,.16)" fill="none"><path d="M90 640V560l40-40V470M130 520h50l30-30M1110 90v70l-40 40v60M1070 200h-60"/><circle cx="210" cy="490" r="6"/><circle cx="1010" cy="200" r="6"/></g></svg>`,
 purple:()=>`<div class="rf"><i></i><i></i><i></i><i></i></div><div class="tc" id="thTc">STUDIO · 00:00:00</div>`,
 gold:()=>`<div class="tk"><div id="thTk"></div></div>`,
 pink:()=>`<div class="sun"></div><div class="fl"></div>`+Array.from({length:26},(_,i)=>`<i class="pt" style="left:${(i*37)%100}%;bottom:-10px;animation-duration:${28+(i*7)%22}s;animation-delay:-${(i*5)%30}s"></i>`).join(""),
 white:()=>`<div class="sc"></div>`,
 black:()=>``};
const fmt=n=>n>=1e6?(n/1e6).toFixed(2)+"M":n>=1e3?(n/1e3).toFixed(2)+"K":String(n);
function feat(m,D){const s=D.st||{},p=D.panel||{},G=D.growth||p.growth||{},ch=String(D.chan||"");const subs=(ch.match(/([\d.,]+\s*[KM]?)\s*subs/i)||[])[1]||(G.subs!=null?fmt(G.subs):"--"),vids=(ch.match(/(\d[\d,]*)\s*videos?/i)||[])[1]||"--";
 if(m=="red")return `<div class="k">COMBAT TELEMETRY // GPU RESERVED</div><div class="n">${s.gpu??"--"}<small style="font-size:.4em"> % GPU</small></div><div class="s">TEMP ${s.gpu_temp??"--"}°C · VRAM ${s.vram??"--"}% · CPU ${s.cpu??"--"}% · RAM ${s.ram??"--"}%</div><div class="s">EFFECTS LOW · ALERTS MUTED · COMPANION HUD HIDDEN</div>`;
 if(m=="green"){const f=p.focus||{},l=+f.left||0;return `<div class="k">FOCUS SESSION</div><div class="n">${String(l/60|0).padStart(2,"0")}:${String(l%60).padStart(2,"0")}</div><div class="s">${l?`${f.mins} MIN FOCUS · STAY WITH IT`:`Say "focus 25 minutes" to begin`}</div>`;}
 if(m=="purple"){const td=(D.todos||[]);return `<div class="k">CREATOR STUDIO</div><div class="n">${E(new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",hour12:false}))}</div><div class="s">${td.length?"NEXT: "+E(td[0]).toUpperCase():"NO OPEN TASKS"}</div><div class="s">OBS · CAPCUT · YOUTUBE STUDIO ON REQUEST</div>`;}
 if(m=="gold"){const gl=(p.goals||[]).slice(0,3);return `<div class="k">LEDGER // GOALS</div><div class="n">${gl.length}<small style="font-size:.35em;color:#7be38f"> GOALS TRACKED</small></div><div class="s">CPU ${s.cpu??"--"}% · RAM ${s.ram??"--"}% · DISK FREE ${s.disk_free??"--"} GB</div>${gl.map(g=>`<div class="s">◆ ${E(g.text||g)}</div>`).join("")||`<div class="s">Say "add goal" to track one</div>`}`;}
 if(m=="pink"){const np=p.playing||{};return `<div class="k">NOW PLAYING</div><div class="n" style="font-size:24px">${E(np.title||"Nothing playing")}</div><div class="s">${E(np.artist||"")} ${np.app?"· "+E(np.app):""}</div><div class="wf" style="height:22px">${Array.from({length:24},(_,i)=>`<u style="animation-duration:${2.4+(i%4)*.6}s;animation-delay:-${i*.2}s"></u>`).join("")}</div>`;}
 if(m=="white"){const hl=Math.max(0,Math.min(100,Math.round(100-0.22*(+s.cpu||0)-0.22*(+s.ram||0)-0.12*(+s.gpu||0))));return `<div class="k">DIAGNOSTIC SCAN</div><div class="n">${hl}%<small style="font-size:.35em"> SYSTEM HEALTH</small></div><svg class="ecg" viewBox="0 0 300 40" style="width:100%;height:40px"><path d="M0 20H80l8-14 8 28 8-22 6 8H190l8-14 8 28 8-22 6 8H300"/></svg><div class="s">CPU ${s.cpu??"--"}% · RAM ${s.ram??"--"}% · DISK ${s.disk_pct??"--"}% · GPU ${s.gpu_temp??"--"}°C</div>`;}
 if(m=="black")return `<div class="k">STEALTH</div><div class="n" style="font-size:28px">PRIVACY ON</div><div class="s">PERSONAL INFO HIDDEN · VOICE LOW · ALERTS MUTED</div>`;
 return "";}
let cur="";
window.vexTheme=function(D){const m=(D&&D.mode)||"blue",b=document.body;window.__mode=m;
 if(m!==cur){[...b.classList].filter(c=>c.startsWith("th")).forEach(c=>b.classList.remove(c));if(m!="blue"){b.classList.add("th","th-"+m);}X.innerHTML=(DECOR[m]||(()=>""))();cur=m;}
 if(m=="blue")return;if(!b.classList.contains("comp"))F.innerHTML=feat(m,D||{});
 if(m=="gold"){const s=(D.st||{}),G=D.growth||(D.panel||{}).growth||{},t=document.getElementById("thTk");if(t)t.innerHTML=[`CPU ${s.cpu??"--"}%`,`RAM ${s.ram??"--"}%`,`GPU ${s.gpu??"--"}%`,`DISK FREE ${s.disk_free??"--"} GB`,`NET ↓ ${s.net_down??"--"}`,`VEX CORE <b>ONLINE</b>`].join("   ◆   ").repeat(2);}
 if(m=="purple"){const t=document.getElementById("thTc");if(t){const d=new Date();t.textContent=(b.classList.contains("comp")?"":"STUDIO · ")+d.toTimeString().slice(0,8);}}};
})();
