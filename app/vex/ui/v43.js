/* 4.3: Settings > Permissions and Settings > Help & updates (crash report, update check). */
(function(){
const A=()=>window.pywebview&&window.pywebview.api,E=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const kb=n=>n>1048576?(n/1048576).toFixed(1)+" MB":n>1024?Math.round(n/1024)+" KB":n+" B";
let U=null;
window.v43Body=async function(tab){
 if(tab=="perms"){let p={perms:[],asks:[],never:[]};try{p=await A().v43_perms();}catch(e){}
  return `<div class="vx-sub" style="margin-bottom:12px">EVERY SWITCH THE ASSISTANT HAS · SAFE CHOICES ARE THE DEFAULT · CHANGES APPLY RIGHT AWAY</div>
  <div class="v43perm">${p.perms.map(x=>`<div class="vx-row v43p"><span><b>${E(x.label)}</b><small>${E(x.desc)}</small></span><span class="vx-tog ${x.on?"on":""}" data-perm="${E(x.k)}" role="switch" aria-checked="${x.on}"><i></i></span></div>`).join("")}</div>
  ${p.perms.some(x=>x.k=="phone_enabled"&&x.on)&&!p.ntfy?`<div class="vx-sub" style="color:#ffc46b;margin-top:6px">PHONE IS ON BUT NO NTFY TOPIC IS SET: ADD YOUR OWN TOPIC IN SETTINGS › PHONE</div>`:""}
  <div class="v4grid2" style="margin-top:16px"><div class="v4card vx-glass"><div class="vx-k">ALWAYS ASKS “SHALL I PROCEED?” FIRST</div>${p.asks.map(s=>`<div class="vx-row" style="font-size:13px"><span>🔒 ${E(s)}</span></div>`).join("")}<div class="vx-sub" style="margin-top:8px">THESE CAN'T BE TURNED OFF. SAY “NO” OR “CANCEL” TO STOP.</div></div>
  <div class="v4card vx-glass"><div class="vx-k">NEVER</div>${p.never.map(s=>`<div class="vx-row" style="font-size:13px"><span>✓ ${E(s)}</span></div>`).join("")}</div></div>`;}
 if(tab=="help"){let c={exists:false,reports:0,size:0,path:""};try{c=await A().v43_crash_info();}catch(e){}
  const u=U||{};
  return `<div class="v4grid2"><div class="v4card vx-glass"><div class="vx-k">CRASH REPORTS (KEPT ON THIS PC ONLY)</div>
   <p style="font:13px/1.7 var(--vx-f-ui);color:var(--vx-ink);margin:8px 0">${c.exists?`${c.reports} report${c.reports==1?"":"s"} saved (${kb(c.size)}).`:"No crashes recorded."} If something goes wrong, open or copy the report and share it with whoever is helping you. Your Windows user name and folders are blanked out. Nothing is ever sent automatically.</p>
   <button class="vx-btn p" id="v43co">Open crash report</button> <button class="vx-btn" id="v43cc">Copy to clipboard</button> <span class="vx-sub" id="v43cm"></span>
   <div class="vx-sub" style="margin-top:8px;word-break:break-all">${E(c.path||"")}</div></div>
   <div class="v4card vx-glass"><div class="vx-k">UPDATES</div>
   <p style="font:13px/1.7 var(--vx-f-ui);color:var(--vx-ink);margin:8px 0" id="v43um">${E(u.msg||"Check whether a newer version is out. This only downloads a tiny public version file; nothing about you is sent, and nothing installs by itself.")}</p>
   ${u.notes?`<p class="vx-sub" style="text-transform:none;letter-spacing:0">${E(u.notes)}</p>`:""}
   <button class="vx-btn p" id="v43uc">Check for updates</button> ${u.newer&&u.url?`<button class="vx-btn" id="v43ug">Open download page</button>`:""}</div></div>
   <div class="vx-sub" style="margin-top:14px">SAY “WHAT CAN YOU DO” FOR A TOUR · HOLD CTRL+ALT+V TO TALK · CTRL+ALT+X STOPS EVERYTHING</div>
   <div style="margin-top:10px"><button class="vx-btn" id="v43wz">Run setup again</button></div>`;}
 return "";};
window.v43Bind=function(tab,page,reopen){
 page.querySelectorAll("[data-perm]").forEach(t=>t.onclick=async()=>{const on=!t.classList.contains("on");t.classList.toggle("on",on);try{await A().v43_perm_set(t.dataset.perm,on);}catch(e){}reopen("perms");});
 const g=id=>page.querySelector("#"+id),m=g("v43cm");
 if(g("v43co"))g("v43co").onclick=async()=>{try{await A().v43_crash_open();}catch(e){}};
 if(g("v43cc"))g("v43cc").onclick=async()=>{let r={};try{r=await A().v43_crash_copy();}catch(e){}if(m)m.textContent=r.ok?"COPIED":"COULDN'T COPY";};
 if(g("v43uc"))g("v43uc").onclick=async()=>{const um=g("v43um");if(um)um.textContent="Checking…";try{U=await A().v43_update_check();}catch(e){U={msg:"Couldn't check."};}reopen("help");};
 if(g("v43ug"))g("v43ug").onclick=()=>{try{A().v43_open_url(U.url)}catch(e){}};
 if(g("v43wz"))g("v43wz").onclick=()=>{try{window.vexPage("wizard")}catch(e){}};};
const st=document.createElement("style");st.textContent=`.v43p{align-items:center;gap:18px;padding:10px 4px}.v43p span:first-child{display:flex;flex-direction:column;gap:3px;font-size:14px}.v43p small{font:12px/1.5 var(--vx-f-ui,sans-serif);color:var(--vx-dim,#9fb6c8);max-width:70ch}.v43p .vx-tog{flex:none}`;
document.head.appendChild(st);
})();
