'use strict';
/* 天空之城 Online 攻略資料庫 —— 純靜態前端，資料按需載入 */

/* ───────── 小工具 ───────── */
const $ = s => document.querySelector(s);
const view = () => $('#view');

function el(tag, attrs, kids) {
  const n = document.createElement(tag);
  for (const k in attrs || {}) {
    const v = attrs[k];
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') n.className = v;
    else if (k === 'text') n.textContent = v;
    else if (k === 'html') n.innerHTML = v;
    else n.setAttribute(k, v);
  }
  for (const c of [].concat(kids || [])) {
    if (c === null || c === undefined || c === false) continue;
    n.appendChild(typeof c === 'object' ? c : document.createTextNode(String(c)));
  }
  return n;
}
const frag = kids => { const f = document.createDocumentFragment(); for (const k of kids) if (k) f.appendChild(k); return f; };
const num = n => (n === null || n === undefined || n === '') ? '' : Number(n).toLocaleString('en-US');

function rate(r) {
  if (!r && r !== 0) return '';
  const p = r * 100;
  return (p >= 10 ? p.toFixed(0) : p >= 1 ? p.toFixed(1) : p.toFixed(2)) + '%';
}
const rateClass = t => t === 'veryrare' ? 'rate-v' : t === 'rare' ? 'rate-r' : 'rate-c';

/* ───────── 名詞對照 ───────── */
const T = {
  element: { MONSTER_ETC: '一般', MONSTER_FIRE: '火', MONSTER_ICE: '冰',
             MONSTER_LIGHTNING: '雷', BEAST: '動物', DEMON: '惡魔', DRAGON: '龍', UNDEAD: '不死' },
  cls: { FIG: '劍士', ARC: '弓箭手', MAG: '魔法師', CLA: '聖職者', CLE: '聖職者', ALL: '全職業' },
  gender: { ALL: '不限', MALE: '男性', FEMALE: '女性' },
  tier: { common: '普通', rare: '稀有', veryrare: '極稀有' },
  stat: { addStr: '力量', addSta: '體力', addDex: '敏捷', addInt: '智力',
          atkPct: '攻擊力', skillAtkPct: '技能攻擊力', defPct: '防禦力', def: '防禦',
          avoid: '迴避', hit: '命中', critical: '爆擊', hpRegen: 'HP 回復', mpRegen: 'MP 回復',
          maxHpPct: '最大 HP', maxMpPct: '最大 MP', magicResist: '魔法抗性',
          atkBeast: '對動物攻擊', atkDemon: '對惡魔攻擊', atkUndead: '對不死攻擊',
          atkMonster: '對怪物攻擊', defBeast: '對動物防禦', defDemon: '對惡魔防禦',
          defUndead: '對不死防禦', defMonster: '對怪物防禦' },
  enchant: { 1: '強化的', 2: '精緻的', 3: '精煉的', 4: '完美的', 5: '無瑕的', 6: '極緻的' },
  pctStat: new Set(['atkPct', 'skillAtkPct', 'defPct', 'maxHpPct', 'maxMpPct',
                    'atkBeast', 'atkDemon', 'atkUndead', 'atkMonster',
                    'defBeast', 'defDemon', 'defUndead', 'defMonster']),
};
const clsName = c => T.cls[c] || c;

function aiLabel(ai, aggressive) {
  const bits = [aggressive ? '主動攻擊' : '被動'];
  if (ai.includes('RACE')) bits.push('同族支援');
  if (ai.includes('REINFORCE')) bits.push('呼叫援軍');
  if (ai.includes('R_AWAY')) bits.push('會逃跑');
  return bits.join('、');
}

/* 道具效果：{effectType, sustainTime, values:{hp:100}} 這種結構 */
const EFFECT = { hp: '回復 HP', mp: '回復 MP', hpPct: '回復 HP', mpPct: '回復 MP',
                 maxHpPct: '最大 HP', hit: '命中', avoid: '迴避', critical: '爆擊',
                 addStr: '力量', addSta: '體力', addDex: '敏捷', addInt: '智力' };
const PCT_EFFECT = new Set(['hpPct', 'mpPct', 'maxHpPct']);
function effectText(e) {
  if (!e || typeof e !== 'object') return e || '';
  const parts = Object.entries(e.values || {})
    .filter(([, v]) => v)
    .map(([k, v]) => `${EFFECT[k] || k} +${v}${PCT_EFFECT.has(k) ? '%' : ''}`);
  if (e.effectType === 'SUSTAIN' && e.sustainTime) parts.push(`持續 ${e.sustainTime} 秒`);
  return parts.join('、');
}

function statText(stats) {
  const out = [];
  for (const k in stats || {}) {
    const v = stats[k];
    if (!v) continue;
    out.push((T.stat[k] || k) + ' +' + v + (T.pctStat.has(k) ? '%' : ''));
  }
  return out;
}

/* ───────── 資料存取 ───────── */
const cache = {};
async function data(name) {
  if (!cache[name]) {
    cache[name] = fetch('data/' + name + '.json').then(r => {
      if (!r.ok) throw new Error(name);
      return r.json();
    });
  }
  return cache[name];
}
/* 合併過的 NPC 會把被併掉的 id 記在 aliasIds，別處既有的參照才不會斷 */
const byId = (list, id) =>
  list.find(x => x.id === id) || list.find(x => (x.aliasIds || []).includes(id));

/* 掉落／獎勵／材料只給 id + 名稱，得自行判斷屬於哪個域 */
const KIND = { m: 'monsters', p: 'maps', e: 'equips', f: 'fashion',
               i: 'items', r: 'recipes', q: 'quests', n: 'npcs' };
let idx = null, idMap = null;
async function index() {
  if (!idx) {
    idx = await data('index');
    idMap = new Map();
    for (const row of idx) {
      const [k, id, name] = row;
      if (!idMap.has(id)) idMap.set(id, []);
      idMap.get(id).push([k, name]);
    }
  }
  return idx;
}
const ITEMISH = ['i', 'e', 'f'];
function itemHref(id, name) {
  const cands = (idMap && idMap.get(id)) || [];
  let hit = cands.find(c => ITEMISH.includes(c[0]) && c[1] === name)
         || cands.find(c => ITEMISH.includes(c[0]));
  return hit ? '#/' + KIND[hit[0]] + '/' + id : null;
}

/* 名稱 + 圖示，能連就連 */
function itemCell(o, kind) {
  const href = kind ? '#/' + kind + '/' + o.id : itemHref(o.id, o.name);
  const inner = [o.icon ? el('img', { class: 'ic sm', src: o.icon, alt: '', loading: 'lazy' }) : null, o.name];
  return href ? el('a', { class: 'nm', href }, inner) : el('span', { class: 'nm' }, inner);
}

/* ───────── 可排序 / 可篩選表格 ───────── */
const PAGE = 150;

function table(rows, cols, opts) {
  opts = opts || {};
  let sortKey = opts.sort || null, desc = opts.desc !== false, shown = PAGE;

  const tb = el('tbody');
  const thead = el('tr', {}, cols.map((c, i) => {
    const th = el('th', { text: c.h, title: c.title || '' });
    th.onclick = () => {
      if (sortKey === i) desc = !desc; else { sortKey = i; desc = !!c.n; }
      draw(true);
    };
    return th;
  }));
  const wrap = el('div', { class: 'tw' }, [el('table', {}, [el('thead', {}, [thead]), tb])]);
  const more = el('button', { class: 'more' });
  more.onclick = () => {
    const at = tb.children.length;
    shown += PAGE * 3;
    draw(true);
    const first = tb.children[at];
    if (first && first.scrollIntoView) first.scrollIntoView({ block: 'start' });
  };

  function draw(keep) {
    if (!keep) shown = PAGE;
    let list = rows;
    if (sortKey !== null) {
      const c = cols[sortKey];
      const key = c.v || (r => c.c(r));
      list = rows.slice().sort((a, b) => {
        const x = key(a), y = key(b);
        const r = c.n ? (Number(x) || 0) - (Number(y) || 0) : String(x).localeCompare(String(y), 'zh-Hant');
        return desc ? -r : r;
      });
    }
    [...thead.children].forEach((th, i) => {
      th.className = i === sortKey ? (desc ? 's d' : 's') : '';
    });
    tb.textContent = '';
    const f = document.createDocumentFragment();
    for (const r of list.slice(0, shown)) {
      f.appendChild(el('tr', {}, cols.map(c => {
        return el('td', { class: (c.n ? 'n' : '') + (c.wrap ? ' wrap' : '') }, [cell(c.c(r))]);
      })));
    }
    tb.appendChild(f);
    const now = Math.min(shown, list.length);
    more.hidden = list.length <= shown;
    more.textContent = `顯示更多　已顯示 ${num(now)} / 共 ${num(list.length)} 筆`;
  }
  draw();
  return { node: frag([wrap, more]), redraw: draw };
}

/* 篩選列：每個欄位一個下拉，加一個關鍵字框 */
function listPage(title, sub, rows, cols, filters, opts) {
  const st = {};
  const bar = el('div', { class: 'filters' });
  const count = el('span', { class: 'count' });

  const kw = el('input', { type: 'search', placeholder: '篩選名稱⋯' });
  kw.oninput = () => { st.__kw = kw.value.trim(); apply(); };
  bar.appendChild(kw);

  /* 四種篩選器：
     { h, v }                    值完全相符
     { h, opts, match(row, v) }  自訂條件 —— 例如「這件裝備劍士能不能用」
     { h, range }                數值區間，產生上下限兩個輸入格
     { h, multi, has(row, v) }   可複選，選幾項就要全部具備（用來疊條件縮範圍）
     另外任何一種都可以加 { def } 指定預設值 */
  for (const f of filters || []) {
    if (f.multi) {
      st[f.h] = [];
      const chips = el('span', { class: 'multi-chips' });
      const sel = el('select', {}, [el('option', { value: '', text: f.h })]
        .concat(f.multi.map(o => el('option', { value: o.v, text: o.t }))));
      const redraw = () => {
        chips.textContent = '';
        for (const v of st[f.h]) {
          const o = f.multi.find(x => x.v === v);
          const chip = el('button', { class: 'chip', type: 'button', text: (o ? o.t : v) + ' ×' });
          chip.onclick = () => { st[f.h] = st[f.h].filter(x => x !== v); redraw(); apply(); };
          chips.appendChild(chip);
        }
        /* 已選的不再出現在下拉選單裡 */
        for (const opt of sel.options) if (opt.value) opt.hidden = st[f.h].includes(opt.value);
        sel.value = '';
      };
      sel.onchange = () => {
        if (sel.value && !st[f.h].includes(sel.value)) st[f.h].push(sel.value);
        redraw(); apply();
      };
      bar.appendChild(sel); bar.appendChild(chips);
      continue;
    }
    if (f.range) {
      const nums = rows.map(f.range).filter(n => typeof n === 'number' && !isNaN(n));
      if (!nums.length) continue;
      const lo = Math.min(...nums), hi = Math.max(...nums);
      const mk = (which, ph) => {
        const inp = el('input', { type: 'number', class: 'num-input', placeholder: ph,
                                  min: lo, max: hi });
        inp.oninput = () => { st[f.h + which] = inp.value === '' ? null : Number(inp.value); apply(); };
        return inp;
      };
      bar.appendChild(el('span', { class: 'range-filter' },
        [f.h, mk('_min', String(lo)), '–', mk('_max', String(hi))]));
      continue;
    }
    const vals = f.opts || [...new Set(rows.map(f.v).filter(v => v !== '' && v !== null && v !== undefined))];
    if (vals.length < 2) continue;
    if (!f.opts) vals.sort(f.n ? (a, b) => a - b : (a, b) => String(a).localeCompare(String(b), 'zh-Hant'));
    const sel = el('select', {}, [el('option', { value: '', text: f.h })]
      .concat(vals.map(v => el('option', { value: String(v), text: (f.label ? f.label(v) : v) }))));
    if (f.def !== undefined && vals.some(v => String(v) === String(f.def))) {
      sel.value = String(f.def); st[f.h] = String(f.def);
    }
    sel.onchange = () => { st[f.h] = sel.value; apply(); };
    bar.appendChild(sel);
  }
  bar.appendChild(count);

  const host = el('div');
  let t = null;
  function apply() {
    let out = rows;
    if (st.__kw) {
      const q = st.__kw.toLowerCase();
      out = out.filter(r => String(r.name || '').toLowerCase().includes(q));
    }
    for (const f of filters || []) {
      if (f.range) {
        const lo = st[f.h + '_min'], hi = st[f.h + '_max'];
        if (lo !== null && lo !== undefined) out = out.filter(r => (f.range(r) ?? -Infinity) >= lo);
        if (hi !== null && hi !== undefined) out = out.filter(r => (f.range(r) ?? Infinity) <= hi);
        continue;
      }
      if (f.multi) {
        for (const v of st[f.h] || []) out = out.filter(r => f.has(r, v));
        continue;
      }
      const v = st[f.h];
      if (!v) continue;
      out = f.match ? out.filter(r => f.match(r, v)) : out.filter(r => String(f.v(r)) === v);
    }
    count.textContent = `${num(out.length)} 筆`;
    host.textContent = '';
    t = table(out, cols, opts);
    host.appendChild(t.node);
  }
  apply();
  return frag([el('h1', { text: title }), sub ? el('p', { class: 'sub', text: sub }) : null, bar, host]);
}

