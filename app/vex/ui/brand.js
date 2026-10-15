/* Public build: shows the assistant's chosen name everywhere the UI says "Vex" (text, titles, canvas text). */
(function(){
const N=(window.__AN||"Vex").trim()||"Vex";if(N=="Vex")return;
const U=N.toUpperCase(),reU=/\bVEX\b/g,reN=/\bVex\b/g;
const fix=s=>(s&&(s.indexOf("VEX")>=0||s.indexOf("Vex")>=0))?s.replace(reU,U).replace(reN,N):s;
window.vexBrand=fix;
for(const P of [CanvasRenderingContext2D.prototype]){for(const f of ["fillText","strokeText","measureText"]){const o=P[f];P[f]=function(t,...a){return o.call(this,typeof t=="string"?fix(t):t,...a);};}}
const SKIP={SCRIPT:1,STYLE:1,TEXTAREA:1,INPUT:1};
function walk(n){if(!n)return;if(n.nodeType==3){const v=n.nodeValue,w=fix(v);if(w!==v)n.nodeValue=w;return;}
 if(n.nodeType!=1||SKIP[n.nodeName])return;
 if(n.nodeName=="IMG"&&(n.getAttribute("src")||"").indexOf("wordmark.svg")>=0){const h=n.style.height||(n.getAttribute("height")?n.getAttribute("height")+"px":"1em"),sp=document.createElement("span");
  sp.textContent=U;sp.style.cssText="font-family:VexMono,monospace;letter-spacing:.18em;color:#e9fbff;font-weight:700;line-height:1;display:inline-block;font-size:"+(h=="1em"?"1em":"calc("+h+" * .8)");n.replaceWith(sp);return;}
 for(const at of ["title","placeholder","aria-label"]){const v=n.getAttribute&&n.getAttribute(at);if(v){const w=fix(v);if(w!==v)n.setAttribute(at,w);}}
 for(let c=n.firstChild;c;c=c.nextSibling)walk(c);}
function all(){document.title=fix(document.title);walk(document.body);}
let q=[],t=0;
const mo=new MutationObserver(ms=>{for(const m of ms){if(m.type=="characterData")q.push(m.target);else m.addedNodes.forEach(x=>q.push(x));}
 if(!t)t=requestAnimationFrame(()=>{t=0;const L=q;q=[];mo.disconnect();L.forEach(walk);mo.observe(document.documentElement,{subtree:true,childList:true,characterData:true});});});
function go(){all();mo.observe(document.documentElement,{subtree:true,childList:true,characterData:true});}
if(document.body)go();else document.addEventListener("DOMContentLoaded",go);
})();
