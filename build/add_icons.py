# -*- coding: utf-8 -*-
"""
補上 docs/data/monsters.json 與 docs/data/npcs.json 缺的 icon 欄位。

背景：這兩份資料裡本來就各自帶著「image」（怪物）／「portrait」（NPC）欄位，
指向 docs/img/monsters 或 docs/img/npcs 底下的實際圖檔，只是網站前端讀的是
「icon」這個 key，所以列表頁一直顯示不出圖（只有 maps.json 裡的怪物清單被
另外處理過，帶了正確的 icon）。

判斷優先順序（可信度由高到低）：
  1. 資料本身既有欄位：monsters.json 的 image / npcs.json 的 portrait。
     這是遊戲原始資料帶出來的，最可靠。
  2. 其他檔案裡已經驗證過的既有對應：
     - maps.json 的 monsters[*].icon（依 id 對應）
     - quests.json 的 hunt[*].target.icon（依 id 對應，target 就是怪物）
     這兩個只用來「交叉驗證」上面的 image 欄位是否一致，衝突時以資料本身
     （image/portrait）為準，並回報衝突筆數。
  3. 都沒有的話，才退回用「檔名比對」：拿 name 去對 docs/img/monsters 或
     docs/img/npcs 底下的檔名，比對時考慮：
       - 全形符號替換：% -> ％、/ -> ／、# -> ＃（檔名系統不能用半形這些符號）
       - 同名不同圖的 -2、-3 後綴：若同一個 name 在資料裡出現多次且都還沒
         有圖，依照它們在原始資料裡出現的順序，依序配對 name.png、
         name-2.png、name-3.png...
  4. 上述都比對不到，icon 留空字串 ""，不亂配一張圖。

重跑保證：本腳本是純函式式重算（不依賴前一次執行結果），只要輸入資料與圖檔
目錄不變，兩次執行輸出的 JSON bytes 會完全相同（md5 相同）。
"""
import json
import os
import re
import hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'docs', 'data')
IMG = os.path.join(ROOT, 'docs', 'img')

MONSTERS_PATH = os.path.join(DATA, 'monsters.json')
NPCS_PATH = os.path.join(DATA, 'npcs.json')
MAPS_PATH = os.path.join(DATA, 'maps.json')
QUESTS_PATH = os.path.join(DATA, 'quests.json')

FULLWIDTH_MAP = {
    '%': '％',
    '/': '／',
    '#': '＃',
}

SUFFIX_RE = re.compile(r'^(.*)-(\d+)$')


def fullwidth(name):
    """把檔名系統禁用的半形符號換成全形，供檔名比對用。"""
    out = name
    for half, full in FULLWIDTH_MAP.items():
        out = out.replace(half, full)
    return out


def list_png_stems(dirpath):
    """列出資料夾底下所有 .png 檔名（不含副檔名）。"""
    stems = set()
    for fn in os.listdir(dirpath):
        if fn.lower().endswith('.png'):
            stems.add(fn[:-4])
    return stems


def group_by_base(stems):
    """把「基底名-2」「基底名-3」這類檔名，依基底名分組並排序。
    沒有後綴的排最前面（視為第 1 張），其餘依數字後綴排序。
    回傳 dict: base_name -> [stem, stem, ...]（已排序）
    """
    groups = {}
    for stem in stems:
        m = SUFFIX_RE.match(stem)
        if m:
            base, n = m.group(1), int(m.group(2))
        else:
            base, n = stem, 1
        groups.setdefault(base, []).append((n, stem))
    for base in groups:
        groups[base].sort(key=lambda t: t[0])
        groups[base] = [stem for _, stem in groups[base]]
    return groups


def build_filename_matcher(dirpath, subdir):
    """回傳一個函式：給一串「同名記錄」的 name 清單（依原始順序），
    依序配對 dirpath 底下對應的圖檔，回傳對應的 icon 相對路徑清單
    （長度與輸入相同，配不到的位置是 None）。
    """
    stems = list_png_stems(dirpath)
    groups = group_by_base(stems)

    def match_many(name):
        """單一 name 對應到候選檔名分組（可能有 -2/-3 多張）。"""
        candidates = [name, fullwidth(name)]
        for cand in candidates:
            if cand in groups:
                return groups[cand]
        return []

    def resolve(names_in_order):
        """names_in_order: 同一個 name 值在原始資料中依序出現的清單。
        回傳等長的 icon 路徑清單（找不到的是 None）。
        """
        if not names_in_order:
            return []
        name = names_in_order[0]
        stems_for_name = match_many(name)
        result = []
        for i in range(len(names_in_order)):
            if i < len(stems_for_name):
                result.append('img/%s/%s.png' % (subdir, stems_for_name[i]))
            else:
                result.append(None)
        return result

    return resolve


