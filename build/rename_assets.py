#!/usr/bin/env python3
"""把雜湊檔名的圖檔改成可辨識的中文名稱，並同步更新所有 JSON 連結。

  guide-assets/monsters/J0001.3ebde599.png  ->  img/monsters/娃娃草.png
  guide-assets/icons/F0302.1649c88c.png     ->  img/items/娃娃草的樹葉.png
  guide-assets/minimaps/M0001.d24b0169.png  ->  img/maps/戰士之路.png
  guide-assets/npcs/N0001.xxxxxxxx.png      ->  img/npcs/露西.png
"""
import json, os, re, shutil, collections, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'docs', 'data')
OLD  = os.path.join(ROOT, 'docs', 'assets')
NEW  = os.path.join(ROOT, 'docs', 'img')
FOLDER = {'monsters': 'monsters', 'icons': 'items', 'minimaps': 'maps', 'npcs': 'npcs'}
# 除了檔案系統禁用字元，% 和 # 在網址裡有特殊意義，一併換成全形避免連結解析錯誤
ILLEGAL = str.maketrans({'/': '／', '\\': '＼', ':': '：', '*': '＊',
                         '?': '？', '"': '＂', '<': '＜', '>': '＞', '|': '｜',
                         '%': '％', '#': '＃'})

def collect(obj, out):
    if isinstance(obj, dict):
        for v in obj.values():
            if isinstance(v, str) and v.startswith('guide-assets/'):
                out[v][(obj.get('id'), obj.get('name'))] += 1
            else:
                collect(v, out)
    elif isinstance(obj, list):
        for v in obj:
            collect(v, out)

def canonical_names():
    refs = collections.defaultdict(collections.Counter)
    for f in sorted(os.listdir(DATA)):
        if f.endswith('.json'):
            collect(json.load(open(os.path.join(DATA, f), encoding='utf-8')), refs)
    names = {}
    for path, ctr in refs.items():
        base = os.path.basename(path).split('.')[0]
        exact = [n for (i, n) in ctr if i == base and n]          # 檔名 ID 與資料 ID 相符者最準
        if exact:
            names[path] = exact[0]
        else:                                                      # 退而求其次：最常被引用的名稱
            tally = collections.Counter()
            for (i, n), k in ctr.items():
                if n:
                    tally[n] += k
            names[path] = tally.most_common(1)[0][0]
    return names

def build_map(names):
    groups = collections.defaultdict(list)
    for path, name in names.items():
        groups[(path.split('/')[1], name)].append(path)
    mapping = {}
    for (folder, name), paths in groups.items():
        safe = name.translate(ILLEGAL).strip().rstrip('.') or 'unnamed'
        ext = os.path.splitext(paths[0])[1]
        for n, path in enumerate(sorted(paths), 1):                # 同名不同圖 -> 名稱-2、名稱-3
            suffix = '' if n == 1 else f'-{n}'
            mapping[path] = f'img/{FOLDER[folder]}/{safe}{suffix}{ext}'
    return mapping

def rewrite(obj, mapping):
    if isinstance(obj, dict):
        return {k: (mapping.get(v, v) if isinstance(v, str) else rewrite(v, mapping))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [rewrite(v, mapping) for v in obj]
    return obj

def main():
    names = canonical_names()
    mapping = build_map(names)
    assert len(set(mapping.values())) == len(mapping), '目標檔名仍有衝突'

    for old, new in mapping.items():
        dst = os.path.join(ROOT, 'docs', new)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(OLD, old), dst)

    for f in sorted(os.listdir(DATA)):
        if not f.endswith('.json'):
            continue
        p = os.path.join(DATA, f)
        data = rewrite(json.load(open(p, encoding='utf-8')), mapping)
        json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

    with open(os.path.join(ROOT, 'private', 'asset-map.json'), 'w', encoding='utf-8') as fh:
        json.dump(mapping, fh, ensure_ascii=False, indent=1)      # 只留本機，不進 repo

    shutil.rmtree(OLD)
    print(f'renamed {len(mapping)} files')

if __name__ == '__main__':
    main()
