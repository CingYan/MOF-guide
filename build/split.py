# -*- coding: utf-8 -*-
"""把 mof.json 切成分區檔，並建立全站搜尋索引"""
import json, os

D = 'docs/data'
d = json.load(open(f'{D}/mof.json'))

SECTIONS = ['monsters','skills','weapons','armors','accessories',
            'pets','npcs','locations','drop_index']
for k in SECTIONS:
    json.dump(d[k], open(f'{D}/{k}.json','w'), ensure_ascii=False, separators=(',',':'))
    print(f"  {k:14s} {os.path.getsize(f'{D}/{k}.json')/1024:7.1f} KB")

# 全站搜尋索引
idx = []
for m in d['monsters']:    idx.append(['m', m['name'], m.get('kr',''), f"Lv.{m['level']} {m['loc']}"])
for s in d['skills']:      idx.append(['s', s['name'], s.get('kr',''), f"{s['job']} 技能"])
for w in d['weapons']:     idx.append(['w', w['name'], '', f"Lv.{w['lv']} {w['group']}"])
for a in d['armors']:      idx.append(['a', a['name'], '', f"Lv.{a['lv']} {a['part'] or a['group']}"])
for a in d['accessories']: idx.append(['c', a['name'], '', f"Lv.{a['lv']} {a['group']}"])
for p in d['pets']:        idx.append(['p', p['name'], p.get('kr',''), '寵物'])
for n in d['npcs']:        idx.append(['n', n['name'], n.get('kr',''), n['loc']])
for l in d['locations']:   idx.append(['l', l['name'], l.get('kr',''), '地點'])
for item in d['drop_index']: idx.append(['d', item, '', '掉落物'])

# 系統／道具表也進索引
seen = {(r[0], r[1]) for r in idx}
sysd = json.load(open(f'{D}/systems.json'))
for s in sysd['systems']:
    for t in s['tables']:
        hl = [h.lower() for h in t['headers']]
        ni = next((i for i,h in enumerate(hl) if 'name' in h), None)
        if ni is None:
            ni = next((i for i,h in enumerate(hl) if h not in ('image','')), None)
        if ni is None: continue
        for r in t['rows']:
            if len(r['c']) > ni and r['c'][ni] and len(r['c'][ni]) < 60:
                key = ('y', r['c'][ni])
                if key in seen: continue
                seen.add(key)
                idx.append(['y', r['c'][ni], '', s['zh']])

json.dump(idx, open(f'{D}/index.json','w'), ensure_ascii=False, separators=(',',':'))
print(f"  {'index':14s} {os.path.getsize(f'{D}/index.json')/1024:7.1f} KB  ({len(idx)} 筆)")
os.remove(f'{D}/mof.json')
print("完成")
