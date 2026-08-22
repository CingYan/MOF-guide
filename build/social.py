#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""七個社群／對戰系統頁 -> docs/data/social.json（台灣正體）+ docs/img/social/ 圖示。

處理的頁面：PvP、Party、PvM、Circle、Wedding、War Task and Material Supply、
Weather。抓取方式與 build/fetch.py 相同（curl 打 MediaWiki API），圖示流程與
build/skill_icons.py 相同（imageinfo 取網址、依中文名存檔、已存在且非空就不重抓）。

── 為什麼是「解析 + 對照表」而不是硬寫一份 JSON ──
原文是印尼文，散文沒辦法機械翻譯，所以譯文寫在下面的對照表裡；但表格、數值、
段落結構一律每次重新從 wikitext 解析出來，對照表用「清理過的原文」當 key。
好處是上游改字時對不上的段落會被 report_missing() 列出來，不會默默留著舊譯文。

── 翻譯範圍（刻意設限，寧缺勿猜）──
1. 系統／機制用語、數值單位、能力值名稱：翻譯，英文原名以「中文（English）」保留。
2. 道具名：只在 docs/data/items.json 找得到「效果數字完全吻合」的既有中文品項時
   才採用該中文名（例如 Wedding Ticket 的「婚禮進行 2 小時、新郎新娘各 5 張請帖」
   與 I0954「婚禮使用券」desc 一字不差），其餘保留原文。
3. 技能名：用 Fandom 的圖示檔名（Shaman_Skill3.png）對到 docs/data/wiki.json 既有
   的中文技能名，對照結果抄進 SKILL_ZH；wiki.json 本身仍是英文的 12 筆自行翻譯。
   注意 Fandom 的英文技能名與遊戲內中文名常常不是字面互譯（Fire Ball = 隕石術），
   所以對照依據是圖示檔名，不是名稱字面。
4. 職業：只翻四個基本職（劍士／弓箭手／魔法師／聖職者，對得上 wiki.json 的 jobTree
   第一層）。二轉以後的職業名保留原文 —— jobTree 的分支命名與這裡的英文名不是同一
   套（例如這裡 Fighter 線是 Sword Master/Gladiator/Heroes/General/Slayer/Dragon
   Knight，jobTree 是狂戰士／聖殿武士／統帥／聖騎士／征服者／十字軍），對不起來。
5. 人名、地名、怪物名：全部保留原文。專案裡的 monsters.json／maps.json 是另一套
   命名，實測用「等級＋HP」去對 PvM 的 117 隻怪，只有 30 隻唯一命中、38 隻撞號、
   49 隻查無對應，證據強度不足，不猜。

