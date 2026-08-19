/* 天空之城 Online 攻略資料庫 */
'use strict';

// ---------- 中文對照 ----------
const T = {
  job:{Fighter:'戰士',Archer:'弓手',Mage:'法師',Cleric:'聖職'},
  attr:{Earth:'地',Fire:'火',Water:'水',Wind:'風',Holy:'聖',Dark:'暗',Ice:'冰',
        Lightning:'雷',Other:'無',None:'—',Animal:'動物',Demon:'惡魔',Undead:'不死',
        Dragon:'龍',Ghost:'幽靈',Turtle:'龜',Guard:'守衛',Plant:'植物'},
  temper:{Aggresive:'主動',Aggressive:'主動',Passive:'被動',Neutral:'中立'},
  rarity:{Normal:'普通',Rare:'稀有'},
  part:{Helm:'頭盔',Cloth:'衣服',Pants:'褲子',Gloves:'手套',Shoes:'鞋子'},
  move:{Land:'地面',Flying:'飛行'},
  sk:{'Skills Type':'類型','Damage':'傷害','Attack Range':'攻擊距離','Delay Skill':'冷卻',
      'Target':'目標','MP Requirement':'消耗 MP','Item Required':'需求武器',
      'Need Level':'需求等級','Need Class':'需求職業','Duration':'持續時間',
      'Effect':'效果','Range':'範圍','Cast Time':'施法時間'},
};
const tr=(m,v)=>(v&&m[v])||v||'';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=s=>{const m=String(s??'').replace(/[.,](?=\d{3}\b)/g,'').match(/-?\d+(\.\d+)?/);return m?+m[0]:null};
const dmgAvg=s=>{const m=String(s??'').match(/(\d+)\s*~\s*(\d+)/);return m?(+m[1]+ +m[2])/2:num(s)};

// ---------- 資料載入 ----------
const CACHE={}, IMGMAP={};
async function load(name){
  if(CACHE[name]) return CACHE[name];
  const r=await fetch(`data/${name}.json`);
  if(!r.ok) throw new Error(`載入 ${name} 失敗`);
  return CACHE[name]=await r.json();
}
const imgTag=(f,cls='ico')=>{
  const m=IMGMAP[f];
  return m?`<img class="${cls}" src="img/${m}" alt="" loading="lazy">`:'';
};

// ---------- 排序表格元件 ----------
function tableSort(tbl){
  tbl.querySelectorAll('th[data-k]').forEach(th=>{
    th.onclick=()=>{
      const k=th.dataset.k, tb=tbl.tBodies[0];
      const desc=th.classList.contains('s')&&!th.classList.contains('d');
      tbl.querySelectorAll('th').forEach(x=>x.classList.remove('s','d'));
      th.classList.add('s'); if(desc) th.classList.add('d');
      const rows=[...tb.querySelectorAll('tr[data-v]')];
      const groups=rows.map(r=>[r, r.nextElementSibling&&r.nextElementSibling.classList.contains('detail')?r.nextElementSibling:null]);
      groups.sort(([a],[b])=>{
        let x=a.dataset[k]??'', y=b.dataset[k]??'';
        const nx=parseFloat(x), ny=parseFloat(y);
        let c = (!isNaN(nx)&&!isNaN(ny)) ? nx-ny : String(x).localeCompare(String(y));
        return desc?-c:c;
      });
      groups.forEach(([r,d])=>{tb.appendChild(r); if(d) tb.appendChild(d)});
    };
  });
}
function expandRows(tbl){
  tbl.querySelectorAll('tr.exp').forEach(tr=>{
    tr.onclick=e=>{
      if(e.target.tagName==='A') return;
      const d=tr.nextElementSibling;
      if(!d||!d.classList.contains('detail'))return;
      const open=d.style.display!=='none';
      d.style.display=open?'none':'table-row';
      tr.classList.toggle('open',!open);
    };
  });
}

// ---------- 視圖 ----------
const V={};

