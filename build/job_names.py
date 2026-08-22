#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把站上的職業名稱統一成「遊戲內實際名稱」。

用法：
    python3 build/job_names.py

行為：
    - 只讀 docs/data/items.json（不寫）當佐證來源。
    - 就地改寫 docs/data/wiki.json、docs/data/character.json、docs/data/social.json
      裡「確定是職業欄位」的值。不會動 docs/app.js、docs/style.css、
      docs/data/items.json、docs/data/equips.json，也不動任何道具／怪物／地圖名稱。
    - 可重複執行；跑兩次三個 JSON 的 md5 都相同。
    - 改動前後 assert：技能仍 154 筆、每筆 levels 筆數不變、
      levels[].f 裡「職業欄位以外」的鍵值完全沒動。

──────────────────────────────────────────────────────────────────────────
一、為什麼「遊戲內名稱」是這一套
──────────────────────────────────────────────────────────────────────────
docs/data/items.json 的技能書品項名把職業寫死在字面上，而且剛好切成兩組、
零重疊（本檔啟動時會重算一次驗證）：

  三轉 16 職，品項寫「XX N級 技術」：
    騎士 鐵甲武士 將軍 英雄 遊俠 狙擊手 神射手 神槍手
    法櫃巫師 黃教巫師 咒術師 哲人 聖徒 聖騎士 主教 聖靈判官
  四轉 8 職，品項寫「XX N等級 技能書」：
    終極鬥士 聖堂武士 皇家射手 鎗神 賢者 冥術師 先知 教皇

這 24 個名字是遊戲自己的文字，站上原本用的是另一套（wiki 翻譯）命名。

──────────────────────────────────────────────────────────────────────────
二、對位鍵：img 前綴，不是舊職業名
──────────────────────────────────────────────────────────────────────────
wiki.json 每個技能的 img 是遊戲原始素材檔名（Sage_Skill1.png），前綴就是該技能
所屬職業的英文代號。全站 33 個前綴對「該技能的職業欄位」是嚴格一對一。

絕對不可以用舊名字當鍵做字串取代，理由有二：
  (1)「賢者」在兩套系統裡是不同職業：站上的賢者＝三轉 Sage（遊戲內叫哲人），
     遊戲內的賢者＝四轉 Sorcerer（站上叫咒術師）。「咒術師」同理互撞。
     用名字當鍵一定會串在一起。
  (2)「賢者法衣」「賢者長褲」「賢者之帽」「朝聖者祭服」「聖者祭司服」
     「死靈咒術師」「賢者之平原」都是裝備／道具／怪物／地圖名稱，
     全域取代會毀掉上百筆資料。

所以本檔一律以 img 前綴（或等價的、逐列驗證過的定位資訊）當鍵，
一次把職業欄位改寫成新名稱，不做「舊名→新名」的字串映射。

──────────────────────────────────────────────────────────────────────────
三、前綴 → 遊戲內職業名 的證據
──────────────────────────────────────────────────────────────────────────
啟動時會用 items.json 重新推導一次：把每本技能書的基本名（去掉羅馬階級）對到
同名的 wiki 技能，該技能的 img 前綴就投給該書 pandora 上的職業。只採計
「pandora 只掛一個職業」的書（遁避訓練同時掛狙擊手與遊俠，跳過）。結果：

  Arc_Bishop→教皇 Arc_Mage→法櫃巫師 Bishop→主教 Cardinal→先知
  Dragon_Knight→終極鬥士 General→將軍 Heroes→英雄 Holy_Avanger→聖靈判官
  Imperial_Shooter→皇家射手 Knight→騎士 Oracle→冥術師 Ranger→遊俠
  Sage→哲人 Saint→聖徒 Shaman→黃教巫師 Sharpshooter→神射手
  Slayer→聖堂武士 Sniper→狙擊手 Sorcerer→賢者 Specialist→神槍手
  Sword_Master→鐵甲武士 Trickster→鎗神 Warlock→咒術師

