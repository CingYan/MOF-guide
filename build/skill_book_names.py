#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用 docs/data/items.json 的「技能書」品項中文名，補上 docs/data/wiki.json 裡
還是英文的技能名稱（build/skill_names.py 跑完之後仍剩 49 筆）。

用法：
    python3 build/skill_book_names.py

行為：
    - 只讀 docs/data/items.json（不寫），只就地改寫 docs/data/wiki.json。
      不會動 docs/app.js、docs/style.css 或其他任何檔案。
    - 只改 MAPPING 裡列出的技能：把 name 換成中文、加 en 欄位保留原英文、
      levels[*].name 跟著換（"Inferno III" -> "百萬噸級火焰 III"）。
    - 套用前逐筆二次驗證 img / 職業 / 等級 / 技能書是否仍吻合，任何一項對不上
      就跳過該筆並印警告，不硬套。
    - 可重複執行；跑兩次 wiki.json 的 md5 相同。
    - 全程檢查 skills 筆數（154）與每筆 levels 筆數不變。

──────────────────────────────────────────────────────────────────────────
方法（為什麼可以這樣配）
──────────────────────────────────────────────────────────────────────────
關鍵不是職業名稱，而是 wiki.json 每個技能的 `img` 欄位：它是遊戲原始素材檔名
（Sage_Skill1.png、Holy_Avanger_Skill6.png…），前綴就是該技能所屬職業的英文
代號。把技能按 img 前綴分組，再把技能書按 pandora（「將軍1級 技術」）的職業
分組，然後用「書名 == 已中文化技能名」的 43 組已知正確配對去反推兩套職業命名
的對照表，就得到一組乾淨的一對一職業對照（見下方 JOB_MAP）。

有了職業對照之後，候選集合被壓到每組 2~8 筆，再疊三個訊號做整體一對一指派：
  (1) 巴哈「大 陸 島 嶼 對 N P C 學 技 能 所 需 點 數」的表格，逐職業列出
      主動/被動 + 中文技能名 + 等級 —— 拿來當硬條件過濾（類型、等級必須相符）。
  (2) 技能書 desc 與 wiki desc 的字元 bigram Jaccard 相似度。
  (3) wiki levels[*].f 的數值欄位（傷害 %、爆擊 %、回復量、隊伍加成…）與
      技能書 desc 裡的數字直接對撞。

這套流程套回 43 組已知正確配對，重現 37/43 = 86.0%；6 筆失誤全是同職業內
語意近乎相同的對稱配對（賦予閃電屬性/賦予黑暗屬性、上下端攻擊/四方攻擊、
以及狙擊手/遊俠共用的遁避訓練造成的結構性假失誤）。本檔採用的 24 筆都不落在
那種對稱組裡：每一筆都另外有一個決定性訊號（數值、獨佔等級、或同組窮舉），
逐筆證據見 MAPPING 的註解。

沒把握的一律不動：剩下 25 筆保持英文，原因見檔尾 UNRESOLVED。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI_JSON_PATH = os.path.join(ROOT, "docs", "data", "wiki.json")
ITEMS_JSON_PATH = os.path.join(ROOT, "docs", "data", "items.json")