V['']=V['home']=async()=>{
  const [w,m,s]=await Promise.all([load('weapons'),load('monsters'),load('skills')]);
  return `
  <h1>天空之城 Online 攻略資料庫</h1>
  <p class="sub">Master of Fantasy · 非官方玩家攻略站</p>
  <div class="note">
    <b>這個站在幹嘛？</b> 原始 wiki 是印尼文、資料散在幾百個頁面、表格不能排序也不能篩選。
    這裡把全站 ${w.length+m.length+s.length}+ 筆資料重新整理成<b>可搜尋、可篩選、可排序</b>的資料庫，
    並加上 wiki 沒有的 <a href="#/drops">掉落物反查</a>。
  </div>
  <h2>四大職業</h2>
  <div class="grid">${['Fighter','Archer','Mage','Cleric'].map(j=>`
    <a class="card jobcard ${j}" href="#/jobs?j=${j}">
      <h3>${T.job[j]} <small style="color:var(--tx3);font-weight:400">${j}</small></h3>
      <p>可用武器 ${w.filter(x=>x.jobs.includes(j)).length} 把 · 技能 ${s.filter(x=>x.job===j).length} 個</p>
    </a>`).join('')}</div>
  <h2>資料總覽</h2>
  <div class="grid">
    <a class="card" href="#/weapons"><h3>⚔️ 武器 ${w.length}</h3><p>13 種類型，可依職業、稀有度、等級篩選，傷害排序</p></a>
    <a class="card" href="#/armors"><h3>🛡️ 防具飾品 590</h3><p>各職業防具 400 件、盾 28 面、飾品 162 件</p></a>
    <a class="card" href="#/skills"><h3>✨ 技能 ${s.length}</h3><p>四職業全技能，含 I～X 各等級數值</p></a>
    <a class="card" href="#/monsters"><h3>👹 怪物圖鑑 ${m.length}</h3><p>等級、HP、屬性、出沒地、完整掉落表</p></a>
    <a class="card" href="#/drops"><h3>🔍 掉落物反查</h3><p>輸入道具名，反查哪些怪會掉 —— wiki 沒有這功能</p></a>
    <a class="card" href="#/attr"><h3>🔥 屬性相剋</h3><p>武器屬性 vs 怪物屬性完整矩陣，附「打這種怪帶什麼」反查</p></a>
    <a class="card" href="#/systems"><h3>⚙️ 遊戲系統</h3><p>強化、製作、藥水、狀態異常、轉職考試等機制資料表</p></a>
    <a class="card" href="#/pets"><h3>🐾 寵物 8</h3><p>各寵物 Lv.1～10 加成完整對照</p></a>
    <a class="card" href="#/npcs"><h3>💬 NPC 與任務</h3><p>64 位 NPC，含任務等級、目標、獎勵</p></a>
    <a class="card" href="#/locations"><h3>🗺️ 地點</h3><p>城鎮、地城、區域與所屬 NPC</p></a>
  </div>`;
};

// --- 職業 ---
V['jobs']=async(p)=>{
  const [w,s]=await Promise.all([load('weapons'),load('skills')]);
  const TREE={
    Fighter:['Fighter','Knight','Berserker / Templar','Warlord / Paladin','Conqueror / Crusader'],
    Archer:['Archer','Hunter','Ranger / Sniper','Predator / Gunner','Beast Master / Destroyer'],
    Mage:['Mage','Wizard','Sorcerer / Warlock','Archmage / Necromancer','Magister / Lich'],
    Cleric:['Cleric','Priest','Saint / Paladin','Holy Avenger / Bishop','Cardinal / Arc Bishop'],
  };
  const cur=p.j||'Fighter';
  const ws=w.filter(x=>x.jobs.includes(cur)), ss=s.filter(x=>x.job===cur);
  const byType={}; ws.forEach(x=>(byType[x.group]=byType[x.group]||[]).push(x));
  return `
  <h1>職業</h1>
  <p class="sub">四大職業的轉職路線、可用武器與技能。轉職樹依 wiki 的 1～5 轉資料整理。</p>
  <div class="chips" style="margin-bottom:18px">${Object.keys(T.job).map(j=>
    `<a class="chip ${j===cur?'on':''}" href="#/jobs?j=${j}">${T.job[j]}</a>`).join('')}</div>
  <h2>${T.job[cur]} ${cur}</h2>
  <h3>轉職路線</h3>
  <div class="tree">${TREE[cur].map((t,i)=>`${i?' → ':''}<b>${i+1}轉：</b>${esc(t)}`).join('<br>')}</div>
  <h3>可用武器（${ws.length} 把）</h3>
  <div class="chips">${Object.entries(byType).sort((a,b)=>b[1].length-a[1].length).map(([g,arr])=>
    `<a class="chip" href="#/weapons?g=${encodeURIComponent(g)}">${esc(g)} ${arr.length}</a>`).join('')}</div>
  <h3>技能（${ss.length} 個）</h3>
  <div class="chips">${ss.map(x=>
    `<a class="chip" href="#/skills?q=${encodeURIComponent(x.name)}">${esc(x.name)}</a>`).join('')}</div>`;
};

