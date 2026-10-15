// Vex 4.0 product layer (original art, no sounds): cinematic boot, briefing cards, live captions + mic waveform,
// 'show me' glass panel, task step log, PTT chip, theme gallery, idle live wallpaper, smart-home tiles,
// first-run wizard, Settings/About with changelog, showcase hooks. Uses tokens.css.
(function(){
const A=()=>window.pywebview&&window.pywebview.api,E=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const css=`
#v4boot{position:fixed;inset:0;z-index:90;background:#000;display:none;align-items:center;justify-content:center;flex-direction:column;cursor:pointer}
#v4boot.on{display:flex}#v4boot.out{opacity:0;transition:opacity .9s ease}
#v4boot svg.rings{width:min(46vh,520px);height:min(46vh,520px)}
#v4boot .rg{fill:none;stroke:var(--vx-a);transform-origin:50% 50%;stroke-dasharray:var(--L);stroke-dashoffset:var(--L);animation:v4draw 1.4s var(--vx-ease) forwards,v4spin 9s linear infinite}
@keyframes v4draw{to{stroke-dashoffset:0}}@keyframes v4spin{to{transform:rotate(360deg)}}
#v4boot .core{fill:url(#v4cg);opacity:0;animation:v4pop .8s 1.2s forwards}@keyframes v4pop{to{opacity:1}}
#v4boot .wm{height:42px;margin-top:22px;opacity:0;animation:v4pop .6s 1.6s forwards}
#v4boot .chk{margin-top:18px;width:min(520px,80vw);font:12px/1.9 var(--vx-f-mono);letter-spacing:.18em;color:var(--vx-dim)}
#v4boot .chk div{display:flex;justify-content:space-between;opacity:0;transform:translateX(-8px);transition:all .25s}#v4boot .chk div.on{opacity:1;transform:none}
#v4boot .chk b{color:var(--vx-a);font-weight:400}#v4boot .chk b.ok:after{content:"  ✓";color:#7dffb0}
#v4boot .wel{margin-top:16px;font:300 34px var(--vx-f-ui);color:#fff;letter-spacing:.04em;opacity:0;transition:opacity .6s;text-align:center}
#v4boot .wel small{display:block;font:13px var(--vx-f-mono);letter-spacing:.3em;color:var(--vx-a);margin-top:6px}
#v4boot .skip{position:absolute;right:28px;bottom:24px;font:10px var(--vx-f-mono);letter-spacing:.3em;color:var(--vx-dim)}
#v4boot .tag{position:absolute;left:28px;bottom:24px;font:10px var(--vx-f-mono);letter-spacing:.3em;color:var(--vx-dim)}
#v4brief{position:fixed;left:50%;bottom:96px;transform:translate(-50%,30px);z-index:60;display:flex;gap:14px;opacity:0;pointer-events:none;transition:all .6s var(--vx-ease)}
body.v4brf #bpCard{opacity:0!important;transition:opacity .4s}
#v4brief.on{opacity:1;transform:translate(-50%,0);pointer-events:auto}
#v4brief .hd{position:absolute;left:0;top:-34px;font:12px var(--vx-f-mono);letter-spacing:.3em;color:var(--vx-a)}
#v4brief .c{width:200px;padding:14px 16px;opacity:0;transform:translateY(16px);transition:all .5s var(--vx-ease)}#v4brief .c.on{opacity:1;transform:none}
#v4brief .vx-big{font-size:34px;margin:6px 0 2px}#v4brief .vx-row{font-size:11px;line-height:1.7}#v4brief .vx-row b{max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#v4cap{position:fixed;left:50%;bottom:150px;transform:translateX(-50%);z-index:55;width:min(900px,60vw);text-align:center;pointer-events:none}
#v4cap .l{font:400 14px var(--vx-f-ui);color:rgba(233,251,255,.72);text-shadow:0 1px 6px #000;margin:4px 0;opacity:0;transition:opacity .4s}#v4cap .l.on{opacity:1}
#v4cap .l i{font:10px var(--vx-f-mono);letter-spacing:.3em;color:var(--vx-a);font-style:normal;margin-right:10px}
#v4media{position:fixed;right:28px;top:50%;transform:translate(30px,-50%);z-index:62;width:min(560px,32vw);padding:14px;opacity:0;pointer-events:none;transition:all .5s var(--vx-ease)}
#v4media.on{opacity:1;transform:translate(0,-50%);pointer-events:auto}
#v4media .x{position:absolute;right:10px;top:8px;cursor:pointer;color:var(--vx-dim);font:14px var(--vx-f-mono)}
#v4media iframe,#v4media img{width:100%;aspect-ratio:16/9;border:0;display:block;margin-top:10px;object-fit:contain;background:#000}
#v4media p{font:13px/1.6 var(--vx-f-ui);color:var(--vx-ink);margin-top:10px;max-height:30vh;overflow:auto}
#v4steps{position:fixed;right:28px;top:200px;z-index:58;width:min(340px,19vw);padding:10px 12px;opacity:0;transition:opacity .4s;pointer-events:none}
#v4steps.on{opacity:1}#v4steps .s{font:11px/1.7 var(--vx-f-mono);color:var(--vx-dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v4steps .s i{font-style:normal;margin-right:8px}#v4steps .s.run i{color:var(--vx-a)}#v4steps .s.ok i{color:#7dffb0}#v4steps .s.err i{color:#ff6b7a}
#v4ptt{position:fixed;left:50%;bottom:44px;transform:translateX(-50%);z-index:57;font:10px var(--vx-f-mono);letter-spacing:.28em;color:var(--vx-dim);pointer-events:auto;cursor:pointer}
#v4ptt b{color:var(--vx-a);font-weight:400;border:1px solid var(--vx-line);padding:1px 6px;margin:0 4px}
body.aionly #v4ptt{bottom:20px}body:not(.aionly) #v4ptt{display:none}
#v4page{position:fixed;inset:0;z-index:80;display:none;background:rgba(1,6,14,.86);backdrop-filter:blur(8px);overflow:auto}
#v4page.on{display:block}#v4page .in{max-width:1180px;margin:56px auto;padding:28px 34px}
#v4page .top{display:flex;align-items:center;gap:16px;margin-bottom:22px}#v4page .top img{height:30px}#v4page .top .x{margin-left:auto}
#v4page h2{font:300 26px var(--vx-f-ui);color:#fff;letter-spacing:.04em}
.v4tg{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.v4th{padding:0;cursor:pointer;overflow:hidden;transition:transform var(--vx-t-fast)}.v4th:hover{transform:translateY(-3px)}
.v4th .pv{height:150px;position:relative;overflow:hidden}.v4th .meta{padding:10px 12px}.v4th .meta>*{display:block;margin-top:2px}
.v4th .meta b{display:block;font:400 16px var(--vx-f-ui);color:#fff}.v4th.cur{outline:2px solid var(--vx-a)}
.v4th .pv .o{position:absolute;left:50%;top:46%;width:64px;height:64px;transform:translate(-50%,-50%);border-radius:50%}
.v4th .pv .r{position:absolute;left:50%;top:46%;width:104px;height:104px;transform:translate(-50%,-50%);border-radius:50%;border:1px solid}
.v4th .pv .cd{position:absolute;left:10px;bottom:10px;width:70px;height:22px;border:1px solid}
.v4th .pv .cd2{position:absolute;right:10px;top:10px;width:46px;height:14px;border:1px solid}
.v4tabs{display:flex;gap:8px;margin-bottom:18px}
.v4cl{border-left:2px solid var(--vx-a);padding:4px 0 4px 14px;margin:10px 0}.v4cl b{font:400 14px var(--vx-f-mono);color:var(--vx-a)}.v4cl p{font:13px/1.6 var(--vx-f-ui);color:var(--vx-ink);margin-top:2px}
.v4grid2{display:grid;grid-template-columns:1.2fr 1fr;gap:18px}.v4card{padding:18px}
.v4sh{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.v4sh .t{padding:16px}.v4sh .t .st{font:10px var(--vx-f-mono);letter-spacing:.24em;color:#ff9aa6;margin-top:8px}.v4sh .t .st.c{color:#7dffb0}
.v4wz{max-width:760px!important}.v4dots{display:flex;gap:10px;justify-content:center;margin:6px 0 22px}.v4dots i{width:34px;height:3px;background:var(--vx-line)}.v4dots i.on{background:var(--vx-a)}
.v4wz .st{min-height:300px}.v4wz label{display:block;margin:16px 0 6px}.v4wz .nav{display:flex;justify-content:space-between;margin-top:24px}
.v4meter{height:10px;border:1px solid var(--vx-line);margin-top:10px}.v4meter i{display:block;height:100%;width:0;background:var(--vx-a);transition:width .1s}
body.v4idle .bpP,body.v4idle #bpCard,body.v4idle .inputbar,body.v4idle #v4ptt,body.v4idle #v4cap,body.v4idle #v4steps,body.v4idle .dash .w{opacity:0!important;transition:opacity 2s}
body.v4idle #v4wall{opacity:1}
#v4wall{position:fixed;inset:0;z-index:4;pointer-events:none;opacity:0;transition:opacity 2s;display:flex;align-items:flex-end;justify-content:flex-end;padding:0 48px 40px}
#v4wall div{font:200 96px var(--vx-f-ui);color:rgba(255,255,255,.22);letter-spacing:.06em;text-align:right}#v4wall small{display:block;font:12px var(--vx-f-mono);letter-spacing:.5em;color:var(--vx-a);opacity:.6}
#v4scan{position:fixed;left:0;right:0;height:3px;z-index:59;background:var(--vx-a);box-shadow:0 0 18px var(--vx-a);top:-10px;pointer-events:none}
#v4scan.on{animation:v4sc 2.4s ease-in-out 2}@keyframes v4sc{0%{top:0}50%{top:100%}100%{top:0}}
@media (min-width:2200px){#v4page .in{zoom:1.45}#v4brief{zoom:1.3}#v4media{zoom:1.25}#v4steps{zoom:1.2}#v4cap{zoom:1.2}#v4boot .chk,#v4boot .wel,#v4boot .wm{zoom:1.3}}
#v4show{position:fixed;left:28px;top:14px;z-index:70;display:none}#v4show.on{display:block}
`;
const st=document.createElement("style");st.textContent=css;document.head.appendChild(st);
const mk=(id,cls,html,tag)=>{const e=document.createElement(tag||"div");e.id=id;if(cls)e.className=cls;if(html)e.innerHTML=html;document.body.appendChild(e);return e;};
const WM='<img src="brand/wordmark.svg" alt="VEX">',GL='<img src="brand/glyph.svg" alt="">';

// ---------- 1. cinematic boot
const boot=mk("v4boot","");
let bootT=[];
function bootClose(){bootT.forEach(clearTimeout);bootT=[];if(!boot.classList.contains("on"))return;boot.classList.add("out");setTimeout(()=>boot.classList.remove("on","out"),900);}
function playBoot(b){b=b||{};bootT.forEach(clearTimeout);bootT=[];
 const R=[[230,1.2,"8 10"],[200,2,""],[168,1,"2 6"],[136,3,"40 14"],[104,1.2,""]];
 boot.innerHTML=`<svg class="rings" viewBox="0 0 500 500"><defs><radialGradient id="v4cg"><stop offset="0" stop-color="#fff"/><stop offset=".4" stop-color="var(--vx-a)"/><stop offset="1" stop-color="var(--vx-a)" stop-opacity="0"/></radialGradient></defs>
 ${R.map((r,i)=>{const L=Math.round(2*Math.PI*r[0]);return `<circle class="rg" cx="250" cy="250" r="${r[0]}" stroke-width="${r[1]}" style="--L:${L};animation-delay:${i*.18}s,${i*.18}s;animation-duration:1.4s,${9+i*3}s;${i%2?"animation-direction:normal,reverse;":""}" ${r[2]?`stroke-dasharray="${r[2]}"`:""} opacity="${.9-i*.1}"/>`}).join("")}
 ${Array.from({length:60},(_,i)=>{const a=i*6*Math.PI/180,r1=242,r2=i%5?248:256;return `<line x1="${250+Math.cos(a)*r1}" y1="${250+Math.sin(a)*r1}" x2="${250+Math.cos(a)*r2}" y2="${250+Math.sin(a)*r2}" stroke="var(--vx-a)" opacity="0" style="animation:v4pop .2s ${(0.9+i*0.012).toFixed(2)}s forwards"/>`}).join("")}
 <circle class="core" cx="250" cy="250" r="70"/></svg>
 <div class="wm"><img src="brand/wordmark.svg" style="height:42px"></div>
 <div class="chk">${(b.checks||[]).map(c=>`<div><span>${E(c.k)}</span><b class="${c.ok?"ok":""}">${E(c.v)}</b></div>`).join("")}</div>
 <div class="wel">Welcome back, sir.<small>${E(b.time||"")}${b.wx?" · "+E(b.wx).toUpperCase():""}</small></div>
 <div class="tag">VEX ${E(b.version||"")} · ${E(b.tagline||"")}</div><div class="skip">CLICK OR PRESS ANY KEY TO SKIP</div>`;
 boot.classList.remove("out");boot.classList.add("on");
 boot.querySelectorAll(".chk div").forEach((d,i)=>bootT.push(setTimeout(()=>d.classList.add("on"),1700+i*230)));
 const tw=1700+(b.checks||[]).length*230+250;bootT.push(setTimeout(()=>boot.querySelector(".wel").style.opacity=1,tw));
 if(!window.__v4hold)bootT.push(setTimeout(bootClose,tw+2600));}
boot.addEventListener("click",bootClose);addEventListener("keydown",e=>{if(boot.classList.contains("on"))bootClose();});
window.vexBoot=async()=>{let b={};try{b=await A().v40_boot();}catch(e){}if(b.skip)return;playBoot(b);};

// ---------- 2. briefing cards
const brief=mk("v4brief","");let briefT=0;
function showBrief(d){if(!d||!d.cards)return;clearTimeout(briefT);
 brief.innerHTML=`<div class="hd">BRIEFING · ${E(d.greeting||"").toUpperCase()} · ${E(d.time||"")}</div>`+d.cards.map(c=>`<div class="c vx-glass vx-br"><div class="vx-k">${E(c.title)}</div><div class="vx-big">${E(c.big)}</div><div class="vx-sub">${E(c.sub)}</div><div style="margin-top:8px">${(c.rows||[]).map(r=>`<div class="vx-row"><span>${E(r[0])}</span><b>${E(r[1])}</b></div>`).join("")}</div></div>`).join("");
 brief.classList.add("on");document.body.classList.add("v4brf");brief.querySelectorAll(".c").forEach((c,i)=>setTimeout(()=>c.classList.add("on"),150+i*140));
 briefT=setTimeout(()=>{brief.classList.remove("on");document.body.classList.remove("v4brf");},16000);}
brief.addEventListener("click",()=>{brief.classList.remove("on");document.body.classList.remove("v4brf");});
window.vexBrief=async(spoken)=>{try{if(spoken){await A().v40_brief(true);}else showBrief(await A().v40_brief(false));}catch(e){}};

// ---------- 3. live captions + mic waveform
const cap=mk("v4cap","",'<div class="l" id="v4cV"></div>');let capT={};
function caption(who,text){if(who!="vex")return;const el=document.getElementById("v4cV");if(!el)return;
 el.innerHTML=`<i>${who=="you"?"YOU":"VEX"}</i>${E(String(text).slice(0,220))}`;el.classList.add("on");clearTimeout(capT[who]);capT[who]=setTimeout(()=>el.classList.remove("on"),who=="you"?5000:Math.min(12000,2500+String(text).length*55));}
// 4.0: no mic waveform and no captions of your speech; only subtle captions of Vex replies.

// ---------- 5. 'show me' glass panel
const media=mk("v4media","vx-glass vx-br");
function showMedia(m){if(!m||m.kind=="close"){media.classList.remove("on");media.innerHTML="";return;}
 let h=`<div class="x" title="Close">✕</div><div class="vx-k">VEX // ${E(m.kind=="youtube"?"VIDEO":m.kind=="image"?"IMAGE":"PANEL")}</div><div style="font:400 18px var(--vx-f-ui);color:#fff;margin-top:4px">${E(m.title||"")}</div>`;
 if(m.kind=="youtube")h+=`<iframe src="https://www.youtube-nocookie.com/embed/${E(m.id)}?rel=0" allow="encrypted-media; picture-in-picture" allowfullscreen></iframe>`;
 if((m.kind=="image"||m.kind=="topic")&&m.src)h+=`<img src="${E(m.src)}" alt="">`;
 if(m.text)h+=`<p>${E(m.text)}</p>`;if(m.kind=="link")h+=`<p>${E(m.url)}</p>`;
 if(m.url&&m.kind=="topic")h+=`<div class="vx-sub" style="margin-top:6px">SOURCE · WIKIPEDIA</div>`;
 media.innerHTML=h;media.classList.add("on");media.querySelector(".x").onclick=()=>showMedia({kind:"close"});}
window.vexShowMe=async q=>{try{showMedia(await A().v40_show(q));}catch(e){}};

// ---------- 6. task step log
const steps=mk("v4steps","vx-glass");let stepT=0,STEPS=[];
function drawSteps(){steps.innerHTML=`<div class="vx-k" style="margin-bottom:6px">TASK LOG</div>`+STEPS.slice(0,7).map(s=>`<div class="s ${E(s.state)}"><i>${s.state=="ok"?"✓":s.state=="err"?"✕":"▸"}</i>${E(s.t)} ${E(s.text)}</div>`).join("");}
function addStep(s){STEPS.unshift(s);STEPS=STEPS.slice(0,30);drawSteps();steps.classList.add("on");clearTimeout(stepT);stepT=setTimeout(()=>steps.classList.remove("on"),12000);}

// ---------- 7. push-to-talk chip
const ptt=mk("v4ptt","",'HOLD <b>CTRL</b>+<b>ALT</b>+<b>V</b> TO TALK · SAY "MINI ORB" FOR THE FLOATING ORB');ptt.onclick=()=>{try{A().v40_ptt()}catch(e){}};

// ---------- 9. idle live wallpaper
const wall=mk("v4wall","",'<div><span id="v4wc">--:--</span><small>VEX · IDLE</small></div>');
function wake(){if(document.body.classList.contains("v4idle"))document.body.classList.remove("v4idle");}
["mousemove","keydown","mousedown"].forEach(e=>addEventListener(e,wake,{passive:true}));
setInterval(async()=>{try{const r=await A().v40_idle();if(r&&r.on&&r.idle>r.after)document.body.classList.add("v4idle");else wake();}catch(e){}},30000);
setInterval(()=>{const c=document.getElementById("v4wc");if(c)c.textContent=new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",hour12:false});},5000);

// ---------- scan sweep (showcase / diagnostics)
const scan=mk("v4scan","");function scanFx(){scan.classList.remove("on");void scan.offsetWidth;scan.classList.add("on");}

// ---------- pages: theme gallery, About/Settings, setup wizard
const page=mk("v4page","");
const PV={blue:["#04163a","linear-gradient(rgba(120,190,255,.12) 1px,transparent 1px) 0 0/12px 12px,linear-gradient(90deg,rgba(120,190,255,.12) 1px,transparent 1px) 0 0/12px 12px,#04163a"],
 red:["#14020a","repeating-linear-gradient(-45deg,rgba(255,48,70,.5) 0 6px,transparent 6px 12px) top/100% 8px no-repeat,linear-gradient(rgba(255,40,60,.1) 1px,transparent 1px) 0 0/16px 16px,#14020a"],
 green:["#03140d","radial-gradient(ellipse at 30% 30%,#0b3a24,transparent 60%),#03140d"],purple:["#0d0418","radial-gradient(ellipse at 50% 40%,#2a0d4d,#0b0316 70%)"],
 gold:["#0a0803","repeating-linear-gradient(135deg,rgba(232,184,74,.08) 0 1px,transparent 1px 10px),#0a0803"],pink:["#1a0628","linear-gradient(180deg,#12052e,#3a0b4a 55%,#16031e 62%,#07010c)"],
 white:["#0c1014","repeating-linear-gradient(0deg,rgba(255,255,255,.05) 0 1px,transparent 1px 4px),#0c1014"],black:["#020203","#020203"]};
function close(){page.classList.remove("on");page.innerHTML="";}
function frame(title,body,extra){return `<div class="in vx-glass vx-br ${extra||""}"><div class="top">${GL.replace('<img','<img style="height:34px"')}${WM}<span class="vx-badge" id="v4ver">v4.3</span><h2 style="margin-left:14px">${E(title)}</h2><button class="vx-btn x" id="v4x">Close</button></div>${body}</div>`;}
async function themes(){let d={themes:[],cur:"blue"};try{d=await A().v40_themes();}catch(e){}
 page.innerHTML=frame("Theme gallery",`<div class="vx-sub" style="margin-bottom:16px">EIGHT ORIGINAL THEMES · EACH ONE CHANGES THE CORE, BACKGROUND, FONTS AND LAYOUT ACCENTS · CLICK TO APPLY</div><div class="v4tg">${d.themes.map(t=>{const p=PV[t.k]||PV.blue,c=t.color;return `<div class="v4th vx-glass ${t.k==d.cur?"cur":""}" data-k="${t.k}"><div class="pv" style="background:${p[1]}"><div class="r" style="border-color:${c};opacity:.6"></div><div class="o" style="background:radial-gradient(circle,#fff 0,${c} 35%,transparent 70%)"></div><div class="cd" style="border-color:${c}"></div><div class="cd2" style="border-color:${c}"></div></div><div class="meta"><span class="vx-k" style="color:${c}">${E(t.k.toUpperCase())} · ${E(t.mode)}</span><b>${E(t.name)}</b><span class="vx-sub" style="letter-spacing:.05em">${E(t.desc)}</span></div></div>`}).join("")}</div>`);
 page.classList.add("on");page.querySelector("#v4x").onclick=close;
 page.querySelectorAll(".v4th").forEach(el=>el.onclick=async()=>{try{await A().v40_apply_theme(el.dataset.k);document.body.dataset.mode=el.dataset.k;}catch(e){}themes();});}
async function about(tab){let a={changelog:[],credits:[],safety:[]},sh={tiles:[]};try{a=await A().v40_about();sh=await A().v40_smart();}catch(e){}tab=tab||"about";
 const tabs=`<div class="v4tabs">${[["about","About"],["perms","Permissions"],["startup","Startup"],["changes","Changelog"],["smart","Smart home"],["privacy","Privacy"],["help","Help & updates"]].map(t=>`<button class="vx-btn ${t[0]==tab?"on":""}" data-tab="${t[0]}">${t[1]}</button>`).join("")}</div>`;
 let body="";
 if(tab=="about")body=`<div class="v4grid2"><div class="v4card vx-glass" style="text-align:center;padding:34px"><img src="brand/icon.png" style="width:120px;border-radius:26px"><div style="margin:16px 0 6px"><img src="brand/wordmark.svg" style="height:46px"></div><div class="vx-sub" style="font-size:14px;letter-spacing:.3em">${E(a.tagline||"")}</div><div style="margin-top:14px"><span class="vx-badge">VERSION ${E(a.version||"")}</span> <span class="vx-badge">LOCAL-FIRST</span> <span class="vx-badge">ORIGINAL ART</span></div></div>
  <div class="v4card vx-glass"><div class="vx-k">WHAT'S NEW IN ${E(a.version||"")}</div><p style="font:13px/1.7 var(--vx-f-ui);color:var(--vx-ink);margin-top:8px">${E((a.changelog[0]||["",""])[1])}</p><div class="vx-k" style="margin-top:16px">CREDITS</div>${(a.credits||[]).map(c=>`<div class="vx-row"><span>${E(c)}</span></div>`).join("")}</div></div>`;
 if(tab=="startup"){let w={};try{w=await A().v40_wizard();}catch(e){}body=`<div class="vx-row" style="font-size:14px;margin-bottom:10px"><span>Play intro presentation on startup</span><span class="vx-tog ${w.intro_on?"on":""}" data-i="intro_on"><i></i></span></div>
  <div class="vx-row" style="font-size:14px"><span>How often</span><span><button class="vx-btn ${w.intro_freq!="every"?"on":""}" data-f="day">First launch of the day</button> <button class="vx-btn ${w.intro_freq=="every"?"on":""}" data-f="every">Every launch</button></span></div>
  <div class="vx-row" style="font-size:14px;margin-top:10px"><span>Briefing cards when Vex wakes</span><span class="vx-tog ${w.brief_on_wake?"on":""}" data-i="brief_on_wake"><i></i></span></div>
  <div class="vx-sub" style="margin-top:14px">THE INTRO: BOOT → BRIEFING → MODE PREVIEWS → SCAN → BACK TO YOUR MODE. SKIP: CLICK, ESC OR SAY “SKIP”. NEVER DURING GAMES. NO SOUNDS UNLESS YOU TURN THEM ON. <a href="#" id="v4play" style="color:var(--vx-a)">PLAY IT NOW</a></div>`;}
 if(tab=="changes")body=(a.changelog||[]).map(c=>`<div class="v4cl"><b>v${E(c[0])}</b><p>${E(c[1])}</p></div>`).join("");
 if(tab=="smart")body=`<div class="vx-sub" style="margin-bottom:14px">OPT-IN · NOTHING IS CONNECTED UNTIL YOU ADD A HUB IN CONNECTIONS · VEX NEVER SIGNS IN FOR YOU</div>
  <div class="vx-row" style="font-size:13px;margin-bottom:6px"><span>Smart home enabled</span><span class="vx-tog ${sh.enabled?"on":""}" data-s="enabled"><i></i></span></div>
  <div class="vx-row" style="font-size:13px;margin-bottom:16px"><span>Modes change the room lights (red mode → red lights)</span><span class="vx-tog ${sh.mode_lights?"on":""}" data-s="mode_lights"><i></i></span></div>
  <div class="v4sh">${(sh.tiles||[]).map(t=>`<div class="t vx-glass vx-br"><div class="vx-k">${E(t.k.toUpperCase())}</div><div style="font:400 17px var(--vx-f-ui);color:#fff;margin-top:6px">${E(t.name)}</div><div class="st ${t.connected?"c":""}">${t.connected?"● CONNECTED":"○ DISCONNECTED"}</div></div>`).join("")}</div>`;
 if(tab=="privacy")body=(a.safety||[]).map(s=>`<div class="vx-row" style="font-size:14px"><span>✓ ${E(s)}</span></div>`).join("");
 if((tab=="perms"||tab=="help")&&window.v43Body)body=await window.v43Body(tab);
 page.innerHTML=frame("Settings · About",tabs+body);page.classList.add("on");page.querySelector("#v4x").onclick=close;
 page.querySelectorAll("[data-tab]").forEach(b=>b.onclick=()=>about(b.dataset.tab));
 if(window.v43Bind)window.v43Bind(tab,page,about);
 page.querySelectorAll("[data-i]").forEach(t=>t.onclick=async()=>{const o={};o[t.dataset.i]=!t.classList.contains("on");try{await A().v40_wizard_save(o);}catch(e){}about("startup");});
 page.querySelectorAll("[data-f]").forEach(b=>b.onclick=async()=>{try{await A().v40_wizard_save({intro_freq:b.dataset.f});}catch(e){}about("startup");});
 {const pl=page.querySelector("#v4play");if(pl)pl.onclick=e=>{e.preventDefault();close();try{A().v40_intro()}catch(x){}};}
 page.querySelectorAll("[data-s]").forEach(t=>t.onclick=async()=>{const o={};o[t.dataset.s]=!t.classList.contains("on");try{await A().v40_smart_save(o);}catch(e){}about("smart");});}
let WZ={i:0,d:{}},meterT=0,olT=0,vpT=0;
async function wizard(){try{WZ.d=await A().v40_wizard();}catch(e){WZ.d={user_name:"",assistant_name:"Vex",mode:"blue"};}
 try{WZ.dev=await A().pub_devices();}catch(e){WZ.dev={inputs:[],outputs:[]};}
 try{WZ.vp=await A().v43_voicepack();}catch(e){WZ.vp=null;}
 try{WZ.pm=await A().v43_perms();}catch(e){WZ.pm=null;}
 WZ.i=0;WZ.brain=WZ.brain||"local";drawWiz();}
function wzOl(){clearTimeout(olT);olT=0;(async()=>{let o={},j={};try{o=await A().pub_ollama();}catch(e){}try{j=await A().v43_ollama_job();}catch(e){}WZ.ol=o;WZ.oj=j;
 if(WZ.auto&&o.running&&!(o.models||[]).length&&!(o.pull&&o.pull.model)){WZ.auto=false;try{await A().pub_ollama_pull("qwen2.5:3b");}catch(e){}}
 if(WZ.i==3)drawWiz();
 if((o.pull&&o.pull.model&&!o.pull.done&&!o.pull.error)||(j.running)||(j.launched&&!o.running))olT=setTimeout(wzOl,1500);})();}
function wzVp(){clearTimeout(vpT);vpT=0;(async()=>{try{WZ.vp=await A().v43_voicepack();}catch(e){}if(WZ.vp&&WZ.vp.job&&WZ.vp.job.running)vpT=setTimeout(wzVp,1000);if(WZ.i==2)drawWiz();})();}
const MB=n=>Math.round((n||0)/1e6);
function drawWiz(){clearInterval(meterT);const d=WZ.d,i=WZ.i,N=8,dev=WZ.dev||{inputs:[],outputs:[]},an=(d.assistant_name||"Vex").trim()||"Vex";
 const mic=(id,q)=>`<button class="vx-btn" data-ask="${id}" data-q="${E(q)}" title="Answer by voice" ${WZ.vp&&WZ.vp.ready?"":"disabled style='opacity:.4' title='Needs the voice pack (step 3)'"}>🎤 Say it</button>`;
 const adr=[["sir","Sir"],["maam","Ma'am"],["name","By my name"],["none","Just talk normally"]];
 const opt=(arr,cur,def)=>`<option value="">${def}</option>`+arr.map(n=>`<option ${n==cur?"selected":""} value="${E(n)}">${E(n)}</option>`).join("");
 const bar=p=>`<div style="height:6px;background:rgba(255,255,255,.1);margin:10px 0"><div style="height:6px;width:${p||0}%;background:var(--vx-a,#6fe6ff);transition:width .4s"></div></div>`;
 // voice pack
 const vp=WZ.vp||{},vj=vp.job||{};let pack;
 if(!WZ.vp)pack=`<div class="vx-sub">CHECKING…</div>`;
 else if(vp.ready)pack=`<p style="font-size:15px">✓ Voice pack installed. You can talk to ${E(an)}.</p>${vj.restart?`<div class="vx-sub">${E(an.toUpperCase())} RESTARTS ONCE WHEN YOU FINISH SETUP SO VOICE TURNS ON.</div>`:""}`;
 else if(vj.running)pack=`<div class="vx-k">DOWNLOADING · ${vj.pct||0}% · ${MB(vj.got)} OF ${MB(vj.total)} MB</div>${bar(vj.pct)}<div class="vx-sub">${E(vj.part||"")} · YOU CAN KEEP GOING, IT FINISHES IN THE BACKGROUND</div><button class="vx-btn" id="wzVc" style="margin-top:8px">Cancel</button>`;
 else pack=`${vj.error?`<p style="color:#ff8a8a;font-size:13px">${E(vj.error)}</p>`:""}<p style="font-size:14px;line-height:1.55">To hear you, ${E(an)} needs its speech engine (about <b>${vp.size_mb||236} MB</b>, one time). It runs entirely on this PC.</p>
   <ul style="font-size:13px;line-height:1.7;margin:4px 0 12px 18px"><li>Speech engine: ctranslate2, tokenizers, onnxruntime, vosk from <b>PyPI</b></li><li>Speech model: Whisper base.en from <b>Hugging Face</b> (Systran)</li><li>Wake-word model: Vosk small English from <b>alphacephei.com</b></li></ul>
   <button class="vx-btn p" id="wzVd">Download voice pack</button> <span class="vx-sub" style="margin-left:8px">EVERY FILE IS CHECKED AGAINST A FIXED CHECKSUM</span>
   <div class="vx-sub" style="margin-top:10px">OR SKIP FOR NOW AND TYPE TO ${E(an.toUpperCase())}. YOU CAN DOWNLOAD IT LATER FROM SETUP.</div>`;
 // brain
 const ol=WZ.ol||{},oj=WZ.oj||{},pl=ol.pull||{},hasM=(ol.models||[]).length>0;let brain="";
 if(WZ.brain=="local"){
  if(!WZ.ol)brain=`<div class="vx-sub">CHECKING FOR OLLAMA…</div>`;
  else if(!ol.installed&&!ol.running){
   if(oj.running)brain=`<div class="vx-k">${E((oj.stage||"downloading").toUpperCase())} · ${oj.pct||0}%${oj.total?` · ${MB(oj.got)} OF ${MB(oj.total)} MB`:""}</div>${bar(oj.pct)}<div class="vx-sub">OFFICIAL INSTALLER FROM OLLAMA.COM · SIGNATURE CHECKED BEFORE IT RUNS</div>`;
   else if(oj.launched)brain=`<p style="font-size:14px">The Ollama setup window is open. Click <b>Install</b> there (Windows may ask for permission). This page notices when it's done.</p><button class="vx-btn" id="wzOC">Check again</button>`;
   else brain=`${oj.error?`<p style="color:#ff8a8a;font-size:13px">${E(oj.error)}</p>`:""}<p style="font-size:14px;line-height:1.55">${E(an)} thinks with <b>Ollama</b>, a free app that runs the AI on your PC. Nothing you say goes to the cloud.</p>
    <button class="vx-btn p" id="wzOI">Set up Ollama for me</button> <button class="vx-btn" id="wzOS">I'll get it from ollama.com</button> <button class="vx-btn" id="wzOC">Check again</button>
    <div class="vx-sub" style="margin-top:8px">DOWNLOADS THE OFFICIAL INSTALLER (ABOUT 1.6 GB), CHECKS ITS DIGITAL SIGNATURE, THEN OPENS IT FOR YOU. AFTER THAT THE FAST BRAIN (qwen2.5:3b, ABOUT 1.9 GB) DOWNLOADS AUTOMATICALLY.</div>`;}
  else if(pl.model&&!pl.done&&!pl.error)brain=`<div class="vx-k">DOWNLOADING ${E(pl.model)} · ${pl.pct||0}%</div>${bar(pl.pct)}<div class="vx-sub">${E(pl.status||"")} · YOU CAN FINISH SETUP, IT KEEPS GOING</div>`;
  else if(hasM&&!pl.error)brain=`<p style="font-size:15px">✓ Brain ready: <b>${E((ol.models||[]).join(", "))}</b></p>${(ol.models||[]).some(m=>m.startsWith("qwen2.5:7b"))?"":`<div class="vx-row" style="font-size:13px"><span>Optional <b>big brain</b> for hard questions · qwen2.5:7b · about 4.7 GB · needs a 6 GB+ GPU or 16 GB RAM</span><button class="vx-btn" data-pull="qwen2.5:7b">Download</button></div>`}`;
  else brain=`${pl.error?`<p style="color:#ff8a8a;font-size:13px">${E(pl.error)}</p>`:""}<p style="font-size:14px">Ollama is installed. Download the brain (one time):</p>
   <div class="vx-row" style="font-size:13px"><span><b>Fast brain</b> (recommended) · qwen2.5:3b · about 1.9 GB · quick answers on most PCs</span><button class="vx-btn p" data-pull="qwen2.5:3b">Download</button></div>
   <div class="vx-row" style="font-size:13px"><span><b>Big brain</b> (optional) · qwen2.5:7b · about 4.7 GB · for hard questions</span><button class="vx-btn" data-pull="qwen2.5:7b">Download</button></div>`;}
 else{const P=[["groq","Groq (free tier, very fast)"],["gemini","Google Gemini"],["openai","OpenAI (ChatGPT)"],["anthropic","Anthropic Claude"],["openrouter","OpenRouter"]],k=WZ.kp||"groq",r=WZ.kr;
  brain=`<p style="font-size:14px;line-height:1.55">Use an AI service you already have. Your key is encrypted with Windows and only sent to that service. Questions you ask go to them.</p>
   <label class="vx-k">SERVICE</label><select class="vx-in" id="wzKP">${P.map(([v,l])=>`<option value="${v}" ${v==k?"selected":""}>${l}</option>`).join("")}</select>
   <label class="vx-k">API KEY</label><div style="display:flex;gap:8px"><input class="vx-in" id="wzKK" type="password" autocomplete="off" placeholder="Paste your key"><button class="vx-btn p" id="wzKS">Save & test</button></div>
   ${r?`<p style="font-size:13px;color:${r.ok?"#8dffb0":"#ff8a8a"}">${r.ok?"✓ ":""}${E(r.msg||"")}</p>`:""}
   <div class="vx-sub">YOU PAY THE SERVICE DIRECTLY IF THEY CHARGE. ${E(an.toUpperCase())} NEVER BUYS ANYTHING.</div>`;}
 const pm=WZ.pm||{perms:[]},ov=(pm.perms.find(x=>x.k=="online_voice")||{}).on!==false;
 const S=[`<div class="vx-k">STEP 1 · WELCOME</div><h2 style="margin:10px 0">Let's set up your assistant.</h2>
   <label class="vx-k">WHAT'S YOUR NAME? <span style="opacity:.6">(OPTIONAL)</span></label><div style="display:flex;gap:8px"><input class="vx-in" id="wzN" value="${E(d.user_name||"")}" placeholder="Your name">${mic("wzN","What's your name?")}</div>
   <label class="vx-k">NAME YOUR ASSISTANT</label><div style="display:flex;gap:8px"><input class="vx-in" id="wzA" maxlength="20" value="${E(d.assistant_name||"Vex")}" placeholder="Vex">${mic("wzA","What would you like to call me?")}</div>
   <label class="vx-k">HOW SHOULD IT ADDRESS YOU?</label><div>${adr.map(([k,l])=>`<button class="vx-btn ${(d.address||"sir")==k?"on":""}" data-adr="${k}">${l}</button>`).join(" ")}</div>
   <label class="vx-k">YOUR CITY, FOR WEATHER <span style="opacity:.6">(OPTIONAL)</span></label><input class="vx-in" id="wzC" value="${E(d.weather_city||"")}" placeholder="e.g. Leeds">
   <div class="vx-sub" style="margin-top:10px">THE WAKE PHRASE BECOMES “HEY ${E(an.toUpperCase())}”. <a href="#" id="wzSkipAll" style="color:var(--vx-a)">SKIP SETUP AND USE DEFAULTS</a></div>`,
  `<div class="vx-k">STEP 2 · MIC & SPEAKERS</div><h2 style="margin:10px 0">Test your microphone and speakers.</h2>
   <label class="vx-k">MICROPHONE</label><select class="vx-in" id="wzM">${opt(dev.inputs,d.mic_device,"Windows default microphone")}</select>
   <div class="vx-row" style="font-size:13px;margin-top:8px"><span>Mic level (talk to test)</span><span style="display:flex;gap:3px" id="wzL">${Array.from({length:12},()=>`<i style="display:block;width:8px;height:14px;background:var(--vx-a,#6fe6ff);opacity:.15"></i>`).join("")}</span></div>
   <label class="vx-k" style="margin-top:12px">SPEAKERS / HEADPHONES</label><div style="display:flex;gap:8px"><select class="vx-in" id="wzO">${opt(dev.outputs,d.speaker_device,"Windows default output")}</select><button class="vx-btn" id="wzT">▶ Play test</button></div>
   <div class="vx-sub" style="margin-top:10px">LEVEL ONLY. YOUR VOICE IS NEVER RECORDED OR SAVED.</div>`,
  `<div class="vx-k">STEP 3 · VOICE PACK</div><h2 style="margin:10px 0">Download the voice pack.</h2>${pack}`,
  `<div class="vx-k">STEP 4 · THE BRAIN</div><h2 style="margin:10px 0">Choose how ${E(an)} thinks.</h2>
   <div class="v43choice">${[["local","Free local AI","Private · runs on your PC · Ollama"],["key","My own API key","Groq, Gemini, OpenAI, Claude…"]].map(([k,t,s])=>`<button class="vx-btn ${WZ.brain==k?"on":""}" data-brain="${k}"><b>${t}</b><small>${s}</small></button>`).join("")}</div>${brain}
   <div class="vx-sub" style="margin-top:12px">YOU CAN CHANGE THIS LATER IN CONNECTIONS.</div>`,
  `<div class="vx-k">STEP 5 · PICK A THEME</div><h2 style="margin:10px 0">Choose your look. You can change it any time.</h2><div class="v4tg" style="grid-template-columns:repeat(4,1fr)">${Object.keys(PV).map(k=>`<div class="v4th vx-glass ${k==d.mode?"cur":""}" data-k="${k}"><div class="pv" style="height:70px;background:${PV[k][1]}"></div><div class="meta"><span class="vx-k">${k.toUpperCase()}</span></div></div>`).join("")}</div>`,
  `<div class="vx-k">STEP 6 · INTRO</div><h2 style="margin:10px 0">Play the intro when ${E(an)} opens?</h2>
   <div class="vx-row" style="font-size:13px"><span>Play the intro presentation on startup</span><span class="vx-tog ${d.intro_on?"on":""}" id="wzI"><i></i></span></div>
   <div class="vx-row" style="font-size:13px;margin-top:8px"><span>How often</span><span><button class="vx-btn ${d.intro_freq!="every"?"on":""}" data-fq="day">First launch of the day</button> <button class="vx-btn ${d.intro_freq=="every"?"on":""}" data-fq="every">Every launch</button></span></div>
   <div class="vx-row" style="font-size:13px;margin-top:8px"><span>UI sound effects</span><span class="vx-tog ${d.ui_sounds?"on":""}" id="wzS"><i></i></span></div>
   <div class="vx-row" style="font-size:13px"><span>Briefing cards when ${E(an)} wakes</span><span class="vx-tog ${d.brief_on_wake?"on":""}" id="wzB"><i></i></span></div>
   <div class="vx-sub" style="margin-top:12px">SKIP THE INTRO ANY TIME: CLICK, PRESS ESC OR SAY “SKIP”. IT NEVER PLAYS DURING GAMES.</div>`,
  `<div class="vx-k">STEP 7 · PRIVACY</div><h2 style="margin:10px 0">Here's what ${E(an)} does with your data.</h2>
   <div class="v43priv">
   <div class="vx-row"><span>📷 Camera</span><b>OFF · only runs if you turn on hand control</b></div>
   <div class="vx-row"><span>🎙 Your voice</span><b>NEVER SAVED · turned into text in memory, then discarded</b></div>
   <div class="vx-row"><span>📡 Tracking</span><b>NONE · no account, no ID, no analytics, nothing uploaded about you</b></div>
   <div class="vx-row"><span>🔒 Risky actions</span><b>ALWAYS ASK FIRST · power, deletes, sends, running programs</b></div>
   <div class="vx-row"><span>📱 Phone notifications</span><b>OFF · opt in later with your own private topic</b></div>
   <div class="vx-row"><span>🔊 Online voice <small>Sends only the words ${E(an)} speaks to Microsoft's speech service for natural audio. Off = offline Windows voice.</small></span><span class="vx-tog ${ov?"on":""}" id="wzV"><i></i></span></div>
   </div><div class="vx-sub" style="margin-top:10px">EVERY SWITCH IS ON THE PERMISSIONS PAGE (SETTINGS › ABOUT › PERMISSIONS, OR SAY “OPEN PERMISSIONS”).</div>`,
  `<div class="vx-k">STEP 8 · READY</div><h2 style="margin:10px 0">All set${d.user_name?", "+E(d.user_name):""}.</h2>
   <div class="vx-row" style="font-size:14px"><span>Talk</span><b>SAY “HEY ${E(an.toUpperCase())}” OR HOLD CTRL+ALT+V</b></div>
   <div class="vx-row" style="font-size:14px"><span>Type</span><b>CLICK THE CHAT BOX</b></div>
   <div class="vx-row" style="font-size:14px"><span>Stop everything</span><b>CTRL+ALT+X OR “${E(an.toUpperCase())} STOP”</b></div>
   <div class="vx-row" style="font-size:14px"><span>Help</span><b>“WHAT CAN YOU DO?”</b></div>
   ${WZ.vp&&WZ.vp.ready?"":`<div class="vx-sub" style="margin-top:10px;color:#ffc46b">VOICE IS OFF UNTIL THE VOICE PACK IS DOWNLOADED (STEP 3).</div>`}`];
 page.innerHTML=frame("Setup",`<div class="v4dots">${Array.from({length:N},(_,k)=>`<i class="${k<=i?"on":""}"></i>`).join("")}</div><div class="st">${S[i]}</div><div class="nav"><button class="vx-btn" id="wzB1" ${i==0?"style='visibility:hidden'":""}>Back</button><button class="vx-btn p" id="wzN1">${i==N-1?"Finish":(i==2&&!(WZ.vp&&WZ.vp.ready)&&!vj.running)||(i==3&&!hasM&&WZ.brain=="local")?"Skip for now":"Next"}</button></div>`,"v4wz");
 page.classList.add("on");page.querySelector("#v4x").onclick=close;
 const g=id=>document.getElementById(id);
 const keep=()=>{if(g("wzN"))d.user_name=g("wzN").value.trim();if(g("wzA"))d.assistant_name=g("wzA").value.trim()||"Vex";if(g("wzC"))d.weather_city=g("wzC").value.trim();if(g("wzM"))d.mic_device=g("wzM").value;if(g("wzO"))d.speaker_device=g("wzO").value;};
 page.querySelectorAll("[data-ask]").forEach(b=>b.onclick=async()=>{keep();b.textContent="Listening…";b.disabled=true;let r={};try{r=await A().pub_listen(b.dataset.q);}catch(e){}
  const inp=g(b.dataset.ask);if(r&&r.text&&inp){inp.value=r.text.replace(/^\w/,c=>c.toUpperCase());}b.textContent=r&&r.text?"🎤 Again":"🎤 Didn't catch that";b.disabled=false;keep();});
 page.querySelectorAll("[data-adr]").forEach(b=>b.onclick=()=>{keep();d.address=b.dataset.adr;drawWiz();});
 {const a=g("wzA");if(a)a.oninput=()=>{keep();const s=page.querySelector(".st .vx-sub");if(s&&s.firstChild)s.firstChild.nodeValue="THE WAKE PHRASE BECOMES “HEY "+((a.value.trim()||"Vex").toUpperCase())+"”. ";};}
 {const sk=g("wzSkipAll");if(sk)sk.onclick=async e=>{e.preventDefault();keep();try{await A().v40_wizard_save({user_name:d.user_name||"",assistant_name:an,address:d.address||"sir",setup_done:true});}catch(x){}close();location.reload();};}
 if(i==1){const sv=async()=>{keep();try{await A().v40_wizard_save({mic_device:d.mic_device||"",speaker_device:d.speaker_device||""});}catch(e){}};
  ["wzM","wzO"].forEach(id=>{const s=g(id);if(s)s.onchange=sv;});
  const t=g("wzT");if(t)t.onclick=async()=>{await sv();t.textContent="▶ Playing…";try{await A().v43_speaker_test();}catch(e){}setTimeout(()=>{if(g("wzT"))g("wzT").textContent="▶ Play again";},3500);};
  meterT=setInterval(async()=>{let v=0;try{v=(await A().pub_mic_level()).lvl||0;}catch(e){}const L=g("wzL");if(L){const n=Math.round(Math.min(1,v*2.2)*12);[...L.children].forEach((b,k)=>b.style.opacity=k<n?"1":".15");}},120);}
 if(i==2){if(!WZ.vp||(WZ.vp.job&&WZ.vp.job.running&&!vpT))wzVp();
  const dl=g("wzVd");if(dl)dl.onclick=async()=>{try{WZ.vp=await A().v43_voicepack_install();}catch(e){}drawWiz();wzVp();};
  const vc=g("wzVc");if(vc)vc.onclick=async()=>{try{await A().v43_voicepack_cancel();}catch(e){}wzVp();};}
 if(i==3){if(!WZ.ol&&WZ.brain=="local")wzOl();
  page.querySelectorAll("[data-brain]").forEach(b=>b.onclick=()=>{WZ.brain=b.dataset.brain;drawWiz();if(WZ.brain=="local")wzOl();});
  const os=g("wzOS");if(os)os.onclick=()=>{try{A().pub_open_ollama_site()}catch(e){}};
  const oi=g("wzOI");if(oi)oi.onclick=async()=>{WZ.auto=true;try{WZ.oj=await A().v43_ollama_install();}catch(e){}wzOl();};
  const oc=g("wzOC");if(oc)oc.onclick=()=>{WZ.ol=null;drawWiz();wzOl();};
  page.querySelectorAll("[data-pull]").forEach(b=>b.onclick=async()=>{try{await A().pub_ollama_pull(b.dataset.pull);}catch(e){}wzOl();});
  const kp=g("wzKP");if(kp)kp.onchange=()=>{WZ.kp=kp.value;WZ.kr=null;};
  const ks=g("wzKS");if(ks)ks.onclick=async()=>{const k=(g("wzKK").value||"").trim(),p=g("wzKP").value;WZ.kp=p;if(!k){WZ.kr={ok:false,msg:"Paste a key first."};drawWiz();return;}
   ks.textContent="Testing…";ks.disabled=true;let r={};try{await A().conn_save(p,{key:k});await A().conn_route(p,"");r=await A().conn_test(p);}catch(e){r={ok:false,msg:String(e)};}
   WZ.kr={ok:!!(r&&r.ok),msg:(r&&r.msg)||(r&&r.ok?"Connected.":"That key didn't work.")};drawWiz();};}
 {const t=g("wzI");if(t)t.onclick=()=>{d.intro_on=!d.intro_on;drawWiz();};page.querySelectorAll("[data-fq]").forEach(b=>b.onclick=()=>{d.intro_freq=b.dataset.fq;drawWiz();});}
 page.querySelectorAll(".st .v4th").forEach(el=>el.onclick=()=>{d.mode=el.dataset.k;try{document.body.dataset.mode=el.dataset.k;}catch(e){}drawWiz();});
 ["wzS","wzB"].forEach(id=>{const t=g(id);if(t)t.onclick=()=>{if(id=="wzS")d.ui_sounds=!d.ui_sounds;else d.brief_on_wake=!d.brief_on_wake;drawWiz();};});
 {const v=g("wzV");if(v)v.onclick=async()=>{const on=!v.classList.contains("on");try{WZ.pm=await A().v43_perm_set("online_voice",on);}catch(e){const x=(WZ.pm.perms||[]).find(x=>x.k=="online_voice");if(x)x.on=on;}drawWiz();};}
 page.querySelector("#wzB1").onclick=()=>{keep();WZ.i=Math.max(0,i-1);drawWiz();};
 page.querySelector("#wzN1").onclick=async()=>{keep();if(i<N-1){WZ.i++;drawWiz();return;}
  try{await A().v40_wizard_save({user_name:d.user_name||"",assistant_name:an,address:d.address||"sir",weather_city:d.weather_city||"",mic_device:d.mic_device||"",speaker_device:d.speaker_device||"",mode:d.mode,ui_sounds:!!d.ui_sounds,brief_on_wake:!!d.brief_on_wake,intro_on:!!d.intro_on,intro_freq:d.intro_freq||"day",setup_done:true});}catch(e){}
  const rs=WZ.vp&&WZ.vp.job&&WZ.vp.job.restart;
  page.innerHTML=frame("Setup",`<div style="text-align:center;padding:60px 0"><img src="brand/icon.png" style="width:96px;border-radius:22px"><h2 style="margin-top:18px;font-size:34px">Welcome${d.user_name?", "+E(d.user_name):""}.</h2><div class="vx-sub" style="margin-top:8px">${E(an.toUpperCase())} IS ${rs?"RESTARTING TO TURN ON VOICE":"ONLINE"} · SAY “HEY ${E(an.toUpperCase())}”</div></div>`,"v4wz");page.querySelector("#v4x").onclick=close;
  setTimeout(()=>{close();if(rs){try{A().v43_restart()}catch(e){location.reload();}}else location.reload();},3500);};}
(function(){const st=document.createElement("style");st.textContent=`.v43choice{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:4px 0 14px}.v43choice .vx-btn{display:flex;flex-direction:column;align-items:flex-start;gap:4px;padding:12px 14px;text-align:left}.v43choice small{opacity:.7;font-size:11px;letter-spacing:.04em}.v43priv .vx-row{font-size:13px;padding:7px 0;gap:16px}.v43priv .vx-row>span{display:flex;flex-direction:column;gap:2px}.v43priv small{opacity:.7;font-size:11px;max-width:52ch}.v43priv b{text-align:right;font-size:12px;letter-spacing:.04em}`;document.head.appendChild(st);})();
window.vexPage=p=>p=="themes"?themes():p=="about"?about():p=="perms"?about("perms"):p=="help"?about("help"):p=="wizard"?wizard():close();
addEventListener("keydown",e=>{if(e.key=="Escape"&&page.classList.contains("on"))close();if(e.key=="Escape"&&window.__v4intro){try{A().v40_skip()}catch(x){}}});
addEventListener("mousedown",()=>{if(window.__v4intro){try{A().v40_skip()}catch(x){}}});
boot.addEventListener("click",()=>{if(window.__v4intro){try{A().v40_skip()}catch(x){}}});

// ---------- 4. memory tab polish: searchable list with delete
async function memPolish(){const host=document.getElementById("memory");if(!host||document.getElementById("v4mem"))return;
 const box=document.createElement("div");box.id="v4mem";box.className="vx-glass vx-br";box.style.cssText="padding:16px;margin:16px 0";
 box.innerHTML=`<div class="vx-k">MEMORY VAULT</div><div class="vx-sub" style="margin:6px 0 10px">EVERYTHING VEX REMEMBERS · STORED ONLY ON THIS PC · DELETE ANYTHING</div><input class="vx-in" id="v4mq" placeholder="Search memories"><div id="v4ml" style="margin-top:10px"></div>`;
 const sc=host.querySelector(".scroll>div")||host;sc.prepend(box);const draw=async()=>{let m=[];try{m=await A().memory_list();}catch(e){}const q=(document.getElementById("v4mq").value||"").toLowerCase();
  const L=(m||[]).filter(x=>!q||String(x.text||"").toLowerCase().includes(q));
  document.getElementById("v4ml").innerHTML=L.length?L.slice().reverse().map(x=>`<div class="vx-row" style="border-bottom:1px solid var(--vx-line);padding:4px 0"><span style="color:var(--vx-ink);white-space:normal">${E(x.text)}</span><span><span class="vx-sub">${E(String(x.at||x.t||"").slice(0,10))}</span> <button class="vx-btn" data-del="${E(x.id)}" style="padding:2px 10px">Delete</button></span></div>`).join(""):`<div class="vx-sub">NOTHING YET · SAY “REMEMBER THAT …”</div>`;
  document.querySelectorAll("#v4ml [data-del]").forEach(b=>b.onclick=async()=>{if(!confirm("Delete this memory?"))return;try{await A().memory_delete(b.dataset.del);}catch(e){}draw();});};
 document.getElementById("v4mq").oninput=draw;draw();setInterval(()=>{if(host.offsetParent)draw();},15000);}

// ---------- events
const prev=window.vexOn;
window.vexOn=(ev,d)=>{try{
  if(ev=="transcript"&&d)caption(d.who,d.text);
  else if(ev=="intro"&&d){window.__v4intro=!!d.on;}
  else if(ev=="briefing")showBrief(d);else if(ev=="media")showMedia(d);else if(ev=="step")addStep(d);
  else if(ev=="boot")playBoot(d);else if(ev=="page")window.vexPage(d&&d.page);else if(ev=="scanfx")scanFx();
  else if(ev=="modeset"&&d&&d.mode)document.body.dataset.mode=d.mode;
 }catch(e){}return prev&&prev(ev,d);};
function start(){memPolish();(async()=>{try{const w=await A().v40_wizard();if(!w.done){setTimeout(wizard,9000);}}catch(e){}})();
 try{A().v40_steps().then(s=>{STEPS=s||[];drawSteps();});}catch(e){}
 if(!window.__v4booted){window.__v4booted=1;window.vexBoot();}}
if(A())setTimeout(start,200);else addEventListener("pywebviewready",()=>setTimeout(start,200));
})();