/* ───────── 明細頁共用零件 ───────── */
const isNode = v => v && typeof v === 'object' && typeof v.nodeType === 'number';
const cell = v => isNode(v) ? v : String(v ?? '');

const dl = pairs => el('dl', { class: 'detail' },
  pairs.filter(p => p && p[1] !== '' && p[1] !== null && p[1] !== undefined)
       .flatMap(([k, v]) => [el('dt', { text: k }), el('dd', {}, [cell(v)])]));

function section(title, rows, cols, opts) {
  if (!rows || !rows.length) return null;
  return frag([el('h2', { text: `${title}（${rows.length}）` }), table(rows, cols, opts).node]);
}
const back = (href, text) => el('a', { class: 'back', href, text: '← ' + text });
const tags = list => el('div', { class: 'tags' }, list.filter(Boolean).map(t =>
  typeof t === 'string' ? el('span', { class: 'tag', text: t }) : el('span', { class: 'tag ' + t[1], text: t[0] })));

/* 圖示 + 名稱 + 描述的頁首 */
function hero(o, extra) {
  return el('div', { class: 'hero' }, [
    o.icon ? el('img', { src: o.icon, alt: '' }) : null,
    el('div', {}, [el('h1', { text: o.name }), extra || null,
                   o.desc ? el('p', { class: 'desc', text: o.desc }) : null]),
  ]);
}

/* 掉落 / 販售 / 獎勵這類「誰有這個東西」的共用欄位 */
const dropCols = [
  { h: '道具', c: d => itemCell(d) },
  { h: '機率', n: true, v: d => d.rate, c: d => el('span', { class: rateClass(d.rateTier), text: rate(d.rate) }) },
  { h: '數量', c: d => d.min ? (d.min === d.max ? d.min : `${d.min}–${d.max}`) : '' },
];
const fromMonCols = [
  { h: '怪物', c: m => itemCell(m, 'monsters') },
  { h: '等級', n: true, v: m => m.level, c: m => m.level ?? '' },
  { h: '機率', n: true, v: m => m.rate, c: m => el('span', { class: rateClass(m.rateTier), text: rate(m.rate) }) },
];

/* ───────── 各域頁面 ───────── */
const V = {};

V.monsters = async () => {
  const rows = await data('monsters');
  return listPage('怪物', `${rows.length} 種。點名稱看掉落與出沒地圖。`, rows, [
    { h: '名稱', c: m => itemCell(m, 'monsters') },
    { h: '等級', n: true, v: m => m.level, c: m => m.level },
    { h: 'HP', n: true, v: m => m.hp, c: m => num(m.hp) },
    { h: '經驗', n: true, v: m => m.exp, c: m => num(m.exp) },
    { h: '攻擊', n: true, v: m => m.maxAtk, c: m => `${m.minAtk}–${m.maxAtk}` },
    { h: '防禦', n: true, v: m => m.def, c: m => m.def },
    { h: '屬性', c: m => T.element[m.element] || m.element },
    { h: '行為', c: m => m.aggressive ? '主動' : '被動' },
    { h: '掉落', n: true, v: m => m.drops.length, c: m => m.drops.length },
  ], [
    { h: '等級', range: m => m.level },
    { h: '屬性', v: m => T.element[m.element] || m.element },
    { h: '行為', v: m => m.aggressive ? '主動' : '被動' },
    { h: 'BOSS', v: m => m.bossRank ? 'BOSS' : '' },
  ], { sort: 1, desc: false });
};

V.monster = async id => {
  const [ms, maps] = await Promise.all([data('monsters'), data('maps')]);
  const m = byId(ms, id);
  if (!m) return el('p', { class: 'empty', text: '找不到這隻怪物。' });
  const here = maps.filter(p => p.monsters.some(x => x.id === id));
  return frag([
    back('#/monsters', '怪物列表'),
    hero(m,
         tags([m.bossRank ? ['BOSS', 'r'] : null, [T.element[m.element] || m.element, 'a'],
               m.aggressive ? ['主動攻擊', 'r'] : '被動', m.isRare ? ['稀有', 'g'] : null])),
    dl([['等級', m.level], ['HP', num(m.hp)], ['經驗', num(m.exp)],
        ['攻擊力', `${m.minAtk}–${m.maxAtk}`], ['防禦力', m.def],
        ['命中', m.hit], ['迴避', m.avoid], ['爆擊', m.critical],
        ['移動速度', m.moveSpeed], ['攻擊速度', m.attackSpeed],
        ['行為', aiLabel(m.ai, m.aggressive)],
        ['掉錢', m.money && m.money.amount ? `${num(m.money.amount)}（${rate(m.money.rate)}）` : ''],
        ['每點 HP 換經驗', (m.exp / m.hp).toFixed(2)]]),
    section('掉落物', m.drops, dropCols, { sort: 1 }),
    section('出沒地圖', here, [
      { h: '地圖', c: p => itemCell(p, 'maps') },
      { h: '區域', c: p => p.region },
      { h: '類型', c: p => p.capsLabel },
      { h: '需求等級', n: true, v: p => p.levelReq, c: p => p.levelReq || '—' },
    ]),
  ]);
};

V.maps = async () => {
  const [rows, ms] = await Promise.all([data('maps'), data('monsters')]);
  const lv = Object.fromEntries(ms.map(m => [m.id, m.level]));
  // 地圖自己的 levelReq 有 390/461 是 0，拿來篩幾乎沒有作用；
  // 真正能判斷「這張圖適不適合我現在打」的是圖裡怪物的等級。
  const rng = rows.map(p => {
    const ls = p.monsters.map(x => lv[x.id]).filter(n => typeof n === 'number');
    return Object.assign({ _lo: ls.length ? Math.min(...ls) : null,
                           _hi: ls.length ? Math.max(...ls) : null }, p);
  });
  return listPage('地圖',
    `${rows.length} 張，含 198 張副本。等級篩的是圖裡怪物的等級 —— 打得動才有意義。`, rng, [
    { h: '名稱', c: p => itemCell(p, 'maps') },
    { h: '區域', c: p => p.region },
    { h: '類型', c: p => p.capsLabel },
    { h: '怪物等級', n: true, v: p => p._lo ?? 999,
      c: p => p._lo === null ? el('span', { class: 'muted', text: '無怪物資料' })
                             : (p._lo === p._hi ? `Lv.${p._lo}` : `Lv.${p._lo}–${p._hi}`) },
    { h: '怪物種類', n: true, v: p => p.monsters.length, c: p => p.monsters.length || '' },
    { h: '需求等級', n: true, v: p => p.levelReq, c: p => p.levelReq || '—' },
    { h: 'NPC', n: true, v: p => p.npcs.length, c: p => p.npcs.length || '' },
  ], [
    { h: '怪物等級', range: p => p._lo },
    { h: '區域', v: p => p.region },
    { h: '類型', v: p => p.capsLabel },
    { h: '有無怪物', v: p => p.monsters.length ? '有怪物' : '無怪物資料' },
  ], { sort: 3, desc: false });
};

V.map = async id => {
  const [maps, ms] = await Promise.all([data('maps'), data('monsters')]);
  const p = byId(maps, id);
  if (!p) return el('p', { class: 'empty', text: '找不到這張地圖。' });
  const full = p.monsters.map(x => Object.assign({}, byId(ms, x.id) || {}, x));
  return frag([
    back('#/maps', '地圖列表'),
    el('h1', { text: p.name }),
    tags([[p.region, 'a'], p.capsLabel, p.levelReq ? `需求等級 ${p.levelReq}` : null]),
    p.minimap ? el('p', {}, [el('img', { src: p.minimap, alt: p.name + ' 小地圖',
        style: 'max-width:100%;border:1px solid var(--line);border-radius:8px;background:var(--bg2)' })]) : null,
    section('出沒怪物', full, [
      { h: '怪物', c: m => itemCell(m, 'monsters') },
      { h: '等級', n: true, v: m => m.level, c: m => m.level },
      { h: 'HP', n: true, v: m => m.hp, c: m => num(m.hp) },
      { h: '經驗', n: true, v: m => m.exp, c: m => num(m.exp) },
      { h: '屬性', c: m => T.element[m.element] || '' },
    ], { sort: 1, desc: false }),
    section('駐點 NPC', p.npcs, [
      { h: 'NPC', c: n => itemCell(n, 'npcs') },
      { h: '職務', c: n => n.job || '' },
    ]),
    section('地圖掉落', p.fieldDrops, dropCols, { sort: 1 }),
  ]);
};

/* 一件東西可以同時是掉落物、材料、任務品。原始資料的 category 只有一個值，
   表達不了多重身分，所以用途改由既有關聯欄位推導 —— 這樣永遠跟資料同步。 */
const ROLES = [
  ['怪物掉落', o => (o.droppedBy || []).length],
  ['地圖掉落', o => (o.mapDrops || []).length],
  ['製作材料', o => (o.usedInRecipes || []).length],
  ['製作產出', o => (o.recipes || []).length],
  ['任務需要', o => (o.questsNeeding || []).length],
  ['任務獎勵', o => (o.questRewards || []).length],
  ['商店販售', o => (o.soldBy || []).length],
];
const rolesOf = o => ROLES.filter(([, f]) => f(o)).map(([n]) => n);

/* 選項只列這批資料裡真的有的用途 —— 裝備不會被當製作材料，
   那個選項出現在裝備頁只會讓人點下去看到 0 筆。 */
const roleFilter = rows => ({
  h: '用途',
  opts: ROLES.map(([n]) => n).filter(n => rows.some(o => rolesOf(o).includes(n))),
  match: (o, v) => rolesOf(o).includes(v),
});
const roleCell = o => el('span', { class: 'tags inline' },
  rolesOf(o).map(r => el('span', { class: 'tag', text: r })));

/* 裝備 / 時裝 / 道具共用一套明細 */
/* 同一件裝備的強化階梯：列表預設只顯示未強化的本體，
   所以明細頁要把六個階級的數值一次攤開，資訊才沒少 */
const ENCHANT_PRE = ['強化的', '精緻的', '精煉的', '完美的', '無瑕的', '極緻的'];
const baseName = n => {
  for (const p of ENCHANT_PRE) if (n.startsWith(p)) return n.slice(p.length);
  return n;
};
function enchantLadder(rows, o) {
  const base = baseName(o.name);
  const fam = rows.filter(x => baseName(x.name) === base)
                  .sort((a, b) => (a.enchantLevel || 0) - (b.enchantLevel || 0));
  if (fam.length < 2) return null;
  return section('強化階梯', fam, [
    { h: '階級', c: x => x.enchantLevel ? `${T.enchant[x.enchantLevel]}（+${x.enchantLevel}）` : '未強化' },
    { h: '名稱', c: x => x.id === o.id ? el('b', { text: x.name }) : itemCell(x, kindOf(x)) },
    { h: '攻擊', c: x => x.attack ? `${x.attack.min}–${x.attack.max}` : '' },
    { h: '附加能力', wrap: true, c: x => statText(x.stats).join('、') },
    { h: '價格', n: true, v: x => x.price || 0, c: x => x.price ? num(x.price) + ' 利比' : '' },
  ]);
}
let kindOf = () => 'equips';

function gearDetail(kind, listName, backLabel) {
  return async id => {
    const rows = await data(listName);
    const o = byId(rows, id);
    if (!o) return el('p', { class: 'empty', text: '找不到這個項目。' });
    const st = statText(o.stats);
    kindOf = () => kind;
    return frag([
      back('#/' + kind, backLabel),
      hero(o, tags([o.slotGroup ? [o.slotGroup, 'a'] : (o.category ? [o.category, 'a'] : null),
                    o.levelReq ? `需求等級 ${o.levelReq}` : null,
                    o.gender && o.gender !== 'ALL' ? T.gender[o.gender] : null,
                    o.tradable === false ? ['不可交易', 'r'] : null,
                    ...(o.classes || []).map(c => [clsName(c), 'g'])])),
      dl([['價格', o.price ? num(o.price) : ''],
          ['需求等級', o.levelReq || ''],
          ['可用職業', (o.classes || []).length ? o.classes.map(clsName).join('、') : (o.classes ? '全職業' : '')],
          ['需求能力', o.reqStats ? statText(Object.fromEntries(
              Object.entries(o.reqStats).map(([k, v]) => ['add' + k[0].toUpperCase() + k.slice(1), v]))).join('、') : ''],
          ['攻擊力', o.attack ? `${o.attack.min}–${o.attack.max}` : ''],
          ['附加能力', st.length ? st.join('、') : ''],
          ['分類', o.category || ''],
          ['使用期限', o.useTerm ? o.useTerm + ' 天' : ''],
          ['最大堆疊', o.maxStack > 1 ? o.maxStack : ''],
          ['效果', effectText(o.effects)]]),

      enchantLadder(rows, o),
      section('怪物掉落', o.droppedBy, fromMonCols, { sort: 2 }),
      section('地圖掉落', o.mapDrops, [
        { h: '地圖', c: d => itemCell(d, 'maps') },
        { h: '機率', n: true, v: d => d.rate, c: d => rate(d.rate) },
      ], { sort: 1 }),
      section('NPC 販售', o.soldBy, [
        { h: 'NPC', c: n => itemCell(n, 'npcs') },
        { h: '價格', n: true, v: n => n.price, c: n => num(n.price) },
      ]),
      section('任務獎勵', o.questRewards, [
        { h: '任務', c: q => itemCell(q, 'quests') },
        { h: '數量', c: q => q.count || '' },
        { h: '職業', c: q => clsName(q.classGroup) },
      ]),
      section('可製作', o.recipes, [{ h: '配方', c: r => itemCell(r, 'recipes') }]),
      section('作為材料', o.usedInRecipes, [{ h: '配方', c: r => itemCell(r, 'recipes') }]),
      section('任務需要', o.questsNeeding, [{ h: '任務', c: q => itemCell(q, 'quests') }]),
    ]);
  };
}

