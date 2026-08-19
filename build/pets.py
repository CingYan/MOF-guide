#!/usr/bin/env python3
"""寵物資料合併：以 mof-pets 那批已交叉查證的繁中 CSV 為主，
舊版 wiki（英文、git 歷史 e531fdb）只在 CSV 沒涵蓋的欄位當備援。

CSV 沒有的欄位（寵物屬性 Animal/Demon/Dragon/Other、寵物敘述、韓文名的
「英文別名」寫法）才回頭用舊 wiki；凡是 CSV 有給數字的地方，一律以 CSV
為準，因為它標了「數值來源」與「已驗證等級」，是實際核對過的。

阿利（Ghost）完全沒進這批 CSV——現有資料就是查不到牠的加成效果，不是
腳本漏抓，所以 levels 留空、peak 留空、note 照實寫「查不到」。
"""
import csv
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'docs', 'data')
CSV_DIR = '/home/node/clawd/tmp/mof-pets'

OLD_PETS_COMMIT = 'e531fdb'  # 舊 wiki pets.json 消失前最後一次還在工作目錄的 commit


def load_old_pets():
    """舊 wiki 8 筆資料只留在 git 歷史裡，工作目錄早已刪除，得用 git show 撈。"""
    out = subprocess.run(
        ['git', 'show', f'{OLD_PETS_COMMIT}:docs/data/pets.json'],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return {p['name']: p for p in json.loads(out.stdout)}


def load_items():
    with open(os.path.join(DATA, 'items.json'), encoding='utf-8') as f:
        return {it['id']: it for it in json.load(f)}


def read_csv(name):
    # CSV 是 UTF-8 with BOM，utf-8 讀會在第一個欄名前面留下 ﻿。
    with open(os.path.join(CSV_DIR, name), encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


ATTR_ZH = {'Animal': '動物', 'Demon': '惡魔', 'Dragon': '龍', 'Other': '其他'}

# mof_pet_levels.csv「屬性」欄位是中文，但格式（要不要 %、要不要秒）跟輸出
# schema 要求的「詞 +數值」還是差一步，這裡只補上顯示用的詞尾。
CSV_STAT = {
    '技能攻擊%': ('技能攻擊力', '%'),
    '掉寶率%':   ('掉寶率', '%'),
    '攻擊力%':   ('攻擊力', '%'),
    '防禦%':     ('防禦力', '%'),
    '普攻間隔(秒)': ('攻擊速度', '秒'),
    '攻擊': ('攻擊', ''),
    '敏捷': ('敏捷', ''),
    '智力': ('智力', ''),
    '力量': ('力量', ''),
}


def fmt_val(v):
    return v if v.startswith('-') else '+' + v


def build_levels(rows_for_pet):
    """把 mof_pet_levels.csv 裡同一隻寵物、同一等級的多列屬性合成一筆 eff 字串。

    惡魔金一個等級有「普攻間隔(秒)」+「防禦%」兩列、G-Joe 有「攻擊」+「敏捷」
    兩列，這些必須合併成一筆，不能拆成兩個 lv 相同的項目。
    """
    by_lv = {}
    for r in rows_for_pet:
        lv = int(r['等級'])
        cn, suffix = CSV_STAT[r['屬性']]
        by_lv.setdefault(lv, {'parts': [], 'verified': False})
        by_lv[lv]['parts'].append(f"{cn} {fmt_val(r['數值'])}{suffix}")
        if r['已實機驗證'].strip().upper() == 'Y':
            by_lv[lv]['verified'] = True
    levels = []
    for lv in sorted(by_lv):
        levels.append({
            'lv': lv,
            'eff': '、'.join(by_lv[lv]['parts']),
            'verified': by_lv[lv]['verified'],
        })
    return levels


def egg_info(items, egg_id):
    it = items[egg_id]
    return it['name'], it.get('desc', ''), it.get('icon', ''), it.get('price', 0)


def food_entry(items, food_id):
    it = items[food_id]
    return {'id': food_id, 'name': it['name'], 'icon': it.get('icon', ''), 'desc': it.get('desc', '')}


# 英文 wiki 名稱 -> 中文寵物名／蛋 ID。蛋 ID 已經跟 mof_pet_summary.csv 的
# 「蛋ID」欄位交叉核對過，一致；attr 這個欄位 CSV 完全沒提供，固定回頭用
# 舊 wiki 的 Animal/Demon/Dragon/Other。
PET_MAP = {
    'Penguin':     {'zh': '麻吉',   'eggId': 'K0413'},
    'Tinkerbell':  {'zh': '艾琳',   'eggId': 'K0412'},
    'Devil Jean':  {'zh': '惡魔金', 'eggId': 'K0427'},
    'Dino':        {'zh': '恐龍',   'eggId': 'K0401'},
    'Robot':       {'zh': 'G-Joe',  'eggId': 'K0437'},
    'Teddy':       {'zh': '貝貝',   'eggId': 'K0425'},
    'Mint':        {'zh': '薄荷',   'eggId': 'K0430'},
    'Ghost (Pet)': {'zh': '阿利',   'eggId': 'K0409'},  # 不在任何一份 CSV 裡
}

# 這批 CSV 對「聖騎士」「小飛俠」兩個原本以為對不上蛋的疑點，靠
# mof_pet_food.csv 的「敘述中的寵物名」欄位解掉了：那只是道具敘述用的
# 另一個遊戲內稱呼，跟蛋的中文名字不同，但是同一隻寵物。人工核對
# food CSV 內容後才敢在這裡下結論，不是憑空猜的。
ALIAS_NOTE = {
    '恐龍': '飛龍寵物「聖騎士」',
    '艾琳': '仙子寵物「小飛俠」',
}

# CSV 與舊 wiki 對不上的地方：兩邊都保留，peak 用 CSV（有標來源），
# note 補一句舊資料的另一個數字，不擅自二選一。逐一比對
# mof_pet_levels.csv 與 e531fdb 那份 pets.json 的 eff 才找出這兩筆。
PEAK_CONFLICT = {
    '艾琳': '舊 wiki 資料記為 +28% 掉寶率（逐等級 5/8/10/12/15/18/20/22/25/28%），與 CSV／巴哈數值不同，來源不同，兩者都保留。',
    '恐龍': '舊 wiki 資料記為 +10% 攻擊力（逐等級 1.5~10% 線性遞增），與 CSV／巴哈數值不同，來源不同，兩者都保留。',
}

MINT_NOTE = (
    '現行道具 K0430 敘述寫「能提升主人的體力、敏捷能力值」（體力=Stamina），'
    '但 CSV 與舊 wiki 的逐等級數值一致，實際都是敏捷／力量（Agility／Strength），'
    '沒有體力這個屬性。敘述文字保留原樣不改，差異照實記錄。'
)

DEVIL_JEAN_NOTE = (
    '舊資料標為 Delay Skill（技能冷卻），但伺服器主已確認該欄位實為攻擊速度'
    '（공격속도），影響普攻間隔而非技能；現行道具說明寫「降低主人的攻擊速度並'
    '提升防禦力」。CSV 的「普攻間隔(秒)」＋「防禦%」逐等級數值與舊 wiki 完全一致，'
    '互相印證。蛋名叫「惡魔金」但專用飼料 K0428 寫的是「戴比進」，中文名稱不一致，'
    '兩者應為同一隻寵物（K0428 desc 明確寫「惡魔寵物戴比進」對應惡魔屬性）。另外'
    '現行資料裡「惡魔金的蛋」有兩個 id：K0427（一般商城道具，可交易）與 K0429'
    '（活動道具 EVENT_INSTANT，不可交易），圖示與敘述相同，這裡以 K0427 作為'
    ' eggId 代表。'
)

GHOST_NOTE = '現有資料查不到加成效果。'


def build():
    old_pets = load_old_pets()
    items = load_items()

    summary_rows = {r['寵物']: r for r in read_csv('mof_pet_summary.csv')}
    food_rows = {r['寵物']: r for r in read_csv('mof_pet_food.csv')}
    level_rows = read_csv('mof_pet_levels.csv')
    levels_by_pet = {}
    for r in level_rows:
        levels_by_pet.setdefault(r['寵物'], []).append(r)

    pets = []
    for en, spec in PET_MAP.items():
        zh = spec['zh']
        wiki = old_pets[en]
        egg_name, egg_desc, egg_icon, egg_price = egg_info(items, spec['eggId'])

        summary = summary_rows.get(zh)
        foods = []
        note_parts = []

        if zh in food_rows:
            frow = food_rows[zh]
            foods.append(food_entry(items, frow['道具ID']))
            if zh in ALIAS_NOTE:
                note_parts.append(
                    f"專用飼料 {frow['道具ID']}（{frow['飼料名稱']}）的道具敘述稱牠為"
                    f"{ALIAS_NOTE[zh]}，與蛋的名稱不同，是同一隻寵物。"
                )

        if summary is None:
            # 只有阿利落在這個分支：CSV 完全沒有這隻寵物的任何資料。
            levels = []
            peak = ''
            source = ''
            verified = ''
            note_parts.append(GHOST_NOTE)
        else:
            levels = build_levels(levels_by_pet.get(zh, []))
            peak_lv = levels[-1] if levels else None
            peak = peak_lv['eff'] if peak_lv else ''
            source = summary['數值來源']
            verified = '' if summary['已驗證等級'] == '-' else summary['已驗證等級']
            if zh in PEAK_CONFLICT:
                note_parts.append(PEAK_CONFLICT[zh])

        if zh == '惡魔金':
            note_parts.insert(0, DEVIL_JEAN_NOTE)
        if zh == '薄荷':
            note_parts.append(MINT_NOTE)

        pets.append({
            'name': zh,
            'en': en,
            'kr': summary['韓文名'] if summary else wiki.get('kr', ''),
            'attr': ATTR_ZH.get(wiki.get('attr', ''), wiki.get('attr', '')),
            'eggId': spec['eggId'],
            'eggName': egg_name,
            'eggDesc': egg_desc,
            'eggIcon': egg_icon,
            'eggPrice': egg_price,
            'foods': foods,
            'levels': levels,
            'peak': peak,
            'source': source,
            'verified': verified,
            'note': ' '.join(note_parts),
        })

    # 技能書：名稱／圖示／價格取 items.json，效果數值與需求等級取 CSV。
    # items.json 的 desc 只有文字敘述（「增加寵物主人HP的自動恢復量」），
    # CSV 才有實際幅度（+20% HP 回復）與生效所需的寵物等級，兩邊互補不重複。
    SKILL_IDS = ['K0404', 'K0405', 'K0406', 'K0410', 'K0411']
    csv_skills = {
        r['道具ID']: r
        for r in read_csv('mof_pet_skills.csv')
    }
    skills = []
    for sid in SKILL_IDS:
        it = items[sid]
        cs = csv_skills.get(sid, {})
        lv = (cs.get('需求寵物等級') or '').strip()
        skills.append({
            'id': sid, 'name': it['name'],
            'eff': (cs.get('效果') or '').strip(),
            'lvReq': int(lv) if lv.isdigit() else 0,
            'desc': it.get('desc', ''),
            'icon': it.get('icon', ''), 'price': it.get('price', 0),
        })

    exp = build_exp()

    return {'pets': pets, 'skills': skills, 'unmatched': [], 'exp': exp}


def build_exp():
    """mof_pet_exp.csv 是三段式表格（升級 LOVE / 擊怪 LOVE / 總計），中間用空列分隔。"""
    with open(os.path.join(CSV_DIR, 'mof_pet_exp.csv'), encoding='utf-8-sig', newline='') as f:
        rows = list(csv.reader(f))

    blocks = []
    cur = []
    for row in rows:
        if not row or not any(cell.strip() for cell in row):
            blocks.append(cur)
            cur = []
        else:
            cur.append(row)
    if cur:
        blocks.append(cur)

    level_block, gain_block, total_block = blocks
    levels = [{'lv': int(lv), 'love': int(love)} for lv, love in level_block[1:]]
    gain = [{'diff': diff, 'love': int(love)} for diff, love in gain_block[1:]]
    # 這段只有單獨一列（標籤,總計），不像前兩段是「標題列+資料列」。
    total = int(total_block[0][1])

    return {'levels': levels, 'gain': gain, 'total': total}


def main():
    result = build()
    out_path = os.path.join(DATA, 'pets.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, separators=(',', ':'))
    non_empty = sum(1 for p in result['pets'] if p['levels'])
    print(
        f"寫入 {out_path}，共 {len(result['pets'])} 隻寵物"
        f"（{non_empty} 隻有逐等級數值）、{len(result['skills'])} 個技能書、"
        f"unmatched {len(result['unmatched'])} 筆。"
    )


if __name__ == '__main__':
    main()
