#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「系統」頁（強化石表 + 轉職考試題庫）殘留的英文／印尼文中文化。

只處理 docs/data/wiki.json 裡的 w['stones']（4 張強化石表）與
w['exam']（71 題轉職考試），並順手複查 w['skills'] / w['badges'] 這兩塊
先前已中文化過、但仍有漏網英文／印尼文的欄位。

w['matrix'] / w['jobTree'] / w['jobWeapons'] / w['monAttrs'] 經檢查已全數
為中文，這裡不再處理。

比對依據（重要，寫在這裡而不是散落在 dict 裡，方便日後複查）：

1. 強化石名稱：對照 docs/data/items.json 裡 category == "強化石" 的 30 筆
   （G1231/G1232/G1233/G1234 = 基礎方/水/銀/金石；G1462~G1473 = 發光的強化
   方/水/銀/金石 I/II/III；G1596/G1597 = 強化紅/綠寶石；G1598~G1603 = 發光的
   強化紅/綠寶石 I/II/III）。wiki 表格英文用 "Ruby Stone"/"Diamond Stone"
   代表最後兩階，但 items.json 只有「紅寶石／綠寶石」兩色，且沒有任何
   「鑽石」強化石存在 —— 所以判定 wiki 的 "Diamond Stone" 其實對應
   items.json 的「強化綠寶石」（原文用詞不準，但物件只有這一種能對得上，
   且與 Ruby 恰好湊成紅/綠寶石一對）。
   "Sealed X Stone"：items.json 只查得到 I0755「密封的強化紅寶石」、
   I0756「密封的強化綠寶石」兩筆，規律是「密封的」+ 對應階的基礎名稱，
   其餘 Pillar/Water/Silver/Gold 沒有對應項目，用同一規律類推
   （例如 Sealed Water Stone -> 密封的強化的水石，沿用水石基礎名稱
   本身「強化的水石」中間那個「的」，不額外整理成看起來更順的字面）。

2. 強化階級 Good/Great/Super/Extreme/Heroes/Legendary：遊戲資料裡找不到
   既有中文對照，採一般電玩慣用譯法（優良／優秀／超級／極致／英雄／傳說）。

3. 能力效果詞：Skill Attack/Attack/Defense/Evasion/Accuracy/Critical rate/
   Agility/Intellect/Attack Speed/Attack Range 等，依常見翻法對照，
   "... Points" 的 Points 依指示省略不譯。

4. 頭目名稱：使用者已查證的 19 筆對照表直接套用；另外三個在表格出現、
   但查無實據的 "Chocachoca"／"Medusa"／"Typerose King Of Beast"，
   在 docs/data/wiki.json 的 w['badges'] 內用同樣方式（"en" 欄位對照
   中文 boss 名）都找不到對應項目，因此保留英文原文，不猜。

5. 轉職考試（w['exam']）77 個原始答案裡，實際只有 71 個不重複、且
   "Captain Hyde"／"Babidu" 兩個名字在目前的 wiki.json 裡完全找不到
   （已用全文搜尋確認），因此這兩筆對照表雖然保留在 dict 裡（不影響
   任何比對結果），但目前的資料不會用到。
   其餘每一筆的判斷依據，見 EXAM_NAME 之後的個別註解，主要來源：
   - docs/data/npcs.json 的 desc 欄（含年齡／職業／興趣／特技／座右銘）
     與題目文字逐句核對，命中率極高（例如「興趣：收集漂亮的瓶子」對
     「興趣：搜集美麗的瓶子」）。
   - docs/data/monsters.json 的 name／desc 欄，只用「英文字面 = 中文
     名稱組成部件」這種精準對應（例如 Pink Jelly=粉紅果凍、
     Rabbit Mask=假面兔），或 desc 內容與題目近乎同義改寫的強證據
     （例如「巨大布丁」desc 講「以自己的身體吸引住敵人...吸收」對應
     「Curse Jelly」題目「將敵人吸入體內來攻擊」）。
   - 對不上的一律保留英文，不用「等級排序」「同一家族湊數」這類弱證據
     去湊答案（唯一例外是強化石頭目表，那份對照表是使用者已驗證過、
     直接提供的，不是本腳本自行推論）。