23 個前綴各自唯一命中，沒有一對多。剩下的第 24 個三轉職 Paladin 沒有
「書名 == 已中文化技能名」的配對（書名都差在「的／之」），但三轉 16 個前綴
只剩 Paladin、16 個遊戲內三轉職名只剩「聖騎士」，窮舉唯一 → Paladin→聖騎士。
（本檔會 assert 這個窮舉條件成立。）

基礎職 4 個（Fighter 劍士、Archer 弓箭手、Mage 魔法師、Cleric 聖職者）與
二轉職 4 個（Gladiator 鬥士、Hunter 獵人、Wizard 巫師、Priest 祭司）
沒有技能書，遊戲內文字查不到，維持站上現名不動（詳見檔尾 NO_EVIDENCE）。

──────────────────────────────────────────────────────────────────────────
四、jobTree 的處理
──────────────────────────────────────────────────────────────────────────
jobTree 原本那 20 個名字是「另一套命名」，來自 Fandom 的轉職樹頁，經
build/wiki_i18n.py 的 TERM 翻成中文（Berserker 狂戰士、Templar 聖殿武士、
Warlord 統帥、Conqueror 征服者、Crusader 十字軍、Predator 掠奪者、Gunner 槍手、
Beast Master 馴獸師、Destroyer 毀滅者、Archmage 大魔導士、Necromancer 死靈法師、
Magister 魔導師、Lich 巫妖…）。這些名字在技能資料裡一個都不存在，
所以「按名字對位」是不可能的，只能按「哪一條線的第幾階」對位。

階層由技能的需求等級推出來（本檔啟動時重算）：
    第0階 lv3-19、第1階 lv20-39、第2階 lv40-59、第3階 lv60-79、第4階 lv90+
每條線每階的職業集合因此完全確定，與 jobTree 原本的 5 列一一對上。

同一列裡「左／右」哪一支是哪一職，靠兩份互相獨立的資料定出來：
  (a) docs/data/character.json 的能量條表（表頭就叫「職業需求」），
      四條能量條剛好是第1~4階，每列寫「A / B」：
        紫: 騎士/劍聖   狙擊手/遊俠   大魔導/薩滿    聖者/聖騎士
        黑: 將軍/英雄   神射手/專家   賢者/惡魔法師  聖裁者/主教
        橘: 龍騎士/殺戮者 帝國射手/詭術師 咒術師/神諭者 樞機主教/大主教
      直行讀下來就是六條轉職鏈。
  (b) build/social.py 的 KEEP_JOB（抄自 Fandom 的職業鏈寫法）：
        Knight/General/Dragon Knight     Sword Master/Heroes/Slayer
        Sniper/Sharpshooter/Imperial Shooter   Ranger/Specialist/Trickster
        Arc Mage/Sage/Sorcerer           Shaman/Warlock/Oracle
        Saint/Holy Avanger/Cardinal      Paladin/Bishop/Arc Bishop
  兩份完全吻合，CHAINS 就照這八條鏈寫。

左右順序：jobTree 本來對得上名字的兩列（聖職者第2階「聖者 / 聖騎士」、
弓箭手第2階「遊俠 / 狙擊手」）保留原本的左右；劍士線與魔法師線原本的名字
無法對位，沒有「原順序」可保留，改用 character.json 能量條表的直行順序。
分支結構（每列幾支、哪兩個同階）完全不動。

一個必須修正的例外：jobTree 劍士線第1階原本寫「騎士」（Fandom 那套把 Knight
當二轉），但技能資料裡 Knight/騎士 是三轉（lv40-59），劍士線的二轉是
Gladiator/鬥士（lv20-39）。不改的話「騎士」會同時出現在第1階與第2階。
本檔改成「鬥士」——這是站上技能資料自己的既有名稱，不是新造的字。

──────────────────────────────────────────────────────────────────────────
五、動到的欄位（每一處都先證明是職業欄位）
──────────────────────────────────────────────────────────────────────────
docs/data/wiki.json
  · skills[].levels[].f.需求職業 / f.職業  —— 欄位名就是職業，值全部是職業名，
    且與該技能 img 前綴嚴格一對一。
  · jobTree.<四條線>[]  —— 前端以「職業進階」標題呈現（docs/app.js:1172）。
  （skills[].job 與 badges[].jobs[] 只放四個基礎職，不需要改，但仍會驗證。）

