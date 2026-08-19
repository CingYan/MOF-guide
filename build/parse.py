# -*- coding: utf-8 -*-
"""把 MoF wiki 原始 wikitext 解析成結構化 JSON"""
import json, re, os, collections

RAW = json.load(open('data/raw.json'))

# ---------- 通用工具 ----------
def clean(s):
    if s is None: return ''
    s = re.sub(r'\[\[File:[^\]]*\]\]', '', s)
    s = re.sub(r'\[\[([^\|\]]*)\|([^\]]*)\]\]', r'\2', s)
    s = re.sub(r'\[\[([^\]]*)\]\]', r'\1', s)
    s = re.sub(r"'''?", '', s)
    s = re.sub(r'<br\s*/?>', ' / ', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'\{\{[^}]*\}\}', '', s)
    return s.strip()

def first_image(text):
    m = re.search(r'\|image\s*=\s*File:([^\n\|\}]+)', text)
    if m: return m.group(1).strip()
    m = re.search(r'\[\[File:([^\]\|]+\.(?:png|gif|jpg))', text, re.I)
    return m.group(1).strip() if m else ''

def infobox(text):
    """抽 Infobox 的 Row N title / Row N info 配對"""
    out = {}
    for n in range(1, 15):
        t = re.search(r'\|Row %d title\s*=\s*(.*?)(?=\n\|Row|\n\||\}\})' % n, text, re.S)
        i = re.search(r'\|Row %d info\s*=\s*(.*?)(?=\n\|Row|\n\||\}\})' % n, text, re.S)
        if t and i:
            k = clean(re.split(r'\|(?:Box title|imagewidth|image)\s*=', t.group(1))[0])
            v = clean(re.split(r'\|(?:Box title|imagewidth|image)\s*=', i.group(1))[0])
            if k: out[k] = v
    return out

def parse_tables(text):
    """解析所有 wikitable，回傳 [{'headers':[...], 'rows':[[...]]}]"""
    tables = []
    for tbl in re.findall(r'\{\|(.*?)\n\|\}', text, re.S):
        headers, rows, cur = [], [], None
        for line in tbl.split('\n'):
            ls = line.strip()
            if ls.startswith('!'):
                cell = ls[1:]
                if '|' in cell:
                    attr, rest = cell.split('|', 1)
                    if '=' in attr and '[[' not in attr:
                        cell = rest
                headers.append(clean(cell))
            elif ls.startswith('|-'):
                if cur is not None: rows.append(cur)
                cur = []
            elif ls.startswith('|') and cur is not None:
                cell = ls[1:]
                # 剝掉 cell 屬性： | style="..." | 內容
                if '|' in cell:
                    attr, rest = cell.split('|', 1)
                    if '=' in attr and '[[' not in attr and '{{' not in attr:
                        cell = rest
                cur.append(clean(cell))
        if cur: rows.append(cur)
        rows = [r for r in rows if any(x for x in r)]
        if headers and rows: tables.append({'headers': headers, 'rows': rows})
    return tables

def desc_section(text, name):
    m = re.search(r'==+\s*%s\s*==+\n(.*?)(?=\n==|\Z)' % re.escape(name), text, re.S)
    return clean(m.group(1))[:600] if m else ''

def korean(text):
    m = re.search(r'\(Korean:\s*([^\)]+)\)', text)
    return m.group(1).strip() if m else ''

# ---------- 分類判定 ----------
JOBS = ['Fighter', 'Archer', 'Mage', 'Cleric']
# 來源：各職業頁「Senjata yang bisa digunakan oleh seorang X adalah ...」
JOB_WEAPONS = {
    'Fighter': ['Sword','Dagger','Hammer','Long Sword','Axe','Spear','Dual Sword'],
    'Archer':  ['Bow','Crossbow','Dagger','Gun'],
    'Mage':    ['Staff','Dagger','Book'],
    'Cleric':  ['Hammer','Staff','Cross'],
}
WEAPON_JOBS = {}
for _j, _ws in JOB_WEAPONS.items():
    for _w in _ws: WEAPON_JOBS.setdefault(_w, []).append(_j)
WEAPON_PAGES, ARMOR_PAGES = [], []
monsters, skills, npcs, locations, pets, misc = [], [], [], [], [], []
weapons, armors, accessories = [], [], []

def num(s):
    m = re.search(r'-?[\d.,]+', str(s).replace(',', ''))
    try: return float(m.group(0)) if m else None
    except: return None