6. w['skills'] 的 desc 欄位，還有 26 筆整句是印尼文（未被上一輪
   wiki_i18n.py 處理到），以及另外一批 desc 是中文但夾雜幾個英文／印尼文
   詞（Dark Magic／crossbow／holy／undead／dualsword／double sword／
   darkness／lightning／Dead 屬性）沒翻。這裡一併修掉。

7. w['badges'] 裡有一筆徽章 "Hao's Rest" 整個名稱沒翻譯，而且它的
   method 欄位「完成 Charlote 的所有任務」、另一筆「惡魔獵人」徽章的
   method「完成 Dracula 的所有任務」，Charlote／Dracula 都是未翻譯的
   NPC 英文名。這裡用 data/raw.json 的原始 wiki 頁面反查：
   - Charlote：原始頁面聲音檔案是 npc_horunha*.ogg（韓文 호른하르트 的
     羅馬拼音），對照 docs/data/quests.json 裡等級 42、於「郝代杻入口」
     發布、內容是獵殺 Ancient Beetle 的任務 Q0199「賀登的歷史」
     （原文 "Kisah dari Charlote"），該任務 NPC 正是 N0155「虎任哈日特」，
     锁定唯一對應。
   - Dracula：原始頁面聲音檔案是 npc_batecura*.ogg，對照
     docs/data/npcs.json 的 N0152「巴泰規拉」（193cm，職業「城主」，
     興趣「鑑賞美術品」，座右銘「不要再吸血了」），身高／職業／興趣／
     座右銘四項全部吻合原始頁面的 193 Cm / Landlord / Menikmati seni /
     吸血座右銘，確定無疑。
   - "Hao's Rest" 徽章名稱本身：來源任務發生在地圖「郝代杻入口」
     （H0000），同一區域內 docs/data/maps.json 有「M0043 古代人之休息地」
     這張地圖，語意（Hao's Rest = 某處的休息地）與地區直接對應，
     採用這個既有地圖名稱作譯名。

執行方式：
    python3 build/system_i18n.py

冪等：所有替換都是「英文/印尼文原文 -> 中文」的精確字串比對，跑第二次時
找不到原文字串（已經被換成中文）就不會再動，因此重跑兩次輸出位元組相同。
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(ROOT, 'docs', 'data', 'wiki.json')


# ---------------------------------------------------------------------------
# ① 強化石表
# ---------------------------------------------------------------------------

# 依 docs/data/items.json category=="強化石" 的 30 筆比對出來的名稱對照。
STONE_NAME = {
    'Pillar Stone': '強化方石',
    'Pillar Stone I': '發光的強化方石 I',
    'Pillar Stone II': '發光的強化方石 II',
    'Pillar Stone III': '發光的強化方石 III',
    'Water Stone': '強化的水石',
    'Water Stone I': '發光的強化水石 I',
    'Water Stone II': '發光的強化水石 II',
    'Water Stone III': '發光的強化水石 III',
    'Silver Stone': '強化的銀石',
    'Silver Stone I': '發光的強化銀石 I',
    'Silver Stone II': '發光的強化銀石 II',
    'Silver Stone III': '發光的強化銀石 III',
    'Gold Stone': '強化的金石',
    'Gold Stone I': '發光的強化金石 I',
    'Gold Stone II': '發光的強化金石 II',
    'Gold Stone III': '發光的強化金石 III',
    'Ruby Stone': '強化紅寶石',
    'Ruby Stone I': '發光的強化紅寶石 I',
    'Ruby Stone II': '發光的強化紅寶石 II',
    'Ruby Stone III': '發光的強化紅寶石 III',
    # 見檔頭說明：wiki 原文的 "Diamond Stone" 其實對應 items.json 的
    # 「強化綠寶石」（遊戲裡沒有「鑽石強化石」這種東西）。
    'Diamond Stone': '強化綠寶石',
    'Diamond Stone I': '發光的強化綠寶石 I',
    'Diamond Stone II': '發光的強化綠寶石 II',
    'Diamond Stone III': '發光的強化綠寶石 III',
    # Sealed 系列：Ruby/Diamond 兩筆有 items.json I0755/I0756 實證，
    # 其餘 4 筆用「密封的」+ 基礎名稱同一規律類推。
    'Sealed Pillar Stone': '密封的強化方石',
    'Sealed Water Stone': '密封的強化的水石',
    'Sealed Silver Stone': '密封的強化的銀石',
    'Sealed Gold Stone': '密封的強化的金石',
    'Sealed Ruby Stone': '密封的強化紅寶石',
    'Sealed Diamond Stone': '密封的強化綠寶石',
}