docs/data/character.json
  · gauge.bars[].table 的「職業需求」欄 —— 表頭就是職業需求；每格拆開後
    每個成分都恰好是職業名；四條能量條對應第1~4階。逐格用
    (線, 階) 候選集合解出唯一指派才改，解不出唯一解就跳過。
  · statusSources.skills[].table 的「職業」欄 —— 表頭就是職業，而且每一列
    自帶 img（Hunter_Skill1.png…），與 wiki.json 同一把鍵。

docs/data/social.json
  · party.tables[] 中表頭含「職業」的兩張表 —— 值本來是英文職業名
    （Shaman、Sage、Warlock…，build/social.py 當初刻意保留原文）。
    逐列再用「技能名稱」欄回查 wiki.json 拿到 img 前綴驗證，對不上就跳過。

刻意不動（有查過但證明不是職業欄位）：
  · docs/data/items.json / equips.json —— 命令禁止改；且 D0810「狙擊手」之類
    是裝備品名不是職業欄位。
  · docs/data/npcs.json 的 traits「職業」（莎拉嘉德=祭司、路易=大主教）——
    這是 NPC 的身分描述，同欄其他值是「流浪商人／船長／藥材商」，
    而且 npcs.json 本來就是遊戲文字，不是站上翻譯。
  · docs/data/major-skill.json 的「專家可以製作…炸彈」—— 生活技能敘述，
    原文是印尼文 "Spesialis"（泛稱），且 character.json 明載該技能職業＝「無」。
  · docs/data/notes.json 的 topics ['狙擊手','遊俠'] —— 是玩家筆記標籤，
    而且這兩個名字在新舊命名中相同，無事可做。
  · dungeons/grind/maps/quests/monsters/recipes/index.json 的命中全部是
    怪物名（死靈咒術師）、地圖名（賢者之平原）、道具名（朝聖者祭服）。
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "build"))

WIKI = os.path.join(ROOT, "docs", "data", "wiki.json")
ITEMS = os.path.join(ROOT, "docs", "data", "items.json")
CHARACTER = os.path.join(ROOT, "docs", "data", "character.json")
SOCIAL = os.path.join(ROOT, "docs", "data", "social.json")

# ---------------------------------------------------------------------------
# 前綴 -> (站上現名, 遊戲內實際名)
# 三轉／四轉那 24 筆由 items.json 推導並在 verify_prefix_jobs() 重算驗證；
# 基礎職與二轉職沒有遊戲內佐證，兩欄相同（維持現名）。
# ---------------------------------------------------------------------------
PREFIX_JOB = {
    # 基礎職（無佐證，維持現名）
    "Fighter": ("劍士", "劍士"),
    "Archer": ("弓箭手", "弓箭手"),
    "Mage": ("魔法師", "魔法師"),
    "Cleric": ("聖職者", "聖職者"),
    # 二轉（無佐證，維持現名）
    "Gladiator": ("鬥士", "鬥士"),
    "Hunter": ("獵人", "獵人"),
    "Wizard": ("巫師", "巫師"),
    "Priest": ("祭司", "祭司"),
    # 三轉
    "Knight": ("騎士", "騎士"),
    "Sword_Master": ("劍聖", "鐵甲武士"),
    "General": ("將軍", "將軍"),
    "Heroes": ("英雄", "英雄"),
    "Ranger": ("遊俠", "遊俠"),
    "Sniper": ("狙擊手", "狙擊手"),
    "Sharpshooter": ("神射手", "神射手"),
    "Specialist": ("專家", "神槍手"),
    "Arc_Mage": ("大魔導", "法櫃巫師"),
    "Shaman": ("薩滿", "黃教巫師"),
    "Sage": ("賢者", "哲人"),
    "Warlock": ("惡魔法師", "咒術師"),
    "Saint": ("聖者", "聖徒"),
    "Paladin": ("聖騎士", "聖騎士"),
    "Holy_Avanger": ("聖裁者", "聖靈判官"),
    "Bishop": ("主教", "主教"),
    # 四轉
    "Dragon_Knight": ("龍騎士", "終極鬥士"),
    "Slayer": ("殺戮者", "聖堂武士"),
    "Imperial_Shooter": ("帝國射手", "皇家射手"),
    "Trickster": ("詭術師", "鎗神"),
    "Sorcerer": ("咒術師", "賢者"),
    "Oracle": ("神諭者", "冥術師"),
    "Cardinal": ("樞機主教", "先知"),
    "Arc_Bishop": ("大主教", "教皇"),
    # 活動技能（沒有職業）
    "Event": ("無", "無"),
}

