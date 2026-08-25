#!/usr/bin/env python3
"""把鑰匙副本加進練功排行。

原本 120 張副本房間圖一張都沒進排行，因為 maps.json 裡那些房間沒有怪物資料。
但 dungeons.json 有，而且帶隻數（幽靈海賊 x50），比一般地圖的資料還完整。

以「一場副本」為單位，不是以房間為單位 —— 你進去是打完整場，不是打單一房間。
所以名稱就是「眾多海賊船」「無限竹林」這種。

兩種數字都算：
  效率      每點 HP 換到多少經驗，跟一般地圖同一個口徑，可以直接比
  整場總量  跑完一趟能拿多少經驗、要打掉多少 HP（只有算得出來的才給）

無限型沒有隻數是正確的，怪物無限湧出本來就沒有總量，那種只給效率。
既有那 78 筆「副本」是 D#### 的野外型地下城（達連廢礦），跟這裡無關。

可重複執行：先移除自己上次加的，再重算。
"""
import json, pathlib

DATA = pathlib.Path(__file__).resolve().parent.parent / "docs/data"
load = lambda n: json.loads((DATA / f"{n}.json").read_text("utf-8"))

TYPE = "副本鑰匙"
mons = {m["id"]: m for m in load("monsters")}
dung = load("dungeons")["dungeons"]
grind = [g for g in load("grind") if g.get("type") != TYPE]

added = 0
for group in dung["groups"]:
    for run in group.get("runs") or []:
        mlist, total_exp, total_hp, counted = [], 0, 0, True
        for m in run.get("monsters") or []:
            src = mons.get(m["monsterId"])
            if not src or not src.get("exp"):
                counted = False
                continue
            c = m.get("count")
            if c is None:
                counted = False
            mlist.append({"id": m["monsterId"], "name": m["name"], "level": m["level"],
                          "hp": m["hp"], "exp": src["exp"], "icon": m.get("icon"),
                          **({"count": c} if c else {})})
            total_exp += src["exp"] * (c or 0)
            total_hp += m["hp"] * (c or 0)
        if not mlist:
            continue

        boss = run.get("boss")
        bsrc = mons.get((boss or {}).get("monsterId")) if boss else None
        if boss and bsrc and bsrc.get("exp"):
            mlist.append({"id": boss["monsterId"], "name": boss["name"], "level": boss["level"],
                          "hp": boss["hp"], "exp": bsrc["exp"], "icon": boss.get("icon"),
                          "count": 1, "boss": True})
            total_exp += bsrc["exp"]
            total_hp += boss["hp"]

        # 效率用「每點 HP 換到多少經驗」，跟一般地圖同口徑；有隻數就依隻數加權。
        # 無限型沒有隻數：雜怪無限湧出、頭目只有一隻，若用 count 預設 1 讓兩者等權，
        # 單一頭目的高經驗會把整場效率灌爆（無限暗黑樹林曾因此排到全站第一）。
        # 所以隻數不全時，效率只用雜怪算；頭目仍留在清單裡，另由排除頭目欄處理。
        regs = [m for m in mlist if not m.get("boss")]
        weighted = bool(regs) and all(m.get("count") for m in regs)
        pool = mlist if weighted else (regs or mlist)
        w = [(m, m.get("count", 1)) for m in pool]
        exp = sum(m["exp"] * c for m, c in w) / sum(c for _, c in w)
        hp = sum(m["hp"] * c for m, c in w) / sum(c for _, c in w)
        money = sum((mons[m["id"]].get("money") or {}).get("amount", 0) * c for m, c in w) / sum(c for _, c in w)
        aggr = sum(1 for m in pool if (mons.get(m["id"]) or {}).get("aggressive"))

        row = {
            "id": (run.get("maps") or [{}])[0].get("mapId", group["id"]),
            "name": run["typeName"] + group["name"],
            "region": (group.get("continent") or {}).get("name", ""),
            "levelReq": 0, "type": TYPE,
            "avgLv": round(sum(m["level"] for m in mlist) / len(mlist), 1),
            "kinds": len(mlist),
            "exp": round(exp), "hp": round(hp), "eff": round(exp / hp, 3) if hp else 0,
            "money": round(money), "aggressive": aggr,
            "effBasis": "counted" if weighted else "trash",
            "monsters": mlist,
        }
        if counted and total_hp:
            row["runExp"] = total_exp
            row["runHp"] = total_hp
        grind.append(row)
        added += 1

grind.sort(key=lambda g: -g.get("eff", 0))
(DATA / "grind.json").write_text(json.dumps(grind, ensure_ascii=False, separators=(",", ":")), "utf-8")
full = sum(1 for g in grind if g.get("type") == TYPE and g.get("runExp"))
print(f"加入副本 {added} 場（其中 {full} 場算得出整場總量，其餘是無限型）")