# 強化階級：遊戲資料裡查無既有中文譯名，採通用電玩慣用譯法。
TIER_NAME = {
    'Good': '優良',
    'Great': '優秀',
    'Super': '超級',
    'Extreme': '極致',
    'Heroes': '英雄',
    'Legendary': '傳說',
}

# 能力效果詞（表 3：屬性加成）。
EFFECT_TERM = {
    'Skill Attack': '技能攻擊力',
    'Attack': '攻擊力',
    'Defense': '防禦力',
    'Evasion': '迴避',
    'Accuracy': '命中',
    'Critical rate': '爆擊率',
    'Agility': '敏捷',
    'Strength': '力量',
    'Intellect': '智力',
    'Stamina': '體力',
    'Max HP': '最大 HP',
    'Max MP': '最大 MP',
    'Attack Speed': '攻擊速度',
    'Attack Range': '攻擊距離',
}

# 頭目名稱：使用者已查證（舊資料怪物等級對現行 boss 等級一比一落位 +
# 韓文名交叉驗證）的 19 筆，直接套用。
BOSS_NAME = {
    'Captain Jay Bubble': '深海閻王',
    'Dr Kingbo': 'DR.金伯',
    'Blue Fire Bead': '吸血魔珠',
    'Wolf Heroes': '貝爾沃夫',
    'Jelly Master': '巨大果凍',
    'Chadunka': '車頓卡',
    'Fire Master Jelly': '火焰果凍',
    'Volcano': '火山岩怪',
    'Gratos The Ancient Machine': '拉克馬提IV',
    'Endless Dragon': '卡司特蘭',
    'Beawolf': '鐵爪影狼',
    'Destroyer': '惡猛螳螂',
    'Skeleton Hand': '撒旦的左手',
    'Ware Wolf': '首領趴趴犬',
    'Evil Minotaur': '死亡山羊',
    'Darksiders': '黃金爪小精靈',
    'Curse Sword': '血魔劍',
    'Dark Lord': '黑暗魔王',
    'Orochi': '鷲翼蛇妖',
    # 註：Chocachoca / Medusa / Typerose King Of Beast 三個頭目名在
    # w['badges'] 的 "en" 欄位裡查不到對應項目，無法驗證，保留英文。
}

# 密封強化石掉落表最後一欄「寶箱」，同表另外還殘留這兩個英文道具名，
# 遊戲資料裡沒有「Gold/Diamond Wedding Box」這種確切品項名可查證，
# 這裡只做字面直譯（金色／鑽石 + 婚禮寶箱），不是身份確認，若有更精準
# 的官方名稱應以那個為準。
CHEST_NAME = {
    'Gold Wedding Box': '黃金婚禮寶箱',
    'Diamond Wedding Box': '鑽石婚禮寶箱',
}

_TIER_RE = re.compile(r'^(Good|Great|Super|Extreme|Heroes|Legendary)(\s*\(.*\))$')
_EFFECT_RE = re.compile(r'^([+-][\d.]+%?)\s+(.+)$')
_PRICE_RE = re.compile(r'^(\d+)\.(\d{3}) Libi$')


def _tier(cell):
    m = _TIER_RE.match(cell)
    if not m:
        return cell
    return TIER_NAME[m.group(1)] + m.group(2)


def _effect(cell):
    m = _EFFECT_RE.match(cell)
    if not m:
        return cell
    num, term = m.groups()
    if term.endswith(' Points'):
        term = term[:-len(' Points')]
    zh = EFFECT_TERM.get(term)
    if zh is None:
        return cell
    return f'{zh} {num}'


def _price(cell):
    m = _PRICE_RE.match(cell)
    if not m:
        return cell
    return f'{m.group(1)},{m.group(2)} Libi'


def _csv_map(cell, table):
    parts = [p.strip() for p in cell.split(',')]
    return ', '.join(table.get(p, p) for p in parts)