def lvnum(s):
    n = num(s)
    return int(n) if n is not None else None

# ---------- 主迴圈 ----------
for title, p in RAW.items():
    text, cats = p['text'], p['cats']
    img = first_image(text)
    ib = infobox(text)
    tbls = parse_tables(text)

    # === 怪物 ===
    if 'Monster' in cats:
        drops = []
        for t in tbls:
            h = [x.lower() for x in t['headers']]
            if any('item name' in x for x in h):
                ni = next((i for i,x in enumerate(h) if 'item name' in x), 1)
                ci = next((i for i,x in enumerate(h) if 'category' in x), None)
                ri = next((i for i,x in enumerate(h) if 'rarity' in x), None)
                for r in t['rows']:
                    if len(r) > ni and r[ni]:
                        drops.append({'name': r[ni],
                                      'cat': r[ci] if ci is not None and len(r)>ci else '',
                                      'rarity': r[ri] if ri is not None and len(r)>ri else ''})
        monsters.append({
            'name': title, 'img': img, 'kr': korean(text),
            'level': lvnum(ib.get('Level')),
            'temper': ib.get('Temper',''),
            'hp': lvnum(ib.get('Health')),
            'attr': ib.get('Attribute',''),
            'move': ib.get('Land/Flying',''),
            'loc': ib.get('Location',''),
            'boss': 'Boss' in cats, 'mini': 'Mini-Boss' in cats,
            'regions': [c for c in cats if c not in
                        ('Monster','Land','Flying','Aggresive','Neutral','Passive','Boss','Mini-Boss',
                         'Animal','Demon','Undead','Other','Ice','Fire','Lightning','Dragon','Ghost',
                         'Turtle','Guard','Circle','Event Exclusive Monster','PVM Exclusive Monster')],
            'desc': desc_section(text, 'Monster Description'), 'drops': drops,
        })
        continue

    # === 技能 ===
    if any(c.endswith('Skill') for c in cats):
        job = next((j for j in JOBS if f'{j} Skill' in cats), '')
        levels = []
        for m in re.finditer(r"===\s*'''?(.+?)'''?\s*===\n(.*?)(?=\n===|\n==[^=]|\Z)", text, re.S):
            lname, body = m.group(1).strip(), m.group(2)
            f = {}
            for bm in re.finditer(r'^\*\s*([^:]+):\s*(.+)$', body, re.M):
                f[clean(bm.group(1))] = clean(bm.group(2))
            if f: levels.append({'name': lname, 'f': f})
        skills.append({
            'name': title, 'img': img, 'kr': korean(text), 'job': job,
            'type': 'Passive' if 'Passive Skill' in cats else 'Active',
            'desc': desc_section(text, 'Skill Description'), 'levels': levels,
        })
        continue

    # === 武器 / 防具 / 飾品 ===
    if 'Weapon' in cats or 'Armor' in cats or 'Accessory' in cats:
        kind = 'weapon' if 'Weapon' in cats else ('armor' if 'Armor' in cats else 'accessory')
        # 依 === 段落切開，段落名若是職業就記下來
        segs, cur_job = [], ''
        parts = re.split(r"\n=+\s*'{0,3}\[{0,2}([A-Za-z /]+?)\]{0,2}'{0,3}\s*=+(?=\n)", '\n' + text)
        segs.append(('', parts[0]))
        for i in range(1, len(parts) - 1, 2):
            segs.append((parts[i].strip(), parts[i+1]))
        tbls = []
        for head, body in segs:
            j = head if head in JOBS else ''
            for t in parse_tables(body):
                t['job'] = j
                tbls.append(t)
        for t in tbls:
            h = [x.lower() for x in t['headers']]
            def idx(*keys):
                for k in keys:
                    for i,x in enumerate(h):
                        if k in x: return i
                return None
            i_name = idx('weapon name','armor name','accessory name','item name','name')
            if i_name is None: continue
            cols = {
                'rarity': idx('rarity'), 'lv': idx('level requirement','level'),
                'dmg': idx('damage'), 'spd': idx('attack speed','speed'),
                'rng': idx('range'), 'attr': idx('attribute'), 'price': idx('price'),
                'eff': idx('effect'), 'add': idx('additional'), 'def': idx('defense'),
                'part': idx('body part','part'),
            }
            for r in t['rows']:
                if len(r) <= i_name or not r[i_name]: continue
                g = lambda k: (r[cols[k]] if cols[k] is not None and len(r) > cols[k] else '')
                jobs = WEAPON_JOBS.get(title, []) if kind == 'weapon' else ([t.get('job')] if t.get('job') else JOBS)
                item = {'name': r[i_name], 'group': title, 'kind': kind, 'jobs': jobs,
                        'rarity': g('rarity'), 'lv': lvnum(g('lv')), 'dmg': g('dmg'),
                        'spd': g('spd'), 'rng': g('rng'), 'attr': g('attr'),
                        'price': g('price'), 'eff': g('eff'), 'add': g('add'),
                        'def': lvnum(g('def')), 'part': g('part')}
                if item['add'] and item['add'] == item['eff']: item['add'] = ''
                (weapons if kind=='weapon' else armors if kind=='armor' else accessories).append(item)
        continue

    # === 寵物 ===
    if 'Pet' in cats:
        eff = []
        for t in tbls:
            h = [x.lower() for x in t['headers']]
            if any('level' in x for x in h) and any('effect' in x for x in h):
                li = next(i for i, x in enumerate(h) if 'level' in x)
                ei = next(i for i, x in enumerate(h) if 'effect' in x)
                for r in t['rows']:
                    if len(r) > max(li, ei) and lvnum(r[li]) is not None:
                        eff.append({'lv': lvnum(r[li]), 'e': r[ei]})
        eff.sort(key=lambda x: x['lv'])
        pets.append({'name': title, 'img': img, 'kr': korean(text),
                     'attr': ib.get('Attribute',''), 'food': ib.get('Pet Food',''),
                     'desc': desc_section(text,'Pet Description'), 'eff': eff})
        continue

    # === NPC ===
    if 'NPC' in cats:
        quests = []
        for t in tbls:
            h = [x.lower() for x in t['headers']]
            if any('quest name' in x for x in h):
                gi = lambda k: next((i for i,x in enumerate(h) if k in x), None)
                i_n, i_l, i_m, i_r = gi('quest name'), gi('quest level'), gi('mission'), gi('reward')
                for r in t['rows']:
                    if i_n is not None and len(r) > i_n and r[i_n]:
                        quests.append({'name': r[i_n],
                                       'lv': lvnum(r[i_l]) if i_l is not None and len(r)>i_l else None,
                                       'mission': r[i_m] if i_m is not None and len(r)>i_m else '',
                                       'reward': r[i_r] if i_r is not None and len(r)>i_r else ''})
        npcs.append({'name': title, 'img': img, 'kr': korean(text),
                     'loc': ib.get('Location',''), 'job': ib.get('Job',''),
                     'quests': quests})
        continue

    # === 地點 ===
    if 'Location' in cats:
        locations.append({'name': title, 'img': img, 'kr': korean(text),
                          'regions': [c for c in cats if c != 'Location'],
                          'desc': clean(re.split(r'\n==', text)[0])[:500]})
        continue

    misc.append({'name': title, 'cats': cats, 'img': img})