// --- 武器 ---
V['weapons']=async(p)=>{
  const w=await load('weapons');
  const groups=[...new Set(w.map(x=>x.group))].sort();
  return {html:`
  <h1>武器資料庫</h1>
  <p class="sub">${w.length} 把武器。點欄位標題可排序，「傷害」用平均值排。</p>
  <div class="filters">
    <select id="fj"><option value="">全部職業</option>${Object.entries(T.job).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select>
    <select id="fg"><option value="">全部類型</option>${groups.map(g=>`<option value="${esc(g)}"${p.g===g?' selected':''}>${esc(g)}</option>`).join('')}</select>
    <select id="fr"><option value="">全部稀有度</option><option value="Rare">稀有</option><option value="Normal">普通</option></select>
    <input type="number" id="fmin" placeholder="等級 ≥" style="width:92px">
    <input type="number" id="fmax" placeholder="等級 ≤" style="width:92px">
    <select id="fa"><option value="">全部屬性</option>${[...new Set(w.map(x=>x.attr))].filter(Boolean).sort().map(a=>`<option value="${esc(a)}"${p.a===a?' selected':''}>${tr(T.attr,a)}</option>`).join('')}</select>
    <input type="text" id="fq" placeholder="名稱關鍵字" value="${esc(p.q||'')}">
    <span class="cnt" id="cnt"></span>
  </div>
  <div class="tw"><table id="tb">
    <thead><tr>
      <th class="hide-m"></th><th data-k="name">武器名稱</th><th data-k="group">類型</th>
      <th data-k="rar">稀有</th><th data-k="lv" class="n">等級</th><th data-k="dmg" class="n">傷害</th>
      <th data-k="spd" class="n hide-m">攻速</th><th data-k="rng" class="n hide-m">射程</th>
      <th data-k="attr" class="hide-m">屬性</th><th data-k="price" class="n hide-m">價格</th><th>效果</th>
    </tr></thead><tbody></tbody>
  </table></div>`,
  init(){
    const tb=document.querySelector('#tb tbody');
    const f=()=>{
      const j=fj.value,g=fg.value,r=fr.value,a=fa.value,mn=+fmin.value||0,mx=+fmax.value||999,q=fq.value.toLowerCase();
      const rows=w.filter(x=>(!j||x.jobs.includes(j))&&(!g||x.group===g)&&(!r||x.rarity===r)
        &&(!a||x.attr===a)&&(x.lv==null||(x.lv>=mn&&x.lv<=mx))&&(!q||x.name.toLowerCase().includes(q)));
      cnt.textContent=`${rows.length} 把`;
      tb.innerHTML=rows.map(x=>`<tr data-v data-name="${esc(x.name)}" data-group="${esc(x.group)}"
        data-rar="${x.rarity==='Rare'?1:0}" data-lv="${x.lv??0}" data-dmg="${dmgAvg(x.dmg)??0}"
        data-spd="${num(x.spd)??0}" data-rng="${num(x.rng)??0}" data-attr="${esc(x.attr)}" data-price="${num(x.price)??0}">
        <td class="hide-m"></td>
        <td class="nm">${esc(x.name)}<span class="kr">${x.jobs.map(j=>T.job[j]).join('・')}</span></td>
        <td>${esc(x.group)}</td>
        <td><span class="t ${x.rarity==='Rare'?'rare':'norm'}">${tr(T.rarity,x.rarity)||'—'}</span></td>
        <td class="n">${x.lv??'—'}</td><td class="n">${esc(x.dmg)||'—'}</td>
        <td class="n hide-m">${esc(x.spd)||'—'}</td><td class="n hide-m">${esc(x.rng)||'—'}</td>
        <td class="hide-m">${tr(T.attr,x.attr)||'—'}</td>
        <td class="n hide-m">${esc(String(x.price).replace(' Libi',''))||'—'}</td>
        <td>${esc(x.eff==='None'?'':x.eff)}${x.add&&x.add!=='None'?'<br><span style="color:var(--gold2);font-size:12px">'+esc(x.add)+'</span>':''}</td>
      </tr>`).join('')||'<tr><td colspan="11" class="empty">沒有符合條件的武器</td></tr>';
      tableSort(tb.closest('table'));
    };
    ['fj','fg','fr','fa','fmin','fmax'].forEach(i=>document.getElementById(i).onchange=f);
    fq.oninput=f; f();
  }};
};

// --- 防具 / 飾品 ---
V['armors']=async()=>{
  const [a,c]=await Promise.all([load('armors'),load('accessories')]);
  const all=[...a,...c];
  return {html:`
  <h1>防具與飾品</h1>
  <p class="sub">${a.length} 件防具（含 ${a.filter(x=>x.group==='Shield').length} 面盾）與 ${c.length} 件飾品。</p>
  <div class="filters">
    <select id="fj"><option value="">全部職業</option>${Object.entries(T.job).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select>
    <select id="fp"><option value="">全部部位</option>${[...new Set(all.map(x=>x.part||x.group))].filter(Boolean).map(p=>`<option value="${esc(p)}">${tr(T.part,p)}</option>`).join('')}</select>
    <input type="number" id="fmin" placeholder="等級 ≥" style="width:92px">
    <input type="number" id="fmax" placeholder="等級 ≤" style="width:92px">
    <input type="text" id="fq" placeholder="名稱關鍵字">
    <span class="cnt" id="cnt"></span>
  </div>
  <div class="tw"><table id="tb">
    <thead><tr><th data-k="name">名稱</th><th data-k="part">部位</th><th data-k="job" class="hide-m">職業</th>
    <th data-k="lv" class="n">等級</th><th data-k="def" class="n">防禦</th>
    <th data-k="price" class="n hide-m">價格</th><th>效果</th></tr></thead><tbody></tbody>
  </table></div>`,
  init(){
    const tb=document.querySelector('#tb tbody');
    const f=()=>{
      const j=fj.value,p=fp.value,mn=+fmin.value||0,mx=+fmax.value||999,q=fq.value.toLowerCase();
      const rows=all.filter(x=>(!j||x.jobs.includes(j))&&(!p||(x.part||x.group)===p)
        &&(x.lv==null||(x.lv>=mn&&x.lv<=mx))&&(!q||x.name.toLowerCase().includes(q)));
      cnt.textContent=`${rows.length} 件`;
      tb.innerHTML=rows.map(x=>`<tr data-v data-name="${esc(x.name)}" data-part="${esc(x.part||x.group)}"
        data-job="${esc(x.jobs.join())}" data-lv="${x.lv??0}" data-def="${x.def??0}" data-price="${num(x.price)??0}">
        <td class="nm">${esc(x.name)}</td><td>${tr(T.part,x.part)||esc(x.group)}</td>
        <td class="hide-m">${x.jobs.length===4?'全職業':x.jobs.map(j=>`<span class="t ${j}">${T.job[j]}</span>`).join(' ')}</td>
        <td class="n">${x.lv??'—'}</td><td class="n">${x.def??'—'}</td>
        <td class="n hide-m">${esc(String(x.price).replace(' Libi',''))||'—'}</td>
        <td>${esc(x.eff==='None'?'':x.eff)}</td></tr>`).join('')||'<tr><td colspan="7" class="empty">沒有符合條件的裝備</td></tr>';
      tableSort(tb.closest('table'));
    };
    ['fj','fp','fmin','fmax'].forEach(i=>document.getElementById(i).onchange=f);
    fq.oninput=f; f();
  }};
};