# ---------------------------------------------------------------------------
# 職業對照表：技能書 pandora 的職業名 -> wiki.json 技能 img 前綴
#
# 三轉 16 職（由 43 組「書名 == 已中文化技能名」的已知配對反推，每一格都是
# 唯一對應，沒有一對多）：
#   將軍→General(4)   英雄→Heroes(4)   騎士→Knight(3)   鐵甲武士→Sword_Master(3)
#   哲人→Sage(3)      咒術師→Warlock(4) 法櫃巫師→Arc_Mage(2) 黃教巫師→Shaman(5)
#   狙擊手→Sniper(3)  遊俠→Ranger(1)   神射手→Sharpshooter(2) 神槍手→Specialist(3)
#   聖徒→Saint(3)     主教→Bishop(3)
#   （括號內是支持該格的已知配對數；遊俠/狙擊手共用「遁避訓練」一本，
#     所以遊俠那格只有 1 票，但 Ranger 其餘 6 本全部落在 Ranger 前綴。）
#   聖騎士→Paladin、聖靈判官→Holy_Avanger 沒有「書名完全等於技能名」的已知
#   配對（都差在「的/之」），但 8 本 Paladin 書全部只能落在 Paladin 的 7 個
#   技能上、4 本聖靈判官書全部只能落在 Holy_Avanger 的 7 個技能上。
#
# 四轉 8 職（技能書 I0798-I0877，每職剛好 2 本；wiki 每個四轉職剛好 2 個技能）：
#   終極鬥士→Dragon_Knight  聖堂武士→Slayer      皇家射手→Imperial_Shooter
#   鎗神→Trickster          賢者→Sorcerer        冥術師→Oracle
#   先知→Cardinal           教皇→Arc_Bishop
#   佐證一：id 排列本身就是「8 職各一本」跑兩輪 ——
#     I0798/0803/0808/0813/0818/0823/0828/0833 是每職的第 1 本，
#     I0838/0843/0848/0853/0858/0863/0868/0873 是每職的第 2 本，
#     而且第 1 本對到 *_Skill1、第 2 本對到 *_Skill2，順序完全吻合。
#   佐證二：巴哈「分享職業心得-其實很強的【鎗神】」寫明轉職路線
#     「弓箭手→遊俠→神鎗手→鎗神」，鎗神就是神槍手(Specialist)的四轉，
#     對上 wiki 弓箭手線的四轉 Trickster。
#   佐證三：注意兩套命名互相打架 —— 技能書的「賢者」是四轉(=wiki 咒術師,
#     Sorcerer)，而 wiki 的「賢者」是三轉 Sage(=技能書的「哲人」)。所以職業名
#     絕對不能當鍵，只能當反推出來的對照表用。
# ---------------------------------------------------------------------------
JOB_MAP = {
    # 三轉
    "將軍": "General", "英雄": "Heroes", "騎士": "Knight", "鐵甲武士": "Sword_Master",
    "哲人": "Sage", "咒術師": "Warlock", "法櫃巫師": "Arc_Mage", "黃教巫師": "Shaman",
    "狙擊手": "Sniper", "遊俠": "Ranger", "神射手": "Sharpshooter", "神槍手": "Specialist",
    "聖徒": "Saint", "主教": "Bishop", "聖騎士": "Paladin", "聖靈判官": "Holy_Avanger",
    # 四轉
    "終極鬥士": "Dragon_Knight", "聖堂武士": "Slayer", "皇家射手": "Imperial_Shooter",
    "鎗神": "Trickster", "賢者": "Sorcerer", "冥術師": "Oracle",
    "先知": "Cardinal", "教皇": "Arc_Bishop",
}