const gearCols = extra => [
  { h: '名稱', c: o => itemCell(o) },
  { h: '部位', c: o => o.slotGroup || o.category || '' },
  { h: '等級', n: true, v: o => o.levelReq, c: o => o.levelReq || '' },
  ...extra,
  { h: '價格', n: true, v: o => o.price, c: o => num(o.price) },
];

/* 選劍士要看到所有劍士穿得下的：只限劍士的、劍士與別的職業共用的、以及不限職業的。
   原本把 classes 併成字串比對，於是「劍士」和「劍士、聖職者」變成兩個選項，共用裝備就被濾掉了。 */
const CLASS_OPTS = ['劍士', '弓箭手', '魔法師', '聖職者'];
const classFilter = {
  h: '職業',
  opts: CLASS_OPTS,
  match: (o, v) => {
    const cs = (o.classes || []).map(clsName);
    return cs.length === 0 || cs.includes(v);
  },
};

/* 附加能力多選：選項只放實際有裝備帶到的屬性，並依出現件數排序 */
function statFilter(rows) {
  const n = {};
  for (const r of rows) for (const k in r.stats || {}) if (r.stats[k]) n[k] = (n[k] || 0) + 1;
  const opts = Object.keys(n).sort((a, b) => n[b] - n[a])
    .map(k => ({ v: k, t: T.stat[k] || k }));   /* 只依常見度排序，不顯示件數 —— 那是全體件數，和當下篩選結果不同，會誤導 */
  return { h: '附加能力（可複選）', multi: opts, has: (r, k) => !!(r.stats || {})[k] };
}

/* 強化階級：站上一半的裝備是強化版本，預設只看未強化，要看再切 */
const enchantFilter = {
  h: '強化階級', v: o => o.enchantLevel || 0, n: true, def: 0,
  label: v => Number(v) ? `${T.enchant[v]}（+${v}）` : '未強化',
};

V.equips = async () => {
  const rows = await data('equips');
  return listPage('戰鬥裝備',
    `${num(rows.length)} 件，其中 ${num(rows.filter(o => o.enchantLevel).length)} 件是強化版本。`
    + '預設只顯示未強化的本體，切換「強化階級」可以看各階數值。'
    + '選職業會一併列出該職業能用的共用裝備與不限職業的裝備。', rows,
    gearCols([
      { h: '攻擊', n: true, v: o => o.attack ? o.attack.max : 0, c: o => o.attack ? `${o.attack.min}–${o.attack.max}` : '' },
      { h: '附加能力', wrap: true, c: o => statText(o.stats).join('、') },
      { h: '職業', c: o => (o.classes || []).map(clsName).join('、') || '全職業' },
      { h: '用途', wrap: true, c: roleCell },
    ]),
    [{ h: '部位', v: o => o.slotGroup }, classFilter,
     { h: '等級', range: o => o.levelReq }, enchantFilter, statFilter(rows), roleFilter(rows)],
    { sort: 2, desc: false });
};
V.equip = gearDetail('equips', 'equips', '裝備列表');

V.fashion = async () => {
  const rows = await data('fashion');
  return listPage('時裝', `${num(rows.length)} 件。`, rows,
    gearCols([{ h: '性別', c: o => T.gender[o.gender] || '' },
              { h: '期限', c: o => o.useTerm ? o.useTerm + ' 天' : '永久' }]),
    [{ h: '部位', v: o => o.slotGroup }, { h: '性別', v: o => T.gender[o.gender] || '' },
     { h: '等級', range: o => o.levelReq }, roleFilter(rows)],
    { sort: 2, desc: false });
};
V.fashionItem = gearDetail('fashion', 'fashion', '時裝列表');

V.items = async () => {
  const rows = await data('items');
  return listPage('道具', `${num(rows.length)} 種。`, rows, [
    { h: '名稱', c: o => itemCell(o) },
    { h: '分類', c: o => o.category },
    { h: '用途', wrap: true, c: roleCell },
    { h: '說明', wrap: true, c: o => (o.desc || '').split('\n')[0] },
    { h: '價格', n: true, v: o => o.price, c: o => num(o.price) },
  ], [{ h: '分類', v: o => o.category }, roleFilter(rows)], { sort: 1, desc: false });
};
V.item = gearDetail('items', 'items', '道具列表');

/* ───────── 製作材料遞迴展開 ─────────
   直接從 recipes.json 即時算，不預先展開存檔：
   完整展開 517 筆會產生 4 MB，而原始配方只有 403 KB，
   而且即時算才能讓「份數」改一個數字就整份重算。 */

/* 同一個中間材料常有多張配方（鐵塊有 16 張、鋼鐵塊 7 張）。
   往下展開時取「單次產出最多」那張當代表 —— 那通常也是玩家實際會用的批量配方。 */
function craftIndex(recipes) {
  const best = new Map();
  for (const r of recipes) {
    if (!r.ingredients || !r.ingredients.length) continue;
    const key = r.result.name;
    const cur = best.get(key);
    if (!cur || (r.result.count || 1) > (cur.result.count || 1)) best.set(key, r);
  }
  return best;
}

/* 關鍵：同一材料會被多個父節點需要，必須等它「所有」父節點都算完、需求收齊，
   才可以往下展開。分層展開是錯的 —— 同一材料若同時出現在第 1 層與第 2 層，
   會被展開兩次而灌水（實測 517 筆有 390 筆對不上）。
   正解是拓樸排序：先把依賴圖建出來，保證每個材料只在收齊需求後處理一次。 */
function craftTotals(root, qty, index) {
  const rootName = root.result.name;

  // 先走一遍收集所有會用到的材料，以及「誰需要誰」
  // 有一種「拿舊的換新的」升級配方（製作法-狼齒：狼牙 + 材料 → 狼牙）。
  // 那把舊的確實要自己準備，所以要當成材料計入，但不能再往下展開，否則會無限遞迴。
  const selfUse = new Map();
  const children = new Map();      // 材料 → 它的下層材料集合
  const parents = new Map();       // 材料 → 有幾個上層材料需要它
  const stack = [rootName];
  const visited = new Set([rootName]);
  children.set(rootName, new Set());
  parents.set(rootName, 0);

  while (stack.length) {
    const name = stack.pop();
    const rec = name === rootName ? root : index.get(name);
    if (!rec) continue;
    for (const g of rec.ingredients) {
      if (g.name === name) { selfUse.set(name, g.count); continue; }
      children.get(name).add(g.name);
      parents.set(g.name, (parents.get(g.name) || 0) + 1);
      if (!visited.has(g.name)) {
        visited.add(g.name);
        children.set(g.name, new Set());
        stack.push(g.name);
      }
    }
  }

  // 需求量：從頂層往下推，但只在某材料的上層全部處理完之後才推它
  const need = new Map([[rootName, qty]]);
  const ready = [rootName];
  const done = new Set();
  const crafted = new Map();

  while (ready.length) {
    const name = ready.shift();
    if (done.has(name)) continue;
    done.add(name);
    const rec = name === rootName ? root : index.get(name);
    if (!rec) continue;                                    // 葉節點，不再往下
    const total = need.get(name) || 0;
    const y = rec.result.count || 1;
    const crafts = Math.ceil(total / y);
    crafted.set(name, { yield: y, crafts, icon: rec.result.icon, id: rec.result.id });
    for (const g of rec.ingredients) {
      if (g.name === name) continue;                       // 升級配方的舊件，最後單獨計
      need.set(g.name, (need.get(g.name) || 0) + g.count * crafts);
      parents.set(g.name, parents.get(g.name) - 1);
      if (parents.get(g.name) === 0) ready.push(g.name);   // 這個材料的需求收齊了
    }
  }

  // 有環的話會有材料永遠等不到 0，補做一輪避免整段漏掉
  for (const name of visited) {
    if (!done.has(name) && index.has(name)) {
      const rec = index.get(name);
      const total = need.get(name) || 0;
      const y = rec.result.count || 1;
      crafted.set(name, { yield: y, crafts: Math.ceil(total / y),
                          icon: rec.result.icon, id: rec.result.id });
    }
  }

  const intermediates = [], leaves = [];
  for (const [name, n] of selfUse) {
    const c = crafted.get(name);
    leaves.push({ name, count: n * (c ? c.crafts : 1), upgrade: true });
  }
  for (const [name, count] of need) {
    if (name === rootName) continue;
    const c = crafted.get(name);
    if (c) intermediates.push({ name, needed: count, yield: c.yield, crafts: c.crafts,
                                icon: c.icon, id: c.id });
    else leaves.push({ name, count });
  }
  intermediates.sort((a, b) => b.needed - a.needed);
  leaves.sort((a, b) => b.count - a.count);
  return { intermediates, leaves };
}

V.recipes = async () => {
  const rows = await data('recipes');
  return listPage('製作配方', `${rows.length} 份。`, rows, [
    { h: '配方', c: r => itemCell(r, 'recipes') },
    { h: '產物', c: r => itemCell(r.result) },
    { h: '分類', c: r => r.resultCategory || '' },
    { h: '成功率', n: true, v: r => r.successRate, c: r => rate(r.successRate) },
    { h: '材料', wrap: true, c: r => r.ingredients.map(i => i.name + (i.count > 1 ? '×' + i.count : '')).join('、') },
  ], [{ h: '分類', v: r => r.resultCategory }], { sort: 3 });
};

V.recipe = async id => {
  const rows = await data('recipes');
  const r = rows.find(x => x.id === id);
  if (!r) return el('p', { class: 'empty', text: '找不到這份配方。' });
  return frag([
    back('#/recipes', '配方列表'),
    hero(r),
    dl([['產物', itemCell(r.result)], ['分類', r.resultCategory || ''],
        ['成功率', rate(r.successRate)], ['製作經驗', r.expBonus || ''],
        ['配方書', r.book ? itemCell(r.book) : '']]),
    section('直接材料', r.ingredients, [
      { h: '材料', c: i => itemCell(i) },
      { h: '數量', n: true, v: i => i.count, c: i => i.count },
    ]),
    craftPlan(r, rows),
    section('可製作的 NPC', r.npcs, [{ h: 'NPC', c: n => itemCell(n, 'npcs') }]),
    section('配方掉落來源', r.recipeItemDroppedBy, fromMonCols, { sort: 2 }),
  ]);
};

/* 展開到底的材料清單：中間物要做幾次、最底層要準備多少 */
function craftPlan(root, recipes) {
  if (!root.ingredients || !root.ingredients.length) return null;
  const index = craftIndex(recipes);
  const host = el('div');
  const qtyInput = el('input', { type: 'number', class: 'num-input', value: '1', min: '1' });
  const summary = el('span', { class: 'count' });

  function draw() {
    const qty = Math.max(1, Number(qtyInput.value) || 1);
    const { intermediates, leaves } = craftTotals(root, qty, index);
    host.textContent = '';
    summary.textContent = `中間物 ${intermediates.length} 種 · 底層材料 ${leaves.length} 種`;

    if (intermediates.length) {
      host.appendChild(el('h3', { text: '要自己先做的（中間材料）' }));
      host.appendChild(table(intermediates, [
        { h: '材料', c: m => itemCell(m) },
        { h: '總共需要', n: true, v: m => m.needed, c: m => num(m.needed) },
        { h: '單次產出', n: true, v: m => m.yield, c: m => m.yield },
        { h: '要製作', n: true, v: m => m.crafts, c: m => el('b', { text: num(m.crafts) + ' 次' }) },
      ]).node);
    }

    host.appendChild(el('h3', { text: '最後要去打或去買的（底層材料）' }));
    host.appendChild(table(leaves, [
      { h: '材料', c: m => el('span', { class: 'nm' }, [
          itemCell(m), m.upgrade ? el('span', { class: 'tag r', text: '升級用舊件' }) : null]) },
      { h: '需要數量', n: true, v: m => m.count, c: m => el('b', { text: num(m.count) }) },
    ]).node);
    host.appendChild(el('p', { class: 'sub', text:
      '點材料名稱可以看它由哪些怪物掉落、哪些 NPC 販售。' }));
  }

  qtyInput.oninput = draw;
  draw();

  return frag([
    el('h2', { text: '完整材料展開' }),
    el('p', { class: 'sub', text:
      '把所有中間材料一路拆到最底層。同一種材料被多個地方需要時會先加總，'
      + '再依「單次產出數」換算要製作幾次 —— 所以總量通常比逐項相乘來得少。' }),
    el('div', { class: 'filters' }, [
      el('span', { class: 'range-filter' }, ['要做幾個', qtyInput]), summary,
    ]),
    host,
  ]);
}

