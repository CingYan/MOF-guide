#!/usr/bin/env python3
"""把強化石表的「圖示」欄接上 items.json 既有的圖與道具頁。

wiki 的石頭表原本每列帶一個 img 檔名（Pillar_Stone.png），但那批圖從來沒抓下來，
所以「圖示」欄一直只是把名稱再印一次。items.json 裡本來就有這些石頭、也有圖，
用名稱對起來即可，不需要另外去抓圖。

可重複執行：只寫 icon / itemId 兩個欄位，對不到就不寫（保持缺就是缺）。
"""
import json, os, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs/data/wiki.json"
ITEMS = ROOT / "docs/data/items.json"

wiki = json.loads(WIKI.read_text("utf-8"))
by_name = {i["name"]: i for i in json.loads(ITEMS.read_text("utf-8"))}

hit = miss = 0
for table in wiki["stones"]:
    if not table["headers"] or table["headers"][0] != "圖示":
        continue                      # 只有前兩張是石頭清單，後兩張是強化效果表
    for row in table["rows"]:
        item = by_name.get(row["c"][1])
        if not item or not item.get("icon"):
            row.pop("icon", None); row.pop("itemId", None)
            miss += 1
            continue
        assert (ROOT / "docs" / item["icon"]).exists(), f'圖不存在：{item["icon"]}'
        row["icon"] = item["icon"]
        if item.get("id"):
            row["itemId"] = item["id"]
        hit += 1

WIKI.write_text(json.dumps(wiki, ensure_ascii=False, separators=(",", ":")), "utf-8")
print(f"強化石接上圖示：{hit} 列；items.json 查無對應（維持沒有圖）：{miss} 列")
