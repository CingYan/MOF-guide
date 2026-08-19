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
const byId = (list, id) => list.find(x => x.id === id);

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

  for (const f of filters || []) {
    const vals = [...new Set(rows.map(f.v).filter(v => v !== '' && v !== null && v !== undefined))];
    if (vals.length < 2) continue;
    vals.sort(f.n ? (a, b) => a - b : (a, b) => String(a).localeCompare(String(b), 'zh-Hant'));
    const sel = el('select', {}, [el('option', { value: '', text: f.h })]
      .concat(vals.map(v => el('option', { value: String(v), text: (f.label ? f.label(v) : v) }))));
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
      const v = st[f.h];
      if (v) out = out.filter(r => String(f.v(r)) === v);
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
    hero(Object.assign({ icon: null }, m, { icon: (maps.flatMap(p => p.monsters).find(x => x.id === id) || {}).icon }),
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
  const rows = await data('maps');
  return listPage('地圖', `${rows.length} 張。`, rows, [
    { h: '名稱', c: p => itemCell(p, 'maps') },
    { h: '區域', c: p => p.region },
    { h: '類型', c: p => p.capsLabel },
    { h: '需求等級', n: true, v: p => p.levelReq, c: p => p.levelReq || '—' },
    { h: '怪物種類', n: true, v: p => p.monsters.length, c: p => p.monsters.length || '' },
    { h: 'NPC', n: true, v: p => p.npcs.length, c: p => p.npcs.length || '' },
  ], [{ h: '區域', v: p => p.region }, { h: '類型', v: p => p.capsLabel }], { sort: 3, desc: false });
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

/* 裝備 / 時裝 / 道具共用一套明細 */
function gearDetail(kind, listName, backLabel) {
  return async id => {
    const rows = await data(listName);
    const o = byId(rows, id);
    if (!o) return el('p', { class: 'empty', text: '找不到這個項目。' });
    const st = statText(o.stats);
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

V.equips = async () => {
  const rows = await data('equips');
  return listPage('戰鬥裝備', `${num(rows.length)} 件。可按部位、職業、等級篩選。`, rows,
    gearCols([
      { h: '攻擊', n: true, v: o => o.attack ? o.attack.max : 0, c: o => o.attack ? `${o.attack.min}–${o.attack.max}` : '' },
      { h: '附加能力', wrap: true, c: o => statText(o.stats).join('、') },
      { h: '職業', c: o => (o.classes || []).map(clsName).join('、') || '全職業' },
    ]),
    [{ h: '部位', v: o => o.slotGroup },
     { h: '職業', v: o => (o.classes || []).map(clsName).join('、') || '全職業' }],
    { sort: 2, desc: false });
};
V.equip = gearDetail('equips', 'equips', '裝備列表');

V.fashion = async () => {
  const rows = await data('fashion');
  return listPage('時裝', `${num(rows.length)} 件。`, rows,
    gearCols([{ h: '性別', c: o => T.gender[o.gender] || '' },
              { h: '期限', c: o => o.useTerm ? o.useTerm + ' 天' : '永久' }]),
    [{ h: '部位', v: o => o.slotGroup }, { h: '性別', v: o => T.gender[o.gender] || '' }],
    { sort: 2, desc: false });
};
V.fashionItem = gearDetail('fashion', 'fashion', '時裝列表');

V.items = async () => {
  const rows = await data('items');
  return listPage('道具', `${num(rows.length)} 種。`, rows, [
    { h: '名稱', c: o => itemCell(o) },
    { h: '分類', c: o => o.category },
    { h: '說明', wrap: true, c: o => (o.desc || '').split('\n')[0] },
    { h: '價格', n: true, v: o => o.price, c: o => num(o.price) },
    { h: '堆疊', n: true, v: o => o.maxStack, c: o => o.maxStack > 1 ? o.maxStack : '' },
  ], [{ h: '分類', v: o => o.category }], { sort: 1, desc: false });
};
V.item = gearDetail('items', 'items', '道具列表');

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
    section('所需材料', r.ingredients, [
      { h: '材料', c: i => itemCell(i) },
      { h: '數量', n: true, v: i => i.count, c: i => i.count },
    ]),
    section('可製作的 NPC', r.npcs, [{ h: 'NPC', c: n => itemCell(n, 'npcs') }]),
    section('配方掉落來源', r.recipeItemDroppedBy, fromMonCols, { sort: 2 }),
  ]);
};

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
  return listPage('NPC', `${rows.length} 位。`, rows, [
    { h: '名稱', c: n => itemCell(n, 'npcs') },
    { h: '職務', c: n => n.job || '' },
    { h: '區域', c: n => n.region || '' },
    { h: '所在地', c: n => (n.maps || []).map(m => m.name).join('、') },
    { h: '功能', c: n => (n.roleLabels || []).join('、') },
  ], [{ h: '區域', v: n => n.region }, { h: '功能', v: n => (n.roleLabels || [])[0] || '' }]);
};