V.quests = async () => {
  const rows = await data('quests');
  return listPage('任務', `${rows.length} 個。獎勵為原始數值，不套倍率。`, rows, [
    { h: '任務', c: q => itemCell(q, 'quests') },
    { h: '等級', n: true, v: q => q.levelReq, c: q => q.levelReq || '' },
    { h: '類型', c: q => q.typeLabel || '' },
    { h: '職業', c: q => clsName(q.classReq) },
    { h: '區域', c: q => (q.regions || []).join('、') },
    { h: '經驗', n: true, v: q => q.rewards.exp, c: q => num(q.rewards.exp) },
    { h: '金錢', n: true, v: q => q.rewards.gold, c: q => num(q.rewards.gold) },
  ], [{ h: '類型', v: q => q.typeLabel }, { h: '職業', v: q => clsName(q.classReq) },
      { h: '區域', v: q => (q.regions || [])[0] || '' }], { sort: 1, desc: false });
};

V.quest = async id => {
  const rows = await data('quests');
  const q = byId(rows, id);
  if (!q) return el('p', { class: 'empty', text: '找不到這個任務。' });
  const objectives = [
    ...q.hunt.map(h => ({ k: '討伐', t: itemCell(h.target, 'monsters'), n: h.count })),
    ...q.collect.map(c => ({ k: '蒐集', t: itemCell(c.target), n: c.count })),
    ...q.delivery.map(d => ({
      k: '遞送',
      t: el('span', { class: 'nm' }, [itemCell(d.item), ' → ',
            d.to ? itemCell(d.to, 'npcs') : '', d.from ? `（來自 ${d.from.name}）` : '']),
    })),
    ...q.indun.map(d => ({
      k: '地城',
      t: el('span', { class: 'nm' }, [d.dungeon,
            d.entryItem ? el('span', { class: 'nm' }, ['｜入場道具 ', itemCell(d.entryItem)]) : '']),
    })),
  ];
  return frag([
    back('#/quests', '任務列表'),
    el('h1', { text: q.name }),
    tags([q.typeLabel ? [q.typeLabel, 'a'] : null, q.levelReq ? `等級 ${q.levelReq}` : null,
          q.classReq !== 'ALL' ? [clsName(q.classReq), 'g'] : null,
          q.fameReq ? `名聲 ${q.fameReq}` : null,
          q.timeLimit ? ['限時', 'r'] : null,
          q.permanentGiveup ? ['放棄後不可再接', 'r'] : null]),
    q.desc ? el('p', { class: 'desc', text: q.desc }) : null,
    section('任務目標', objectives,
      [{ h: '種類', c: o => o.k },
       { h: '內容', wrap: true, c: o => o.t },
       { h: '數量', n: true, v: o => o.n || 0, c: o => o.n || '' }]),
    section('相關 NPC', q.npcs, [
      { h: 'NPC', c: n => itemCell(n, 'npcs') },
      { h: '所在地', c: n => (n.maps || []).map(m => m.name).join('、') },
    ]),
    section('前置任務', q.prereq, [{ h: '任務', c: p => itemCell(p, 'quests') }]),
    el('h2', { text: '任務獎勵' }),
    dl([['經驗', num(q.rewards.exp)], ['金錢', num(q.rewards.gold)],
        ['專長點數', q.rewards.specialtyPt || ''],
        ['修練點數', (q.rewards.lessonPt || []).some(Boolean) ? q.rewards.lessonPt.join(' / ') : '']]),
    section('獎勵道具', q.rewards.items, [
      { h: '道具', c: i => itemCell(i) },
      { h: '數量', c: i => i.count || '' },
      { h: '職業', c: i => clsName(i.classGroup) },
    ]),
  ]);
};

V.npcs = async () => {
  const rows = await data('npcs');
  const merged = rows.reduce((a, n) => a + (n.aliasIds || []).length, 0);
  return listPage('NPC',
    `${rows.length} 位。原始資料有 ${rows.length + merged} 筆，其中 ${merged} 筆是同一位 NPC 的重複紀錄`
    + '（同一個名字出現在多張地圖，或商店與任務分成兩筆），已合併並列出全部所在地。'
    + '販售或任務內容不同的同名 NPC 是不同個體，維持獨立條目。', rows, [
    { h: '名稱', c: n => itemCell(n, 'npcs') },
    { h: '所在地', n: true, v: n => (n.maps || []).length,
      c: n => (n.maps || []).length > 1 ? `${(n.maps || []).length} 處` : ((n.maps || [])[0] || {}).name || '' },
    { h: '職務', c: n => n.job || '' },
    { h: '區域', c: n => n.region || '' },
    { h: '所在地', c: n => (n.maps || []).map(m => m.name).join('、') },
    { h: '功能', c: n => (n.roleLabels || []).join('、') },
  ], [{ h: '區域', v: n => n.region }, { h: '功能', v: n => (n.roleLabels || [])[0] || '' }]);
};

/* NPC 個人檔案：原始 desc 的分隔符號寫法很亂（冒號有無、半形全形、
   欄位名打錯字），已在 build/npc_profile.py 解析成欄位，這裡只負責排版 */
/* 同名的其他 NPC：合併只併「內容完全相同」的，剩下同名多筆代表真的是不同個體 */
function sameNameVariants(rows, n) {
  const others = rows.filter(x => x.name === n.name && x.id !== n.id);
  if (!others.length) return null;
  return frag([
    el('p', { class: 'lead', text:
      `站上還有 ${others.length} 位同名的「${n.name}」，販售或任務內容不同，是不同的個體。` }),
    section('同名的其他' + n.name, others, [
      { h: 'NPC', c: x => itemCell(x, 'npcs') },
      { h: '所在地', wrap: true, c: x => (x.maps || []).map(m => m.name).join('、') || '—' },
      { h: '販售', n: true, v: x => (x.sells || []).length,
        c: x => (x.sells || []).length ? `${(x.sells || []).length} 種` : '—' },
      { h: '任務', n: true, v: x => (x.quests || []).length,
        c: x => (x.quests || []).length ? `${(x.quests || []).length} 個` : '—' },
      { h: '角色', wrap: true, c: x => (x.roleLabels || []).join('、') },
    ]),
  ]);
}

function npcProfile(n) {
  const p = n.profile, t = n.traits || [], notes = n.notes || [];
  if (!p && !t.length && !notes.length) return null;
  const bits = p ? [['年齡', p.age], ['血型', p.blood], ['身高', p.height], ['體重', p.weight]]
                     .filter(([, v]) => v && v !== '?') : [];
  return el('div', { class: 'profile' }, [
    bits.length ? el('div', { class: 'chips' },
      bits.map(([k, v]) => el('span', { class: 'tag', text: `${k} ${v}` }))) : null,
    t.length ? el('dl', {}, t.flatMap(o => [
      el('dt', { text: o.k }), el('dd', { class: 'wrap', text: o.v })])) : null,
    notes.length ? el('ul', { class: 'notes' },
      notes.map(x => el('li', { class: 'wrap', text: x }))) : null,
  ]);
}

V.npc = async id => {
  const [rows, quests] = await Promise.all([data('npcs'), data('quests')]);
  const n = byId(rows, id);
  if (!n) return el('p', { class: 'empty', text: '找不到這位 NPC。' });
  const qs = quests.filter(q => q.npcs.some(x => x.id === id));
  return frag([
    back('#/npcs', 'NPC 列表'),
    /* desc 是原始那整塊文字，個人檔案已拆成欄位，兩者不重複顯示 */
    hero(Object.assign({}, n, { desc: (n.traits || n.profile) ? null : n.desc }),
         tags([n.region ? [n.region, 'a'] : null, n.job || null,
               ...(n.roleLabels || []).map(r => [r, 'g'])])),
    npcProfile(n),
    section('所在地', n.maps, [
      { h: '地圖', c: m => itemCell(m, 'maps') },
      { h: '座標', c: m => (m.x || m.y) ? `${m.x}, ${m.y}` : '' },
    ]),
    /* 同名但內容不同的，是真的不同個體（決鬥場的流浪商人賣 PvP 稱號、
       學習之路程的賣時裝）。不把差異藏起來，直接並列讓人看得出差在哪。 */
    sameNameVariants(rows, n),
    section('販售商品', n.sells, [
      { h: '商品', c: s => itemCell(s) },
      { h: '價格', n: true, v: s => s.price, c: s => num(s.price) },
    ], { sort: 1, desc: false }),
    section('相關任務', qs, [
      { h: '任務', c: q => itemCell(q, 'quests') },
      { h: '等級', n: true, v: q => q.levelReq, c: q => q.levelReq || '' },
      { h: '類型', c: q => q.typeLabel || '' },
    ], { sort: 1, desc: false }),
  ]);
};

/* ───────── 練功效率（本站自行計算） ───────── */
V.grind = async () => {
  const rows = await data('grind');
  return listPage('練功地圖排行',
    `依「每點 HP 能換到多少經驗」排序 —— 數字越高，打死一隻的效益越好。`
    + `共 ${num(rows.length)} 筆，含 ${rows.filter(g => g.type === '副本鑰匙').length} 場鑰匙副本。`
    + `先用「平均等級」篩出打得動的範圍，再看效率。`
    + `鑰匙副本以「一整場」為單位（你進去是打完整場，不是打單一房間），`
    + `所以另給整場總量；無限型怪物無限湧出、沒有總量，只給效率。`
    + `頭目 HP 動輒上萬、經驗也高，混進平均會把效率撐歪（本城登基廳 8.66 → 排除後 2.63），`
    + `所以另給一欄「排除頭目」的效率，也可以直接用「頭目」篩選器只看沒有頭目的地圖。`,
    rows, [
      { h: '地圖', c: g => itemCell(g, 'maps') },
      { h: '區域', c: g => g.region },
      { h: '平均等級', n: true, v: g => g.avgLv, c: g => g.avgLv },
      { h: '效率', n: true, v: g => g.eff, c: g => el('b', { text: g.eff.toFixed(2) }),
        title: '平均經驗 ÷ 平均 HP（含頭目）' },
      { h: '排除頭目', n: true, v: g => g.effNoBoss ?? -1,
        c: g => g.effNoBoss === undefined ? '—'
              : el('b', { class: g.effNoBoss < g.eff - 0.005 ? 'warn' : '',
                          text: g.effNoBoss.toFixed(2) }),
        title: '只算一般怪的效率。與左欄差很多代表該圖的數字是被頭目撐起來的' },
      { h: '頭目', c: g => g.boss || g.miniBoss
          ? el('span', { class: 'tag ' + (g.boss ? 'r' : 'g'),
                         text: (g.boss ? `${g.boss} 頭目` : '') + (g.boss && g.miniBoss ? ' ' : '')
                               + (g.miniBoss ? `${g.miniBoss} 小頭目` : '') })
          : '' },
      { h: '平均經驗', n: true, v: g => g.exp, c: g => num(g.exp) },
      { h: '平均 HP', n: true, v: g => g.hp, c: g => num(g.hp) },
      { h: '整場經驗', n: true, v: g => g.runExp || 0,
        c: g => g.runExp ? num(g.runExp) : (g.type === '副本鑰匙' ? '無限' : ''),
        title: '跑完一趟能拿到的總經驗' },
      { h: '整場 HP', n: true, v: g => g.runHp || 0,
        c: g => g.runHp ? num(g.runHp) : '', title: '跑完一趟要打掉的總 HP' },
      { h: '平均掉錢', n: true, v: g => g.money, c: g => num(g.money) },
      { h: '主動怪', n: true, v: g => g.aggressive, c: g => g.aggressive ? g.aggressive + ' 種' : '' },
      { h: '怪物種類', n: true, v: g => g.kinds, c: g => g.kinds },
    ], [
      { h: '平均等級', range: g => g.avgLv },
      { h: '頭目', v: g => g.bossTag },
      { h: '區域', v: g => g.region },
      { h: '類型', v: g => g.type },
    ], { sort: 3 });
};

/* ───────── 寵物 ─────────
   逐等級效果來自舊版社群資料，中文名稱與道具說明來自現行資料。
   下面這份職業建議是本站的判斷，不是遊戲內建資料，判斷依據都寫在頁面上。 */