def translate_stones(w):
    tables = w['stones']

    # 表 0：強化石清單（圖示／名稱／強化階級／價格）
    for row in tables[0]['rows']:
        c = row['c']
        c[0] = STONE_NAME.get(c[0], c[0])
        c[1] = STONE_NAME.get(c[1], c[1])
        c[2] = _tier(c[2])
        c[3] = _price(c[3])

    # 表 1：密封強化石（圖示／名稱／解封石／BOSS／寶箱）
    for row in tables[1]['rows']:
        c = row['c']
        c[0] = STONE_NAME.get(c[0], c[0])
        c[1] = STONE_NAME.get(c[1], c[1])
        c[2] = _csv_map(c[2], STONE_NAME)
        c[3] = _csv_map(c[3], BOSS_NAME)
        c[4] = _csv_map(c[4], CHEST_NAME)

    # 表 2：機率表（強化階級／武器分組機率）
    for row in tables[2]['rows']:
        c = row['c']
        c[0] = _tier(c[0])

    # 表 3：屬性加成表（強化階級／各武器加成）
    for row in tables[3]['rows']:
        c = row['c']
        c[0] = _tier(c[0])
        for i in range(1, len(c)):
            c[i] = _effect(c[i])


# ---------------------------------------------------------------------------
# ② 轉職考試題庫（w['exam']，71 題，只換「答案」欄）
# ---------------------------------------------------------------------------

EXAM_NAME = {
    # --- 使用者已知確定的 NPC（部分未出現在目前 exam 資料中，保留無妨）---
    'Laura': '蘿拉',
    'Cruno': '克魯諾',
    'Captain Hyde': '克丁哈以德',  # 目前 wiki.json 查無此字串，保留對照表
    'Babidu': '巴比度',            # 同上
    'Keydan': '齊丹',
    'Linea': '麗內雅',
    'Rinoa': '麗歐娜',

    # --- NPC：透過 docs/data/npcs.json 的職業/年齡/興趣/特技/座右銘欄位
    #     與題目文字逐句核對確認（詳見各行註解），信心度高 ---
    # 開場白提到「Buzz、Hawkeye、Keydan、Linea」是四位轉職考官；
    # Keydan/Linea 已確認，N0016~N0019 剛好是同一組連號 NPC
    # （普茲=劍術教官／SWORD、霍克=弓術教官／BOW、齊丹、麗內雅），
    # 由消去法 + 職業標籤對上題目「刻苦訓練」「遠距離攻擊技藝」。
    'Hawkeye': '霍克',   # N0017 弓術教官，desc 完全對應「遠距離攻擊技藝的教導者」
    'Buzz': '普茲',      # N0016 劍術教官
    'Rosy': '露西',      # N0001 desc：16歲／興趣「搜集美麗的瓶子」，與題目字句幾乎一致
    'Fei': '佩伊',       # N0002 desc：17歲／特技「製作鐵鎚」，與題目「17歲／鎚擊」吻合
    'Osvall': '奧斯華',  # N0003 防禦商人，鐵匠鋪／盾牌相關，且發音對應 Osvall
    'Philip': '菲力普',  # N0022 職業「盜賊行幫長」，對應題目 Thief Union
    'Yuffie': '尤莉',    # N0023 desc 興趣「干涉別人的事情」，與題目「插手他人事務」一致
    'Jane': '珍',        # N0133 職業「宿舍及事物箱管理人」，對應「管理倉庫物品」
    'Runpei': '路菲',    # N0131 職業「代銷管理人」，對應「委託他出售物品」；亦見徽章
                          # 「路菲的商店主人 / Owner of Runpei」交叉印證
    'Harlock': '哈洛克', # N0134 職業「船長」，對應「唯一願意幫助我們航行的船主」
    'Roland': '羅蘭德',  # N0160 職業「司令官／聯合司令官」，對應「戰場指揮權向來由他掌握」
    'Louie': '羅雲',     # N0161 職業「補給官」，desc「物資不能不足」，對應「管理部隊補給」
    'Verdin': '貝爾丁',  # N0021 職業「酒店主人」，desc 完全對應「富有的人...擁有一家飯店」

    # --- 怪物：docs/data/monsters.json，英文字面精準對到中文名稱組成部件，
    #     或 desc 內容與題目幾乎同義改寫（詳見各行註解）---
    'Pink Jelly': '粉紅果凍',
    'Purple Jelly': '紫色果凍',       # 題目本身就是「Pink Jely 進化後的形態」
    'Yellow Dreams': '黃夢',          # J0121，黃=Yellow、夢=Dreams
    'Blue Dreams': '青夢',            # J0141，同一家族僅剩此三色可對應
    'Red Dreams': '紅夢',             # J0251
    'Rabbit Mask': '假面兔',          # J0181，兔=Rabbit、假面=Mask
    'Queen Bee': '女王蜂',            # J0281
    'Bumble Bee': '大黃蜂',           # J0271，大黃蜂是 bumblebee 的通行譯法
    'Ghost Sword': '鬼劍',            # J0412，鬼=Ghost、劍=Sword
    'Phantom Warrior': '幻影戰士',    # J0343，幻影=Phantom、戰士=Warrior
    'Magic Sword': '魔劍',            # J0461，魔=Magic、劍=Sword
    'Zombie': '殭屍',                 # J0462，殭屍在傳統上正是穿著素白官服（清代殭屍形象），
                                       # 對應題目「他從不脫下他的白色制服」
    'Drum Racoon': '桶子狸',          # J0211，desc「住在桶子裡的怪物」對應題目字句
    'Old Skeleton Prisoner': '死靈囚犯',  # J0471 desc「拖拉著腳踝上的腳鍊行走」對應題目
                                           # 「腳上掛著非常巨大的鐵墜」
    'Curse Jelly': '巨大布丁',        # J0736 desc「以自己的身體吸引住敵人...吸收」
                                       # 幾乎是題目「將敵人吸入體內來攻擊」的同義改寫
    'Crab': '自大的螃蟹',             # J0398 desc「以巨大的螯腳來攻擊」對應
                                       # 「一對用來攻擊敵人的鉗子」

    # --- 怪物：desc 主題吻合、但字面非唯一嚴格對應，中等信心度，
    #     列在這裡並在報告中特別註明，供覆核 ---
    'Sand Stoker': '沙怪',            # J0419 desc「移動的同時具有吞食物體的能力」
    'Sea Star Warrior': '人面海星',   # J0409，「Sea Star」= 海星字面精準對應，
                                       # 但「人面」「Warrior」非字面互譯，中等信心度
    'Wolf Ranger': '夜狼弓箭手',      # J0421，Ranger／Archer 為常見電玩慣例對應，
                                       # 非嚴格字面翻譯，中等信心度
    'Harpy': '威克鷹',                # J0732 desc「翅膀」＋「腳指甲攻擊」對應題目，
                                       # 但「鷹」非「Harpy」字面翻譯，中等信心度
}