// --- 技能 ---
V['skills']=async(p)=>{
  const s=await load('skills');
  return {html:`
  <h1>技能資料庫</h1>
  <p class="sub">${s.length} 個技能。點任一列展開該技能 I～X 各等級的完整數值。</p>
  <div class="filters">
    <div class="chips" id="cj">
      <button class="chip on" data-j="">全部</button>
      ${Object.entries(T.job).map(([k,v])=>`<button class="chip" data-j="${k}">${v}</button>`).join('')}
    </div>
    <select id="ft"><option value="">主動＋被動</option><option value="Active">主動</option><option value="Passive">被動</option></select>
    <input type="text" id="fq" placeholder="技能名稱" value="${esc(p.q||'')}">
    <span class="cnt" id="cnt"></span>
  </div>
  <div class="tw"><table id="tb">
    <thead><tr><th data-k="name">技能</th><th data-k="job">職業</th><th data-k="type">類型</th>
    <th data-k="lv" class="n">最低等級</th><th data-k="ranks" class="n hide-m">階級數</th><th class="hide-m">說明（原文）</th></tr></thead>
    <tbody></tbody></table></div>`,
  init(){
    let job='';
    const tb=document.querySelector('#tb tbody');
    const f=()=>{
      const t=ft.value,q=fq.value.toLowerCase();
      const rows=s.filter(x=>(!job||x.job===job)&&(!t||x.type===t)&&(!q||x.name.toLowerCase().includes(q)));
      cnt.textContent=`${rows.length} 個`;
      tb.innerHTML=rows.map(x=>{
        const lv=x.levels.length?num(x.levels[0].f['Need Level']):null;
        const det=x.levels.map(L=>`<div class="lvb"><b>${esc(L.name)}</b><dl>${
          Object.entries(L.f).filter(([k])=>k!=='Need Class').map(([k,v])=>
            `<dt>${esc(tr(T.sk,k))}</dt><dd>${esc(String(v).replace(' Detik',' 秒'))}</dd>`).join('')}</dl></div>`).join('');
        return `<tr data-v class="exp" data-name="${esc(x.name)}" data-job="${esc(x.job)}" data-type="${esc(x.type)}"
          data-lv="${lv??0}" data-ranks="${x.levels.length}">
          <td class="nm">${esc(x.name)}<span class="kr">${esc(x.kr)}</span></td>
          <td><span class="t ${x.job}">${T.job[x.job]||'—'}</span></td>
          <td>${x.type==='Active'?'主動':'被動'}</td>
          <td class="n">${lv??'—'}</td><td class="n hide-m">${x.levels.length}</td>
          <td class="hide-m" style="color:var(--tx3);font-size:12px">${esc((x.desc||'').slice(0,60))}</td></tr>
        <tr class="detail" style="display:none"><td colspan="6">
          ${x.desc?`<p style="color:var(--tx2);margin-bottom:10px;font-size:13px">${esc(x.desc)}</p>`:''}
          <div class="lv">${det||'<span style="color:var(--tx3)">此技能沒有分級數值</span>'}</div></td></tr>`;
      }).join('')||'<tr><td colspan="6" class="empty">找不到技能</td></tr>';
      tableSort(tb.closest('table')); expandRows(tb.closest('table'));
    };
    cj.onclick=e=>{if(!e.target.dataset.j&&e.target.dataset.j!=='')return;
      [...cj.children].forEach(c=>c.classList.remove('on'));e.target.classList.add('on');job=e.target.dataset.j;f()};
    ft.onchange=f; fq.oninput=f; f();
  }};
};