const PET_PICKS = [
  {
    who: '魔法師',
    pick: '麻吉',
    why: '傷害幾乎全部來自技能，「技能攻擊力 +10%」是唯一直接加在輸出上的寵物加成。',
  },
  {
    who: '聖職者',
    pick: '麻吉',
    why: '同樣以技能為主要輸出，理由與魔法師相同。',
  },
  {
    who: '劍士',
    pick: '麻吉',
    why: '技能為主就選麻吉。普攻為主才考慮恐龍，但恐龍的攻擊力加成兩份資料一份寫 6%、一份寫 10%，'
       + '取低標時仍輸給麻吉的 10%，所以除非你確定自己幾乎不放技能，否則麻吉還是比較穩。',
  },
  {
    who: '弓箭手',
    pick: '麻吉',
    why: '判斷方式與劍士相同。恐龍的數值爭議也一樣適用。',
  },
  {
    who: '練等與打寶',
    pick: '艾琳',
    why: '掉寶率加成是所有寵物裡唯一的一份，Lv.10 已有人實機驗證。但它完全不加傷害，打王時要換回輸出寵。',
  },
];

const PET_CAVEATS = [
  ['惡魔金只對普攻型有意義',
   '舊資料把它標成「技能冷卻」，但伺服器主已確認該欄位實際上是攻擊速度，影響的是普攻間隔而不是技能。'
   + '技能型職業吃不到主要效果；它附帶的防禦加成，用寵物技能書「防禦力上升」任何寵物都拿得到。'],
  ['先買「拾取」，再想加成',
   '五本寵物技能書與品種無關，任何寵物都吃得到，而且都只要 1000。'
   + '「拾取」會自動撿道具和錢，是這幾本裡唯一每一秒都在生效的；加成類的等養到等級才有感。'],
  ['數值有兩份說法的地方，頁面兩邊都列',
   '舊版社群資料與現行道具說明對某些寵物的加成項目不一致，本站不代為二選一，差異直接標在該寵物的備註欄。'],
];

/* 平坦數值在低等級最值錢，但 G-Joe 偏偏鎖在 Lv.28 才能孵。
   下面這張表是拿站上的武器資料實算的：各等級區間內單手／雙手武器攻擊力的中位數，
   再看 +20 佔多少比重。 */
const FLAT_DECAY = [
  ['Lv.1–15', 15, '孵不出來'],
  ['Lv.16–30', 50, '40.0%'],
  ['Lv.28–35', 71, '28.2%'],
  ['Lv.36–50', 98, '20.5%'],
  ['Lv.51–70', 145, '13.8%'],
  ['Lv.71–90', 198, '10.1%'],
  ['Lv.91+', 252, '7.9%'],
];

function gjoeCase() {
  return frag([
    el('h2', { text: 'G-Joe 為什麼沒進建議名單' }),
    el('p', { class: 'sub', text:
      'Lv.10 給的是「攻擊 +20、敏捷 +14」——平坦數值，不是百分比。'
      + '這兩件事在這個遊戲裡差很多，而 G-Joe 剛好卡在最尷尬的位置。' }),
    el('div', { class: 'two-col' }, [
      el('div', {}, [
        el('h3', { text: '問題一：平坦加成會隨等級貶值' }),
        table(FLAT_DECAY.map(([seg, med, pct]) => ({ seg, med, pct })), [
          { h: '等級區間', c: r => r.seg },
          { h: '武器攻擊力中位數', n: true, v: r => r.med, c: r => r.med },
          { h: '+20 佔比', c: r => r.pct === '孵不出來'
              ? el('span', { class: 'muted', text: r.pct })
              : el('b', { text: r.pct }) },
        ]).node,
        el('p', { class: 'sub', text:
          '平坦 +20 最值錢的時候是 Lv.15 以前——但蛋標明高階寵物，那時候根本孵不出來。'
          + '等你到得了 Lv.28，它已經只剩武器攻擊力的三成不到，之後一路掉到不足一成。' }),
      ]),
      el('div', {}, [
        el('h3', { text: '問題二：加成是「邊養邊貶值」' }),
        el('p', { class: 'sub', text:
          '+20 是 Lv.10 才有的數字，Lv.1 只有 +2。而寵物從 Lv.1 養到 Lv.10 要 4,602,420 點 LOVE '
          + '——就算每隻怪都打高七等以上、每隻拿滿 40 點，也要十一萬多隻。'
          + '換句話說，你養到它給 +20 的那天，+20 已經比你開始養的時候更不值錢了。' }),
        el('h3', { text: '問題三：敏捷對多數職業不加傷害' }),
        el('p', { class: 'sub', text:
          '另外那半的 +14 敏捷影響的是命中與迴避，不是輸出。'
          + '真正拿來比的其實只有 +20 攻擊那一半。' }),
        el('h3', { text: '那它什麼時候值得養？' }),
        el('p', { class: 'sub', text:
          '如果你是幾乎不放技能的純普攻打法，而且剛好在 Lv.28–40 這段——'
          + '那時候 +20 還佔得到武器攻擊力的兩成以上，是有意義的。'
          + '但只要你的輸出有一部分來自技能，麻吉的百分比加成會隨著你換裝一起長大，G-Joe 不會。' }),
      ]),
    ]),
    el('p', { class: 'sub', text:
      '順帶一提：G-Joe 的蛋和麻吉的蛋都是 1000，所以這不是花錢多寡的取捨，純粹是加成型態的差別。' }),
  ]);
}

V.pets = async () => {
  const d = await data('pets');
  const picks = el('div', { class: 'tw' }, [el('table', {}, [
    el('thead', {}, [el('tr', {}, [el('th', { text: '職業／用途' }), el('th', { text: '建議' }),
                                   el('th', { text: '理由' })])]),
    el('tbody', {}, PET_PICKS.map((p) => el('tr', {}, [
      el('td', {}, [el('b', { text: p.who })]),
      el('td', {}, [el('b', { class: 'pick', text: p.pick })]),
      el('td', { class: 'wrap' }, [p.why]),
    ]))),
  ])]);

  const caveats = el('div', { class: 'trait-grid' }, PET_CAVEATS.map(([t, x]) =>
    el('article', { class: 'trait-card' }, [el('h3', { text: t }), el('p', { text: x })])));

  const hasSource = d.pets.some(p => p.source || p.verified);
  const list = table(d.pets, [
    { h: '寵物', c: p => el('a', { class: 'nm', href: '#/pets/' + encodeURIComponent(p.name) }, [
        p.eggIcon ? el('img', { class: 'ic sm', src: p.eggIcon, alt: '', loading: 'lazy' }) : null,
        p.name]) },
    { h: '屬性', c: p => p.attr || '' },
    { h: 'Lv.10 效果', wrap: true, c: p => el('b', { text: p.peak || '—' }) },
    ...(hasSource ? [
      { h: '數值來源', c: p => p.source || '—' },
      { h: '實機驗證', c: p => p.verified ? el('span', { class: 'tag g', text: p.verified }) : '—',
        title: '有人實際養到這個等級並回報數值' },
    ] : []),
    { h: '蛋', c: p => p.eggName || '' },
    { h: '專用飼料', wrap: true, c: p => (p.foods || []).map(f => f.name).join('、') },
    { h: '備註', wrap: true, c: p => p.note || '' },
  ]).node;

  const skills = table(d.skills || [], [
    { h: '技能書', c: s => el('span', { class: 'nm' }, [
        s.icon ? el('img', { class: 'ic sm', src: s.icon, alt: '', loading: 'lazy' }) : null, s.name]) },
    { h: '效果', c: s => el('b', { text: s.eff || s.desc || '' }) },
    { h: '生效條件', c: s => s.lvReq > 1 ? `寵物 Lv.${s.lvReq} 以上` : '立即生效' },
    { h: '道具說明', wrap: true, c: s => s.desc || '' },
    { h: '價格', n: true, v: s => s.price, c: s => num(s.price) },
  ], { sort: 2, desc: false }).node;

  return frag([
    el('h1', { text: '寵物' }),
    el('p', { class: 'sub', text:
      `${d.pets.length} 隻。寵物加成掛在主人身上，選錯不會壞事，但也等於白養一隻。` }),

    el('h2', { text: '哪個職業該養哪一隻' }),
    el('p', { class: 'sub', text: '本站判斷，非遊戲內資料。依據寫在下面的注意事項裡。' }),
    picks,

    el('h2', { text: '注意事項' }),
    caveats,

    gjoeCase(),

    el('h2', { text: `寵物一覽（${d.pets.length}）` }),
    list,

    (d.skills || []).length ? frag([
      el('h2', { text: '寵物技能書' }),
      el('p', { class: 'sub', text: '掛在寵物身上、效果加在主人身上，任何寵物都能吃，與品種無關。' }),
      skills,
    ]) : null,

    d.exp ? frag([
      el('h2', { text: '養成成本' }),
      el('p', { class: 'sub', text:
        `寵物靠 LOVE 升級，打越高等的怪拿越多。Lv.1 養到 Lv.10 總共要 ${num(d.exp.total)} 點。` }),
      el('div', { class: 'two-col' }, [
        el('div', {}, [
          el('h3', { text: '各級所需 LOVE' }),
          table(d.exp.levels, [
            { h: '等級', n: true, v: l => l.lv, c: l => 'Lv.' + l.lv },
            { h: '升下一級', n: true, v: l => l.love, c: l => l.love ? num(l.love) : '—' },
          ], { sort: 0, desc: false }).node,
        ]),
        el('div', {}, [
          el('h3', { text: '打怪取得 LOVE' }),
          table(d.exp.gain, [
            { h: '怪物相對等級', c: g => g.diff },
            { h: '每隻', n: true, v: g => g.love, c: g => g.love },
          ], { sort: 1 }).node,
        ]),
      ]),
    ]) : null,

    (d.unmatched || []).length ? frag([
      el('h2', { text: '資料不齊的寵物' }),
      el('p', { class: 'sub', text: '現行資料裡找得到專用飼料，但找不到對應的蛋，因此無法確認取得方式與加成。' }),
      table(d.unmatched, [
        { h: '名稱', c: u => u.name },
        { h: '種類', c: u => u.kind || '' },
        { h: '說明', wrap: true, c: u => u.note || '' },
      ]).node,
    ]) : null,
  ]);
};

V.pet = async name => {
  const d = await data('pets');
  const p = d.pets.find(x => x.name === decodeURIComponent(name));
  if (!p) return el('p', { class: 'empty', text: '找不到這隻寵物。' });
  return frag([
    back('#/pets', '寵物列表'),
    hero({ name: p.name, icon: p.eggIcon, desc: p.eggDesc },
         tags([p.attr ? [p.attr, 'a'] : null, p.peak ? [p.peak, 'g'] : null,
               p.en && p.en !== p.name ? p.en : null])),
    dl([['蛋', p.eggName || ''], ['蛋的價格', p.eggPrice ? num(p.eggPrice) : ''],
        ['Lv.10 效果', p.peak || ''], ['數值來源', p.source || ''],
        ['實機驗證到', p.verified || ''], ['原始名稱', p.kr || ''],
        ['備註', p.note || '']]),
    section('逐等級效果', p.levels, [
      { h: '等級', n: true, v: l => l.lv, c: l => 'Lv.' + l.lv },
      { h: '效果', wrap: true, c: l => l.eff || '—' },
      ...(p.levels.some(l => 'verified' in l)
        ? [{ h: '實機驗證', c: l => l.verified ? el('span', { class: 'tag g', text: '已驗證' }) : '' }]
        : []),
    ], { sort: 0, desc: false }),
    section('專用飼料', p.foods, [
      { h: '飼料', c: f => itemCell(f) },
      { h: '說明', wrap: true, c: f => f.desc || '' },
    ]),
  ]);
};

/* ───────── wiki 補充：技能 / 徽章 / 系統 ───────── */
V.skills = async () => {
  const w = await data('wiki');
  const rows = w.skills.map((s, i) => Object.assign({ _i: i }, s));
  return listPage('技能', `${rows.length} 個。點名稱看各等級數值。`, rows, [
    { h: '名稱', c: s => el('a', { class: 'nm', href: '#/skills/' + s._i }, [
      s.icon ? el('img', { class: 'ic sm', src: s.icon, alt: '', loading: 'lazy' }) : null, s.name]) },
    { h: '職業', c: s => s.job || '—' },
    { h: '類型', c: s => s.type || '' },
    { h: '等級數', n: true, v: s => s.levels.length, c: s => s.levels.length },
    { h: '說明', wrap: true, c: s => s.desc || '' },
  ], [{ h: '職業', v: s => s.job || '—' }, { h: '類型', v: s => s.type }]);
};

V.skill = async i => {
  const w = await data('wiki');
  const s = w.skills[Number(i)];
  if (!s) return el('p', { class: 'empty', text: '找不到這個技能。' });
  const keys = [...new Set(s.levels.flatMap(l => Object.keys(l.f)))];
  return frag([
    back('#/skills', '技能列表'),
    hero(s, tags([s.job ? [s.job, 'a'] : null, s.type ? [s.type, 'g'] : null])),
    section('各等級數值', s.levels,
      [{ h: '階級', c: l => l.name }].concat(keys.map(k => ({ h: k, c: l => l.f[k] ?? '' })))),
  ]);
};

