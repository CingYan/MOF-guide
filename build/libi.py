#!/usr/bin/env python3
"""把貨幣單位 Libi 改成中文「利比」，並統一千分位。

Libi 是遊戲貨幣，中文版就叫「利比」—— 巴哈那 554 篇裡「利比」出現 503 次，
全部是任務獎勵單位（「EXP360，利比550」），而「金幣」只有 2 次。它跟起始地
「利比村莊」同名（韓文 리비）。

原始資料留了兩種千分位：逗號式（1,000）和印尼式的句點（1.000）。已驗證所有
句點後面一律是三位數，沒有一個是小數點，所以可以安全換算。

這支是後處理，要在其他 build 腳本之後跑（跟 normalize_text.py 同性質）。
可重複執行：已經是「利比」的不會再被動到。
"""
import pathlib, re

DATA = pathlib.Path(__file__).resolve().parent.parent / "docs/data"

def fix(m):
    num = m.group(1)
    if num:
        # 句點式千分位（1.000 / 20.000）換成逗號式，再統一重排
        plain = num.replace(".", "").replace(",", "")
        num = f"{int(plain):,}" if plain.isdigit() else num
        return f"{num} 利比"
    return "利比"

total = 0
for path in sorted(DATA.glob("*.json")):
    text = path.read_text("utf-8")
    # 大小寫都要抓：商城道具的名稱寫成大寫「LIBI 100% (4H)」
    new, n = re.subn(r"([\d.,]+)?\s*\bLibi\b", fix, text)
    new, n2 = re.subn(r"\bLIBI\b", "利比", new)
    n += n2
    if n:
        path.write_text(new, "utf-8")
        total += n
        print(f"  {path.name}: {n} 處")

# icon 路徑裡也有 LIBI（商城道具的圖），磁碟檔名要一起改，否則圖會斷。
# 站上的慣例就是「檔名等於品項名」，所以跟著改名而不是把路徑排除在外。
IMG = pathlib.Path(__file__).resolve().parent.parent / "docs/img"
renamed = 0
for sub in IMG.iterdir():
    if not sub.is_dir():
        continue
    for f in sub.iterdir():
        if "LIBI" in f.name:
            f.rename(f.with_name(f.name.replace("LIBI", "利比")))
            renamed += 1
if renamed:
    print(f"圖檔一併改名 {renamed} 個")
print(f"合計 {total} 處")