// --- 怪物 ---
V['monsters']=async(p)=>{
  const m=await load('monsters');
  const regions=[...new Set(m.flatMap(x=>x.regions))].sort();
  return {html:`
  <h1>怪物圖鑑</h1>
  <p class="sub">${m.length} 隻怪物。點任一列展開掉落物清單。部分怪物 wiki 未記錄 HP，顯示為「—」。</p>
  <div class="filters">
    <select id="fr"><option value="">全部地區</option>${regions.map(r=>`<option value="${esc(r)}">${esc(r)}</option>`).join('')}</select>
    <select id="fa"><option value="">全部屬性</option>${[...new Set(m.map(x=>x.attr))].filter(Boolean).sort().map(a=>`<option value="${esc(a)}">${tr(T.attr,a)}</option>`).join('')}</select>
    <select id="ft"><option value="">全部性格</option><option value="Aggresive">主動攻擊</option><option value="Passive">被動</option><option value="Neutral">中立</option></select>
    <select id="fb"><option value="">全部</option><option value="1">只看 Boss</option></select>
    <input type="number" id="fmin" placeholder="等級 ≥" style="width:92px">
    <input type="number" id="fmax" placeholder="等級 ≤" style="width:92px">
    <input type="text" id="fq" placeholder="名稱關鍵字" value="${esc(p.q||'')}">
    <span class="cnt" id="cnt"></span>
  </div>
  <div class="tw"><table id="tb">
    <thead><tr><th></th><th data-k="name">怪物</th><th data-k="lv" class="n">等級</th>
    <th data-k="hp" class="n">HP</th><th data-k="temper">性格</th><th data-k="attr" class="hide-m">屬性</th>
    <th data-k="move" class="hide-m">移動</th><th data-k="loc">出沒地</th><th data-k="drops" class="n hide-m">掉落</th></tr></thead>
    <tbody></tbody></table></div>`,
  init(){
    const tb=document.querySelector('#tb tbody');
    const f=()=>{
      const r=fr.value,a=fa.value,t=ft.value,b=fb.value,mn=+fmin.value||0,mx=+fmax.value||999,q=fq.value.toLowerCase();
      const rows=m.filter(x=>(!r||x.regions.includes(r))&&(!a||x.attr===a)&&(!t||x.temper===t)
        &&(!b||x.boss)&&(x.level==null||(x.level>=mn&&x.level<=mx))&&(!q||x.name.toLowerCase().includes(q)));
      cnt.textContent=`${rows.length} 隻`;
      tb.innerHTML=rows.map(x=>`
        <tr data-v class="exp" data-name="${esc(x.name)}" data-lv="${x.level??0}" data-hp="${x.hp??0}"
          data-temper="${esc(x.temper)}" data-attr="${esc(x.attr)}" data-move="${esc(x.move)}"
          data-loc="${esc(x.loc)}" data-drops="${x.drops.length}">
          <td>${imgTag(x.img)}</td>
          <td class="nm">${esc(x.name)}${x.boss?' <span class="t boss">BOSS</span>':x.mini?' <span class="t mini">精英</span>':''}<span class="kr">${esc(x.kr)}</span></td>
          <td class="n">${x.level??'—'}</td><td class="n">${x.hp??'—'}</td>
          <td><span class="t ${x.temper==='Aggresive'?'ag':x.temper==='Neutral'?'ne':'pa'}">${tr(T.temper,x.temper)||'—'}</span></td>
          <td class="hide-m">${tr(T.attr,x.attr)||'—'}</td><td class="hide-m">${tr(T.move,x.move)||'—'}</td>
          <td>${esc(x.loc)||'—'}</td><td class="n hide-m">${x.drops.length||'—'}</td></tr>
        <tr class="detail" style="display:none"><td colspan="9">
          ${x.desc?`<p style="color:var(--tx2);font-size:13px;margin-bottom:10px">${esc(x.desc)}</p>`:''}
          ${x.drops.length?`<div class="dl">${x.drops.map(d=>
            `<a class="${d.rarity==='Rare'?'r':''}" href="#/drops?q=${encodeURIComponent(d.name)}">${esc(d.name)}${d.rarity==='Rare'?' ★':''}</a>`).join('')}</div>`
            :'<span style="color:var(--tx3)">wiki 未記錄掉落物</span>'}</td></tr>`).join('')
        ||'<tr><td colspan="9" class="empty">沒有符合條件的怪物</td></tr>';
      tableSort(tb.closest('table')); expandRows(tb.closest('table'));
    };
    ['fr','fa','ft','fb','fmin','fmax'].forEach(i=>document.getElementById(i).onchange=f);
    fq.oninput=f; f();
  }};
};

