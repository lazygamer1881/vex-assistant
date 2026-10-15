// Vex 3.3 cinematic "<colour> protocol". Same timeline on every monitor (role "main" = orb monitor, "side" = others). Total 7.2s.
(function(){
const css=`#vxP{position:fixed;inset:0;z-index:2147483000;background:#000;opacity:0;transition:opacity .35s;overflow:hidden;font-family:VexMono,"Share Tech Mono",monospace;pointer-events:none}
#vxP.on{opacity:1}#vxP .l{position:absolute;inset:0;display:grid;place-items:center;opacity:0;transition:opacity .25s}#vxP .l.on{opacity:1}
#vxP .rend{font-size:clamp(18px,2.2vw,44px);letter-spacing:.9em;color:var(--pc);text-shadow:0 0 18px var(--pc);animation:vxPf .32s steps(2) infinite}
#vxP .rend small{display:block;text-align:center;font-size:.32em;letter-spacing:.5em;margin-top:18px;opacity:.7}
@keyframes vxPf{50%{opacity:.15}}
#vxP .ttl{text-align:center;color:#fff}#vxP .ttl b{display:block;font-weight:400;font-size:clamp(40px,7.5vw,170px);letter-spacing:.18em;color:var(--pc);text-shadow:0 0 30px var(--pc),0 0 90px var(--pc);
 animation:vxPt 1.8s cubic-bezier(.2,.9,.2,1) both}#vxP .ttl i{display:block;font-style:normal;font-size:clamp(12px,1vw,20px);letter-spacing:1.1em;color:var(--pc);opacity:.8;margin-top:10px}
#vxP .ttl:before,#vxP .ttl:after{content:"";display:block;height:1px;margin:24px auto;width:0;background:linear-gradient(90deg,transparent,var(--pc),transparent);animation:vxPw 1.2s .2s ease-out forwards}
@keyframes vxPw{to{width:min(80vw,1400px)}}
@keyframes vxPt{0%{opacity:0;letter-spacing:1em;filter:blur(14px)}60%{opacity:1;filter:blur(0)}100%{letter-spacing:.18em}}
#vxP .term{place-items:start;padding:3vh 3vw;font-size:clamp(10px,.8vw,15px);line-height:1.45;color:var(--pc);text-shadow:0 0 6px var(--pc);white-space:pre;overflow:hidden}
#vxP .orbp{position:absolute;left:var(--ox,50%);top:50%;width:16px;height:16px;margin:-8px;border-radius:50%;background:#fff;box-shadow:0 0 30px 8px var(--pc),0 0 80px 30px var(--pc);opacity:0;transform:scale(.2)}
#vxP .orbp.go{animation:vxPo 1.1s ease-in forwards}@keyframes vxPo{0%{opacity:0;transform:scale(.2)}30%{opacity:1;transform:scale(1)}85%{transform:scale(2.2)}100%{opacity:1;transform:scale(1.4)}}
#vxP .wave{position:absolute;left:var(--ox,50%);top:50%;width:10px;height:10px;margin:-5px;border-radius:50%;border:3px solid var(--pc);box-shadow:0 0 40px var(--pc),inset 0 0 40px var(--pc);opacity:0}
#vxP .wave.go{animation:vxPs 1.05s cubic-bezier(.1,.7,.3,1) forwards}#vxP .wave.w2.go{animation-delay:.12s}
@keyframes vxPs{0%{opacity:1;transform:scale(1)}100%{opacity:0;transform:scale(420)}}
#vxP .flash{position:absolute;inset:0;background:radial-gradient(circle at var(--ox,50%) 50%,#fff 0%,var(--pc) 35%,transparent 75%);opacity:0}
#vxP .flash.go{animation:vxPx .9s ease-out forwards}@keyframes vxPx{0%{opacity:0}18%{opacity:1}100%{opacity:0}}
#vxP .scan{position:absolute;inset:0;background:repeating-linear-gradient(0deg,rgba(255,255,255,.04) 0 1px,transparent 1px 3px)}`;
function hex(n){return Array.from({length:n},()=>"0123456789ABCDEF"[Math.random()*16|0]).join("");}
const LINES=["> handshake :: core.local","> palette.matrix rebuild","> shader cache invalidate","> recolor nodes","> sync display bus","> uplink monitor[{m}] ok","> theme.vault write","> reactor ring phase {p}","> chroma shift {h}"];
window.vexProtocol=function(p,role){
 if(document.getElementById("vxP"))return;
 if(!document.getElementById("vxPcss")){const s=document.createElement("style");s.id="vxPcss";s.textContent=css;document.head.appendChild(s);}
 const pre=document.documentElement.style.filter;document.documentElement.style.filter="none"; // overlay shows the true colour
 const o=document.createElement("div");o.id="vxP";o.style.setProperty("--pc",p.color);o.style.setProperty("--ox",role=="side"?"115%":"50%");
 const name=String(p.name||"").toUpperCase();
 o.innerHTML=`<div class="l a"><div class="rend">RENDERING<small>${name} PALETTE</small></div></div><div class="l b"><div class="ttl"><b>${name} PROTOCOL</b><i>VEX // CHROMA OVERRIDE</i></div></div>
 <div class="l t term"></div><div class="orbp"></div><div class="wave"></div><div class="wave w2"></div><div class="flash"></div><div class="scan"></div>`;
 document.body.appendChild(o);const q=s=>o.querySelector(s),show=(c,on)=>q(c).classList.toggle("on",on),at=(t,f)=>setTimeout(f,t*1000);
 requestAnimationFrame(()=>o.classList.add("on"));
 let tt=0;const term=q(".t"),tick=()=>{const L=LINES[Math.random()*LINES.length|0].replace("{m}",1+(Math.random()*2|0)).replace("{p}",(Math.random()*360|0)+"°").replace("{h}",name.toLowerCase());
  term.textContent=(term.textContent+"\n"+L+"  0x"+hex(8)+"  "+hex(16)).split("\n").slice(-60).join("\n");};
 if(role=="main"){at(.4,()=>show(".a",true));at(1.7,()=>{show(".a",false);show(".b",true);});}
 else{at(.4,()=>{show(".t",true);tt=setInterval(tick,28);});}
 at(1.9,()=>{if(role=="main")return;});
 at(3.5,()=>{show(".a",false);show(".b",false);show(".t",false);clearInterval(tt);});
 at(4.0,()=>q(".orbp").classList.add("go"));
 at(5.1,()=>{q(".orbp").style.opacity=0;q(".wave").classList.add("go");o.querySelectorAll(".wave")[1].classList.add("go");q(".flash").classList.add("go");
  try{const L=p.look||{};if(window.vexApplyLook&&p.look){vexApplyLook(L); // new theme behind the flash; counter-filter keeps the overlay its true colour
   const f=[];if(L.dark)f.push(`brightness(${(1/(1-L.dark)).toFixed(3)})`);if(L.sat&&L.sat!=1)f.push(`saturate(${(1/Math.max(.05,L.sat)).toFixed(3)})`);if(L.hue)f.push(`hue-rotate(${-L.hue}deg)`);o.style.filter=f.join(" ");}
   else document.documentElement.style.filter=pre;}catch(e){}});
 at(6.3,()=>o.classList.remove("on"));
 at(7.2,()=>{o.remove();try{window.vexUiLog&&vexUiLog("protocol: "+name+" sequence done ("+role+")");}catch(e){}});
};
})();
