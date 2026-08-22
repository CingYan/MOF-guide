#!/usr/bin/env python3
"""把全站搜尋索引同步回現行資料。

原本產生索引的 build/split.py 讀的是 docs/data/mof.json，那個檔在資料管線
改版後就不存在了，重跑會把資料洗掉，所以不能用。這支只做同步，不重建：

  1. 名稱：依 id 從各分區檔取現行名稱（例如 Mithril -> 祕銀改名後）
  2. 已合併掉的條目：NPC 合併後被併走的 id 不再是主鍵，索引要跟著刪，
     否則搜尋會跑出 101 筆重複的 NPC
  3. 現行資料有、索引沒有的條目：補進去

摘要欄（第 4 欄）維持原樣，那是索引自己的格式，跟名稱無關。
可重複執行。
"""
import json, pathlib

DATA = pathlib.Path(__file__).resolve().parent.parent / "docs/data"
load = lambda n: json.loads((DATA / f"{n}.json").read_text("utf-8"))

# 索引類型代號 -> 分區檔
KIND = {"m": "monsters", "p": "maps", "e": "equips", "f": "fashion",
        "i": "items", "r": "recipes", "q": "quests", "n": "npcs"}

names, order = {}, {}
for k, src in KIND.items():
    for i, row in enumerate(load(src)):
        if isinstance(row, dict) and row.get("id"):
            names[(k, row["id"])] = row.get("name", "")
            order[(k, row["id"])] = i

idx = load("index")
out, dropped, renamed = [], 0, 0
for row in idx:
    key = (row[0], row[1])
    if key not in names:          # 已被合併掉或已不存在
        dropped += 1
        continue
    if row[2] != names[key]:
        row[2] = names[key]
        renamed += 1
    out.append(row)

have = {(r[0], r[1]) for r in out}
added = 0
for key, nm in names.items():
    if key not in have:
        out.append([key[0], key[1], nm, ""])
        added += 1

(DATA / "index.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
print(f"索引 {len(idx)} -> {len(out)} 筆（改名 {renamed}、移除已合併 {dropped}、補上 {added}）")