# ---------------------------------------------------------------------------
# 對照表欄位：
#   (英文技能名, wiki img, 期望職業(f.職業/f.需求職業), 期望等級(f.等級/f.需求等級),
#    中文技能名, 技能書首本 id, 技能書職業(pandora；四轉/活動技能書可能沒有),
#    證據)
#
# 中文名一律照 items.json 技能書的原字串（遊戲內文字），不做潤飾。
# 前四欄是套用前的二次驗證用；對不上就跳過不套。
# ---------------------------------------------------------------------------
MAPPING = [
    # ===== 活動技能（Event_Skill*，無職業、只有 1 階）=====
    # 這兩本技能書沒有羅馬階級也沒有 pandora，剛好對上 wiki 只有 1 階、
    # 職業為「無」的兩個 Event 技能；且 id 連號 I0905/I0906 對 Skill1/Skill2。
    ("Hide", "Event_Skill1.png", "無", "20", "隱身術", "I0905", "",
     "I0905 隱身術「使用暗黑的魔力, 隱身自己身體的技術.」vs wiki「使用黑魔法進行隱匿」；"
     "全 540 本技能書只有 I0905/I0906 沒有羅馬階級，剛好對上 wiki 僅有的兩個 1 階技能"),
    ("Injure Enemy", "Event_Skill2.png", "無", "25", "醉生夢死術", "I0906", "",
     "I0906 醉生夢死術「使技能攻擊到的怪物持續受到傷害.」vs wiki「對怪物施加 DOT（持續傷害）」；"
     "1 階、無職業，與 Hide 同組，id 連號對 Event_Skill2"),

    # ===== 聖靈判官 / Holy_Avanger 三轉（4 本書，7 個技能）=====
    # 巴哈 NPC 學技能表：聖靈判官 主動 1.勇猛的祝福(lv60) 2.賦予神性的屬性(lv70)；
    #                    被動 1.神的反擊(lv61) 2.光之保護(lv71)。四筆全部有硬條件。
    ("Anger", "Holy_Avanger_Skill6.png", "聖裁者", "61", "神的反擊", "I0144", "聖靈判官",
     "巴哈 NPC 表：聖靈判官 被動 神的反擊 lv61 == wiki Anger 被動 lv61；書 desc「攻擊力上升」"
     "對上 f.傷害 5%→；同 lv61 被動的 Spiritual Art 是「對不死傷害提升」且 f.條件（攻擊）+需鎚/手杖，"
     "與搭檔書 I0149 光的保護(=Holy Shield, f.條件（防禦）+武器「無」)不同族，故取 Anger"),
    ("Holy Shield", "Holy_Avanger_Skill7.png", "聖裁者", "71", "光的保護", "I0149", "聖靈判官",
     "巴哈 NPC 表：聖靈判官 被動 光之保護 lv71 == wiki Holy Shield 被動 lv71；書 desc「提升防禦力」"
     "直接對上 f.防禦力 10%→20%；同 lv71 被動的 Exorcism 只有「對惡魔傷害提升」沒有防禦欄位"),
    ("Self-curse", "Holy_Avanger_Skill5.png", "聖裁者", "60", "勇猛的祝福", "I0244", "聖靈判官",
     "書 desc「犧牲自己的攻擊力與防禦力讓組隊隊員的攻擊力與防禦力提升」逐項對上 f：傷害 -10%、"
     "防禦力 -10%、隊伍傷害 +2%、隊伍防禦力 +3%；巴哈 NPC 表 聖靈判官 主動 勇猛的祝福 lv60 相符"),
    ("Holy Attribute", "Holy_Avanger_Skill3.png", "聖裁者", "70", "賦予神性的屬性", "I0249", "聖靈判官",
     "書 desc「對於所有組隊隊員賦予神聖屬性」vs wiki「為自身及隊伍成員附加神聖屬性」；"
     "巴哈 NPC 表 聖靈判官 主動 賦予神性的屬性 lv70，而 Holy_Avanger 唯一 lv70 主動技能就是它；"
     "與 賦予火/冰/閃電/黑暗屬性 四本同一系列（那四本書名與 wiki 名完全相同）"),

    # ===== 哲人 / Sage 三轉（6 本書，8 個技能）=====
    ("Ice Illusion", "Sage_Skill7.png", "賢者", "70", "禁止接近", "I0189", "哲人",
     "巴哈 NPC 表：哲人 主動 禁止接近 lv70；書 desc「用冰牆擋住怪物與自己之間且不會遭受損害」"
     "對上 f.迴避 100.0% / 持續 15.00 秒 / 目標自身；另一個 lv70 主動 Chain Wave 是 傷害160%、"
     "目標多體的傷害技，與「冰牆／不會遭受損害」完全不合"),

    # ===== 聖徒 / Saint 三轉（7 本書，7 個技能，其餘 6 本已對上中文技能）=====
    ("Life Aura", "Saint_Skill7.png", "聖者", "51", "生命之靈氣", "I0660", "聖徒",
     "聖徒 7 本書對 7 個技能，其中 6 本（生命之波浪/神的祝福/消滅死者/祈禱/降魔的盔甲/神的力量）"
     "已對上已中文化技能，窮舉只剩 生命之靈氣 ↔ Life Aura；巴哈 NPC 表 聖徒 主動 第5項"
     "「生命之??」lv51（原作者辨識不出字）== wiki Life Aura 需求等級 51 主動；"
     "書 desc「使自己與組隊隊員的體力提升…使週圍組隊隊員的HP恢復」對上 f.隊伍力量 +2 與 desc「加速隊伍成員 HP 回復」"),

    # ===== 四轉 · 劍士線 =====
    ("Bladestorm", "Dragon_Knight_Skill1.png", "龍騎士", "90", "會心之一擊", "I0798", "終極鬥士",
     "終極鬥士 2 本書對 Dragon_Knight 2 個技能；I0838 影子劍術(=Continuous Blow)決定後窮舉剩此筆；"
     "書名「會心之一擊」對上 f.爆擊 30.0%→50.0%（Bladestorm 是 Dragon_Knight 唯一帶爆擊欄位的技能）"),
    ("Continuous Blow", "Dragon_Knight_Skill2.png", "龍騎士", "91", "影子劍術", "I0838", "終極鬥士",
     "書 desc「跟影子一樣有快速劍攻擊的能力」對上 f.攻擊速度 -120 / 需要道具「短劍、長劍、雙劍」/ 條件 攻擊 5.0%"),
    ("Multistrike", "Slayer_Skill1.png", "殺戮者", "90", "周圍打擊", "I0803", "聖堂武士",
     "書 desc「一般武器攻擊變成周圍攻擊, 但是攻擊力變弱」逐項對上 f.傷害 -10% / 目標自身 / 持續 8.00 秒，"
     "與 wiki「使用通常只能攻擊單一怪物的武器時，可以同時攻擊一群怪物」同義"),
    ("Divine Life", "Slayer_Skill2.png", "殺戮者", "91", "生命保護膜", "I0843", "聖堂武士",
     "書 desc「體力未滿10%時集中精神,改為消耗MP來代替體力」vs wiki「若 HP 低於 10%…有機率用 MP 保護自身」"
     "—— 10% 這個數字兩邊一致，決定性"),

    # ===== 四轉 · 弓箭手線 =====
    ("Soul Shot", "Imperial_Shooter_Skill1.png", "帝國射手", "90", "必殺一擊", "I0808", "皇家射手",
     "書 I0812（第 V 階）desc「被箭射中的一般怪物會反覆受到30%的傷害,Boss怪物則為3%」"
     "vs wiki「對敵人造成三次各 30% HP 傷害（對 BOSS 為 3%）」—— 30%/3% 兩個數字同時吻合，決定性"),
    ("Rejuvenation", "Imperial_Shooter_Skill2.png", "帝國射手", "91", "靈的保護", "I0848", "皇家射手",
     "書 desc「提高HP與MP的自動回復率,得到延長生命的能力」vs wiki「提升 HP 及 MP 的回復速率」，"
     "f.MP 回復率提升 20.0%→；皇家射手另一本 必殺一擊 已定，窮舉相符"),
    ("Chain Shot", "Trickster_Skill1.png", "詭術師", "90", "一彈爆炸", "I0813", "鎗神",
     "鎗神 2 本書對 Trickster 2 個技能；I0853 超速度槍(=Rapid Fire, 被動)決定後，"
     "唯一剩下的主動技能就是 Chain Shot（f.目標多體、可用武器「十字弓、銃」，與書 desc"
     "「一發射擊,對被擊中的怪物及其周圍怪物造成巨大傷害」的範圍攻擊相符）"),
    ("Rapid Fire", "Trickster_Skill2.png", "詭術師", "91", "超速度槍", "I0853", "鎗神",
     "書 desc「持槍時攻擊速度變快」逐項對上 f：技能類型 被動 / 可用武器「銃」/ 條件 攻擊 2.0%，"
     "wiki desc「使用手槍攻擊敵人時有機率加快攻擊速度」"),

    # ===== 四轉 · 魔法師線 =====
    ("Inferno", "Sorcerer_Skill1.png", "咒術師", "90", "百萬噸級火焰", "I0818", "賢者",
     "書 I~V desc 寫明「以自身攻擊力300%/320%/340%/360%/380%的威力」，"
     "wiki Inferno I~V 的 f.傷害 = 300%/320%/340%/360%/380% —— 五階數值完全相同，決定性"),
    ("Soul Meditation", "Sorcerer_Skill2.png", "咒術師", "91", "精神集中", "I0858", "賢者",
     "書 desc「集中精神,使用技能所消耗的MP量減少」vs wiki「使用技能時減少 MP 消耗」，同為 被動"),
    ("Hellfire", "Oracle_Skill1.png", "神諭者", "90", "強打昏迷", "I0823", "冥術師",
     "書 desc「以強力的一擊對1隻怪物造成巨大傷害,並使其失去意識」逐項對上 f：目標單體 / 傷害 400% / "
     "暈眩機率 50.0%（Oracle 另一技 Elements Mastery 是被動無傷害）"),
    ("Elements Mastery", "Oracle_Skill2.png", "神諭者", "91", "屬性強化", "I0863", "冥術師",
     "書 desc「與5級的閃電屬性賦予和黑暗屬性賦予技能一起使用時,提升攻擊力」vs wiki"
     "「隊伍成員的攻擊同時具有雷和闇屬性時提升攻擊力」—— 閃電+黑暗 兩個屬性同時點名，決定性"),

    # ===== 四轉 · 聖職者線 =====
    ("Cruno's Blessing", "Cardinal_Skill1.png", "樞機主教", "90", "經驗者的幫助", "I0828", "先知",
     "書 desc「使自己與隊員狩獵怪物獲得的獎勵經驗值增加」對上 f.自身經驗加成 2% / 隊伍經驗加成 1%"
     "（全 154 個技能只有這一個帶經驗加成欄位），決定性"),
    ("Holy Protection", "Cardinal_Skill2.png", "樞機主教", "91", "無敵", "I0868", "先知",
     "先知另一本 經驗者的幫助 已定，窮舉剩此筆；書 desc「一定時間內減少從敵人受到的傷害」"
     "對上 f.技能類型 被動 / 條件 防禦 5.0%，wiki「技能啟動時降低對手的攻擊力」同為減傷"),
    ("Moon's Blessing", "Arc_Bishop_Skill1.png", "大主教", "90", "漩渦", "I0833", "教皇",
     "書 desc「使用漩渦, 給附近的怪物致命傷和昏迷」逐項對上 f：目標多體 / 傷害 400% / 暈眩機率 12.0%，"
     "wiki「對周圍對手造成致命傷害，使其無法移動」"),
    ("Resistance Aura", "Arc_Bishop_Skill2.png", "大主教", "91", "耐受性強化", "I0873", "教皇",
     "教皇另一本 漩渦 已定，窮舉剩此筆；書 desc「使怪物耐性變得更強.(目前怪物耐性為0%的情況除外)」"
     "對上 wiki「大量擊殺敵人時提升獲得的屬性加成數量」—— 講的是同一套怪物屬性耐性成長機制，"
     "且 Resistance 與「耐受性」字面亦相符"),
]

