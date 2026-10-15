// Vex 3.0 hand control: webcam + MediaPipe HandLandmarker, fully local (bundled in ui/lib/mediapipe).
// The camera only runs while Hand control is on; frames stay in memory and are never saved or sent.
import {FilesetResolver, HandLandmarker} from "./lib/mediapipe/vision_bundle.mjs";
const api=()=>window.pywebview&&window.pywebview.api, LOG=m=>{try{window.vexUiLog&&vexUiLog("hand: "+m)}catch(e){}};
const css=document.createElement("style");css.textContent=`
body.aionly nav,body.aionly header,body.aionly #dtabs,body.aionly #radial,body.aionly #rain,body.aionly #links,body.aionly #frame,body.aionly #interf,body.aionly #amb,
body.aionly .dash.hud>.w:not(.hero),body.aionly .hero .inputbar,body.aionly .hero .readout,body.aionly #ticker,body.aionly #fxBadge{opacity:0!important;pointer-events:none!important;visibility:hidden!important}
body.aionly #home,body.aionly main,body.aionly #app,body.aionly #home .dash.hud{perspective:none!important;transform:none!important;filter:none!important;contain:none!important;backdrop-filter:none!important}
body.aionly .dash.hud{grid-template-columns:1fr!important;grid-template-rows:1fr!important;grid-template-areas:"hero"!important}
body.aionly .dash.hud>.w.hero{display:flex!important;position:fixed!important;inset:0!important;width:100vw!important;height:100vh!important;z-index:5;flex-direction:column!important;align-items:center!important;justify-content:center!important;transform:none!important;grid-area:hero!important;background:none!important;border-color:transparent!important;box-shadow:none!important;backdrop-filter:none!important}
body.aionly .dash.hud>.w.hero::before,body.aionly .dash.hud>.w.hero::after{opacity:0!important}
body.aionly #gl{opacity:.55;transition:opacity .8s}
nav,header,#dtabs,.dash.hud>.w,#rain,#frame{transition:opacity .5s,visibility .5s}
body.unfolding nav{animation:vxSlideL .7s cubic-bezier(.2,.9,.2,1) both}
body.unfolding header,body.unfolding #dtabs{animation:vxSlideT .7s .1s cubic-bezier(.2,.9,.2,1) both}
body.unfolding .dash.hud>.w:not(.hero){animation:vxUnfold .9s cubic-bezier(.2,.9,.2,1) both}
body.unfolding .dash.hud>.w:nth-child(2){animation-delay:.12s}body.unfolding .dash.hud>.w:nth-child(3){animation-delay:.2s}body.unfolding .dash.hud>.w:nth-child(4){animation-delay:.28s}
body.unfolding .dash.hud>.w:nth-child(5){animation-delay:.36s}body.unfolding .dash.hud>.w:nth-child(n+6){animation-delay:.44s}
body.folding .dash.hud>.w:not(.hero),body.folding nav,body.folding header,body.folding #dtabs{animation:vxFold .45s ease-in both}
@keyframes vxUnfold{0%{opacity:0;transform:perspective(900px) scale(.35) rotateY(35deg);filter:blur(10px) brightness(3);clip-path:inset(48% 0 48% 0)}
 55%{opacity:1;clip-path:inset(0 0 0 0);filter:blur(0) brightness(1.8)}100%{opacity:1;transform:none;filter:none;clip-path:inset(0 0 0 0)}}
@keyframes vxFold{to{opacity:0;transform:scale(.4);filter:blur(8px) brightness(2.5);clip-path:inset(50% 0 50% 0)}}
@keyframes vxSlideL{from{opacity:0;transform:translateX(-120%)}to{opacity:1;transform:none}}
@keyframes vxSlideT{from{opacity:0;transform:translateY(-140%)}to{opacity:1;transform:none}}
#vxScan{position:fixed;inset:0;pointer-events:none;z-index:9990;display:none;background:radial-gradient(circle at 50% 50%,transparent 0,transparent var(--r),#5ff3ff55 calc(var(--r) + 2px),transparent calc(var(--r) + 40px))}
body.unfolding #vxScan{display:block;animation:vxRing .9s ease-out both}
@property --r{syntax:"<length>";inherits:false;initial-value:0px}
@keyframes vxRing{from{--r:0px}to{--r:2200px}}
#vxHint{position:fixed;left:50%;bottom:4%;transform:translateX(-50%);z-index:60;font:11px "VexMono",monospace;letter-spacing:.35em;color:#7fefffaa;display:none}
body.aionly #vxHint{display:block}
#hdot{position:fixed;left:16px;bottom:16px;width:7px;height:7px;border-radius:50%;background:#0b3a46;box-shadow:0 0 0 1px #19d8ff55;z-index:9998;display:none;pointer-events:none;transition:background .2s,box-shadow .2s}
#hdot.on{background:#5ff3ff;box-shadow:0 0 8px #19d8ff}
body.aionly #reticle,body.aionly #retT{display:none!important}
html,body{background:#01030a!important}
#bgfx{opacity:.35!important}#amb{opacity:.4}
#orb{opacity:.75}
#greet{text-shadow:0 0 10px rgba(34,229,255,.35)!important}
.dash.hud>.w:not(.hero){background:linear-gradient(160deg,rgba(6,22,34,.72),rgba(2,8,16,.82))!important;border:1px solid rgba(95,243,255,.22)!important;
 box-shadow:0 30px 60px -20px rgba(0,0,0,.9),0 0 0 1px rgba(95,243,255,.05) inset,0 0 24px rgba(25,216,255,.06)!important;
 transform:perspective(1400px) rotateY(var(--ry,0deg)) rotateX(var(--rx,0deg)) translateZ(var(--tz,0px));transform-style:preserve-3d;transition:transform .6s cubic-bezier(.2,.9,.2,1),opacity .5s,visibility .5s}
#vxScanl{position:fixed;inset:0;pointer-events:none;z-index:9989;background:repeating-linear-gradient(0deg,rgba(120,240,255,.035) 0 1px,transparent 1px 3px);mix-blend-mode:screen}
#vxShim{position:fixed;inset:0;pointer-events:none;z-index:9988;background:linear-gradient(105deg,transparent 40%,rgba(127,239,255,.045) 48%,rgba(255,255,255,.06) 50%,rgba(127,239,255,.045) 52%,transparent 60%);background-size:300% 100%;animation:vxShim 9s linear infinite;mix-blend-mode:screen}
@keyframes vxShim{from{background-position:150% 0}to{background-position:-150% 0}}
body.lowfx #vxShim{display:none}`;
const sc0=document.createElement("div");sc0.id="vxScan";document.body.appendChild(sc0);
const hint=document.createElement("div");hint.id="vxHint";hint.textContent="SAY \u201COPEN EVERYTHING\u201D OR OPEN YOUR HAND";document.body.appendChild(hint);
let VIEW="ai",viewSeq=-1;
function setView(m,src){m=m=="full"?"full":"ai";if(m==VIEW)return;VIEW=m;const b=document.body;LOG("view -> "+m+" ("+(src||"")+")");
 const a=api();a&&a.set_view&&a.set_view(m);
 if(m=="full"){b.classList.remove("folding");b.classList.remove("aionly");b.classList.add("unfolding");try{const d=document.querySelector(".dash.hud");d.classList.remove("unf");void d.offsetWidth;d.classList.add("unf");}catch(e){}
  dispatchEvent(new Event("resize"));setTimeout(()=>b.classList.remove("unfolding"),1500);}
 else{b.classList.remove("unfolding");b.classList.add("folding");setTimeout(()=>{b.classList.remove("folding");b.classList.add("aionly");dispatchEvent(new Event("resize"));},430);}}