── 刻意捨棄的欄位 ──
Weather 表的 Sound 欄只有 .ogg 檔連結，本站不放音檔，整欄不輸出。
各頁的 Gallery／截圖區塊同理不輸出。
"""
import json, os, pathlib, re, subprocess, time, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "docs/data/social.json"
OUT_IMG = ROOT / "docs/img/social"
API = "https://master-of-fantasy.fandom.com/api.php"
TITLES = ["PvP", "Party", "PvM", "Circle", "Wedding",
          "War Task and Material Supply", "Weather"]
ILLEGAL = str.maketrans({"/": "／", "\\": "＼", ":": "：", "*": "＊", "?": "？",
                         '"': "＂", "<": "＜", ">": "＞", "|": "｜",
                         "%": "％", "#": "＃"})

MISSING = []


def curl(url=None, post=None):
    if post is not None:
        pathlib.Path("/tmp/_mofsocial_post.txt").write_text(post, "utf-8")
        cmd = ["curl", "-s", "-m", "60", "-X", "POST",
               "--data-binary", "@/tmp/_mofsocial_post.txt",
               "-H", "Content-Type: application/x-www-form-urlencoded", API]
    else:
        cmd = ["curl", "-s", "-m", "60", url]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def fetch_pages():
    post = ("action=query&format=json&prop=revisions&rvprop=content&rvslots=main"
            "&titles=" + urllib.parse.quote("|".join(TITLES)))
    d = json.loads(curl(post=post))
    pages = {}
    for p in d["query"]["pages"].values():
        rev = p.get("revisions")
        pages[p["title"]] = rev[0]["slots"]["main"]["*"] if rev else None
    for t in TITLES:
        if not pages.get(t):
            raise SystemExit(f"抓不到頁面：{t}")
    return pages


# ---------------------------------------------------------------------------
# wikitext 清理／解析
# ---------------------------------------------------------------------------
FILE_RE = re.compile(r"\[\[File:([^\]|]+)((?:\|[^\[\]]*)*)\]\]")


def _file_sub(m):
    """有 link= 的圖示用連結名稱代替（原文那裡沒有文字，只有圖）；
    沒有 link= 的圖示直接拿掉（原文圖後面一定緊接著名稱）。"""
    link = re.search(r"\|link=([^|\]]+)", m.group(2))
    return f" {link.group(1)} " if link else " "


def clean(s, expand_links=False):
    s = re.sub(r"\{\{.*?\}\}", "", s, flags=re.S)
    s = FILE_RE.sub(_file_sub, s)
    if expand_links:   # 只有 Weather 的地點欄要保留「區域（地圖）」的區域名
        s = re.sub(r"\[\[([^\]|]*)\|([^\]|]*)\]\]", r"\1（\2）", s)
    s = re.sub(r"\[\[[^\]|]*\|([^\]|]*)\]\]", r"\1", s)
    s = re.sub(r"\[\[([^\]|]*)\]\]", r"\1", s)
    s = s.replace("'''", "").replace("''", "")
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+([,.;:)])", r"\1", s)
    s = re.sub(r"(?<=\S) ?, ?(?=\S)", ", ", s)
    # 同一個技能的 Special1~4 變體會連著出現五次同名，收成一次
    while True:
        t = re.sub(r"\b(\w[\w' ]*?) \1\b", r"\1", s)
        if t == s:
            break
        s = t
    return s.strip()


def files_in(s):
    return [m.group(1).replace(" ", "_") for m in FILE_RE.finditer(s)]


def split_blocks(text):
    """回傳 [(level, 標題, 內文)]；level 0 是標題前的前言。"""
    text = re.sub(r"<gallery>.*?</gallery>", "", text, flags=re.S)
    text = re.sub(r"\[\[Category:[^\]]*\]\]", "", text)
    out, cur = [], [0, "", []]
    for line in text.split("\n"):
        m = re.match(r"^(=+)\s*(.*?)\s*\1\s*$", line)
        if m:
            out.append((cur[0], cur[1], "\n".join(cur[2])))
            cur = [len(m.group(1)), clean(m.group(2)), []]
        else:
            cur[2].append(line)
    out.append((cur[0], cur[1], "\n".join(cur[2])))
    return out


def _strip_attrs(cell):
    if "|" in cell and re.match(r"^\s*(style|scope|align|colspan|rowspan)\b", cell):
        return cell.split("|", 1)[1]
    return cell


def parse_tables(body, expand_cols=()):
    """把 {| ... |} 解析成 headers / rows / icons（icons 與 rows 同形狀）。"""
    tables = []
    for raw in re.findall(r"^\{\|.*?^\|\}", body, flags=re.S | re.M):
        headers, rows, icons, cur, curi = [], [], [], None, None
        for line in raw.split("\n")[1:]:
            line = line.strip()
            if line.startswith("!"):
                headers += [clean(_strip_attrs(c)) for c in line[1:].split("!!")]
            elif line.startswith("|-"):
                if cur is not None:
                    rows.append(cur), icons.append(curi)
                cur, curi = [], []
            elif line.startswith("|}"):
                break
            elif line.startswith("|") and cur is not None:
                cell = _strip_attrs(line[1:])
                cur.append(clean(cell, expand_links=len(cur) in expand_cols))
                curi.append(files_in(cell))
        if cur is not None:
            rows.append(cur), icons.append(curi)
        tables.append({"headers": headers, "rows": rows, "icons": icons})
    return tables


def parse_prose(body):
    """回傳 (段落 list, 條列 list)，各自是 (清理後文字, 圖示檔名 list)。"""
    body = re.sub(r"^\{\|.*?^\|\}", "", body, flags=re.S | re.M)
    paras, bullets = [], []
    for line in body.split("\n"):
        s = line.strip()
        if not s:
            continue
        target = bullets if s.startswith("*") else paras
        target.append((clean(s.lstrip("*").strip()), files_in(s)))
    return [p for p in paras if p[0]], [b for b in bullets if b[0]]


# ---------------------------------------------------------------------------
# ① 規則式轉換：純數值、單位、可套公式的句型
# ---------------------------------------------------------------------------
def sep(s):
    """印尼文用點當千分位（2.000 Libi），換成台灣習慣的逗號。"""
    return re.sub(r"(?<=\d)\.(?=\d{3}\b)", ",", s)


AUTO = [
    (r"-", lambda m: "—"),
    (r"[\d,]+", lambda m: m.group(0)),
    (r"[\d,]+%", lambda m: m.group(0)),
    (r"\d+~\d+", lambda m: m.group(0)),
    (r"([\d,\sX-]+) Points", lambda m: m.group(1).strip() + " 點"),
    (r"([\d,]+) Libi", lambda m: m.group(1) + " Libi"),
    (r"(\d+) Major Skill Points", lambda m: m.group(1) + " 點專業技能點數"),
    (r"Lv\.(\S+)~Lv\.(\S+)", lambda m: f"Lv.{m.group(1)}～Lv.{m.group(2)}"),
    (r"Lv\.(\S+)~MAX", lambda m: f"Lv.{m.group(1)}～最高等級"),
    (r"(\d+) Player", lambda m: m.group(1) + " 人"),
    (r"(.+) \(Boss\)", lambda m: m.group(1) + "（頭目）"),
    (r"(.+) \(Mini-Boss\)", lambda m: m.group(1) + "（小頭目）"),
    (r"(.+) Monster", lambda m: m.group(1) + " 的怪物"),
    (r"(\d) Level diatas Player: (\d+) Monster",
     lambda m: f"比角色高 {m.group(1)} 級：{m.group(2)} 隻"),
]
AUTO = [(re.compile(p + r"\Z"), f) for p, f in AUTO]


def auto(s):
    t = sep(s)
    for pat, fn in AUTO:
        m = pat.match(t)
        if m and m.end() == len(t):
            return fn(m)
    return None


# ---------------------------------------------------------------------------
# ② 刻意保留原文的專有名詞
# ---------------------------------------------------------------------------
# 二轉以後的職業名（jobTree 的分支命名對不上，見檔頭說明）
KEEP_JOB = [
    "Knight/General/Dragon Knight", "Sword Master/Heroes/Slayer",
    "Sniper/Sharpshooter/Imperial Shooter", "Ranger/Specialist/Trickster",
    "Arc Mage/Sage/Sorcerer", "Shaman/Warlock/Oracle",
    "Saint/Holy Avanger/Cardinal", "Paladin/Bishop/Arc Bishop",
]

# PvM 怪物名、地名 —— 專案內既有中文命名是另一套，對不起來（見檔頭說明）
KEEP = set("""
Shaman Sage Warlock Oracle Priest Saint Paladin Holy Avanger Cardinal
Slow Coach|Power Up|Grass|Ant|Pink Jelly|Wild Pigieon|Cosh|Chipmunk|Cabbage
Yellow Dreams|Queen Ant|Blue Dreams|Pigieon Skeleton|Chochas|Phantom Sailor
Skull Pirates|Poltergeist|Countess|Phantom Officer|High Pirates|Stone Cosh
Small Demon|Skeleton Wheel|Chip Mohican|Rabbit Mask|Wounded Crab|Ground Mecas
Drum Racoon|Break Sword|Tree Tag|Wild Boar|Red Dream|Chogals|Amber Ghost
Bumble Bee|Queen Bee|Kaniba|Kaniba Anger|Tree Plank|Dog Fighter|Dog Soldier
Light Of Dark|Small Feary|Demon Deers|Evil Candle|Fierce Pumpkin Ghost|Red Devil
Phantom Warrior|Phantom Soldier|Phantom Captain|Dog Captain|Big Boo|Metal Cabbage
Purple Jelly|Gamakichi|Goblin|Totempool|Zombie Goblin|Anger Goblin|Goblin Chief
Crab|Big Tree|Sea Star Warrior|Sand Stoker|Blue Rock|Blue Jelly|Gamatatsu
Bibos Fighter|Bibos Trainer|Evil Tree|Bibos Shaman|Red Rock|Tree Tag Wood Big
Fighter Mecas|Ghost Sword|Wolf Fighter|Wolf Ranger|Sanchoseu|Harpy|Wolf General
Queen Harpy|Little Black Dragon|Ghost|Rock|Black Skeleton Wheel|Bapho|Magic Sword
Zombie|Old Skeleton Prisoner|Orc|Orc Stone|Skeleton Warrior|Skeleton Wizard
Orc Boss|Ancient Beetle|White Snake|Machine Sentinel|Machine Warrior|Black Big Boo
Ancient Skeleton Warrior|Ancient Skeleton Wizard|Anger Wolf General|Kanzim
""".replace("\n", " ").replace("|", " ").split())
KEEP |= set(KEEP_JOB)
KEEP |= {
    # 技能名：wiki.json 對應的圖示欄位本身還是英文，沒有既有中文名可抄
    "Elements Mastery", "Revitalize", "Life Aura", "Self-curse",
    "Holy Attribute", "Cruno's Blessing",
    # 軍階：查不到對得上的既有中文，不猜（Chargeman、Pro-Guard）
    "Chargeman", "Pro-Guard",
    # Weather 的地點欄整欄是地名
    "Glan Wood（Battlefield, West Way）, West Enpa（Bluestar Forest Entrance, Corn Field）",
    "East Way, Corn Harvest, North Enpa（Exit Golden Grove）",
    "Cram Hill（Volcano Entrance）, Bluestar River Downside, Bluestar River Upside, Evil Corn Field",
    "Dark Hill（Dark Tower Entrance）",
    "Ciberian（Enter of Snow Field, Center of Snow Field, Exit of Snow Field）",
    "Enter of Paperon Wall, Exit of Paperon Wall",
}


# ---------------------------------------------------------------------------
# ③ 譯文對照表：key 是 clean() 之後的原文，對不到就會被 report_missing() 列出來
# ---------------------------------------------------------------------------
ZH = {
# ── PvP ────────────────────────────────────────────────────────────────────
"PvP (Player versus Player) adalah sebuah mode dimana player bertarung dengan player lainnya. Pembuat room PvP dapat menentukan mode PvP dan Use Items atau No Items di arena PvP. PvP terbagi atas 2 mode yaitu Deathmatch dan Team Battle. Dalam mode Deathmatch, kamu harus melawan seluruh peserta PvP dan bertahan hidup sampai akhir. Dalam mode Team Battle, kamu beserta anggota teammu harus melawan seluruh anggota team lawan. Jumlah total maksimal pemain yang bisa masuk kedalam ruangan PvP adalah 12 dengan 8 pemain (Deathmatch) atau 4 pemain (Team Battle) di masing-masing team dan 4 orang spectator. Semua peserta PvP harus membayar 1000 Libi untuk bisa mengikuti PvP mode. Spectator harus membayar 500 Libi untuk bisa melihat pertarungan di arena PvP. Pemenang mode PvP Deathmatch/Team Battle adalah yang berhasil bertahan hidup ketika seluruh peserta PvP lainnya/seluruh anggota team lawan terbunuh atau yang memiliki jumlah kill point paling tertinggi ketika waktunya habis. PvP hanya berlangsung selama 180 Detik. PvP hanya bisa diakses dari Libi Town di Field of Honor dengan mengklik tombol PvP yang ada di tengah layar. Semua pemain akan mendapatkan PvP Point setelah menyelesaikan mode PvP. Kamu hanya dapat mengikuti PvP sebanyak 20 kali sehari dan akan direset setiap jam 12 Malam.":
"PvP（Player versus Player）是玩家與玩家互相對戰的模式。開房的人可以決定 PvP 的對戰模式，以及競技場內要 Use Items（可用道具）還是 No Items（禁用道具）。PvP 分成 Deathmatch 與 Team Battle 兩種：Deathmatch 要對抗其他所有參賽者並存活到最後；Team Battle 則是和隊友一起對抗敵隊全員。PvP 房間最多可以進 12 人，Deathmatch 每隊 8 人、Team Battle 每隊 4 人，另外還有 4 個觀戰名額。所有參賽者要付 1000 Libi 才能參加 PvP 模式，觀戰者要付 500 Libi 才能觀看競技場內的戰鬥。Deathmatch／Team Battle 的勝者，是其他參賽者／敵隊成員全部陣亡後還活著的人，或是時間結束時擊殺點數最高的人。PvP 每場只進行 180 秒。PvP 只能在 Libi Town 的 Field of Honor，點畫面正中央的 PvP 按鈕進入。完成 PvP 模式後，所有玩家都會拿到 PvP 點數。每天最多只能參加 20 場 PvP，每天午夜 12 點重置。",
"Room Type": "房型",
"Required Level": "需求等級",
"PvP Limit": "每日參加上限",
"PvP Cost": "參賽費用",
"Spectator Cost": "觀戰費用",
"Room Cost": "開房費用",
"Junior": "初級（Junior）",
"Middle": "中級（Middle）",
"Senior": "高級（Senior）",
"Advance": "進階（Advance）",
"Free for All": "自由混戰（Free for All）",
"Unlimited": "無上限",
"PvP Points": "PvP 點數",
"Player Rank": "名次",
"PVP Rank": "PvP 稱號",
"Title": "稱號",
"Title Icon": "稱號圖示",
"Total PvP Points": "累計 PvP 點數",
"Noble 1": "貴族 1（Noble 1）",
"Noble 2": "貴族 2（Noble 2）",
"Noble 3": "貴族 3（Noble 3）",
"Heroes 1": "英雄 1（Heroes 1）",
"Heroes 2": "英雄 2（Heroes 2）",
"Heroes 3": "英雄 3（Heroes 3）",
"WarLord 1": "軍閥 1（WarLord 1）",
"WarLord 2": "軍閥 2（WarLord 2）",
"WarLord 3": "軍閥 3（WarLord 3）",
"WarLord 4": "軍閥 4（WarLord 4）",
"God of War": "戰神（God of War）",
"Tips & Trick": "攻略要點",
"All Job": "全職業通用",
"Kamu harus memiliki status Agility yang tinggi karena status Agility meningkatkan Accuracy, Critical, dan Evasion.":
"敏捷（Agility）要練高，因為敏捷會同時提升命中、爆擊與迴避。",
"Beberapa skill party tidak dapat digunakan di mode PvP.":
"部分隊伍技能在 PvP 模式無法使用。",
"Gunakan Major Skill Great Ghost Illusion untuk menghindari serangan lawan.":
"用專業技能 Great Ghost Illusion 閃避對手的攻擊。",
"Efek 100% Evasion dari Great Ghost Illusion tidak dapat menghidari skill trap lawan jadi berhati-hatilah ketika berjalan ke arena lawanmu.":
"Great Ghost Illusion 的 100% 迴避效果擋不掉對手的陷阱技能，走進對手場地時要小心。",
"Equip Ring, Necklace, dan Badge yang memiliki efek bagus untuk mode PvP.":
"配戴在 PvP 模式效果好的戒指（Ring）、項鍊（Necklace）與徽章（Badge）。",
"Equip Mirror Medal dan 2 pasang Mirage Ring agar lawan sulit untuk menyerangmu.":
"配戴 Mirror Medal 加兩對 Mirage Ring，讓對手難以打中你。",
"Equip Mirror Medal dan 2 pasang Eagle's Eye Ring agar lawan sulit untuk menghindar dari seranganmu.":
"配戴 Mirror Medal 加兩對 Eagle's Eye Ring，讓對手難以閃避你的攻擊。",
"Gunakan skill Power Burst, Wind Arrow, Fire Ball, dan Nova Strike ketika gauge bar yang berada dibawah HP dan MP bar sudah penuh karena skill tersebut menembusi Defense dan Evasion sekaligus juga instant kill lawanmu.":
"HP 與 MP 條下方的能量條集滿時，使用怒擊（Power Burst）、風之箭矢（Wind Arrow）、隕石術（Fire Ball）或聖十字攻擊（Nova Strike）；這些技能會同時穿透防禦力與迴避，可以直接秒殺對手。",
"Pastikan kamu memiliki senjata yang sudah memasuki level Extreme (+4), Heroes (+5), atau Legendary (+6).":
"武器要先強化到 Extreme（+4）、Heroes（+5）或 Legendary（+6）等級。",
"PvP Cup hanya mengizinkan anggota dari masing-masing team berasal dari 4 Job dasar yang berbeda.":
"PvP Cup 規定每一隊的成員必須分別來自四種不同的基本職業。",
"Lindungilah anggota teammu yang memilih job Cleric karena dia memiliki skill Revitalize dan Revive sehingga dia akan menjadi target utama lawanmu.":
"要保護隊上選聖職者（Cleric）的隊友，因為他有 Revitalize 和復活（Revive），一定會成為對手的首要目標。",
"Senjata yang dibawa: Dagger, Long Sword, Axe, dan Dual Sword.":
"建議武器：短劍（Dagger）、長劍（Long Sword）、斧（Axe）、雙劍（Dual Sword）。",
"Gunakan Dual Sword untuk menghindari serangan lawan dan gunakan skill buff Dualsword Training untuk meningkatkan Defensemu.":
"用雙劍閃避對手攻擊，並開啟增益技能雙劍防禦（Dualsword Training）提升防禦力。",
"Ketika berada didekat lawan, langsung ganti ke Dagger dan gunakan skill Roar untuk memberikan efek Stun kepada semua lawan yang berada didekatmu.":
"貼近對手時立刻換成短劍，使用死者之歌（Roar）讓周圍所有對手陷入暈眩。",
"Gunakan skill buff Tiger's Fury lalu pakai Axe sebagai senjata utama jika mau fokus pada Damage atau Long Sword jika mau fokus pada Critical.":
"先開增益技能力量上升（Tiger's Fury），想吃傷害就用斧當主武器，想吃爆擊就用長劍。",
"Gunakan skill Whirlwind ketika menggunakan Long Sword karena Axe tidak dapat digunakan dengan skill tersebut.":
"旋風（Whirlwind）只能在使用長劍時發動，斧無法使用這個技能。",
"Gunakan Axe ketika menggunakan skill Bladestorm karena skill area tersebut memiliki Critical yang tinggi dan Axe memiliki damage yang terkuat dari semua senjata di Master Of Fantasy.":
"使用 Bladestorm 時搭配斧，因為這個範圍技爆擊很高，而斧是 Master Of Fantasy 全武器中傷害最高的。",
"Gunakan skill buff Defensive Stance ketika berada di arena lawan.":
"進到對手場地時先開增益技能不屈之鬥志（Defensive Stance）。",
"Jika beruntung skill buff Endurance aktif ketika kamu diserang musuh sehingga Defensemu meningkat secara drastis.":
"運氣好的話，被攻擊時會觸發增益技能鐵壁（Endurance），防禦力大幅上升。",
"Jika beruntung lawanmu akan terkena status Stun dari efek Deadly Blow ketika kamu menyerangnya tanpa menggunakan skill attack.":
"運氣好的話，不用攻擊技能的普通攻擊會透過抽打（Deadly Blow）的效果讓對手陷入暈眩。",
"Jika beruntung skill buff Continuous Blow aktif ketika kamu menyerang musuh sehingga Attack Speedmu menjadi lebih cepat.":
"運氣好的話，攻擊時會觸發增益技能 Continuous Blow，攻擊速度變快。",
"Senjata yang dibawa: Long Sword dan Dual Sword.": "建議武器：長劍與雙劍。",
"Gunakan skill buff Tiger's Fury, Sword's Blessing, Focus, dan Power Surge dalam waktu yang bersamaan, lalu langsung gunakan skill Lethal Strike untuk langsung membunuh lawanmu dari jarak yang jauh jika serangan tersebut Critical.":
"同時開啟增益技能力量上升（Tiger's Fury）、狂暴劍（Sword's Blessing）、猛攻的姿勢（Focus）與英雄心（Power Surge），接著立刻使用功令斬（Lethal Strike）；只要打出爆擊，就能從遠處直接擊殺對手。",
"Gunakan skill Backstab untuk menyerang semua lawan yang berada di dekatmu.":
"使用 Backstab 攻擊周圍所有對手。",
"Gunakan Dual Sword untuk menghindari serangan lawan.": "用雙劍閃避對手的攻擊。",
"Jika beruntung skill buff Anger aktif ketika kamu diserang musuh sehingga Damagemu meningkat secara drastis.":
"運氣好的話，被攻擊時會觸發增益技能憤怒（Anger），傷害大幅上升。",
"Senjata yang dibawa: Bow dan Crossbow.": "建議武器：弓（Bow）與十字弓（Crossbow）。",
"Gunakan Skill Race agar dapat bergerak dengan cepat":
"使用加速術（Race）讓移動速度變快。",
"Gunakan Skill Instant Arrow untuk menyerang lawanmu dengan sangat cepat.":
"使用瞬間射擊（Instant Arrow）以極快的速度攻擊對手。",
"Gunakan skill buff Arrow Blessing lalu langsung gunakan skill Poisoned Arrow atau Enchanted Arrow untuk langsung membunuh lawanmu dari jarak yang jauh jika serangan tersebut Critical.":
"先開增益技能狙擊方法（Arrow Blessing），接著立刻使用猛毒之火箭（Poisoned Arrow）或致命射擊（Enchanted Arrow）；只要打出爆擊，就能從遠處直接擊殺對手。",
"Gunakan skill Multi Shot ketika berada di dekat lawanmu karena skill area ini memiliki damage yang tinggi.":
"貼近對手時使用多人射擊（Multi Shot），這個範圍技傷害很高。",
"Gunakan skill Power Shot untuk menyerang lawan yang berada didepanmu karena skill ini dapat memberikan efek stop dan memiliki damage yang tinggi.":
"用力量射擊（Power Shot）攻擊正前方的對手，這個技能有停止效果而且傷害很高。",
"Jika beruntung skill buff Precise Shooting aktif ketika kamu menyerang musuh sehingga Akurasimu meningkat secara drastis.":
"運氣好的話，攻擊時會觸發增益技能鬆氣（Precise Shooting），命中大幅上升。",
"Jika beruntung skill buff Shadow Figure aktif ketika kamu diserang musuh sehingga Evasionmu meningkat secara drastis.":
"運氣好的話，被攻擊時會觸發增益技能絕對回避（Shadow Figure），迴避大幅上升。",
"Senjata yang dibawa: Crossbow.": "建議武器：十字弓。",
"Gunakan seluruh skill Trap yang ada. Jika bermain mode Team Battle, pasang trap di dekat arena teammu sendiri untuk menjebak lawan yang datang.":
"把手上所有陷阱技能都用上。打 Team Battle 時把陷阱佈在自己隊伍場地附近，等對手闖進來。",
"Gunakan skill Hammer Shot kepada lawan yang berada di depanmu karena memiliki efek Stun dan memiliki damage yang tinggi.":
"對正前方的對手使用榔頭射擊（Hammer Shot），有暈眩效果而且傷害很高。",
"Gunakan skill Blinding Shot ketika berada di dekat lawanmu karena skill area ini memiliki efek Stun.":
"貼近對手時使用爆發的子彈（Blinding Shot），這個範圍技有暈眩效果。",
"Senjata yang dibawa: Staff dan Book.": "建議武器：手杖（Staff）與魔法書（Book）。",
"Gunakan skill buff Mana Shield untuk menukarkan damage yang diterima ke MP sendiri.":
"用增益技能精神保護幕（Mana Shield）把受到的傷害轉嫁到自己的 MP。",
"Gunakan skill Ice Illusion ketika berjalan ke arena lawan karena tidak seperti Great Ghost Illusion, skill ini dapat menghindari skill trap lawan.":
"走進對手場地時使用 Ice Illusion；和 Great Ghost Illusion 不同，這個技能可以閃過對手的陷阱技能。",
"Gunakan skill yang memiliki efek freeze di Team Battle supaya anggota teammu jadi bisa fokus mengincar target utama yang berada di arena lawanmu seperti Cleric.":
"打 Team Battle 時用有冰凍效果的技能，讓隊友可以專心鎖定對方場地的首要目標，例如聖職者。",
"Gunakan skill Earthquake ketika berada di dekat lawanmu karena memiliki efek Stun.":
"貼近對手時使用地震（Earthquake），有暈眩效果。",
"Senjata yang dibawa: Book.": "建議武器：魔法書。",
"Gunakan skill Summon Dragon ketika berada didekat lawanmu.":
"貼近對手時使用飛龍召喚（Summon Dragon）。",
"Gunakan skill Hellfire karena skill tersebut bisa memberikan efek Stun.":
"使用 Hellfire，這個技能帶暈眩效果。",
"Senjata yang dibawa: Cross.": "建議武器：十字架（Cross）。",
"Menghadapi lawan yang memilih job Mage berkat skill passive Holy Guardian yang meningkatkan Magic Resist.":
"靠被動技能降魔之盔甲（Holy Guardian）提升魔法抗性，適合對上選魔法師的對手。",
"Gunakan skill Energy Burst ketika berada di dekat lawanmu karena skill area ini memiliki damage yang tinggi.":
"貼近對手時使用神的力量（Energy Burst），這個範圍技傷害很高。",
"Senjata yang dibawa: Hammer.": "建議武器：鎚（Hammer）。",
"Gunakan skill Guardian's Fury, Shockwave, dan Moon's Blessing ketika berada didekat lawanmu karena skill area tersebut memiliki efek Stun.":
"貼近對手時使用神之憤怒（Guardian's Fury）、衝擊派（Shockwave）與 Moon's Blessing，這些範圍技都有暈眩效果。",
"Jika beruntung skill Angry Roar aktif ketika kamu diserang musuh sehingga semua lawan yang berada didekatmu terkena status stun.":
"運氣好的話，被攻擊時會觸發營力之釋放（Angry Roar），周圍所有對手陷入暈眩。",
"Gallery": "圖庫",
"Trivia": "雜項補充",
# ── Party ──────────────────────────────────────────────────────────────────
"Party sangat bermanfaat ketika kamu akan pergi hunting. Jumlah maksimal anggota party hanya bisa terdiri dari 5 member saja termasuk karaktermu. Semua anggota party dapat menggunakan Party Chat, warna dari tulisan Party Chat adalah cyan. Semua anggota party dapat mengambil Libi dan Item drop-an dari Monster yang terbunuh. Untuk mengajak pemain lain bergabung kedalam sebuah party, kamu harus mengklik kanan nama pemain atau karakter pemain lalu pilih Invite Party kemudian menunggu apakah dia menolak undangan party atau tidak. Kamu hanya bisa mengajak pemain lain bergabung kedalam party jika level mereka, 10 level lebih rendah atau tinggi dari karaktermu. Semua anggota party akan mendapatkan Exp jika berada ditempat yang sama dengan anggota party yang sedang hunting. Exp yang diterima anggota party akan disetarakan dengan anggota party yang berada di tempat yang sama.":
"出門打怪時組隊非常實用。一支隊伍最多 5 人，含你自己的角色在內。所有隊員都可以使用隊伍頻道（Party Chat），隊伍頻道的文字顏色是青色。所有隊員都撿得到被擊殺怪物掉落的 Libi 與道具。要邀請其他玩家入隊，在對方的玩家名稱或角色上按右鍵，選 Invite Party，然後等對方決定是否接受。只有等級與你相差 10 級以內的玩家才邀得進來。只要和正在打怪的隊員待在同一個地點，所有隊員都會拿到經驗值；隊員拿到的經驗值會在同地點的隊員之間均分。",
"Mercenary Bonus": "傭兵加成",
"Jika kamu menjadi ketua party dan memiliki Major Skill Mercenary, maka semua anggota partymu akan mendapatkan Accuracy, Evasion, dan Attack bonus.":
"你擔任隊長並且擁有專業技能 Mercenary 時，全隊成員都會獲得命中、迴避與攻擊力加成。",
"Skill Level": "技能等級",
"1-4 Member Party": "1～4 人隊伍",
"5 Member Party": "5 人隊伍",
"Basic": "基礎（Basic）",
"Beginner": "初階（Beginner）",
"Intermediate": "中階（Intermediate）",
"Great": "高階（Great）",
"Special": "特級（Special）",
"Skill Party": "隊伍技能",
"Berikut adalah daftar skill yang dapat digunakan atau bermanfaat bagi semua anggota party:":
"以下是可以對全隊成員發揮作用的技能：",
"Mage": "魔法師（Mage）",
"Cleric": "聖職者（Cleric）",
"Skill Icon": "技能圖示",
"Skill Name": "技能名稱",
"Job": "職業",
"Hero's Song": "狂氣之歌（Hero's Song）",
"Illusive Power": "加速咒文（Illusive Power）",
"Fire Attribute": "賦予火屬性（Fire Attribute）",
"Ice Attribute": "賦予冰屬性（Ice Attribute）",
"Lightning Attribute": "賦予閃電屬性（Lightning Attribute）",
"Darkness Attribute": "賦予黑暗屬性（Darkness Attribute）",
"Revive": "復活（Revive）",
"Summon": "召喚（Summon）",
"Soothing Prayer": "生命之波濤（Soothing Prayer）",
"Blessing": "神之祝福（Blessing）",
"Holy Shout": "聖騎士之吶喊（Holy Shout）",
"Enchant Attack": "攻擊的縲繩（Enchant Attack）",
"Party Bonus": "隊伍加成",
"Jika nama dari skill party berbeda tetapi memiliki efek yang sama, maka kedua efek dari skill tersebut dapat digunakan dalam waktu yang bersamaan. Bonus status yang terkena efek dari skill party terdiri dari:":
"隊伍技能的名稱不同但效果相同時，兩個效果可以同時生效。受隊伍技能影響的加成狀態有：",
"Team Attribute Bonus": "隊伍屬性加成（Team Attribute Bonus）",
"Party Damage": "隊伍傷害（Party Damage）",
"Defense Bonus": "防禦力加成（Defense Bonus）",
"Up Attack": "攻擊力上升（Up Attack）",
"Up Strength": "力量上升（Up Strength）",
"Up Agility": "敏捷上升（Up Agility）",
"Up Intellect": "智力上升（Up Intellect）",
"Team Exp Bonus": "隊伍經驗值加成（Team Exp Bonus）",
"Grinding Exp Tips": "練功經驗值要點",
"Bawalah 1 anggota party yang levelnya 8-10 lebih rendah dari levelmu ketempat monster yang memiliki HP Bar berwarna biru atau masuk kedalam Instant Dungeon karena monster yang memiliki HP Bar berwarna biru lebih lemah dan Exp yang diterima menjadi lebih besar karena ada anggota party yang levelnya lebih rendah dari level monster tersebut.":
"帶一位比你低 8～10 級的隊員，到 HP 條顯示藍色的怪物區，或是進副本（Instant Dungeon）。HP 條藍色的怪物比較弱，而且隊伍裡有等級低於怪物的成員時，拿到的經驗值會更多。",
"Suruhlah anggota party yang kamu ajak diam di lokasi yang aman jika kamu tidak perlu bantuan.":
"不需要幫忙的時候，請帶進來的隊員待在安全的地方就好。",
"Jika HP anggota party yang kamu ajak tinggi, suruhlah dia membantu memancing banyak monster ke arah karaktermu. (Note: Jangan lakukan hal tersebut jika kamu hunting di Castle of Heaven dan Rundwell Fortress karena monster-monster tersebut memiliki damage yang tinggi dan bisa memberikan Status Effect)":
"隊員 HP 高的話，可以請他幫忙把大量怪物拉到你的角色這邊。（注意：在 Castle of Heaven 和 Rundwell Fortress 打怪時別這樣做，那裡的怪物傷害很高，還會造成異常狀態。）",
"Jika HP anggota party yang kamu ajak rendah, suruhlah dia membawa 2-3 monster ke arah karaktermu.":
"隊員 HP 低的話，請他一次只帶 2～3 隻怪物過來就好。",
"Jika Job dari anggota party yang kamu ajak adalah Cleric, mintalah dia menggunakan semua skill party atau heal.":
"隊員的職業是聖職者（Cleric）的話，請他把隊伍技能全開，或是負責補血。",
# ── PvM ────────────────────────────────────────────────────────────────────
"PvM (Player versus Monster) adalah sebuah mode dimana player dari masing-masing team bertarung untuk melawan para Monster. Jumlah total maksimal pemain yang bisa masuk kedalam ruangan PvM adalah 12 dengan 6 pemain di masing-masing team. Pemenang mode PvM ditentukan dengan jumlah kill point tertinggi ketika waktunya habis atau jika seluruh pemain di team lain terbunuh oleh para monster. PvM hanya bisa diakses dari Libi Town di Field of Honor. Monster-monster yang muncul di mode ini dimulai dari yang level terendah sampai yang tertinggi. Semua pemain akan mendapatkan PvP Point setelah menyelesaikan mode PvM.":
"PvM（Player versus Monster）是兩隊玩家各自對抗怪物的模式。PvM 房間最多可以進 12 人，每隊 6 人。勝負由時間結束時擊殺點數較高的一方決定，或是另一隊玩家全被怪物殺光時分出。PvM 只能在 Libi Town 的 Field of Honor 進入。這個模式出現的怪物會從最低等級一路排到最高等級。完成 PvM 模式後，所有玩家都會拿到 PvP 點數。",
"Monster List": "怪物列表",
"Berikut adalah daftar seluruh monster yang muncul di PvM mode:":
"以下是 PvM 模式會出現的所有怪物：",
"Bunuh Slow Coach agar ada 3 Power Up yang muncul untuk menyerang dan menganggu pemain di team lain.":
"擊殺 Slow Coach 會刷出 3 個 Power Up，可以用來攻擊、干擾另一隊的玩家。",
"Bunuh Boss dari para Monster secepatnya karena tidak akan ada satupun monster yang bisa muncul kecuali Power Up sebelum berhasil membunuhnya.":
"頭目要盡快解決；頭目沒死之前，除了 Power Up 以外不會再刷出任何怪物。",
"Gunakan semua Ring, Necklace, dan Badge yang memiliki efek untuk menaikkan damage.":
"把所有能提升傷害的戒指（Ring）、項鍊（Necklace）與徽章（Badge）都戴上。",
"Gunakan semua skill area dan trap.": "所有範圍技與陷阱技能全部用上。",
"Jangan menggunakan skill yang bisa memberikan efek freeze karena kamu tidak dapat menyerang monster yang sedang terkena status freeze.":
"不要用會造成冰凍效果的技能，處於冰凍狀態的怪物是打不到的。",
"Semua monster yang muncul dimode ini ada kemungkinan menjatuhkan drop rare Assassin's Ring, Envoy Ring, Eagle's Eye Ring, dan Mirage Ring.":
"這個模式出現的所有怪物都有機會掉出稀有物：Assassin's Ring、Envoy Ring、Eagle's Eye Ring 與 Mirage Ring。",
"Skill Open Wound milik General langsung memberikan 29 damage kepada Slow Coach tanpa menghiraukan defense yang dimilikinya.":
"General 的技能目標（Open Wound）可以無視防禦力，直接對 Slow Coach 造成 29 點傷害。",
"General/Dragon Knight, Heroes/Slayer, Specialist/Trickster, Sage/Sorcerer, dan Bishop/Arc Bishop adalah kombinasi team terbaik untuk mode PvM.":
"General／Dragon Knight、Heroes／Slayer、Specialist／Trickster、Sage／Sorcerer 與 Bishop／Arc Bishop 是 PvM 模式最好的隊伍組合。",
"Setelah membunuh Endless Dragon, hanya Slow Coach dan Power Up yang bisa muncul di arenamu.":
"打倒 Endless Dragon 之後，場上只會再刷出 Slow Coach 和 Power Up。",
"Hanya monster-monster yang tinggal di wilayah Libi Island (kecuali Castle of Heaven) yang muncul di mode ini.":
"只有棲息在 Libi Island 區域的怪物會出現在這個模式，Castle of Heaven 的怪物除外。",
# ── Circle ─────────────────────────────────────────────────────────────────
"Circle adalah sebuah organisasi yang makin mempererat komunitas sesama pemain. Banyak kuis dan tugas-tugas yang bisa dilakukan bersama-sama dalam sebuah Circle, tentunya dengan hadiah yang lebih menarik. Sebuah Circle dapat berkompetisi dengan Circle lain untuk memperebutkan ranking Circle yang terbaik. Karaktermu harus memiliki Major Skill Basic/Beginner/Intermediate/Great/Special Circle Building untuk membuat suatu Circle. Jika kamu sudah memiliki Circle, kamu dapat masuk kedalam Circle Room. Setiap Circle hanya bisa memiliki sebanyak 2 orang Circle Vice.Semua anggota circle kamu dapat menggunakan Circle Chat, warna dari tulisan Circle Chat adalah kuning.":
"社團（Circle）是讓玩家之間更緊密的組織。社團裡有很多可以一起完成的問答與任務，獎勵也更豐厚。社團之間還可以互相競爭，搶最佳社團的排名。角色必須先擁有專業技能 Circle Building（Basic／Beginner／Intermediate／Great／Special）才能建立社團。有社團之後就能進入社團房間（Circle Room）。每個社團最多只能有 2 位副團長（Circle Vice）。所有社團成員都可以使用社團頻道（Circle Chat），社團頻道的文字顏色是黃色。",
"Seorang Ketua Circle juga dapat menambah jumlah anggotanya sebanyak 10 orang dengan menggunakan Item Mall Circle Expansion Scroll.":
"團長還可以使用商城道具公會員擴大卷軸（Circle Expansion Scroll），把成員上限再往上加 10 人。",
"Max Member": "成員上限",
"Circle Role": "社團職務",
"Circle Master adalah ketua dari sebuah Circle. Circle Master dapat melakukan semua hal mengenai Circle. Seorang Circle Master dapat membuat Circle Member menjadi Circle Vice. Hanya ketua circle yang dapat membubarkan Circlenya sendiri.":
"團長（Circle Master）是社團的領導者，社團相關的所有事情都能做，可以把一般團員升為副團長。只有團長能解散自己的社團。",
"Circle Vice adalah wakil dari sebuah Circle. Seorang Circle Vice hanya dapat mengambil Circle Quest, mengkick anggota circle kecuali Circle Master dan Circle Vice lainnya, menginvite pemain lain kedalam circle.":
"副團長（Circle Vice）是社團的副手，只能接社團任務、把其他成員踢出社團（團長與另一位副團長除外），以及邀請其他玩家加入社團。",
"Circle Member adalah anggota biasa dari sebuah Circle.":
"團員（Circle Member）是社團的一般成員。",
"Circle Rank": "社團排名",
"Peringkat dari suatu Circle akan mempengaruhi Bonus Exp yang diterima oleh seluruh anggota Circle yang sedang hunting. Kamu dapat meningkatkan point circlemu dengan menyelesaikan Circle Quest yang diambil oleh seorang Circle Master atau Circle Vice. Semua peringkat Circle akan direset ketiap hari Jumat pukul 19:00. Kamu dapat melihat peringkat Circle dengan mengklik Circle Board yang berada di Study Way, Bluestar Harbour, The Center of Papreon":
"社團排名會影響所有正在打怪的社團成員拿到的額外經驗值。完成團長或副團長接下的社團任務就能累積社團點數。所有社團排名每週五 19:00 重置。點 Study Way、Bluestar Harbour、The Center of Papreon 的社團看板（Circle Board）就能查看社團排名。",
"Rank": "排名",
"Bonus Exp": "額外經驗值",
"Dibawah 30": "30 名以後",
"Quest Circle": "社團任務",
"Quest Circle adalah sebuah quest khusus yang dapat diselesaikan secara bersama-sama dengan semua anggota Circlemu. Quest Circle hanya dapat diambil oleh seorang Circle Master atau Circle Vice dengan berbicara kepada Nostel, Ted, dan Bruno. Setiap Quest Circle memiliki jumlah batas waktu tersisa yang berbeda-beda. Beberapa Quest Circle yang diambil dapat diskip oleh Circle Master atau Circle Vice dengan menekan tombol Give Up. Quest Circle terdiri dari:":
"社團任務是可以由全社團成員一起完成的特殊任務，只有團長或副團長能向 Nostel、Ted、Bruno 領取。每個社團任務的剩餘時限都不一樣。部分接下的社團任務可以由團長或副團長按 Give Up 放棄。社團任務有以下幾種：",
"Total Experience: Mendapatkan sebanyak X experience. Ketika Quest Circle ini selesai semua anggota circle akan mendapatkan 20% dari experience yang mereka kontribusikan. Quest Circle ini tidak dapat di Give Up.":
"Total Experience（總經驗值）：累積取得 X 點經驗值。任務完成時，全體社團成員會拿回自己貢獻經驗值的 20%。這種任務不能放棄。",
"Study Session: Mencapai 82 point dengan berhasil menyelesaikan Class. Registrasilah pada Laura untuk mengikuti kelas. Point yang didapat tergantung dari kelas yang diambil. Junior: 4 point, Middle: 5 point, Senior: 6 point. Quest Circle ini tidak dapat di Give Up.":
"Study Session（上課）：靠完成課程累積到 82 點。向 Laura 報名上課，拿到的點數依課程而定：Junior 4 點、Middle 5 點、Senior 6 點。這種任務不能放棄。",
"Circle Dungeon: Menyelesaikan Circle Dungeon bersama anggota Circle sebanyak 1 kali. Quest Circle ini dapat di Give Up.":
"Circle Dungeon（社團副本）：和社團成員一起通關社團副本 1 次。這種任務可以放棄。",
"Hunting: Dapatkanlah 1500 point dengan cara membunuh Monster yang lebih kuat dari karaktermu. Monster dengan HP Bar berwarna biru: 1 point, Monster dengan HP Bar berwarna ungu: 2 points. Quest Circle ini tidak dapat di Give Up.":
"Hunting（狩獵）：擊殺比自己角色強的怪物，累積 1500 點。HP 條藍色的怪物 1 點，HP 條紫色的怪物 2 點。這種任務不能放棄。",
"Boss Hunt: Membunuh sebanyak X Boss atau Mini-Boss. Mereka ditandakan dengan nama yang berwarna merah. Satu boss bernilai 1 point. Quest Circle ini tidak dapat di Give Up.":
"Boss Hunt（討伐頭目）：擊殺 X 隻頭目或小頭目，牠們的名稱顯示為紅色。一隻算 1 點。這種任務不能放棄。",
"War Task: Selesaikan War Task bersama-sama dan mencapai X point. Quest Circle ini dapat di Give Up.":
"War Task（戰爭任務）：全社團一起完成戰爭任務，累積到 X 點。這種任務可以放棄。",
# ── Wedding ────────────────────────────────────────────────────────────────
"Karaktermu dapat menikahi karakter pemain lain di Master Of Fantasy setelah kamu berhasil melamarnya terlebih dahulu. Kamu dapat melamar pasanganmu dengan berbicara kepada Anna. Pemain yang ingin kamu lamar harus berada di Channel yang sama.":
"在 Master Of Fantasy 裡，先向對方求婚成功之後，你的角色就可以和其他玩家的角色結婚。找 Anna 對話即可求婚。想求婚的對象必須和你在同一個頻道（Channel）。",
"Syarat-syarat yang diperlukan untuk Wedding adalah:": "舉行婚禮的條件如下：",
"Karaktermu dan pasanganmu minimal harus sudah melakukan pergantian ke 2nd Job.":
"你和對方的角色都至少要完成二轉。",
"Kamu dan pasanganmu membutuhkan Wedding Ticket dan Couple Ring.":
"你和對方都需要婚禮使用券（Wedding Ticket）與情侶戒指（Couple Ring）。",
"Inventory Karaktermu dan pasanganmu tidak boleh penuh.":
"你和對方角色的背包都不能是滿的。",
"Pernikahan hanya bisa dilakukan di Channel 7.": "婚禮只能在第 7 頻道舉行。",
"Pendaftaran pernikahan berlangsung selama 3 hari. Jadwal pernikahan dapat dilihat di Wedding Schedule Board yang terletak di Inter Place. Kamu hanya dapat masuk kedalam Wedding Hall setelah mendapatkan undangan pernikahan dari pemain yang akan menikah. Waktu pernikahan adalah 20 menit, jika lewat maka pernikahan akan gagal, harap semua undangan memasuki ruangan pernikahan. Pada saat Wedding berlangsung, masukkan nama karakter yang ingin kamu suruh untuk mengantarkan Bouquet Flower. Bouquet Flower adalah item buff yang dapat digunakan ketika sedang hunting Monster.":
"婚禮登記為期 3 天。婚禮時程可以到 Inter Place 的婚禮時程看板（Wedding Schedule Board）查詢。必須先拿到新人發出的婚禮請帖，才能進入婚禮會場（Wedding Hall）。婚禮時間為 20 分鐘，超時婚禮就會失敗，請所有受邀者務必準時進場。婚禮進行中，輸入你想指定去遞送花束（Bouquet Flower）的角色名稱。花束是一種增益道具，打怪時可以使用。",
"Kamu dapat menceraikan pasanganmu dengan berbicara kepada Anna. Kamu memiliki batas waktu 3 hari untuk membuat pilihan tersebut. Jika pasanganmu menyetujuinya maka kamu akan bercerai. Kamu akan bercerai secara otomatis jika karakter pasanganmu telah dihapus.":
"找 Anna 對話可以和配偶離婚，你有 3 天的時間做決定。對方同意就會離婚。如果配偶的角色被刪除，則會自動離婚。",
"Wedding Ticket": "婚禮使用券（Wedding Ticket）",
"Wedding Ticket adalah tiket undangan pernikahan yang dikirimkan kepada pemain lainnya yang hanya bisa kamu beli dari Item Mall (IM) saja. Kamu dan pasanganmu harus sama-sama membagikan undangan pernikahan. Masukkan nama karakter yang kamu ingin undang kedalam pernikahanmu. Kamu hanya dapat mengundang pemain yang telah melakukan pergantian ke 2nd Job. Pemain yang telah berhasil mendapatkan Surat Undangan didalam inventorynya dapat menghadiri upacara pernikahan.":
"婚禮使用券是用來發給其他玩家的婚禮邀請券，只能在商城（Item Mall，IM）購買。你和配偶雙方都要各自發送請帖，輸入想邀請來參加婚禮的角色名稱。只能邀請已完成二轉的玩家。背包裡順利收到婚禮請帖的玩家才能出席婚禮。",
"Image": "圖示",
"Item Name": "道具名稱",
"Effect": "效果",
"2 jam waktu pernikahan dan 5 undangan untuk mempelai pria dan 5 untuk pengantin wanita.":
"婚禮進行 2 小時，新郎與新娘各可使用 5 張請帖。",
"Premium Wedding Ticket": "高級婚禮使用券（Premium Wedding Ticket）",
"3 jam waktu pernikahan dan 10 undangan untuk mempelai pria dan 10 untuk pengantin wanita.":
"婚禮進行 3 小時，新郎與新娘各可使用 10 張請帖。",
"Couple Ring": "情侶戒指（Couple Ring）",
"Couple Ring hanya bisa didapatkan setelah membuka Couple Gift Box yang bisa dibeli dari Anna dan Item Mall. Jika Cincin pasanganmu telah diganti, maka Cincin sebelumnya akan diambil.":
"情侶戒指要打開情侶禮盒（Couple Gift Box）才拿得到，禮盒可以向 Anna 或在商城購買。若配偶的戒指換過，先前那只戒指會被收回。",
"Jika kamu memiliki Gold Couple Ring atau Diamond Couple Ring, maka akan muncul Treasure Box ditempat Honey Moon. Kamu tidak dapat memanggil pasanganmu jika kamu atau dia berada ditempat yang sama atau didalam Instant Dungeon atau berada di tempat yang ada batas persyaratan minimal level untuk masuk ke dalam wilayah tersebut.":
"擁有金色情侶戒指或鑽石情侶戒指時，蜜月地點會出現寶箱（Treasure Box）。若你和配偶已經在同一個地點、其中一方在副本（Instant Dungeon）內，或身處有最低等級限制的區域，就無法召喚配偶。",
"Couple Gift Box": "情侶禮盒（Couple Gift Box）",
"Wedding Ring": "結婚戒指（Wedding Ring）",
"Silver Couple Gift Box": "銀色情侶禮盒（Silver Couple Gift Box）",
"Silver Couple Ring": "銀色情侶戒指（Silver Couple Ring）",
"Sepasang cincin perak. Akan memberikan couple-effect saat digunakan bersama pasangan, tidak dapat memanggil pasangan":
"一對銀戒指。與配偶一起配戴時會產生情侶特效，無法召喚配偶。",
"Gold Couple Gift Box": "金色情侶禮盒（Gold Couple Gift Box）",
"Gold Couple Ring": "金色情侶戒指（Gold Couple Ring）",
"Sepasang cincin emas dengan efek Sparkling Heart. Dapat memanggil pasangan sebanyak 2 kali dalam sehari":
"一對金戒指，帶有 Sparkling Heart 特效。每天可以召喚配偶 2 次。",
"Diamond Couple Gift Box": "鑽石情侶禮盒（Diamond Couple Gift Box）",
"Diamond Couple Ring": "鑽石情侶戒指（Diamond Couple Ring）",
"Sepasang cincin berlian dengan efek Sparkling Heart. Dapat memanggil pasangan sebanyak 5 kali dalam sehari dan memberikan bonus exp 10%":
"一對鑽石戒指，帶有 Sparkling Heart 特效。每天可以召喚配偶 5 次，並提供 10% 額外經驗值。",
# ── War Task and Material Supply ───────────────────────────────────────────
"War Task": "戰爭任務（War Task）",
"War Task adalah sebuah tugas yang diberikan oleh Roland dan Philip untuk membunuh sekelompok Monster dalam jumlah yang tertentu. Kamu hanya bisa memilih sebanyak 3 Monster yang diinginkan untuk War Task yang levelnya diatas 1 sampai 7 dari level karaktermu. Semakin tinggi level dari Monster, maka semakin sedikit jumlah yang dibutuhkan untuk membunuh Monster tersebut.":
"戰爭任務是 Roland 和 Philip 發布的委託，內容是擊殺指定數量的某種怪物。一次最多可以挑 3 種怪物，怪物等級必須比角色高 1～7 級。怪物等級愈高，需要擊殺的數量愈少。",
"Jika level kamu diatas 51, kamu hanya bisa mengambil War Task ketika berada di Benua Arnos. Kamu sudah tidak bisa mengambil War Task ketika mencapai level 108 karena Monster biasa yang tersisa hanya Slick Worm dan Illusion. Hadiah dari menyelesaikan sebuah War Task adalah Exp dan War Task Points.":
"等級超過 51 之後，只有身在 Arnos 大陸時才接得到戰爭任務。到了 108 級就再也接不到，因為剩下的普通怪物只有 Slick Worm 和 Illusion。完成戰爭任務的獎勵是經驗值與戰爭任務點數。",
"Material Supply": "物資補給（Material Supply）",
"Material Supply adalah sebuah tugas yang diberikan oleh Louie untuk mengumpulkan Material-material dan Mineral dari para Monster. Hadiah dari menyelesaikan sebuah Material Supply adalah Libi dan War Task Points.":
"物資補給是 Louie 發布的委託，內容是從怪物身上蒐集各種素材與礦石。完成物資補給的獎勵是 Libi 與戰爭任務點數。",
"Prestasi War Task": "戰爭任務階級",
"Total Points": "累計點數",
"Student": "學生（Student）",
"Private First Class": "一等兵（Private First Class）",
"Special Forces Team": "特種部隊（Special Forces Team）",
"Elite Army": "精銳部隊（Elite Army）",
"Low Rank Officer": "下級軍官（Low Rank Officer）",
"High Rank Officer": "高級軍官（High Rank Officer）",
"General": "將軍（General）",
"Commander": "司令官（Commander）",
"Hero": "英雄（Hero）",
"War Task Reward": "戰爭任務獎勵",
"Reward": "獎勵",
# ── Weather ────────────────────────────────────────────────────────────────
"Iklim cuaca di akademi Master of Fantasy sangat unik dan setiap tempat memiliki cuaca tertentu. Setiap cuaca mempunyai efek masing-masing yang dapat mempengaruhi status karakter. Misalkan jika turun salju maka kecepatan gerak pada karakter akan menurun atau pada saat hujan tingkat pemulihan (recovery) pada karakter akan berkurang.":
"Master of Fantasy 學院的氣候相當特別，每個地方都有各自的天氣，而每種天氣都有各自的效果，會影響角色的狀態。例如下雪時角色的移動速度會下降，下雨時角色的回復速度會變差。",
"Weather List": "天氣列表",
"Weather Name": "天氣名稱",
"Location": "出現地點",
"Drizzle": "毛毛雨（Drizzle）",
"Raindrops": "落雨（Raindrops）",
"Heavyrain": "大雨（Heavyrain）",
"Sleet": "雨夾雪（Sleet）",
"Snowstorm": "暴風雪（Snowstorm）",
"Snowfall": "降雪（Snowfall）",
"Lightning (Unused)": "閃電（Lightning，未啟用）",
"None": "無",
"-25% HP Regen, +2% Bonus Exp": "HP 回復 -25%、額外經驗值 +2%",
"-50% HP Regen, +4% Bonus Exp": "HP 回復 -50%、額外經驗值 +4%",
"-75% HP Regen, +6% Bonus Exp": "HP 回復 -75%、額外經驗值 +6%",
"-10% Speed of Travel, +3% Bonus Exp": "移動速度 -10%、額外經驗值 +3%",
"-20% Speed of Travel, +6% Bonus Exp": "移動速度 -20%、額外經驗值 +6%",
"-30% Speed of Travel, +9% Bonus Exp": "移動速度 -30%、額外經驗值 +9%",
"BGM music tidak dapat didengar di Ribi Island jika ada cuaca di tempat tersebut kecuali di benua Arnos.":
"在 Ribi Island，只要當地正在出現天氣效果就聽不到背景音樂，Arnos 大陸不受影響。",
}