// --- 掉落物反查 ---
V['drops']=async(p)=>{
  const di=await load('drop_index');
  const keys=Object.keys(di);
  return {html:`
  <h1>掉落物反查</h1>
  <p class="sub">輸入道具名稱，反查哪些怪物會掉。收錄 ${keys.length} 種道具、來自 ${new Set(Object.values(di).flat().map(x=>x.mon)).size} 隻怪物。這是原始 wiki 沒有的功能。</p>
  <div class="filters">
    <input type="text" id="fq" placeholder="例：Core、Cross、Herbs…" value="${esc(p.q||'')}" style="min-width:260px">
    <select id="fr"><option value="">全部稀有度</option><option value="Rare">只看稀有</option><option value="Common">只看普通</option></select>
    <span class="cnt" id="cnt"></span>
  </div>
  <div id="out"></div>`,
  init(){
    const f=()=>{
      const q=fq.value.trim().toLowerCase(), r=fr.value;
      if(!q){out.innerHTML='<div class="empty">在上方輸入道具名稱開始查詢<br><span style="font-size:12px">試試 Core、Cross、Stone</span></div>';cnt.textContent='';return}
      let ks=keys.filter(k=>k.toLowerCase().includes(q));
      const res=ks.map(k=>[k,di[k].filter(x=>!r||x.rarity===r)]).filter(([,v])=>v.length).slice(0,120);
      cnt.textContent=`${res.length} 種道具`;
      out.innerHTML=res.length?res.map(([k,v])=>`
        <h3>${esc(k)} <span style="color:var(--tx3);font-weight:400;font-size:12px">${v.length} 個來源</span></h3>
        <div class="tw"><table><thead><tr><th>怪物</th><th class="n">等級</th><th>出沒地</th><th>稀有度</th></tr></thead>
        <tbody>${v.sort((a,b)=>(a.lv??0)-(b.lv??0)).map(x=>`<tr>
          <td class="nm"><a href="#/monsters?q=${encodeURIComponent(x.mon)}">${esc(x.mon)}</a></td>
          <td class="n">${x.lv??'—'}</td><td>${esc(x.loc)||'—'}</td>
          <td><span class="t ${x.rarity==='Rare'?'rare':'norm'}">${x.rarity==='Rare'?'稀有':'普通'}</span></td>
        </tr>`).join('')}</tbody></table></div>`).join('')
        :'<div class="empty">查無此道具</div>';
    };
    fq.oninput=f; fr.onchange=f; f(); fq.focus();
  }};
};

// --- 寵物 ---
V['pets']=async()=>{
  const p=await load('pets');
  return `<h1>寵物</h1>
  <p class="sub">共 ${p.length} 隻。寵物由商城購買（Ghost 為初始寵），從蛋開始養到 Lv.10 才有滿加成。
  另有 5 種技能書（HP/MP 回復、自動拾取、命中光環、防禦光環）與品種無關，任何寵物最多同時掛 4 個。</p>
  <div class="tw"><table><thead><tr><th>寵物</th><th>屬性</th><th>Lv.1</th><th>Lv.5</th><th>Lv.10（滿級）</th></tr></thead>
  <tbody>${p.map(x=>{
    const g=n=>{const e=x.eff.find(y=>y.lv===n);return e?esc(String(e.e).replace(/\s*Detik/g,' 秒')):'—'};
    return `<tr><td class="nm">${imgTag(x.img)}${esc(x.name)}<span class="kr">${esc(x.kr)}</span></td>
    <td>${tr(T.attr,x.attr)||'—'}</td><td>${g(1)}</td><td>${g(5)}</td>
    <td style="color:var(--gold2);font-weight:600">${g(10)}</td></tr>`}).join('')}</tbody></table></div>
  <div class="note"><b>選寵建議：</b>輸出向看 <b>Penguin</b>（+10% 技能攻擊）或 <b>Dino</b>（+10% 傷害）；
  補職與需要高頻施法的看 <b>Devil Jean</b>（技能延遲 -0.1 秒、+5% 防禦），因為延遲縮減對治療也生效。
  <b>Tinkerbell</b>（+28% 掉寶率）是打寶用。<b>Ghost</b> 無任何效果且不能使用寵物技能。</div>`;
};

// --- NPC ---
V['npcs']=async()=>{
  const n=await load('npcs');
  const withQ=n.filter(x=>x.quests.length);
  return {html:`<h1>NPC 與任務</h1>
  <p class="sub">${n.length} 位 NPC，其中 ${withQ.length} 位有任務（共 ${n.reduce((s,x)=>s+x.quests.length,0)} 個）。點有任務的 NPC 展開。</p>
  <div class="filters">
    <select id="fq2"><option value="">全部 NPC</option><option value="1">只看有任務的</option></select>
    <input type="text" id="fq" placeholder="NPC 或地點">
    <span class="cnt" id="cnt"></span>
  </div>
  <div class="tw"><table id="tb"><thead><tr><th></th><th data-k="name">NPC</th><th data-k="loc">所在地</th>
  <th class="hide-m">職務</th><th data-k="qn" class="n">任務數</th></tr></thead><tbody></tbody></table></div>`,
  init(){
    const tb=document.querySelector('#tb tbody');
    const f=()=>{
      const only=fq2.value,q=fq.value.toLowerCase();
      const rows=n.filter(x=>(!only||x.quests.length)&&(!q||x.name.toLowerCase().includes(q)||(x.loc||'').toLowerCase().includes(q)));
      cnt.textContent=`${rows.length} 位`;
      tb.innerHTML=rows.map(x=>`
        <tr data-v class="${x.quests.length?'exp':''}" data-name="${esc(x.name)}" data-loc="${esc(x.loc)}" data-qn="${x.quests.length}">
          <td>${imgTag(x.img)}</td>
          <td class="nm">${esc(x.name)}<span class="kr">${esc(x.kr)}</span></td>
          <td>${esc(x.loc)||'—'}</td><td class="hide-m" style="color:var(--tx2);font-size:12px">${esc((x.job||'').slice(0,40))}</td>
          <td class="n">${x.quests.length||'—'}</td></tr>
        ${x.quests.length?`<tr class="detail" style="display:none"><td colspan="5">
          <div class="tw"><table><thead><tr><th>任務</th><th class="n">等級</th><th>目標</th><th>獎勵</th></tr></thead>
          <tbody>${x.quests.map(qq=>`<tr><td class="nm">${esc(qq.name)}</td><td class="n">${qq.lv??'—'}</td>
          <td style="font-size:12px;color:var(--tx2)">${esc(qq.mission)}</td>
          <td style="font-size:12px">${esc(qq.reward)}</td></tr>`).join('')}</tbody></table></div></td></tr>`:''}`).join('')
        ||'<tr><td colspan="5" class="empty">查無 NPC</td></tr>';
      tableSort(tb.closest('table')); expandRows(tb.closest('table'));
    };
    fq2.onchange=f; fq.oninput=f; f();
  }};
};

