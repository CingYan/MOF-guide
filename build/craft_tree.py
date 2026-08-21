#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
製作材料遞迴展開建置腳本。

背景：docs/data/recipes.json 裡的 517 筆配方，很多中間材料（例如「鋼鐵塊」）
本身又有自己的配方，而且同一個中間材料常常被好幾個不同的父配方同時用到
（例如「暴風之眼」本體、「他馬思克斯」、「米絲麗」都需要鋼鐵塊）。
如果每個分支各自展開、各自無條件無條件除以單次產出數再無條件進位，
會導致同一種材料被重複「進位」好幾次，算出來的採集/製作數量會偏多、不準。

所以這裡分成兩個獨立的資料結構來解決兩件不同的事：

1. tree：純粹給人看的「配方結構圖」。每個節點的 count 就是「父配方裡寫的
   單次用量」，不會被祖先要做幾次而放大。這樣使用者展開樹狀圖時，看到的
   數字跟遊戲內配方介面上看到的一樣，不會因為深層路徑而膨脹到失真。

2. totals：真正要拿去買/打/做幾次的「跨全樹加總」結果。做法是把整棵樹
   看成一個有向無環圖（同一個材料 id 只會有一個節點，即使被多個父節點
   引用），用拓樸排序保證「所有會需要某材料的父節點都處理完，才去看該
   材料總共被要求多少」，再統一對總量做 ceil(需求/單次產出) 決定要做幾次，
   接著把這次數乘上該配方的所有原料用量，繼續往下加總。這樣不管一個材料
   被幾個地方引用，都只會在最後「一次性」決定要做幾輪。

