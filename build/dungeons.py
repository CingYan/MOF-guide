#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「副本 / 寶箱 / 地圖大師」三頁整理成 docs/data/dungeons.json。

三頁原文是印尼文＋英文專有名詞，這裡翻成台灣正體中文，並把提到的地圖、怪物、
道具、NPC 對回站上既有的 maps.json / monsters.json / items.json / npcs.json，
輸出 mapId / monsterId / itemId / npcId 讓前端互相連結。

對照方式（不是猜的）：
  * 怪物：外部頁面的資料表帶等級、HP、屬性、性格、所在地，先用「等級＋HP」硬條件
    篩，再用屬性、性格、所在地區收斂，最後拿頁面附的韓文原名跟站上中文名對讀
    （例：포쿠링→波庫林、정글 파파고→趴趴犬、해골 주술사→死靈咒術師）確認。
    77 隻全部對上，對照表寫死在 MONSTER 裡，跑的時候會回頭驗 id 還在不在。
  * 站上另有一組「強化○○」怪（J1288–J1319），等級固定落在 30/40/50/60/70/80/
    90/100，剛好就是副本進階／迷宮八組的怪與頭目，順序也一一對得上，另外用
    ENHANCED 記下來。缺號的六隻（J1292/J1294/J1295/J1299/J1309/J1313）站上沒有。
  * 地圖：站上「競技地圖」區的 I0101–I0172 就是這八組副本的房間，依
    普通／無限／眾多／迷宮四段順序對號入座。

