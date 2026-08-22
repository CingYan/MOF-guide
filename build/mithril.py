#!/usr/bin/env python3
"""把裝備名稱裡殘留的 Mithril / loon 換成站上既有的中文。

中文站上本來就有，只是基礎款有、「改造的／熟練的／精巧的／修護的／提升的」
那些變體款留著英文：

    祕銀短劍          (H0018) lv70  icon=祕銀短劍.png
    改造的Mithril 短劍 (Z0144) lv70  icon=祕銀短劍.png     <- 同圖同等級

    北歐細工短劍        (H0017)       icon=北歐細工短劍.png
    改造的 loon 細工短劍             icon=北歐細工短劍.png

圖檔名就是對應關係的證據，所以套用前會逐件驗證：換完的字必須出現在
該裝備自己的圖檔名裡，對不上就不換並回報。

只換那個英文字，不動武器後綴 —— 基礎款寫「巨劍」而變體款寫「大劍」、
基礎款「之斧」變體款「斧子」，那是原始資料自己的用字差異，不是我該統一的。
英文字前後多餘的空白一併去掉（中文之間不需要）。

itoliwun 不處理：站上沒有對應中文，品項名就叫「(音譯近itoliwun)」，
上游自己都標明是音譯猜的，不再猜一層。
"""
import json, os, pathlib, re

DATA = pathlib.Path(__file__).resolve().parent.parent / "docs/data"
WORDS = {"Mithril": "祕銀", "loon": "北歐"}
PAT = re.compile(r"\s*(" + "|".join(WORDS) + r")\s*")

equips = {e["name"]: e for e in json.loads((DATA / "equips.json").read_text("utf-8"))}

def rename(name):
    if not PAT.search(name):
        return None
    new = PAT.sub(lambda m: WORDS[m.group(1)], name)
    e = equips.get(name)
    if e:                                   # 有圖就拿圖檔名當證據驗一次
        icon = os.path.splitext(os.path.basename(e.get("icon") or ""))[0]
        word = WORDS[PAT.search(name).group(1)]
        if word not in icon:
            print(f"  ⚠ 跳過（圖檔名 {icon!r} 對不上 {word}）：{name}")
            return None
    return new

total = 0
for path in sorted(DATA.glob("*.json")):
    data = json.loads(path.read_text("utf-8"))
    n = 0
    def walk(node):
        global n
        if isinstance(node, dict):
            if isinstance(node.get("name"), str) and (new := rename(node["name"])):
                node["name"] = new
                n += 1
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(data)
    if n:
        sep = (",", ": ") if path.name == "character.json" else (",", ":")
        kw = {"sort_keys": True} if path.name == "character.json" else {}
        path.write_text(json.dumps(data, ensure_ascii=False, separators=sep, **kw), "utf-8")
        print(f"  {path.name}: {n} 處")
        total += n
print(f"合計 {total} 處")