def assign_filename_icons(records, dirpath, subdir):
    """對還沒有 icon 的 records（monsters 或 npcs），依 name 分組後
    用檔名比對配上 icon。回傳 dict: record 的 index -> icon path（僅含配到的）。
    """
    resolver = build_filename_matcher(dirpath, subdir)

    # 依 name 分組，保留原始出現順序（只挑還沒有 icon 的）
    order_by_name = {}
    for idx, rec in enumerate(records):
        if rec.get('icon'):
            continue
        order_by_name.setdefault(rec['name'], []).append(idx)

    assigned = {}
    for name, idxs in order_by_name.items():
        paths = resolver([name] * len(idxs))
        for idx, path in zip(idxs, paths):
            if path and os.path.exists(os.path.join(ROOT, 'docs', path)):
                assigned[idx] = path
    return assigned


def main():
    monsters = json.load(open(MONSTERS_PATH, encoding='utf-8'))
    npcs = json.load(open(NPCS_PATH, encoding='utf-8'))
    maps = json.load(open(MAPS_PATH, encoding='utf-8'))
    quests = json.load(open(QUESTS_PATH, encoding='utf-8'))

    report = {
        'monsters_total': len(monsters),
        'npcs_total': len(npcs),
    }

    # ---------------------------------------------------------------
    # 1. 怪物：先建立「其他檔案裡既有的正確對應」索引，用來交叉驗證
    #    maps.json monsters[*] 與 quests.json hunt[*].target 都是依 id
    #    對應怪物，且理論上帶的是同一張圖。
    # ---------------------------------------------------------------
    xref_by_id = {}  # monster id -> {source_name: icon}
    for mp in maps:
        for mon in mp.get('monsters', []):
            if mon.get('icon'):
                xref_by_id.setdefault(mon['id'], {})['maps.json'] = mon['icon']
    for q in quests:
        for h in q.get('hunt', []):
            t = h.get('target')
            if t and t.get('icon'):
                xref_by_id.setdefault(t['id'], {})['quests.json(hunt)'] = t['icon']

    monster_conflicts = 0
    monster_from_own_field = 0
    for m in monsters:
        primary = m.get('image') or ''
        refs = xref_by_id.get(m['id'], {})
        for src, icon in refs.items():
            if primary and icon != primary:
                monster_conflicts += 1
            elif not primary and icon:
                # 資料本身沒有 image，但外部索引有，也採用（仍算「既有資料」來源）
                primary = icon
        if primary:
            m['icon'] = primary
            monster_from_own_field += 1
        else:
            m['icon'] = ''

    # 檔名比對兜底（monsters.json 目前每筆都有 image，理論上不會用到，
    # 但保留這條路徑以應付未來資料缺欄位的情況）。
    mon_dir = os.path.join(IMG, 'monsters')
    assigned = assign_filename_icons(monsters, mon_dir, 'monsters')
    monster_from_filename = 0
    for idx, path in assigned.items():
        monsters[idx]['icon'] = path
        monster_from_filename += 1

    # ---------------------------------------------------------------
    # 2. NPC：npcs.json 自帶的 portrait 欄位是既有正確資料（maps.json /
    #    quests.json 的 npcs 陣列本身沒有帶 icon，無從交叉比對）。
    # ---------------------------------------------------------------
    npc_from_own_field = 0
    for n in npcs:
        primary = n.get('portrait') or ''
        n['icon'] = primary
        if primary:
            npc_from_own_field += 1

    npc_dir = os.path.join(IMG, 'npcs')
    assigned_n = assign_filename_icons(npcs, npc_dir, 'npcs')
    npc_from_filename = 0
    for idx, path in assigned_n.items():
        npcs[idx]['icon'] = path
        npc_from_filename += 1

    # ---------------------------------------------------------------
    # 3. 把 icon 欄位搬到 name 後面（跟 maps.json 裡怪物清單的欄位順序一致），
    #    只調整欄位順序，不動其他任何欄位的值。
    # ---------------------------------------------------------------
    def reorder(rec):
        new = {}
        for k, v in rec.items():
            if k == 'icon':
                continue
            new[k] = v
            if k == 'name':
                new['icon'] = rec['icon']
        if 'icon' not in new:
            new['icon'] = rec.get('icon', '')
        return new

    monsters = [reorder(m) for m in monsters]
    npcs = [reorder(n) for n in npcs]

    # ---------------------------------------------------------------
    # 4. 驗證每個非空 icon 路徑真的存在，並收集找不到圖的名字
    # ---------------------------------------------------------------
    def check_broken(records):
        broken = []
        for r in records:
            if r['icon'] and not os.path.exists(os.path.join(ROOT, 'docs', r['icon'])):
                broken.append((r['id'], r['name'], r['icon']))
        return broken

    monster_broken = check_broken(monsters)
    npc_broken = check_broken(npcs)

    monster_missing = sorted({r['name'] for r in monsters if not r['icon']})
    npc_missing = sorted({r['name'] for r in npcs if not r['icon']})

    monster_filled = sum(1 for r in monsters if r['icon'])
    npc_filled = sum(1 for r in npcs if r['icon'])

    # ---------------------------------------------------------------
    # 5. 寫回檔案（緊湊格式，跟原始檔案一致：無空白、無多餘換行）
    # ---------------------------------------------------------------
    before_m_size = os.path.getsize(MONSTERS_PATH)
    before_n_size = os.path.getsize(NPCS_PATH)

    with open(MONSTERS_PATH, 'w', encoding='utf-8') as f:
        json.dump(monsters, f, ensure_ascii=False, separators=(',', ':'))
    with open(NPCS_PATH, 'w', encoding='utf-8') as f:
        json.dump(npcs, f, ensure_ascii=False, separators=(',', ':'))

    after_m_size = os.path.getsize(MONSTERS_PATH)
    after_n_size = os.path.getsize(NPCS_PATH)

    def md5(path):
        return hashlib.md5(open(path, 'rb').read()).hexdigest()

    # ---------------------------------------------------------------
    # 6. 報告
    # ---------------------------------------------------------------
    print('=== 怪物 monsters.json ===')
    print('總筆數: %d' % len(monsters))
    print('補上 icon: %d 筆 / 空白: %d 筆' % (monster_filled, len(monsters) - monster_filled))
    print('  其中：來自既有資料(image/交叉驗證): %d 筆，來自檔名比對: %d 筆' % (
        monster_from_own_field, monster_from_filename))
    print('  既有資料 vs 交叉驗證來源 衝突筆數: %d' % monster_conflicts)
    print('  壞掉的 icon 路徑(檔案不存在): %d' % len(monster_broken))
    if monster_broken:
        print('  壞掉明細:', monster_broken[:20])
    print('  找不到圖的怪物 (共 %d 筆), 前 20 筆:' % len(monster_missing))
    print('   ', monster_missing[:20])

    print()
    print('=== NPC npcs.json ===')
    print('總筆數: %d' % len(npcs))
    print('補上 icon: %d 筆 / 空白: %d 筆' % (npc_filled, len(npcs) - npc_filled))
    print('  其中：來自既有資料(portrait): %d 筆，來自檔名比對: %d 筆' % (
        npc_from_own_field, npc_from_filename))
    print('  壞掉的 icon 路徑(檔案不存在): %d' % len(npc_broken))
    if npc_broken:
        print('  壞掉明細:', npc_broken[:20])
    print('  找不到圖的 NPC (共 %d 筆), 前 20 筆:' % len(npc_missing))
    print('   ', npc_missing[:20])

    print()
    print('=== 檔案大小 ===')
    print('monsters.json: %d -> %d bytes' % (before_m_size, after_m_size))
    print('npcs.json: %d -> %d bytes' % (before_n_size, after_n_size))

    print()
    print('=== md5（供重跑比對用）===')
    print('monsters.json md5: %s' % md5(MONSTERS_PATH))
    print('npcs.json md5: %s' % md5(NPCS_PATH))


if __name__ == '__main__':
    main()