# 資料本身的錯字：這一階的 levels[*].name 拼錯了（Meditationo），
# 一般規則（完全相符 or 以「英文名 + 空白」開頭）接不到，這裡明列例外。
LEVEL_NAME_FIX = {
    ("Soul Meditation", "Soul Meditationo IV"): "IV",
}

# 保持英文、不動的 25 筆（沒有技能書、也沒有巴哈資料可佐證）：
#   Gladiator 二轉 6：Fatal Blow / Swift Strike / Backstab / Chance Attack /
#                     Synchronization / Shield Training
#   Hunter   二轉 6：Set Trap / Double Shot / Blessed Shot / Dark Arrow /
#                     Precision / Gun Training
#   Wizard   二轉 7：Electric Charge / Drain / Mana Restoration / Magic Missile /
#                     Evocation / Freezing Energy / Magic Power
#   Priest   二轉 1：Revitalize
#     → 技能書只發行三轉與四轉技能（二轉四職 Gladiator/Hunter/Wizard/Priest
#       一本都沒有），巴哈 NPC 表也只收三轉，所以這 20 筆無據可考。
#   Holy_Avanger 3：Holy Revenge(lv60 主動) / Spiritual Art(lv61 被動) /
#                    Exorcism(lv71 被動)
#     → 聖靈判官只有 4 本書，已全部用掉。
#   Sage 2：Chain Wave / Truth of Soul
#     → 哲人 6 本書全部用掉：痲痺/賦予火屬性/賦予冰屬性/防禦的祝福 已對上，
#       禁止接近 → Ice Illusion，剩下的「神力搾取」按巴哈 NPC 表窮舉是哲人
#       被動 lv61「魔力之剝削」，也就是 wiki 已經叫「強力之剝削」的那筆
#       （Sage_Skill4，f.回復 MP 60/效果發動率 5.0%/等級 61），不是 Truth of Soul。
#       Truth of Soul(lv71 被動) 與 強力之剝削 兩者 desc、回復 MP 數值幾乎相同，
#       在沒有第三個訊號可切開之前，寧可保持英文。
UNRESOLVED_NOTE = "25 筆保持英文（二轉 20 + 聖靈判官 3 + 哲人 2）"

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
         "VIII": 8, "IX": 9, "X": 10,
         "Ⅰ": 1, "Ⅱ": 2, "Ⅲ": 3, "Ⅳ": 4, "Ⅴ": 5, "Ⅵ": 6, "Ⅶ": 7,
         "Ⅷ": 8, "Ⅸ": 9, "Ⅹ": 10}
