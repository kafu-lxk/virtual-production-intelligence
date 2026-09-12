let articles=[];
const $=s=>document.querySelector(s);
async function load(){
  try{
    const r=await fetch("data/articles.json");
    articles=await r.json();
  }catch(e){
    articles=[];
  }
  render();
}
function checked(cls){return [...document.querySelectorAll("."+cls+":checked")].map(x=>x.value)}
function render(){
  const q=$("#search").value.trim().toLowerCase();
  const cats=checked("cat"), regions=checked("region");
  const filtered=articles.filter(a=>{
    const text=[a.title,a.summary,a.source,a.country,...(a.categories||[]),...(a.technologies||[])].join(" ").toLowerCase();
    const hit=!q||text.includes(q);
    const cat=!cats.length||cats.some(x=>(a.categories||[]).includes(x));
    const reg=!regions.length||regions.includes(a.country);
    return hit&&cat&&reg;
  });
  $("#count").textContent=filtered.length;
  $("#articles").innerHTML=filtered.length?filtered.map(a=>`
    <article class="card">
      <h2>${esc(a.title)}</h2>
      <div class="meta">${esc(a.date)} ・ ${esc(a.country)} ・ ${esc(a.source)}</div>
      <div class="tags">${[...(a.categories||[]),...(a.technologies||[])].map(x=>`<span class="tag">${esc(x)}</span>`).join("")}</div>
      <div class="summary">${esc(a.summary)}</div>
      <div class="source"><a href="${esc(a.url)}" target="_blank" rel="noopener">Original source ↗</a></div>
    </article>`).join(""):`<div class="empty">条件に一致する情報がありません。</div>`;
}
function esc(v){return String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}
$("#search").addEventListener("input",render);
document.querySelectorAll(".cat,.region").forEach(x=>x.addEventListener("change",render));
$("#clear").addEventListener("click",()=>{document.querySelectorAll("input[type=checkbox]").forEach(x=>x.checked=false);$("#search").value="";render()});
load();