V.npc = async id => {
  const [rows, quests] = await Promise.all([data('npcs'), data('quests')]);
  const n = byId(rows, id);
  if (!n) return el('p', { class: 'empty', text: '找不到這位 NPC。' });
  const qs = quests.filter(q => q.npcs.some(x => x.id === id));
  return frag([
    back('#/npcs', 'NPC 列表'),
    hero(n, tags([n.region ? [n.region, 'a'] : null, n.job || null,
                  ...(n.roleLabels || []).map(r => [r, 'g'])])),
    section('所在地', n.maps, [
      { h: '地圖', c: m => itemCell(m, 'maps') },
      { h: '座標', c: m => (m.x || m.y) ? `${m.x}, ${m.y}` : '' },
    ]),
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
    `依「每點 HP 能換到多少經驗」排序 —— 數字越高，打死一隻的效益越好。共 ${rows.length} 張有怪地圖。`,
    rows, [
      { h: '地圖', c: g => itemCell(g, 'maps') },
      { h: '區域', c: g => g.region },
      { h: '平均等級', n: true, v: g => g.avgLv, c: g => g.avgLv },
      { h: '效率', n: true, v: g => g.eff, c: g => el('b', { text: g.eff.toFixed(2) }),
        title: '平均經驗 ÷ 平均 HP' },
      { h: '平均經驗', n: true, v: g => g.exp, c: g => num(g.exp) },
      { h: '平均 HP', n: true, v: g => g.hp, c: g => num(g.hp) },
      { h: '平均掉錢', n: true, v: g => g.money, c: g => num(g.money) },
      { h: '主動怪', n: true, v: g => g.aggressive, c: g => g.aggressive ? g.aggressive + ' 種' : '' },
      { h: '怪物種類', n: true, v: g => g.kinds, c: g => g.kinds },
    ], [{ h: '區域', v: g => g.region }, { h: '類型', v: g => g.type }], { sort: 3 });
};

/* ───────── wiki 補充：技能 / 徽章 / 系統 ───────── */
V.skills = async () => {
  const w = await data('wiki');
  const rows = w.skills.map((s, i) => Object.assign({ _i: i }, s));
  return listPage('技能', `${rows.length} 個。點名稱看各等級數值。`, rows, [
    { h: '名稱', c: s => el('a', { href: '#/skills/' + s._i, text: s.name }) },
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
    el('h1', { text: s.name }),
    tags([s.job ? [s.job, 'a'] : null, s.type ? [s.type, 'g'] : null]),
    s.desc ? el('p', { class: 'desc', text: s.desc }) : null,
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

V.system = async () => {
  const w = await data('wiki');
  const kv = (title, obj) => frag([el('h3', { text: title }), el('dl', { class: 'detail' },
    Object.entries(obj).flatMap(([k, v]) =>
      [el('dt', { text: k }), el('dd', { text: Array.isArray(v) ? v.join(' → ') : v })]))]);
  const rawTable = t => el('div', { class: 'tw' }, [el('table', {}, [
    el('thead', {}, [el('tr', {}, t.headers.map(h => el('th', { text: h })))]),
    el('tbody', {}, t.rows.map(r => el('tr', {}, r.c.map(c => el('td', { class: 'wrap', text: c }))))),
  ])]);

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
    ['skills', '技能', '154 個'],
    ['badges', '徽章', '58 枚'],
    ['system', '遊戲系統', '屬性 · 轉職 · 題庫'],
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
const NAV = [['', '首頁'], ['grind', '練功'], ['monsters', '怪物'], ['maps', '地圖'],
             ['equips', '裝備'], ['fashion', '時裝'], ['items', '道具'], ['recipes', '製作'],
             ['quests', '任務'], ['npcs', 'NPC'], ['skills', '技能'], ['badges', '徽章'],
             ['system', '系統']];

const ROUTE = {
  '': V.home, grind: V.grind,
  monsters: V.monsters, maps: V.maps, equips: V.equips, fashion: V.fashion,
  items: V.items, recipes: V.recipes, quests: V.quests, npcs: V.npcs,
  skills: V.skills, badges: V.badges, system: V.system,
};
const ROUTE1 = {
  monsters: V.monster, maps: V.map, equips: V.equip, fashion: V.fashionItem,
  items: V.item, recipes: V.recipe, quests: V.quest, npcs: V.npc, skills: V.skill,
};

function drawNav(active) {
  $('#nav').textContent = '';
  for (const [h, t] of NAV) {
    $('#nav').appendChild(el('a', { href: '#/' + h, text: t, class: h === active ? 'on' : '' }));
  }
}

async function route() {
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
