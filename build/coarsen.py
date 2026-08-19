#!/usr/bin/env python3
"""把過度精確的數值粗略化，並把資料版本改成一般化的標示。

掉落率原本是 0.472421 這種直接從資料表倒出來的精度，實際使用只需要
「約 47%」。統一取 2 位有效數字，稀有掉落仍保得住 0.083% 這種量級。
"""
import json, os

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'data')
RATE_KEYS = {'rate', 'successRate'}

def sig2(x):
    if not isinstance(x, float) or x <= 0:
        return x
    import math
    digits = -int(math.floor(math.log10(abs(x)))) + 1
    return round(x, max(digits, 2))

def walk(o):
    if isinstance(o, dict):
        return {k: (sig2(v) if k in RATE_KEYS and isinstance(v, float) else walk(v))
                for k, v in o.items()}
    if isinstance(o, list):
        return [walk(v) for v in o]
    return o

changed = 0
for f in sorted(os.listdir(DATA)):
    if not f.endswith('.json') or f == 'meta.json':
        continue
    p = os.path.join(DATA, f)
    src = json.load(open(p, encoding='utf-8'))
    out = walk(src)
    if out != src:
        changed += 1
    json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

meta = json.load(open(os.path.join(DATA, 'meta.json'), encoding='utf-8'))
meta.pop('dataVersion', None)          # 建置雜湊，對讀者沒意義
meta['updated'] = meta.pop('generatedAt', '')[:7]
json.dump(meta, open(os.path.join(DATA, 'meta.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'coarsened {changed} files')
