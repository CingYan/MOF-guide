#!/usr/bin/env python3
"""徽章資料中文化：以中文玩家整理的內容為主，另一份英／印尼文資料作為對照。

同一枚徽章兩邊數值不一致時，中文為主、差異記在 alt 欄位，不擅自二選一。
"""
import json, os, re

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'data')

# en（原資料名稱）: (中文名, 取得方式, 效果, 遊戲內敘述, 補充說明, 與另一份資料的差異)
ZH = {
 'Honor of the Dead': ('榮耀の戰士', '死亡時隨機取得', '死亡懲罰率 -50%',
    '怪物與戰爭中英勇壯烈的戰士', '隨機取得，不必刻意送死。', ''),
 'Red Syrup Addict': ('紅色藥水之中毒者', '飲用紅色藥水時隨機取得',
    'HP 藥水效果 -50%、自動回復 HP +100%', '喝了太多藥水而中毒',
    '取得條件眾說紛紜：有人說 HP 低於 20% 時飲用較容易，也有人說狂飲比較快。目前確切條件不明。', ''),
 'Blue Syrup Addict': ('藍色藥水之中毒者', '飲用藍色藥水時隨機取得',
    'MP 藥水效果 -50%、自動回復 MP +100%', '喝了太多藍色藥水而中毒',
    '已確認由飲用藍色藥水取得；早期「喝藍水會拿到紅色藥水中毒者」的說法並不正確。', ''),
 'Friend of Wyvern': ('飛龍朋友', '搭乘飛龍隨機取得', '免費搭乘飛龍',
    '多多利用飛龍就能與飛龍成為朋友',
    '運氣成分高。有人第一次搭乘就拿到，也有人繞行一周才取得，同樣做法未必人人有效。', ''),
 'Master of Merits': ('功績精通者', '解戰爭任務隨機取得', '戰爭任務功勳獎勵 +10%',
    '因為立下很多功績而成為功績精通者，立功時可獲得功績分數',
    '10% 看似不多，長期累積相當可觀。', ''),
 'Sword Master': ('劍術精通者', '玩劍士的兩種小遊戲隨機取得', '劍術課業修練所得 +5%',
    '因為上了很多劍術課程而成為劍術精通者', '精通者系列隱藏徽章，已確認為小遊戲隨機取得，機率極低。', ''),
 'Archery Master': ('弓術精通者', '玩弓手的兩種小遊戲隨機取得', '弓術課業修練所得 +5%',
    '因為上了很多弓術課程而成為弓術精通者', '精通者系列隱藏徽章，已確認為小遊戲隨機取得，機率極低。', ''),
 'Magic Master': ('魔法精通者', '玩法師的兩種小遊戲隨機取得', '魔法課業修練所得 +5%',
    '因為上了很多魔法課程而成為魔法精通者', '精通者系列隱藏徽章，已確認為小遊戲隨機取得，機率極低。', ''),
 'Theology Master': ('神學精通者', '玩聖職的兩種小遊戲隨機取得', '神學課業修練所得 +5%',
    '因為上了很多神學課程而成為神學精通者', '精通者系列隱藏徽章，已確認為小遊戲隨機取得，機率極低。', ''),
 'Third Eye': ('第三隻眼', '不明', '可鎖定較遠處的怪物並攻擊（攻擊範圍 +10，需搭配遠距攻擊或技能）',
    '透過第三隻眼看見遠方的怪物並加以攻擊',
    '取得方式與實際效果都仍不明確。傳聞打怪取得、登出後消失的是「偽·第三隻眼」，無法裝備，屬已知異常。', ''),
 'Merchant of the Best': ('紅頂商人', '購買物品時隨機取得', '向 NPC 商店購買道具的費用 -3%',
    '可從商店賺取很大的利益', '', ''),
 'Extra Money': ('購物優惠', '販賣物品時隨機取得', '賣給 NPC 的道具價格 +40%',
    '經常透過商店 NPC 買賣物品後獲得的優惠',
    '實際增幅究竟是 40%、還是徽章上顯示的 20%，仍待更多實測。', ''),
 'Friend of Runpei': ('路菲的朋友', '於拍賣場買賣東西時隨機取得', '手續費優惠 20%',
    '經常光顧路菲就成為朋友', '拍賣場兩種徽章之一。', '另一份資料記為「只需支付 3% 手續費」'),
 'Owner of Runpei': ('路菲的商店主人', '於拍賣場買賣東西時隨機取得', '販賣手續費固定 100',
    '經常利用路菲做生意，就能成為路菲商店的主人', '拍賣場第二種徽章，持有者較少。', ''),
 'Strengthening the Best': ('第一強化', '強化時隨機取得', '強化成功率 +5%',
    '大量強化就能在強化時得到成功率的利益', '取得後可以擺攤幫人強化。', ''),
 'Active in Circle': ('社團活動熱衷者', '解公會課題隨機取得', '解任務時公會點數額外 +2 點',
    '在社團活動中積極參與，社團課程結束時增加評價分數',
    '取得方式與效果都不甚明確，持有者不多。', '另一份資料記為「社團點數 +2%」'),
 'Scholarship Student': ('獎學生', '修業第一名（小遊戲第一名）', '初級課業修練全部免費',
    'Lv.40 以上的課程點數可為好學生設定免費課程', '取得方式相當神秘，資料仍不完整。',
    '另一份資料記為「使用修練卡完成課程獲得的點數 ×2」'),
 'Super Scholarship Student': ('超級獎學生', '取得獎學生徽章後再次獲得第一名', '中級課業修練全部免費',
    'Lv.60 以上的課程點數可為好學生設定免費課程',
    '已有圖片佐證確實存在，但持有者不多。', '另一份資料記為「使用高級修練卡完成課程獲得的點數 ×2」'),
 'Basic Goal': ('基本的目標', '於 Lv.20 轉職前沒有放棄任何研究，即可隨機取得', '獎賞經驗值 +1%',
    '對於直到第一次轉職為止都不放棄研究的使用者給予稱讚',
    '原以為是必得徽章，但有不少人未取得，因此列為隱藏徽章。', ''),
 'Intermediate Goal': ('重要的目標', '於 Lv.40 轉職前沒有放棄任何研究，即可隨機取得', '獎賞經驗值 +2%',
    '對於直到第二次轉職為止都不放棄研究的使用者給予稱讚',
    '二轉取得。名稱與一轉相同但顏色不同，效果為 2%。', ''),
 'Noble Goal': ('高貴的目標', '於 Lv.60 轉職前沒有放棄任何研究，即可隨機取得', '獎賞經驗值 +3%',
    '對於直到第三次轉職為止都不放棄研究的使用者給予稱讚', '三轉取得。', ''),
 'Conqueror of Libi Island': ('利比城的征服者', '打敗頭目後隨機取得', '攻擊 +5%、迴避 +10%',
    '在爭戰中與利比城的敵人首領交戰得勝',
    '取得方式有多種說法：打利比島頭目隨機取得、打遍所有頭目、打 Lv.50 以上頭目隨機取得。'
    '另有定量說法為每種頭目各打 20 隻，再加卡司特蘭 5 隻。尚無定論。', ''),
 'Dethroned King of Libi': ('利比城的霸王', '取得征服者徽章後，打敗頭目再隨機取得', '攻擊 +10%、防禦 +20%',
    '制伏利比城的敵人首領',
    '利比城系列中最稀有的一枚。可確定前提是先取得征服者，與「利比城的英雄」無關。'
    '另有定量說法為取得征服者後每種頭目各打 50 隻。', ''),
 'Hero of Libi Island': ('利比城的英雄', '解完 60 級利比島任務即可取得', '命中 +5%、防禦 +10%',
    '解決利比城所有問題就成為英雄',
    '取得方式說法一致，不靠運氣，但等級門檻較高。', '另一份資料記為「命中 +10%」'),
}

