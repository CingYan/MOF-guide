#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把角色數值、狀態異常兩頁 wiki 整理成 docs/data/character.json，並抓對應圖示。

來源頁面（MediaWiki API，prop=revisions）：
    Player Character  角色建立、能力值、能力點、經驗表、能量條、師徒制度……
    Status Effect     定身／暈眩／冰凍三種狀態異常，以及會造成狀態的怪物、徽章、技能
    Attribute         屬性相剋——整頁內容與 docs/data/wiki.json 的 matrix / monAttrs
                      完全重複（六種武器屬性、八種怪物屬性、相剋加減），故不收錄，
                      避免同一份資料在站上出現兩次。

翻譯：原文是印尼文，這裡用固定對照表逐條翻成台灣正體中文，不在建置時呼叫任何
翻譯服務，所以同樣的 wiki 內容跑幾次結果都一樣（md5 相同）。對照表以「原文字串」
當 key，wiki 改字就會查不到，此時保留原文並在最後印出未翻譯清單，不會靜默瞎掰。

名詞沿用 build/wiki_i18n.py 與 build/skill_names.py 既有的譯法（定身／暈眩／冰凍、
力量／敏捷／智力、鬥士／劍聖……），技能中文名直接取 docs/data/wiki.json 已驗證過的
en -> name 對照，怪物中文名取 docs/data/monsters.json（用等級＋地區驗證後才套用）。

數字一律照原文，只把印尼式千分位句點換成逗號（1.215 -> 1,215），不做任何換算。

圖示：把頁面裡的 [[File:xxx.png]] 透過 imageinfo 取得網址後下載到 docs/img/character/，
用中文名命名；下載後檢查檔案存在且非 0 位元組，抓不到就不寫 icon 欄位。已存在且
非空的檔案不重抓，可重複執行。頁面裡的遊戲畫面截圖（.jpg thumb）不屬於圖示，略過。

用法：
    python3 build/character.py            # 產生 docs/data/character.json
    python3 build/character.py --dump      # 只印出目前查不到翻譯的原文字串
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(ROOT, 'docs', 'data', 'character.json')
IMG_DIR = os.path.join(ROOT, 'docs', 'img', 'character')
WIKI_JSON = os.path.join(ROOT, 'docs', 'data', 'wiki.json')
MONSTERS_JSON = os.path.join(ROOT, 'docs', 'data', 'monsters.json')
API = 'https://master-of-fantasy.fandom.com/api.php'
TITLES = ['Player Character', 'Status Effect', 'Attribute']

ILLEGAL = str.maketrans({'/': '／', '\\': '＼', ':': '：', '*': '＊', '?': '？',
                         '"': '＂', '<': '＜', '>': '＞', '|': '｜',
                         '%': '％', '#': '＃'})

MISSING = []          # 查不到翻譯的原文，最後統一印出


# ── wiki API ────────────────────────────────────────────────────────────────
def curl(url=None, post=None):
    if post is not None:
        tmp = '/tmp/_mofchar_post.txt'
        with open(tmp, 'w', encoding='utf-8') as fh:
            fh.write(post)
        cmd = ['curl', '-s', '-m', '60', '-X', 'POST', '--data-binary', '@' + tmp,
               '-H', 'Content-Type: application/x-www-form-urlencoded', API]
    else:
        cmd = ['curl', '-s', '-m', '60', url]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def fetch_pages(titles):
    post = ('action=query&format=json&prop=revisions&rvprop=content&rvslots=main'
            '&titles=' + urllib.parse.quote('|'.join(titles), safe='|'))
    data = json.loads(curl(post=post))
    out = {}
    for page in data['query']['pages'].values():
        if 'revisions' in page:
            out[page['title']] = page['revisions'][0]['slots']['main']['*']
    for t in titles:
        if t not in out:
            sys.exit(f'抓不到頁面：{t}')
    return out


# ── wikitext 基本處理 ────────────────────────────────────────────────────────
FILE_RE = re.compile(r'\[\[File:([^\]|]+)((?:\|[^\]]*)?)\]\]', re.I)
SIZE_RE = re.compile(r'^\d+px$|^thumb$|^right$|^left$|^center$|^frame$|^border$', re.I)


def take_files(text):
    """抽出 [[File:...]]，回傳 (剩下的文字, [{'file','caption','link'}...])。"""
    files = []

    def sub(m):
        params = [p.strip() for p in m.group(2).split('|') if p.strip()]
        caption, link = '', ''
        for p in params:
            if p.lower().startswith('link='):
                link = p.split('=', 1)[1].strip()
            elif '=' not in p and not SIZE_RE.match(p):
                caption = caption or p
        files.append({'file': m.group(1).strip().replace(' ', '_'),
                      'caption': caption, 'link': link})
        return ''

    return FILE_RE.sub(sub, text), files


