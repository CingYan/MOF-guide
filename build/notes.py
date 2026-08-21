#!/usr/bin/env python3
"""把玩家筆記裡「機制類、不隨版本變」的那批抽出來給網站用。

分類結果來自 private/baha/triage.json（不進 repo）。
只取 class == "keep" —— 那些講的是遊戲怎麼運作，資料表本身表達不了；
class == "verify" 的 294 篇含具體數值，要逐筆跟現行資料對照過才敢放，先不收。
"""
import json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'private', 'baha', 'triage.json')
OUT = os.path.join(ROOT, 'docs', 'data', 'notes.json')

# 依主題分組，比照原本的分類但併成讀者看得懂的幾大類
GROUP = [
    ('組隊與練功效率', ['組隊', '經驗', '越級', '增啪', '練功', '托怪', '打怪']),
    ('職業與配點',     ['配點', '職業', '技能', '爆擊', '命中', '屬性加成', '狙擊', '遊俠', '聖徒', '聖職', '主教']),
    ('強化與裝備',     ['強化', '特武', '武器']),
    ('副本與徽章',     ['副本', '徽章', '稱號', '海賊王']),
    ('其他機制',       []),
]

def group_of(a):
    hay = a['title'] + ' ' + a['category'] + ' ' + ' '.join(a.get('topics') or [])
    for name, kws in GROUP:
        if kws and any(k in hay for k in kws):
            return name
    return '其他機制'

src = json.load(open(SRC, encoding='utf-8'))
keeps = [a for a in src['articles'] if a['class'] == 'keep']

by = collections.OrderedDict((g, []) for g, _ in GROUP)
for a in keeps:
    by[group_of(a)].append({
        'title': a['title'],
        'author': a.get('author') or '',
        'date': a.get('date') or '',
        'topics': a.get('topics') or [],
        'text': a['extract'],
        'note': a.get('conflicts') or '',
    })

out = {
    'groups': [{'name': g, 'notes': v} for g, v in by.items() if v],
    'kept': len(keeps),
    'held': src['counts']['verify'],   # 待查證、暫不收錄的數量
}
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(f"收錄 {len(keeps)} 篇，分成 {len(out['groups'])} 組；"
      f"另有 {out['held']} 篇待查證未收錄。輸出 {os.path.getsize(OUT)//1024} KB")
