// Vex 3.4 effects: voice-reactive orb feed, synthesised UI sounds, cinematic boot line, full-scan visualisation, holo notification cards.
(function(){
const A=()=>window.pywebview&&window.pywebview.api,E=s=>String(s==null?"":s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
let SND=false;setInterval(async()=>{try{const h=await A().hand_state();SND=!!h.sounds&&h.mode!="black";}catch(e){}},4000);
// ---------- sounds (pure WebAudio synthesis, original)
let ac=null;const ctx=()=>ac||(ac=new (window.AudioContext||window.webkitAudioContext)());
function tone(f0,f1,dur,vol,type,delay){if(!SND)return;try{const c=ctx();if(c.state=="suspended")c.resume();const t=c.currentTime+(delay||0),o=c.createOscillator(),g=c.createGain(),fl=c.createBiquadFilter();
 o.type=type||"sine";o.frequency.setValueAtTime(f0,t);o.frequency.exponentialRampToValueAtTime(Math.max(20,f1),t+dur);fl.type="lowpass";fl.frequency.value=3800;
 g.gain.setValueAtTime(0.0001,t);g.gain.exponentialRampToValueAtTime(vol,t+0.012);g.gain.exponentialRampToValueAtTime(0.0001,t+dur);o.connect(fl);fl.connect(g);g.connect(c.destination);o.start(t);o.stop(t+dur+0.05);}catch(e){}}
const SFX={wake:()=>{tone(520,1040,.16,.05,"sine");tone(780,1560,.18,.03,"triangle",.07);},think:()=>tone(1400,1200,.05,.02,"square"),
 reply:()=>{tone(880,660,.12,.035);},alert:()=>{tone(660,990,.12,.05,"triangle");tone(990,1320,.16,.04,"triangle",.13);},
 boot:()=>{[0,.12,.24,.36].forEach((d,i)=>tone(300+i*180,320+i*190,.22,.035,"sine",d));tone(120,60,1.2,.05,"sine",.4);},
 whoosh:()=>tone(1800,90,.9,.04,"sawtooth"),scan:()=>{for(let i=0;i<10;i++)tone(900+i*60,900+i*60,.03,.015,"square",i*.09);}};
window.vexSfx=k=>SFX[k]&&SFX[k]();
// ---------- hook events
let lastState="";
if(window.vexOn){const o=window.vexOn;window.vexOn=(ev,d)=>{try{
 if(ev=="level")window.__lvl={v:+d.v||0,src:d.src||"",t:performance.now()};
 else if(ev=="state"&&d&&d.state!=lastState){const s=d.state;if(s=="listening"&&lastState!="listening")SFX.wake();else if(s=="thinking")SFX.think();else if(s=="speaking"&&lastState=="thinking")SFX.reply();lastState=s;}
 else if(ev=="notify"){SFX.alert();card(d.title,d.text);try{loadDash()}catch(e){}}
 else if(ev=="bootdone"){bootTitle();}
 else if(ev=="scan"){scanFx(d);}
 }catch(e){}if(ev=="notify")return;return o(ev,d);};}
// protocol whoosh
if(window.vexProtocol){const p=window.vexProtocol;window.vexProtocol=(a,b)=>{try{SFX.alert();setTimeout(SFX.whoosh,5000);}catch(e){}return p(a,b);};}
// ---------- styles
const st=document.createElement("style");st.textContent=`
#vxCards{position:fixed;right:28px;top:90px;z-index:9995;display:flex;flex-direction:column;gap:12px;perspective:900px;pointer-events:none}
.vxCard{pointer-events:auto;width:340px;padding:12px 16px 12px 18px;background:linear-gradient(150deg,rgba(6,26,40,.86),rgba(2,8,16,.92));border:1px solid rgba(95,243,255,.35);color:#cdefff;
 box-shadow:0 20px 50px -18px #000,0 0 30px rgba(25,216,255,.12);clip-path:polygon(0 0,calc(100% - 16px) 0,100% 16px,100% 100%,16px 100%,0 calc(100% - 16px));
 animation:vxCin .7s cubic-bezier(.2,.9,.2,1) both;position:relative;overflow:hidden;cursor:pointer}
.vxCard::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:#5ff3ff;box-shadow:0 0 12px #19d8ff}
.vxCard::after{content:"";position:absolute;inset:0;background:linear-gradient(100deg,transparent 30%,rgba(255,255,255,.12) 50%,transparent 70%);transform:translateX(-120%);animation:vxShn 1.1s .35s ease-out}
.vxCard b{display:block;font:400 11px VexMono,monospace;letter-spacing:.3em;color:#7fefff;margin-bottom:5px}.vxCard span{font-size:14px;line-height:1.4}
.vxCard.out{animation:vxCout .45s ease-in forwards}
@keyframes vxCin{0%{opacity:0;transform:translateX(120px) rotateY(-50deg) scale(.9);filter:blur(6px) brightness(2)}100%{opacity:1;transform:none;filter:none}}
@keyframes vxCout{to{opacity:0;transform:translateX(80px) rotateY(-30deg) scale(.92);filter:blur(4px)}}@keyframes vxShn{to{transform:translateX(120%)}}
#vxBoot{position:fixed;inset:0;z-index:9996;pointer-events:none;display:grid;place-items:center;opacity:0;transition:opacity .5s}#vxBoot.on{opacity:1}
#vxBoot .t{font:300 clamp(18px,2vw,40px) VexMono,monospace;letter-spacing:.6em;color:#dffcff;text-shadow:0 0 18px #19d8ff;text-align:center;margin-top:46vh}
#vxBoot .t small{display:block;font-size:.4em;letter-spacing:.8em;color:#5ff3ffaa;margin-top:12px}
#vxBoot i{position:absolute;left:50%;top:50%;width:20px;height:20px;margin:-10px;border-radius:50%;border:1px solid #5ff3ff;box-shadow:0 0 20px #19d8ff;animation:vxBr 1.6s cubic-bezier(.1,.7,.3,1) forwards}
#vxBoot i:nth-child(2){animation-delay:.18s}#vxBoot i:nth-child(3){animation-delay:.36s}@keyframes vxBr{0%{opacity:1;transform:scale(1)}100%{opacity:0;transform:scale(90)}}
#vxDiag{position:fixed;inset:0;z-index:9994;pointer-events:none;opacity:0;transition:opacity .6s;font-family:VexMono,monospace;color:#bff8ff;background:radial-gradient(ellipse at 50% 50%,rgba(1,10,18,.55),rgba(0,3,10,.88))}
#vxDiag.on{opacity:1}#vxDiag .sweep{position:absolute;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,#5ff3ff,transparent);box-shadow:0 0 22px #19d8ff,0 0 60px #19d8ff;top:0;animation:vxSw 2.2s cubic-bezier(.4,0,.2,1) 2}
@keyframes vxSw{0%{top:0}50%{top:100%}100%{top:0}}
#vxDiag h2{position:absolute;top:7vh;left:0;right:0;text-align:center;font-weight:300;letter-spacing:.7em;font-size:clamp(16px,1.5vw,30px);margin:0;color:#dffcff;text-shadow:0 0 14px #19d8ff}
#vxDiag .grid{position:absolute;left:6vw;right:6vw;top:16vh;bottom:12vh;display:grid;grid-template-columns:repeat(4,1fr);gap:22px}
#vxDiag .c{border:1px solid rgba(95,243,255,.25);background:rgba(2,12,20,.6);padding:16px 18px;opacity:0;transform:translateY(20px) scale(.96);transition:all .55s cubic-bezier(.2,.9,.2,1);clip-path:polygon(0 0,calc(100% - 14px) 0,100% 14px,100% 100%,14px 100%,0 calc(100% - 14px));position:relative}
#vxDiag .c.on{opacity:1;transform:none}#vxDiag .c b{font-weight:400;font-size:10px;letter-spacing:.35em;color:#7fefffaa}
#vxDiag .c .v{font-size:clamp(28px,2.6vw,54px);font-weight:300;margin:8px 0 2px;color:#fff;text-shadow:0 0 14px rgba(34,229,255,.5)}#vxDiag .c small{color:#8fc8d6;font-size:11px;letter-spacing:.12em}
#vxDiag .ring{width:110px;height:110px;float:right;margin:-6px -4px 0 6px}#vxDiag .c.warn{border-color:#ffd166aa}#vxDiag .c.warn .v{color:#ffd166}
#vxDiag .c .ln{font-size:11px;color:#a9d8e4;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#vxDiag .verdict{position:absolute;bottom:5vh;left:0;right:0;text-align:center;letter-spacing:.6em;font-size:14px;color:#4ade80;text-shadow:0 0 12px #4ade80;opacity:0;transition:opacity .6s}#vxDiag .verdict.on{opacity:1}#vxDiag .verdict.w{color:#ffd166;text-shadow:0 0 12px #ffb703}`;
document.head.appendChild(st);
const cards=document.createElement("div");cards.id="vxCards";document.body.appendChild(cards);
function card(t,x){const d=document.createElement("div");d.className="vxCard";d.innerHTML=`<b>${E(String(t||"NOTICE").toUpperCase())}</b><span>${E(x||"")}</span>`;cards.prepend(d);
 const kill=()=>{d.classList.add("out");setTimeout(()=>d.remove(),460);};d.onclick=kill;setTimeout(kill,14000);while(cards.children.length>4)cards.lastChild.remove();}
window.vexCard=card;window.toast=(t,x)=>card(t,x);
function bootTitle(){if(document.getElementById("vxBoot"))return;const b=document.createElement("div");b.id="vxBoot";const h=new Date().getHours(),tod=h<5?"NIGHT WATCH":h<12?"GOOD MORNING":h<18?"GOOD AFTERNOON":"GOOD EVENING";
 b.innerHTML=`<i></i><i></i><i></i><div class="t">ALL SYSTEMS ONLINE<small>${tod} // ${E(new Date().toLocaleTimeString([], {hour:"numeric",minute:"2-digit"}))}</small></div>`;document.body.appendChild(b);
 SFX.boot();requestAnimationFrame(()=>b.classList.add("on"));setTimeout(()=>b.classList.remove("on"),3600);setTimeout(()=>b.remove(),4300);}
window.vexBootTitle=bootTitle;
function ring(p,warn){p=Math.max(0,Math.min(100,+p||0));const r=46,c=2*Math.PI*r;const col=warn?"#ffd166":"#5ff3ff";
 return `<svg class="ring" viewBox="0 0 110 110"><circle cx="55" cy="55" r="${r}" fill="none" stroke="#0b2a36" stroke-width="5"/><circle cx="55" cy="55" r="${r}" fill="none" stroke="${col}" stroke-width="5" stroke-linecap="round" stroke-dasharray="0 ${c}" transform="rotate(-90 55 55)" style="filter:drop-shadow(0 0 6px ${col})"><animate attributeName="stroke-dasharray" from="0 ${c}" to="${c*p/100} ${c}" dur="1.2s" fill="freeze"/></circle>
 <circle cx="55" cy="55" r="36" fill="none" stroke="${col}" stroke-opacity=".25" stroke-dasharray="2 4"/></svg>`;}
function scanFx(d){const old=document.getElementById("vxDiag");old&&old.remove();const s=document.createElement("div");s.id="vxDiag";const up=+d.uptime||0;
 const C=[];const add=(k,v,sub,p,warn,extra)=>C.push(`<div class="c ${warn?"warn":""}">${p!=null?ring(p,warn):""}<b>${k}</b><div class="v">${E(v)}</div><small>${E(sub||"")}</small>${extra||""}</div>`);
 add("PROCESSOR",(d.cpu??"--")+"%","CPU LOAD",d.cpu,(d.cpu||0)>90);add("MEMORY",(d.ram??"--")+"%",(d.ram_total||"?")+" GB INSTALLED",d.ram,(d.ram||0)>88);
 add("GRAPHICS",d.gpu!=null?d.gpu+"%":"--",(d.gpu_name||"GPU")+(d.vram!=null?" · VRAM "+d.vram+"%":""),d.gpu,false);
 add("THERMALS",d.gpu_temp!=null?d.gpu_temp+"°C":"--","GPU CORE TEMP",d.gpu_temp!=null?Math.min(100,d.gpu_temp):null,(d.gpu_temp||0)>83);
 (d.drives||[]).slice(0,2).forEach(x=>add("DRIVE "+x.d+":",x.used+"%",x.free+" GB FREE OF "+x.total,x.used,x.used>92));
 add("NETWORK",d.net&&d.net.latency!=null?d.net.latency+" ms":"OFFLINE",(d.net&&d.net.ip||"")+" · "+(d.net&&d.net.host||""),null,!(d.net&&d.net.latency!=null),
  `<div class="ln">↓ ${E(d.net_down??"--")}   ↑ ${E(d.net_up??"--")}</div>`);
 add("PROCESSES",d.procs||"--","UPTIME "+String(up/3600|0).padStart(2,"0")+":"+String(up/60%60|0).padStart(2,"0"),null,false,(d.top||[]).slice(0,4).map(t=>`<div class="ln">${E(t.name)} · ${t.mb} MB</div>`).join(""));
 const w=(d.warn||[]).length;
 s.innerHTML=`<div class="sweep"></div><h2>FULL SYSTEM DIAGNOSTIC // ${E(d.at||"")}</h2><div class="grid">${C.join("")}</div><div class="verdict ${w?"w":""}">${w?"ATTENTION // "+E(d.warn.join(" · ").toUpperCase()):"SCAN COMPLETE // ALL SYSTEMS NOMINAL"}</div>`;
 document.body.appendChild(s);SFX.scan();requestAnimationFrame(()=>s.classList.add("on"));
 s.querySelectorAll(".c").forEach((c,i)=>setTimeout(()=>c.classList.add("on"),500+i*260));setTimeout(()=>s.querySelector(".verdict").classList.add("on"),500+C.length*260+300);
 s.style.pointerEvents="auto";s.onclick=()=>{s.classList.remove("on");setTimeout(()=>s.remove(),600);};
 setTimeout(()=>{s.classList.remove("on");setTimeout(()=>s.remove(),700);},16000);}
window.vexScanFx=scanFx;
})();