/* 名稱來源：中文玩家資料 > 由頭目名推得 > 我方暫譯 > 未譯 */
const NAMED = { zh: '', boss: '', tr: '暫譯', en: '未譯' };

V.badges = async () => {
  const w = await data('wiki');
  const rows = w.badges.map(b => Object.assign({ _src: NAMED[b.named] || '' }, b));
  return listPage('徽章',
    `${rows.length} 枚。徽章佔一個額外的飾品欄位，效果多半是經驗、機率或費用加成。` +
    `取得方式多為隨機，社群實測的說法附在最後一欄。`,
    rows, [
      { h: '名稱', wrap: true, c: b => el('span', {}, [
          el('b', { text: b.name }),
          b._src ? el('span', { class: 'tag', text: b._src }) : null,
          b.en && b.en !== b.name ? el('small', { class: 'sub', text: ' ' + b.en }) : null]) },
      { h: '稀有度', c: b => b.rarity || '' },
      { h: '等級', n: true, v: b => b.lv || 0, c: b => b.lvtext || b.lv || '' },
      { h: '效果', wrap: true, c: b => el('span', {}, [
          b.eff || '',
          b.alt ? el('small', { class: 'sub', text: '（' + b.alt + '）' }) : null]) },
      { h: '取得方式', wrap: true, c: b => b.method || '' },
      { h: '說明', wrap: true, c: b => el('span', {}, [
          b.flavor ? el('small', { class: 'sub', text: b.flavor }) : null,
          b.note || '']) },
      { h: '價格', c: b => b.price || '' },
    ],
    [{ h: '稀有度', v: b => b.rarity }, { h: '名稱來源', v: b => b._src || '已確認' }],
    { sort: 2, desc: false });
};

/* 第一欄的圖：欄名叫「圖示」就整格放圖，否則貼在文字前面 */
const rawCell = (r, c, i, mode) => {
  if (i !== 0 || !mode) return el('td', { class: 'wrap', text: c });
  const img = r.icon ? el('img', { class: mode === 'only' ? '' : 'ic sm',
                                   src: r.icon, alt: '', loading: 'lazy' }) : null;
  const link = img && r.itemId ? el('a', { href: '#/items/' + r.itemId }, [img]) : img;
  return mode === 'only' ? el('td', { class: 'ic' }, [link])
                         : el('td', { class: 'wrap nm' }, [link, c]);
};
const rawTable = t => {
  const mode = !t.rows.some(r => r.icon) ? null
             : t.headers[0] === '圖示' ? 'only' : 'inline';
  return el('div', { class: 'tw' }, [el('table', {}, [
    el('thead', {}, [el('tr', {}, t.headers.map(h => el('th', { text: h })))]),
    el('tbody', {}, t.rows.map(r => el('tr', {}, r.c.map((c, i) => rawCell(r, c, i, mode))))),
  ])]);
};
V.system = async () => {
  const w = await data('wiki');
  const kv = (title, obj) => frag([el('h3', { text: title }), el('dl', { class: 'detail' },
    Object.entries(obj).flatMap(([k, v]) =>
      [el('dt', { text: k }), el('dd', { text: Array.isArray(v) ? v.join(' → ') : v })]))]);
  /* 第一欄叫「圖示」的表（強化石），該欄改畫圖並連到道具頁；其餘照舊出文字 */


  return frag([
    el('h1', { text: '遊戲系統' }),
    el('p', { class: 'sub', text: '轉職、屬性相剋、強化石與轉職考試題庫。' }),

    el('h2', { text: '屬性相剋' }),
    el('p', { class: 'sub', text: '「剋制」代表用該屬性攻擊會加成，「被抵抗」代表傷害會被削減。' }),
    el('div', { class: 'tw' }, [el('table', { class: 'matrix' }, [
      el('thead', {}, [el('tr', {}, [el('th', { text: '攻擊屬性' }), el('th', { text: '剋制' }), el('th', { text: '被抵抗' })])]),
      el('tbody', {}, Object.entries(w.matrix).map(([k, v]) => el('tr', {}, [
        el('td', {}, [el('b', { text: k })]),
        el('td', { class: 'wrap' }, [v.up.length ? v.up.join('、') : '—']),
        el('td', { class: 'wrap' }, [v.down.length ? v.down.join('、') : '—']),
      ]))),
    ])]),
    el('p', { class: 'sub', text: '怪物屬性：' + w.monAttrs.join('、') }),

    el('h2', { text: '轉職路線' }),
    kv('職業進階', w.jobTree),
    kv('可用武器', w.jobWeapons),

    el('h2', { text: '強化石' }),
    frag(w.stones.map(rawTable)),

    el('h2', { text: `轉職考試題庫（${w.exam.rows.length}）` }),
    rawTable(w.exam),
  ]);
};

/* ───────── 玩家筆記 ─────────
   這批講的是「遊戲怎麼運作」—— 組隊平均等級怎麼算、越級加成的門檻在哪、
   爆擊為什麼要先堆命中。這些資料表裡沒有，只有玩過的人寫得出來。 */
V.notes = async () => {
  const d = await data('notes');
  return frag([
    el('h1', { text: '玩家筆記' }),
    el('p', { class: 'sub', text:
      `${d.kept} 篇機制說明，整理自玩家社群的攻略討論（2007–2010）。`
      + `這裡只收「不隨版本變的規則」—— 例如經驗值怎麼算、越級的加成與代價、`
      + `爆擊與命中的關係。含具體數值的另有 ${d.held} 篇，要逐筆跟現行資料對照過才會收，暫不列入。` }),

    frag(d.groups.map(g => frag([
      el('h2', { text: `${g.name}（${g.notes.length}）` }),
      el('div', { class: 'note-list' }, g.notes.map(n => el('article', { class: 'note-card' }, [
        el('h3', { text: n.title }),
        el('div', { class: 'note-meta' }, [
          n.author ? `${n.author}` : '', n.author && n.date ? ' · ' : '', n.date || '',
        ]),
        (n.topics || []).length ? tags(n.topics) : null,
        el('p', { class: 'desc', text: n.text }),
        n.note ? el('p', { class: 'note-warn', text: '⚠ ' + n.note }) : null,
      ]))),
    ]))),

    el('h2', { text: '為什麼有些沒收' }),
    el('div', { class: 'trait-grid' }, [
      el('article', { class: 'trait-card' }, [
        el('h3', { text: '含數值的先擱著' }),
        el('p', { text: `掉落出處、價格、等級門檻這類寫死數字的內容共 ${d.held} 篇。`
          + '遊戲改版過很多次，那些數字未必還準，而站上多數同類資料已經直接來自現行資料表。'
          + '要收之前得逐筆比對，沒比對過就放上來，等於用舊資料蓋掉新資料。' }),
      ]),
      el('article', { class: 'trait-card' }, [
        el('h3', { text: '站上已有的不重複收' }),
        el('p', { text: '屬性相剋、轉職考試題庫、任務掉落物這些，站上的版本更完整也更新，'
          + '再放一份舊的只會讓人不知道該信哪個。' }),
      ]),
      el('article', { class: 'trait-card' }, [
        el('h3', { text: '玩法主張不算事實' }),
        el('p', { text: '「體力該不該點高」「敏捷優先還是力量優先」這類是玩家各自的主張，'
          + '不是可以查證的規則。有收錄的會標明那是某位玩家的看法，不是定論。' }),
      ]),
    ]),
  ]);
};

/* ───────── 首頁 ───────── */
V.home = async () => {
  const [meta, g] = await Promise.all([data('meta'), data('grind')]);
  const c = meta.counts;
  const cards = [
    ['grind', '練功地圖', `${meta.grind} 張排行`],
    ['monsters', '怪物', `${c.monsters} 種 · 完整掉落`],
    ['maps', '地圖', `${c.maps} 張`],
    ['equips', '戰鬥裝備', `${num(c.equips)} 件`],
    ['fashion', '時裝', `${num(c.fashion)} 件`],
    ['items', '道具', `${num(c.items)} 種`],
    ['recipes', '製作配方', `${c.recipes} 份`],
    ['quests', '任務', `${c.quests} 個`],
    ['npcs', 'NPC', `${c.npcs} 位`],
    ['pets', '寵物', '8 隻 · 職業建議'],
    ['skills', '技能', '154 個'],
    ['badges', '徽章', '59 枚'],
    ['system', '遊戲系統', '屬性 · 轉職 · 題庫'],
    ['notes', '玩家筆記', '32 篇機制說明'],
  ];
  const top = g.slice().sort((a, b) => b.eff - a.eff).slice(0, 10);
  return frag([
    el('h1', { text: '天空之城 Online 攻略資料庫' }),
    el('p', { class: 'sub', text: `全站 ${num(meta.searchIndex)} 筆資料可直接搜尋，離線也能查。` }),
    el('div', { class: 'cards' }, cards.map(([h, t, s]) =>
      el('a', { class: 'card', href: '#/' + h }, [el('b', { text: t }), el('small', { text: s })]))),
    el('h2', { text: '練功效率前 10' }),
    table(top, [
      { h: '地圖', c: x => itemCell(x, 'maps') },
      { h: '區域', c: x => x.region },
      { h: '平均等級', n: true, v: x => x.avgLv, c: x => x.avgLv },
      { h: '效率', n: true, v: x => x.eff, c: x => el('b', { text: x.eff.toFixed(2) }) },
    ]).node,
    el('p', { class: 'sub' }, [el('a', { href: '#/grind', text: '看完整排行 →' })]),
  ]);
};

/* ───────── 全站搜尋 ───────── */
const KLABEL = { m: '怪物', p: '地圖', e: '裝備', f: '時裝', i: '道具', r: '配方', q: '任務', n: 'NPC' };
const DETAIL = { m: 'monsters', p: 'maps', e: 'equips', f: 'fashion', i: 'items', r: 'recipes', q: 'quests', n: 'npcs' };

function initSearch() {
  const input = $('#q'), box = $('#suggest');
  let hits = [], cur = -1;

  const close = () => { box.hidden = true; cur = -1; };
  const go = () => {
    if (cur >= 0 && hits[cur]) { location.hash = hits[cur].href; input.blur(); close(); }
  };

  input.addEventListener('input', async () => {
    const q = input.value.trim().toLowerCase();
    if (q.length < 1) return close();
    const list = await index();
    hits = [];
    for (const [k, id, name, hint] of list) {
      const p = name.toLowerCase().indexOf(q);
      if (p < 0) continue;
      hits.push({ k, name, hint, href: '#/' + DETAIL[k] + '/' + id, rank: p });
      if (hits.length > 400) break;
    }
    hits.sort((a, b) => a.rank - b.rank || a.name.length - b.name.length);
    hits = hits.slice(0, 30);
    box.textContent = '';
    if (!hits.length) { box.appendChild(el('a', { class: 'k', text: '找不到符合的項目' })); box.hidden = false; return; }
    hits.forEach((h, i) => box.appendChild(el('a', { href: h.href }, [
      el('span', { class: 'k', text: KLABEL[h.k] }), h.name, el('span', { class: 'h', text: h.hint }),
    ])));
    cur = -1; box.hidden = false;
  });

  input.addEventListener('keydown', e => {
    if (box.hidden) return;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      cur = (cur + (e.key === 'ArrowDown' ? 1 : -1) + hits.length) % hits.length;
      [...box.children].forEach((c, i) => c.classList.toggle('on', i === cur));
      box.children[cur] && box.children[cur].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter') { e.preventDefault(); if (cur < 0) cur = 0; go(); }
    else if (e.key === 'Escape') close();
  });
  document.addEventListener('click', e => { if (!e.target.closest('.searchbox')) close(); });
  box.addEventListener('click', () => setTimeout(close, 0));
}

/* ───────── 路由 ───────── */
/* 專業技能：所有職業共用，向克魯諾用專業技能點數學 */
V.major = async () => {
  const d = await data('major-skill');
  const rows = d.skills.map((s, i) => Object.assign({ _i: i }, s));
  return frag([
    el('p', { class: 'lead', text: d.intro }),
    listPage('專業技能', `${rows.length} 個，分屬 ${new Set(rows.map(r => r.group)).size} 個系列。`, rows, [
      { h: '名稱', c: s => el('span', { class: 'nm' }, [
        s.icon ? el('img', { class: 'ic sm', src: s.icon, alt: '', loading: 'lazy' }) : null,
        el('b', { text: s.name })]) },
      { h: '系列', c: s => s.group || '—' },
      { h: '階級', c: s => s.tier || '—' },
      { h: '點數', n: true, v: s => s.cost, c: s => s.cost },
      { h: '說明', wrap: true, c: s => s.desc || '' },
    ], [{ h: '系列', v: s => s.group || '—' }, { h: '階級', v: s => s.tier || '—' },
        { h: '點數', range: s => s.cost }]),
  ]);
};