// --- 地點 ---
V['locations']=async()=>{
  const l=await load('locations');
  return `<h1>地點</h1><p class="sub">${l.length} 個城鎮、地城與區域。</p>
  <div class="grid">${l.map(x=>`<div class="card"><h3>${esc(x.name)}</h3>
    ${x.kr?`<p style="color:var(--tx3);font-size:11px">${esc(x.kr)}</p>`:''}
    <p style="margin-top:6px">${esc((x.desc||'').slice(0,140))}…</p>
    <div class="chips" style="margin-top:10px">${x.regions.slice(0,3).map(r=>
      `<a class="chip" href="#/monsters?q=&r=${encodeURIComponent(r)}" style="font-size:11px">${esc(r)}</a>`).join('')}</div>
  </div>`).join('')}</div>`;
};


// --- 屬性相剋 ---
V['attr']=async()=>{
  const {matrix,monAttrs}=await load('systems');
  const w=await load('weapons');
  const WA=Object.keys(matrix);
  const cellOf=(wa,ma)=>{
    const m=matrix[wa];
    if(m.up.includes(ma)) return ['up','▲ 加成','#4caf72'];
    if(m.down.includes(ma)) return ['down','▼ 減傷','#e05c4a'];
    return ['-','—','var(--tx3)'];
  };
  const best={};
  monAttrs.forEach(ma=>{
    best[ma]={good:WA.filter(wa=>matrix[wa].up.includes(ma)),
              bad:WA.filter(wa=>matrix[wa].down.includes(ma))};
  });
  return `
  <h1>屬性相剋</h1>
  <p class="sub">武器屬性會影響對不同屬性怪物的傷害。直排是<b>武器屬性</b>，橫排是<b>怪物屬性</b>。</p>
  <div class="tw"><table>
    <thead><tr><th>武器 ＼ 怪物</th>${monAttrs.map(a=>`<th style="text-align:center">${tr(T.attr,a)}<br><span style="font-weight:400;color:var(--tx3);font-size:10px">${a}</span></th>`).join('')}</tr></thead>
    <tbody>${WA.map(wa=>`<tr>
      <td class="nm">${tr(T.attr,wa)||wa}<span class="kr">${wa}</span></td>
      ${monAttrs.map(ma=>{const [,txt,col]=cellOf(wa,ma);
        return `<td style="text-align:center;color:${col};font-weight:600;font-size:12px">${txt}</td>`}).join('')}
    </tr>`).join('')}</tbody>
  </table></div>
  <div class="note"><b>Earth（地）沒有任何相剋關係</b>——對所有屬性怪物都是原傷害。
  wiki 的 Attribute 頁只列出上述加成／減傷，沒有給實際百分比數字。</div>
  <h2>反查：我要打這種怪，該帶什麼屬性？</h2>
  <div class="grid">${monAttrs.map(ma=>`
    <div class="card"><h3>對付 ${tr(T.attr,ma)} <small style="color:var(--tx3);font-weight:400">${ma}</small></h3>
      <p style="color:#6fd497">✔ 帶：${best[ma].good.length?best[ma].good.map(x=>tr(T.attr,x)).join('、'):'無加成屬性'}</p>
      <p style="color:#ff8f7d">✘ 避開：${best[ma].bad.length?best[ma].bad.map(x=>tr(T.attr,x)).join('、'):'無'}</p>
      <div class="chips" style="margin-top:8px">${best[ma].good.map(x=>{
        const n=w.filter(y=>y.attr===x).length;
        return n?`<a class="chip" style="font-size:11px" href="#/weapons?a=${x}">${tr(T.attr,x)}武器 ${n}</a>`:''}).join('')}</div>
    </div>`).join('')}</div>`;
};

