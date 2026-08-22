#!/usr/bin/env python3
"""強化階級改用遊戲內實際名稱。

系統頁的強化階級原本寫「優良 (+1) / 優秀 (+2) / 超級 (+3) / 極致 (+4) /
英雄 (+5) / 傳說 (+6)」—— 那是從 wiki 的英文（Good/Great/Super…）翻的，
遊戲裡根本不是這樣叫。

實際名稱就在站上自己的 equips.json 裡：強化後的裝備會加前綴，
例如「不滅的皇帝法杖」→ 強化的／精緻的／精煉的／完美的／無瑕的／極緻的。

證據：84 個裝備族擁有完整六階，而且六階的 id 全部嚴格遞增（84/84），
順序就是階級順序。X0157–X0162 是其中一族的連號。

注意「極緻」不是「極致」—— 原本那份翻譯連這個字都寫錯。

可重複執行。
"""
import json, pathlib

WIKI = pathlib.Path(__file__).resolve().parent.parent / "docs/data/wiki.json"

# 舊譯名 -> 遊戲內實際前綴
TIERS = {
    "優良 (+1)": "強化的 (+1)",
    "優秀 (+2)": "精緻的 (+2)",
    "超級 (+3)": "精煉的 (+3)",
    "極致 (+4)": "完美的 (+4)",
    "英雄 (+5)": "無瑕的 (+5)",
    "傳說 (+6)": "極緻的 (+6)",
}

wiki = json.loads(WIKI.read_text("utf-8"))
n = 0
for table in wiki["stones"]:
    if "強化階級" not in table["headers"]:
        continue
    col = table["headers"].index("強化階級")
    for row in table["rows"]:
        if (new := TIERS.get(row["c"][col])):
            row["c"][col] = new
            n += 1

WIKI.write_text(json.dumps(wiki, ensure_ascii=False, separators=(",", ":")), "utf-8")
print(f"強化階級改用遊戲內名稱：{n} 格")