# 中文資料獨有、原資料沒有的徽章
EXTRA = [{
    'name': '功績狂熱', 'en': '', 'group': '徽章', 'kind': '飾品',
    'jobs': ['劍士', '弓箭手', '魔法師', '聖職者'], 'rarity': '稀有',
    'lv': None, 'lvtext': '', 'price': '', 'add': '', 'def': None,
    'dmg': '', 'spd': '', 'rng': '', 'attr': '', 'part': '', 'type': '稀有',
    'method': '解戰爭任務隨機取得', 'eff': '功績任務的怪物數量 -10%', 'named': 'zh',
    'flavor': '', 'note': '常解戰爭任務的玩家最想要的徽章之一，靠運氣取得。', 'alt': '',
}]

# 頭目名稱對照。
# 驗證方式：舊資料的等級與現行資料的頭目等級逐一對上（28/29/38/42/45/48/49/50/58/
# 60/61/65/70/75/80/85/91/100/110 各只有一隻），再用舊資料保留的韓文名交叉檢查，
# 例如 혈마검 = 血魔劍、차둔카 = 車頓卡、베어울프 = 貝爾沃夫、치프 파파고 = 首領趴趴犬。
BOSS = {
 'Captain Jay Bubble': '深海閻王', 'Dr Kingbo': 'DR.金伯', 'Dr. Kingbo': 'DR.金伯', 'Gastran': '卡司特蘭', 'Blue Fire Bead': '吸血魔珠',
 'Wolf Heroes': '貝爾沃夫', 'Jelly Master': '巨大果凍', 'Chadunka': '車頓卡',
 'Fire Master Jelly': '火焰果凍', 'Volcano': '火山岩怪',
 'Gratos The Ancient Machine': '拉克馬提IV', 'Gratos Machine IV': '拉克馬提IV',
 'Endless Dragon': '卡司特蘭', 'Beawolf': '鐵爪影狼', 'Destroyer': '惡猛螳螂',
 'Skeleton Hand': '撒旦的左手', 'Ware Wolf': '首領趴趴犬', 'Evil Minotaur': '死亡山羊',
 'Darksiders': '黃金爪小精靈', 'Curse Sword': '血魔劍', 'Dark Lord': '黑暗魔王',
 'Orochi': '鷲翼蛇妖',
}

