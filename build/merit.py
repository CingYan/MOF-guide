#!/usr/bin/env python3
"""功勳（戰爭任務點數）獨立成頁。

原本只是社群頁裡的一個小段落，但功勳是專業技能點數的主要來源之一，
值得單獨一頁。

階級表有兩份來源、互相對不起來，兩份都保留讓人自己判斷：

  獎勵點數完全一致：2,2,2,3,3,3,4,4,4,5（十階逐階對應）
  門檻不同：中文那份是 100/300/500/1000/1800/3000/4700/7000/10000/14000，
            站上原本那份多數 +100
  站上原本那份自己有矛盾：「7,100-10,999」和「10,100-13,999」區間重疊

中文階級名補上了原本翻不出來的兩個（Chargeman -> 突襲隊員、
Pro-Guard -> 親衛兵）—— 依十階的順序對位，兩份的獎勵點數逐階相同，
順序對應是可靠的。

專業技能點數的三個來源也一併整理：功勳、學年考試、PvP。
"""
import json, pathlib

DATA = pathlib.Path(__file__).resolve().parent.parent / "docs/data"
social = json.loads((DATA / "social.json").read_text("utf-8"))["warTask"]

# 中文玩家攻略記載的階級表（2008-02-20，巴哈精華區）
ZH = [(100, "一般兵", 2), (300, "突襲隊員", 2), (500, "特遣隊員", 2),
      (1000, "精銳兵", 3), (1800, "親衛兵", 3), (3000, "低階軍官", 3),
      (4700, "高階軍官", 4), (7000, "軍官", 4), (10000, "司令官", 4),
      (14000, "英雄", 5)]

# 站上原有那份（來自現行資料）：階級名 + 門檻，去掉「0-99 學生」那列才對得齊
rows = social["tables"][0]["rows"][1:]
cur = [r[1] for r in rows]
cur_th = [r[0] for r in rows]

tiers = [{"n": i + 1, "zhPoint": p, "zhName": nm, "skillPoints": sp,
          "altName": cur[i] if i < len(cur) else "",
          "altRange": cur_th[i] if i < len(cur_th) else ""}
         for i, (p, nm, sp) in enumerate(ZH)]

out = {
    "title": "功勳",
    "en": "War Task",
    "intro": social["sections"][0]["body"],
    "supply": social["sections"][1]["body"],
    "quota": social["sections"][0].get("items") or [],
    "tiers": tiers,
    "note": "階級表有兩份來源。獎勵點數十階逐階完全相同，但升階門檻不一樣，"
            "而且站上原有那份自己有區間重疊（7,100–10,999 與 10,100–13,999）。"
            "兩份都列出來，不替你決定信哪一份。",
    "sources": [
        {"of": "專業技能點數", "from": "功勳", "detail": "每升一個功勳階級給 2～5 點，十階共 32 點。"},
        {"of": "專業技能點數", "from": "學年考試", "detail": "每通過一個學年給 2 點。"},
        {"of": "專業技能點數", "from": "PvP", "detail": "對戰也能取得，玩家攻略有記載。"},
    ],
    "terms": [
        {"zh": "功勳", "alt": "功績", "note": "玩家慣用「功勳」；同一篇攻略裡也寫作「功績」。"},
        {"zh": "專攻點數", "alt": "專業技能點數", "note": "玩家慣用「專攻點數」，站上技能頁用「專業技能」。"},
    ],
}
(DATA / "merit.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
print(f"功勳頁資料：{len(tiers)} 階、{len(out['sources'])} 個點數來源")
print(f"  總計專業技能點數（功勳滿階）：{sum(t['skillPoints'] for t in tiers)} 點")