# 沒有遊戲內佐證、維持現名的前綴（回報用）
NO_EVIDENCE = ["Fighter", "Archer", "Mage", "Cleric",
               "Gladiator", "Hunter", "Wizard", "Priest"]

# 名稱在新舊兩套裡相同的職業（複合值「狙擊手、遊俠」要用到）
UNCHANGED_NAMES = {g for s, g in PREFIX_JOB.values() if s == g}

# jobTree：四條線的 base / 二轉 / 兩條分支鏈（分支鏈 = 第2、3、4 階）
CHAINS = {
    "劍士": {
        "base": "Fighter", "second": "Gladiator",
        "left": ["Knight", "General", "Dragon_Knight"],
        "right": ["Sword_Master", "Heroes", "Slayer"],
    },
    "弓箭手": {
        "base": "Archer", "second": "Hunter",
        "left": ["Ranger", "Specialist", "Trickster"],
        "right": ["Sniper", "Sharpshooter", "Imperial_Shooter"],
    },
    "魔法師": {
        "base": "Mage", "second": "Wizard",
        "left": ["Arc_Mage", "Sage", "Sorcerer"],
        "right": ["Shaman", "Warlock", "Oracle"],
    },
    "聖職者": {
        "base": "Cleric", "second": "Priest",
        "left": ["Saint", "Holy_Avanger", "Cardinal"],
        "right": ["Paladin", "Bishop", "Arc_Bishop"],
    },
}

JOB_KEYS = ("職業", "需求職業")
ROMAN = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"}
RE_LV = re.compile(r"^(.*?)\s*([IVX]+)$")
RE_BOOK_JOB = re.compile(r"^(.+?)\s*\d+\s*(?:級|等級)\s*(?:技術|技能書)$")
RE_PAREN = re.compile(r"^(.*?)（(.*)）$")


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save(path, data, sort_keys=False):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"),
                  sort_keys=sort_keys)


