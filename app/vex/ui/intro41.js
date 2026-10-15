// Vex 4.1 startup presentation ("intro41"). Original art only: no sounds, no faces, no channel stats, no camera.
// One ~52 s timeline shared by the main window (3D core + overlay) and every companion HUD, synced by wall clock.
// Skippable: click / Esc (main window) or saying "skip". The backend never plays it during games/VR.
(function(){
"use strict";
const COMP=document.body.classList.contains("comp");
const A=()=>window.pywebview&&window.pywebview.api;
const LOGF=m=>{try{(window.vexUiLog||(x=>A()&&A().ui_log&&A().ui_log(x)))(m)}catch(e){}};
const DUR=52;
const MODES=["red","green","purple","gold","pink","white","black"];
const MC={blue:"#5fd4ff",red:"#ff3a4a",green:"#6ff0a0",purple:"#c08cff",gold:"#f0c060",pink:"#ff70d0",white:"#f2f6ff",black:"#a33a3a"};
const MRGB={blue:[95,212,255],red:[255,58,74],green:[111,240,160],purple:[192,140,255],gold:[240,192,96],pink:[255,112,208],white:[242,246,255],black:[163,58,58]};
const MBG={blue:"#020b1c",red:"#14020a",green:"#03140d",purple:"#0d0418",gold:"#0a0803",pink:"#1a0628",white:"#0c1014",black:"#020203"};
const MCLR={red:0x14020a,green:0x03140d,purple:0x0d0418,gold:0x0a0803,pink:0x1a0628,white:0x0c1014,black:0x020203};
const MNAME={red:["STRIKE","RED MODE","TACTICAL · LOW-FX · ALERTS MUTED"],green:["GROVE","GREEN MODE","CALM STUDY · FOCUS TIMER"],
 purple:["STUDIO","PURPLE MODE","CREATOR STUDIO · OBS · CAPCUT ON COMMAND"],gold:["LEDGER","GOLD MODE","GOALS · SYSTEM LEDGER"],
 pink:["NIGHTDRIVE","PINK MODE","SYNTHWAVE · AFTER HOURS"],white:["LAB","WHITE MODE","CLEAN LAB · DIAGNOSTICS"],black:["SHADE","BLACK MODE","STEALTH · PRIVATE · DIMMED"]};
const T_TOUR=23,SEGL=3,LOCKS=[8.9,9.7,10.5];
const SECT=[[0,"COLD BOOT"],[2,"CORE ASSEMBLY"],[8.3,"RING LOCK"],[11.6,"SYSTEMS ONLINE"],[15.2,"DAILY BRIEFING"],[22.6,"MODE TOUR"],[44,"HOLOGRAPHIC SCAN"],[48.5,"ONLINE"]];
const cl=(x,a=0,b=1)=>x<a?a:x>b?b:x,seg=(t,a,b)=>cl((t-a)/(b-a)),eo=x=>1-Math.pow(1-x,3),ei=x=>x*x*x,eio=x=>x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;
const eb=x=>{const c1=1.70158,c3=c1+1;return 1+c3*Math.pow(x-1,3)+c1*Math.pow(x-1,2);};
const hit=(t,a,k=8)=>t<a?0:Math.exp(-(t-a)*k);
const rgba=(m,a)=>{const c=MRGB[m]||MRGB.blue;return `rgba(${c[0]},${c[1]},${c[2]},${a})`;};
const R=(s=>()=>{s=(s*16807)%2147483647;return (s-1)/2147483646;})(4141);

// ---------- DOM
const css=`#i41{position:fixed;inset:0;z-index:2147483000;display:none;pointer-events:none}#i41.on{display:block}
#i41 canvas{position:absolute;inset:0;width:100%;height:100%}
body:not(.comp) #i41.on{pointer-events:auto;cursor:pointer}
body.i41on>*:not(#i41):not(#gl):not(script):not(style){opacity:0!important;transition:opacity .5s ease!important;pointer-events:none!important}`;
const st=document.createElement("style");st.textContent=css;document.head.appendChild(st);
const root=document.createElement("div");root.id="i41";const cv=document.createElement("canvas");root.appendChild(cv);document.body.appendChild(root);
const x=cv.getContext("2d");
let W=0,H=0,DPR=1;function fit(){DPR=Math.min(1.25,devicePixelRatio||1);W=innerWidth;H=innerHeight;cv.width=Math.round(W*DPR);cv.height=Math.round(H*DPR);x.setTransform(DPR,0,0,DPR,0,0);}
addEventListener("resize",fit);fit();
const AN=((window.__AN||"Vex").trim()||"Vex").toUpperCase();
const UIF='"Segoe UI",system-ui,sans-serif',MONO='VexMono,Consolas,monospace',BLK='"Segoe UI Black","Segoe UI",system-ui,sans-serif';

// scanline + fine-grid patterns (pre-rendered once: cheap per frame)
const pat=(w,h,fn)=>{const c=document.createElement("canvas");c.width=w;c.height=h;fn(c.getContext("2d"));return x.createPattern(c,"repeat");};
const SCAN=pat(4,4,g=>{g.fillStyle="rgba(0,0,0,.35)";g.fillRect(0,0,4,1);});
const GRID=pat(40,40,g=>{g.strokeStyle="rgba(230,240,255,.10)";g.lineWidth=1;g.strokeRect(.5,.5,40,40);g.fillStyle="rgba(230,240,255,.05)";for(let i=8;i<40;i+=8){g.fillRect(i,0,1,40);g.fillRect(0,i,40,1);}});

// ---------- kinetic typography
const cw={};function wch(ch,font){const k=font+ch;if(cw[k]==null){x.font=font;cw[k]=x.measureText(ch).width;}return cw[k];}
const GL="#%&@$/\\<>01XV=+*";
// draws str with per-letter entrance: o={t (local time), size, font, col, ls (letter spacing em), st (stagger), dur, dec (decode), al ('c'|'l'|'r'), out (0..1 exit), glitch}
function kin(str,px,py,o){const t=o.t;if(t<=0)return;const sz=o.size,font=`${o.w||400} ${sz}px ${o.font||UIF}`,ls=(o.ls||0)*sz,stg=o.st==null?.04:o.st,du=o.dur||.45;
 let tw=0;const ws=[...str].map(c=>{const w=wch(c,font);tw+=w+ls;return w;});tw-=ls;let cx=o.al=="l"?px:o.al=="r"?px-tw:px-tw/2;
 x.font=font;x.textBaseline="middle";const out=o.out||0;const chars=[...str];
 for(let i=0;i<chars.length;i++){const c=chars[i];let u=(t-i*stg)/du;if(u<=0){cx+=ws[i]+ls;continue;}u=cl(u);
  let ox=0,oy=(1-eo(u))*sz*.55*(o.dir||1),sc=1+(1-eo(u))*(o.zoom||0),a=cl(u*2.2)*(1-out);
  if(out>0){oy-=out*sz*.4*((i%2)?1:-1)*(o.burst||0);ox+=out*sz*(o.spread||0)*(i-chars.length/2)/chars.length;}
  let ch=c;if(o.dec&&u<.6&&c!=" ")ch=GL[(Math.random()*GL.length)|0];
  const gx=cx+ws[i]/2+ox,gy=py+oy;x.save();x.translate(gx,gy);if(sc!==1)x.scale(sc,sc);x.textAlign="center";
  const g=(o.glitch||0)+(u<1?(1-u)*.6*(o.rgbIn||0):0);
  if(g>0){x.globalCompositeOperation="lighter";x.globalAlpha=a*.8;x.fillStyle="rgba(255,40,80,1)";x.fillText(ch,-g*sz*.06,0);x.fillStyle="rgba(40,220,255,1)";x.fillText(ch,g*sz*.06,0);x.globalCompositeOperation="source-over";}
  x.globalAlpha=a;if(o.glow){x.shadowColor=o.glow;x.shadowBlur=sz*.35;}x.fillStyle=o.col||"#fff";x.fillText(ch,0,0);x.restore();cx+=ws[i]+ls;}
 x.globalAlpha=1;return tw;}
function txt(s,px,py,size,col,al="l",font=MONO,a=1,w=400){x.globalAlpha=a;x.font=`${w} ${size}px ${font}`;x.textAlign=al=="c"?"center":al=="r"?"right":"left";x.textBaseline="middle";x.fillStyle=col;x.fillText(s,px,py);x.globalAlpha=1;}
function brackets(cx,cy,w,h,l,col,a,lw=2){x.globalAlpha=a;x.strokeStyle=col;x.lineWidth=lw;x.beginPath();
 [[-1,-1],[1,-1],[1,1],[-1,1]].forEach(([sx,sy])=>{const X=cx+sx*w/2,Y=cy+sy*h/2;x.moveTo(X-sx*l,Y);x.lineTo(X,Y);x.lineTo(X,Y-sy*l);});x.stroke();x.globalAlpha=1;}

// ---------- state
let S=null,raf=0,ended=true,fr={n:0,last:0,slow:0,worst:0},modeSet="",hidT=0;
const I={on:false};window.__i41=I;
function geo(){const me=S.me||{x:0,w:W,h:H},sc=W/(me.w||W);return {me,sc};}
function coreLocal(){if(!COMP){const o=document.getElementById("orb"),r=o&&o.getBoundingClientRect();if(r&&r.width>20)return [r.left+r.width/2,r.top+r.height/2];return [W/2,H*.47];}
 const {me,sc}=geo(),c=S.core||[me.x+me.w*1.5,(me.h||H)/2];return [(c[0]-me.x)*sc,(c[1]-(me.y||0))*sc];}

// ---------- comp-only: 2D particle emblem (hexagon + V glyph + rings), original design
let EMB=null;function emblem(){const n=1500,P=[],rr=Math.min(W,H)*.26,cx=W/2,cy=H*.5;const tg=[];
 const lineP=(a,b,k)=>{for(let i=0;i<k;i++){const u=i/k;tg.push([a[0]+(b[0]-a[0])*u,a[1]+(b[1]-a[1])*u]);}};
 for(let s=0;s<6;s++){const a0=s/6*6.283-1.5708,a1=(s+1)/6*6.283-1.5708;lineP([cx+Math.cos(a0)*rr,cy+Math.sin(a0)*rr],[cx+Math.cos(a1)*rr,cy+Math.sin(a1)*rr],110);}
 for(let i=0;i<320;i++){const a=i/320*6.283;tg.push([cx+Math.cos(a)*rr*.62,cy+Math.sin(a)*rr*.62]);}
 lineP([cx-rr*.42,cy-rr*.36],[cx,cy+rr*.44],200);lineP([cx+rr*.42,cy-rr*.36],[cx,cy+rr*.44],200);
 for(let i=0;i<120;i++){const a=R()*6.283,q=R()*rr*.14;tg.push([cx+Math.cos(a)*q,cy+Math.sin(a)*q]);}
 for(let i=0;i<n;i++){const t=tg[i%tg.length],a=R()*6.283,d=Math.max(W,H)*(.6+R()*.6);P.push({sx:cx+Math.cos(a)*d,sy:cy+Math.sin(a)*d,tx:t[0]+(R()-.5)*2,ty:t[1]+(R()-.5)*2,d:R()*.55,s:1+R()*1.6});}
 EMB={P,rr,cx,cy};}

// ---------- briefing card
function card(c,px,py,w,h,a,u,m){if(a<=0)return;x.save();x.globalAlpha=a;x.fillStyle="rgba(6,24,52,.72)";x.fillRect(px,py,w,h);x.strokeStyle=rgba(m,.45);x.lineWidth=1;x.strokeRect(px+.5,py+.5,w-1,h-1);
 brackets(px+w/2,py+h/2,w+6,h+6,12,MC[m],a,2);x.globalAlpha=a;
 const f=h/170;txt(c.title||"",px+16*f,py+20*f,12*f,MC[m],"l",MONO,a);
 let big=String(c.big||"--");const num=parseFloat(big);if(!isNaN(num)&&u<1){const k=Math.round(num*eo(u));big=big.replace(/^-?\d+(\.\d+)?/,String(k));}
 txt(big,px+16*f,py+56*f,40*f,"#fff","l",UIF,a,300);txt(c.sub||"",px+16*f,py+84*f,11*f,"rgba(180,210,240,.8)","l",MONO,a);
 (c.rows||[]).slice(0,3).forEach((r,i)=>{const yy=py+(108+i*20)*f;txt(String(r[0]||""),px+16*f,yy,11*f,"rgba(150,190,230,.75)","l",MONO,a*cl(u*2-i*.3));
  let v=String(r[1]||"");x.font=`${11*f}px ${MONO}`;while(v.length>3&&x.measureText(v).width>w-70*f)v=v.slice(0,-2)+"…";txt(v,px+w-16*f,yy,11*f,"#e9fbff","r",MONO,a*cl(u*2-i*.3));});
 x.restore();}

// ---------- mode worlds (drawn semi-transparent over the 3D core in main, opaque on companions)
function world(m,u,a,cx,cy){if(a<=0)return;const op=COMP;x.save();x.globalAlpha=1;
 if(op){x.fillStyle=MBG[m];x.fillRect(0,0,W,H);}
 const A2=(v)=>v*a;const col=MC[m];
 if(m=="red"){x.globalAlpha=A2(op?.9:.55);x.fillStyle=rgba("red",.08);x.fillRect(0,0,W,H);
  x.strokeStyle=rgba("red",.55);x.lineWidth=1;x.beginPath();x.moveTo(0,cy);x.lineTo(W,cy);x.moveTo(cx,0);x.lineTo(cx,H);x.stroke();
  const off=(u*160)%40;x.fillStyle=rgba("red",.35);for(let i=-2;i<W/40+2;i++){const X=i*40+off;x.beginPath();x.moveTo(X,H*.13);x.lineTo(X+18,H*.13);x.lineTo(X+38,H*.16);x.lineTo(X+20,H*.16);x.fill();x.beginPath();x.moveTo(X,H*.84);x.lineTo(X+18,H*.84);x.lineTo(X+38,H*.87);x.lineTo(X+20,H*.87);x.fill();}
  const rr=Math.min(W,H)*(.2+.012*Math.sin(u*9));brackets(cx,cy,rr*2,rr*2,rr*.25,col,A2(1),3);
  x.globalAlpha=A2(.8);x.strokeStyle=col;x.lineWidth=2;x.beginPath();x.arc(cx,cy,rr*1.25,u*2.6,u*2.6+1.1);x.stroke();x.beginPath();x.arc(cx,cy,rr*1.25,u*2.6+3.14,u*2.6+4.24);x.stroke();
  txt("THREAT GRID // CLEAR",cx+rr*1.05,cy-rr*1.05,12,col,"l",MONO,A2(.9));txt("TGT-00 · NO CONTACTS",cx-rr*1.05,cy+rr*1.08,12,col,"r",MONO,A2(.9));}
 else if(m=="green"){x.globalAlpha=A2(op?.9:.5);x.strokeStyle=rgba("green",.35);x.lineWidth=1.2;
  for(let k=0;k<9;k++){const r0=((k*70+u*40)%630)+60;x.globalAlpha=A2((op?.8:.5)*(1-r0/700));x.beginPath();for(let i=0;i<=72;i++){const t=i/72*6.283,rr=r0*(1+.05*Math.sin(t*5+k+u*.8));const X=cx+Math.cos(t)*rr*1.25,Y=cy+Math.sin(t)*rr*.8;i?x.lineTo(X,Y):x.moveTo(X,Y);}x.stroke();}
  x.fillStyle=rgba("green",.7);for(let i=0;i<46;i++){const px=(i*137.5)%W,py=H-((u*40+i*53)%H);x.globalAlpha=A2(.5*Math.sin(i+u)*.5+.3);x.fillRect(px,py,2,2);}}
 else if(m=="purple"){x.globalAlpha=A2(op?1:.85);x.fillStyle=SCAN;x.fillRect(0,0,W,H);x.globalAlpha=A2(.9);
  const m2=Math.min(W,H)*.06;brackets(W/2,H/2,W-m2*4,H*.62,m2*.8,col,A2(.9),2);
  const lx=W*.07,ly=H*.71,lw=Math.min(W*.36,620)*eo(cl(u*2.2)),lh=H*.07;const g=x.createLinearGradient(lx,0,lx+lw,0);g.addColorStop(0,"rgba(122,44,255,.85)");g.addColorStop(1,"rgba(192,140,255,.1)");x.fillStyle=g;x.fillRect(lx,ly,lw,lh);
  x.fillStyle="#fff";x.fillRect(lx,ly,6,lh);if(u>.4){txt("CREATOR STUDIO",lx+22,ly+lh*.38,lh*.34,"#fff","l",UIF,A2(cl((u-.4)*3)),600);txt("SCENES · OBS · CAPCUT · ON YOUR COMMAND",lx+22,ly+lh*.74,lh*.17,"rgba(235,220,255,.9)","l",MONO,A2(cl((u-.5)*3)));}}
 else if(m=="gold"){x.globalAlpha=A2(op?.9:.6);const items=S.tick||[];const str=(items.join("   ◆   ")+"   ◆   ").repeat(3);
  [[H*.15,1],[H*.85,-1]].forEach(([yy,dir])=>{x.fillStyle="rgba(240,192,96,.12)";x.fillRect(0,yy-14,W,28);x.font=`14px ${MONO}`;x.fillStyle=col;x.textBaseline="middle";x.textAlign="left";const tw=x.measureText(str).width/3;const off=((u*140*dir)%tw+tw)%tw;x.fillText(str,-off,yy);});
  for(let s=0;s<2;s++){const bx=s?W*.86:W*.06,n=10;for(let i=0;i<n;i++){const hgt=(.3+.7*Math.abs(Math.sin(i*1.7+u*1.6+s)))*H*.22;x.fillStyle=i%3?rgba("gold",.45):rgba("gold",.85);x.fillRect(bx+i*12,H*.68-hgt,7,hgt);}}
  x.strokeStyle=rgba("gold",.6);x.lineWidth=1;x.beginPath();x.arc(cx,cy,Math.min(W,H)*.24,0,6.283);x.stroke();txt("LEDGER // GOALS",cx,cy+Math.min(W,H)*.27,13,col,"c",MONO,A2(.9));}
 else if(m=="pink"){const hz=H*.66,sr=Math.min(W,H)*.2,rise=eo(cl(u*1.4));x.globalCompositeOperation=op?"source-over":"lighter";x.globalAlpha=A2(op?1:.55);
  const sy=hz+sr*.25-sr*.55*rise;const g=x.createLinearGradient(0,sy-sr,0,sy+sr);g.addColorStop(0,"#ffd36e");g.addColorStop(.55,"#ff5fb8");g.addColorStop(1,"#a01d8f");
  x.save();x.beginPath();x.rect(0,0,W,hz);x.clip();x.fillStyle=g;x.beginPath();x.arc(W/2,sy,sr,0,6.283);x.fill();x.globalCompositeOperation="destination-out";if(op){x.globalCompositeOperation="source-over";x.fillStyle=MBG.pink;}
  for(let i=0;i<7;i++){const yy=sy+sr*(.05+i*.14),hh=2+i*1.6;x.fillRect(W/2-sr,yy,sr*2,hh);}x.restore();
  x.globalCompositeOperation=op?"source-over":"lighter";x.globalAlpha=A2(op?.9:.5);x.strokeStyle="#ff5fd0";x.lineWidth=1.3;x.beginPath();x.moveTo(0,hz);x.lineTo(W,hz);
  for(let i=-14;i<=14;i++){x.moveTo(W/2+i*W*.02,hz);x.lineTo(W/2+i*W*.16,H);}const sp=(u*.9)%1;for(let j=0;j<10;j++){const z=(j+sp)/10,yy=hz+(H-hz)*z*z;x.moveTo(0,yy);x.lineTo(W,yy);}x.stroke();x.globalCompositeOperation="source-over";}
 else if(m=="white"){x.globalAlpha=A2(op?1:.7);x.fillStyle=GRID;x.fillRect(0,0,W,H);x.strokeStyle="rgba(242,246,255,.55)";x.lineWidth=1;x.beginPath();
  for(let i=0;i<W;i+=20){const l=i%100==0?14:6;x.moveTo(i,H*.14);x.lineTo(i,H*.14+l);x.moveTo(i,H*.86);x.lineTo(i,H*.86-l);}x.moveTo(cx-W*.3,cy);x.lineTo(cx+W*.3,cy);x.moveTo(cx,cy-H*.3);x.lineTo(cx,cy+H*.3);x.stroke();
  [.14,.22].forEach((k,i)=>{const r=Math.min(W,H)*k;x.setLineDash(i?[4,6]:[]);x.beginPath();x.arc(cx,cy,r,0,6.283);x.stroke();x.setLineDash([]);txt("Ø "+(r/40).toFixed(2),cx+r*.72,cy-r*.72,12,"#f2f6ff","l",MONO,A2(.9));});}
 else if(m=="black"){x.globalAlpha=A2(.75);x.fillStyle="#000";x.fillRect(0,0,W,H);const g=x.createRadialGradient(cx,cy,0,cx,cy,Math.max(W,H)*.6);g.addColorStop(0,"rgba(0,0,0,0)");g.addColorStop(1,"rgba(0,0,0,.9)");x.globalAlpha=A2(1);x.fillStyle=g;x.fillRect(0,0,W,H);
  if(op){x.globalAlpha=A2(.5);x.strokeStyle=rgba("black",.6);x.beginPath();x.arc(cx,cy,Math.min(W,H)*.12,0,6.283);x.stroke();}}
 x.restore();}
// transition masks: return true if clip path set
function mask(m,u,cx,cy){const e=eo(cl(u));x.beginPath();
 if(m=="red"){const X=-H+(W+2*H)*e;x.moveTo(X-W*2,0);x.lineTo(X,0);x.lineTo(X-H,H);x.lineTo(X-W*2-H,H);x.closePath();}
 else if(m=="green"){x.arc(cx,cy,Math.hypot(W,H)*e,0,6.283);}
 else if(m=="purple"){const hh=H*(u<.25?.004:eo(cl((u-.25)/.75)));x.rect(0,H/2-hh/2,W,hh);}
 else if(m=="gold"){for(let i=0;i<6;i++){const k=eo(cl(u*1.3-i*.06));x.rect(0,i*H/6,W*k,H/6+1);}}
 else if(m=="pink"){const hz=H*.66,k=eo(cl(u));x.rect(0,hz-hz*k,W,(hz+(H-hz))*k+1);}
 else if(m=="white"){x.rect(0,0,W,H*e);}
 else {x.rect(0,0,W,H);}
 x.clip();}
function transFX(m,u,cx,cy){if(u>=1||u<0)return;const e=eo(u);x.save();
 if(m=="red"){const X=-H+(W+2*H)*e;x.globalCompositeOperation="lighter";x.strokeStyle="#ffd0d4";x.shadowColor="#ff2a40";x.shadowBlur=30;x.lineWidth=6*(1-u)+1;x.beginPath();x.moveTo(X,0);x.lineTo(X-H,H);x.stroke();}
 else if(m=="green"){x.strokeStyle=rgba("green",.8*(1-u));x.lineWidth=3;for(let k=0;k<3;k++){x.beginPath();x.arc(cx,cy,Math.max(0,Math.hypot(W,H)*e-k*60),0,6.283);x.stroke();}}
 else if(m=="purple"){if(u<.25){const bars=["#c08cff","#7a2cff","#ffffff","#3a1a66","#ff70d0","#1a0628","#f0e6ff"];x.globalAlpha=.85*(1-u*4);bars.forEach((b,i)=>{x.fillStyle=b;x.fillRect(i*W/7,0,W/7+1,H);});}
  else{const hh=H*eo(cl((u-.25)/.75));x.fillStyle="rgba(255,255,255,.8)";x.fillRect(0,H/2-hh/2-2,W,3);x.fillRect(0,H/2+hh/2-1,W,3);}}
 else if(m=="gold"){x.fillStyle="#ffe2a0";x.shadowColor="#f0c060";x.shadowBlur=20;for(let i=0;i<6;i++){const k=eo(cl(u*1.3-i*.06));if(k>0&&k<1)x.fillRect(W*k-4,i*H/6,4,H/6);}}
 else if(m=="pink"){const hz=H*.66,k=eo(u);x.strokeStyle="#ffd36e";x.shadowColor="#ff5fb8";x.shadowBlur=24;x.lineWidth=3;x.beginPath();x.moveTo(0,hz-hz*k);x.lineTo(W,hz-hz*k);x.moveTo(0,hz+(H-hz)*k);x.lineTo(W,hz+(H-hz)*k);x.stroke();}
 else if(m=="white"){x.fillStyle="#fff";x.shadowColor="#fff";x.shadowBlur=30;x.fillRect(0,H*e-2,W,4);}
 x.restore();}
function glitch(k){if(k<=0)return;x.save();x.globalCompositeOperation="lighter";const n=(8+k*18)|0;
 for(let i=0;i<n;i++){const y=Math.random()*H,h=2+Math.random()*H*.04*k,ox=(Math.random()-.5)*W*.1*k;x.fillStyle=i%3==0?`rgba(255,40,90,${.25*k})`:i%3==1?`rgba(40,220,255,${.25*k})`:`rgba(255,255,255,${.12*k})`;x.fillRect(ox+Math.random()*W*.4,y,W*(.2+Math.random()*.6),h);}
 x.restore();}

// ---------- 3D camera path (relative to the core) for the main window
const CAM=[[0,-26,12,64],[1.5,-26,12,64],[4.5,12,6,34],[7.6,6,-2,10.5],[9.6,-4,1.5,12.5],[11.6,-1,.5,15],[15.2,-6,-3,19],[22.6,5,-1,18]];
const CUTS=[[7,2,13],[-8,-3,15],[0,6,12],[9,-4,14],[0,-5,13],[-7,2,12],[0,0,20]];
function catmull(p0,p1,p2,p3,u){const u2=u*u,u3=u2*u;return .5*((2*p1)+(-p0+p2)*u+(2*p0-5*p1+4*p2-p3)*u2+(-p0+3*p1-3*p2+p3)*u3);}
function camAt(t){if(t<CAM[CAM.length-1][0]){let i=0;while(i<CAM.length-2&&t>CAM[i+1][0])i++;const a=CAM[Math.max(0,i-1)],b=CAM[i],c=CAM[i+1],d=CAM[Math.min(CAM.length-1,i+2)],u=eio(seg(t,b[0],c[0]));return [1,2,3].map(k=>catmull(a[k],b[k],c[k],d[k],u));}
 if(t<T_TOUR){const a=CAM[CAM.length-1];return [a[1],a[2],a[3]];}
 if(t<44){const k=Math.min(6,((t-T_TOUR)/SEGL)|0),u=(t-T_TOUR-k*SEGL)/SEGL,c=CUTS[k];return [c[0]*(1-.25*u),c[1]*(1-.25*u),c[2]+(16-c[2])*.3*u];}
 const u=eio(seg(t,44,48.4));return [0,1-u,17-0.5*u];}

// ---------- main frame
function frame(now){raf=requestAnimationFrame(frame);if(!S)return;const t=window.__i41T!=null?window.__i41T:(Date.now()-S.t0)/1000;
 if(fr.last){const dt=now-fr.last;if(t>0&&t<DUR){fr.n++;if(dt>20)fr.slow++;if(dt>fr.worst)fr.worst=dt;}}fr.last=now;
 if(t>=DUR){end("done");return;}
 x.clearRect(0,0,W,H);const [cx,cy]=coreLocal();const {me,sc}=geo();
 // per-section mode for the 3D core + tokens
 let md="blue";if(t>=T_TOUR&&t<44){const k=Math.min(6,((t-T_TOUR)/SEGL)|0),u=t-T_TOUR-k*SEGL;md=u<.18&&k>0?MODES[k-1]:MODES[k];if(k==0&&u<.18)md="blue";}
 if(t>=48.5)md=S.mode||"blue";
 if(!COMP&&md!==modeSet){modeSet=md;document.body.dataset.mode=md;window.__tintM=null;}
 if(!COMP&&document.body.dataset.mode!==md)document.body.dataset.mode=md;
 // 3D driver values
 if(!COMP){const c=camAt(t);I.cx=c[0];I.cy=c[1];I.cz=c[2];I.ce=eio(seg(t,48.4,50.2));
  I.asm=1.2*eo(seg(t,2.2,8.2));I.cg=seg(t,4.6,8.0);I.wv=t>6.2;I.rv=.5*seg(t,6.4,8.3);I.rl=LOCKS.map(L=>ei(seg(t,L-.9,L)));
  let f=0;LOCKS.forEach(L=>f+=hit(t,L,9)*.9);f+=hit(t,11.75,6)*.5+hit(t,48.5,2.8)*1.6;for(let k=1;k<7;k++)f+=hit(t,T_TOUR+k*SEGL+.18,10)*.35;I.flash=f*.8;
  let dof=1-seg(t,2.0,7.4);dof+=.75*seg(t,12.1,12.8)*(1-seg(t,14.4,15.1));dof+=.22*seg(t,15.2,16)*(1-seg(t,22,22.6));I.dof=cl(dof);
  const gw=(a,b)=>t>a&&t<b?Math.sin((t-a)/(b-a)*Math.PI):0;let g=gw(14.6,15.3)+gw(22.3,23.0)*.9+gw(43.8,44.3)*.8;for(let k=1;k<7;k++)g+=gw(T_TOUR+k*SEGL-.06,T_TOUR+k*SEGL+.2)*.45;
  I.gl=cl(g);I.rgb=cl(g+hit(t,48.5,3)*1.2+hit(t,3.0,7)*.6+hit(t,3.6,7)*.6+hit(t,4.2,7)*.6);I.pulse=hit(t,48.5,2.6);I.clear=(t>=T_TOUR&&t<44)?MCLR[md]:null;}
 // ---- backgrounds
 if(COMP){x.fillStyle=MBG.blue;x.fillRect(0,0,W,H);const g=x.createRadialGradient(W/2,H/2,0,W/2,H/2,Math.max(W,H)*.7);g.addColorStop(0,"#0a2d66");g.addColorStop(1,"#010818");x.globalAlpha=cl(seg(t,1.5,4));x.fillStyle=g;x.fillRect(0,0,W,H);x.globalAlpha=1;}
 else{const k=1-seg(t,.8,2.6);if(k>0){x.fillStyle=`rgba(0,0,0,${k})`;x.fillRect(0,0,W,H);}}
 // ---- S0 cold open
 if(t<2.6){const ln=eo(seg(t,.15,.9))*(1-eo(seg(t,1.7,2.3)));if(ln>0){x.fillStyle="rgba(170,240,255,.9)";x.shadowColor="#5fd4ff";x.shadowBlur=18;x.fillRect(W/2-W*.4*ln,H/2-1,W*.8*ln,2);x.shadowBlur=0;}
  kin("INITIALIZING "+AN+" CORE",W/2,H/2+34,{t:t-.4,size:16,font:MONO,ls:.35,col:"#9fe9ff",dec:true,st:.03,dur:.3,out:seg(t,2.0,2.5)});}
 // ---- S1 assembly
 if(t>=1.8&&t<(COMP?12.2:9)){if(COMP){if(!EMB)emblem();const a=1.2*eo(seg(t,2.2,8.2));x.globalAlpha=1-seg(t,11.6,12.1);x.globalCompositeOperation="lighter";for(const p of EMB.P){let q=cl((a-p.d)/.45);q=eo(q);const sw=(1-q)*1.2;
    const dx=p.sx+(p.tx-p.sx)*q,dy=p.sy+(p.ty-p.sy)*q;const rx=EMB.cx+(dx-EMB.cx)*Math.cos(sw)-(dy-EMB.cy)*Math.sin(sw),ry=EMB.cy+(dx-EMB.cx)*Math.sin(sw)+(dy-EMB.cy)*Math.cos(sw);
    x.fillStyle=q>.98?"rgba(170,240,255,.95)":"rgba(95,212,255,.55)";x.fillRect(rx,ry,p.s,p.s);}x.globalCompositeOperation="source-over";x.globalAlpha=1;}
  else{x.save();x.globalCompositeOperation="lighter";const k=seg(t,2,5)*(1-seg(t,6.5,8));for(let i=0;i<40;i++){const a=i*2.399+t*.2,d0=Math.max(W,H)*(.7-((t*.35+i*.037)%1)*.6);x.strokeStyle=`rgba(120,230,255,${.35*k})`;x.lineWidth=1;x.beginPath();x.moveTo(cx+Math.cos(a)*d0,cy+Math.sin(a)*d0);x.lineTo(cx+Math.cos(a)*(d0-80),cy+Math.sin(a)*(d0-80));x.stroke();}x.restore();}
  if(t<9)[...AN.slice(0,5)].map((L,i,a)=>[L,3.0+i*(1.2/Math.max(1,a.length-1)),a.length<2?0:(i-(a.length-1)/2)*(2/(a.length-1))]).forEach(([L,s,p])=>{const u=t-s;if(u>0&&u<.62){const sz=H*.5*(1+.25*(1-eo(cl(u/.62))));kin(L,W/2+p*W*.2,H/2,{t:9,size:sz,font:BLK,w:900,col:"rgba(233,251,255,.92)",glitch:.8*(1-u/.62),out:seg(u,.32,.62),glow:"#5fd4ff"});}});
  const pc=Math.round(100*cl(eo(seg(t,2.2,8.2))*1.05));txt(`PARTICLE ASSEMBLY  ${String(pc).padStart(3," ")}%`,W*.07,H*.8,13,"#9fe9ff","l",MONO,seg(t,4.8,5.3)*(1-seg(t,8.4,8.9)));
  txt(`${Math.round(8400*cl(eo(seg(t,2.2,8.2))*1.05))} / 8400 POINTS`,W*.07,H*.8+20,11,"rgba(160,200,240,.7)","l",MONO,seg(t,4.8,5.3)*(1-seg(t,8.4,8.9)));}
 // ---- S2 ring lock (+ comp 2D rings) + checks
 if(t>=6&&t<12.2){const ck=1-seg(t,11.6,12.1);
  if(COMP&&!EMB)emblem();if(COMP&&EMB){LOCKS.forEach((L,k)=>{const l=ei(seg(t,L-.9,L)),r=EMB.rr*(1.15+k*.16)*(1+(1-l)*.6),a=(1-l)*4*(k%2?1:-1)+t*.15*(k+1);x.globalAlpha=(.25+.75*l)*seg(t,6.4,7.4)*ck;x.strokeStyle=k==1?"#f0c060":"#5fd4ff";x.lineWidth=l>=1?3:1.5;
    x.beginPath();x.ellipse(EMB.cx,EMB.cy,r,r*(.35+.65*l),a,0,6.283);x.stroke();x.globalAlpha=1;});}
  LOCKS.forEach((L,k)=>{const h=hit(t,L,7);if(t>L){const r=Math.min(W,H)*(.2+k*.035)*(1+.25*(1-eo(seg(t,L,L+.25))));brackets(cx,cy,r*2,r*2,r*.22,"#e9fbff",h*1.2*ck,3);
    kin(`RING 0${k+1} LOCKED`,cx+Math.min(W,H)*.29,cy-60+k*26,{t:t-L,size:13,font:MONO,ls:.3,col:k==1?"#f0c060":"#9fe9ff",al:"l",st:.02,dur:.25,out:seg(t,11.5,12)});}
    if(h>.05){x.fillStyle=`rgba(220,250,255,${h*.22})`;x.fillRect(0,0,W,H);}});
  const CK=S.checks||[];CK.slice(0,8).forEach((c,i)=>{const s=8.2+i*.38,u=t-s;if(u<=0)return;const y=H*.3+i*26,a=cl(u*4)*ck;
   txt(c.k,W*.07,y,12,"rgba(160,200,240,.8)","l",MONO,a);kin(String(c.v).toUpperCase(),W*.07+190,y,{t:u,size:12,font:MONO,al:"l",col:"#e9fbff",dec:true,st:.015,dur:.2,out:1-ck});
   if(u>.45)txt(c.ok?"✓":"–",W*.07-22,y,13,c.ok?"#7dffb0":"#ff9a9a","l",MONO,a);});}
 // ---- S3 title card
 if(t>=11.6&&t<15.4){const out=seg(t,14.55,15.25);const sz=Math.min(H*.22,W*.13);
  if(!COMP||true){x.fillStyle=`rgba(0,0,0,${.35*seg(t,11.6,12.2)*(1-out)})`;x.fillRect(0,0,W,H);}
  const tw=kin(AN,W/2,H/2-sz*.12,{t:t-11.7,size:sz,font:BLK,w:900,ls:.28,col:"#ffffff",st:.09,dur:.5,zoom:.5,rgbIn:1.4,glow:"#5fd4ff",out,burst:1,spread:2.5,glitch:out*2})||sz*2.5;
  const lk=eo(seg(t,12.0,12.8))*(1-out);x.fillStyle="rgba(95,212,255,.8)";x.fillRect(W/2-tw/2-W*.18*lk-30,H/2-sz*.12,W*.18*lk,2);x.fillRect(W/2+tw/2+30,H/2-sz*.12,W*.18*lk,2);
  kin("//  SYSTEMS ONLINE",W/2,H/2+sz*.55,{t:t-12.4,size:Math.max(16,sz*.16),font:MONO,ls:.45,col:"#9fe9ff",dec:true,st:.035,dur:.3,out});
  if(COMP)kin(`DISPLAY ${(S.n||1)} · LINKED TO CORE`,W/2,H/2+sz*.8,{t:t-13,size:Math.max(12,sz*.09),font:MONO,ls:.3,col:"rgba(160,200,240,.85)",st:.02,dur:.25,out});
  glitch(out>0&&out<1?Math.sin(out*Math.PI):0);}
 // ---- S4 briefing
 if(t>=15.0&&t<22.9){const out=seg(t,22.0,22.6),b=S.brief||{},cards=(b.cards||[]).slice(0,5),hello=`${(b.greeting||"Hello").toUpperCase()}, ${String(S.user||"").toUpperCase()}`.replace(/, $/,"");
  if(COMP){x.fillStyle=`rgba(1,8,24,${.6*seg(t,15,15.6)*(1-out)})`;x.fillRect(0,0,W,H);}
  kin("DAILY BRIEFING",W*.07,H*.2,{t:t-15.3,size:Math.min(56,H*.05),font:UIF,w:300,ls:.12,col:"#fff",al:"l",st:.03,dur:.4,rgbIn:1,out});
  kin(`${hello}  ·  ${b.time||S.time||""}  ·  ${String(b.date||"").toUpperCase()}`,W*.07,H*.2+Math.min(44,H*.04),{t:t-15.8,size:13,font:MONO,ls:.25,col:MC.blue,al:"l",dec:true,st:.012,dur:.2,out});
  if(cards.length){const n=cards.length,f=COMP?Math.min(1.5,W/1300):Math.min(1.45,W/1400),cw2=200*f,ch=170*f,gap=16*f,tot=n*cw2+(n-1)*gap;
   cards.forEach((c,i)=>{const s=16.0+i*.32,u=seg(t,s,s+.7),uo=seg(t,22.0+i*.06,22.45+i*.06);if(u<=0)return;const e=eo(u);
    let px=W/2-tot/2+i*(cw2+gap),py=H*.86-ch-16*f;if(COMP){py=H*.5-ch/2;}
    const z=1+(1-e)*.6;x.save();x.translate(px+cw2/2,py+ch/2+uo*H*.25);x.scale(z,z);x.rotate((1-e)*.12*(i%2?1:-1));card(c,-cw2/2,-ch/2,cw2,ch,e*(1-uo),seg(t,s+.3,s+1.2),"blue");x.restore();});}
  glitch(t>22.3?Math.sin(seg(t,22.3,22.9)*Math.PI)*.9:0);}
 // ---- S5 mode tour
 if(t>=22.6&&t<44.4){const tt=t-T_TOUR;
  if(t<T_TOUR){kin("MODE TOUR",W/2,H/2,{t:t-22.6,size:H*.09,font:BLK,w:900,ls:.3,col:"#fff",st:.03,dur:.25,rgbIn:1.5});}
  else{const k=Math.min(6,(tt/SEGL)|0),u=tt-k*SEGL,m=MODES[k],pm=k?MODES[k-1]:null,tu=u/.55,fade=1-seg(t,43.6,44.3);
   if(pm&&tu<1){world(pm,u+SEGL,fade,cx,cy);}
   x.save();if(tu<1)mask(m,tu,cx,cy);world(m,u,fade,cx,cy);x.restore();transFX(m,tu,cx,cy);
   const nm=MNAME[m],out=seg(u,2.55,2.95),bx=W*.07,by=H*.62,nsz=Math.min(H*.12,W*.08);
   kin(nm[1],bx,by-nsz*.75,{t:u-.25,size:Math.max(12,nsz*.14),font:MONO,ls:.4,col:MC[m],al:"l",st:.02,dur:.2,dec:true,out});
   kin(nm[0],bx,by,{t:u-.3,size:nsz,font:BLK,w:900,ls:.08,col:m=="black"?"#c25050":"#fff",al:"l",st:.045,dur:.35,dir:m=="white"?-1:1,rgbIn:m=="purple"?2:.6,glow:MC[m],out,spread:m=="red"?1.2:0,burst:m=="gold"?1:0});
   kin(nm[2],bx,by+nsz*.68,{t:u-.6,size:Math.max(12,nsz*.15),font:MONO,ls:.2,col:"rgba(230,240,255,.85)",al:"l",st:.012,dur:.2,out});
   txt(`${k+1}/7`,W*.93,H*.2,13,MC[m],"r",MONO,cl(u*3)*(1-out));}}
 // ---- S6 holographic scan sweep (global coordinates, both monitors in sync)
 if(t>=43.9&&t<48.6){const sp=S.span||[me.x,me.x+me.w],gx=sp[0]-300+(sp[1]-sp[0]+600)*eio(seg(t,44.3,47.6)),lx=(gx-me.x)*sc,fade=1-seg(t,48.1,48.6);
  x.save();x.globalAlpha=fade;const tr=W*.35,g=x.createLinearGradient(lx-tr,0,lx,0);g.addColorStop(0,"rgba(95,212,255,0)");g.addColorStop(1,"rgba(95,212,255,.28)");x.fillStyle=g;x.fillRect(lx-tr,0,tr,H);
  x.globalCompositeOperation="lighter";x.fillStyle="#bff4ff";x.shadowColor="#5fd4ff";x.shadowBlur=40;x.fillRect(lx-2,0,4,H);x.shadowBlur=0;
  x.strokeStyle="rgba(95,212,255,.25)";x.lineWidth=1;x.beginPath();for(let y=(t*120)%24;y<H;y+=24){x.moveTo(Math.max(0,lx-tr),y);x.lineTo(lx,y);}x.stroke();x.globalCompositeOperation="source-over";
  const labs=COMP?[[.5,.5,"EMBLEM INTEGRITY 100%"],[.25,.3,"DISPLAY "+(S.n||1)+" · OK"],[.72,.7,"COMPANION LINK · SYNCED"]]:[[.5,.47,"CORE 100%"],[.35,.3,"RINGS 3 / 3"],[.66,.68,"PRIVACY · CAMERA OFF"],[.3,.7,"WAKE WORD · LISTENING"],[.7,.28,"DISPLAYS · 2 LINKED"]];
  labs.forEach(([fx,fy,s])=>{const X=COMP?W*fx:(fx==.5?cx:W*fx),Y=COMP?H*fy:(fy==.47?cy:H*fy);if(lx>X){const a=cl((lx-X)/200);brackets(X,Y,150,46,10,"#5fd4ff",a,1.5);txt(s,X,Y,12,"#e9fbff","c",MONO,a);}});
  const pct=Math.round(100*eio(seg(t,44.3,47.6)));txt(`HOLO SCAN  ${pct}%`,W*.93,H*.2,13,"#9fe9ff","r",MONO,fade);
  if(t>47.5)kin("SCAN COMPLETE · ALL SYSTEMS NOMINAL",W/2,H*.8,{t:t-47.5,size:15,font:MONO,ls:.3,col:"#9fe9ff",dec:true,st:.015,dur:.2,out:seg(t,48.2,48.6)});
  x.restore();glitch(t<44.3?Math.sin(seg(t,43.9,44.3)*Math.PI)*.7:0);}
 // ---- S7 shockwave -> resolve to the core
 if(t>=48.4){const {me:mm}=geo();const gc=COMP?(S.core||[mm.x+mm.w*1.5,mm.h/2]):[mm.x+cx/sc,(mm.y||0)+cy/sc];const lcx=(gc[0]-mm.x)*sc,lcy=(gc[1]-(mm.y||0))*sc;
  const u=seg(t,48.5,50.3),rad=eo(u)*Math.hypot((S.span?S.span[1]-S.span[0]:W/sc),mm.h||H)*sc*1.05,a=1-u;
  if(t<48.9){const f=hit(t,48.5,6);x.fillStyle=`rgba(230,250,255,${.55*f})`;x.fillRect(0,0,W,H);}
  if(u>0&&u<1){x.save();x.globalCompositeOperation="lighter";for(let k=0;k<3;k++){const r=Math.max(0,rad-k*40*sc);x.strokeStyle=k==0?`rgba(235,252,255,${a})`:`rgba(95,212,255,${a*.5})`;x.lineWidth=(k==0?10:24)*(1-u*.7);x.beginPath();x.arc(lcx,lcy,r,0,6.283);x.stroke();}x.restore();}
  if(!COMP)kin("YOUR DESKTOP, AWAKE.",W/2,Math.min(H*.86,cy+Math.min(W,H)*.3),{t:t-49.3,size:Math.min(30,H*.03),font:UIF,w:300,ls:.35,col:"#e9fbff",st:.035,dur:.4,out:seg(t,51.1,51.8)});
  else kin(AN+" ONLINE",W/2,H/2,{t:t-49.6,size:Math.min(64,H*.07),font:BLK,w:900,ls:.3,col:"#e9fbff",st:.05,dur:.4,out:seg(t,51.0,51.7),glow:"#5fd4ff"});
  if(t>50.9&&document.body.classList.contains("i41on"))document.body.classList.remove("i41on");
  if(COMP){root.style.opacity=String(1-seg(t,51.2,52));}else root.style.opacity=String(1-seg(t,51.4,52));}
 // ---- letterbox + HUD (always on top)
 const lb=eo(seg(t,0,.9))*(1-eo(seg(t,50.3,51.3))),bh=H*.105*lb;if(bh>.5){x.fillStyle="#000";x.fillRect(0,0,W,bh);x.fillRect(0,H-bh,W,bh);const ac=MC[md]||MC.blue;x.fillStyle=ac;x.globalAlpha=.6;x.fillRect(0,bh-1,W,1);x.fillRect(0,H-bh,W,1);x.globalAlpha=1;
  const a=seg(t,.6,1.2)*(1-seg(t,50,50.6));let sec=SECT[0][1];SECT.forEach(s=>{if(t>=s[0])sec=s[1];});const fs=Math.max(10,Math.min(13,bh*.14));
  txt(AN+"  //  STARTUP SEQUENCE",W*.03,bh/2,fs,"#e9fbff","l",MONO,a);txt(sec,W*.97,bh/2,fs,ac,"r",MONO,a);
  txt(COMP?`DISPLAY ${S.n||1} · IN SYNC WITH CORE`:`SEQ T+${t.toFixed(1).padStart(4,"0")}s`,W*.03,H-bh/2,fs,"rgba(160,200,240,.8)","l",MONO,a);
  if(!COMP)txt("CLICK · ESC · SAY \u201CSKIP\u201D",W*.97,H-bh/2,fs,"rgba(160,200,240,.8)","r",MONO,a);
  x.fillStyle=ac;x.globalAlpha=.8*a;x.fillRect(W*.3,H-bh/2-1,W*.4*cl(t/DUR),2);x.globalAlpha=.2*a;x.fillRect(W*.3,H-bh/2-1,W*.4,2);x.globalAlpha=1;}}

function start(d){S=d;ended=false;fr={n:0,last:0,slow:0,worst:0};modeSet="";EMB=null;S.tick=S.tick||[];
 if(!COMP){I.on=true;I.rst=false;window.__v4intro=true;const b=document.getElementById("v4boot");if(b)b.classList.remove("on");}
 root.style.opacity="1";root.classList.add("on");document.body.classList.add("i41on");fit();cancelAnimationFrame(raf);raf=requestAnimationFrame(frame);
 if(!COMP)LOGF("intro41: start (t0 offset "+Math.round(Date.now()-d.t0)+" ms, "+W+"x"+H+")");return 1;}
function end(why){if(ended)return;ended=true;cancelAnimationFrame(raf);x.clearRect(0,0,W,H);root.classList.remove("on");document.body.classList.remove("i41on");
 if(!COMP){I.on=false;I.rst=true;window.__v4intro=false;if(S&&S.mode)document.body.dataset.mode=S.mode;window.__tintM=null;
  const sec=(fr.n/Math.max(.001,Math.min(DUR,(Date.now()-(S?S.t0:Date.now()))/1000)));
  LOGF(`intro41: end (${why}) frames=${fr.n} avg=${sec.toFixed(1)}fps slow(>20ms)=${fr.slow} worst=${Math.round(fr.worst)}ms`);}
 S=null;}
window.i41=d=>{if(!d)return 0;if(d.on===false){end("stopped");return 1;}return start(d);};
const skip=()=>{if(!S||COMP)return;end("skipped");try{A().v40_skip()}catch(e){}};
root.addEventListener("mousedown",skip);addEventListener("keydown",e=>{if(e.key=="Escape"&&S)skip();});
const prev=window.vexOn;window.vexOn=function(ev,d){if(ev=="intro41"){window.i41(d);return;}if(ev=="intro"&&d&&d.on===false&&S)end("stopped");return prev&&prev.apply(this,arguments);};
})();
