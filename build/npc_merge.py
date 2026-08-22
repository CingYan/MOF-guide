#!/usr/bin/env python3
"""合併重複的 NPC，並把散在各檔的販售清單灌回 NPC。

站主 2026-08-22 核定的三條規則：
  1. 同名且販售、任務、角色標籤三者完全相同 -> 併成一筆，底下列出所有地點
  2. 任一項不同 -> 保留為獨立條目（真的是不同個體，例如決鬥場的流浪商人賣
     PvP 稱號、學習之路程的賣 48 種時裝）
  3. S 系列併進同名的 N

關於 S 系列：先前誤判成空殼。實際上 S 是同一個 NPC 的「裝備／飾品店」那一面，
equips.json 有 446 筆 soldBy 指向 S 系列（例如 S0046 杜尼賣力量項鍊）。
NPC 的 sells 欄位當初只從 items.json 灌，沒灌 equips/fashion/recipes，
所以 S 看起來才像空的。這裡一併補回來。

被併掉的 id 不會消失：全部登記在 aliasIds，前端查 id 時會一併解析，
所以其他檔案既有的 2,000 多筆參照一個都不會斷。
"""
import json, pathlib, collections

DATA = pathlib.Path(__file__).resolve().parent.parent / "docs/data"
load = lambda n: json.loads((DATA / f"{n}.json").read_text("utf-8"))

npcs = load("npcs")
by_id = {x["id"]: x for x in npcs}

# ── 1. 把各檔的「誰在賣」灌回 NPC ──────────────────────────────────────
extra = collections.defaultdict(dict)          # npcId -> {itemId: 一筆販售紀錄}
for src, kind in (("equips", "equips"), ("fashion", "fashion"), ("items", "items")):
    for row in load(src):
        for s in row.get("soldBy") or []:
            if s["id"] in by_id:
                rec = {"id": row["id"], "name": row["name"], "kind": kind}
                if row.get("icon"):
                    rec["icon"] = row["icon"]
                if s.get("price"):
                    rec["price"] = s["price"]
                extra[s["id"]][row["id"]] = rec
filled = 0
for npc in npcs:
    got = extra.get(npc["id"])
    if not got:
        continue
    have = {s["id"] for s in npc.get("sells") or []}
    add = [v for k, v in got.items() if k not in have]
    if add:
        npc.setdefault("sells", []).extend(add)
        filled += len(add)

# ── 2. 依規則分組 ─────────────────────────────────────────────────────
def sig(x):
    return (tuple(sorted(s["id"] for s in x.get("sells") or [])),
            tuple(sorted(q["id"] for q in x.get("quests") or [])),
            tuple(sorted(x.get("roleLabels") or [])))

# S 先歸到同名的 N（S 沒有地點/任務，只帶商店角色與販售）
n_by_name = collections.defaultdict(list)
for x in npcs:
    if x["id"][0] == "N":
        n_by_name[x["name"]].append(x)

groups, orphan_s = collections.defaultdict(list), []
for x in npcs:
    if x["id"][0] == "S":
        if n_by_name.get(x["name"]):
            groups[("S->N", x["name"])].append(x)
        else:
            orphan_s.append(x)
    else:
        groups[(x["name"], sig(x))].append(x)

def merge(head, rest):
    """把 rest 併進 head：地點、販售、任務、角色標籤取聯集，id 登記為別名。"""
    for other in rest:
        head.setdefault("aliasIds", []).append(other["id"])
        for field, key in (("maps", lambda m: (m["id"], m.get("x"), m.get("y"))),
                           ("sells", lambda s: s["id"]),
                           ("quests", lambda q: q["id"]),
                           ("questRewards", lambda q: q["id"])):
            have = {key(i) for i in head.get(field) or []}
            for i in other.get(field) or []:
                if key(i) not in have:
                    head.setdefault(field, []).append(i); have.add(key(i))
        head["roleLabels"] = sorted(set(head.get("roleLabels") or []) |
                                    set(other.get("roleLabels") or []))
        head["roles"] = sorted(set(head.get("roles") or []) | set(other.get("roles") or []))
        if not head.get("desc") and other.get("desc"):
            head["desc"] = other["desc"]

out, merged_n, merged_s = [], 0, 0
for (a, _), g in groups.items():
    if a == "S->N":
        continue                                   # S 稍後併進 N，不獨立成列
    head, rest = g[0], g[1:]
    if rest:
        merge(head, rest); merged_n += len(rest)
    out.append(head)

# S 併進同名 N：挑「商店角色標籤重疊最多」的那一筆當歸屬，避免併錯個體
for (a, name), g in groups.items():
    if a != "S->N":
        continue
    cands = [x for x in out if x["name"] == name and x["id"][0] == "N"]
    for s in g:
        want = set(s.get("roleLabels") or [])
        head = max(cands, key=lambda c: len(want & set(c.get("roleLabels") or []))) if cands else None
        if head is None:
            out.append(s); continue
        merge(head, [s]); merged_s += 1
out.extend(orphan_s)

out.sort(key=lambda x: x["id"])
(DATA / "npcs.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
print(f"補回販售 {filled} 筆")
print(f"NPC {len(npcs)} -> {len(out)} 筆（N 內部合併 {merged_n}、S 併入 {merged_s}、無對應 S {len(orphan_s)}）")
print(f"登記別名 {sum(len(x.get('aliasIds') or []) for x in out)} 個")