RE_LV = re.compile(r"^(.*?)\s*([IVXⅠ-Ⅹ]+)$")
RE_JOB = re.compile(r"^(.+?)\s*\d+\s*(?:級|等級)")


def split_book_level(name):
    """「鐵壁 III」-> ("鐵壁", 3)；「隱身術」-> ("隱身術", None)"""
    m = RE_LV.match(name)
    if m and m.group(1) and m.group(2) in ROMAN:
        return m.group(1).strip(), ROMAN[m.group(2)]
    return name.strip(), None


def load_skill_books(path):
    """回傳 {技能書基本名: {"ids": [...], "jobs": set(), "descs": [...]}}"""
    with open(path, "r", encoding="utf-8") as fh:
        items = json.load(fh)
    books = {}
    for it in items:
        if it.get("itemType") != "SKILL_BOOK":
            continue
        base, _ = split_book_level(it["name"])
        b = books.setdefault(base, {"ids": [], "jobs": set(), "descs": []})
        b["ids"].append(it["id"])
        b["descs"].append(it.get("desc", ""))
        for p in it.get("pandora", []):
            m = RE_JOB.match(p.get("name", ""))
            if m:
                b["jobs"].add(m.group(1).strip())
    for b in books.values():
        b["ids"].sort()
    return books


