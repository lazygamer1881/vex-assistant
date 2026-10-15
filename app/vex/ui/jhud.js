// Vex 3.7 reactor HUD for the expanded dashboard: concentric segmented arcs, arc gauges (CPU/RAM/GPU/disk/net/temp),
// clock/date arc, weather/status arcs, rotating radial text + tick rings, callouts, radial tab menu, thin bracket panels.
// Original art. Recolours with the mode (page hue filter), static in low-FX.
(function(){
const A=()=>window.pywebview&&window.pywebview.api,NS="http://www.w3.org/2000/svg";
const st=document.createElement("style");st.textContent=`
#vxJ{position:fixed;inset:0;width:100vw;height:100vh;z-index:2;pointer-events:none;opacity:0;transition:opacity .6s;font-family:VexMono,monospace;overflow:visible}
body:not(.aionly) #vxJ.on{opacity:1}
#vxJ .tk{stroke:#5ff3ff;stroke-opacity:.38;stroke-width:1}
#vxJ .tr{fill:none;stroke:#5ff3ff;stroke-opacity:.14;stroke-width:1}
#vxJ .th{fill:none;stroke:#5ff3ff;stroke-opacity:.22;stroke-width:6}
#vxJ .gv{fill:none;stroke:#8ff8ff;stroke-width:6;filter:drop-shadow(0 0 5px #19d8ff);transition:stroke-dasharray 1.2s cubic-bezier(.2,.8,.2,1)}
#vxJ .gv.w{stroke:#ffd166;filter:drop-shadow(0 0 5px #ffb627)}
#vxJ .ln{fill:none;stroke:#5ff3ff;stroke-opacity:.5;stroke-width:1}
#vxJ .ln2{fill:none;stroke:#5ff3ff;stroke-opacity:.25;stroke-width:1;stroke-dasharray:2 5}
#vxJ .seg{fill:none;stroke:#5ff3ff;stroke-opacity:.45;stroke-width:2.2}
#vxJ .seg2{fill:none;stroke:#9ffcff;stroke-opacity:.25;stroke-width:9}
#vxJ text{fill:#bff8ff;letter-spacing:.22em;text-shadow:0 0 6px rgba(95,243,255,.7)}
#vxJ .lab{fill:#7fe9f6;font-size:10.5px;letter-spacing:.3em}
#vxJ .val{fill:#effdff;font-size:13px;letter-spacing:.12em}
#vxJ .clk{font-size:30px;letter-spacing:.32em;fill:#effdff;text-shadow:0 0 14px rgba(95,243,255,.9)}
#vxJ .dt{font-size:12px;letter-spacing:.42em;fill:#8ff5ff}
#vxJ .arcT{font-size:12.5px;letter-spacing:.3em;fill:#bff8ff}
#vxJ .ring{font-size:10px;letter-spacing:.55em;fill:#5ff3ff;fill-opacity:.45}
#vxJ .dot{fill:#bff8ff;filter:drop-shadow(0 0 4px #19d8ff)}
#vxJ .mi{pointer-events:auto;cursor:pointer}
#vxJ .mi path{fill:rgba(95,243,255,.05);stroke:#5ff3ff;stroke-opacity:.55;stroke-width:1;transition:fill .3s}
#vxJ .mi:hover path{fill:rgba(95,243,255,.16)}#vxJ .mi.on path{fill:rgba(95,243,255,.22);stroke-opacity:1;filter:drop-shadow(0 0 6px #19d8ff)}
#vxJ .mi text{font-size:12px;letter-spacing:.4em;fill:#dffcff}
#vxJ .rot{animation:vxJr 60s linear infinite}#vxJ .rot.r2{animation-duration:90s;animation-direction:reverse}#vxJ .rot.r3{animation-duration:24s}#vxJ .rot.r4{animation-duration:140s;animation-direction:reverse}
@keyframes vxJr{to{transform:rotate(360deg)}}
#vxJ .u{opacity:0}
#vxJ.on .u{animation:vxJu 1.1s cubic-bezier(.2,.9,.2,1) both;animation-delay:var(--d,0s)}
@keyframes vxJu{0%{opacity:0;transform:scale(.55) rotate(-40deg)}60%{opacity:1}100%{opacity:1;transform:none}}
#vxJ .blink{animation:vxJb 2.4s steps(2) infinite}@keyframes vxJb{50%{opacity:.25}}
body.lowfx #vxJ *{animation-play-state:paused!important}body.lowfx #vxJ.on .u{animation:none;opacity:1}
/* layout: big central reactor, panels become thin floating brackets */
body:not(.aionly) #radial,body:not(.aionly) #dtabs,body:not(.aionly) #ticker{opacity:0!important;pointer-events:none!important}
body:not(.aionly) .dash.hud .w:not(.hero){background:linear-gradient(180deg,rgba(95,243,255,.035),rgba(95,243,255,.01))!important;border:none!important;box-shadow:none!important;backdrop-filter:none!important;-webkit-backdrop-filter:none!important;border-radius:0!important;transform:none!important}
body:not(.aionly) .dash.hud .w:not(.hero)::before{content:"";position:absolute;inset:0;left:0;right:0;top:0;height:auto;box-shadow:none;pointer-events:none;
 background:linear-gradient(#5ff3ff,#5ff3ff) 0 0/22px 1px,linear-gradient(#5ff3ff,#5ff3ff) 0 0/1px 22px,linear-gradient(#5ff3ff,#5ff3ff) 100% 0/22px 1px,linear-gradient(#5ff3ff,#5ff3ff) 100% 0/1px 22px,
 linear-gradient(#5ff3ff,#5ff3ff) 0 100%/22px 1px,linear-gradient(#5ff3ff,#5ff3ff) 0 100%/1px 22px,linear-gradient(#5ff3ff,#5ff3ff) 100% 100%/22px 1px,linear-gradient(#5ff3ff,#5ff3ff) 100% 100%/1px 22px,
 linear-gradient(90deg,transparent,rgba(95,243,255,.35),transparent) 50% 0/60% 1px;background-repeat:no-repeat;filter:drop-shadow(0 0 4px #19d8ff)}
body:not(.aionly) .dash.hud .w:not(.hero)::after{opacity:.18!important}
body:not(.aionly) .dash.hud .w:not(.hero) input,body:not(.aionly) .dash.hud .w:not(.hero) .btn{background:rgba(95,243,255,.04)!important;border-color:rgba(95,243,255,.25)!important}
body:not(.aionly) #greet,body:not(.aionly) #stateText,body:not(.aionly) #hint,body:not(.aionly) .inputbar{position:relative;z-index:3;left:auto}`;
document.head.appendChild(st);
const sv=document.createElementNS(NS,"svg");sv.id="vxJ";document.body.appendChild(sv);
const P=(cx,cy,r,a)=>[cx+r*Math.cos(a*Math.PI/180),cy+r*Math.sin(a*Math.PI/180)];
const arc=(cx,cy,r,a0,a1,ccw)=>{const [x0,y0]=P(cx,cy,r,a0),[x1,y1]=P(cx,cy,r,a1),big=Math.abs(a1-a0)>180?1:0;return `M${x0.toFixed(1)},${y0.toFixed(1)} A${r},${r} 0 ${big} ${ccw?0:1} ${x1.toFixed(1)},${y1.toFixed(1)}`;};
const GA=[["CPU","cpu",1.20,148,212],["RAM","ram",1.32,148,212],["GPU","gpu",1.44,148,212],["DISK","disk_pct",1.20,-32,32],["NET","net",1.32,-32,32],["TEMP","gpu_temp",1.44,-32,32]];
const TABS=[["home","HOME"],["system","SYSTEM"],["activity","ACTIVITY"],["memory","MEMORY"]];
let G={},geo="",D={};
function build(){const o=document.getElementById("orb"),hero=document.querySelector(".dash.hud .w.hero");if(!o||!hero)return;const r=o.getBoundingClientRect(),h=hero.getBoundingClientRect();if(!r.width||!h.width){sv.classList.remove("on");geo="";return;}
 const W=innerWidth,H=innerHeight,cx=r.left+r.width/2,cy=r.top+r.height/2;
 const u=Math.max(60,Math.min(r.width*0.62,(cy-46)/1.98,(h.width/2)/1.9));const key=[W,H,cx|0,cy|0,u|0].join();if(key==geo)return;geo=key;
 sv.setAttribute("viewBox",`0 0 ${W} ${H}`);const T=(k,d)=>`<g class="u" style="--d:${d}s;transform-origin:${cx}px ${cy}px">${k}</g>`,RO=(c,k)=>`<g class="rot ${c}" style="transform-origin:${cx}px ${cy}px">${k}</g>`;
 let s=`<defs><mask id="vxJm"><rect width="${W}" height="${H}" fill="#fff"/><path d="M${cx},${cy} L${P(cx,cy,u*3,62)} L${P(cx,cy,u*3,118)} Z" fill="#000"/></mask>
  <path id="vxJclk" d="${arc(cx,cy,u*1.36,238,302)}"/><path id="vxJdt" d="${arc(cx,cy,u*1.2,225,315)}"/>
  <path id="vxJwx" d="${arc(cx,cy,u*1.6,172,118,1)}"/><path id="vxJstat" d="${arc(cx,cy,u*1.6,62,8,1)}"/>
  <path id="vxJring" d="${arc(cx,cy,u*1.71,0,359.9)}"/>`;
 TABS.forEach((t,i)=>{const a0=236+i*17.5+1.5,a1=a0+14.5;s+=`<path id="vxJm${i}" d="${arc(cx,cy,u*1.885,a0,a1)}"/>`;});s+=`</defs>`;
 // inner tick ring
 let tk="";for(let i=0;i<180;i++){const a=i*2,L=i%15==0?.09:(i%5==0?.055:.03),[x0,y0]=P(cx,cy,u*1.05,a),[x1,y1]=P(cx,cy,u*(1.05+L),a);tk+=`M${x0.toFixed(1)},${y0.toFixed(1)}L${x1.toFixed(1)},${y1.toFixed(1)}`;}
 s+=T(RO("r2",`<path class="tk" d="${tk}"/><circle class="tr" cx="${cx}" cy="${cy}" r="${u*1.05}"/>`),.05);
 // gauge arcs
 let g="";GA.forEach(([n,k,rr,a0,a1],i)=>{const left=a0>90,R=u*rr;g+=`<path class="th" d="${arc(cx,cy,R,a0,a1)}"/><path class="gv" id="vxJg${i}" pathLength="100" stroke-dasharray="0 100" d="${left?arc(cx,cy,R,a1,a0,1):arc(cx,cy,R,a0,a1)}"/>`;
  const k3=i%3,[lx,ly]=P(cx,cy,R,left?a1+4+k3*6:a0-4-k3*6);g+=`<text class="lab" x="${(left?lx-8:lx+8).toFixed(1)}" y="${(ly+4).toFixed(1)}" text-anchor="${left?"end":"start"}">${n} <tspan class="val" id="vxJv${i}">--</tspan></text>`;});
 s+=T(g,.15);
 // clock / date arcs
 s+=T(`<text class="clk"><textPath href="#vxJclk" startOffset="50%" text-anchor="middle" id="vxJc">--:--:--</textPath></text><text class="dt"><textPath href="#vxJdt" startOffset="50%" text-anchor="middle" id="vxJd">--</textPath></text>`,.25);
 // weather + status arcs (lower sides, kept clear of the greeting)
 s+=T(`<path class="tr" d="${arc(cx,cy,u*1.66,172,118,1)}"/><path class="tr" d="${arc(cx,cy,u*1.66,62,8,1)}"/><text class="arcT"><textPath href="#vxJwx" startOffset="50%" text-anchor="middle" id="vxJw">WEATHER --</textPath></text><text class="arcT"><textPath href="#vxJstat" startOffset="50%" text-anchor="middle" id="vxJs">STATUS --</textPath></text>`,.35);
 // rotating radial text + segmented rings (masked clear of the greeting)
 let seg="";for(let i=0;i<36;i++){const a0=i*10+1,a1=a0+(i%3==0?7:4);seg+=`<path class="seg" d="${arc(cx,cy,u*1.78,a0,a1)}"/>`;}
 let seg2="";[[20,48],[110,128],[200,236],[290,302]].forEach(([a,b])=>seg2+=`<path class="seg2" d="${arc(cx,cy,u*1.5,a,b)}"/>`);
 const ringTxt=Array(6).fill("VEX CORE SYSTEMS // HOLO INTERFACE // SIGNAL LOCK // ").join("");
 s+=`<g mask="url(#vxJm)">`+T(RO("",`<text class="ring"><textPath href="#vxJring">${ringTxt}</textPath></text>`),.45)+T(RO("r4",seg),.5)+T(RO("r3",seg2),.55)+T(`<circle class="tr" cx="${cx}" cy="${cy}" r="${u*1.95}"/><circle class="ln2" cx="${cx}" cy="${cy}" r="${u*1.56}"/>`,.6)+`</g>`;
 // degree markers
 let dg="";[0,90,180,270].forEach(a=>{if(a==90)return;const [x,y]=P(cx,cy,u*2.02,a);dg+=`<text class="lab" x="${x.toFixed(1)}" y="${(y+4).toFixed(1)}" text-anchor="middle" style="font-size:9px">${String(a).padStart(3,"0")}</text>`;});s+=T(dg,.65);
 // callouts: angled lines from the core to small data labels
 let co="";[[228,-1,"CORE // ONLINE","vxJk0"],[312,1,"THERMAL --","vxJk1"],[150,-1,"UPLINK --","vxJk2"],[30,1,"MODE --","vxJk3"]].forEach(([a,dir,t,id])=>{const [x0,y0]=P(cx,cy,u*1.0,a),[x1,y1]=P(cx,cy,u*1.62,a),x2=cx+dir*u*2.06;
  co+=`<circle class="dot" cx="${x0.toFixed(1)}" cy="${y0.toFixed(1)}" r="2.4"/><path class="ln" d="M${x0.toFixed(1)},${y0.toFixed(1)}L${x1.toFixed(1)},${y1.toFixed(1)}L${x2.toFixed(1)},${y1.toFixed(1)}"/><circle class="dot blink" cx="${x2.toFixed(1)}" cy="${y1.toFixed(1)}" r="3"/>
  <text class="lab" id="${id}" x="${(x2-dir*4).toFixed(1)}" y="${(y1-8).toFixed(1)}" text-anchor="${dir>0?"end":"start"}">${t}</text>`;});s+=T(co,.75);
 // radial tab menu (top arc)
 let mn="";TABS.forEach((t,i)=>{const a0=236+i*17.5+1.5,a1=a0+14.5,R1=u*1.83,R2=u*1.95,[ax,ay]=P(cx,cy,R1,a0),[bx,by]=P(cx,cy,R2,a1);
  mn+=`<g class="mi" data-t="${t[0]}"><path d="${arc(cx,cy,R2,a0,a1)} L${P(cx,cy,R1,a1).map(v=>v.toFixed(1))} ${arc(cx,cy,R1,a1,a0,1).replace(/^M[^A]+/,"")} Z"/><text dy="4"><textPath href="#vxJm${i}" startOffset="50%" text-anchor="middle">${t[1]}</textPath></text></g>`;});
 s+=T(mn,.85);
 sv.innerHTML=s;sv.querySelectorAll(".mi").forEach(m=>m.onclick=()=>{const b=document.querySelector(`#dtabs button[data-t="${m.dataset.t}"]`);b&&b.click();});
 fill();sv.classList.remove("on");void sv.getBBox;requestAnimationFrame(()=>sv.classList.add("on"));}
const $=id=>document.getElementById(id),txt=(id,v)=>{const e=$(id);if(e&&e.textContent!==v)e.textContent=v;};
function fill(){const s=D.st||{},w=D.wx||{};const net=s.net_down!=null?Math.min(100,Math.log10(1+parseFloat(s.net_down)||0)*33):0;
 const V={cpu:s.cpu,ram:s.ram,gpu:s.gpu,disk_pct:s.disk_pct,net:net,gpu_temp:s.gpu_temp};
 GA.forEach(([n,k],i)=>{const v=V[k];const e=$("vxJg"+i);if(e){e.setAttribute("stroke-dasharray",`${Math.max(0,Math.min(100,+v||0)).toFixed(1)} 100`);e.classList.toggle("w",(k=="gpu_temp"&&v>83)||(k!="net"&&k!="gpu_temp"&&v>90));}
  txt("vxJv"+i,v==null?"--":k=="net"?(s.net_down!=null?String(s.net_down).toUpperCase():"--"):k=="gpu_temp"?Math.round(v)+"°C":Math.round(v)+"%");});
 txt("vxJw",w.temp!=null?`${Math.round(w.temp)}°${(w.unit||"F").replace("°","")} ${String(w.desc||"").toUpperCase()} · ${String(w.place||"").split(",")[0].toUpperCase()}`:"WEATHER // OFFLINE");
 txt("vxJs",`AI LOCAL · CPU ${s.cpu??"--"}% · LINK OK`);txt("vxJk1","THERMAL "+(s.gpu_temp!=null?Math.round(s.gpu_temp)+"°C":"--"));txt("vxJk2","UPLINK ↓"+(s.net_down??"--"));txt("vxJk3","MODE "+String(D.mode||"blue").toUpperCase());
 const tab=(document.querySelector(".dash.hud")||{}).dataset;sv.querySelectorAll(".mi").forEach(m=>m.classList.toggle("on",tab&&m.dataset.t==tab.tab));}
function clock(){const d=new Date();txt("vxJc",d.toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:false}));
 txt("vxJd",d.toLocaleDateString([],{weekday:"long",day:"2-digit",month:"short",year:"numeric"}).toUpperCase().replace(/,/g,""));}
async function poll(){if(document.body.classList.contains("aionly"))return;try{D=await A().jhud();fill();}catch(e){}}
let wasAi=true;setInterval(()=>{const ai=document.body.classList.contains("aionly");if(ai){wasAi=true;sv.classList.remove("on");return;}if(wasAi){wasAi=false;geo="";setTimeout(()=>{build();poll();},450);}else build();clock();},1000);
setInterval(poll,2500);addEventListener("resize",()=>{geo="";});
})();