def translate_exam(w):
    for row in w['exam']['rows']:
        c = row['c']
        c[1] = EXAM_NAME.get(c[1], c[1])


# ---------------------------------------------------------------------------
# ③ 複查 skills / badges 殘留英文、印尼文
# ---------------------------------------------------------------------------

# w['skills'] 有 26 筆 desc 整句仍是印尼文（先前 wiki_i18n.py 沒處理到）。
# 以技能名稱（154 筆全部不重複）為 key，避免同句不同技能誤用同一段文字。
SKILL_DESC_FIX = {
    'Bow Mastery': '提升使用弓的能力',
    'Double Shot': '射擊兩次',
    'Energy Restore': '提升 MP 恢復',
    'Gun Mastery': '提升使用手槍的能力',
    'Precision': '提升爆擊機率',
    'Guardian': '提升對怪物攻擊的防禦力',
    'Holy Armor': '提升自身防禦力',
    'Prayers': '提升 MP 恢復',
    'Axe Mastery': '使用斧時提升攻擊力',
    'Combat Training': '提升攻擊破壞力',
    'Spear Mastery': '使用長槍時提升攻擊力',
    'Strengthening': '提升體力',
    'Vital Energy': '提升最大 HP',
    'Chain Wave': '在一定距離內對敵人造成兩次傷害',
    'Dagger Blessing': '使用短劍時提升致命攻擊機率',
    'Enchanted Life': '提升最大 HP',
    'Evocation': '提升 MP 恢復',
    'Harden Body': '提升防禦力',
    'Magic Power': '提升 MP 恢復',
    'Magic Shield': '提升防禦力',
    'Mana Surge': '提升最大 MP',
    'Mind Recovery': '進一步提升 MP 恢復',
    'Soul Meditation': '使用技能時減少 MP 消耗',
    'Staff Mastery': '使用魔法杖時提升能力',
    'Staff Training': '使用魔法杖時提升攻擊力',
}

