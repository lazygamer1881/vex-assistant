// Vex 3.2: Connections tab, Displays + Look settings, live look, captions, systems strip.
(function(){
const A=()=>window.pywebview&&window.pywebview.api,$=q=>document.querySelector(q),E=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const st=document.createElement("style");st.textContent=`
#connections .scroll{overflow:auto;width:100%}.cx{padding:26px 34px;max-width:1500px}
.cxh{display:flex;align-items:baseline;gap:18px}.cxh h2{font:300 22px "VexMono",monospace;letter-spacing:.4em;color:#bff8ff;margin:0}
#cxVault{font:11px "VexMono",monospace;letter-spacing:.2em;color:#5ff3ffaa}.cxp{color:#8fb3c0;max-width:900px;font-size:13px}
.cxrow{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:8px 0 14px}.cxrow label{font-size:12px;color:#8fb3c0}
.cxgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px;margin-bottom:22px}
.cxc{position:relative;padding:14px 16px;background:linear-gradient(160deg,rgba(6,22,34,.75),rgba(2,8,16,.9));border:1px solid rgba(95,243,255,.18);
 clip-path:polygon(0 0,calc(100% - 14px) 0,100% 14px,100% 100%,14px 100%,0 calc(100% - 14px));transition:border-color .3s}
.cxc:hover{border-color:rgba(95,243,255,.45)}.cxc h4{margin:0 0 6px;font:400 13px "VexMono",monospace;letter-spacing:.18em;color:#d6fbff;display:flex;justify-content:space-between}
.cxc .on{color:#4ade80}.cxc .off{color:#64748b}.cxc small{display:block;color:#7f9aa6;margin:4px 0 8px;font-size:11px}
.cxc input{width:100%;margin:3px 0;background:#020a12;border:1px solid #19d8ff33;color:#cdefff;padding:6px 8px;font:12px "VexMono",monospace}
.cxc .bt{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}.cxc .msg{font-size:11px;color:#9fdcef;margin-top:6px;min-height:14px}
.cxc ul{margin:4px 0 6px 16px;padding:0;color:#a7c6d1;font-size:12px}
#vxModal{position:fixed;inset:0;z-index:10000;background:rgba(0,3,10,.78);display:none;place-items:center}#vxModal.on{display:grid}
#vxModal .bx{max-width:520px;padding:22px 26px;background:#03111b;border:1px solid #5ff3ff66;box-shadow:0 0 40px #19d8ff22;color:#cdefff}
#vxModal h3{font:400 15px "VexMono",monospace;letter-spacing:.2em;margin:0 0 10px}
.dispm{display:flex;gap:14px;align-items:flex-end;margin:8px 0}.dispm div{border:1px solid #19d8ff55;display:grid;place-items:center;font:11px "VexMono",monospace;color:#9fefff;cursor:pointer;background:#020a12}
.dispm div.main{border-color:#5ff3ff;box-shadow:0 0 12px #19d8ff55;color:#fff}
#vxCap{position:fixed;left:50%;bottom:15%;transform:translateX(-50%);max-width:min(70vw,1100px);text-align:center;font:300 15px "VexMono",monospace;letter-spacing:.08em;color:#bff8ffd0;z-index:58;pointer-events:none;text-shadow:0 0 8px #19d8ff55;opacity:0;transition:opacity .6s}
#vxCap.on{opacity:1}#vxCap i{display:inline-block;width:.55em;height:1em;background:#5ff3ff;vertical-align:-2px;margin-left:2px;animation:vxBl 1s steps(2) infinite}
@keyframes vxBl{50%{opacity:0}}
#vxSys{position:fixed;top:18px;left:50%;transform:translateX(-50%);z-index:58;font:10px "VexMono",monospace;letter-spacing:.32em;color:#5ff3ff88;display:none;white-space:nowrap}
body.aionly #vxSys{display:block}#vxSys b{color:#bff8ff;font-weight:400}#vxSys .dot{display:inline-block;width:5px;height:5px;border-radius:50%;background:#4ade80;margin:0 6px 1px;box-shadow:0 0 6px #4ade80}
#reticle,#retT{display:none!important}
#greet{font-size:calc(clamp(20px,1.9vw,48px) * var(--vxText,1))!important}#stateText{font-size:calc(1.05rem * var(--vxText,1))!important}
.dash.hud .w{font-size:calc(1em * var(--vxText,1))}
#vxScanl{opacity:var(--vxScan,1)}`;document.head.appendChild(st);
const modal=document.createElement("div");modal.id="vxModal";modal.innerHTML='<div class="bx"><h3 id="vmT"></h3><div id="vmB"></div><div class="bt" style="display:flex;gap:10px;margin-top:14px"><button class="btn p" id="vmY">Allow &amp; continue</button><button class="btn" id="vmN">Cancel</button></div></div>';document.body.appendChild(modal);
function ask(t,b){return new Promise(r=>{$("#vmT").textContent=t;$("#vmB").innerHTML=b;modal.classList.add("on");$("#vmY").onclick=()=>{modal.classList.remove("on");r(true)};$("#vmN").onclick=()=>{modal.classList.remove("on");r(false)};});}
// ---------- live look
let lookSeq=-1;window.vexApplyLook=L=>{if(!L)return;window.__look=L;const r=document.documentElement;const f=[];if(L.hue)f.push(`hue-rotate(${L.hue}deg)`);if(L.sat!=1)f.push(`saturate(${L.sat})`);if(L.dark)f.push(`brightness(${(1-L.dark).toFixed(2)})`);
 r.style.filter=f.join(" ");r.style.setProperty("--vxText",L.text||1);r.style.setProperty("--vxScan",L.scan==null?1:L.scan);};
// ---------- captions (typewriter of what Vex says)
const cap=document.createElement("div");cap.id="vxCap";document.body.appendChild(cap);let capT=0;
function caption(t){clearTimeout(capT);let i=0;t=String(t||"").slice(0,220);cap.classList.add("on");const step=()=>{cap.innerHTML=E(t.slice(0,i))+"<i></i>";if(i++<t.length)capT=setTimeout(step,18);else capT=setTimeout(()=>cap.classList.remove("on"),Math.max(3500,t.length*60));};step();}
if(window.vexOn){const o=window.vexOn;window.vexOn=(ev,d)=>{try{if(ev=="transcript"&&d&&d.who=="vex"&&document.body.classList.contains("aionly"))caption(d.text);}catch(e){}return o(ev,d);};}
// ---------- systems strip (AI-only)
const sys=document.createElement("div");sys.id="vxSys";document.body.appendChild(sys);
async function strip(){const a=A();if(!a||!a.conn_list)return;try{const c=await a.conn_list(),ac=await a.acct_list(),d=await a.disp_info(),h=await a.hand_state();
 const n=c.agents.filter(x=>x.configured&&x.id!="local").length,na=ac.filter(x=>x.connected).length;
 sys.innerHTML=`<span class="dot"></span><b>${E((h.name||"VEX").toUpperCase())}</b> ONLINE &nbsp;·&nbsp; BRAIN <b>LOCAL</b>${n?" +"+n:""} &nbsp;·&nbsp; LINKS <b>${na}</b> &nbsp;·&nbsp; CAM <b>${h.enabled?"ON":"OFF"}</b> &nbsp;·&nbsp; DISPLAYS <b>${d.monitors.length}</b>${d.mode=="span"?" SPAN":""}`;}catch(e){}}
setInterval(strip,5000);setTimeout(strip,2500);
// poll for look + page requests
async function poll(){try{const a=A();if(a&&a.hand_state){const h=await a.hand_state();if(h.look_seq!==lookSeq){lookSeq=h.look_seq;vexApplyLook(h.look);}
 if(h.page){a.page_done();if(window.vexView)vexView("full","voice");setTimeout(()=>window.goPage&&goPage(h.page),450);if(h.page=="connections")loadCx();}}}catch(e){}setTimeout(poll,1200);}
setTimeout(poll,1500);
// ---------- Connections tab
async function loadCx(){const a=A();if(!a||!a.conn_list)return;const c=await a.conn_list();
 $("#cxVault").textContent=c.vault_ok?"◆ DPAPI VAULT ONLINE":"◆ VAULT UNAVAILABLE";
 const opts=c.agents.filter(x=>x.id!="webhook").map(x=>`<option value="${x.id}">${E(x.label)}</option>`).join("");
 $("#cxBrain").innerHTML=`<option value="auto">Auto (local unless a key is set)</option>`+opts;$("#cxBrain").value=c.brain;
 $("#cxHard").innerHTML=`<option value="">Same brain</option>`+opts;$("#cxHard").value=c.hard||"";
 $("#cxAgents").innerHTML=c.agents.map(x=>`<div class="cxc" data-id="${x.id}"><h4>${E(x.label)}<span class="${x.configured?"on":"off"}">${x.configured?"● CONNECTED":"○ NOT SET"}</span></h4>
  ${x.id=="local"?`<small>Free, private, on this PC. Model: ${E(x.model)}</small>`:""}
  ${x.needs_key?`<small>Optional. Paste your own API key${x.key_set?" (one is saved - paste a new one to replace)":""}.</small><input type="password" class="k" placeholder="${x.key_set?"•••••••• saved":"API key"}"><input class="m" value="${E(x.model)}" placeholder="model">`:""}
  ${x.id=="lmstudio"?`<small>Uses LM Studio's local server (free, on this PC).</small><input class="b" value="${E(x.base)}"><input class="m" value="${E(x.model)}" placeholder="model">`:""}
  ${x.id=="webhook"?`<small>Any agent with an HTTP endpoint (n8n, a custom MCP bridge, your own server). Vex POSTs {"input": "..."} and reads "reply".</small><input class="u" value="${E(x.url)}" placeholder="https://..."><input type="password" class="k" placeholder="optional bearer token">`:""}
  ${x.id!="local"?`<small>Say: "ask ${E(x.id=="openai"?"chatgpt":x.id=="anthropic"?"claude":x.id=="webhook"?"my agent":x.id)} ..."</small>`:""}
  <div class="bt">${x.id!="local"?'<button class="btn p sv">Save</button>':""}<button class="btn ts">Test</button>${x.id!="local"&&x.configured?'<button class="btn cl">Disconnect</button>':""}</div><div class="msg"></div></div>`).join("");
 document.querySelectorAll("#cxAgents .cxc").forEach(el=>{const id=el.dataset.id,msg=el.querySelector(".msg"),v=q=>{const i=el.querySelector(q);return i?i.value:""};
  const sv=el.querySelector(".sv");if(sv)sv.onclick=async()=>{const r=await a.conn_save(id,{key:v(".k"),model:v(".m"),base:v(".b"),url:v(".u"),enabled:true});msg.textContent=r.msg;setTimeout(loadCx,900);};
  const cl=el.querySelector(".cl");if(cl)cl.onclick=async()=>{const r=await a.conn_save(id,{clear:true});msg.textContent=r.msg;setTimeout(loadCx,900);};
  el.querySelector(".ts").onclick=async()=>{msg.textContent="Testing…";const r=await a.conn_test(id);msg.textContent=(r.ok?"✓ ":"✕ ")+r.msg;};});
 $("#cxRoute").onclick=async()=>{await a.conn_route($("#cxBrain").value,$("#cxHard").value);$("#cxRouteMsg").textContent="Saved ✓";setTimeout(()=>$("#cxRouteMsg").textContent="",3000);};
 const ac=await a.acct_list();
 $("#cxAccts").innerHTML=ac.map(x=>`<div class="cxc" data-id="${x.id}"><h4>${E(x.label)}<span class="${x.connected?"on":"off"}">${x.connected?"● CONNECTED":"○ DISCONNECTED"}</span></h4>
  <small>Vex will be able to:</small><ul>${x.scopes.map(s=>`<li>${E(s)}</li>`).join("")}</ul><small>${E(x.setup)}</small>
  ${x.webhook?`<input type="password" class="w" placeholder="${x.connected?"•••••••• saved":"https://discord.com/api/webhooks/..."}">`:`<input class="ci" value="${E(x.client_id)}" placeholder="Client ID (from your own developer app)">${x.id!="spotify"?'<input type="password" class="cs" placeholder="Client secret (Google desktop client)">':""}`}
  <div class="bt">${x.connected?'<button class="btn dc">Disconnect</button>':`<button class="btn p cn">${x.webhook?"Save":"Connect…"}</button>`}</div><div class="msg"></div></div>`).join("");
 document.querySelectorAll("#cxAccts .cxc").forEach(el=>{const id=el.dataset.id,msg=el.querySelector(".msg"),x=ac.find(z=>z.id==id),v=q=>{const i=el.querySelector(q);return i?i.value:""};
  const dc=el.querySelector(".dc");if(dc)dc.onclick=async()=>{const r=await a.acct_disconnect(id);msg.textContent=r.msg;setTimeout(loadCx,800);};
  const cn=el.querySelector(".cn");if(cn)cn.onclick=async()=>{
   if(x.webhook){if(!await ask("CONNECT DISCORD WEBHOOK",`<p>Vex will be allowed to post to that one channel. It will always say what it's posting and ask <b>"Shall I proceed?"</b> first.</p>`))return;const r=await a.acct_discord(v(".w"));msg.textContent=r.msg;setTimeout(loadCx,800);return;}
   if(!await ask("CONNECT "+x.label.toUpperCase(),`<p>Your browser will open ${E(x.label.split(" ")[0])}'s own sign-in page. You sign in there; Vex never sees your password.</p><p>Vex will be able to:</p><ul>${x.scopes.map(s=>`<li>${E(s)}</li>`).join("")}</ul><p>You can disconnect any time, which deletes the token.</p>`))return;
   const r=await a.acct_connect(id,v(".ci"),v(".cs"));msg.textContent=r.msg;const t=setInterval(async()=>{const l=await a.acct_list();if((l.find(z=>z.id==id)||{}).connected){clearInterval(t);loadCx();}},3000);setTimeout(()=>clearInterval(t),300000);};});}