def _field(f, *keys):
    for k in keys:
        v = f.get(k)
        if v:
            return v
    return ""


def main():
    with open(WIKI_JSON_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    books = load_skill_books(ITEMS_JSON_PATH)

    skills = data["skills"]
    orig_skill_count = len(skills)
    orig_level_counts = [len(s["levels"]) for s in skills]

    # ---- 對照表自身健檢：英文名、中文名都不可重複，中文名不可撞已有技能 ----
    en_names = [m[0] for m in MAPPING]
    cn_names = [m[4] for m in MAPPING]
    by_en_names = set(en_names)
    assert len(set(en_names)) == len(en_names), "MAPPING 有重複的英文名！"
    assert len(set(cn_names)) == len(cn_names), "MAPPING 有重複的中文名！"
    # 只比對「不歸本檔管」的技能（已跑過一次時，這些技能的 en 已經是英文原名，
    # name 已是新中文名，要排除掉才不會誤判撞名）。
    others_cn = {s["name"] for s in skills if (s.get("en") or s["name"]) not in by_en_names}
    dup = set(cn_names) & others_cn
    assert not dup, f"中文名與現有技能撞名：{dup}"

    by_en = {m[0]: m for m in MAPPING}
    renamed, skipped_already, mismatched = [], [], []

    for s in skills:
        lookup = s.get("en") or s["name"]
        m = by_en.get(lookup)
        if not m:
            continue
        en_name, img, exp_job, exp_lvl, cn_name, book_id, book_job, _evidence = m

        if s.get("en") == en_name and s["name"] == cn_name:
            skipped_already.append(en_name)
            continue

        # ---- 套用前二次驗證：wiki 端 ----
        f0 = s["levels"][0].get("f", {})
        act_job = _field(f0, "職業", "需求職業")
        act_lvl = _field(f0, "等級", "需求等級")
        problems = []
        if s.get("img") != img:
            problems.append(f"img {s.get('img')}≠{img}")
        if act_job != exp_job:
            problems.append(f"職業 {act_job}≠{exp_job}")
        if act_lvl != exp_lvl:
            problems.append(f"等級 {act_lvl}≠{exp_lvl}")

        # ---- 套用前二次驗證：技能書端 ----
        bk = books.get(cn_name)
        if bk is None:
            problems.append(f"items.json 找不到技能書「{cn_name}」")
        else:
            if book_id not in bk["ids"]:
                problems.append(f"技能書 id {book_id} 不在 {bk['ids']}")
            if book_job and book_job not in bk["jobs"]:
                problems.append(f"技能書職業 {sorted(bk['jobs'])} 不含 {book_job}")
            if book_job and JOB_MAP.get(book_job) != img.split("_Skill")[0]:
                problems.append(f"職業對照 {book_job}→{JOB_MAP.get(book_job)} 對不上 {img}")

        if problems:
            mismatched.append((en_name, "；".join(problems)))
            continue

        s["en"] = en_name
        s["name"] = cn_name
        for lv in s["levels"]:
            old = lv["name"]
            fix = LEVEL_NAME_FIX.get((en_name, old))
            if fix:
                lv["name"] = cn_name + " " + fix
            elif old == en_name:
                lv["name"] = cn_name
            elif old.startswith(en_name + " "):
                lv["name"] = cn_name + old[len(en_name):]
            # 其餘（資料誤植成別的技能名）保持原樣，不亂改。
        renamed.append(en_name)

    # ---- 安全檢查 ----
    assert len(skills) == orig_skill_count, "skills 筆數變了！"
    assert [len(s["levels"]) for s in skills] == orig_level_counts, "有技能的 levels 筆數變了！"
    assert orig_skill_count == 154, f"技能總數應為 154，實際 {orig_skill_count}"

    with open(WIKI_JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))

    still_en = [s["name"] for s in skills
                if not any("一" <= c <= "鿿" for c in s["name"])]
    print(f"技能總數：{orig_skill_count}（不變）")
    print(f"本次改名：{len(renamed)} 個")
    print(f"已改過、本次跳過：{len(skipped_already)} 個")
    print(f"仍為英文：{len(still_en)} 個 —— {UNRESOLVED_NOTE}")
    if mismatched:
        print(f"警告：{len(mismatched)} 筆驗證不通過，已跳過未套用：", file=sys.stderr)
        for name, why in mismatched:
            print(f"  - {name}: {why}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
