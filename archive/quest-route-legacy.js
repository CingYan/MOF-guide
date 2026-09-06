/* 舊版任務路線（已停用）
 * 目前網站改用 docs/app.js 內的任務流程頁；本檔僅供歷史參考，不會被 index.html 載入。
 */

/* 任務路線：給玩家實際照著跑的版本。
   先按前置深度分段，再按區域整理「接取 → 一次完成 → 回報」；
   同區域同一目標只列一次，避免把可一起完成的目標拆散。 */
V.questRoute = async () => {
  const [quests, monsters] = await Promise.all([data('quests'), data('monsters')]);
  const byQuest = new Map(quests.map(q => [q.id, q])), memo = new Map();
  function depth(q, trail = new Set()) {
    if (memo.has(q.id)) return memo.get(q.id);
    if (trail.has(q.id)) return 0;
    trail.add(q.id);
    const d = (q.prereq || []).reduce((n, p) => Math.max(n, depth(byQuest.get(p.id), trail) + 1), 0);
    trail.delete(q.id); memo.set(q.id, d); return d;
  }
  const drops = new Map();
  monsters.forEach(m => (m.drops || []).forEach(d => {
    if (!drops.has(d.id)) drops.set(d.id, []);
    drops.get(d.id).push(m);
  }));
  const done = JSON.parse(localStorage.getItem('mof-quest-route-done') || '{}');
  const collected = JSON.parse(localStorage.getItem('mof-quest-route-collected') || '{}');
  const saveCollected = () => localStorage.setItem('mof-quest-route-collected', JSON.stringify(collected));
  const root = el('div', { class: 'quest-route' });
  const list = el('div', { class: 'quest-route-list' });
  const search = el('input', { type: 'search', placeholder: '篩選區域、NPC、怪物或任務' });
  const fromLevel = el('input', { type: 'number', min: 1, max: 110, placeholder: '例如 60', 'aria-label': '目前等級' });
  const toLevel = el('input', { type: 'number', min: 1, max: 110, placeholder: '例如 110', 'aria-label': '目標等級' });
  const onlyOpen = el('input', { type: 'checkbox', 'aria-label': '只看未完成' });
  const summary = el('p', { class: 'lead' });
  const monsterById = new Map(monsters.map(m => [m.id, m]));
  const monsterGroups = new Map();
  const questMonsterIds = new Map();
  const addMonsterQuest = (m, q, objective) => {
    if (!m?.id || !objective?.target?.id) return;
    const groupKey = m.name.replace(/^\[[^\]]+\]\s*/, '').trim() || m.id;
    if (!monsterGroups.has(groupKey)) monsterGroups.set(groupKey, { monster: m, monsters: new Map(), quests: [], objectives: new Map() });
    const g = monsterGroups.get(groupKey);
    g.monsters.set(m.id, m);
    if (!g.quests.some(x => x.id === q.id)) g.quests.push(q);
    const key = objective.type + ':' + objective.target.id;
    if (!g.objectives.has(key)) g.objectives.set(key, { type: objective.type, target: objective.target, count: 0 });
    g.objectives.get(key).count += Number(objective.count) || 0;
    if (!questMonsterIds.has(q.id)) questMonsterIds.set(q.id, new Set());
    questMonsterIds.get(q.id).add(m.id);
  };
  quests.forEach(q => {
    (q.hunt || []).forEach(x => addMonsterQuest(monsterById.get(x.target?.id), q, { type: '討伐', target: x.target, count: x.count }));
    (q.collect || []).forEach(x => {
      // 同一掉落物可能有多個來源；任務只放入第一個來源群，避免玩家看到重複任務。
      // 其他來源仍可由道具頁查看，實際狩獵時可自行選擇。
      const source = (drops.get(x.target?.id) || [])[0];
      if (source) addMonsterQuest(source, q, { type: '蒐集', target: x.target, count: x.count });
    });
  });
  const npcChains = new Map();
  quests.forEach((q, index) => (q.npcs || []).forEach(n => {
    if (!npcChains.has(n.id)) npcChains.set(n.id, []);
    npcChains.get(n.id).push({ q, index });
  }));
  npcChains.forEach(chain => chain.sort((a, b) => (a.q.levelReq || 0) - (b.q.levelReq || 0) || a.index - b.index));
  const npcPrevious = new Map();
  npcChains.forEach(chain => chain.forEach((entry, i) => {
    if (i > 0) npcPrevious.set(entry.q.id, chain[i - 1].q);
  }));
  const routeMemo = new Map();
  function routeDepth(q, trail = new Set()) {
    if (routeMemo.has(q.id)) return routeMemo.get(q.id);
    if (trail.has(q.id)) return 0;
    trail.add(q.id);
    const deps = [...(q.prereq || []).map(p => byQuest.get(p.id)).filter(Boolean), npcPrevious.get(q.id)].filter(Boolean);
    const d = deps.reduce((n, p) => Math.max(n, routeDepth(p, trail) + 1), 0);
    trail.delete(q.id); routeMemo.set(q.id, d); return d;
  }
  const chainInfo = (q, npc) => {
    const chain = npcChains.get(npc.id) || [], i = chain.findIndex(x => x.q.id === q.id);
    return i > 0 ? `NPC 排隊前置：${chain[i - 1].q.name}（完成並回報後才能接）` : '';
  };
  function draw() {
    const needle = search.value.trim().toLocaleLowerCase();
    const start = Math.max(1, Number(fromLevel.value) || 1), end = Math.max(start, Number(toLevel.value) || 110);
    const openState = new Map([...list.querySelectorAll('details[data-route-key]')]
      .map(node => [node.dataset.routeKey, node.open]));
    const isOpen = key => openState.has(key) ? openState.get(key) : !!needle;
    list.textContent = '';
    let shown = 0, finished = 0, total = 0;
    const groups = [...monsterGroups.values()].map(g => {
      const selected = g.quests.filter(q => (Number(q.levelReq) || 0) >= start && (Number(q.levelReq) || 0) <= end);
      return { ...g, selected };
    }).filter(g => g.selected.length);
    const areaGroups = new Map();
    groups.forEach(g => {
      const area = g.selected.find(q => q.regions?.some(Boolean))?.regions?.find(Boolean) || g.monster.regions?.find(Boolean) || '未分類區域';
      if (!areaGroups.has(area)) areaGroups.set(area, []);
      areaGroups.get(area).push(g);
    });
    [...areaGroups.values()].forEach(gs => gs.sort((a, b) => (a.monster.level || 0) - (b.monster.level || 0) || a.monster.name.localeCompare(b.monster.name, 'zh-Hant')));
    const areaMinLevel = new Map();
    quests.forEach(q => (q.regions || []).filter(Boolean).forEach(area => {
      const level = Number(q.levelReq) || 0;
      areaMinLevel.set(area, Math.min(areaMinLevel.get(area) ?? Infinity, level));
    }));
    const orderedAreas = [...areaGroups.entries()].sort(([, a], [, b]) =>
      (areaMinLevel.get(a[0]) ?? Math.min(...a.flatMap(g => g.selected.map(q => Number(q.levelReq) || 0)))) -
      (areaMinLevel.get(b[0]) ?? Math.min(...b.flatMap(g => g.selected.map(q => Number(q.levelReq) || 0)))));
    const areaDetails = new Map();
    orderedAreas.forEach(([area, areaMonsterGroups]) => {
      const areaList = el('div', { class: 'quest-route-monster-list' });
      areaMonsterGroups.forEach(g => {
      const qs = g.selected.slice().sort((a, b) => routeDepth(a) - routeDepth(b) || (a.levelReq || 0) - (b.levelReq || 0) || a.name.localeCompare(b.name, 'zh-Hant'));
      const hay = [g.monster.name, ...(g.monster.regions || []), ...(g.monster.maps || []).map(m => m.name), ...qs.flatMap(q => [q.name, ...(q.npcs || []).map(n => n.name), ...(q.hunt || []).map(x => x.target.name), ...(q.collect || []).map(x => x.target.name)])].join(' ').toLocaleLowerCase();
      const allDone = qs.every(q => done[q.id]); total += qs.length; if (allDone) finished++;
      if ((needle && !hay.includes(needle)) || (onlyOpen.checked && allDone)) return;
      shown++;
      const makeCheck = q => {
        const c = el('input', { type: 'checkbox', checked: !!done[q.id], 'aria-label': `標記任務 ${q.name} 完成` });
        c.onchange = () => { done[q.id] = c.checked; localStorage.setItem('mof-quest-route-done', JSON.stringify(done)); draw(); };
        const groupMonsterIds = new Set(g.monsters.keys());
        const objectives = [
          ...(q.hunt || []).filter(x => groupMonsterIds.has(x.target?.id)).map(x =>
            el('span', {}, ['討伐 ', itemCell(x.target, 'monsters'), ` ×${num(x.count)}`])),
          ...(q.collect || []).filter(x => (drops.get(x.target?.id) || []).some(m => groupMonsterIds.has(m.id))).map(x =>
            el('span', {}, ['蒐集 ', itemCell(x.target, 'items'), ` ×${num(x.count)}`])),
        ];
        const actions = (q.delivery || []).map(d => `遞送：${d.item?.name || '指定物品'}${d.to?.name ? ` → ${d.to.name}` : ''}`);
        const npcText = (q.npcs || []).map(n => n.name).join('、') || '無 NPC';
        const prev = (q.npcs || []).map(n => chainInfo(q, n)).filter(Boolean).join('；');
        return el('li', { class: 'quest-route-task' }, [el('label', {}, [c, el('a', { href: '#/quests/' + q.id, text: q.name }),
          el('span', { class: 'dim', text: `（Lv.${q.levelReq || 0}｜${npcText}）` })]),
          objectives.length ? el('span', { class: 'quest-route-condition' }, [
            '條件：', ...objectives.flatMap((part, i) => [i ? '、' : '', part]),
          ]) : el('span', { class: 'quest-route-condition quest-route-muted', text: '條件：無狩獵／蒐集' }),
          (q.prereq || []).length ? el('span', { class: 'quest-route-meta', text: '明確前置：' + q.prereq.map(x => x.name).join('、') }) : null,
          prev ? el('span', { class: 'quest-route-meta quest-route-warning', text: prev }) : null,
          actions.length ? el('span', { class: 'quest-route-meta quest-route-action', text: actions.join('；') }) : null]);
      };
      const objectiveTotals = new Map();
      qs.forEach(q => {
        (q.hunt || []).filter(x => g.monsters.has(x.target?.id)).forEach(x => {
          const key = '討伐:' + g.monster.name.replace(/^\[[^\]]+\]\s*/, '').trim();
          const current = objectiveTotals.get(key) || { type: '討伐', target: g.monster, count: 0, variants: new Map() };
          current.count += Number(x.count) || 0;
          current.variants.set(x.target.id, (current.variants.get(x.target.id) || 0) + (Number(x.count) || 0));
          objectiveTotals.set(key, current);
        });
        (q.collect || []).filter(x => (drops.get(x.target?.id) || []).some(m => g.monsters.has(m.id))).forEach(x => {
          const key = '蒐集:' + x.target.id;
          objectiveTotals.set(key, { type: '蒐集', target: x.target, count: (objectiveTotals.get(key)?.count || 0) + (Number(x.count) || 0) });
        });
      });
      const objectiveList = [...objectiveTotals.values()].map(o => {
        if (o.type === '討伐') {
          const variantSummary = [...o.variants.entries()].map(([id, count], i) => {
            const variant = g.monsters.get(id);
            const label = variant?.name?.startsWith('[') ? variant.name.match(/^\[([^\]]+)\]/)?.[1] || '變體' : '普通';
            return `${i ? '、' : ''}${label} ×${num(count)}`;
          }).join('');
          return el('li', {}, [el('span', { class: 'tag r', text: '討伐' }), ' ',
            itemCell(o.target, 'monsters'), `（${variantSummary}；同一狩獵批次）`]);
        }
        const owned = Math.min(Math.max(Number(collected[o.target.id]) || 0, 0), o.count);
        const remain = Math.max(0, o.count - owned);
        const amount = el('input', { type: 'number', min: 0, max: o.count, value: owned,
          class: 'quest-route-progress-input', 'aria-label': `${o.target.name} 已取得數量` });
        amount.onchange = () => {
          collected[o.target.id] = Math.min(Math.max(Number(amount.value) || 0, 0), o.count);
          saveCollected(); draw();
        };
        const complete = el('input', { type: 'checkbox', checked: remain === 0,
          'aria-label': `完成蒐集 ${o.target.name}` });
        complete.onchange = () => {
          collected[o.target.id] = complete.checked ? o.count : 0;
          saveCollected(); draw();
        };
        return el('li', {}, [el('span', { class: 'tag a', text: '蒐集' }), ' ',
          itemCell(o.target, 'items'), ` 共 ${num(o.count)}｜尚缺 ${num(remain)} `,
          amount, ' ', el('label', { class: 'quest-route-progress-check' }, [complete, '完成'])]);
      });
      const variants = [...g.monsters.values()];
      const maps = [...new Set(variants.flatMap(m => (m.maps || []).map(x => x.name)))];
      const variantText = variants.length > 1 ? `變體：${variants.map(m => m.name).join('、')}` : '';
      const batches = [...qs.reduce((map, q) => {
        const stage = routeDepth(q);
        if (!map.has(stage)) map.set(stage, []);
        map.get(stage).push(q);
        return map;
      }, new Map()).entries()];
      const earlyCollections = [...new Map(qs.flatMap(q => (q.collect || [])
        .filter(x => (drops.get(x.target?.id) || []).some(m => g.monsters.has(m.id)))
        .map(x => [x.target.id, x.target]))).values()];
      areaList.appendChild(el('details', { class: 'quest-route-monster', 'data-route-key': `monster:${area}:${g.monster.id}`, open: isOpen(`monster:${area}:${g.monster.id}`) }, [
        el('summary', { class: 'quest-route-monster-summary', text: `${g.monster.name}（Lv.${Math.min(...variants.map(m => m.level || 0))}）｜${maps.join('、') || '出沒地圖未記錄'}｜${qs.length} 個相關任務` }),
        variantText ? el('p', { class: 'quest-route-meta quest-route-variants', text: variantText }) : null,
        el('p', { class: 'quest-route-meta quest-route-hunt-guide', text: '以下依任務解鎖條件排列：先接取本批任務，再依「本批狩獵目標」一次完成，最後回報並進入下一批。之後才解鎖的任務不會提前計入。' }),
        el('details', { class: 'quest-route-objectives', open: true }, [el('summary', { text: '本群需求總覽（含後續任務；實際依批次解鎖）' }), el('ul', {}, objectiveList)]),
        el('h3', { text: '任務時間軸（接取 → 狩獵 → 回報）' }),
        earlyCollections.length ? el('p', { class: 'quest-route-meta quest-route-prep', text: `可提前準備蒐集品：${earlyCollections.map(x => x.name).join('、')}；即使後續任務尚未解鎖，取得的物品也會記錄在背包。` }) : null,
        frag(batches.map(([stage, batch], batchIndex) => el('section', { class: 'quest-route-batch' }, [
          el('h4', { text: `第 ${batchIndex + 1} 批｜任務鏈第 ${stage + 1} 階（解鎖：Lv.${[...new Set(batch.map(q => Number(q.levelReq) || 0))].sort((a, b) => a - b).join('、')}）` }),
          el('strong', { class: 'quest-route-step-label', text: '① 先接取' }),
          el('ol', { class: 'quest-route-tasks' }, batch.sort((a, b) => (a.levelReq || 0) - (b.levelReq || 0) || routeDepth(a) - routeDepth(b) || a.name.localeCompare(b.name, 'zh-Hant')).map(makeCheck)),
          (() => {
            const batchObjectives = new Map();
            batch.forEach(q => {
              (q.hunt || []).filter(x => g.monsters.has(x.target?.id)).forEach(x => {
                const key = '討伐:' + x.target.id;
                batchObjectives.set(key, { type: '討伐', target: x.target, count: (batchObjectives.get(key)?.count || 0) + (Number(x.count) || 0) });
              });
              (q.collect || []).filter(x => (drops.get(x.target?.id) || []).some(m => g.monsters.has(m.id))).forEach(x => {
                const key = '蒐集:' + x.target.id;
                batchObjectives.set(key, { type: '蒐集', target: x.target, count: (batchObjectives.get(key)?.count || 0) + (Number(x.count) || 0) });
              });
            });
            const objectives = [...batchObjectives.values()].map(o => {
              if (o.type === '討伐') return el('li', {}, [el('span', { class: 'tag r', text: '討伐' }), ' ', itemCell(o.target, 'monsters'), ` ×${num(o.count)}`]);
              const owned = Math.min(Math.max(Number(collected[o.target.id]) || 0, 0), o.count);
              return el('li', {}, [el('span', { class: 'tag a', text: '蒐集' }), ' ', itemCell(o.target, 'items'),
                ` ×${num(o.count)}｜目前尚缺 ${num(Math.max(0, o.count - owned))}`]);
            });
            const npcs = [...new Set(batch.flatMap(q => (q.npcs || []).map(n => n.name)))];
            return frag([
              el('strong', { class: 'quest-route-step-label', text: '② 前往狩獵' }),
              objectives.length ? el('ul', { class: 'quest-route-batch-objectives' }, objectives) : el('p', { class: 'quest-route-meta quest-route-muted', text: '本批沒有討伐／蒐集目標，完成任務動作即可。' }),
              el('strong', { class: 'quest-route-step-label', text: '③ 完成並回報' }),
              el('p', { class: 'quest-route-meta quest-route-action', text: npcs.length ? `回報：${npcs.join('、')}；回報後才進入下一批。` : '本批沒有記錄回報 NPC。' }),
            ]);
          })(),
        ]))),
      ]));
      });
      if (!areaList.childNodes.length) return;
      const areaDetail = el('details', { class: 'quest-route-area', 'data-route-key': `area:${area}`, open: isOpen(`area:${area}`) }, [
        el('summary', { class: 'quest-route-area-summary', text: `${area}｜${areaMonsterGroups.length} 個怪物群` }),
        areaList,
      ]);
      areaDetails.set(area, { detail: areaDetail, content: areaList });
      list.appendChild(areaDetail);
    });
    const areaOf = q => (q.regions || [])[0] || '未分類區域';
    const otherAreas = new Map();
    quests.filter(q => !questMonsterIds.has(q.id)).forEach(q => {
      const area = areaOf(q);
      if (!otherAreas.has(area)) otherAreas.set(area, []);
      otherAreas.get(area).push(q);
    });
    otherAreas.forEach((areaQuests, area) => {
      const qs = areaQuests.filter(q => (Number(q.levelReq) || 0) >= start && (Number(q.levelReq) || 0) <= end)
        .sort((a, b) => (a.levelReq || 0) - (b.levelReq || 0) || a.name.localeCompare(b.name, 'zh-Hant'));
      const hay = [area, ...qs.flatMap(q => [q.name, ...(q.npcs || []).map(n => n.name)])].join(' ').toLocaleLowerCase();
      const allDone = qs.length > 0 && qs.every(q => done[q.id]);
      total += qs.length; if (allDone) finished++;
      if (!qs.length || (needle && !hay.includes(needle)) || (onlyOpen.checked && allDone)) return;
      shown++;
      const rows = qs.map(q => {
        const c = el('input', { type: 'checkbox', checked: !!done[q.id], 'aria-label': `標記任務 ${q.name} 完成` });
        c.onchange = () => { done[q.id] = c.checked; localStorage.setItem('mof-quest-route-done', JSON.stringify(done)); draw(); };
        const actions = [
          ...(q.delivery || []).map(d => `遞送：${d.item?.name || '指定物品'}${d.to?.name ? ` → ${d.to.name}` : ''}`),
          ...(q.indun || []).map(d => `副本：${d.dungeon}${d.entryItem?.name ? `｜入場道具：${d.entryItem.name}` : ''}`),
        ];
        return el('li', { class: 'quest-route-task' }, [el('label', {}, [c, el('a', { href: '#/quests/' + q.id, text: q.name }),
          el('span', { class: 'dim', text: `（Lv.${q.levelReq || 0}｜${(q.npcs || []).map(n => n.name).join('、') || '無 NPC'}）` })]),
          el('span', { class: 'quest-route-condition quest-route-muted', text: actions.join('；') || '條件：劇情／對話' }),
          (q.prereq || []).length ? el('span', { class: 'quest-route-meta', text: '明確前置：' + q.prereq.map(x => x.name).join('、') }) : null]);
      });
      const otherSection = el('section', { class: 'quest-route-other' }, [
        el('h3', { text: `其他任務（${qs.length}）` }),
        el('p', { class: 'quest-route-meta', text: '這些任務沒有可連回野外怪物的討伐／掉落條件，仍可能是遞送、副本或 NPC 劇情前置。' }),
        el('ol', { class: 'quest-route-tasks' }, rows),
      ]);
      if (areaDetails.has(area)) {
        areaDetails.get(area).content.appendChild(otherSection);
      } else {
        const content = el('div', { class: 'quest-route-monster-list' }, [otherSection]);
        const detail = el('details', { class: 'quest-route-area', 'data-route-key': `area:${area}`, open: isOpen(`area:${area}`) }, [
          el('summary', { class: 'quest-route-area-summary', text: `${area}｜其他任務` }), content,
        ]);
        areaDetails.set(area, { detail, content });
        list.appendChild(detail);
      }
    });
    summary.textContent = `目前顯示 ${shown} 個任務內容區塊；篩選範圍 Lv.${start}～Lv.${end}，共 ${total} 個任務、${finished} 個已完成區塊。以怪物為主軸集中狩獵；等級只代表解鎖條件，同 NPC 任務須完成並回報前一個後才能接下一個。`;
  }
  search.oninput = draw; onlyOpen.onchange = draw; fromLevel.oninput = draw; toLevel.oninput = draw;
  root.append(el('h1', { text: '任務路線' }), el('p', { class: 'sub', text: '以怪物為主軸串起討伐與掉落任務；同一怪物集中完成，等級只作為任務解鎖條件。每個任務後直接顯示需求；同 NPC 任務須完成並回報前一個後才能接下一個。' }),
    el('div', { class: 'filters quest-route-filters' }, [el('label', {}, ['目前 Lv.', fromLevel]), el('label', {}, ['目標 Lv.', toLevel]), search, el('label', {}, [onlyOpen, '只看未完成'])]), summary, list);
  draw(); return root;
};
