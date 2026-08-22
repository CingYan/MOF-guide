#!/usr/bin/env python3
"""把技能圖示從 Fandom 抓下來，依技能名命名後接進 wiki.json。

wiki.json 本來就是 build/fetch.py 從 master-of-fantasy.fandom.com 的 MediaWiki
API 抓的，每個技能都帶一個 Fandom 檔名（Archer_Skill3.png）。圖一直都拿得到，
先前誤以為要重爬有 bot 防護的那個站，是查錯來源。

命名跟站上其他圖一致，用技能自己的名字，不留 Fandom 的英文檔名。
可重複執行：已存在且非空的檔案不重抓。
"""
import json, os, pathlib, subprocess, time, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs/data/wiki.json"
OUT = ROOT / "docs/img/skills"
API = "https://master-of-fantasy.fandom.com/api.php"
ILLEGAL = str.maketrans({"/": "／", "\\": "＼", ":": "：", "*": "＊", "?": "？",
                         '"': "＂", "<": "＜", ">": "＞", "|": "｜",
                         "%": "％", "#": "＃"})

wiki = json.loads(WIKI.read_text("utf-8"))
skills = [s for s in wiki["skills"] if s.get("img")]

# ── 1. 問 Fandom 每個檔名的真實網址（一次 50 個）──
urls = {}
names = sorted({s["img"] for s in skills})
for i in range(0, len(names), 50):
    batch = names[i:i + 50]
    q = "|".join("File:" + n for n in batch)
    u = f"{API}?action=query&format=json&prop=imageinfo&iiprop=url&titles=" + urllib.parse.quote(q)
    out = subprocess.run(["curl", "-sm60", u], capture_output=True, text=True).stdout
    for p in json.loads(out)["query"]["pages"].values():
        info = p.get("imageinfo")
        if info:
            # 檔名回傳時底線會變空白，轉回去才對得上 img 欄位
            urls[p["title"][len("File:"):].replace(" ", "_")] = info[0]["url"]
    time.sleep(0.5)
print(f"Fandom 查到網址：{len(urls)} / {len(names)}")

# ── 2. 下載，用技能名當檔名 ──
OUT.mkdir(parents=True, exist_ok=True)
got = missing = cached = 0
for s in skills:
    url = urls.get(s["img"])
    if not url:
        s.pop("icon", None)
        missing += 1
        continue
    fn = s["name"].translate(ILLEGAL) + ".png"
    dst = OUT / fn
    if dst.exists() and dst.stat().st_size > 0:
        cached += 1
    else:
        subprocess.run(["curl", "-sfLm60", "-o", str(dst), url], check=False)
        if not dst.exists() or dst.stat().st_size == 0:
            dst.unlink(missing_ok=True)
            s.pop("icon", None)
            missing += 1
            continue
        got += 1
        time.sleep(0.3)
    s["icon"] = "img/skills/" + fn

WIKI.write_text(json.dumps(wiki, ensure_ascii=False, separators=(",", ":")), "utf-8")
print(f"新下載 {got}、已存在 {cached}、抓不到 {missing}")