同一個最終產物常常有好幾張配方（例如「鋼鐵塊」有 7 張配方，產出數從 1 到
18 都有）。往下展開「中間材料要用哪張配方」時，選「單次產出數最高」的那
一張當作代表配方（這是目測最貼近玩家試算表邏輯的選擇：試算表裡鋼鐵塊用的
正是產出 18 個、用瓢蟲將軍的殼＋牛魔王的鐵鎚破那張配方，剛好就是本資料裡
產出數最高的版本）。至於「頂層要展開的是哪張配方」則不做這個代表配方的
篩選，永遠用 recipes.json 裡那一筆自己的原料表——因為 output 裡本來就會
針對「鋼鐵塊 製造方法」「製作法-鋼鐵塊18個」等每一張配方各自產生一筆
entry，使用者要哪張配方的展開結果，就點哪張。
"""
import json
import math
import os
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "docs", "data")
OUT_PATH = os.path.join(DATA_DIR, "craft.json")

GENERATED_FOR = 1  # 固定以「做 1 個」為基準展開，倍率交給前端乘。
MAX_SOURCES = 6  # sources 裡每一類最多列幾筆。


def load_json(name):
    with open(os.path.join(DATA_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def build_item_index(items, equips):
    """把 items.json 跟 equips.json 合併成 id -> 記錄 的查詢表。

    兩份資料的 id 命名空間彼此不重疊（實測交集為 0），所以可以放心合併，
    這樣不管原料 id 落在哪一份檔案裡都能一次查到。
    """
    index = {}
    for rec in items:
        index[rec["id"]] = rec
    for rec in equips:
        index[rec["id"]] = rec
    return index


def build_recipe_index(recipes):
    """依 result.id 分組，並挑出每個材料的「代表配方」（單次產出數最高者）。

    這一步只服務「往下展開中間材料時要用哪張配方」，跟「頂層 entry 本身要
    展開哪張配方」是兩件事——頂層一律用該 entry 自己的原料表。
    """
    by_result = defaultdict(list)
    for r in recipes:
        by_result[r["result"]["id"]].append(r)

    canonical = {}
    for result_id, group in by_result.items():
        # 單次產出數最高優先；產出數相同時用 id 排序取最小值，確保結果穩定可重跑。
        best = sorted(group, key=lambda r: (-r["result"]["count"], r["id"]))[0]
        canonical[result_id] = best
    return by_result, canonical


def get_sources(item_id, item_index):
    """從 items.json / equips.json 撈葉材料的取得方式（怪物掉落 / NPC 販售 / 地圖掉落）。

    droppedBy 跟 mapDrops 依 rate 由高到低排序後取前 MAX_SOURCES 筆，
    這樣使用者優先看到的是命中率最高、最實際的取得管道；soldBy 沒有
    掉落率欄位，維持原始順序取前 MAX_SOURCES 筆即可。查無此 id 或該
    id 沒有對應資料時，三個欄位都給空陣列。
    """
    rec = item_index.get(item_id)
    if rec is None:
        return {"monsters": [], "npcs": [], "maps": []}

    dropped_by = sorted(rec.get("droppedBy") or [], key=lambda d: -d.get("rate", 0))
    map_drops = sorted(rec.get("mapDrops") or [], key=lambda d: -d.get("rate", 0))
    sold_by = rec.get("soldBy") or []

    def names(seq, limit=MAX_SOURCES):
        out = []
        for entry in seq:
            n = entry.get("name")
            if n and n not in out:
                out.append(n)
            if len(out) >= limit:
                break
        return out

    return {
        "monsters": names(dropped_by),
        "npcs": names(sold_by),
        "maps": names(map_drops),
    }


def build_tree(item_id, item_name, count, recipe, canonical, item_index, ancestors, cycles_out):
    """遞迴組出純顯示用的配方結構樹（不做跨節點加總，count 就是父配方寫的用量）。

    ancestors：目前這條路徑上已經展開過的材料 id 集合，用來偵測環狀配方
    （A 需要 B、B 又需要 A 這種）。偵測到就記錄進 cycles_out 並把這個節點
    當成「無法再展開」處理（children 直接留空），不繼續遞迴，避免炸堆疊。
    """
    craftable = recipe is not None
    node = {
        "name": item_name,
        "count": count,
        "craftable": craftable,
        "children": [],
    }
    if craftable:
        node["yield"] = recipe["result"]["count"]

    if not craftable:
        return node

    if item_id in ancestors:
        # 環狀：這個材料的展開路徑上，自己又出現了自己。中止這個分支即可，
        # 不要無限遞迴；同時記一筆環狀警告方便事後排查資料問題。
        path = " -> ".join(ancestors_names(ancestors, item_index) + [item_name])
        cycles_out.append({"itemId": item_id, "itemName": item_name, "path": path})
        node["craftable"] = False
        node["children"] = []
        node.pop("yield", None)
        return node

    ancestors = ancestors + (item_id,)
    for ing in recipe["ingredients"]:
        child_recipe = canonical.get(ing["id"])
        node["children"].append(
            build_tree(
                ing["id"], ing["name"], ing["count"], child_recipe,
                canonical, item_index, ancestors, cycles_out,
            )
        )
    return node


def ancestors_names(ancestor_ids, item_index):
    # 只用來拼 cycles 訊息裡的路徑文字，查不到名字就退回顯示 id。
    # ancestor_ids 用 tuple（依展開順序）而非 set，這樣路徑文字才會照實際
    # 遞迴順序顯示，方便事後排查是哪一條路徑造成環狀。
    out = []
    for aid in ancestor_ids:
        rec = item_index.get(aid)
        out.append(rec["name"] if rec else aid)
    return out


def tree_depth(node):
    if not node["children"]:
        return 1
    return 1 + max(tree_depth(c) for c in node["children"])


def compute_totals(root_id, root_recipe, canonical, item_index, generated_for, cycles_out, root_name):
    """跨全樹加總版本：用拓樸排序保證每個材料的「總需求」在被進一步展開前，
    已經收齊所有會用到它的父節點的貢獻，這樣 ceil(總需求/單次產出) 才只會
    對真正的總量取一次進位，不會因為分支各自算各自而重複多算。

    做法：
      1. 從根節點開始 DFS，把「這棵樹會用到哪些材料、材料之間的父子關係」
         建成一個有向無環圖（edges：父材料 id -> [(子材料 id, 單次用量), ...]）。
         用 on_stack 偵測環狀配方，偵測到就記錄並中止該分支（不建立那條邊）。
      2. 對這個圖做拓樸排序（父節點一定排在子節點前面）。
      3. 依拓樸順序處理每個材料：這時候它的總需求已經收完所有父節點的貢獻，
         若可製作就算出要做幾次（ceil），把「次數 x 該配方每種原料用量」
         加進對應子材料的總需求；若不可製作（葉節點）就直接記為最終需求。
    """
    edges = defaultdict(list)  # item_id -> [(child_id, child_name, child_icon, per_craft_count)]
    craftable_recipe = {}  # item_id -> recipe（該材料在這棵樹裡實際使用的配方）
    expanded = set()

    def expand(item_id, recipe, ancestors):
        if item_id in expanded:
            return
        if recipe is None:
            expanded.add(item_id)
            return
        if item_id in ancestors:
            path = " -> ".join(ancestors_names(ancestors, item_index))
            cycles_out.append({
                "itemId": item_id,
                "itemName": item_index.get(item_id, {}).get("name", item_id),
                "path": f"{path} -> {item_index.get(item_id, {}).get('name', item_id)}",
            })
            return
        craftable_recipe[item_id] = recipe
        next_ancestors = ancestors + (item_id,)
        for ing in recipe["ingredients"]:
            child_recipe = canonical.get(ing["id"])
            edges[item_id].append((ing["id"], ing["name"], ing["icon"], ing["count"]))
            expand(ing["id"], child_recipe, next_ancestors)
        expanded.add(item_id)

    expand(root_id, root_recipe, ())

    # 拓樸排序（DFS post-order 反轉）：對 DAG 一定合法，且不受「哪個父節點先
    # 走到某個共用子節點」影響，多個父節點共用同一子節點也只會處理它一次。
    order = []
    visited = set()

    def topo(u):
        if u in visited:
            return
        visited.add(u)
        for child_id, _, _, _ in edges.get(u, []):
            topo(child_id)
        order.append(u)

    topo(root_id)
    order.reverse()

    demand = defaultdict(int)
    demand[root_id] = generated_for

    leaves = {}
    intermediates = {}

    for item_id in order:
        recipe = craftable_recipe.get(item_id)
        needed = demand[item_id]
        if recipe is not None:
            yield_n = recipe["result"]["count"]
            crafts = math.ceil(needed / yield_n)
            if item_id != root_id:
                rec = item_index.get(item_id)
                intermediates[item_id] = {
                    "id": item_id,
                    "name": rec["name"] if rec else item_id,
                    "icon": rec["icon"] if rec else recipe["result"]["icon"],
                    "needed": needed,
                    "yield": yield_n,
                    "crafts": crafts,
                }
            for child_id, child_name, child_icon, per_craft in edges.get(item_id, []):
                demand[child_id] += crafts * per_craft
        else:
            if item_id == root_id:
                # 根節點本身沒有配方的情況理論上不會發生（root 一定來自
                # ingredients 非空的配方），保留防呆但不特別處理。
                continue
            rec = item_index.get(item_id)
            leaves[item_id] = {
                "id": item_id,
                "name": rec["name"] if rec else item_id,
                "icon": rec["icon"] if rec else "",
                "count": needed,
                "sources": get_sources(item_id, item_index),
            }

    leaves_list = sorted(leaves.values(), key=lambda x: (-x["count"], x["name"]))
    intermediates_list = sorted(intermediates.values(), key=lambda x: (-x["needed"], x["name"]))
    return leaves_list, intermediates_list


def main():
    recipes = load_json("recipes.json")
    items = load_json("items.json")
    equips = load_json("equips.json")

    item_index = build_item_index(items, equips)
    by_result, canonical = build_recipe_index(recipes)

    out_recipes = []
    all_cycles = []
    processed = 0

    for r in recipes:
        if not r.get("ingredients"):
            continue  # 只針對有原料的配方產生條目。

        processed += 1
        root_id = r["result"]["id"]
        root_name = r["result"]["name"]

        tree_cycles = []
        tree = build_tree(
            root_id, root_name, GENERATED_FOR, r,
            canonical, item_index, (), tree_cycles,
        )

        totals_cycles = []
        leaves_list, intermediates_list = compute_totals(
            root_id, r, canonical, item_index, GENERATED_FOR, totals_cycles, root_name,
        )

        for c in tree_cycles + totals_cycles:
            c_full = {"recipeId": r["id"], **c}
            all_cycles.append(c_full)

        out_recipes.append({
            "id": r["id"],
            "name": root_name,
            "recipeName": r["name"],
            "icon": r["result"]["icon"],
            "category": r.get("resultCategory", ""),
            "yield": r["result"]["count"],
            "successRate": r.get("successRate"),
            "depth": tree_depth(tree),
            "tree": tree,
            "totals": {
                "leaves": leaves_list,
                "intermediates": intermediates_list,
            },
        })

    output = {
        "recipes": out_recipes,
        "cycles": all_cycles,
        "generatedFor": GENERATED_FOR,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"處理了 {processed} 筆配方（總共讀入 {len(recipes)} 筆，"
          f"跳過 {len(recipes) - processed} 筆無原料配方）。")
    print(f"偵測到環狀配方 {len(all_cycles)} 筆。")
    print(f"輸出寫入 {OUT_PATH}")


if __name__ == "__main__":
    main()
