#!/usr/bin/env python3
"""把 wiki 補充資料（技能、徽章、屬性、轉職、強化石、考試）中文化。

私服資料本身就是繁中，只有 wiki 補上來的這幾塊是英文／印尼文，
在這裡統一套上翻譯表與名詞對照。
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(ROOT, 'docs', 'data', 'wiki.json')

TXT = {}
for f in ('dst_skills', 'dst_badges', 'dst_systems', 'dst_locations'):
    p = os.path.join(ROOT, 'i18n', f + '.json')
    if os.path.exists(p):
        TXT.update(json.load(open(p, encoding='utf-8')))

TERM = {
    # 職業
    'Fighter': '劍士', 'Knight': '騎士', 'Berserker': '狂戰士', 'Templar': '聖殿武士',
    'Warlord': '統帥', 'Paladin': '聖騎士', 'Conqueror': '征服者', 'Crusader': '十字軍',
    'Archer': '弓箭手', 'Hunter': '獵人', 'Ranger': '遊俠', 'Sniper': '狙擊手',
    'Predator': '掠奪者', 'Gunner': '槍手', 'Beast Master': '馴獸師', 'Destroyer': '毀滅者',
    'Mage': '魔法師', 'Wizard': '巫師', 'Sorcerer': '咒術師', 'Warlock': '惡魔法師',
    'Archmage': '大魔導士', 'Necromancer': '死靈法師', 'Magister': '魔導師', 'Lich': '巫妖',
    'Cleric': '聖職者', 'Priest': '祭司', 'Saint': '聖者', 'Holy Avenger': '聖裁者',
    'Bishop': '主教', 'Cardinal': '樞機主教', 'Arc Bishop': '大主教',
    # 武器
    'Sword': '劍', 'Dagger': '短劍', 'Hammer': '鎚', 'Long Sword': '長劍', 'Axe': '斧',
    'Spear': '長槍', 'Dual Sword': '雙劍', 'Bow': '弓', 'Crossbow': '十字弓', 'Gun': '銃',
    'Staff': '手杖', 'Book': '魔法書', 'Cross': '十字架', 'Shield': '盾牌', 'None': '無',
    # 屬性
    'Fire': '火', 'Ice': '冰', 'Lightning': '雷', 'Holy': '神聖', 'Darkness': '闇',
    'Earth': '地', 'Animal': '動物', 'Undead': '不死', 'Demon': '惡魔', 'Dragon': '龍',
    'Other': '其他',
    # 其他
    'Active': '主動', 'Passive': '被動', 'Normal': '普通', 'Rare': '稀有',
    'Self': '自身', 'Party': '隊伍', 'Enemy': '敵方', 'accessory': '飾品', 'Badge': '徽章',
    # 技能表使用的進階職業名，與轉職樹那份命名不同，一併補上
    'Gladiator': '鬥士', 'Sword Master': '劍聖', 'Slayer': '殺戮者',
    'Dragon Knight': '龍騎士', 'General': '將軍', 'Heroes': '英雄',
    'Sharpshooter': '神射手', 'Imperial Shooter': '帝國射手',
    'Specialist': '專家', 'Trickster': '詭術師',
    'Arc Mage': '大魔導', 'Sage': '賢者', 'Shaman': '薩滿', 'Oracle': '神諭者',
    'Holy Avanger': '聖裁者',
    'Single': '單體', 'Multiple': '多體', 'Land Creatures': '地面生物',
    'Dagger Staff, Book': '短劍、手杖、魔法書',
}

# 少數印尼文題目未包含在翻譯批次內，逐條補上
EXAM_FIX = {
    'Pengajar ilmu serangan jarak jauh': '遠距離攻擊技藝的教導者',
    'Penguasa ilmu sihir': '魔法之道的掌控者',
    'Gadis berumur 16 tahun mempunyai hobi mengkoleksi botol-botol cantik':
        '十六歲少女，興趣是收集漂亮的瓶子',
    'Anak muda berumur 17 tahun mempunyai hobi pushup, mempunyai kemampuan menggunakan hammer blow':
        '十七歲青年，興趣是伏地挺身，擅長使用鎚擊',
    'Bentuk badannya menyerupai papan peringatan': '外型神似告示牌',
    'Monster amat gembira setelah menipu manusia': '騙過人類之後會非常開心的怪物',
    'Komando perang selalu dipegang olehnya': '戰場指揮權向來由他掌握',
}

# 徽章效果欄位是短語拼接，逐詞替換即可
PHRASE = [
    ('Attack terhadap Undead monster', '對不死系怪物攻擊力'),
    ('Attack terhadap Demon monster', '對惡魔系怪物攻擊力'),
    ('Attack terhadap Animal monster', '對動物系怪物攻擊力'),
    ('Attack terhadap Other Monster', '對其他系怪物攻擊力'),
    ('Point yang diterima ketika menyelesaikan class dengan Super Training Card',
     '使用高級修練卡完成課程獲得的點數'),
    ('Point yang diterima ketika menyelesaikan class dengan Training Card',
     '使用修練卡完成課程獲得的點數'),
    ('Kemungkinan sukses ketika mengupgrade senjata atau perisai', '武器或盾牌強化成功率'),
    ('Price item yang dibeli dari NPC', '向 NPC 購買道具的價格'),
    ('Price item yang dijual kepada NPC', '賣給 NPC 的道具價格'),
    ('komisi ketika menggunakan jasa Runpei', '使用倫貝服務的手續費'),
    ('Libi ketika menggunakan jasa Dragon', 'Libi（使用飛龍服務時）'),
    ('Exp Penalty ketika mati', '死亡經驗懲罰'),
    ('Hanya perlu membayar', '只需支付'),
    ('Potion Effect', '藥水效果'), ('Bonus Exp', '經驗加成'),
    ('Stop rate', '定身機率'), ('Stun rate', '暈眩機率'), ('Freeze rate', '冰凍機率'),
    ('durasi stop', '定身時間'), ('durasi stun', '暈眩時間'), ('durasi freeze', '冰凍時間'),
    ('War Task point', '戰爭任務點數'), ('Circle Point', '社團點數'),
    ('HP Regen', 'HP 回復'), ('MP Regen', 'MP 回復'),
    ('Max HP', '最大 HP'), ('Max MP', '最大 MP'),
    ('Accuracy', '命中'), ('Evasion', '迴避'), ('Critical', '爆擊'),
    ('Defense', '防禦力'), ('Damage', '傷害'), ('Attack', '攻擊力'), ('Range', '攻擊範圍'),
    ('Membayar', '支付'), ('komisi', '手續費'), ('detik', '秒'), ('None', '無'),
]

def phrase(s):
    if not isinstance(s, str) or not s.strip():
        return s
    for en, zh in PHRASE:
        s = s.replace(en, zh)
    return s

# 逐字殘留：印尼文單位與少數固定片語
RESIDUE = [(re.compile(r'\bDetik\b'), '秒'),
           (re.compile(r'\bAttack:'), '攻擊：'),
           (re.compile(r'\bDefend:'), '防禦：'),
           (re.compile(r'(\d+)\s*per detik\s*\((\d+)\s*terhadap Boss atau Mini-Boss\)',
                       re.I), r'每秒 \1（對 BOSS／小 BOSS 為 \2）')]

FIELD = {
    'Skills Type': '技能類型', 'Type': '類型', 'Class': '職業', 'Need Class': '需求職業',
    'Level': '等級', 'Need Level': '需求等級', 'Range': '施放距離', 'Attack Range': '攻擊範圍',
    'Target': '目標', 'Weapons': '可用武器', 'Condition': '條件',
    'Condition (Attack)': '條件（攻擊）', 'Condition (Defend)': '條件（防禦）',
    'Item Required': '需要道具', 'MP Cost': 'MP 消耗', 'HP Cost': 'HP 消耗',
    'Consume HP': 'HP 消耗', 'MP Requirement': 'MP 需求', 'Reduce MP Cost': 'MP 消耗降低',
    'Delay': '冷卻時間', 'Delay Skill': '技能冷卻', 'Duration': '持續時間',
    'Damage': '傷害', 'Attack': '攻擊力', 'Skill Attack': '技能攻擊力', 'Magic': '魔法攻擊力',
    'Defense': '防禦力', 'Critical': '爆擊', 'Accuracy': '命中', 'Evasion': '迴避',
    'Attack Speed': '攻擊速度', 'Strength': '力量', 'Agility': '敏捷', 'Intellect': '智力',
    'Theology': '神學', 'Max HP': '最大 HP', 'Max MP': '最大 MP',
    'Recover HP': '回復 HP', 'Recover MP': '回復 MP', 'Restore HP': '回復 HP',
    'Restore MP': '回復 MP', 'MP Regen': 'MP 回復', 'Increases MP Recovery': 'MP 回復量提升',
    'Increases MP Recovery Rate': 'MP 回復率提升',
    'Stun Rate': '暈眩機率', 'Stun Duration': '暈眩時間', 'Stop Rate': '定身機率',
    'Stop Duration': '定身時間', 'Stop Time': '定身時間', 'Freeze Rate': '冰凍機率',
    'Freeze Duration': '冰凍時間', 'Effects Odds': '效果發動率',
    'Instant Death Chance': '即死機率', 'Animal Defense': '對動物防禦',
    'Undead Defense': '對不死防禦', 'Demon Defense': '對惡魔防禦',
    'Up Undead Damage': '對不死傷害提升', 'Up Demon Damage': '對惡魔傷害提升',
    'Party Attack': '隊伍攻擊力', 'Party Defense': '隊伍防禦力', 'Party Damage': '隊伍傷害',
    'Party Agility': '隊伍敏捷', 'Party Strength': '隊伍力量', 'Party Intelligence': '隊伍智力',
    'Party EXP Bonus': '隊伍經驗加成', 'Self EXP Bonus': '自身經驗加成',
    'Image': '圖示', 'Item Name': '名稱', 'Enhancement Level': '強化階級', 'Price': '價格',
    'Unsealed Stone': '解封石', 'Boss/Mini-Boss': 'BOSS／小 BOSS', 'Treasure Box': '寶箱',
    'Question': '題目', 'Answer': '答案',
}

_SPLIT = re.compile(r'\s*/\s*')

def term(s):
    """整串或以 / 分隔的名詞逐段翻譯，翻不到的原樣保留。"""
    if not isinstance(s, str) or not s.strip():
        return s
    if s in TERM:
        return TERM[s]
    for pat, rep in RESIDUE:
        s = pat.sub(rep, s)
    if s in TERM:
        return TERM[s]
    parts = _SPLIT.split(s)
    if len(parts) > 1 and all(p in TERM for p in parts):
        return ' / '.join(TERM[p] for p in parts)
    parts = [p.strip() for p in s.split(',')]
    if len(parts) > 1 and all(p in TERM for p in parts):
        return '、'.join(TERM[p] for p in parts)
    return s

def text(s):
    if not isinstance(s, str) or not s.strip():
        return s
    return EXAM_FIX.get(s.strip(), TXT.get(s, TXT.get(s + '\n', s))).strip()

w = json.load(open(WIKI, encoding='utf-8'))

_MISPLACED = re.compile(r'^\*\s*([A-Za-z][A-Za-z ]+?)\s*:\s*(.*)$')

def unshift(f):
    """wiki 表格把 "*Label: value" 這種續行併進了上一欄，這裡把它移回正確欄位。"""
    out = {}
    for k, v in f.items():
        v = str(v).strip().lstrip(':').strip()
        m = _MISPLACED.match(v)
        if m:
            if m.group(2).strip():                       # 續行沒有值就整欄捨棄
                out.setdefault(FIELD.get(m.group(1), m.group(1)), m.group(2).strip())
        elif v:
            out[k] = v
    return out

for s in w['skills']:
    s['desc'] = text(s['desc'])
    s['job'] = term(s['job'])
    s['type'] = term(s['type'])
    for lv in s['levels']:
        lv['f'] = {FIELD.get(k.strip(), k.strip()): term(text(v))
                   for k, v in unshift(lv['f']).items()}

for b in w['badges']:
    b['jobs'] = [term(j) for j in b['jobs']]
    for k in ('rarity', 'kind', 'group', 'type', 'attr', 'part'):
        b[k] = term(b.get(k))
    for k in ('method', 'eff', 'add', 'lvtext', 'price', 'dmg', 'spd', 'rng'):
        b[k] = phrase(text(b.get(k)))

w['matrix'] = {term(k): {'up': [term(x) for x in v['up']], 'down': [term(x) for x in v['down']]}
               for k, v in w['matrix'].items()}
w['monAttrs'] = [term(a) for a in w['monAttrs']]
w['jobTree'] = {term(k): [term(x) for x in v] for k, v in w['jobTree'].items()}
w['jobWeapons'] = {term(k): [term(x) for x in v] for k, v in w['jobWeapons'].items()}

w['exam']['rows'] = [r for r in w['exam']['rows'] if r['c'][0].strip()]   # 原表有空題目列，捨棄

for t in w['stones'] + [w['exam']]:
    t['headers'] = [FIELD.get(h, term(h)) for h in t['headers']]
    for r in t['rows']:
        r['c'] = [text(term(c)) for c in r['c']]

json.dump(w, open(WIKI, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('wiki i18n done:', len(w['skills']), 'skills,', len(w['badges']), 'badges')