window.vexView=setView;
["vxScanl","vxShim"].forEach(i=>{const e=document.createElement("div");e.id=i;document.body.appendChild(e);});
function tilt(){document.querySelectorAll(".dash.hud>.w:not(.hero)").forEach(w=>{const r=w.getBoundingClientRect();if(!r.width)return;const x=(r.left+r.width/2)/innerWidth-.5,y=(r.top+r.height/2)/innerHeight-.5;
 w.style.setProperty("--ry",(-x*22).toFixed(2)+"deg");w.style.setProperty("--rx",(y*10).toFixed(2)+"deg");w.style.setProperty("--tz",(-Math.abs(x)*40).toFixed(0)+"px");});}
addEventListener("resize",()=>setTimeout(tilt,100));setInterval(tilt,1500);setTimeout(tilt,800);
const css2=document.createElement("style");css2.textContent=`
#hcur{position:fixed;left:0;top:0;width:34px;height:34px;margin:-17px 0 0 -17px;z-index:9999;pointer-events:none;display:none;border-radius:50%;
 border:1.5px solid #5ff3ff;box-shadow:0 0 14px #19d8ff,inset 0 0 10px #19d8ff88;transition:width .12s,height .12s,margin .12s,border-color .12s}
#hcur::before,#hcur::after{content:"";position:absolute;left:50%;top:50%;background:#aefcff;box-shadow:0 0 6px #5ff3ff}
#hcur::before{width:4px;height:4px;margin:-2px;border-radius:50%}
#hcur::after{width:56px;height:56px;margin:-28px;border-radius:50%;background:none;border:1px dashed #5ff3ff55;animation:hspin 6s linear infinite}
#hcur.pinch{width:20px;height:20px;margin:-10px 0 0 -10px;border-color:#ffd166;box-shadow:0 0 18px #ffb703}
#hcur.scroll{border-radius:6px;border-color:#b388ff;box-shadow:0 0 14px #7c4dff}
@keyframes hspin{to{transform:rotate(360deg)}}
.hhover{outline:1px solid #5ff3ffaa!important;box-shadow:0 0 18px #19d8ff55!important}
#hcam{opacity:0!important;visibility:hidden!important;position:fixed;left:14px;bottom:14px;width:232px;z-index:9998;display:none;font:10px "VexMono",monospace;color:#7fefff;letter-spacing:.18em;
 background:#03141cc0;border:1px solid #19d8ff66;clip-path:polygon(0 0,88% 0,100% 14%,100% 100%,12% 100%,0 86%);padding:6px 8px 8px;pointer-events:none}
#hcam canvas{width:216px;height:162px;display:block;margin-top:4px;opacity:.95}
#hcam b{float:right;color:#ffd166;font-weight:400}`;document.head.appendChild(css);document.head.appendChild(css2);
const cur=document.createElement("div");cur.id="hcur";document.body.appendChild(cur);
const box=document.createElement("div");box.id="hcam";box.innerHTML='HAND LINK <b id="hgest">—</b><canvas id="hcv" width="216" height="162"></canvas>';document.body.appendChild(box);
const dot=document.createElement("div");dot.id="hdot";document.body.appendChild(dot);
const cv=box.querySelector("canvas"),cx=cv.getContext("2d"),gl=box.querySelector("#hgest");
const video=document.createElement("video");video.muted=true;video.playsInline=true;
let lm=null,stream=null,camId=null,running=false,st={enabled:false,mouse:false,paused:false,camera:""},starting=false;
let rawPose="",rawAt=0,poseHist=[],viewCd=0,sx=null,sy=null,pinch=false,pinchAt=0,pinchX=0,pinchY=0,dragging=false,downEl=null,hoverEl=null,lastScrollY=null,palmHist=[],swipeCd=0,fistAt=0,fistCd=0,lastPose="",lastMouse=0;
const CONN=[[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[5,9],[9,10],[10,11],[11,12],[9,13],[13,14],[14,15],[15,16],[13,17],[17,18],[18,19],[19,20],[0,17]];
const D=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
async function ensureModel(){if(lm)return lm;const fs=await FilesetResolver.forVisionTasks(new URL("./lib/mediapipe/wasm",location.href).href);
 const mk=d=>HandLandmarker.createFromOptions(fs,{baseOptions:{modelAssetPath:new URL("./lib/mediapipe/hand_landmarker.task",location.href).href,delegate:d},runningMode:"VIDEO",numHands:1,minHandDetectionConfidence:.6,minTrackingConfidence:.5});
 try{lm=await mk("GPU");LOG("model loaded (GPU)");}catch(e){LOG("GPU delegate failed, using CPU: "+e);lm=await mk("CPU");LOG("model loaded (CPU)");}return lm;}
window.vexListCameras=async()=>{try{const d=await navigator.mediaDevices.enumerateDevices();return d.filter(x=>x.kind=="videoinput").map((x,i)=>({id:x.deviceId,name:x.label||("Camera "+(i+1))}));}catch(e){return[];}};
async function start(){if(running||starting)return;starting=true;try{
 const cams=await vexListCameras();if(!cams.length&&!(await navigator.mediaDevices.enumerateDevices()).some(x=>x.kind=="videoinput")){LOG("no webcam detected");toast("Hand control","No webcam detected.");starting=false;return;}
 const v={width:{ideal:640},height:{ideal:480},frameRate:{ideal:30}};if(st.camera)v.deviceId={exact:st.camera};
 try{stream=await navigator.mediaDevices.getUserMedia({video:v,audio:false});}catch(e){if(st.camera){delete v.deviceId;stream=await navigator.mediaDevices.getUserMedia({video:v,audio:false});}else throw e;}
 camId=st.camera;video.srcObject=stream;await video.play();const tr=stream.getVideoTracks()[0];LOG("camera opened: "+tr.label+" "+video.videoWidth+"x"+video.videoHeight);
 await ensureModel();running=true;box.style.display="block";dot.style.display="block";requestAnimationFrame(loop);}catch(e){LOG("camera/model error: "+e);toast("Hand control","Couldn't open the webcam: "+(e.name||e));stop();}starting=false;}
function stop(){running=false;if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;LOG("camera closed");}video.srcObject=null;box.style.display="none";dot.style.display="none";cur.style.display="none";endPinch(true);setHover(null);}
function toast(t,m){try{window.toast&&window.toast(t,m)}catch(e){}}
async function poll(){try{const a=api();if(a&&a.hand_state){st=await a.hand_state();if(st.view_seq!==undefined&&st.view_seq!==viewSeq){const first=viewSeq<0;viewSeq=st.view_seq;if(!first||st.view=="full")setView(st.view,"voice");}const want=st.enabled&&!st.paused&&!(window.vexHidden&&vexHidden());
 if(want&&running&&camId!==st.camera){stop();}if(want&&!running)start();else if(!want&&running)stop();}}catch(e){}setTimeout(poll,1500);}