可重複執行：只寫 docs/data/dungeons.json 與 docs/img/dungeons/，圖已存在且非空
就不重抓；輸出不含時間戳，跑兩次結果一致。
"""
import json
import os
import pathlib
import re
import subprocess
import time
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT_JSON = DOCS / "data/dungeons.json"
OUT_IMG = DOCS / "img/dungeons"
API = "https://master-of-fantasy.fandom.com/api.php"
TITLES = ["Instant Dungeon", "Treasure Box", "Map Master"]

ILLEGAL = str.maketrans({"/": "／", "\\": "＼", ":": "：", "*": "＊", "?": "？",
                         '"': "＂", "<": "＜", ">": "＞", "|": "｜",
                         "%": "％", "#": "＃"})


# ── 取原文 ────────────────────────────────────────────────────────────────
def curl(url=None, post=None):
    if post is not None:
        tmp = "/tmp/_mofdungeon_post.txt"
        open(tmp, "w").write(post)
        cmd = ["curl", "-sm60", "-X", "POST", "--data-binary", "@" + tmp,
               "-H", "Content-Type: application/x-www-form-urlencoded", API]
    else:
        cmd = ["curl", "-sm60", url]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def fetch_pages():
    post = ("action=query&format=json&prop=revisions&rvprop=content&rvslots=main"
            "&titles=" + "|".join(urllib.parse.quote(t) for t in TITLES))
    data = json.loads(curl(post=post))
    pages = {}
    for p in data["query"]["pages"].values():
        pages[p["title"]] = p["revisions"][0]["slots"]["main"]["*"]
    for t in TITLES:
        assert t in pages, "抓不到頁面：" + t
    return pages


# ── wikitext 小工具 ──────────────────────────────────────────────────────
def plain(s):
    """去掉連結、樣板與 HTML，留下純文字。"""
    s = re.sub(r"\[\[(?:File|Image):[^\]]*\]\]", "", s)
    s = re.sub(r"\[\[([^\]|]*)\|([^\]]*)\]\]", r"\2", s)
    s = re.sub(r"\[\[([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"</?[^>]+>", " ", s)
    s = s.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", s).strip()


def parse_tables(text):
    """回傳 [(headers, rows)]，rows 是每列的儲存格原文字串。"""
    out = []
    for block in re.findall(r"\{\|.*?\n\|\}", text, re.S):
        headers, rows, cur = [], [], None
        for line in block.split("\n")[1:-1]:
            line = line.rstrip()
            if line.startswith("!"):
                headers.append(plain(re.sub(r'^!\s*(scope="[^"]*"\s*\|)?', "", line)))
            elif line.startswith("|-"):
                if cur is not None:
                    rows.append(cur)
                cur = []
            elif line.startswith("|") and cur is not None:
                body = line[1:]
                m = re.match(r'\s*style="[^"]*"\s*\|(.*)', body)
                cur.append((m.group(1) if m else body).strip())
        if cur:
            rows.append(cur)
        out.append((headers, rows))
    return out


def files_in(s):
    return [f.replace(" ", "_") for f in re.findall(r"\[\[File:([^\]|]+)", s)]


# ── 對照表 ────────────────────────────────────────────────────────────────
# 副本怪物／頭目 → monsters.json 的基本型
MONSTER = {
    "Skull Pirates": "J0156", "Phantom Officer": "J0206", "High Pirates": "J0216",
    "Captain Jay Bubble": "J0266", "Poltergeist": "J0171", "Countess": "J0176",
    "Wild Boar": "J0940", "Small Feary": "J0610", "Bumble Bee": "J0271",
    "Dr Kingbo": "J0283", "Demon Deers": "J0615", "Chogals": "J0261",
    "Queen Bee": "J0281", "Fierce Pumpkin Ghost": "J0625", "Red Devil": "J0630",
    "Blue Fire Bead": "J0635", "Evil Candle": "J0620", "Evil Tree": "J0655",
    "Dog Soldier": "J0331", "Blue Rock": "J0364", "Purple Jelly": "J0371",
    "Tree Plank": "J0311", "Dog Captain": "J0341", "Wolf Fighter": "J0413",
    "Wolf Ranger": "J0421", "Little Black Dragon": "J0441", "Black Dragon": "J0451",
    "Wolf General": "J0431", "Fighter Mecas": "J0420", "Harpy": "J0422",
    "Black Skeleton Wheel": "J0465", "Sanchoseu": "J0425", "Queen Harpy": "J0432",
    "Fire Master Jelly": "J0485", "Evil Mask Rabbit": "J0727", "Steel Racoon": "J0728",
    "Steel Cabbage": "J0729", "Lightning Jelly": "J0530", "Black Big Boo": "J0501",
    "Evil Chochas": "J0730", "Ancient Skeleton Warrior": "J0511",
    "Machine Sentinel": "J0690", "Ancient Skeleton Wizard": "J0521",
    "Cactuartu": "J0866", "Skeleton Little Dragon": "J0868", "Skeleton Hand": "J0870",
    "Scorpion Cannon": "J0793", "White Demon Axe": "J0869", "Blaster": "J0791",
    "Grasshopper": "J0794", "Evil Spy Head": "J0760", "Demon Spore": "J0818",
    "Crime Dog": "J0820", "Ware Wolf": "J0822", "Abyss Worm": "J0819",
    "Ancient Totem": "J0821", "Skull Tree Tag": "J0817", "Illusion Jelly": "J0816",
    "Killer Joker": "J0763", "Gunslinger": "J0767", "Armor Of Grief": "J0893",
    "Curse Sword": "J0895", "Bamboo Panda": "J0761", "Brutalizz": "J0891",
    "Joker Warrior": "J0764", "Killer Claw": "J0765", "Ancient Ice Skeleton": "J0892",
    "Executioner": "J0766", "Evil Doll": "J0950", "Dead Plank": "J0952",
    "Black Head": "J0960", "Dark Lord": "J0958", "Ghost Shall": "J0959",
    "Slimy Bucket": "J0963", "Skeleton Fire": "J0954", "Black Wizard": "J0956",
    "Onix": "J0957",
}

# 進階／迷宮副本實際刷出來的「強化型」；站上缺號的六隻不列
ENHANCED = {
    "Wild Boar": "J1288", "Small Feary": "J1289", "Bumble Bee": "J1290",
    "Dog Soldier": "J1291", "Purple Jelly": "J1293", "Black Skeleton Wheel": "J1296",
    "Black Big Boo": "J1297", "Ancient Skeleton Warrior": "J1298", "Blaster": "J1300",
    "Grasshopper": "J1301", "Skeleton Little Dragon": "J1302", "Illusion Jelly": "J1303",
    "Skull Tree Tag": "J1304", "Crime Dog": "J1305", "Joker Warrior": "J1306",
    "Killer Claw": "J1307", "Ancient Ice Skeleton": "J1308", "Black Wizard": "J1310",
    "Onix": "J1311", "Dr Kingbo": "J1312", "Fire Master Jelly": "J1314",
    "Lightning Jelly": "J1315", "Skeleton Hand": "J1316", "Ware Wolf": "J1317",
    "Curse Sword": "J1318", "Dark Lord": "J1319",
}

# 副本房間名 → maps.json（站上「競技地圖」區）
DUNGEON_MAP = {
    # 普通
    "Interior of The Pirate Ship": "I0101", "Ghost Base": "I0102",
    "Dark Dungeon": "I0103", "Assembly Area of Evil's": "I0104",
    "Normal - Volcano Cave": "I0105", "Normal - Dark Grove": "I0106",
    "Normal - Bamboo Grove": "I0107", "Normal - Knowledge Tower": "I0108",
    # 無限
    "Normal - Interior of The Pirate Ship": "I0109", "Normal - Ghost Base": "I0110",
    "Normal - Interior of Volcano Cave": "I0111", "Normal - Interior of Dark Grove": "I0112",
    "Normal - Dark Dungeon": "I0113", "Normal - Assembly Area of Evil's": "I0114",
    "Normal - Interior of Bamboo Grove": "I0115", "Normal - Interior of Knowledge Tower": "I0116",
    # 眾多（Advance）
    "Advance - Intrance of Pirate Ship": "I0117", "Advance - Center of Pirate Ship": "I0118",
    "Advance - Exit of Pirate Ship": "I0119",
    "Advance - Intrance of Ghost Base": "I0120", "Advance - Center of Ghost Base": "I0121",
    "Advance - Exit of Ghost Base": "I0122",
    "Advance - Intrance of Volcano Cave": "I0123", "Advance - Center of Volcano Cave": "I0124",
    "Advance - Exit of Volcano Cave": "I0125",
    "Advance - Intrance of Dark Grove": "I0126", "Advance - Center of Dark Grove": "I0127",
    "Advance - Exit of Dark Grove": "I0128",
    "Advance - Intrance of Dark Dungeon": "I0129", "Advance - Center of Dark Dungeon": "I0130",
    "Advance - Exit of Dark Dungeon": "I0131",
    "Advance - Intrance of Assembly Area of Evil's": "I0132",
    "Advance - Center of Assembly Area of Evil's": "I0133",
    "Advance - Exit of Assembly Area of Evil's": "I0134",
    "Advance - Intrance of Bamboo Grove": "I0135", "Advance - Center of Bamboo Grove": "I0136",
    "Advance - Exit of Bamboo Grove": "I0137",
    "Advance - Intrance of Knowledge Tower": "I0138", "Advance - Center of Knowledge Tower": "I0139",
    "Advance - Exit of Knowledge Tower": "I0140",
    # 迷宮（Maze，原文前綴寫 Extreme）
    "Extreme - Intrance of Pirate Ship": "I0141", "Extreme - Center of Pirate Ship": "I0142",
    "Extreme - Pirate Ship Plaza": "I0143", "Extreme - Exit of Pirate Ship": "I0144",
    "Extreme - Intrance of Ghost Base": "I0145", "Extreme - Center of Ghost Base": "I0146",
    "Extreme - Ghost Base Plaza": "I0147", "Extreme - Exit of Ghost Base": "I0148",
    "Extreme - Intrance of Volcano Cave": "I0149", "Extreme - Center of Volcano Cave": "I0150",
    "Extreme - Volcano Cave Plaza": "I0151", "Extreme - Exit of Volcano Cave": "I0152",
    "Extreme - Intrance of Dark Grove": "I0153", "Extreme - Center of Dark Grove": "I0154",
    "Extreme - Dark Grove Plaza": "I0155", "Extreme - Exit of Dark Grove": "I0156",
    "Extreme - Intrance of Dark Dungeon": "I0157", "Extreme - Center of Dark Dungeon": "I0158",
    "Extreme - Dark Dungeon Plaza": "I0159", "Extreme - Exit of Dark Dungeon": "I0160",
    "Extreme - Intrance of Assembly Area of Evil's": "I0161",
    "Extreme - Center of Assembly Area of Evil's": "I0162",
    "Extreme - Assembly Area of Evil's Plaza": "I0163",
    "Extreme - Exit of Assembly Area of Evil's": "I0164",
    "Extreme - Intrance of Bamboo Grove": "I0165", "Extreme - Center of Bamboo Grove": "I0166",
    "Extreme - Bamboo Grove Plaza": "I0167", "Extreme - Exit of Bamboo Grove": "I0168",
    "Extreme - Intrance of Knowledge Tower": "I0169", "Extreme - Center of Knowledge Tower": "I0170",
    "Extreme - Knowledge Tower Plaza": "I0171", "Extreme - Exit of Knowledge Tower": "I0172",
}

# 地區名 → 站上的區域名
REGION = {
    "Ribi Island": "羅溫克林", "Ribi Town": "利比村莊", "Arnos": "阿諾斯",
    "Poseidon": "普賽以道斯", "Ghost Castle": "幽靈城堡", "Cram Hill": "克雷畢",
    "Dark Hill": "達克比拉", "Dark Tower": "達克比拉", "Volcano Cave": "克雷畢",
    "Coast Cave": "克連烏德", "Glan Wood": "克連烏德", "Goldy Land": "寇帝連",
    "Harlon Castle": "郝代杻", "Bibos Town": "比波司城(town)", "Daren Mine": "羅溫克林",
    "Lawn Green": "羅溫克林", "Hunter Village": "寇帝連", "Bluestar Town": "藍星村莊",
    "West Enpa": "沃斯特炎帕", "North Enpa": "挪思炎帕", "East Enpa": "伊斯特炎帕",
    "Albadia Desert": "寇烏馬丁", "Thousands Tree": "萊斯汀", "Navahorn": "納巴虎任",
    "Ciberian": "派貝倫平原", "Wizard Tower": "魔法師之塔", "Big Woods": "大樹林",
    "Rundwell Fortress": "蘭德韋爾要塞", "Castle of Heaven": "天空之城",
    "Paperon": "派貝倫平原", "West Post": "沃斯特炎帕", "Volcano Post": "克雷畢",
    "North Post": "達克比拉", "Death Valley Post": "寇烏馬丁",
}

# 地名的中文譯名（站上沒有同名地圖時用）
PLACE_ZH = {
    "Ribi Island": "利比島", "Ribi Town": "利比村莊", "Arnos": "阿諾斯",
    "Poseidon": "普賽以道斯", "Ghost Castle": "幽靈城堡", "Cram Hill": "克雷畢",
    "Dark Hill": "達克比拉", "Dark Tower": "黑暗之塔", "Volcano Cave": "火山洞窟",
    "Harlon Castle": "郝代杻", "Bluestar Town": "藍星村莊", "West Enpa": "沃斯特炎帕",
    "North Enpa": "挪思炎帕", "East Enpa": "伊斯特炎帕", "Albadia Desert": "寇烏馬丁",
    "Thousands Tree": "萊斯汀", "Navahorn": "納巴虎任", "Ciberian": "派貝倫平原",
    "Wizard Tower": "魔法師之塔", "Big Woods": "大樹林",
    "Rundwell Fortress": "蘭德韋爾要塞", "West Post": "西部前哨基地",
    "Volcano Post": "火山監視塔", "North Post": "北部前哨地基",
    "Death Valley Post": "馬塔前哨基地", "Paperon": "派貝倫", "Navahorn ": "納巴虎任",
    "Meldives Island": "馬爾地夫",
}

NPC = {  # 副本 NPC → npcs.json；賣鑰匙的流浪商人依所在前哨站分開對
    "Hyde": "N0150", "Dracula": "N0152", "Ted": "N0163",
    "Volcano Guard": "N0105", "North Guard": "N0106", "Captain Guard": "N0195",
    "Merchant@Volcano Post": "N0111", "Merchant@North Post": "N0112",
    "Merchant@Death Valley Post": "N0194",
}
NPC_ZH = {  # 站上查無對應，只留譯名
    "Hyde": "克丁哈以德", "Dracula": "巴泰規拉", "Ted": "泰德",
    "Bruno": "布魯諾", "Zangyi": "贊蓋", "Volcano Guard": "火山警備隊長",
    "North Guard": "北部警備隊長", "Captain Guard": "前哨基地隊長",
    "Sinsia": "辛西亞", "Heidi": "海蒂", "Rosy": "羅西", "Merchant": "流浪商人",
}

# 副本組別（依原文表的 Key Name 命名）
GROUP_ZH = {
    "Pirates": "海賊船", "Ghost Castle": "鬼城堡", "Volcano Cave": "火山洞窟",
    "Dark Grove": "暗黑樹林", "Dark Tower": "黑暗之塔", "Evil Base": "魔族集結地",
    "Bamboo Grove": "竹林", "Knowledge Tower": "知識之塔",
}
TYPE_ZH = {"Normal": "普通", "Infinite": "無限", "Advance": "眾多", "Maze": "迷宮"}
TYPE_KEY = {"Normal": "normal", "Infinite": "infinite", "Advance": "advance", "Maze": "maze"}

# 寶箱
BOX = {
    "Bronze Treasure Box": ("青銅寶物箱子", ["J2000"]),
    "Silver Treasure Box": ("銀寶物箱子", ["J2001"]),
    "Gold Treasure Box": ("黃金寶石箱子", ["J2002"]),
    "Gem Treasure Box": ("寶石箱子", ["J2003"]),
    "Extreme Gem Treasure Box": ("高級寶石箱子", ["J2004"]),
    "Ralph Treasure Box": ("拉爾夫寶箱", []),
    "Runpei Treasure Box": ("倫佩寶箱", []),
    "Bydert Treasure Box": ("拜德爾特寶箱", []),
    "Cenacia Treasure Box": ("賽納西亞寶箱", []),
    "Alucard Treasure Box": ("魯茲博特寶箱", []),
    "Gold Wedding Box": ("黃金婚禮箱", ["J2011", "J2012"]),
    "Diamond Wedding Box": ("鑽石婚禮箱", ["J2010"]),
}

# 寶箱掉落物 → items.json；值是 None 代表站上查無同名道具
ITEM = {
    "Intermediate Resume Syrup": "I0013", "Intermediate Mana Syrup": "I0016",
    "Restitution": "I0504", "Instant Move": "I0107",
    "Attacks Syrup": "I0019", "Attack Syrup": "I0019", "Intelligence Syrup": "I0022",
    "High Resume Syrup": "I0014", "High Mana Syrup": "I0017",
    "Huge Resume Syrup": "I0023", "Huge Mana Syrup": "I0024",
    "Sealed Water Stone": "I0666", "Sealed Silver Stone": "I0667",
    "Sealed Gold Stone": "I0668", "Sealed Ruby Stone": "I0755",
    "Sealed Diamond Stone": None, "Speed Potion": "I0083",
    "Experience 100% (1D)": "I0908", "Libi 100% (1D)": "I0913",
    # 十二種氣象魔術，站上是 I0937–I0948 這一組（(CH) 版），依原文列出的順序對號
    "Snow Falling (CH)": "I0937", "Love Aura (CH)": "I0938",
    "Gold Coin Rain (CH)": "I0939", "Popo Rain Magic (CH)": "I0940",
    "HP Rain Magic (CH)": "I0941", "MP Rain Magic (CH)": "I0942",
    "Frozen Rain (CH)": "I0943", "Red Rose (CH)": "I0944",
    "Rainbow Arrow (CH)": "I0945", "Bubble Rain (CH)": "I0946",
    "Rainbow Candy Weather Magic (CH)": "I0947", "Boom Rain (CH)": "I0948",
}
ITEM_ZH = {"Sealed Diamond Stone": "已封印的鑽石"}

# 要抓下來的圖：外部檔名 → 站上檔名（中文）
ICON = {
    "Instant_Dungeon_Key_(Ribi).png": "副本鑰匙-利比島.png",
    "Instant_Dungeon_Key_(Arnos).png": "副本鑰匙-阿諾斯.png",
    "Bronze_Treasure_Box.gif": "青銅寶物箱子.gif",
    "Silver_Treasure_Box.gif": "銀寶物箱子.gif",
    "Gold_Treasure_Box.gif": "黃金寶石箱子.gif",
    "Gem_Treasure_Box.gif": "寶石箱子.gif",
    "Extreme_Gem_Treasure_Box.gif": "高級寶石箱子.gif",
    "Gold_Wedding_Box.gif": "黃金婚禮箱.gif",
    "Diamond_Wedding_Box.gif": "鑽石婚禮箱.gif",
}

MAP_LAYOUT_ZH = {  # 畫廊列出的房間底圖，對到站上的原始地圖
    "Poseidon_-_Captain's_Cabin.png": "E1010",
    "Poseidon_-_Kitchen.png": "E1006",
    "Ghost_Castle_-_Bedroom.png": "G0005",
    "Ghost_Castle_-_Center_Hall.png": "G0003",
    "Ghost_Castle_-_Reception_Room.png": "G0004",
    "Volcano_Cave_-_Volcano_Cave_1F.png": "D0020",
    "Volcano_Cave_-_Volcano_Cave_2F.png": "D0021",
    "Dark_Hill_-_Dark_Forest_1.png": "M0068",
    "Dark_Hill_-_Dark_Forest_2.png": "M0069",
    "Dark_Tower_-_Dark_Tower_Top.png": "D0045",
    "Dark_Tower_-_Dark_Tower_1F.png": "D0031",
    "Dark_Tower_-_Dark_Tower_1F_Step.png": "D0032",
    "West_Enpa_-_Bluestar_Hunter_Hovel.png": "C0006",
    "West_Enpa_-_Bluestar_Seashore_Hill_(Dungeon).png": "C0003",
    "Wizard_Tower_-_The_Dark_Lord_Throne.png": "U0011",
    "Navahorn_-_Center_of_Bamboo_Grove.png": "C0027",
    "Navahorn_-_Exit_of_Bamboo_Grove.png": "C0028",
}

SPAWN_NOTE = {
    "Spawn sebanyak dua kali di ruangan dungeon yang berbeda":
        "在兩個不同的副本房間各出現一次",
}

# ── 譯文（原文為印尼文，逐段翻成台灣正體中文）────────────────────────────
DUNGEON_INTRO = [
    "副本（韓文 인스턴스던전，Instance Dungeon）是只有使用副本鑰匙才能進去的地下城。",
    "副本一次只持續一小時，時間到就會自動被送出副本；也可以按畫面中央的 Exit 鍵自行離開。",
    "副本是練等效率最高的地方，同時也是找稀有武器的好去處。",
    "和使用副本鑰匙的人待在同一張地圖上的隊伍成員，都會一起被帶進副本。",
]
TYPE_DESC = {
    "Normal": "把場上的怪物全部清光，離開副本的傳送門才會出現。",
    "Infinite": "怪物會無限湧出，擊敗頭目才會出現離開副本的傳送門。",
    "Advance": "清光一個區域的怪物後會開啟通往下一個區域的傳送門，重複同樣的流程直到"
               "開出通往頭目區的傳送門；把頭目與所有怪物都打倒後，離開副本的傳送門才會出現。",
    "Maze": "規則與眾多相同，但清光一個區域的怪物後會同時出現兩個傳送門。選門要小心，"
            "有可能被送回第一個區域或先前走過的區域。",
}
DUNGEON_TRIVIA = ["循環副本與強化副本沿用副本「眾多」型的架構。"]

BOX_INTRO = [
    "冒險途中會遇到寶箱，打破後可以拿到藥水、移動卷軸、礦石、封印石與商城道具等物品。",
    "被打破的寶箱會在數小時後重新出現。",
    "婚禮箱打破後會立刻重生，但最多只重生四次。",
    "和怪物一樣，遊戲管理員（GM）可以在任何地方召喚各種寶箱，安全區域也不例外；"
    "由 GM 召喚出來的寶箱一律不會重生。",
]

MAP_MASTER = {
    "name": "地圖大師",
    "en": "Map Master",
    "summary": "地圖大師是某張地圖的持有者。設有地圖大師的區域，小地圖上方會出現皇冠標誌與 Top 字樣。",
    "howTo": [
        "點小地圖上方的皇冠標誌，選「挑戰」即可報名。",
        "按畫面中央的 Start 鍵開始地圖大師挑戰。",
        "從開始挑戰的那張地圖起，你有兩小時的時間在原地打怪。",
        "按下 Pause 鍵或離開該地圖時，挑戰計時會停止。",
        "挑戰期間累積的經驗值越多越有利，經驗值總量最高的人獲勝。",
    ],
    "rules": [
        "挑戰期間，雙倍經驗值道具、部分徽章與「克魯諾的祝福」技能的效果都不會計入挑戰的經驗值總量。",
        "當你的經驗值總量超過前一任地圖大師，或該地點原本還沒有地圖大師時，你的角色就會成為地圖大師。",
        "成為某地的地圖大師後，在該地打怪可以提升怪物給的經驗值、Libi 與掉寶率。",
        "有報名地圖大師挑戰的玩家也會拿到經驗值、Libi 與掉寶加成，但幅度比地圖大師小。",
        "挑戰結束後要等結算：結果從星期三到星期一，每天早上 07:00 更新。",
        "地圖大師的結果每星期二早上 07:00 重置。",
    ],
    "excludedFromExp": [
        {"name": "雙倍經驗值道具", "en": "Double Experience"},
        {"name": "部分徽章", "en": "Badge"},
        {"name": "克魯諾的祝福", "en": "Cruno's Blessing", "icon": "img/skills/Cruno's Blessing.png"},
    ],
    "example": {"name": "蜿蜒釣魚台", "en": "Fishing Place of Horn",
                "note": "納巴虎任境內設有地圖大師挑戰的地點之一。",
                "mapIds": ["C0020", "C0021", "C0022"]},
    "locations": ["North Enpa", "Albadia Desert", "East Enpa",
                  "Thousands Tree", "Navahorn", "Ciberian"],
}

# 站上有、副本頁沒列出來的房間（記下來免得看起來「少了」）
#
# 主名一律用站上實際的房間名稱。副本頁的 Trivia 只寫了一句「Circle Dungeon
# 與 Extreme Dungeon 沿用進階（眾多）格式」，沒有指名對應哪一組房間，所以
# 那兩個英文名是對照推測，不是原文寫明的對應關係，用 guess 欄位標開。
# 「強化」那組名稱本身就對得上 Extreme，可信度比另一組高。
EXTRA_TYPES = [
    {"name": "眾多副本（第二組）", "typeKey": "advance2",
     "mapIdRange": ["I0173", "I0196"],
     "guess": "Circle Dungeon",
     "note": "站上有第二組「眾多」房間（I0173–I0196），八組、每組三間，"
             "架構與副本頁列出的眾多型相同，但副本頁沒有列。"
             "Trivia 提到的 Circle Dungeon 可能是它，名稱對不上，僅為推測。"},
    {"name": "強化副本", "typeKey": "extreme",
     "mapIdRange": ["I0197", "I0220"],
     "guess": "Extreme Dungeon",
     "note": "站上有一組「強化」房間（I0197–I0220），八組、每組三間，"
             "架構與眾多型相同，但副本頁沒有列。名稱對得上 Trivia 的 "
             "Extreme Dungeon。注意副本頁「迷宮」型的房間前綴也寫 Extreme，"
             "那是另一回事，不要混。"},
]


# ── 站上既有資料 ──────────────────────────────────────────────────────────
def load(name):
    return json.loads((DOCS / "data" / (name + ".json")).read_text("utf-8"))


MAPS = {m["id"]: m for m in load("maps")}
MONS = {m["id"]: m for m in load("monsters")}
NPCS = {n["id"]: n for n in load("npcs")}
ITEMS = {}
for _i in load("items"):
    ITEMS.setdefault(_i["id"], _i)


def ref_map(mid):
    m = MAPS.get(mid)
    if not m:
        return None
    out = {"mapId": mid, "name": m["name"]}
    if m.get("minimap"):
        out["minimap"] = m["minimap"]
    return out


def ref_mon(mid):
    m = MONS.get(mid)
    if not m:
        return None
    out = {"monsterId": mid, "name": m["name"], "level": m["level"], "hp": m["hp"]}
    if m.get("icon"):
        out["icon"] = m["icon"]
    return out


def ref_item(iid):
    it = ITEMS.get(iid)
    if not it:
        return None
    out = {"itemId": iid, "name": it["name"]}
    if it.get("icon"):
        out["icon"] = it["icon"]
    return out


# ── 圖 ───────────────────────────────────────────────────────────────────
MAGIC = [(b"\x89PNG\r\n\x1a\n", ".png"), (b"GIF87a", ".gif"), (b"GIF89a", ".gif"),
         (b"\xff\xd8\xff", ".jpg")]


def image_ext(path):
    """看檔頭認格式；認不出來回 None（檔案不完整或不是圖）。"""
    head = path.read_bytes()[:16]
    for sig, ext in MAGIC:
        if head.startswith(sig):
            return ext
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return None


def fetch_icons(names):
    """外部檔名 → 站上路徑；抓不到或檔頭不對就不放進結果。"""
    urls = {}
    names = sorted(set(names))
    for i in range(0, len(names), 50):
        q = "|".join("File:" + n for n in names[i:i + 50])
        u = f"{API}?action=query&format=json&prop=imageinfo&iiprop=url&titles=" + \
            urllib.parse.quote(q)
        try:
            data = json.loads(curl(url=u))
        except Exception:
            continue
        for p in data.get("query", {}).get("pages", {}).values():
            info = p.get("imageinfo")
            if info:
                urls[p["title"][len("File:"):].replace(" ", "_")] = info[0]["url"]
        time.sleep(0.4)

    OUT_IMG.mkdir(parents=True, exist_ok=True)
    got, cached, missing = 0, 0, []
    result = {}
    for src in names:
        want = ICON[src].translate(ILLEGAL)
        dst = OUT_IMG / want
        # 已經有、非空、而且檔頭跟副檔名對得上，就不重抓
        if dst.exists() and dst.stat().st_size > 0 and image_ext(dst) == dst.suffix:
            cached += 1
            result[src] = "img/dungeons/" + dst.name
            continue
        url = urls.get(src)
        if not url:
            missing.append(src)
            continue
        # 圖床預設會轉成 WebP，加 format=original 才拿得到原檔
        url += ("&" if "?" in url else "?") + "format=original"
        tmp = OUT_IMG / (".tmp_" + str(abs(hash(src)) % 10 ** 8))
        subprocess.run(["curl", "-sfLm60", "-o", str(tmp), url], check=False)
        if not tmp.exists() or tmp.stat().st_size == 0:
            tmp.unlink(missing_ok=True)
            missing.append(src)
            continue
        ext = image_ext(tmp)
        if ext is None:                       # 不是認得的圖檔格式，寧可不寫
            tmp.unlink(missing_ok=True)
            missing.append(src)
            continue
        dst = OUT_IMG / (want[:-len(dst.suffix)] + ext)
        tmp.replace(dst)
        got += 1
        time.sleep(0.3)
        result[src] = "img/dungeons/" + dst.name
    print(f"圖示：新下載 {got}、已存在 {cached}、抓不到 {len(missing)}"
          + (" -> " + ", ".join(missing) if missing else ""))
    return result


# ── 副本頁 ───────────────────────────────────────────────────────────────
MON_RE = re.compile(
    r"(?:\[\[)?([A-Za-z][A-Za-z0-9'\- ]*?)(?:\]\])?\s*\((Limitless|\d+)\s*(?:Monster)?\)"
    r"(?:\s*\(([^)]*)\))?")


def parse_monster_cell(cell):
    out = []
    for name, count, note in MON_RE.findall(cell):
        name = name.strip(" ,")
        entry = {"en": name}
        base = MONSTER.get(name)
        if base and ref_mon(base):
            entry.update(ref_mon(base))
        if count == "Limitless":
            entry["unlimited"] = True
            entry["countLabel"] = "無限"
        else:
            entry["count"] = int(count)
            entry["countLabel"] = f"{count} 隻"
        if note:
            entry["note"] = SPAWN_NOTE.get(note.strip(), note.strip())
        out.append(entry)
    return out


def parse_boss_cell(cell):
    name = plain(cell).strip()
    if not name:
        return None
    entry = {"en": name}
    base = MONSTER.get(name)
    if base and ref_mon(base):
        entry.update(ref_mon(base))
    return entry


def parse_dungeons(text, icons):
    body = text.split("==Instant Dungeon List==", 1)[1].split("==Gallery==", 1)[0]
    layouts = parse_layout_gallery(text)

    groups = []
    continent = None
    # 依大陸標題切段，段內再依每個 *NPC: 區塊切
    parts = re.split(r"\n===\s*'''\[\[([^\]]+)\]\]'''\s*===\n", body)
    for idx in range(1, len(parts), 2):
        continent = parts[idx]
        chunk = parts[idx + 1]
        for blk in re.split(r"\n(?=\*NPC:)", chunk):
            if not blk.lstrip().startswith("*NPC:"):
                continue
            meta = {}
            for k, v in re.findall(r"^\*([A-Za-z ]+):\s*(.*)$", blk, re.M):
                meta[k.strip()] = v.strip()
            tables = parse_tables(blk)
            if not tables:
                continue
            headers, rows = tables[0]
            groups.append(build_group(continent, meta, headers, rows, icons, layouts))
    return groups


def link_name(s):
    m = re.match(r"\[\[([^\]|]+)", s or "")
    return m.group(1) if m else (plain(s or "") or None)


def place_ref(en):
    if not en:
        return None
    out = {"en": en, "name": PLACE_ZH.get(en, en)}
    if REGION.get(en):
        out["region"] = REGION[en]
    return out


def build_group(continent, meta, headers, rows, icons, layouts):
    col = {h: i for i, h in enumerate(headers)}
    runs = []
    key_icon = None
    for r in rows:
        if len(r) < len(headers):
            continue
        key_name = plain(r[col["Key Name"]])
        for f in files_in(r[col["Image"]]):
            if f in icons:
                key_icon = icons[f]
        # 型態由 Key Name 的前綴決定
        typ = "Normal"
        base = key_name
        for pre in ("Infinite", "Advance", "Maze"):
            if key_name.startswith(pre + " "):
                typ, base = pre, key_name[len(pre) + 1:]
                break
        maps = []
        for nm in [x.strip() for x in plain(r[col["Dungeon Map Name"]]).split(",")]:
            if not nm:
                continue
            entry = {"en": nm}
            mid = DUNGEON_MAP.get(nm)
            ref = ref_map(mid) if mid else None
            if ref:
                entry.update(ref)
            maps.append(entry)
        mons = parse_monster_cell(r[col["Monster List"]])
        if typ in ("Advance", "Maze"):
            for mo in mons:
                eid = ENHANCED.get(mo["en"])
                if eid and ref_mon(eid):
                    e = ref_mon(eid)
                    mo["enhanced"] = {"monsterId": e["monsterId"], "name": e["name"],
                                      "level": e["level"], "hp": e["hp"]}
        boss = parse_boss_cell(r[col["Boss/Mini-Boss"]])
        if boss and typ in ("Advance", "Maze"):
            eid = ENHANCED.get(boss["en"])
            if eid and ref_mon(eid):
                e = ref_mon(eid)
                boss["enhanced"] = {"monsterId": e["monsterId"], "name": e["name"],
                                    "level": e["level"], "hp": e["hp"]}
        runs.append({
            "type": TYPE_KEY[typ], "typeName": TYPE_ZH[typ], "typeEn": typ,
            "keyName": {"en": key_name,
                        "name": (TYPE_ZH[typ] if typ != "Normal" else "") + GROUP_ZH.get(base, base)},
            "maps": maps, "monsters": mons, "boss": boss,
        })

    base_en = runs[0]["keyName"]["en"] if runs else ""
    npc_en = link_name(meta.get("NPC"))
    key_raw = meta.get("Dungeon Key", "")
    key_where = re.search(r"\(\s*(?:\[\[)?([^\]\)]+?)(?:\]\])?\s*\)", key_raw)
    key_en = link_name(key_raw.split("(")[0])
    layout_en = link_name(meta.get("Map Layout"))

    npc = {"en": npc_en, "name": NPC_ZH.get(npc_en, npc_en)} if npc_en else None
    if npc and NPC.get(npc_en) and NPCS.get(NPC[npc_en]):
        npc["npcId"] = NPC[npc_en]
        npc["name"] = NPCS[NPC[npc_en]]["name"]
        if NPCS[NPC[npc_en]].get("icon"):
            npc["icon"] = NPCS[NPC[npc_en]]["icon"]

    key_npc = {"en": key_en, "name": NPC_ZH.get(key_en, key_en)} if key_en else None
    if key_npc and key_where:
        post = key_where.group(1).strip()
        key_npc["at"] = place_ref(post)
        nid = NPC.get(key_en + "@" + post)
        if nid and NPCS.get(nid):
            key_npc["npcId"] = nid
            key_npc["name"] = NPCS[nid]["name"]
            if NPCS[nid].get("icon"):
                key_npc["icon"] = NPCS[nid]["icon"]

    group = {
        "id": base_en.lower().replace(" ", "-"),
        "name": GROUP_ZH.get(base_en, base_en),
        "en": base_en,
        "continent": place_ref(continent),
        "npc": npc,
        "location": place_ref(link_name(meta.get("Location"))),
        "dungeonKeyFrom": key_npc,
        "mapLayout": place_ref(layout_en),
        "bgm": [{"file": f, "label": lab or None} for f, lab in
                re.findall(r"\[\[File:([^\]|]+)(?:\|([^\]]*))?\]\]", meta.get("BGM", ""))],
        "ambient": [{"file": f} for f in files_in(meta.get("Ambient", ""))],
        "runs": runs,
    }
    if key_icon:
        group["dungeonKeyIcon"] = key_icon
    lay = layouts.get(base_en)
    if lay:
        group["roomLayouts"] = lay
    return group


def parse_layout_gallery(text):
    """Gallery 的 Map Layout：每張底圖對應到哪些副本房間。"""
    sec = text.split("===Map Layout===", 1)
    if len(sec) < 2:
        return {}
    sec = sec[1].split("===Screenshot===", 1)[0]
    out = {}
    for name, gal in re.findall(r"====\s*'''([^']+)'''\s*====\s*\n<gallery>(.*?)</gallery>",
                                sec, re.S):
        rows = []
        for line in gal.strip().split("\n"):
            if "|" not in line:
                continue
            f, caption = line.split("|", 1)
            f = f.strip().replace(" ", "_")
            rooms = []
            for nm in [x.strip() for x in caption.split(",")]:
                if not nm:
                    continue
                ref = ref_map(DUNGEON_MAP.get(nm)) if DUNGEON_MAP.get(nm) else None
                rooms.append(dict({"en": nm}, **(ref or {})))
            row = {"file": f, "rooms": rooms}
            src = MAP_LAYOUT_ZH.get(f)
            if src and ref_map(src):
                row["sourceMap"] = ref_map(src)
            rows.append(row)
        out[name] = rows
    return out


# ── 寶箱頁 ───────────────────────────────────────────────────────────────
DROP_RE = re.compile(r"X(\d+)\s*(?:\[\[File:([^\]|]+)\]\])?\s*([^<\n]+)")


def parse_boxes(text, icons):
    headers, rows = parse_tables(text)[0]
    col = {h: i for i, h in enumerate(headers)}
    out = []
    for r in rows:
        en = plain(r[col["Treasure Name"]])
        zh, ids = BOX.get(en, (en, []))
        box = {"en": en, "name": zh}
        for f in files_in(r[col["Image"]]):
            if f in icons:
                box["icon"] = icons[f]
        hp = plain(r[col["Health"]])
        if hp:
            box["healthText"] = hp
        box["locations"] = [place_ref(x.strip()) for x in
                            re.split(r",\s*", plain(r[col["Location"]])) if x.strip()]
        drops = []
        for cnt, _f, nm in DROP_RE.findall(r[col["Item Drop"]].replace("<br />", "\n")):
            nm = plain(nm).strip()
            if not nm:
                continue
            d = {"en": nm, "count": int(cnt)}
            iid = ITEM.get(nm)
            ref = ref_item(iid) if iid else None
            if ref:
                d.update(ref)
            elif nm in ITEM_ZH:
                d["name"] = ITEM_ZH[nm]
            drops.append(d)
        box["drops"] = drops
        cur = []
        for mid in ids:
            m = MONS.get(mid)
            if not m:
                continue
            cur.append({
                "monsterId": mid, "name": m["name"], "hp": m["hp"],
                "maps": [dict({"mapId": x["id"]}, name=x["name"],
                              region=MAPS.get(x["id"], {}).get("region"))
                         for x in m.get("maps", [])],
                "drops": [{"itemId": d.get("id"), "name": d["name"],
                           "icon": d.get("icon"), "min": d.get("min"),
                           "max": d.get("max"), "rate": d.get("rate")}
                          for d in m.get("drops", [])],
            })
        if cur:
            box["current"] = cur
        out.append(box)
    return out


# ── 主流程 ───────────────────────────────────────────────────────────────
def main():
    pages = fetch_pages()
    icons = fetch_icons(list(ICON))

    dungeons = parse_dungeons(pages["Instant Dungeon"], icons)
    boxes = parse_boxes(pages["Treasure Box"], icons)

    mm = dict(MAP_MASTER)
    mm["locations"] = [place_ref(x) for x in MAP_MASTER["locations"]]

    data = {
        "dungeons": {
            "name": "副本", "en": "Instant Dungeon",
            "intro": DUNGEON_INTRO,
            "types": [{"key": TYPE_KEY[k], "name": TYPE_ZH[k], "en": k, "goal": TYPE_DESC[k]}
                      for k in ("Normal", "Infinite", "Advance", "Maze")],
            "entry": {"requires": "副本鑰匙", "requiresEn": "Instant Dungeon Key",
                      "durationMinutes": 60,
                      "note": "沒有等級門檻的紀錄；進場條件只有持有對應的副本鑰匙。"},
            "groups": dungeons,
            "otherTypes": EXTRA_TYPES,
            "trivia": DUNGEON_TRIVIA,
        },
        "treasureBoxes": {
            "name": "寶箱", "en": "Treasure Box",
            "intro": BOX_INTRO,
            "boxes": boxes,
        },
        "mapMaster": mm,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", "utf-8")

    runs = sum(len(g["runs"]) for g in dungeons)
    hit = sum(1 for g in dungeons for r in g["runs"]
              for m in r["monsters"] if m.get("monsterId"))
    tot = sum(1 for g in dungeons for r in g["runs"] for m in r["monsters"])
    mp = sum(1 for g in dungeons for r in g["runs"] for m in r["maps"] if m.get("mapId"))
    mpt = sum(1 for g in dungeons for r in g["runs"] for m in r["maps"])
    it = sum(1 for b in boxes for d in b["drops"] if d.get("itemId"))
    itt = sum(1 for b in boxes for d in b["drops"])
    print(f"副本 {len(dungeons)} 組 / {runs} 種鑰匙；怪物對照 {hit}/{tot}；房間對照 {mp}/{mpt}")
    print(f"寶箱 {len(boxes)} 種；掉落物對照 {it}/{itt}")
    print(f"地圖大師 1 篇；挑戰地點 {len(mm['locations'])} 處")
    print("輸出 ->", OUT_JSON.relative_to(ROOT), f"({OUT_JSON.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