/* 角色：能力值、能力點、經驗表、能量條、時裝、操作、師徒、狀態異常 */
V.character = async () => {
  const d = await data('character');
  const paras = a => (a || []).map(t => el('p', { class: 'lead', text: t }));
  /* 名稱＋英文原名＋說明的卡片列表，能力值／能力點／狀態異常共用 */
  const defs = (list, body) => el('div', { class: 'defs' }, list.map(o => el('div', { class: 'def' }, [
    o.icon ? el('img', { class: 'ic sm', src: o.icon, alt: '', loading: 'lazy' }) : null,
    el('b', { text: o.name }),
    o.en && o.en !== o.name ? el('span', { class: 'en', text: o.en }) : null,
    el('p', {}, body(o).filter(Boolean).map(t => el('span', { class: 'wrap', text: t }))),
  ])));

  return frag([
    el('h1', { text: '角色' }),
    el('p', { class: 'sub', text: '能力值、能力點、經驗表、能量條、時裝、操作與狀態異常。' }),
    frag(paras(d.intro)),

    el('h2', { text: '能力值' }),
    defs(d.stats, o => [o.desc]),

    el('h2', { text: '能力點' }),
    frag(paras(d.points.intro)),
    defs(d.points.list, o => [o.effect, o.perPoint]),
    d.points.note ? el('p', { class: 'lead', text: d.points.note }) : null,
    rawTable(d.points.cost),
    d.points.reset && d.points.reset.icon
      ? el('p', { class: 'lead nm' }, [
          el('img', { class: 'ic sm', src: d.points.reset.icon, alt: '', loading: 'lazy' }),
          '能力點可以用重置道具歸零重配。']) : null,

    el('h2', { text: '升級經驗表' }),
    rawTable(d.expTable),

    el('h2', { text: '能量條' }),
    frag(paras(d.gauge.intro)),
    frag(d.gauge.bars.map(b => frag([
      el('h3', { text: b.name }), rawTable(b.table)]))),

    el('h2', { text: '狀態異常' }),
    defs(d.statusEffects, o => [o.desc]),
    frag(paras(d.statusSources.intro)),
    el('h3', { text: '會造成狀態異常的怪物' }),
    frag(paras(d.statusSources.monsterIntro)),
    rawTable(d.statusSources.monsters),
    el('h3', { text: '徽章' }),
    rawTable(d.statusSources.badges),
    frag(d.statusSources.skills.map(g => frag([
      el('h3', { text: '技能 —— ' + g.name }), rawTable(g.table)]))),

    el('h2', { text: '師徒' }),
    frag(paras(d.proctor.text)),
    frag(d.proctor.requirements.map(r => frag([
      el('h3', { text: r.title }),
      el('ul', {}, r.items.map(t => el('li', { class: 'wrap', text: t }))),
    ]))),
    el('h3', { text: '前輩獎勵' }), rawTable(d.proctor.seniorRewards),
    el('h3', { text: '後輩獎勵' }), rawTable(d.proctor.juniorRewards),

    el('h2', { text: '時裝' }),
    frag(paras(d.fashion.intro)),
    frag(d.fashion.groups.map(g => frag([
      el('h3', { text: g.name }), rawTable(g.table)]))),

    el('h2', { text: '操作按鍵' }),
    frag(paras(d.controls.intro)),
    el('div', { class: 'tw' }, [el('table', {}, [
      el('thead', {}, [el('tr', {}, [el('th', { text: '按鍵' }), el('th', { text: '功能' })])]),
      el('tbody', {}, d.controls.keys.map(k => el('tr', {}, [
        el('td', {}, [el('kbd', { text: k.key })]), el('td', { class: 'wrap', text: k.action })]))),
    ])]),

    el('h2', { text: '背包與交易' }),
    frag(paras(d.inventory.text)),
    d.quickSlot.icon
      ? el('p', { class: 'lead nm' }, [
          el('img', { class: 'ic sm', src: d.quickSlot.icon, alt: '', loading: 'lazy' }),
          '進階快速欄']) : null,
    frag(paras(d.quickSlot.text)),
    frag(paras(d.privateStore.text)),
    frag(paras(d.trading.text)),
    el('ul', {}, (d.trading.tips || []).map(t => el('li', { class: 'wrap', text: t }))),
  ]);
};

/* 副本、寶箱、地圖大師 */
V.dungeons = async () => {
  const d = await data('dungeons');
  const paras = a => (a || []).map(t => el('p', { class: 'lead', text: t }));
  const ul = a => el('ul', {}, (a || []).map(t => el('li', { class: 'wrap', text: t })));
  /* 名稱＋圖，有 id 就連到對應頁 */
  const ref = (o, kind, idKey, suffix) => {
    const inner = [o.icon ? el('img', { class: 'ic sm', src: o.icon, alt: '', loading: 'lazy' }) : null,
                   o.name + (suffix || '')];
    return o[idKey] ? el('a', { class: 'nm', href: `#/${kind}/${o[idKey]}` }, inner)
                    : el('span', { class: 'nm' }, inner);
  };
  const chips = (list, kind, idKey, suffix) =>
    el('div', { class: 'chips' }, (list || []).map(o => ref(o, kind, idKey, suffix && suffix(o))));

  const run = r => el('div', { class: 'run' }, [
    el('b', { text: r.typeName }),
    r.keyName ? el('span', { class: 'en', text: r.keyName.en }) : null,
    el('div', { class: 'kv' }, [el('span', { text: '房間' }), chips(r.maps, 'maps', 'mapId')]),
    el('div', { class: 'kv' }, [el('span', { text: '怪物' }),
      chips(r.monsters, 'monsters', 'monsterId', m => m.level ? ` Lv${m.level}` : '')]),
  ]);

  const group = g => el('section', { class: 'card dg' }, [
    el('h3', {}, [g.dungeonKeyIcon ? el('img', { class: 'ic sm', src: g.dungeonKeyIcon, alt: '' }) : null,
                  g.name, el('span', { class: 'en', text: g.en })]),
    el('div', { class: 'kv' }, [el('span', { text: '所在' }),
      el('span', { text: [g.continent && g.continent.name, g.location && g.location.name].filter(Boolean).join(' → ') })]),
    g.npc ? el('div', { class: 'kv' }, [el('span', { text: '入口 NPC' }), ref(g.npc, 'npcs', 'npcId')]) : null,
    g.dungeonKeyFrom ? el('div', { class: 'kv' }, [el('span', { text: '鑰匙來源' }),
      el('span', { text: g.dungeonKeyFrom.name })]) : null,
    frag((g.runs || []).map(run)),
  ]);

  const box = b => el('section', { class: 'card dg' }, [
    el('h3', {}, [b.icon ? el('img', { class: 'ic sm', src: b.icon, alt: '' }) : null,
                  b.name, el('span', { class: 'en', text: b.en })]),
    b.hp ? el('div', { class: 'kv' }, [el('span', { text: 'HP' }), el('span', { text: String(b.hp) })]) : null,
    el('div', { class: 'kv' }, [el('span', { text: '地點' }),
      el('span', { text: (b.locations || []).map(l => l.name).join('、') || '—' })]),
    el('div', { class: 'kv' }, [el('span', { text: '掉落' }),
      chips(b.drops, 'items', 'itemId', o => o.count > 1 ? ` ×${o.count}` : '')]),
  ]);

  const dg = d.dungeons, mm = d.mapMaster;
  return frag([
    el('h1', { text: '副本' }),
    el('p', { class: 'sub', text: `${dg.groups.length} 組副本、${dg.types.length} 種型態，另有寶箱與地圖大師。` }),
    frag(paras(dg.intro)),

    el('h2', { text: '四種型態' }),
    el('div', { class: 'defs' }, dg.types.map(t => el('div', { class: 'def' }, [
      el('b', { text: t.name }), el('span', { class: 'en', text: t.en }),
      el('p', {}, [el('span', { class: 'wrap', text: t.goal })]),
    ]))),
    el('p', { class: 'lead', text: `進場只要持有${dg.entry.requires}，一次 ${dg.entry.durationMinutes} 分鐘。${dg.entry.note}` }),

    el('h2', { text: '八組副本' }),
    frag(dg.groups.map(group)),

    el('h2', { text: '站上有、副本資料沒列出來的房間' }),
    el('div', { class: 'defs' }, (dg.otherTypes || []).map(t => el('div', { class: 'def' }, [
      el('b', { text: t.name }),
      t.guess ? el('span', { class: 'en', text: '推測為 ' + t.guess }) : null,
      el('p', {}, [el('span', { class: 'wrap', text: t.note }),
                   el('span', { class: 'wrap', text: t.mapIdRange.join(' – ') })]),
    ]))),

    el('h2', { text: '寶箱' }),
    frag(paras(d.treasureBoxes.intro)),
    frag(d.treasureBoxes.boxes.map(box)),

    el('h2', { text: '地圖大師' }),
    el('p', { class: 'lead', text: mm.summary }),
    el('h3', { text: '怎麼挑戰' }), ul(mm.howTo),
    el('h3', { text: '規則' }), ul(mm.rules),
    el('h3', { text: '挑戰地點' }),
    el('p', { class: 'wrap', text: (mm.locations || []).map(l => l.name).join('、') }),
  ]);
};

/* 社群系統：PvP、組隊、PvM、社團、婚禮、戰爭任務、天氣 */
V.social = async () => {
  const d = await data('social');
  /* 戰爭任務已獨立成「功勳」頁（它是專業技能點數的主要來源），這裡只留指路 */
  const ORDER = ['party', 'circle', 'wedding', 'pvp', 'pvm', 'weather'];

  /* 表格的圖示是與 rows 同形狀的平行矩陣，貼在該格文字前面 */
  const tbl = t => el('div', {}, [
    t.caption ? el('h4', { text: t.caption }) : null,
    el('div', { class: 'tw' }, [el('table', {}, [
      el('thead', {}, [el('tr', {}, t.headers.map(h => el('th', { text: h })))]),
      el('tbody', {}, t.rows.map((r, ri) => el('tr', {}, r.map((c, ci) => {
        const src = ((t.icons || [])[ri] || [])[ci];
        return src ? el('td', { class: 'wrap nm' },
                        [el('img', { class: 'ic sm', src, alt: '', loading: 'lazy' }), c])
                   : el('td', { class: 'wrap', text: c });
      })))),
    ])]),
  ]);

  const sec = x => frag([
    x.h ? el('h3', { text: x.h }) : null,
    x.body ? el('p', { class: 'lead', text: x.body }) : null,
    (x.items || []).length
      ? el('ul', {}, x.items.map((t, i) => el('li', { class: 'wrap' }, [
          (x.itemIcons || [])[i]
            ? el('img', { class: 'ic sm', src: x.itemIcons[i], alt: '', loading: 'lazy' }) : null, t])))
      : null,
  ]);

  const block = key => {
    const b = d[key];
    if (!b) return null;
    return frag([
      el('h2', {}, [b.title, b.en && b.en !== b.title ? el('span', { class: 'en', text: b.en }) : null]),
      b.intro ? el('p', { class: 'lead', text: b.intro }) : null,
      (b.introItems || []).length
        ? el('ul', {}, b.introItems.map(t => el('li', { class: 'wrap', text: t }))) : null,
      frag((b.sections || []).map(sec)),
      frag((b.tables || []).map(tbl)),
    ]);
  };

  return frag([
    el('h1', { text: '社群系統' }),
    el('p', { class: 'sub', text: '組隊、社團、婚禮、對戰模式、戰爭任務與天氣。' }),
    el('nav', { class: 'jump' }, ORDER.filter(k => d[k]).map(k =>
      el('a', { href: '#social-' + k, text: d[k].title }))),
    frag(ORDER.map(k => d[k] ? el('section', { id: 'social-' + k }, [block(k)]) : null)),
    el('h2', { text: '戰爭任務與物資補給' }),
    el('p', { class: 'lead' }, ['內容較多，已獨立成一頁：',
      el('a', { href: '#/merit', text: '功勳' }), '。']),
  ]);
};

/* 導覽分兩組：前半是查資料（怪物、裝備、道具⋯），後半是玩法與系統說明。
   只用一條細分隔線隔開，不加群組標題 —— 標題會變成兩塊擠在列上的雜訊。 */
