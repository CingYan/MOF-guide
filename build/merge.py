# -*- coding: utf-8 -*-
"""合併私服資料（主）與 wiki 資料（補充）成網站資料層"""
import json, os, shutil, collections

SRC, OUT = 'private/raw', 'docs/data'
os.makedirs(OUT, exist_ok=True)

# ---- 1. 私服八大資料，原樣搬過去 ----
DOMAINS = ['monsters','maps','equips','fashion','items','recipes','quests','npcs']
counts = {}
for d in DOMAINS:
    data = json.load(open(f'{SRC}/{d}.json'))
    counts[d] = len(data)
    json.dump(data, open(f'{OUT}/{d}.json','w'), ensure_ascii=False, separators=(',',':'))

# ---- 2. wiki 補充：技能、屬性相剋、轉職樹、徽章 ----
wiki_skills = json.load(open(f'{OUT}/_wiki_skills.json')) if os.path.exists(f'{OUT}/_wiki_skills.json') else []

# ---- 3. 練功效率分析（私服站沒有的東西）----
mons = json.load(open(f'{SRC}/monsters.json'))
maps = json.load(open(f'{SRC}/maps.json'))
mon_by_id = {m['id']: m for m in mons}

grind = []
for mp in maps:
    ms = [mon_by_id[x['id']] for x in mp['monsters'] if x['id'] in mon_by_id]
    ms = [m for m in ms if m['hp'] > 0 and m['exp'] > 0 and not m['isFieldItemBox']]
    if not ms: continue
    lv = sum(m['level'] for m in ms)/len(ms)
    # 每點 HP 換到的經驗 = 打怪效率；越高越好
    eff = sum(m['exp']/m['hp'] for m in ms)/len(ms)
    money = sum((m['money'] or {}).get('amount',0) for m in ms)/len(ms)
    grind.append({
        'id': mp['id'], 'name': mp['name'], 'region': mp['region'],
        'levelReq': mp['levelReq'], 'type': mp['capsLabel'],
        'avgLv': round(lv,1), 'kinds': len(ms),
        'exp': round(sum(m['exp'] for m in ms)/len(ms)),
        'hp': round(sum(m['hp'] for m in ms)/len(ms)),
        'eff': round(eff,3), 'money': round(money),
        'aggressive': sum(1 for m in ms if m['aggressive']),
        'monsters': [{'id':m['id'],'name':m['name'],'level':m['level'],
                      'hp':m['hp'],'exp':m['exp'],'icon':m['image']} for m in ms],
    })
grind.sort(key=lambda x: x['avgLv'])
json.dump(grind, open(f'{OUT}/grind.json','w'), ensure_ascii=False, separators=(',',':'))

# ---- 4. 全站搜尋索引 ----
idx = []
def add(kind, rows, meta):
    for r in rows:
        idx.append([kind, r['id'], r['name'], meta(r)])
add('m', mons, lambda r: f"Lv.{r['level']} HP {r['hp']}")
add('p', maps, lambda r: f"{r['region']} · {r['capsLabel']}")
eq = json.load(open(f'{SRC}/equips.json'))
add('e', eq, lambda r: f"Lv.{r['levelReq']} {r['slotGroup']}")
add('f', json.load(open(f'{SRC}/fashion.json')), lambda r: f"時裝 {r['slotGroup']}")
add('i', json.load(open(f'{SRC}/items.json')), lambda r: r['category'])
add('r', json.load(open(f'{SRC}/recipes.json')), lambda r: f"配方 → {r['result']['name']}")
add('q', json.load(open(f'{SRC}/quests.json')), lambda r: f"Lv.{r['levelReq']} {r['typeLabel']}")
add('n', json.load(open(f'{SRC}/npcs.json')), lambda r: f"{r['region']} {r['job']}")
json.dump(idx, open(f'{OUT}/index.json','w'), ensure_ascii=False, separators=(',',':'))

meta = {
    'counts': counts, 'grind': len(grind), 'searchIndex': len(idx),
    'dataVersion': 'a8546aa2', 'generatedAt': '2026-08-19T16:28:46.694Z',
    'rates': {'exp': 3, 'drop': 3, 'money': 3},
}
json.dump(meta, open(f'{OUT}/meta.json','w'), ensure_ascii=False)

for d in DOMAINS + ['grind','index']:
    print(f"  {d:10s} {os.path.getsize(f'{OUT}/{d}.json')/1024:8.1f} KB")
print(f"\n練功地圖 {len(grind)} 個 · 搜尋索引 {len(idx)} 筆")
