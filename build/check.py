#!/usr/bin/env python3
"""資料完整性檢查。改完資料就跑一次。

起因：把 LIBI 改成「利比」時，icon 路徑裡也含 LIBI，JSON 改了但磁碟檔名沒改，
五張圖直接斷掉。JSDOM 那套只驗有渲染到的頁面，抓不到沒被畫出來的資料。
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
fail = []

# ── 1. 每個 icon/image/portrait 路徑都要真的存在且非空 ──
missing = empty = total = 0
for path in sorted((DOCS / "data").glob("*.json")):
    for rel in re.findall(r'"(?:icon|image|portrait)":\s*"(img/[^"]+)"', path.read_text("utf-8")):
        total += 1
        f = DOCS / rel
        if not f.exists():
            missing += 1; fail.append(f"圖不存在 {path.name}: {rel}")
        elif f.stat().st_size == 0:
            empty += 1; fail.append(f"圖是空檔 {path.name}: {rel}")
print(f"圖片路徑 {total} 個 / 不存在 {missing} / 空檔 {empty}")

# ── 2. 交叉參照的 id 都要解得開 ──
def ids(name):
    try:
        return {x["id"] for x in json.loads((DOCS / "data" / f"{name}.json").read_text("utf-8")) if "id" in x}
    except FileNotFoundError:
        return set()

TABLES = {"mapId": ids("maps"), "monsterId": ids("monsters"),
          "itemId": ids("items"), "npcId": ids("npcs")}
for path in sorted((DOCS / "data").glob("*.json")):
    text = path.read_text("utf-8")
    for key, valid in TABLES.items():
        if not valid:
            continue
        bad = {i for i in re.findall(r'"%s":\s*"([^"]+)"' % key, text) if i not in valid}
        if bad:
            fail.append(f"{path.name} 的 {key} 查無此 id: {sorted(bad)[:5]}")

# ── 3. 不該再出現的英文單位 ──
for path in sorted((DOCS / "data").glob("*.json")):
    for word in ("Libi", "LIBI"):
        n = len(re.findall(r"\b%s\b" % word, path.read_text("utf-8")))
        if n:
            fail.append(f"{path.name} 還有 {n} 處未翻的「{word}」")

if fail:
    print("\n❌ 檢查未通過：")
    for f in fail:
        print("  ", f)
    sys.exit(1)
print("✅ 全部通過")
