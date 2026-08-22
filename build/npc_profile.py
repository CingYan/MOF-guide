#!/usr/bin/env python3
"""把 NPC 的 desc 解析成結構化個人檔案。

desc 本來就是「姓名/年齡/血型/身高/體重」加上職業、興趣、特技、性向、性格、
座右銘幾個欄位，但上游的分隔符號寫法很亂：冒號後有時有空格有時沒有、有時用
全形冒號、有時整個冒號不見、有時連欄位名都不見只剩內容、還有欄位名打錯字
（座右名／特級）和整行只剩一個句點的殘留。

解析成欄位之後，冒號怎麼寫都不影響顯示。

只正規化「欄位名」，內容一個字都不動 —— 內容裡的錯字（精常準備、勤免）是
原始資料的一部分，不是我該改的東西。原始 desc 也原封保留。
可重複執行。
"""
import json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
NPCS = ROOT / "docs/data/npcs.json"

# 欄位名的正規寫法 -> 上游出現過的各種寫法（含錯字）
ALIASES = {
    "職業": ["職業", "職葉"],
    "興趣": ["興趣"],
    "特技": ["特技", "特級"],
    "性向": ["性向"],
    "性格": ["性格"],
    "座右銘": ["座右銘", "座右名", "座右鳴"],
    # 非人物 NPC（公會金庫、前哨基地隊長之類）用的另一組欄位
    "位置": ["位置"], "信念": ["信念"], "專長": ["專長"], "現況": ["現況"],
    "容量": ["容量"], "用途": ["用途"], "規矩": ["規矩"],
}
LOOKUP = {a: k for k, v in ALIASES.items() for a in v}
# 冒號可有可無、可半形可全形、前後空白隨意
LABEL = re.compile(r"^\s*(%s)\s*[:：]?\s*(.*?)\s*$" % "|".join(sorted(LOOKUP, key=len, reverse=True)))
# 檔案頭本身也有一堆變體：年齡血型寫成「?」、體重寫「秘密」、身高前後有空白、
# 還有把血型 O 打成數字 0 的。判準放寬成「五段斜線、第四段是身高」，
# 各段內容原樣保留，不去猜也不去補。
CM = re.compile(r"^[\d.]+\s*[Cc][Mm]$")
def parse_head(line):
    parts = [p.strip() for p in line.split("/")]
    if len(parts) != 5 or not CM.match(parts[3]):
        return None
    return dict(zip(("name", "age", "blood", "height", "weight"), parts))

npcs = json.loads(NPCS.read_text("utf-8"))
n_head = n_trait = n_note = n_fixed = 0

for x in npcs:
    for k in ("profile", "traits", "notes"):
        x.pop(k, None)
    lines = [l.strip() for l in (x.get("desc") or "").split("\n")]
    lines = [l for l in lines if l and l != "."]        # 只剩一個句點的殘留行丟掉
    if not lines:
        continue

    if (h := parse_head(lines[0])):
        x["profile"] = h
        lines = lines[1:]
        n_head += 1

    traits, notes = [], []
    for l in lines:
        if (m := LABEL.match(l)) and m[2]:
            key = LOOKUP[m[1]]
            if m[1] != key:
                n_fixed += 1                            # 欄位名打錯字，正規化
            traits.append({"k": key, "v": m[2]})
        else:
            # 欄位名整個不見（只剩內容）或欄位名是「??」—— 不猜它原本屬於哪一欄
            notes.append(re.sub(r"^[.\s]*(\?\?\s*[:：])?\s*", "", l))
    if traits:
        x["traits"] = traits; n_trait += len(traits)
    if notes:
        x["notes"] = notes; n_note += len(notes)

NPCS.write_text(json.dumps(npcs, ensure_ascii=False, separators=(",", ":")), "utf-8")
print(f"檔案頭 {n_head} 個 / 欄位 {n_trait} 筆（其中欄位名打錯字正規化 {n_fixed} 筆）/ 無欄位名的內容行 {n_note} 筆")
