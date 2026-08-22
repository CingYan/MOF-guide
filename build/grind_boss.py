#!/usr/bin/env python3
"""替練功排行標出頭目，並另算一份「排除頭目」的效率。

怪物資料本來就有 bossRank：0 一般（268 隻）、1 BOSS（17 隻）、2 小 BOSS（11 隻）。

為什麼要另算一份效率：頭目 HP 動輒上萬、經驗也高，混進平均會把整張圖的
效率撐歪，但你未必打得動、也未必打得到（多數頭目有重生時間）。所以
同時給兩個數字，讓人自己挑要看哪個。

只有一般怪的地圖兩個數字相同；整張圖只有頭目的（例如頭目房）排除後
沒有怪可算，effNoBoss 就留空。

要在 build/grind_dungeons.py 之後跑（它會重寫 grind.json）。可重複執行。
"""
import json, pathlib

DATA = pathlib.Path(__file__).resolve().parent.parent / "docs/data"
mons = {m["id"]: m for m in json.loads((DATA / "monsters.json").read_text("utf-8"))}
grind = json.loads((DATA / "grind.json").read_text("utf-8"))

RANK = {1: "boss", 2: "miniBoss"}
for g in grind:
    plain, nb, nmb = [], 0, 0
    for m in g.get("monsters") or []:
        r = (mons.get(m["id"]) or {}).get("bossRank", 0)
        if r == 1:
            nb += 1
        elif r == 2:
            nmb += 1
        else:
            plain.append(m)
    g["boss"] = nb
    g["miniBoss"] = nmb
    g["bossTag"] = "有頭目" if nb else ("有小頭目" if nmb else "無頭目")

    # 排除頭目後重算：有隻數就依隻數加權，跟原本同口徑
    if plain and len(plain) != len(g.get("monsters") or []):
        w = [(m, m.get("count", 1)) for m in plain]
        tot = sum(c for _, c in w)
        exp = sum(m["exp"] * c for m, c in w) / tot
        hp = sum(m["hp"] * c for m, c in w) / tot
        g["expNoBoss"] = round(exp)
        g["hpNoBoss"] = round(hp)
        g["effNoBoss"] = round(exp / hp, 3) if hp else 0
    elif plain:
        g["expNoBoss"], g["hpNoBoss"], g["effNoBoss"] = g["exp"], g["hp"], g["eff"]
    else:
        for k in ("expNoBoss", "hpNoBoss", "effNoBoss"):
            g.pop(k, None)

(DATA / "grind.json").write_text(json.dumps(grind, ensure_ascii=False, separators=(",", ":")), "utf-8")
import collections
c = collections.Counter(g["bossTag"] for g in grind)
print("地圖分類:", dict(c))
shift = [g for g in grind if g.get("effNoBoss") is not None and abs(g["effNoBoss"] - g["eff"]) > 0.3]
print(f"排除頭目後效率變動超過 0.3 的地圖：{len(shift)}")
for g in sorted(shift, key=lambda x: -abs(x["effNoBoss"] - x["eff"]))[:6]:
    print(f"   {g['name']:<16}{g['eff']:>6} -> {g['effNoBoss']:<7}（{g['boss']} 頭目 / {g['miniBoss']} 小頭目）")