# ---------- 掉落物反查 ----------
drop_index = collections.defaultdict(list)
for m in monsters:
    for d in m['drops']:
        drop_index[d['name']].append({'mon': m['name'], 'lv': m['level'],
                                      'rarity': d['rarity'], 'loc': m['loc']})

data = {
    'monsters': sorted(monsters, key=lambda x: (x['level'] is None, x['level'] or 0, x['name'])),
    'skills':   sorted(skills, key=lambda x: (x['job'], x['name'])),
    'weapons':  sorted(weapons, key=lambda x: (x['lv'] is None, x['lv'] or 0)),
    'armors':   sorted(armors, key=lambda x: (x['lv'] is None, x['lv'] or 0)),
    'accessories': sorted(accessories, key=lambda x: (x['lv'] is None, x['lv'] or 0)),
    'pets': pets, 'npcs': sorted(npcs, key=lambda x: x['name']),
    'locations': sorted(locations, key=lambda x: x['name']),
    'drop_index': {k: v for k, v in sorted(drop_index.items())},
    'misc': misc,
}
os.makedirs('docs/data', exist_ok=True)
json.dump(data, open('docs/data/mof.json','w'), ensure_ascii=False, separators=(',',':'))

for k in ['monsters','skills','weapons','armors','accessories','pets','npcs','locations']:
    print(f"{k:14s} {len(data[k]):5d}")
print(f"{'掉落物種類':14s} {len(drop_index):5d}")
print(f"{'未分類':14s} {len(misc):5d}")
print("大小:", round(os.path.getsize('docs/data/mof.json')/1024, 1), "KB")