def plain(text):
    """把 wiki 標記清成純文字。"""
    text = re.sub(r'\[\[[^\]|]+\|([^\]]+)\]\]', r'\1', text)
    text = re.sub(r'\[\[([^\]|]+)\]\]', r'\1', text)
    text = text.replace("'''", '').replace("''", '')
    text = re.sub(r'<br\s*/?>', ' ', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ')
    return re.sub(r'\s+', ' ', text).strip()


def cell(raw):
    """單一表格欄位 -> {'text', 'files'}，先把 style="..."| 這種屬性前綴切掉。"""
    if '|' in raw:
        left, right = raw.split('|', 1)
        if '=' in left and '[[' not in left:
            raw = right
    body, files = take_files(raw)
    return {'text': plain(body), 'files': files}


def parse_tables(text):
    tables = []
    for m in re.finditer(r'\{\|(.*?)\n\|\}', text, re.S):
        headers, rows, cur = [], [], None
        for line in m.group(1).split('\n'):
            line = line.rstrip()
            if line.startswith('|-'):
                if cur:
                    rows.append(cur)
                cur = []
            elif line.startswith('!'):
                headers.append(cell(line[1:]))
            elif line.startswith('|'):
                if cur is None:
                    cur = []
                cur.append(cell(line[1:]))
        if cur:
            rows.append(cur)
        tables.append({'headers': headers, 'rows': [r for r in rows if r]})
    return tables


HEAD_RE = re.compile(r'^(={2,4})\s*(.*?)\s*\1\s*$')


def split_sections(text):
    """回傳 [{'title','level','body'}]，第一段（前言）title 為 ''。"""
    out, title, level, buf = [], '', 0, []
    for line in text.split('\n'):
        m = HEAD_RE.match(line.strip())
        if m:
            out.append({'title': title, 'level': level, 'body': '\n'.join(buf)})
            title = plain(m.group(2))
            level = len(m.group(1))
            buf = []
        else:
            buf.append(line)
    out.append({'title': title, 'level': level, 'body': '\n'.join(buf)})
    return out


def bullets(body):
    """取出最上層的 * 項目（原文，保留 ''' 粗體以便切標題）。"""
    out = []
    for line in body.split('\n'):
        s = line.strip()
        if s.startswith('*') and not s.startswith('**'):
            out.append(s[1:].strip())
    return out


def blocks(body):
    """把「引言 + 底下的 * 項目」綁在一起，回傳 [(引言, [項目...])]。"""
    out, title, items = [], '', []
    for line in body.split('\n'):
        s = line.strip()
        if s.startswith('*') and not s.startswith('**'):
            items.append(plain(take_files(s[1:])[0]))
            continue
        if s.startswith(('{|', '|', '!', '[[Category:', '<gallery', '</gallery')) or not s:
            continue
        if title or items:
            out.append((title, items))
        title, items = plain(take_files(s)[0]), []
    if title or items:
        out.append((title, items))
    return [(t, i) for t, i in out if t or i]


def paragraphs(body):
    """取出一般段落（略過表格、清單、圖片、分類）。"""
    out, skip = [], False
    for line in body.split('\n'):
        s = line.strip()
        if s.startswith('{|'):
            skip = True
        if skip:
            if s.startswith('|}'):
                skip = False
            continue
        if not s or s.startswith(('*', '|', '!', '[[Category:', '<gallery', '</gallery')):
            continue
        s = plain(take_files(s)[0])
        if not s:
            continue
        out.append(s)
    return out


NUM_RE = re.compile(r'(?<![\d.])(\d{1,3}(?:\.\d{3})+)(?![\d.])')


def numfix(s):
    """印尼式千分位句點 -> 逗號（1.215 -> 1,215）；數值本身不動。"""
    return NUM_RE.sub(lambda m: m.group(1).replace('.', ','), s)


# ── 對照表 ─────────────────────────────────────────────────────────────────
# 短語／欄位／固定名詞，沿用 build/wiki_i18n.py 的譯法
TERM = {
    'Image': '圖示', 'Monster': '怪物', 'Status': '狀態',
    'Badge Name': '徽章名稱', 'Skill Name': '技能名稱', 'Skill': '技能',
    'Job': '職業', 'Type': '類型', 'Fashion Name': '時裝名稱',
    'Level': '等級', 'Level Up': '升級', 'Level Up Exp': '升級所需經驗',
    'Total Status Points': '能力點總數', 'Need Points': '所需點數',
    'Bonus Libi': 'Libi 獎勵', '1 Month Login Bonus': '連續登入 1 個月獎勵',
    'Damage': '傷害', 'Skill Damage': '技能傷害', 'Job Requirement': '職業需求',
    'Active': '主動', 'Passive': '被動', 'None': '無',
    'Stop': '定身', 'Stun': '暈眩', 'Freeze': '冰凍',
    # 職業（wiki_i18n.py 既有譯法）
    'Fighter': '劍士', 'Archer': '弓箭手', 'Mage': '魔法師', 'Cleric': '聖職者',
    'Gladiator': '鬥士', 'Knight': '騎士', 'Sword Master': '劍聖',
    'General': '將軍', 'Heroes': '英雄', 'Dragon Knight': '龍騎士', 'Slayer': '殺戮者',
    'Hunter': '獵人', 'Ranger': '遊俠', 'Sniper': '狙擊手',
    'Sharpshooter': '神射手', 'Specialist': '專家',
    'Imperial Shooter': '帝國射手', 'Trickster': '詭術師',
    'Wizard': '巫師', 'Arc Mage': '大魔導', 'Shaman': '薩滿', 'Sage': '賢者',
    'Warlock': '惡魔法師', 'Sorcerer': '咒術師', 'Oracle': '神諭者',
    'Priest': '祭司', 'Saint': '聖者', 'Paladin': '聖騎士',
    'Holy Avanger': '聖裁者', 'Holy Avenger': '聖裁者', 'Bishop': '主教',
    'Cardinal': '樞機主教', 'Arc Bishop': '大主教',
    # 表格值
    '2X Damage': '2 倍傷害', '3X Damage': '3 倍傷害',
    '4X Damage': '4 倍傷害', '5X Damage': '5 倍傷害',
    'Diatas 79': '79 以上', 'Diatas 51': '51 以上',
    '0 (Max Level)': '0（最高等級）',
}

# 時裝名稱
FASHION = {
    'Basic Cloth 1': '基本上衣 1', 'Basic Cloth 2': '基本上衣 2',
    'Basic Cloth 3': '基本上衣 3', 'Basic Cloth 4': '基本上衣 4',
    'Basic Pants 1': '基本褲子 1', 'Basic Pants 2': '基本褲子 2',
    'Basic Pants 3': '基本褲子 3', 'Basic Pants 4': '基本褲子 4',
    'Basic Shoes 1': '基本鞋子 1', 'Basic Shoes 2': '基本鞋子 2',
    'Basic Shoes 3': '基本鞋子 3', 'Basic Shoes 4': '基本鞋子 4',
    'School Uniform Cloth (M)': '學院制服上衣（男）',
    'School Uniform Pants (M)': '學院制服褲子（男）',
    'School Shoes (M)': '學院鞋（男）',
    'School Uniform Cloth (F)': '學院制服上衣（女）',
    'School Uniform Pants (F)': '學院制服褲子（女）',
    'School Shoes (F)': '學院鞋（女）',
}

# 徽章：狀態異常頁用的簡稱 -> 徽章頁的正式英文名（依 Badge 頁的圖檔對照）
BADGE_ALIAS = {
    'Cpt. Jay Bubble': 'Captain Jay Bubble',   # Badge_7.png
    'Splashing Marble': 'Blue Fire Bead',      # Badge_9.png
    'Dayton Card': 'Chadunka',                 # Badge_12.png
    'Fire Jelly Master': 'Fire Master Jelly',  # Badge_13.png
    'Gratos Machine IV': 'Gratos Machine IV',  # Badge_15.png
}

# 怪物：wiki 英文名 -> (中文名, 等級, 地區)；等級與地區會拿去和 monsters.json
# 對驗，對不上就不套用（保留英文）。中文名來自遊戲資料，與 wiki 的英文命名並非
# 直譯，例如 Alucard 的韓文原名是 루즈볼트（Roosevolt）＝魯茲博特。
MONSTER = {
    'Pirate Octopus': ('海賊章魚', 46, '天空之城'),
    'Black Hurricane': ('颶風黑', 47, '天空之城'),
    'Humpty Dumpty': ('漢普蒂鄧普蒂', 49, '天空之城'),
    'Gratos Machine V': ('拉格瑪提Ⅴ', 55, '天空之城'),
    'Goul': ('食屍鬼', 52, '蘭德韋爾要塞'),
    'Dark Snake': ('暗影狙擊手', 56, '蘭德韋爾要塞'),
    'Berserker Mummy': ('幽靈士兵', 60, '蘭德韋爾要塞'),
    'Fly Meepo': ('惡魔夢魘', 65, '蘭德韋爾要塞'),
    'Night Scratch': ('暗夜爪痕', 69, '蘭德韋爾要塞'),
    'Incubus': ('夢魘惡魔', 73, '蘭德韋爾要塞'),
    'Succubus': ('琥珀色魔女', 75, '蘭德韋爾要塞'),
    'Blood Sucker': ('嗜血吸血者', 77, '蘭德韋爾要塞'),
    'Vampirit Pet': ('吸血鬼蝙蝠', 79, '蘭德韋爾要塞'),
    'Lilith': ('吸血女僕', 83, '蘭德韋爾要塞'),
    'Cenacia': ('賽納西亞', 84, '蘭德韋爾要塞'),
    'Vamp Deacon': ('吸血執事', 85, '蘭德韋爾要塞'),
    'Alucard': ('魯茲博特', 99, '蘭德韋爾要塞'),
}

# 長段落／清單：原文 -> 中文（以原文字串當 key，wiki 改字就會落到未翻譯清單）
TXT = {
    # 前言
    "Kamu harus membuat karaktermu terlebih dahulu sebelum dapat bermain Master Of Fantasy. Jumlah maksimal karakter yang dapat kamu buat adalah 3. Pilih nama karakter, Job, dan tampilan Fashion karaktermu. Ketika pertama kali bermain, karakter kamu akan langsung memakai Wooden Weapon, Armor, Shield dan memelihara Ghost. Kamu dapat langsung berburu Monster, menyelesaikan Quest dari seorang NPC, chat dengan pemain lain, mengikuti Exam untuk mempelajari Major Skill, mengikuti class untuk mempelajari skill dari Job yang kamu pilih, membuat Party sebelum pergi hunting, bergabung dengan suatu Circle, bermain mode PvP dan PvM, membeli Pet dan Item Mall. Kamu dapat Wedding dengan pemain lainnya setalah melakukan pergantian ke 2nd Job. Seorang Game Master (GM) dapat dibedakan dari pemain biasa dengan melihat tulisan chat berwarna biru gelap di chat bar.":
        "開始遊玩 Master Of Fantasy 之前必須先建立角色，最多可以建立 3 個角色。建立時要選擇角色名稱、職業（Job）與時裝外觀。第一次進入遊戲時，角色會直接裝備 Wooden Weapon、防具（Armor）與盾牌（Shield），並帶著寵物 Ghost。你可以馬上去獵怪、完成 NPC 的任務、和其他玩家聊天、參加考試（Exam）學習主要技能（Major Skill）、上課學習所選職業的技能、出發狩獵前先組隊（Party）、加入社團（Circle）、進行 PvP 與 PvM、購買寵物與商城道具（Item Mall）。完成二轉之後，可以和其他玩家結婚（Wedding）。遊戲管理員（GM）與一般玩家的分別在於：他在聊天欄的發言是深藍色的。",

    # 時裝
    "Kamu dapat menentukan tampilan Fashion dasar Karaktermu ketika sedang membuat Karakter. Seragam Akademi akan langsung kamu dapatkan secara otomatis setelah kamu berhasil membuat karakter dan masuk kedalam game.":
        "建立角色時可以決定角色的基本時裝外觀。成功建立角色並進入遊戲後，會自動獲得學院制服。",

    # 操作
    "Tombol default di Master Of Fantasy:": "Master Of Fantasy 的預設按鍵：",

    # 能力點
    "Ketika pertama kali kamu memainkan Master Of Fantasy, semua status point karaktermu adalah 4. Total Point yang kamu punya ketika pertama kali bermain Master Of Fantasy adalah 10. Setiap kali Level Up kamu akan mendapatkan bonus 5 Points. Dengan menyelesaikan Quest dari NPC tertentu kamu juga bisa mendapatkan Points. Kamu hanya dapat reset status karaktermu dengan menggunakan Item Mall Status Reset.":
        "初次遊玩 Master Of Fantasy 時，角色的各項能力點都是 4，手上持有的總點數是 10。每次升級可以獲得 5 點。完成特定 NPC 的任務也可以獲得點數。角色能力值只能使用商城道具 Status Reset 重置。",
    "Ketika total status point karaktermu telah mencapai jumlah tertentu, point yang dibutuhkan untuk meningkatkan status akan meningkat:":
        "當角色的能力點總數達到一定數量後，再提升能力值所需的點數也會跟著增加：",

    # 能量條
    "Setelah kamu melakukan pergantian Job untuk yang pertama kalinya, kamu dapat melakukan serangan spesial ketika Gauge Bar yang terletak dibawah MP Bar karaktermu penuh. Gauge Bar akan terisi setiap kali kamu berhasil melakukan serangan kritikal. Serangan spesial dari Gauge Bar tidak dapat Miss dan tidak menghiraukan defense target. Kamu dapat mempercepat peningkatan Gauge Bar dengan menggunakan semua skill yang dapat menyerang lebih dari satu Monster. Serangan spesial dari Gauge Bar selalu Critical. Gauge Bar akan direset secara otomatis ketika kamu logout atau pindah channel.":
        "第一次轉職之後，當角色 MP 條下方的能量條（Gauge Bar）集滿時，就可以使出特殊攻擊。每次成功打出爆擊攻擊，能量條就會累積。能量條的特殊攻擊不會 Miss，也會無視目標的防禦力。使用任何可以同時攻擊多隻怪物的技能，可以加快能量條累積。能量條的特殊攻擊必定是爆擊。登出或切換頻道時，能量條會自動歸零。",

    # 道具欄／快捷列
    "Didalam inventorymu terdapat sebanyak 72 slot item dan 24 slot Fashion Item. Jumlah maksimal Libi yang bisa kamu bawa didalam inventorymu adalah 2,000,000,000 Libi. Kamu dapat melempar keluar item apapun dengan mendrag item dari inventorymu kearah tempat yang kosong lalu tentukan jumlah kuantitas dari item yang ingin kamu lempar keluar dari dalam inventorymu.":
        "道具欄中有 72 格道具欄位與 24 格時裝欄位。道具欄內最多可以攜帶 2,000,000,000 Libi。把道具從道具欄拖曳到空地上，再指定要丟出的數量，就可以把任何道具丟出道具欄。",
    "Untuk menggunakan sebuah skill, kamu harus mendrag skill dari daftar skill yang kamu punya. Yang dapat ditaruh kedalam Quick Slot adalah Skill, Major Skill tertentu, Weapon, Armor, Shield, Ring, Necklace, Badge, Potion, Moving Scroll, Pet Food, Fashion Item, dan Item Mall tertentu. Jumlah total Quick Slot setiap karakter pada awalnya adalah 8 dan akan menjadi 12 setelah menggunakan Premium Quick Slot. Kamu memiliki sebanyak 3 slot yang berbeda, tekan Page Up atau Page Down untuk mengganti slot.":
        "要使用技能，必須從自己的技能清單把技能拖曳出來。可以放進快捷列（Quick Slot）的有：技能、特定的主要技能、武器、防具、盾牌、戒指（Ring）、項鍊（Necklace）、徽章（Badge）、藥水（Potion）、移動卷軸（Moving Scroll）、寵物飼料、時裝道具，以及特定的商城道具。每個角色的快捷列一開始共 8 格，使用 Premium Quick Slot 之後會變成 12 格。你有 3 組不同的快捷列，按 Page Up 或 Page Down 切換。",

    # 師徒制度
    "Syarat menjadi seorang Proctor:": "成為 Proctor（前輩）的條件：",
    "Syarat menjadi seorang Junior:": "成為 Junior（後輩）的條件：",
    "Level dari seorang Senior harus memiliki jarak diatas 10 Level dari seorang Junior.":
        "前輩的等級必須比後輩高 10 級以上。",
    "Seorang Senior hanya dapat memiliki 10 orang Junior.": "一位前輩最多只能收 10 位後輩。",
    "Level dari seorang Junior harus memiliki jarak dibawah 10 Level dari seorang Senior.":
        "後輩的等級必須比前輩低 10 級以上。",
    "Seorang Senior hanya dapat memiliki 1 orang Senior.":
        "一位後輩只能有 1 位前輩。（原文此句寫成「一位 Senior 只能有 1 位 Senior」，應為筆誤）",
    "Seiring dengan pertumbuhan seorang Junior, Exp dan Libi akan dihadiahkan kepada seorang Proctor. Junior akan mendapatkan sedikit Libi pada saat naik level. Proctor akan dikenakan penalty sebesar 1,000 Libi per jumlah Junior yang dimiliki jika mengeluarkan seorang Junior kecuali jika Junior yang memutuskan untuk leave Proctor. Proctor dan Junior dapat saling meninggalkan memo dengan gratis. Keuntungan memiliki Proctor adalah 5% Exp bonus untuk Proctor dan Junior memungkinkan mendapatkan Max Exp. Klik Kanan kepada seseorang yang ingin kamu jadikan sebagai Junior lalu pilih Add Junior. Kamu dapat mengirimkan pesan kepada senior atau juniormu dengan menekan tombol F lalu pilihlah proctor kemudian kirim pesan.":
        "隨著後輩成長，前輩會獲得經驗值與 Libi 獎勵；後輩升級時也會拿到少量 Libi。前輩若主動把後輩逐出，會依名下後輩人數，每位罰 1,000 Libi；但若是後輩自己決定離開就不罰。前輩與後輩之間可以免費互留留言。師徒制度的好處是前輩有 5% 經驗加成，後輩則有機會取得最高經驗值。對想收為後輩的玩家點右鍵，選擇 Add Junior。按 F 鍵後選擇 proctor，就可以傳訊息給自己的前輩或後輩。",

    # 個人商店
    "Kamu dapat membuka tokomu sendiri dengan mengklik kanan karaktermu kemudian pilih Open Store. Kamu harus mendrag item dari inventorymu kearah slot Store kemudian tentukan harga dari item yang ingin kamu jual lalu pilih Mulai. Klik kanan pada karaktermu lalu pilih View Store jika kamu ingin menambah item yang ingin kamu jual atau mengubah harga item. Untuk menutup tokomu kamu harus mengklik kanan karaktermu lalu pilih Close Store. Jika semua barang yang kamu taruh distoremu terjual habis, maka tokomu akan tertutup secara otomatis. Kamu hanya dapat membuka store di Market Ribi Town, Circle Room, Bluestar Town, dan Paperon. Seorang Game Master dapat membuka store dimana saja. Selama kamu membuka toko, kamu tidak dapat bergerak ataupun menyerang monster. Kamu tidak dapat membeli item dari seorang pemain yang menjual itemnya jika pendapatan Libi yang dia terima dari barang yang akan terjual melebihi batas 2,000,000,000 Libi.":
        "對自己的角色點右鍵並選擇 Open Store，就可以開設自己的商店。把道具從道具欄拖曳到商店欄位，設定要賣的價格後選擇「開始」。想追加要賣的道具或修改價格時，對自己的角色點右鍵選擇 View Store。要收攤時，對自己的角色點右鍵選擇 Close Store。擺出的商品全部賣完後，商店會自動關閉。只能在利比村莊（Ribi Town）的市場、社團房間（Circle Room）、藍星村莊（Bluestar Town）與派貝倫（Paperon）開店，遊戲管理員則可以在任何地方開店。開店期間無法移動，也無法攻擊怪物。如果賣家賣出商品後入手的 Libi 會超過 2,000,000,000 Libi 的上限，你就無法向他購買道具。",

    # 交易
    "Kamu dapat melakukan Trade dengan pemain lain dengan klik kanan karakter pemain lain lalu pilih Trade. Kamu dapat mentrade item dengan mendrag item dari inventorymu ke arah slot Trade atau Libi dengan mengklik Libi pada slot Trade. Klik Exchange untuk melakukan Trade.":
        "對其他玩家的角色點右鍵並選擇 Trade，就可以和對方交易。把道具從道具欄拖曳到交易欄位即可交易道具；點交易欄位裡的 Libi 則可以交易金錢。按下 Exchange 完成交易。",
    "Jangan pernah melakukan transaksi trade dengan pemain yang tidak dikenal.":
        "絕對不要和不認識的玩家進行交易。",
    "Seorang GM tidak akan pernah menanyakan ID ataupun password karaktermu.":
        "GM 絕對不會詢問你的角色 ID 或密碼。",
    "Berhati-hatilah terhadap kasus penipuan dalam transaksi trading.":
        "請小心交易詐騙。",
    "Trading sangat efektif jika ingin menyelesaikan Quest yang meminta mencari item drop dari Monster.":
        "任務若要求蒐集怪物掉落的道具，用交易處理會非常有效率。",

    # 狀態異常
    "Di dalam dunia Master Of Fantasy terdapat sebanyak 3 Status Effect yaitu Stop, Stun, dan Freeze. Efek status dapat muncul karena efek dari sebuah Skill dan Badge. Monster yang tinggal di Castle of Heaven dan Rundwell Fortress dapat memberikan efek status kepada player.":
        "Master Of Fantasy 的世界中共有 3 種狀態異常（Status Effect）：定身（Stop）、暈眩（Stun）與冰凍（Freeze）。狀態異常可能由技能與徽章（Badge）的效果造成。居住在天空之城（Castle of Heaven）與蘭德韋爾要塞（Rundwell Fortress）的怪物，也會讓玩家陷入狀態異常。",
    "Berikut adalah daftar monster yang bisa memberikan Status Effect ketika memberikan damage kepada player:":
        "以下是對玩家造成傷害時、可能一併附加狀態異常的怪物清單：",
    "Tidak dapat bergerak atau pindah arah, dapat menyerang, dapat menggunakan semua skill dan item.":
        "無法移動也無法轉向，但可以攻擊，也可以使用所有技能與道具。",
    "Tidak dapat bergerak atau menyerang, hanya dapat menggunakan skill buff dan item.":
        "無法移動也無法攻擊，只能使用增益技能與道具。",
    "Tidak dapat bergerak atau menyerang, Tidak dapat diserang, HP akan berkurang sebanyak 1 damage per detik selama efek freeze masih berlangsung, hanya dapat menggunakan skill buff dan item. Monster akan berhenti menyerangmu dan berjalan kembali ke posisi awal spawn mereka.":
        "無法移動也無法攻擊，同時也不會被攻擊；冰凍效果持續期間，HP 每秒減少 1 點傷害；只能使用增益技能與道具。怪物會停止攻擊你，並走回原本的重生位置。",
}

# 能力點：原文條目 -> (中文名, 英文名, 影響, 每點加成)
POINTS = {
    "Meningkatkan minimal dan maksimal Damage. Setiap 1 Attack point: +1 Damage.":
        ("攻擊", "Attack", "提升最小與最大傷害。", "每 1 點攻擊：+1 傷害。"),
    "Meningkatkan Max HP dan HP Regen. Setiap 1 Strength point: +16 Max HP, +2 HP Regen.":
        ("力量", "Strength", "提升最大 HP 與 HP 回復。", "每 1 點力量：+16 最大 HP、+2 HP 回復。"),
    "Meningkatkan Accuracy, Critical Rate, dan Evasion. Setiap 1 Agility point: +0.3 Accuracy, +0.1 Critical Rate, +0.3 Evasion.":
        ("敏捷", "Agility", "提升命中、爆擊率與迴避。",
         "每 1 點敏捷：+0.3 命中、+0.1 爆擊率、+0.3 迴避。"),
    "Meningkatkan Max MP, MP Regen, dan mengurangi Delay Skill. Setiap 1 Intellect point: +12 Max MP, +2 MP Regen, -1% Delay Skill.":
        ("智力", "Intellect", "提升最大 MP、MP 回復，並縮短技能冷卻。",
         "每 1 點智力：+12 最大 MP、+2 MP 回復、技能冷卻 -1%。"),
}

# 能力值：原文說明 -> (中文名, 英文名, 說明)
STATS = {
    "Total Max HP Karaktermu. Ketika kamu pertama kali bermain MOF, status ini adalah 110 dengan 10 HP Regen per detik. Setiap kali kamu Level Up, +10 Max HP.":
        ("HP", "HP", "角色的最大 HP 總量。初次遊玩 MOF 時，此數值為 110，每秒 HP 回復 10。每次升級，最大 HP +10。"),
    "Total Max MP Karaktermu. Ketika kamu pertama kali bermain MOF, status ini adalah 58 dengan 10 MP Regen per detik. Setiap kali kamu Level Up, +10 Max MP.":
        ("MP", "MP", "角色的最大 MP 總量。初次遊玩 MOF 時，此數值為 58，每秒 MP 回復 10。每次升級，最大 MP +10。"),
    "Minimal dan Maksimal Damage Karaktermu. Perbandingan tinggi rendahnya level karaktermu dengan targetmu mempengaruhi damage yang dihasilkan.":
        ("傷害", "Damage", "角色的最小與最大傷害。角色等級與目標等級的高低差，會影響實際造成的傷害。"),
    "Tingkat Pertahanan Karaktermu. Tanpa Armor atau Shield status ini akan selalu 0.":
        ("防禦力", "Defense", "角色的防禦程度。沒有裝備防具或盾牌時，這個數值永遠是 0。"),
    "Tingkat Akurasi seranganmu. Ketika kamu pertama kali bermain MOF, status ini adalah 81.0%. Jika perbandingan levelmu dengan lawan adalah diatas 12 level, maka seranganmu tidak akan Miss sekalipun status Akurasi karaktermu kecil. Perbandingan tinggi dan rendahnya level lawan akan mempengaruhi Akurasi karaktermu ketika sedang menyerang lawan.":
        ("命中", "Accuracy", "攻擊的命中程度。初次遊玩 MOF 時，此數值為 81.0%。若你和對手的等級差距在 12 級以上，就算命中數值很低，攻擊也不會 Miss。對手等級的高低差，會影響你攻擊時的命中。"),
    "Tingkat kemungkinan terjadinya serangan Kritikal. Ketika kamu pertama kali bermain MOF, status ini adalah 10.4%.":
        ("爆擊率", "Critical Rate", "發生爆擊攻擊的機率。初次遊玩 MOF 時，此數值為 10.4%。"),
    "Tingkat Evasi karaktermu. Ketika kamu pertama kali bermain MOF, status ini adalah 21.1%. Jika perbandingan levelmu dengan lawan adalah diatas 12 level, maka serangan lawanmu akan selalu Miss sekalipun status Evasi karaktermu kecil. Akan tetapi jika perbandingan levelmu dengan lawan adalah dbawah 12 level, maka serangan lawan tidak akan Miss tanpa menghiraukan status Evasi karaktermu.":
        ("迴避", "Evasion", "角色的迴避程度。初次遊玩 MOF 時，此數值為 21.1%。若你和對手的等級差距在 12 級以上，就算迴避數值很低，對手的攻擊也一定會 Miss；但若你和對手的等級差距不到 12 級，則不論迴避數值多少，對手的攻擊都不會 Miss。"),
    "Tingkat Pertahanan terhadap serangan magic.":
        ("魔法防禦", "Magic Resist", "對魔法攻擊的防禦程度。"),
}

# 操作按鍵：原文動作 -> 中文
KEYS = {
    "Menu": "選單",
    "Help": "說明",
    "Key Setting": "按鍵設定",
    "Mengunakan Slot Bar": "使用快捷列",
    "Daftar Quest": "任務清單",
    "Membuka Map": "開啟地圖",
    "Membuka/Menutup Chat Bar": "開啟／關閉聊天欄",
    "Menyerang": "攻擊",
    "Mengambil item yang ada di tanah": "撿取地上的道具",
    "Memilih pemain lain yang dijadikan sebagai target": "選取其他玩家作為目標",
    "Inventory": "道具欄",
    "Equipments": "裝備欄",
    "Diary": "日記",
    "Daftar Skill": "技能清單",
    "Daftar Major Skill": "主要技能清單",
    "Berlari/Berjalan": "跑步／走路切換",
    "Daftar Training": "修練清單",
    "Daftar Teman": "好友清單",
    "Daftar anggota Circle": "社團成員清單",
    "Daftar Party": "隊伍清單",
    "Option": "選項",
    "Mengambil Screenshot": "擷取遊戲畫面",
    "Chat": "聊天",
    "Mengganti Slot Bar": "切換快捷列",
    "Bergerak": "移動",
    # 按鍵欄位本身夾了印尼文說明，一併換掉
    "1, 2, 3, 4, 5, 6, 7, 8 [(9, 0, -, =) harus memakai Premium Quick Slot]":
        "1, 2, 3, 4, 5, 6, 7, 8［(9, 0, -, =) 需使用 Premium Quick Slot］",
}


def tr(s, table=None, mark=True):
    """查表翻譯；查不到就原樣保留並記錄。"""
    if not isinstance(s, str) or not s.strip():
        return s
    src = s.strip()
    for tbl in ([table] if table else []) + [TERM, FASHION, TXT]:
        if tbl and src in tbl:
            return tbl[src]
    if not re.search(r'[A-Za-z一-鿿]', src):      # 純數字／符號不用翻
        return numfix(src)
    if not re.search(r'[A-Za-z]', src):
        return src
    if mark:
        MISSING.append(src)
    return src


def tr_cell(text, table=None):
    """表格欄位：整格、或以 / 分隔的名詞逐段翻譯。"""
    src = text.strip()
    if not src:
        return ''
    for tbl in ([table] if table else []) + [TERM, FASHION]:
        if tbl and src in tbl:
            return tbl[src]
    parts = [p.strip() for p in src.split('/')]
    if len(parts) > 1 and all(p in TERM for p in parts):
        return ' / '.join(TERM[p] for p in parts)
    if re.fullmatch(r'[\d.,~]+(\s*(Libi|Level))?', src):
        s = numfix(src)
        s = re.sub(r'^([\d,]+)\s*Level$', r'\1 級', s)
        return s
    return tr(src, table)


# ── 既有資料裡的中文名 ───────────────────────────────────────────────────────
def load_skill_names():
    """docs/data/wiki.json 已經把 105 個技能改成中文並保留 en，直接沿用。"""
    wiki = json.load(open(WIKI_JSON, encoding='utf-8'))
    out = {}
    for s in wiki['skills']:
        en = s.get('en')
        if en and en != s['name']:
            out[en] = s['name']
    return out


def load_monster_names():
    """用等級＋地區驗證 MONSTER 對照表，通過才給中文名與怪物 id。"""
    mons = json.load(open(MONSTERS_JSON, encoding='utf-8'))
    out = {}
    for en, (zh, lv, region) in MONSTER.items():
        hit = [m for m in mons if m['name'] == zh and m['level'] == lv
               and region in (m.get('regions') or [])]
        if len(hit) == 1:
            out[en] = (zh, hit[0].get('id'))
        else:
            print(f'  ! 怪物對照失敗，保留英文：{en} / {zh}（等級 {lv}、{region}）')
    return out


SKILL_ZH = {}
MON_ZH = {}


def skill_name(en):
    return SKILL_ZH.get(en, en)


# ── 圖示 ────────────────────────────────────────────────────────────────────
WANT_ICONS = []          # [(fandom 檔名, 目標中文名, 掛 icon 的 dict)]


def want_icon(holder, fandom_file, display):
    holder['img'] = fandom_file
    WANT_ICONS.append((fandom_file, display, holder))


def download_icons():
    if not WANT_ICONS:
        return 0, 0, 0
    names = sorted({f for f, _, _ in WANT_ICONS})
    urls = {}
    for i in range(0, len(names), 50):
        batch = names[i:i + 50]
        q = '|'.join('File:' + n for n in batch)
        url = (f'{API}?action=query&format=json&prop=imageinfo&iiprop=url&titles='
               + urllib.parse.quote(q))
        try:
            data = json.loads(curl(url=url))
        except Exception:
            print('  ! imageinfo 批次失敗', i)
            continue
        for page in data.get('query', {}).get('pages', {}).values():
            info = page.get('imageinfo')
            if info:
                key = page['title'][len('File:'):].replace(' ', '_')
                urls[key] = info[0]['url']
        time.sleep(0.4)
    print(f'圖示網址：查到 {len(urls)} / {len(names)}')

    os.makedirs(IMG_DIR, exist_ok=True)
    got = cached = missing = 0
    taken = {}
    for fandom_file, display, holder in WANT_ICONS:
        ext = os.path.splitext(fandom_file)[1].lower() or '.png'
        fn = display.translate(ILLEGAL) + ext
        if taken.get(fn, fandom_file) != fandom_file:
            sys.exit(f'圖示檔名衝突：{fn} 同時對到 {taken[fn]} 與 {fandom_file}')
        taken[fn] = fandom_file
        dst = os.path.join(IMG_DIR, fn)
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            holder['icon'] = 'img/character/' + fn
            cached += 1
            continue
        url = urls.get(fandom_file)
        if not url:
            holder.pop('icon', None)
            missing += 1
            continue
        subprocess.run(['curl', '-sfLm60', '-o', dst, url], check=False)
        if not os.path.exists(dst) or os.path.getsize(dst) == 0:
            if os.path.exists(dst):
                os.unlink(dst)
            holder.pop('icon', None)
            missing += 1
            continue
        holder['icon'] = 'img/character/' + fn
        got += 1
        time.sleep(0.25)
    return got, cached, missing


# ── 表格轉輸出格式 ───────────────────────────────────────────────────────────
def build_table(tbl, cols=None, icon_col=None, icon_name=None, extra=None):
    """{'headers': [...], 'rows': [{'c': [...]}]}；icon_col 那欄的圖另外掛 icon。"""
    headers = [tr_cell(h['text']) for h in tbl['headers']]
    rows = []
    for raw in tbl['rows']:
        texts, files = [], []
        for c in raw:
            txt = c['text']
            if not txt and c['files']:
                txt = c['files'][0]['caption'] or c['files'][0]['link']
            texts.append(txt)
            files.append(c['files'])
        row = {'c': [cols(i, t) if cols else tr_cell(t) for i, t in enumerate(texts)]}
        if icon_col is not None and files[icon_col]:
            want_icon(row, files[icon_col][0]['file'], icon_name(row, texts))
        if extra:
            extra(row, texts)
        rows.append(row)
    return {'headers': headers, 'rows': rows}


# ── 主流程 ──────────────────────────────────────────────────────────────────
def fashion_icon_name(en, suffix):
    """時裝圖檔名：學院制服那幾件名稱本身已標了男女，不再重複加後綴。"""
    zh = FASHION.get(en, en)
    return zh if zh.endswith(('（男）', '（女）')) else zh + suffix


def build_player_character(text, out):
    secs = {s['title']: s for s in split_sections(text)}
    lead = split_sections(text)[0]

    out['intro'] = [tr(p) for p in map(numfix, paragraphs(lead['body']))]

    # 時裝
    fashion_secs = [s for s in split_sections(text) if s['title'] in ('Male', 'Female')]
    fashion = {'intro': [tr(p) for p in paragraphs(secs['Default Fashion Item']['body'])],
               'groups': []}
    for s in fashion_secs:
        suffix = '（男）' if s['title'] == 'Male' else '（女）'
        tbl = parse_tables(s['body'])[0]
        table = build_table(
            tbl,
            cols=lambda i, t: tr_cell(t),
            icon_col=0,
            icon_name=lambda row, texts: fashion_icon_name(texts[1], suffix))
        fashion['groups'].append({
            'name': '男性' if s['title'] == 'Male' else '女性',
            'en': s['title'], 'table': table})
    out['fashion'] = fashion

    # 操作按鍵
    keys = []
    for b in bullets(secs['Controls']['body']):
        m = re.match(r"^'''(.+?)'''\s*:\s*(.*)$", b)
        if not m:
            continue
        k = plain(m.group(1))
        keys.append({'key': KEYS.get(k, k), 'action': tr(plain(m.group(2)), KEYS)})
    out['controls'] = {'intro': [tr(p) for p in paragraphs(secs['Controls']['body'])],
                       'keys': keys}

    # 能力值
    stats = []
    for b in bullets(secs['Character Status']['body']):
        m = re.match(r"^'''(.+?)'''\s*:\s*(.*)$", b)
        if not m:
            continue
        en, desc = plain(m.group(1)), numfix(plain(m.group(2)))
        got = STATS.get(desc)
        if got:
            stats.append({'name': got[0], 'en': got[1], 'desc': got[2]})
        else:
            MISSING.append(desc)
            stats.append({'name': en, 'en': en, 'desc': desc})
    out['stats'] = stats

    # 能力點
    body = secs['Character Points']['body']
    pts, paras = [], paragraphs(body)
    for b in bullets(body):
        m = re.match(r"^'''(.+?)'''\s*:\s*(.*)$", b)
        if not m:
            continue
        en, desc = plain(m.group(1)), numfix(plain(m.group(2)))
        got = POINTS.get(desc)
        if got:
            pts.append({'name': got[0], 'en': got[1], 'effect': got[2], 'perPoint': got[3]})
        else:
            MISSING.append(desc)
            pts.append({'name': en, 'en': en, 'effect': desc, 'perPoint': ''})
    cost_tbl = build_table(parse_tables(body)[0])
    reset = {}
    for f in take_files(body)[1]:
        if f['file'].lower().endswith('.png'):
            want_icon(reset, f['file'], 'Status Reset')
    out['points'] = {'intro': [tr(p) for p in paras[:1]],
                     'list': pts,
                     'note': tr(paras[1]) if len(paras) > 1 else '',
                     'cost': cost_tbl,
                     'reset': reset}

    # 經驗值表
    out['expTable'] = build_table(parse_tables(secs['Exp Points']['body'])[0])

    # 能量條
    gauge = {'intro': [tr(p) for p in paragraphs(secs['Gauge System']['body'])], 'bars': []}
    bar_zh = {'Yellow Gauge Bar': '黃色能量條', 'Purple Gauge Bar': '紫色能量條',
              'Black Gauge Bar': '黑色能量條', 'Orange Gauge Bar': '橘色能量條'}
    for s in split_sections(text):
        if s['title'] not in bar_zh:
            continue
        zh = bar_zh[s['title']]
        tbl = parse_tables(s['body'])[0]
        table = build_table(
            tbl,
            cols=lambda i, t: skill_name(t) if i == 0 else tr_cell(t),
            icon_col=0,
            icon_name=lambda row, texts: f'{skill_name(texts[0])}（{zh}）')
        gauge['bars'].append({'name': zh, 'en': s['title'], 'table': table})
    out['gauge'] = gauge

    # 道具欄 / 快捷列
    qs = {'text': [tr(p) for p in map(numfix, paragraphs(secs['Quick Slot']['body']))]}
    for f in take_files(secs['Quick Slot']['body'])[1]:
        want_icon(qs, f['file'], 'Premium Quick Slot')
    out['inventory'] = {'text': [tr(p) for p in map(numfix, paragraphs(secs['Inventory']['body']))]}
    out['quickSlot'] = qs

    # 師徒制度
    body = secs['Proctor']['body']
    req = [{'title': tr(numfix(t)), 'items': [tr(numfix(x)) for x in items]}
           for t, items in blocks(body) if items]
    out['proctor'] = {
        'text': [tr(numfix(t)) for t, items in blocks(body) if not items],
        'requirements': req,
        'seniorRewards': build_table(parse_tables(
            [s for s in split_sections(text) if s['title'] == 'Senior Libi Rewards'][0]['body'])[0]),
        'juniorRewards': build_table(parse_tables(
            [s for s in split_sections(text) if s['title'] == 'Junior Libi Rewards'][0]['body'])[0]),
    }

    out['privateStore'] = {'text': [tr(numfix(p)) for p in paragraphs(secs['Private Store']['body'])]}
    out['trading'] = {
        'text': [tr(numfix(p)) for p in paragraphs(secs['Trading']['body'])
                 if not p.startswith("Trading Tips")],
        'tips': [tr(plain(b)) for b in bullets(secs['Trading']['body'])],
    }


def build_status_effect(text, out):
    all_secs = split_sections(text)
    secs = {s['title']: s for s in all_secs}
    lead = all_secs[0]

    effects = []
    zh_of = {'Stop': '定身', 'Stun': '暈眩', 'Freeze': '冰凍'}
    for b in bullets(lead['body']):
        m = re.match(r"^'''(.+?)'''\s*:\s*(.*)$", b)
        if not m:
            continue
        en, desc = plain(m.group(1)), plain(m.group(2))
        eff = {'name': zh_of.get(en, en), 'en': en, 'desc': tr(desc)}
        effects.append(eff)
    # gallery 的效果圖
    gallery = re.search(r'<gallery>(.*?)</gallery>', text, re.S)
    if gallery:
        for line in gallery.group(1).strip().split('\n'):
            fn = line.split('|')[0].strip()
            if not fn:
                continue
            en = fn.replace('_Effect.png', '').replace('_', ' ')
            for eff in effects:
                if eff['en'] == en:
                    want_icon(eff, fn, eff['name'] + '效果')
    out['statusEffects'] = effects

    src = {'intro': [tr(p) for p in paragraphs(lead['body'])]}

    # 怪物
    body = secs['Monster List']['body']

    def mon_extra(row, texts):
        got = MON_ZH.get(texts[0])
        if got and got[1]:
            row['monsterId'] = got[1]

    src['monsterIntro'] = [tr(p) for p in paragraphs(body)]
    src['monsters'] = build_table(
        parse_tables(body)[0],
        cols=lambda i, t: (MON_ZH[t][0] if i == 0 and t in MON_ZH else tr_cell(t)),
        icon_col=0,
        icon_name=lambda row, texts: MON_ZH.get(texts[0], (texts[0],))[0],
        extra=mon_extra)

    # 徽章
    def badge_zh(name):
        return BADGE_NAMES.get(BADGE_ALIAS.get(name, name), name)

    src['badges'] = build_table(
        parse_tables(secs['Badge']['body'])[0],
        cols=lambda i, t: (badge_zh(t) if i == 1 else tr_cell(t)),
        icon_col=0,
        icon_name=lambda row, texts: badge_zh(texts[1]))

    # 技能
    src['skills'] = []
    for title, zh in (('Stop Skills', '定身'), ('Stun Skills', '暈眩'), ('Freeze Skills', '冰凍')):
        tbl = parse_tables(secs[title]['body'])[0]
        table = build_table(
            tbl,
            cols=lambda i, t: (skill_name(t) if i == 1 else tr_cell(t)),
            icon_col=0,
            icon_name=lambda row, texts: skill_name(texts[1]))
        src['skills'].append({'name': zh, 'en': title.replace(' Skills', ''), 'table': table})
    out['statusSources'] = src


BADGE_NAMES = {}


def load_badge_names():
    wiki = json.load(open(WIKI_JSON, encoding='utf-8'))
    return {b['en']: b['name'] for b in wiki['badges'] if b.get('en')}


def main():
    global SKILL_ZH, MON_ZH, BADGE_NAMES
    SKILL_ZH = load_skill_names()
    BADGE_NAMES = load_badge_names()
    MON_ZH = load_monster_names()

    pages = fetch_pages(TITLES)
    print('抓到頁面：' + '、'.join(f'{t}（{len(pages[t])} 字元）' for t in TITLES))

    out = {}
    build_player_character(pages['Player Character'], out)
    build_status_effect(pages['Status Effect'], out)
    # Attribute 頁與 docs/data/wiki.json 的 matrix / monAttrs 完全重複，不收錄。

    got, cached, missing_icon = download_icons()
    print(f'圖示：新下載 {got}、已存在 {cached}、抓不到 {missing_icon}')

    if '--dump' in sys.argv:
        seen = []
        for s in MISSING:
            if s not in seen:
                seen.append(s)
        print('\n=== 未翻譯 %d 條 ===' % len(seen))
        for s in seen:
            print(json.dumps(s, ensure_ascii=False) + ': "",')
        return

    with open(OUT_JSON, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    md5 = hashlib.md5(open(OUT_JSON, 'rb').read()).hexdigest()
    print(f'寫出 {os.path.relpath(OUT_JSON, ROOT)}（md5 {md5}）')

    uniq = []
    for s in MISSING:
        if s not in uniq:
            uniq.append(s)
    if uniq:
        print(f'未翻譯 {len(uniq)} 條（已保留原文）：')
        for s in uniq:
            print('  - ' + (s[:90] + '…' if len(s) > 90 else s))


if __name__ == '__main__':
    main()
