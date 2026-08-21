#!/usr/bin/env python3
"""把資料裡的「字面跳脫序列」還原成真正的字元。

原始資料的敘述欄位存的是兩個字元的反斜線加 n，不是換行，
所以 NPC 介紹、怪物介紹會在畫面上直接印出 \n。
CSS 那邊 .desc 已經是 white-space: pre-wrap，換成真的換行就會正確斷行。

可重複執行：已經是真換行的字串不含反斜線，不會被二次處理。
"""
import json, os, re

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'data')

# 只還原確定安全的幾個；未知的跳脫序列原樣保留，寧可留著也不要猜錯
ESCAPES = [
    (re.compile(r'\\n'), '\n'),
    (re.compile(r'\\r'), ''),
    (re.compile(r'\\t'), '  '),
    (re.compile(r'\\\.'), '.'),     # 資料裡有 \. 這種被多跳脫一層的句點
]

count = 0

def fix(s):
    global count
    for pat, rep in ESCAPES:
        s, n = pat.subn(rep, s)
        count += n
    # 還原後可能留下行尾空白與超過兩行的空白段落
    s = '\n'.join(line.rstrip() for line in s.split('\n'))
    return re.sub(r'\n{3,}', '\n\n', s).strip()

def walk(o):
    if isinstance(o, dict):
        return {k: (fix(v) if isinstance(v, str) else walk(v)) for k, v in o.items()}
    if isinstance(o, list):
        return [walk(v) for v in o]
    return o

changed = []
for f in sorted(os.listdir(DATA)):
    if not f.endswith('.json'):
        continue
    p = os.path.join(DATA, f)
    src = json.load(open(p, encoding='utf-8'))
    out = walk(src)
    if out != src:
        changed.append(f)
    json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

print(f'還原 {count} 處跳脫序列，異動檔案：{", ".join(changed) or "無"}')