def md5(path):
    with open(path, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()


def prefix_of(img):
    return (img or "").split("_Skill")[0]


# ---------------------------------------------------------------------------
# 驗證 ①：items.json 的技能書職業本來就切成 16 三轉 + 8 四轉、零重疊
# ---------------------------------------------------------------------------
def verify_book_jobs(items):
    third, fourth = set(), set()
    n = 0
    for it in items:
        if it.get("itemType") != "SKILL_BOOK":
            continue
        n += 1
        for p in it.get("pandora", []):
            name = (p.get("name") or "").strip()
            m = RE_BOOK_JOB.match(name)
            if not m:
                continue
            (third if name.endswith("技術") else fourth).add(m.group(1).strip())
    assert n == 540, f"技能書應為 540 本，實際 {n}"
    assert len(third) == 16, f"三轉職應為 16 個，實際 {sorted(third)}"
    assert len(fourth) == 8, f"四轉職應為 8 個，實際 {sorted(fourth)}"
    assert not (third & fourth), f"三轉與四轉職名重疊：{third & fourth}"
    return third, fourth


# ---------------------------------------------------------------------------
# 驗證 ②：用 items.json 重新推導 前綴 -> 遊戲內職業名，比對 PREFIX_JOB
# ---------------------------------------------------------------------------
def verify_prefix_jobs(items, skills, third, fourth):
    book_job = {}          # 技能書基本名 -> 職業（只收 pandora 單一職業的書）
    multi = set()
    for it in items:
        if it.get("itemType") != "SKILL_BOOK":
            continue
        m = RE_LV.match(it["name"])
        base = m.group(1).strip() if (m and m.group(2) in ROMAN) else it["name"].strip()
        jobs = set()
        for p in it.get("pandora", []):
            mm = RE_BOOK_JOB.match((p.get("name") or "").strip())
            if mm:
                jobs.add(mm.group(1).strip())
        if len(jobs) == 1:
            j = jobs.pop()
            if book_job.setdefault(base, j) != j:
                multi.add(base)
        elif len(jobs) > 1:
            multi.add(base)
    for b in multi:
        book_job.pop(b, None)

    derived = {}
    for s in skills:
        j = book_job.get(s["name"])
        if not j:
            continue
        pre = prefix_of(s["img"])
        derived.setdefault(pre, set()).add(j)

    bad = [(p, v) for p, v in derived.items() if len(v) > 1]
    assert not bad, f"前綴對到多個遊戲內職業：{bad}"
    derived = {p: v.pop() for p, v in derived.items()}
    assert len(set(derived.values())) == len(derived), "不同前綴對到同一個職業名"

    for pre, job in sorted(derived.items()):
        want = PREFIX_JOB[pre][1]
        assert want == job, f"{pre} 推導為「{job}」，PREFIX_JOB 卻寫「{want}」"

    # 沒有直接佐證的三轉前綴，必須靠窮舉唯一決定
    third_pre = {p for p in PREFIX_JOB
                 if PREFIX_JOB[p][1] in third}
    left_pre = sorted(third_pre - set(derived))
    left_job = sorted(third - set(derived.values()))
    assert len(left_pre) == len(left_job) == 1, \
        f"三轉窮舉不唯一：前綴 {left_pre} / 職業 {left_job}"
    assert PREFIX_JOB[left_pre[0]][1] == left_job[0], \
        f"窮舉結果 {left_pre[0]}→{left_job[0]} 與 PREFIX_JOB 不符"

    # 四轉 8 個必須全部有直接佐證
    fourth_pre = {p for p in PREFIX_JOB if PREFIX_JOB[p][1] in fourth}
    assert fourth_pre <= set(derived), \
        f"四轉缺佐證：{sorted(fourth_pre - set(derived))}"
    return derived, left_pre[0]


# ---------------------------------------------------------------------------
# 驗證 ③：build/skill_book_names.py 既有的 JOB_MAP（遊戲內職業名 -> 前綴）
# ---------------------------------------------------------------------------
def verify_job_map():
    try:
        from skill_book_names import JOB_MAP
    except Exception as exc:                      # pragma: no cover
        print(f"警告：讀不到 skill_book_names.JOB_MAP（{exc}），略過比對",
              file=sys.stderr)
        return None
    ours = {g: p for p, (s, g) in PREFIX_JOB.items() if p not in NO_EVIDENCE
            and p != "Event"}
    assert JOB_MAP == ours, (
        "JOB_MAP 與本檔的前綴表不一致：\n"
        f"  只在 JOB_MAP：{sorted(set(JOB_MAP.items()) - set(ours.items()))}\n"
        f"  只在本檔    ：{sorted(set(ours.items()) - set(JOB_MAP.items()))}")
    return len(JOB_MAP)


# ---------------------------------------------------------------------------
# 由技能需求等級推出 (線, 階) -> 前綴集合
# ---------------------------------------------------------------------------
BANDS = [(3, 19, 0), (20, 39, 1), (40, 59, 2), (60, 79, 3), (90, 200, 4)]


def build_tiers(skills):
    lv, line = {}, {}
    for s in skills:
        pre = prefix_of(s["img"])
        line.setdefault(pre, set()).add(s.get("job", ""))
        for l in s["levels"]:
            f = l.get("f", {})
            v = f.get("等級") or f.get("需求等級")
            if v and v.isdigit():
                lv.setdefault(pre, set()).add(int(v))
    tiers = {}
    for pre, levels in lv.items():
        if pre == "Event":
            continue
        got = {t for a, b, t in BANDS
               for x in levels if a <= x <= b}
        assert len(got) == 1, f"{pre} 的等級跨階：{sorted(levels)}"
        assert len(line[pre]) == 1, f"{pre} 對到多條線：{line[pre]}"
        tiers.setdefault((line[pre].pop(), got.pop()), set()).add(pre)
    return tiers


# ---------------------------------------------------------------------------
# 改寫：職業欄位（單一值或「A、B」複合值），以 img 前綴為鍵
# ---------------------------------------------------------------------------
def rewrite_by_prefix(value, prefix, where):
    site, game = PREFIX_JOB[prefix]
    parts = [p.strip() for p in value.split("、")]
    out, hit = [], False
    for p in parts:
        if p in (site, game):
            out.append(game)
            hit = True
        elif p in UNCHANGED_NAMES:
            out.append(p)          # 複合值裡別的職業，且新舊同名
        else:
            raise ValueError(f"{where}：值「{value}」的成分「{p}」"
                             f"不屬於 {prefix}（{site}/{game}），且不是新舊同名的職業")
    if not hit:
        raise ValueError(f"{where}：值「{value}」裡找不到 {prefix} 的職業名")
    return "、".join(out)


# ---------------------------------------------------------------------------
# 改寫：character.json 能量條表（沒有 img，用 (線, 階) 候選集合解唯一指派）
# ---------------------------------------------------------------------------
def solve_cell(cell, tiers):
    """把「A / B」解成唯一的 (線, 階, [前綴...])；解不出唯一解回傳 None。"""
    parts = [p.strip() for p in cell.split("/")]
    sols = []
    for (line, tier), pres in tiers.items():
        if len(pres) != len(parts):
            continue
        assign, used, ok = [], set(), True
        for p in parts:
            cand = [x for x in pres
                    if p in PREFIX_JOB[x] and x not in used]
            if len(cand) != 1:
                ok = False
                break
            assign.append(cand[0])
            used.add(cand[0])
        if ok:
            sols.append((line, tier, assign))
    return sols[0] if len(sols) == 1 else None


def main():
    items = load(ITEMS)
    wiki = load(WIKI)
    skills = wiki["skills"]

    # ---------------- 前置驗證 ----------------
    third, fourth = verify_book_jobs(items)
    derived, by_elim = verify_prefix_jobs(items, skills, third, fourth)
    jm = verify_job_map()
    tiers = build_tiers(skills)

    seen_pre = {prefix_of(s["img"]) for s in skills}
    assert seen_pre <= set(PREFIX_JOB), \
        f"有前綴不在 PREFIX_JOB：{sorted(seen_pre - set(PREFIX_JOB))}"
    assert set(PREFIX_JOB) - seen_pre == set(), \
        f"PREFIX_JOB 有多餘前綴：{sorted(set(PREFIX_JOB) - seen_pre)}"

    # 前綴 <-> 職業欄位值 必須嚴格一對一（複合值另計）
    pre_vals = {}
    for s in skills:
        pre = prefix_of(s["img"])
        for l in s["levels"]:
            for k in JOB_KEYS:
                if k in l.get("f", {}):
                    pre_vals.setdefault(pre, set()).add(l["f"][k])
    for pre, vals in pre_vals.items():
        simple = {v for v in vals if "、" not in v}
        assert simple <= set(PREFIX_JOB[pre]), \
            f"{pre} 的職業欄位出現預期外的值：{sorted(simple)}"

    # ---------------- 改動前快照 ----------------
    n_skills = len(skills)
    lv_counts = [len(s["levels"]) for s in skills]
    other_f = [[{k: v for k, v in l.get("f", {}).items() if k not in JOB_KEYS}
                for l in s["levels"]] for s in skills]
    job_key_shape = [[sorted(k for k in l.get("f", {}) if k in JOB_KEYS)
                      for l in s["levels"]] for s in skills]
    skill_meta = [(s["name"], s["img"], s.get("job", "")) for s in skills]
    old_tree = json.loads(json.dumps(wiki["jobTree"], ensure_ascii=False))

    # ---------------- wiki.json：技能職業欄位 ----------------
    n_field = 0
    for s in skills:
        pre = prefix_of(s["img"])
        for i, l in enumerate(s["levels"]):
            f = l.get("f", {})
            for k in JOB_KEYS:
                if k not in f:
                    continue
                new = rewrite_by_prefix(f[k], pre, f"{s['name']} levels[{i}].f.{k}")
                if new != f[k]:
                    n_field += 1
                f[k] = new

    # ---------------- wiki.json：jobTree ----------------
    assert set(wiki["jobTree"]) == set(CHAINS), "jobTree 的四條線變了"
    new_tree = {}
    for line, rows in wiki["jobTree"].items():
        assert len(rows) == 5, f"{line} 的 jobTree 不是 5 階"
        for i, row in enumerate(rows):
            want = 1 if i < 2 else 2
            assert len(row.split("/")) == want, \
                f"{line} 第{i}階分支數為 {len(row.split('/'))}，預期 {want}"
        c = CHAINS[line]
        out = [PREFIX_JOB[c["base"]][1], PREFIX_JOB[c["second"]][1]]
        for i in range(3):
            l_pre, r_pre = c["left"][i], c["right"][i]
            assert {l_pre, r_pre} == tiers[(line, i + 2)], (
                f"{line} 第{i + 2}階集合不符：CHAINS {sorted([l_pre, r_pre])} "
                f"vs 技能資料 {sorted(tiers[(line, i + 2)])}")
            out.append(f"{PREFIX_JOB[l_pre][1]} / {PREFIX_JOB[r_pre][1]}")
        new_tree[line] = out
    flat = [x for rows in new_tree.values() for row in rows
            for x in row.split(" / ")]
    assert len(flat) == len(set(flat)), \
        f"新 jobTree 有重複職業名：{sorted({x for x in flat if flat.count(x) > 1})}"
    n_tree = sum(1 for line in new_tree
                 for a, b in zip(old_tree[line], new_tree[line]) if a != b)
    wiki["jobTree"] = new_tree

    # 基礎職欄位順便驗一下沒被波及
    assert {s.get("job", "") for s in skills} == {"劍士", "弓箭手", "魔法師", "聖職者", ""}
    for b in wiki["badges"]:
        assert b["jobs"] == ["劍士", "弓箭手", "魔法師", "聖職者"], \
            f"badges 的 jobs 出現非基礎職：{b['jobs']}"

    # ---------------- 改動後 assert ----------------
    assert len(skills) == n_skills == 154, f"技能總數變了：{len(skills)}"
    assert [len(s["levels"]) for s in skills] == lv_counts, "levels 筆數變了"
    assert [[{k: v for k, v in l.get("f", {}).items() if k not in JOB_KEYS}
             for l in s["levels"]] for s in skills] == other_f, \
        "levels[].f 裡職業以外的值被動到了"
    assert [[sorted(k for k in l.get("f", {}) if k in JOB_KEYS)
             for l in s["levels"]] for s in skills] == job_key_shape, \
        "職業欄位的鍵被增刪了"
    assert [(s["name"], s["img"], s.get("job", "")) for s in skills] == skill_meta, \
        "技能名稱／圖示／所屬線被動到了"

    save(WIKI, wiki)

    # ---------------- character.json ----------------
    ch = load(CHARACTER)
    n_gauge = n_status = 0
    skipped = []
    for bar in ch["gauge"]["bars"]:
        t = bar.get("table")
        if not t or "職業需求" not in t["headers"]:
            continue
        ji = t["headers"].index("職業需求")
        for r in t["rows"]:
            cell = r["c"][ji]
            sol = solve_cell(cell, tiers)
            if not sol:
                skipped.append(f"gauge {bar.get('name')} 「{cell}」解不出唯一 (線,階)")
                continue
            _line, _tier, pres = sol
            new = " / ".join(PREFIX_JOB[p][1] for p in pres)
            if new != cell:
                n_gauge += 1
            r["c"][ji] = new
    for grp in ch["statusSources"]["skills"]:
        t = grp["table"]
        if "職業" not in t["headers"]:
            continue
        ji = t["headers"].index("職業")
        for r in t["rows"]:
            pre = prefix_of(r.get("img", ""))
            if pre not in PREFIX_JOB:
                if r["c"][ji] != "無":
                    skipped.append(f"statusSources 未知前綴 {pre}「{r['c'][ji]}」")
                continue
            new = rewrite_by_prefix(r["c"][ji], pre, f"statusSources {r['c'][1]}")
            if new != r["c"][ji]:
                n_status += 1
            r["c"][ji] = new
    save(CHARACTER, ch, sort_keys=True)

    # ---------------- social.json ----------------
    by_name, by_en = {}, {}
    for s in skills:
        by_name.setdefault(s["name"], []).append(s)
        if s.get("en"):
            by_en.setdefault(s["en"], []).append(s)
    eng2pre = {p.replace("_", " "): p for p in PREFIX_JOB}
    so = load(SOCIAL)
    n_social = 0
    for t in so["party"]["tables"]:
        if "職業" not in t["headers"]:
            continue
        ji = t["headers"].index("職業")
        ni = t["headers"].index("技能名稱")
        for r in t["rows"]:
            c = r["c"] if isinstance(r, dict) else r    # social.json 的列是純陣列
            cur = c[ji]
            nm = c[ni]
            m = RE_PAREN.match(nm)
            zh, en = (m.group(1), m.group(2)) if m else (nm, nm)
            pres = {prefix_of(s["img"])
                    for s in by_name.get(zh, []) + by_en.get(en, [])}
            if len(pres) != 1:
                skipped.append(f"social「{nm}」對到 {sorted(pres)}，跳過")
                continue
            pre = pres.pop()
            # 值必須是「該前綴的英文名」或已經改好的中文名，否則不動
            if eng2pre.get(cur) == pre or cur in PREFIX_JOB[pre]:
                new = PREFIX_JOB[pre][1]
            else:
                skipped.append(f"social「{nm}」職業欄「{cur}」對不上 {pre}，跳過")
                continue
            if new != cur:
                n_social += 1
            c[ji] = new
    save(SOCIAL, so)

    # ---------------- 報告 ----------------
    changed = [(p, s, g) for p, (s, g) in sorted(PREFIX_JOB.items()) if s != g]
    print(f"技能書職業：三轉 {len(third)} + 四轉 {len(fourth)}，零重疊")
    print(f"前綴推導：{len(derived)} 個直接命中 + {by_elim} 由窮舉決定"
          f"（共 {len(derived) + 1} / 24）")
    print(f"JOB_MAP 比對：{'一致（%d 筆）' % jm if jm else '略過'}")
    print(f"改名職業：{len(changed)} 個 —— "
          + "、".join(f"{s}→{g}" for _p, s, g in changed))
    print(f"wiki.json  技能職業欄位改寫 {n_field} 處、jobTree 改寫 {n_tree} 列")
    print(f"character.json  能量條「職業需求」{n_gauge} 處、"
          f"statusSources「職業」{n_status} 處")
    print(f"social.json  組隊表「職業」{n_social} 處")
    print(f"維持現名（無遊戲內佐證）：{'、'.join(PREFIX_JOB[p][0] for p in NO_EVIDENCE)}")
    print("jobTree：")
    for line in old_tree:
        for a, b in zip(old_tree[line], new_tree[line]):
            mark = "  " if a == b else "→ "
            print(f"   {mark}{line:4s} {a:22s} {'==' if a == b else '=>'} {b}")
    if skipped:
        print(f"\n跳過 {len(skipped)} 處（沒把握，未改）：", file=sys.stderr)
        for s in skipped:
            print("  -", s, file=sys.stderr)
    for p in (WIKI, CHARACTER, SOCIAL):
        print(f"md5 {os.path.relpath(p, ROOT)} {md5(p)}")


if __name__ == "__main__":
    main()
