#!/usr/bin/env node
/*
 * Quest timeline audit.
 * This is intentionally independent from the browser renderer: it checks the
 * source records first, then the relations used to build the timeline.
 */
const fs = require('fs');

const read = name => JSON.parse(fs.readFileSync(`docs/data/${name}.json`, 'utf8'));
const quests = read('quests');
const monsters = read('monsters');
const items = read('items');
const byQuest = new Map(quests.map(q => [q.id, q]));
const byMonster = new Map(monsters.map(m => [m.id, m]));
const byItem = new Map(items.map(i => [i.id, i]));
const baseName = name => String(name || '').replace(/^\[[^\]]+\]\s*/, '').trim();
const drops = new Map();
for (const monster of monsters) for (const drop of monster.drops || []) {
  if (!drops.has(drop.id)) drops.set(drop.id, []);
  drops.get(drop.id).push(monster);
}

const errors = [];
const warnings = [];
const collectRows = [];
const huntRows = [];
for (const quest of quests) {
  for (const prereq of quest.prereq || []) {
    if (!byQuest.has(prereq.id)) errors.push(`缺少前置任務：${quest.id} -> ${prereq.id}`);
  }
  for (const objective of quest.hunt || []) {
    huntRows.push({ quest, objective });
    if (!byMonster.has(objective.target?.id)) errors.push(`缺少討伐怪物：${quest.id} -> ${objective.target?.id}`);
  }
  for (const objective of quest.collect || []) {
    const sources = drops.get(objective.target?.id) || [];
    collectRows.push({ quest, objective, sources });
    // Quest records carry an authoritative embedded target.  It is valid even
    // when the normalized items index does not contain equipment/reward IDs.
    if (!byItem.has(objective.target?.id) && !objective.target?.name) errors.push(`缺少蒐集物品：${quest.id} -> ${objective.target?.id}`);
    if (!sources.length) warnings.push(`蒐集來源未記錄：${quest.id} ${objective.target?.name || objective.target?.id}`);
  }
}

// One execution group per normalized monster name. Collection tasks attach to
// every monster that actually drops the requested item.
const groups = new Map();
const attach = (key, quest, kind, target) => {
  if (!key) return;
  if (!groups.has(key)) groups.set(key, { tasks: new Map(), variants: new Set() });
  const group = groups.get(key);
  if (!group.tasks.has(quest.id)) group.tasks.set(quest.id, new Set());
  group.tasks.get(quest.id).add(kind);
  if (target?.id) group.variants.add(target.id);
};
for (const row of huntRows) attach(baseName(row.objective.target?.name), row.quest, '討伐', row.objective.target);
for (const row of collectRows) for (const source of row.sources) attach(baseName(source.name), row.quest, '蒐集', source);

// NPC queue is a real dependency: one NPC can expose only one task at a time.
const npcChains = new Map();
quests.forEach((quest, index) => (quest.npcs || []).forEach(npc => {
  if (!npcChains.has(npc.id)) npcChains.set(npc.id, []);
  npcChains.get(npc.id).push({ quest, index });
}));
for (const chain of npcChains.values()) chain.sort((a, b) => (a.quest.levelReq || 0) - (b.quest.levelReq || 0) || a.index - b.index);
const deps = new Map(quests.map(q => [q.id, new Set((q.prereq || []).map(p => p.id))]));
for (const chain of npcChains.values()) chain.forEach((entry, index) => {
  if (index) deps.get(entry.quest.id).add(chain[index - 1].quest.id);
});
const indegree = new Map(quests.map(q => [q.id, 0]));
const edges = new Map(quests.map(q => [q.id, new Set()]));
for (const [id, parents] of deps) for (const parent of parents) {
  if (!byQuest.has(parent)) continue;
  edges.get(parent).add(id);
  indegree.set(id, indegree.get(id) + 1);
}
const ready = quests.filter(q => !indegree.get(q.id)).sort((a, b) => (a.levelReq || 0) - (b.levelReq || 0) || a.id.localeCompare(b.id));
const order = new Map();
while (ready.length) {
  const quest = ready.shift();
  order.set(quest.id, order.size);
  for (const next of edges.get(quest.id)) {
    indegree.set(next, indegree.get(next) - 1);
    if (!indegree.get(next)) ready.push(byQuest.get(next));
  }
  ready.sort((a, b) => (a.levelReq || 0) - (b.levelReq || 0) || a.id.localeCompare(b.id));
}
if (order.size !== quests.length) errors.push(`任務依賴圖有循環或無法排序：${quests.length - order.size} 筆`);
for (const [id, parents] of deps) for (const parent of parents) {
  if (order.has(id) && order.has(parent) && order.get(parent) >= order.get(id)) errors.push(`拓樸倒置：${parent} -> ${id}`);
}