# NPC 對照。音譯相符，並用該 NPC 任務的討伐目標屬性驗證：
# 克丁哈以德的討伐任務 6/6 全是不死系，巴比度以動物系為主，與徽章效果一致。
NPC = {'Laura': '蘿拉', 'Cruno': '克魯諾', 'Captain Hyde': '克丁哈以德', 'Babidu': '巴比度'}

# 其餘徽章名稱為暫譯，UI 會同時顯示原名以便校對
TRANS = {
 'Rookie': '新手', 'Freshman': '新生', 'Under Level Student': '初級生',
 'Middle Level Student': '中級生', 'Upper Level Student': '高級生',
 'Special Level Student': '特級生', 'Master': '大師',
 'Soul Liberator': '靈魂解放者', 'Demon Hunter': '惡魔獵人',
 "Beaver's Savior": '海狸的救星', 'Cruno Guardian Knight': '克魯諾的守護騎士',
 'Unlucky Day': '倒楣的一天', 'Lucky Day': '幸運的一天', 'Public Master': '對人戰精通者',
}

# 尚未中文化的原始敘述：句型統一，怪物與 NPC 專有名詞維持原文
PAT = [
 (re.compile(r'^Hunt\s+(\d+)\s+(.+)$', re.I), r'獵殺 \1 隻 \2'),
 (re.compile(r'^Sering-seringlah mati$', re.I), '經常死亡'),
 (re.compile(r'^Sering-seringlah menggunakan (.+)$', re.I), r'經常使用 \1'),
 (re.compile(r'^Sering-seringlah menjual barang di (.+)$', re.I), r'經常在 \1 販賣物品'),
 (re.compile(r'^Sering-seringlah menitipkan barang di (.+)$', re.I), r'經常在 \1 寄放物品'),
 (re.compile(r'^Sering-seringlah terbang menggunakan jasa (.+)$', re.I), r'經常搭乘 \1'),
 (re.compile(r'^Sering-seringlah menjual item kepada (.+)$', re.I), r'經常向 \1 販賣道具'),
 (re.compile(r'\bSword Point\b'), '劍術課業點數'),
 (re.compile(r'\bBow Point\b'), '弓術課業點數'),
 (re.compile(r'\bMagic Point\b'), '魔法課業點數'),
 (re.compile(r'\bTheology Point\b'), '神學課業點數'),
 (re.compile(r'\bPvP Point\b'), '對人戰點數'),
 (re.compile(r'\bJob 轉職'), '轉職'),
 (re.compile(r'\bTraining Card\b'), '修練卡'),
 (re.compile(r'\bClass\b'), '課程'),
 (re.compile(r'\bWar Task\b'), '戰爭任務'),
 (re.compile(r'\bQuest Circle\b'), '公會課題'),
 (re.compile(r'\bMerchant\b'), '商人'),
 (re.compile(r'(?<=[\u4e00-\u9fff])\s+的'), '的'),
 (re.compile(r'Kemungkinan sukses ketika meng-?upgrade senjata atau perisai'), '武器或盾牌強化成功率'),
 (re.compile(r'ketika menggunakan jasa (\w+)', re.I), r'（使用 \1 服務時）'),
]

def zh_text(s):
    s = (s or '').strip()
    for pat, rep in PAT:
        s = pat.sub(rep, s)
    for en, zh in list(BOSS.items()) + list(NPC.items()):
        s = s.replace(en, zh)
    return s

p = os.path.join(DATA, 'wiki.json')
w = json.load(open(p, encoding='utf-8'))
matched = 0
for b in w['badges']:
    b.setdefault('flavor', '')
    b.setdefault('note', '')
    b.setdefault('alt', '')
    for k in ('lvtext', 'price', 'add', 'attr', 'part'):     # 原資料用 "None" 表示沒有
        if (b.get(k) or '').strip() in ('無', 'None'):
            b[k] = ''
    en = b['name']
    b['en'] = en
    if en in ZH:
        name, method, eff, flavor, note, alt = ZH[en]
        b.update(name=name, method=method, eff=eff, flavor=flavor, note=note, alt=alt, named='zh')
        matched += 1
    else:
        b['method'] = zh_text(b.get('method'))
        b['eff'] = zh_text(b.get('eff'))
        if en in BOSS:
            b['name'], b['named'] = BOSS[en], 'boss'
        elif en in TRANS:
            b['name'], b['named'] = TRANS[en], 'tr'
        else:
            b['named'] = 'en'

w['badges'] += EXTRA
w['badges'].sort(key=lambda b: (b['rarity'] != '普通', b['lv'] or 999, b['name']))

json.dump(w, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
import collections
print(f'中文化 {matched} 枚、新增 {len(EXTRA)} 枚，共 {len(w["badges"])} 枚')
print('名稱來源:', dict(collections.Counter(b['named'] for b in w['badges'])))