# 已翻成中文、但夾雜個別英文詞的 desc（含前後空白，確保精準比對／
# 冪等：翻過一次後這些帶空白的英文子字串就不存在了）。
SKILL_DESC_EMBEDDED_FIX = [
    (' Dark Magic ', '黑魔法'),
    (' crossbow ', '十字弓'),
    (' holy ', '神聖'),
    (' undead ', '不死'),
    (' dualsword ', '雙劍'),
    (' double sword ', '雙劍'),
    (' darkness ', '闇'),
    (' lightning ', '雷'),
    ('Dead 屬性', '不死屬性'),
]


def translate_skills(w):
    for s in w['skills']:
        fix = SKILL_DESC_FIX.get(s['name'])
        if fix is not None:
            s['desc'] = fix
        for eng, zh in SKILL_DESC_EMBEDDED_FIX:
            if eng in s['desc']:
                s['desc'] = s['desc'].replace(eng, zh)


# w['badges']：一筆徽章名稱未翻譯，另外兩筆的 method 欄位裡有未翻譯的
# NPC 英文名（見檔頭第 7 點的反查過程）。
BADGE_NAME_FIX = {
    "Hao's Rest": '古代人之休息地',
}
BADGE_METHOD_FIX = {
    '完成 Charlote 的所有任務': '完成 虎任哈日特 的所有任務',
    '完成 Dracula 的所有任務': '完成 巴泰規拉 的所有任務',
}


def translate_badges(w):
    for b in w['badges']:
        if b['name'] in BADGE_NAME_FIX:
            b['name'] = BADGE_NAME_FIX[b['name']]
        if b.get('method') in BADGE_METHOD_FIX:
            b['method'] = BADGE_METHOD_FIX[b['method']]


# ---------------------------------------------------------------------------
# 驗收：掃描殘留英文
# ---------------------------------------------------------------------------

_ALLOWED_TOKENS = {
    'Libi', 'PvP', 'PvM', 'NPC', 'HP', 'MP', 'BOSS', 'DR', 'DOT', 'ALT',
    'I', 'II', 'III', 'IV', 'V', 'VI', 'G-Joe',
}
_LATIN_RE = re.compile(r'[A-Za-z][A-Za-z\-\']*')


def _residual_latin(cell):
    return [w for w in _LATIN_RE.findall(cell) if w not in _ALLOWED_TOKENS]


def scan_residual(w):
    hits = []
    for ti, t in enumerate(w['stones']):
        for row in t['rows']:
            for ci, cell in enumerate(row['c']):
                bad = _residual_latin(cell)
                if bad:
                    hits.append(('stones', ti, ci, cell, bad))
    for ri, row in enumerate(w['exam']['rows']):
        for ci, cell in enumerate(row['c']):
            bad = _residual_latin(cell)
            if bad:
                hits.append(('exam', ri, ci, cell, bad))
    return hits


def main():
    with open(WIKI, encoding='utf-8') as f:
        w = json.load(f)

    n_skills, n_badges, n_exam = len(w['skills']), len(w['badges']), len(w['exam']['rows'])

    translate_stones(w)
    translate_exam(w)
    translate_skills(w)
    translate_badges(w)

    assert len(w['skills']) == n_skills, 'skills 筆數跑掉了'
    assert len(w['badges']) == n_badges, 'badges 筆數跑掉了'
    assert len(w['exam']['rows']) == n_exam, 'exam rows 筆數跑掉了'

    with open(WIKI, 'w', encoding='utf-8') as f:
        json.dump(w, f, ensure_ascii=False, separators=(',', ':'))

    hits = scan_residual(w)
    print(f'skills={len(w["skills"])} badges={len(w["badges"])} exam_rows={len(w["exam"]["rows"])}')
    print(f'殘留英文儲存格數：{len(hits)}')
    for kind, i, ci, cell, bad in hits:
        print(f'  [{kind}] table/row={i} col={ci}: {cell!r} -> {bad}')


if __name__ == '__main__':
    main()