// --- 遊戲系統 ---
V['systems']=async(p)=>{
  const {systems}=await load('systems');
  const cur=p.s||systems.find(s=>s.tables.length).id;
  const s=systems.find(x=>x.id===cur)||systems[0];
  const tbl=t=>`<div class="tw"><table><thead><tr>${
    t.headers.map(h=>h.toLowerCase()==='image'?'<th></th>':`<th>${esc(h)}</th>`).join('')}</tr></thead>
    <tbody>${t.rows.map(r=>`<tr>${t.headers.map((h,i)=>
      h.toLowerCase()==='image'?`<td>${imgTag(r.img)}</td>`
      :`<td${i===0||i===1?' class="nm"':''}>${esc(r.c[i]||'')}</td>`).join('')}</tr>`).join('')}
    </tbody></table></div>`;
  return `
  <h1>遊戲系統</h1>
  <p class="sub">強化、製作、藥水、狀態異常、轉職考試等機制與道具表。說明文字為 wiki 原文（印尼文），表格數值已整理。</p>
  <div class="chips" style="margin-bottom:18px">${systems.map(x=>
    `<a class="chip ${x.id===cur?'on':''}" href="#/systems?s=${encodeURIComponent(x.id)}">${esc(x.zh)}${x.tables.length?'':' ·'}</a>`).join('')}</div>
  <h2>${esc(s.zh)} <span style="color:var(--tx3);font-size:13px;font-weight:400">${esc(s.id)}</span></h2>
  ${s.intro?`<div class="note">${esc(s.intro)}</div>`:''}
  ${s.tables.length?s.tables.map((t,i)=>`${s.tables.length>1?`<h3>表 ${i+1}（${t.rows.length} 列）</h3>`:''}${tbl(t)}`).join('')
    :'<div class="empty">這個頁面在 wiki 上只有文字說明，沒有資料表</div>'}`;
};

// ---------- 路由 ----------
const NAV=[['','首頁'],['jobs','職業'],['skills','技能'],['weapons','武器'],['armors','防具飾品'],
           ['monsters','怪物圖鑑'],['drops','掉落反查'],['attr','屬性相剋'],['systems','遊戲系統'],
           ['pets','寵物'],['npcs','NPC 任務'],['locations','地點']];

function parseHash(){
  const h=location.hash.replace(/^#\/?/,'');
  const [path,qs]=h.split('?');
  const p={}; new URLSearchParams(qs||'').forEach((v,k)=>p[k]=v);
  return [path||'',p];
}
async function route(){
  const [path,p]=parseHash();
  document.getElementById('nav').innerHTML=NAV.map(([h,t])=>
    `<a href="#/${h}" class="${h===path?'on':''}">${t}</a>`).join('');
  const app=document.getElementById('app');
  app.innerHTML='<div class="empty">載入中…</div>';
  const fn=V[path]||V[''];
  try{
    const r=await fn(p);
    if(typeof r==='string'){app.innerHTML=r}
    else{app.innerHTML=r.html; r.init&&r.init()}
  }catch(e){
    app.innerHTML=`<div class="empty">載入失敗：${esc(e.message)}</div>`;
  }
  window.scrollTo(0,0);
}

// ---------- 全站搜尋 ----------
const KIND={m:['怪物','#/monsters'],s:['技能','#/skills'],w:['武器','#/weapons'],
  a:['防具','#/armors'],c:['飾品','#/armors'],p:['寵物','#/pets'],
  n:['NPC','#/npcs'],l:['地點','#/locations'],d:['掉落物','#/drops'],y:['道具／系統','#/systems']};
async function initSearch(){
  const idx=await load('index');
  const q=document.getElementById('q'), box=document.getElementById('sres');
  const run=()=>{
    const v=q.value.trim().toLowerCase();
    if(v.length<2){box.classList.remove('on');return}
    const hit=idx.filter(([,n,k])=>n.toLowerCase().includes(v)||(k||'').includes(v)).slice(0,40);
    if(!hit.length){box.innerHTML='<b>查無結果</b>';box.classList.add('on');return}
    const g={}; hit.forEach(h=>(g[h[0]]=g[h[0]]||[]).push(h));
    box.innerHTML=Object.entries(g).map(([k,arr])=>
      `<b>${KIND[k][0]}（${arr.length}）</b>`+arr.map(([,n,kr,meta])=>
        `<a href="${KIND[k][1]}?q=${encodeURIComponent(n)}">
          <span>${esc(n)}${kr?` <span style="color:var(--tx3);font-size:11px">${esc(kr)}</span>`:''}</span>
          <span>${esc(meta)}</span></a>`).join('')).join('');
    box.classList.add('on');
  };
  q.oninput=run;
  q.onfocus=()=>{if(q.value.trim().length>=2)run()};
  box.onclick=e=>{if(e.target.closest('a')){box.classList.remove('on');q.value=''}};
  document.addEventListener('click',e=>{if(!e.target.closest('.search'))box.classList.remove('on')});
}

// ---------- 啟動 ----------
(async()=>{
  try{ Object.assign(IMGMAP, await (await fetch('data/imgmap.json')).json()) }catch(e){}
  window.addEventListener('hashchange',route);
  await route();
  initSearch();
})();