const depthMemo = new Map();
const depthVisiting = new Set();
const routeDepth = id => {
  if (depthMemo.has(id)) return depthMemo.get(id);
  if (depthVisiting.has(id)) return 0;
  depthVisiting.add(id);
  const value = Math.max(0, ...[...(deps.get(id) || [])].map(parent => byQuest.has(parent) ? routeDepth(parent) + 1 : 0));
  depthVisiting.delete(id);
  depthMemo.set(id, value);
  return value;
};
const npcPrevious = new Map();
for (const chain of npcChains.values()) chain.forEach((entry, index) => {
  if (index) npcPrevious.set(entry.quest.id, chain[index - 1].quest);
});
const huntNamesByQuest = new Map(quests.map(q => [q.id, new Set()]));
for (const row of huntRows) huntNamesByQuest.get(row.quest.id).add(baseName(row.objective.target?.name));
for (const row of collectRows) for (const source of row.sources) huntNamesByQuest.get(row.quest.id).add(baseName(source.name));

// This is the auditable, row-by-row source of truth used to review the UI.
const taskAudit = quests.map(q => ({
  id: q.id,
  name: q.name,
  level: q.levelReq || 0,
  regions: q.regions || [],
  npcs: (q.npcs || []).map(n => ({ id: n.id, name: n.name })),
  explicitPrerequisites: (q.prereq || []).map(p => ({ id: p.id, name: p.name })),
  npcPrevious: npcPrevious.has(q.id) ? { id: npcPrevious.get(q.id).id, name: npcPrevious.get(q.id).name } : null,
  routeDepth: routeDepth(q.id),
  topoOrder: order.has(q.id) ? order.get(q.id) : null,
  hunt: (q.hunt || []).map(x => ({ target: x.target, count: x.count, monsterExists: byMonster.has(x.target?.id) })),
  collect: (q.collect || []).map(x => ({
    target: x.target,
    count: x.count,
    dropMonsters: (drops.get(x.target?.id) || []).map(m => ({ id: m.id, name: m.name })),
  })),
  delivery: q.delivery || [],
  dungeon: q.indun || [],
  monsterGroups: [...huntNamesByQuest.get(q.id)].filter(Boolean).sort(),
}));

const report = {
  counts: {
    quests: quests.length,
    monsters: monsters.length,
    items: items.length,
    huntRequirements: huntRows.length,
    collectRequirements: collectRows.length,
    collectWithMonsterSource: collectRows.filter(x => x.sources.length).length,
    executionGroups: groups.size,
  },
  errors,
  warnings,
  taskAudit,
  mappings: {
    hunt: huntRows.map(row => ({
      questId: row.quest.id,
      questName: row.quest.name,
      level: row.quest.levelReq || 0,
      target: row.objective.target,
      count: row.objective.count,
      monster: byMonster.get(row.objective.target?.id) || null,
    })),
    collect: collectRows.map(row => ({
      questId: row.quest.id,
      questName: row.quest.name,
      level: row.quest.levelReq || 0,
      target: row.objective.target,
      count: row.objective.count,
      dropMonsters: row.sources.map(m => ({ id: m.id, name: m.name })),
    })),
  },
  monsterGroups: [...groups.entries()].map(([name, group]) => ({
    monster: name,
    levels: [...group.tasks.values()].map(kinds => [...kinds]).length ? [...group.tasks.keys()].map(id => byQuest.get(id).levelReq || 0).sort((a, b) => a - b) : [],
    tasks: [...group.tasks.keys()].map(id => ({ id, name: byQuest.get(id).name, level: byQuest.get(id).levelReq || 0, kinds: [...group.tasks.get(id)] })),
  })),
};
console.log(JSON.stringify(report, null, 2));
process.exitCode = errors.length ? 1 : 0;
