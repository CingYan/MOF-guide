#!/usr/bin/env python3
"""站主實機確認過的寵物等級效果，補標成已驗證。

寵物的 verified 欄位原本來自 tmp/mof-pets/*.csv 的「已實機驗證」欄，
但那批 CSV 已經不在了，所以改用這裡的明確表格，並把出處寫清楚。

只動 verified 標記，效果數值一個字都不改 —— 這裡記錄的是「誰確認過」，
不是「數值是多少」。若哪天實測值與站上不符，那要另外處理，不是在這裡改。

可重複執行。
"""
import json, pathlib

PETS = pathlib.Path(__file__).resolve().parent.parent / "docs/data/pets.json"

# 寵物名 -> {等級: 出處}
CONFIRMED = {
    "麻吉": {
        6: "2026-08-22 站主遊戲內截圖：Lv6 基本技能「增加技能攻擊力 6%」",
        **{lv: "2026-08-22 站主回報實機確認，與站上數值相符（無截圖）" for lv in range(1, 6)},
    },
}

pets = json.loads(PETS.read_text("utf-8"))
n = 0
for pet in pets["pets"]:
    conf = CONFIRMED.get(pet["name"])
    if not conf:
        continue
    for lv in pet["levels"]:
        if lv["lv"] in conf and not lv.get("verified"):
            lv["verified"] = True
            n += 1
    # 重算「實機驗證到」摘要：取已驗證等級的連續區間寫法
    done = sorted(l["lv"] for l in pet["levels"] if l.get("verified"))
    if done:
        runs, start, prev = [], done[0], done[0]
        for v in done[1:]:
            if v != prev + 1:
                runs.append((start, prev)); start = v
            prev = v
        runs.append((start, prev))
        pet["verified"] = "、".join(f"Lv{a}" if a == b else f"Lv{a}–{b}" for a, b in runs)

PETS.write_text(json.dumps(pets, ensure_ascii=False, separators=(",", ":")), "utf-8")
print(f"補標已驗證：{n} 個等級")
for p in pets["pets"]:
    if p.get("verified"):
        print(f'   {p["name"]:<8}{p["verified"]}')