window.loadCx=loadCx;
document.addEventListener("click",e=>{const n=e.target.closest&&e.target.closest('.nb[data-p="connections"]');if(n)setTimeout(loadCx,50);if(e.target.closest&&e.target.closest('.nb[data-p="settings"]'))setTimeout(loadSet32,300);});
// ---------- Displays + Look in Settings
async function loadSet32(){const a=A();if(!a||!a.disp_info)return;const d=await a.disp_info();const sc=0.045;
 $("#dispBox").innerHTML=`<div class="dispm">${d.monitors.map(m=>`<div data-n="${m.n}" class="${m.n==d.main?"main":""}" style="width:${m.w*sc}px;height:${m.h*sc}px">${m.n}<br>${m.w}×${m.h}${m.n==d.main?"<br>ORB":d.mode=="span"?"<br>HUD":d.mode=="ondemand"?"<br>ON DEMAND":""}</div>`).join("")}</div>
  <div class="cxrow"><button class="btn ${d.mode=="ondemand"?"p":""}" id="dmO">Other monitor on demand</button><button class="btn ${d.mode=="single"?"p":""}" id="dmS">Single monitor</button><button class="btn ${d.mode=="span"?"p":""}" id="dmA">Always-on HUD</button>
  <button class="btn ${d.style!="terminal"?"p":""}" id="dmK">Compact HUD</button><button class="btn ${d.style=="terminal"?"p":""}" id="dmT">Terminal HUD</button>
  <label>HUD click-through</label><div class="toggle ${d.clickthrough?"on":""}" id="dmC"></div><span id="dmMsg" style="font-size:12px;color:#9fdcef"></span></div>`;
 document.querySelectorAll(".dispm div").forEach(x=>x.onclick=async()=>{$("#dmMsg").textContent=await a.disp_move(x.dataset.n);setTimeout(loadSet32,1500);});
 $("#dmO").onclick=async()=>{$("#dmMsg").textContent=await a.disp_mode("ondemand");setTimeout(loadSet32,800);};
 $("#dmS").onclick=async()=>{$("#dmMsg").textContent=await a.disp_mode("single");setTimeout(loadSet32,800);};$("#dmA").onclick=async()=>{$("#dmMsg").textContent=await a.disp_mode("span");setTimeout(loadSet32,800);};
 $("#dmK").onclick=async()=>{$("#dmMsg").textContent=await a.disp_style("compact");setTimeout(loadSet32,800);};$("#dmT").onclick=async()=>{$("#dmMsg").textContent=await a.disp_style("terminal");setTimeout(loadSet32,800);};
 $("#dmC").onclick=async e=>{e.target.classList.toggle("on");await a.disp_clickthrough(e.target.classList.contains("on"));};
 const L=await a.look_get();$("#lookBox").innerHTML=`<div class="cxrow">${L.presets.map(p=>`<button class="btn ${L.look.preset==p?"p":""}" data-p="${E(p)}">${E(p)}</button>`).join("")}<button class="btn" id="lkU">Undo</button><button class="btn" id="lkR">Reset look</button><span id="lkM" style="font-size:12px;color:#9fdcef"></span></div>`;
 document.querySelectorAll("#lookBox [data-p]").forEach(b=>b.onclick=async()=>{$("#lkM").textContent=await a.look_preset(b.dataset.p);setTimeout(loadSet32,600);});
 $("#lkU").onclick=async()=>{$("#lkM").textContent=await a.look_undo();setTimeout(loadSet32,600);};$("#lkR").onclick=async()=>{$("#lkM").textContent=await a.look_reset();setTimeout(loadSet32,600);};}
window.loadSet32=loadSet32;
})();