setTimeout(poll,2500);
function ext(h,t,p){return D(h[t],h[0])>D(h[p],h[0])*1.12;}
function pose(h){const s=D(h[0],h[9])||.1,pin=D(h[4],h[8])/s;const i=ext(h,8,6),m=ext(h,12,10),r=ext(h,16,14),p=ext(h,20,18);
 if(pin<(pinch?.5:.33))return"pinch";if(i&&m&&r&&p)return"palm";if(i&&m&&!r&&!p)return"two";if(!i&&!m&&!r&&!p)return"fist";if(i)return"point";return"none";}
function elAt(x,y){cur.style.display="none";const e=document.elementFromPoint(x,y);cur.style.display="block";return e;}
function target(e){return e&&e.closest("button,a,input,select,textarea,.toggle,[onclick],.w,li,.memrow,label")||e;}
function setHover(e){if(hoverEl==e)return;hoverEl&&hoverEl.classList.remove("hhover");hoverEl=e;e&&e!=document.body&&e.classList.add("hhover");}
function fire(e,type,x,y){if(!e)return;const o={bubbles:true,cancelable:true,clientX:x,clientY:y,button:0,buttons:type.endsWith("up")?0:1,pointerId:7,pointerType:"mouse",isPrimary:true};
 try{e.dispatchEvent(new PointerEvent(type.replace("mouse","pointer"),o));}catch(_){}e.dispatchEvent(new MouseEvent(type,o));}
