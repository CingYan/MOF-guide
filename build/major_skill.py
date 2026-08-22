#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「Major Skill（專業技能）」頁做成結構化資料 -> docs/data/major-skill.json。

來源頁的表格是印尼文，這裡整頁翻成台灣正體中文；技能名同時保留英文原名
（en 欄位），跟 wiki.json 的技能寫法一致。

翻譯用「家族樣板 + 從原文抽數字」的做法：每個技能家族一個中文樣板，樣板裡
的每個數字都用 regex 從原文那一列抓出來，抓不到就整列不翻、保留原文並印出來
（絕不猜數字）。同一家族只有數字不同的敘述因此不會翻錯階級。

圖示：頁面上 25 張 Major_Skill_N.png 由 92 個技能共用，依「第一個用到它的技能
中文名」命名下載到 docs/img/major-skill/。
可重複執行：已存在且非空的檔案不重抓，輸出順序固定，兩次跑出來的 JSON 一樣。
"""
import json, pathlib, re, subprocess, sys, time, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "docs/data/major-skill.json"
OUT_IMG = ROOT / "docs/img/major-skill"
API = "https://master-of-fantasy.fandom.com/api.php"
PAGE = "Major Skill"

ILLEGAL = str.maketrans({"/": "／", "\\": "＼", ":": "：", "*": "＊", "?": "？",
                         '"': "＂", "<": "＜", ">": "＞", "|": "｜",
                         "%": "％", "#": "＃"})


def curl(url):
    return subprocess.run(["curl", "-sm60", url], capture_output=True, text=True).stdout


# ── 1. 取頁面原始碼 ──────────────────────────────────────────────
u = (f"{API}?action=query&format=json&prop=revisions&rvprop=content&rvslots=main"
     f"&titles={urllib.parse.quote(PAGE)}")
page = list(json.loads(curl(u))["query"]["pages"].values())[0]
text = page["revisions"][0]["slots"]["main"]["*"]
print(f"取得頁面原始碼 {len(text)} 字元")


def norm(s):
    """把換行、連續空白壓成單一空白，方便 regex 對樣板。"""
    return " ".join(s.split())


# ── 2. 解析表格 ─────────────────────────────────────────────────
# 欄位固定是 Skill Icon / Skill Name / Description / Skill Point Cost。
# 頁面目前只有一張表，但這裡照樣掃全部的 {| ... |}，多表也吃得下。
def parse_tables(src):
    tables = []
    for m in re.finditer(r"^\{\|.*?^\|\}", src, re.S | re.M):
        body = m.group(0)
        headers = [norm(re.sub(r'^\s*!\s*(scope="[^"]*"\s*\|)?', "", h))
                   for h in re.findall(r"^!.*$", body, re.M)]
        rows = []
        for chunk in re.split(r"\n\|-\s*\n", body)[1:]:
            chunk = chunk.split("\n|}")[0]
            cells = [c.strip() for c in re.split(r"\n\|(?![-}])", "\n" + chunk) if c.strip()]
            cells = [norm(re.sub(r'^style="[^"]*"\s*\|', "", c)) for c in cells]
            if cells:
                rows.append(cells)
        tables.append({"headers": headers, "rows": rows})
    return tables


tables = parse_tables(text)
rows = []
for t in tables:
    if len(t["headers"]) < 4 or "Skill Name" not in t["headers"]:
        continue
    for c in t["rows"]:
        assert len(c) == 4, f"欄數不對：{c}"
        rows.append(c)
print(f"表格 {len(tables)} 張，技能列 {len(rows)} 筆")
assert rows, "沒有解析到任何技能列"


# ── 3. 中文對照表 ───────────────────────────────────────────────
TIER_ZH = {"Basic": "基礎", "Beginner": "初級", "Intermediate": "中級",
           "Great": "高級", "Special": "特級"}

FAMILY_ZH = {
    "Circle Building": "社團建立",
    "Mercenary": "傭兵",
    "Hunters": "獵人",
    "Devil": "惡魔",
    "Soul": "靈魂",
    "Poison": "毒藥",
    "First Aid": "急救",
    "Settings": "設置",
    "Monster Transform": "怪物變身",
    "Mind Tree Transform": "心靈之樹變身",
    "Life Tree Transform": "生命之樹變身",
    "Turtle Transform": "烏龜變身",
    "Alchemy": "鍊金術",
    "Mineral": "礦石加工",
    "Weaponry": "武器製作",
    "Blunt": "鈍器製作",
    "Bow & Gun": "弓槍製作",
    "Shield": "盾牌製作",
    "Mind Focus": "精神集中",
    "Mermaid Song": "人魚之歌",
    "Ghost Illusion": "幽靈幻影",
    "Mind Expansion": "精神擴張",
}


def split_name(en):
    """把英文技能名拆成（階級, 家族）。沒有階級前綴的回 (None, 全名)。"""
    for tier in TIER_ZH:
        if en.startswith(tier + " "):
            return tier, en[len(tier) + 1:]
    return None, en


# ── 4. 敘述翻譯樣板 ─────────────────────────────────────────────
# 每個樣板 = (regex, 產生中文的 function)。regex 對不上就不翻。
QS = "可從快速欄使用。"


def T(pattern, fn):
    return re.compile(pattern), fn


DESC_BY_FAMILY = {
    "Circle Building": T(
        r"Minimal Level: (\d+)\. Hanya dapat memiliki (\d+) orang pengikut",
        lambda g, n: f"想組成一個社群就需要有組織，在 Master of Fantasy 學院裡我們稱它為"
                     f"【Circle】。想擁有頂尖的社群，就必須有一位睿智的領袖。"
                     f"最低等級：{g[0]}。最多只能擁有 {g[1]} 名成員。"),
    "Mercenary": T(
        r"Kemampuan menyerang \+(\d+)%\. Kemampuan bertahan \+(\d+)%\. Hit Rate \+(\d+)%",
        lambda g, n: f"幫助你的夥伴越多，能發揮出來的戰鬥力就越強。攻擊能力 +{g[0]}%。"
                     f"防禦能力 +{g[1]}%。命中率 +{g[2]}%。"
                     f"這些能力會隨著技能等級與成員人數一起提升。"),
    "Hunters": T(
        r"monster \[Beast\] (\d+)%\..*?monster \[Undead\] -(\d+)%",
        lambda g, n: f"掌握怪物的資料與弱點，狩獵起來就會更有效率。此技能會提升對"
                     f"【動物】系怪物的攻擊 {g[0]}%，並降低對【不死】系怪物的攻擊 -{g[1]}%。"),
    "Devil": T(
        r"\[Devil\] Monster \+(\d+)%, Serangan terhadap \[Beast\] Monster -(\d+)%",
        lambda g, n: f"研究【惡魔】系怪物的弱點之後，你就能對【惡魔】系怪物打出更高的傷害。"
                     f"對【惡魔】系怪物的攻擊 +{g[0]}%，對【動物】系怪物的攻擊 -{g[1]}%。"),
    "Soul": T(
        r"monster \[Undead\] \+(\d+)%\. Serangan terhadap monster \[Devil\] -(\d+)%",
        lambda g, n: f"學會這個技能，你就能了解【不死】系怪物的弱點。"
                     f"對【不死】系怪物的攻擊 +{g[0]}%。對【惡魔】系怪物的攻擊 -{g[1]}%。"),
    "Poison": T(
        r"Tingkat keberhasilan (\d+)%\. Akan mengurangi HP lawan (\d+)%",
        lambda g, n: f"毒藥在狩獵和戰爭時都非常好用，對怪物下毒能讓牠變得更虛弱。"
                     f"成功率 {g[0]}%。可減少對手 HP {g[1]}%。"),
    "First Aid": T(
        r"Membutuhkan (\d+) MP\. Menyembuhkan (\d+) HP\. Delay skill (\d+) detik",
        lambda g, n: f"不用聖職者幫忙，這個技能就能治療自己的傷勢。消耗 {g[0]} MP。"
                     f"回復 {g[1]} HP。技能延遲 {g[2]} 秒。{QS}"),
    "Settings": T(
        r"Damage: (\d+)\. Area of Effect: (\d+)\. MP Requirement: (\d+)\. Delay skill: (\d+) detik",
        lambda g, n: f"專家可以製作威力不算強、但在戰鬥中相當實用的炸彈。傷害：{g[0]}。"
                     f"作用範圍：{g[1]}。MP 需求：{g[2]}。技能延遲：{g[3]} 秒。{QS}"),
    "Mind Tree Transform": T(
        r"(\d+) MP per detik\..*?Durasi: (\d+) detik",
        lambda g, n: f"變成 Spirit Tree，回復周圍其他玩家的 MP。每秒 {g[0]} MP。無法移動。"
                     f"持續時間：{g[1]} 秒。{QS}"),
    "Life Tree Transform": T(
        r"(\d+) HP per detik\..*?Durasi: (\d+) detik",
        lambda g, n: f"變成 Life Tree，回復周圍其他玩家的 HP。每秒 {g[0]} HP。無法移動。"
                     f"持續時間：{g[1]} 秒。{QS}"),
    "Turtle Transform": T(
        r"Durasi: (\d+) detik",
        lambda g, n: f"變成烏龜，但不會獲得該怪物的力量。會被攻擊。可以移動。"
                     f"持續時間：{g[0]} 秒。{QS}"),
    "Alchemy": T(
        r"Mengolah bahan-bahan sampah",
        lambda g, n: "把用不到的雜項材料加工成有用的藥水或卷軸。"
                     "能做出哪些東西，取決於你的技能等級。"),
    "Mineral": T(
        r"Semua mineral yang kamu dapatkan",
        lambda g, n: "你取得的所有礦石都能用這個技能加工，而這些礦石材料在製作武器或盾牌時"
                     "非常有用。能加工哪些礦石，取決於你的技能等級。"),
    "Weaponry": T(
        r"jenis swords, dagger, spear",
        lambda g, n: "可以用這個技能製作劍、匕首、長槍類的武器。能製作的武器等級，"
                     "取決於你掌握的技能等級。快把武器收藏補齊吧。"),
    "Blunt": T(
        r"jenis Axe, Mace, Book, Staff",
        lambda g, n: "可以用這個技能製作斧、鎚、書、法杖類的武器。能製作的武器等級，"
                     "取決於你掌握的技能等級。快把武器收藏補齊吧。"),
    "Bow & Gun": T(
        r"jenis Bow, Gun dan Cross bow",
        lambda g, n: "可以用這個技能製作弓、槍、十字弓類的武器。能製作的武器等級，"
                     "取決於你掌握的技能等級。快把武器收藏補齊吧。"),
    "Shield": T(
        r"Penggunaan tameng untuk beberapa orang sangatlah penting",
        lambda g, n: "盾牌對某些人來說非常重要，學會這個技能之後，"
                     "你就能打造出合適的盾牌。"),
    "Mind Focus": T(
        r"Membutuhkan (\d+) HP\. Menyembuhkan (\d+) MP\. Delay skill (\d+) detik",
        lambda g, n: f"不用聖職者幫忙，這個技能就能回復自己的魔力。消耗 {g[0]} HP。"
                     f"回復 {g[1]} MP。技能延遲 {g[2]} 秒。{QS}"),
    "Mermaid Song": T(
        r"Jarak memanggil (\d+)",
        lambda g, n: f"奏出樂音，吸引獵物主動靠過來。呼喚的距離取決於技能等級。"
                     f"呼喚距離 {g[0]}。"),
    "Ghost Illusion": T(
        r"Durasi: (\d+) detik",
        lambda g, n: f"像畫家描繪自己的幻想那樣在空中作畫，然後消失在夢境之中。"
                     f"怪物無法攻擊你，你可以攻擊怪物。持續時間：{g[0]} 秒。{QS}"),
    "Mind Expansion": T(
        r"Jumlah buff yang dapat digunakan: (\d+)",
        lambda g, n: f"{n}會增加可以同時使用的 buff（有持續時間的技能，"
                     f"能在畫面右上角看到）數量。可使用的 buff 數量：{g[0]}。"),
}

# Monster Transform 每個階級變的東西不一樣，敘述不共用樣板，按英文全名各給一條。
DESC_BY_NAME = {
    "Basic Monster Transform": T(
        r"Durasi: (\d+) detik",
        lambda g, n: f"變成石頭來騙過敵人。看到石頭的怪物會一頭霧水然後離開你。"
                     f"無法被攻擊。無法移動。持續時間：{g[0]} 秒。{QS}"),
    "Beginner Monster Transform": T(
        r"Durasi: (\d+) detik",
        lambda g, n: f"變成 Grass 來騙過敵人。怪物不會再主動攻擊。無法被攻擊。無法攻擊。"
                     f"持續時間：{g[0]} 秒。{QS}"),
    "Intermediate Monster Transform": T(
        r"Durasi: (\d+) detik",
        lambda g, n: f"變成中階怪物，但不會獲得該怪物的力量。會被怪物攻擊。可以移動。"
                     f"持續時間：{g[0]} 秒。{QS}"),
    "Great Monster Transform": T(
        r"Durasi: (\d+) detik",
        lambda g, n: f"變成高階怪物，但不會獲得該怪物的力量。會被攻擊。可以移動。"
                     f"持續時間：{g[0]} 秒。{QS}"),
}


def translate_desc(en_name, family, zh_name, src):
    rule = DESC_BY_NAME.get(en_name) or DESC_BY_FAMILY.get(family)
    if not rule:
        return None
    pat, fn = rule
    m = pat.search(src)
    if not m:
        return None
    return fn(m.groups(), zh_name)


# ── 5. 組出技能清單 ─────────────────────────────────────────────
skills, untranslated = [], []
for icon_cell, en_name, desc_src, cost_cell in rows:
    tier_en, family_en = split_name(en_name)
    tier_zh = TIER_ZH.get(tier_en) if tier_en else None
    family_zh = FAMILY_ZH.get(family_en)
    zh_name = (tier_zh or "") + family_zh if family_zh else en_name
    if not family_zh:
        untranslated.append((en_name, "技能名沒有中文對照"))

    desc = translate_desc(en_name, family_en, zh_name, desc_src)
    if desc is None:
        desc = desc_src                       # 翻不出來就保留原文，不瞎掰
        untranslated.append((en_name, "敘述樣板對不上，保留原文"))

    assert re.fullmatch(r"\d+", cost_cell), f"{en_name} 的點數不是數字：{cost_cell!r}"

    s = {"name": zh_name, "en": en_name, "desc": desc, "cost": int(cost_cell)}
    if family_zh:
        s["group"], s["groupEn"] = family_zh, family_en
    if tier_zh:
        s["tier"], s["tierEn"] = tier_zh, tier_en
    fm = re.search(r"File:([^\]|]+)", icon_cell)
    if fm:
        s["_file"] = fm.group(1).strip().replace(" ", "_")
    skills.append(s)

print(f"技能 {len(skills)} 個")

# ── 6. 前言 ────────────────────────────────────────────────────
intro = ("專業技能（Major Skill）是由克魯諾（Cruno）教授的特殊技能，"
         "要向他支付專業技能點數（Major Skill Point）才能學。"
         "點數可以從考試（Exam）或戰爭任務與物資補給"
         "（War Task and Material Supply）取得。"
         "專業技能所有職業都能使用。"
         "你也可以用商城道具「Major Skill Reset」把角色的專業技能重置掉。")

# 前言裡那張重置道具圖，一起抓下來給前端用
RESET_FILE = "Major_Skill_Reset.png"
RESET_ZH = "專業技能重置"

# ── 7. 抓圖 ────────────────────────────────────────────────────
# 多個技能共用同一張圖時，檔名用第一個用到它的技能中文名。
first_user = {}
for s in skills:
    fn = s.get("_file")
    if fn and fn not in first_user:
        first_user[fn] = s["name"]
if RESET_FILE not in first_user:
    first_user[RESET_FILE] = RESET_ZH

files = list(first_user)
urls = {}
for i in range(0, len(files), 50):
    q = "|".join("File:" + n for n in files[i:i + 50])
    u = (f"{API}?action=query&format=json&prop=imageinfo&iiprop=url&titles="
         + urllib.parse.quote(q))
    for p in json.loads(curl(u))["query"]["pages"].values():
        info = p.get("imageinfo")
        if info:
            # API 回傳的標題會把底線換成空白，轉回去才對得上
            urls[p["title"][len("File:"):].replace(" ", "_")] = info[0]["url"]
    time.sleep(0.5)
print(f"查到圖片網址：{len(urls)} / {len(files)}")

OUT_IMG.mkdir(parents=True, exist_ok=True)
paths, got, cached, missing = {}, 0, 0, 0
for fn in files:
    url = urls.get(fn)
    if not url:
        missing += 1
        continue
    name = first_user[fn].translate(ILLEGAL) + ".png"
    dst = OUT_IMG / name
    if dst.exists() and dst.stat().st_size > 0:
        cached += 1
    else:
        subprocess.run(["curl", "-sfLm60", "-o", str(dst), url], check=False)
        if not dst.exists() or dst.stat().st_size == 0:   # 抓壞了就不給 icon 欄位
            dst.unlink(missing_ok=True)
            missing += 1
            continue
        got += 1
        time.sleep(0.3)
    paths[fn] = "img/major-skill/" + name
print(f"圖示：新下載 {got}、已存在 {cached}、抓不到 {missing}")

with_icon = 0
for s in skills:
    fn = s.pop("_file", None)
    if fn and fn in paths:
        s["icon"] = paths[fn]
        with_icon += 1
print(f"有圖的技能 {with_icon} 個、沒圖 {len(skills) - with_icon} 個")

# ── 8. 分組摘要（前端要做分頁/分類時直接用）──────────────────────
groups, seen = [], set()
for s in skills:
    g = s.get("group")
    if not g or g in seen:
        continue
    seen.add(g)
    groups.append({"name": g, "en": s["groupEn"],
                   **({"icon": s["icon"]} if s.get("icon") else {})})

out = {"intro": intro, "groups": groups, "skills": skills}
if RESET_FILE in paths:
    out["resetIcon"] = paths[RESET_FILE]

# ── 9. 簡體字防呆 ──────────────────────────────────────────────
# 只列「簡體專用、台灣正體不會用」的字，避免誤判（擊/傷/戰/職 這種正體字不能列）。
SIMPLIFIED = set(
    "这个级点数术学习练问题时间说话对为国实现验证组织开关闭东车马鸟龙凤"
    "书报纸买卖钱银铁钢电脑络软盘库结构语标则规围绕过来动态变换转询创运"
    "执编译连调试错误处参类继属击伤复战队装备护饰药剂轴务经币仓购镶宝"
    "职业边远进还应该让认识发头长门单双项顺须顾领风飞鱼齐齿龟恶爱会儿农"
    "军决冲净凉刚别剑劳势医华卫厂历压厌县叶号员团园图圆场坏块坚坛声壶"
    "够绩绪续维绿义乡养兽兴举旧显晓暂权杀条极档树桥检楼样机杂枪欢欧灵质"
    "韩设计议论记谁请讲谅谈详诚谢积称种稳穷窃竞笔简签纪纯纲纳纵纷"
    "线练细终绍给绝统丝罚罢艺节芦苏茎荐荡获莲萧营萨"
)
bad = sorted({c for c in json.dumps(out, ensure_ascii=False) if c in SIMPLIFIED})
if bad:
    sys.exit(f"輸出裡有簡體字：{''.join(bad)}")

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
print(f"寫出 {OUT_JSON.relative_to(ROOT)}：{len(skills)} 個技能、{len(groups)} 組")

if untranslated:
    print("\n沒翻／保留原文：")
    for n, why in untranslated:
        print(f"  {n} — {why}")