/* 功勳：戰爭任務點數，也是專業技能點數的主要來源 */
V.merit = async () => {
  const d = await data('merit');
  return frag([
    el('h1', {}, [d.title, el('span', { class: 'en', text: d.en })]),
    el('p', { class: 'sub', text: '戰爭任務、物資補給，以及專業技能點數怎麼來。' }),
    el('p', { class: 'lead', text: d.intro }),
    d.quota.length ? frag([
      el('h3', { text: '可接的怪物數量（依等級差）' }),
      el('ul', {}, d.quota.map(t => el('li', { class: 'wrap', text: t }))),
    ]) : null,
    el('h3', { text: '物資補給' }),
    el('p', { class: 'lead', text: d.supply }),

    el('h2', { text: '功勳階級與專業技能點數' }),
    el('p', { class: 'lead', text: d.note }),
    el('div', { class: 'tw' }, [el('table', {}, [
      el('thead', {}, [el('tr', {}, ['階', '累計功勳', '階級', '專業技能點數', '另一份來源的階級', '另一份的區間']
        .map(h => el('th', { text: h })))]),
      el('tbody', {}, d.tiers.map(t => el('tr', {}, [
        el('td', { text: String(t.n) }),
        el('td', { text: num(t.zhPoint) + ' 點' }),
        el('td', {}, [el('b', { text: t.zhName })]),
        el('td', {}, [el('b', { text: '+' + t.skillPoints })]),
        el('td', { class: 'wrap dim', text: t.altName }),
        el('td', { class: 'wrap dim', text: t.altRange }),
      ]))),
    ])]),
    el('p', { class: 'lead', text:
      `十階全部升滿共 ${d.tiers.reduce((a, t) => a + t.skillPoints, 0)} 點專業技能點數。` }),

    el('h2', { text: '專業技能點數的來源' }),
    el('div', { class: 'defs' }, d.sources.map(x => el('div', { class: 'def' }, [
      el('b', { text: x.from }),
      el('p', {}, [el('span', { class: 'wrap', text: x.detail })]),
    ]))),
    el('p', { class: 'lead' }, ['點數怎麼花：', el('a', { href: '#/major', text: '專業技能' }),
      '。另一個來源的細節看 ', el('a', { href: '#/schoolyear', text: '學年考試' }), '。']),

    el('h2', { text: '用語' }),
    el('div', { class: 'tw' }, [el('table', {}, [
      el('thead', {}, [el('tr', {}, ['站上用字', '別名', '說明'].map(h => el('th', { text: h })))]),
      el('tbody', {}, d.terms.map(t => el('tr', {}, [
        el('td', {}, [el('b', { text: t.zh })]),
        el('td', { text: t.alt }),
        el('td', { class: 'wrap', text: t.note }),
      ]))),
    ])]),
  ]);
};

/* 學年考試：升學年要繳錢、打指定怪、回學院答題，每學年給 2 點專攻點。
   怪物名以 2008 官方改版後譯名為準 —— 拿站上怪物資料對照，改版後譯名
   49 筆中 48 筆對得上，舊譯名只對得上 5 筆，所以舊名只留在同列供對照。 */
V.schoolyear = async () => {
  const d = await data('schoolyear');
  const grind = new Map(d.grind.map(g => [g.year, g.rows]));
  const mon = (name, id, cur) => id
    ? el('a', { href: '#/monsters/' + id, text: cur || name })
    : el('span', { text: name });

  /* 費用分兩欄：實測過的才是數字，其餘一律標成未驗證的攻略值。
     目前抽驗 2 筆、2 筆都跟攻略不符，所以不能讓兩者看起來一樣可信。 */
  const feeRows = d.years.map(y => {
    const ok = y.feeSource === 'verified';
    return el('tr', { class: ok ? 'fee-verified' : '' }, [
      el('td', {}, [el('b', { text: y.year + ' 學年' })]),
      el('td', {}, [
        el('b', { text: num(y.fee) + ' 利比' }),
        ok ? el('span', { class: 'tag-ok', text: '實測' }) : null,
      ]),
      el('td', { class: 'dim wrap', text: ok
        ? (y.bahaFee && y.bahaFee !== y.fee ? '攻略寫 ' + num(y.bahaFee) + '，錯' : '—')
        : '未驗證，取自 2007 攻略' }),
      el('td', { class: 'dim', text: (grind.get(y.year) || []).length
        ? (grind.get(y.year) || []).length + ' 隻' : (y.year === 2 ? '不需打怪' : '—') }),
      el('td', { class: 'dim', text: y.answersOnly ? '僅有答案' : '題目 + 答案' }),
    ]);
  });

  const yearBlock = y => {
    const rows = grind.get(y.year) || [];
    return el('section', { class: 'sy-year', id: 'sy-' + y.year }, [
      el('h3', {}, [`${y.year} 學年`, el('span', { class: 'en',
        text: num(y.fee) + ' 利比' + (y.feeSource === 'verified' ? '（實測）' : '（未驗證）') })]),
      rows.length ? el('p', { class: 'lead wrap' }, ['所需怪物：', ...rows.flatMap((r, i) => [
        i ? '、' : '', el('span', {}, [
          el('span', { class: 'dim', text: 'Lv' + r.level + ' ' }),
          mon(r.name, r.monsterId),
          r.oldName && r.oldName !== r.name ? el('span', { class: 'dim', text: '（舊名 ' + r.oldName + '）' }) : null,
          r.maps.length ? el('span', { class: 'dim', text: ' ' + r.maps.join('、') }) : null,
        ]),
      ])]) : el('p', { class: 'lead dim', text: y.year === 2 ? '不需打怪即可考。' : '' }),
      y.answersOnly
        ? el('p', { class: 'lead wrap' }, ['答案：', ...y.questions.flatMap((q, i) => [
            i ? '、' : '',
            el('span', {}, [
              q.level ? el('span', { class: 'dim', text: 'Lv' + q.level + ' ' }) : null,
              mon(q.answer, q.monsterId, q.currentName),
            ]),
          ]), el('span', { class: 'dim', text: '（來源未記題目）' })])
        : el('div', { class: 'tw' }, [el('table', {}, [
            el('thead', {}, [el('tr', {}, ['解答', '現行圖鑑描述（認題用這欄）', '2007 攻略的題目']
              .map(h => el('th', { text: h })))]),
            el('tbody', {}, y.questions.map(q => el('tr', {}, [
              el('td', { class: 'wrap' }, [
                q.level ? el('span', { class: 'dim', text: 'Lv' + q.level + ' ' }) : null,
                el('b', {}, [mon(q.answer, q.monsterId, q.siteName || q.currentName)]),
                q.guideLevel ? el('span', { class: 'dim', text: '（攻略誤植 Lv' + q.guideLevel + '）' }) : null,
                (q.siteName && q.siteName !== q.answer)
                  ? el('span', { class: 'dim', text: '（攻略寫 ' + q.answer + '）' }) : null,
                q.maps && q.maps.length ? el('span', { class: 'dim', text: ' ' + q.maps.join('、') }) : null,
              ]),
              el('td', { class: 'wrap' }, [
                q.realDesc ? el('b', { text: q.realDesc + '／' + q.realShort }) : null,
                q.realDesc ? el('span', { class: 'tag-ok', text: '實測題目' }) : null,
                (!q.realDesc && q.playerConfirmed)
                  ? el('span', { class: 'tag-ok', text: '玩家確認攻略無誤' }) : null,
                q.realDesc ? el('br', {}) : null,
                el('span', { class: q.realDesc ? 'dim' : '', text: q.monsterDesc || '—' }),
              ]),
              el('td', { class: 'wrap dim', text: q.desc + '／' + q.short }),
            ]))),
          ])]),
    ]);
  };

  return frag([
    el('h1', {}, [d.title, el('span', { class: 'en', text: d.en })]),
    el('p', { class: 'sub', text: '升學年的費用、所需怪物與完整題庫。' }),
    el('p', { class: 'lead', text: d.intro }),

    el('p', { class: 'lead wrap', text: d.howto.replace(/\*\*/g, '') }),
    el('p', { class: 'lead' }, ['專攻點的其他來源看 ', el('a', { href: '#/merit', text: '功勳' }),
      '，點數怎麼花看 ', el('a', { href: '#/major', text: '專業技能' }), '。']),

    el('h2', { text: '費用一覽' }),
    el('p', { class: 'lead', text: d.verify }),
    el('div', { class: 'tw' }, [el('table', {}, [
      el('thead', {}, [el('tr', {}, ['學年', '考試費用', '資料狀態', '所需怪物', '題庫']
        .map(h => el('th', { text: h })))]),
      el('tbody', {}, feeRows),
    ])]),

    el('h2', { text: '逐學年題庫' }),
    el('p', { class: 'lead wrap', text: d.questionNote.replace(/\*\*/g, '') }),
    el('p', { class: 'lead', text: d.naming }),
    el('p', { class: 'jump' }, d.years.flatMap((y, i) => [
      i ? ' ' : '', el('a', { href: '#sy-' + y.year, text: y.year }),
    ])),
    ...d.years.map(yearBlock),

    d.renames && d.renames.length ? frag([
      el('h2', { text: '攻略舊譯名對照' }),
      el('p', { class: 'lead', text: '實測比對出來的改譯。攻略的句型多半沒錯，換掉名詞就能對上。' }),
      el('div', { class: 'tw' }, [el('table', {}, [
        el('thead', {}, [el('tr', {}, ['2007 攻略', '現行遊戲'].map(h => el('th', { text: h })))]),
        el('tbody', {}, d.renames.map(r => el('tr', {}, [
          el('td', { class: 'dim', text: r.old }), el('td', {}, [el('b', { text: r.new })]),
        ]))),
      ])]),
    ]) : null,

    el('h2', { text: '資料落差' }),
    el('ul', {}, d.gaps.map(t => el('li', { class: 'wrap', text: t }))),

    el('h2', { text: '用語' }),
    el('div', { class: 'tw' }, [el('table', {}, [
      el('thead', {}, [el('tr', {}, ['站上用字', '別名', '說明'].map(h => el('th', { text: h })))]),
      el('tbody', {}, d.terms.map(t => el('tr', {}, [
        el('td', {}, [el('b', { text: t.site })]),
        el('td', { text: t.aka.join('、') }),
        el('td', { class: 'wrap', text: t.note }),
      ]))),
    ])]),

    el('h2', { text: '資料來源' }),
    el('div', { class: 'defs' }, d.sources.map(x => el('div', { class: 'def' }, [
      el('b', { text: x.title }),
      el('p', {}, [el('span', { class: 'wrap dim', text: `${x.author}・${x.date}　${x.use}` })]),
    ]))),
  ]);
};

const NAV_GROUPS = [
  [['', '首頁'], ['monsters', '怪物'], ['maps', '地圖'], ['equips', '裝備'],
              ['fashion', '時裝'], ['items', '道具'], ['recipes', '製作'],
              ['quests', '任務'], ['npcs', 'NPC'], ['pets', '寵物']],
  [['grind', '練功'], ['skills', '技能'], ['major', '專業技能'],
                  ['character', '角色'], ['dungeons', '副本'], ['social', '社群'], ['merit', '功勳'], ['schoolyear', '學年考試'],
                  ['badges', '徽章'], ['system', '系統'], ['notes', '玩家筆記']],
];
const NAV = NAV_GROUPS.flat();

const ROUTE = {
  '': V.home, grind: V.grind, major: V.major, character: V.character, dungeons: V.dungeons, social: V.social, merit: V.merit, schoolyear: V.schoolyear,
  monsters: V.monsters, maps: V.maps, equips: V.equips, fashion: V.fashion,
  items: V.items, recipes: V.recipes, quests: V.quests, npcs: V.npcs,
  pets: V.pets, skills: V.skills, badges: V.badges, system: V.system, notes: V.notes,
};
const ROUTE1 = {
  monsters: V.monster, maps: V.map, equips: V.equip, fashion: V.fashionItem,
  items: V.item, recipes: V.recipe, quests: V.quest, npcs: V.npc,
  pets: V.pet, skills: V.skill,
};

function drawNav(active) {
  $('#nav').textContent = '';
  NAV_GROUPS.forEach((items, i) => {
    if (i) $('#nav').appendChild(el('span', { class: 'nav-sep' }));
    for (const [h, t] of items) {
      $('#nav').appendChild(el('a', { href: '#/' + h, text: t, class: h === active ? 'on' : '' }));
    }
  });
}

async function route() {
  /* 頁內錨點（#social-party 這種）不是路由，交給瀏覽器自己捲，不要重畫整頁 */
  if (location.hash && !location.hash.startsWith('#/')) return;
  const parts = location.hash.replace(/^#\/?/, '').split('/').filter(Boolean);
  const [sec, id] = parts;
  drawNav(sec || '');
  view().textContent = '';
  view().appendChild(el('p', { class: 'loading', text: '載入中⋯' }));
  try {
    await index();
    const fn = id ? ROUTE1[sec] : ROUTE[sec || ''];
    if (!fn) throw new Error('404');
    const node = await fn(id);
    view().textContent = '';
    view().appendChild(node);
  } catch (err) {
    view().textContent = '';
    view().appendChild(el('p', { class: 'empty', text: '這個頁面不存在，或資料載入失敗。' }));
    view().appendChild(el('p', {}, [el('a', { href: '#/', text: '← 回首頁' })]));
  }
  window.scrollTo(0, 0);
}

window.addEventListener('hashchange', route);
data('meta').then(m => { $('#stamp').textContent = '資料更新：' + m.updated; }).catch(() => {});
initSearch();
route();

if (typeof window !== 'undefined') window.ROUTE = ROUTE;  /* 測試用：讓回歸腳本能檢查路由名稱 */