function mouse(fx,fy,ev,amt){if(!st.mouse)return;const a=api();if(!a||!a.hand_mouse)return;const n=performance.now();if(ev=="move"&&n-lastMouse<33)return;lastMouse=n;a.hand_mouse(fx,fy,ev,amt||0);}
function scrollable(e){while(e&&e!=document.body){const s=getComputedStyle(e);if(/(auto|scroll)/.test(s.overflowY)&&e.scrollHeight>e.clientHeight+4)return e;e=e.parentElement;}return document.querySelector(".page.on .scroll")||document.scrollingElement;}
function endPinch(cancel){if(!pinch)return;pinch=false;cur.classList.remove("pinch");const x=sx,y=sy,e=elAt(x,y);
 if(!cancel){fire(dragging?e:downEl,"mouseup",x,y);if(!dragging&&downEl){const t=target(downEl);if(t&&t.focus)t.focus();t&&t.click();}mouse(x/innerWidth,y/innerHeight,dragging?"up":"click");}
 dragging=false;downEl=null;}
function switchTab(dir){if(VIEW!="full")return;const tabs=[...document.querySelectorAll("#dtabs button")];if(!tabs.length)return;let i=tabs.findIndex(t=>t.classList.contains("on"));i=(i+dir+tabs.length)%tabs.length;tabs[i].click();LOG("swipe -> "+tabs[i].dataset.t);}
function loop(){if(!running)return;requestAnimationFrame(loop);if(video.readyState<2)return;const now=performance.now();
 if(loop.t&&now-loop.t<30)return;loop.t=now;let r;try{r=lm.detectForVideo(video,now);}catch(e){LOG("detect error "+e);stop();return;}
 cx.save();cx.clearRect(0,0,216,162);cx.translate(216,0);cx.scale(-1,1);
 const h=r.landmarks&&r.landmarks[0];
 if(h){cx.strokeStyle="#5ff3ff";cx.lineWidth=1.4;cx.shadowColor="#19d8ff";cx.shadowBlur=6;cx.beginPath();CONN.forEach(([a,b])=>{cx.moveTo(h[a].x*216,h[a].y*162);cx.lineTo(h[b].x*216,h[b].y*162);});cx.stroke();
  h.forEach((p,i)=>{cx.fillStyle=(i==8||i==4)?"#ffd166":"#aefcff";cx.beginPath();cx.arc(p.x*216,p.y*162,i==8?3.2:2,0,7);cx.fill();});}
 cx.restore();cx.strokeStyle="#19d8ff44";cx.strokeRect(.5,.5,215,161);
 dot.classList.toggle("on",!!h);if(h){window.__mouse={x:(sx==null?0:sx/innerWidth-.5)*2,y:(sy==null?0:sy/innerHeight-.5)*2};}
 if(!h){gl.textContent="NO HAND";cur.style.display="none";endPinch(true);setHover(null);palmHist=[];fistAt=0;lastScrollY=null;return;}
 const P=pose(h);gl.textContent={pinch:dragging?"DRAG":"PINCH",palm:"PALM",two:"SCROLL",fist:"FIST",point:"POINT",none:"—"}[P];
 // cursor: index tip (mirrored), central 70% of the frame maps to the whole window; smoothed
 const tip=P=="two"?{x:(h[8].x+h[12].x)/2,y:(h[8].y+h[12].y)/2}:(P=="pinch"?{x:(h[4].x+h[8].x)/2,y:(h[4].y+h[8].y)/2}:h[8]);
 const fx=Math.min(1,Math.max(0,((1-tip.x)-.15)/.7)),fy=Math.min(1,Math.max(0,(tip.y-.15)/.65));const tx=fx*innerWidth,ty=fy*innerHeight;
 if(sx==null){sx=tx;sy=ty;}const k=Math.hypot(tx-sx,ty-sy)>80?.55:.3;sx+=(tx-sx)*k;sy+=(ty-sy)*k;
 cur.style.display="block";cur.style.transform=`translate(${sx}px,${sy}px)`;cur.classList.toggle("scroll",P=="two");
 if(P!="palm")palmHist=[];if(P!="fist")fistAt=0;if(P!="two")lastScrollY=null;
 if(P=="pinch"){const e=elAt(sx,sy);if(!pinch){pinch=true;pinchAt=now;pinchX=sx;pinchY=sy;downEl=e;cur.classList.add("pinch");fire(e,"mousedown",sx,sy);}
  else{if(!dragging&&(Math.hypot(sx-pinchX,sy-pinchY)>28&&now-pinchAt>180)){dragging=true;mouse(pinchX/innerWidth,pinchY/innerHeight,"down");}
   if(dragging){fire(e,"mousemove",sx,sy);if(downEl&&downEl.type=="range"){const b=downEl.getBoundingClientRect();downEl.value=+downEl.min+(+downEl.max-+downEl.min)*Math.min(1,Math.max(0,(sx-b.left)/b.width));downEl.dispatchEvent(new Event("input",{bubbles:true}));}
    else{const sc=scrollable(e);sc&&(sc.scrollTop-=(sy-(loop.py||sy)));}}}
  mouse(sx/innerWidth,sy/innerHeight,"move");}
 else{endPinch(false);
  if(P=="point"||P=="none"){const e=elAt(sx,sy);setHover(target(e));mouse(sx/innerWidth,sy/innerHeight,"move");}else setHover(null);
  if(P=="two"){const y=tip.y;if(lastScrollY!=null){const dy=(y-lastScrollY)*innerHeight*2.2;if(Math.abs(dy)>.5){const sc=scrollable(elAt(sx,sy));sc&&(sc.scrollTop+=dy);if(st.mouse)mouse(sx/innerWidth,sy/innerHeight,"wheel",-Math.round(dy*2));}}lastScrollY=y;}
  if(P=="palm"&&now>swipeCd){const x=1-h[9].x;palmHist.push([now,x]);palmHist=palmHist.filter(p=>now-p[0]<450);const dx=x-palmHist[0][1];
   if(Math.abs(dx)>.22){switchTab(dx>0?1:-1);swipeCd=now+900;palmHist=[];}}
  if(P=="fist"&&now>fistCd){if(!fistAt)fistAt=now;const p=Math.min(1,(now-fistAt)/1000);gl.textContent="FIST "+Math.round(p*100)+"%";
   if(p>=1){fistCd=now+2500;fistAt=0;const a=api();a&&a.hand_wake&&a.hand_wake().then(r=>{LOG("fist -> "+r);toast("Hand control",r=="wake"?"Listening…":"Going quiet.");});}}}
 loop.py=sy;if(P!=rawPose){rawPose=P;rawAt=now;}
 if(now-rawAt>220&&P!=lastPose){if(P=="palm"||P=="fist")poseHist.push([now,P]);poseHist=poseHist.filter(p=>now-p[0]<1200);
  const n=poseHist.length;if(n>=2&&now>viewCd){const a=poseHist[n-2][1],b=poseHist[n-1][1];
   if(a=="fist"&&b=="palm"&&VIEW=="ai"){setView("full","open hand");viewCd=now+1500;swipeCd=now+1200;}
   else if(a=="palm"&&b=="fist"&&VIEW=="full"){setView("ai","close hand");viewCd=now+1500;fistCd=now+1600;}}
  lastPose=P;}
}
window.vexHand={start,stop,state:()=>({running,st})};
