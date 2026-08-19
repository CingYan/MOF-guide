# -*- coding: utf-8 -*-
"""抽出遊戲系統/道具頁，並手工建立屬性相剋矩陣"""
import json, re, os, sys
sys.path.insert(0,'build')
raw = json.load(open('data/raw.json'))

def clean(s):
    s = re.sub(r'\[\[File:([^\]\|]+)[^\]]*\]\]', '', s or '')
    s = re.sub(r'\[\[([^\|\]]*)\|([^\]]*)\]\]', r'\2', s)
    s = re.sub(r'\[\[([^\]]*)\]\]', r'\1', s)
    s = re.sub(r"'''?", '', s); s = re.sub(r'<br\s*/?>', ' / ', s)
    s = re.sub(r'<[^>]+>', '', s); s = re.sub(r'\{\{[^}]*\}\}', '', s)
    return s.strip()

def cell(ls):
    c = ls[1:]
    if '|' in c:
        a, r = c.split('|', 1)
        if '=' in a and '[[' not in a: c = r
    return clean(c)

def img_of(ls):
    m = re.search(r'\[\[File:([^\]\|]+)', ls)
    return m.group(1).strip() if m else ''

def tables(text):
    out = []
    for tbl in re.findall(r'\{\|(.*?)\n\|\}', text, re.S):
        heads, rows, cur, curimg = [], [], None, ''
        for line in tbl.split('\n'):
            ls = line.strip()
            if ls.startswith('!'):
                heads.append(cell('|' + ls[1:]))
            elif ls.startswith('|-'):
                if cur is not None: rows.append({'c': cur, 'img': curimg})
                cur, curimg = [], ''
            elif ls.startswith('|') and cur is not None:
                if 'File:' in ls and not curimg: curimg = img_of(ls)
                cur.append(cell(ls))
        if cur: rows.append({'c': cur, 'img': curimg})
        rows = [r for r in rows if any(x for x in r['c'])]
        if heads and rows: out.append({'headers': heads, 'rows': rows})
    return out

PAGES = {
 'Attribute':'屬性系統','Strengthening Stone':'武器強化','Potion':'藥水',
 'Core':'核心 Core','Mineral':'礦石','Skill Book':'技能書','Training Card':'訓練卡',
 'Moving Scroll':'移動卷軸','PvP Item':'PvP 道具','Treasure Box':'寶箱',
 'Status Effect':'狀態異常','Crafting':'製作','Instant Dungeon':'即時地城',
 'Major Skill':'生活技能','Party':'組隊','PvP':'PvP','PvM':'PvM','Circle':'公會 Circle',
 'Wedding':'結婚','Exam':'轉職考試','Quest':'任務系統','Weather':'天氣',
 'Candy':'糖果','Chocolate':'巧克力','Job':'職業系統','Player Character':'角色',
}
systems = []
for page, zh in PAGES.items():
    if page not in raw: continue
    t = raw[page]['text']
    intro = clean(re.split(r'\n==', t)[0])
    systems.append({'id': page, 'zh': zh, 'intro': intro[:700], 'tables': tables(t)})

# ---- 屬性相剋矩陣（來源：Attribute 頁 "Attribute Bonus" 散文，手工結構化）----
MATRIX = {
  'Fire':      {'up':['Ice','Animal'],      'down':['Fire','Demon']},
  'Lightning': {'up':['Animal','Demon'],    'down':['Lightning','Undead']},
  'Ice':       {'up':['Lightning'],         'down':['Ice','Animal']},
  'Holy':      {'up':['Undead','Demon'],    'down':[]},
  'Darkness':  {'up':['Animal','Other'],    'down':['Undead','Demon']},
  'Earth':     {'up':[],                    'down':[]},
}
MON_ATTRS = ['Fire','Ice','Lightning','Other','Animal','Undead','Demon','Dragon']

json.dump({'systems': systems, 'matrix': MATRIX, 'monAttrs': MON_ATTRS},
          open('docs/data/systems.json','w'), ensure_ascii=False, separators=(',',':'))
print("系統頁:", len(systems), "|", round(os.path.getsize('docs/data/systems.json')/1024,1), "KB")
for s in systems:
    if s['tables']: print(f"  {s['zh']:12s} {len(s['tables'])} 表 / {sum(len(t['rows']) for t in s['tables'])} 列")
