# -*- coding: utf-8 -*-
"""共用的 wikitext 清理工具。

重點：wiki 大量用「圖片連結」來代表物品/怪物/技能名稱，例如
    [[File:Lv.46_Pirate_Octopus.gif|Pirate Octopus|link=Pirate Octopus]]
    [[File:Knight_Skill1.png|link=Defensive Stance]]
    [[File:Life_Grass.png]] x1
名稱藏在 link= 參數、caption、或檔名裡。舊版把整個 [[File:...]] 刪掉，
導致核心、技能書、製作材料、狀態異常等表格出現整欄空白。
"""
import re

# 檔名 -> 可讀名稱：去掉 Lv.N_ 前綴、_DropN / _Icon / _I 等尾綴、底線換空白
_LVPFX = re.compile(r'^Lv\.?\s*\d+[_\s]+', re.I)
_SFX   = re.compile(r'[_\s]*(Drop\d*|Icon|Logo|Dot|Sprite\w*|\(\w\)|\d)$', re.I)

def name_from_filename(fn: str) -> str:
    n = re.sub(r'\.(png|gif|jpe?g|svg|ogg)$', '', fn.strip(), flags=re.I)
    n = _LVPFX.sub('', n)
    n = n.replace('_', ' ').strip()
    n = _SFX.sub('', n).strip()
    return n

def _file_label(inner: str) -> str:
    """從 [[File:...]] 的內容取出最合適的顯示名稱。"""
    parts = [p.strip() for p in inner.split('|')]
    fname = parts[0]
    opts  = parts[1:]
    # 1) link= 目標最準
    for o in opts:
        if o.lower().startswith('link='):
            tgt = o[5:].strip()
            if tgt: return tgt
    # 2) caption（排除排版關鍵字與尺寸）
    SKIP = {'thumb','thumbnail','right','left','center','none','frame',
            'frameless','border','baseline','middle','sub','super','top','bottom'}
    for o in opts:
        lo = o.lower()
        if lo in SKIP or re.fullmatch(r'\d+\s*px', lo) or '=' in o:
            continue
        if o: return o
    # 3) 退回檔名
    return name_from_filename(fname)

def clean(s, keep_file_names=True):
    if s is None: return ''
    s = str(s)
    if keep_file_names:
        s = re.sub(r'\[\[File:([^\]]*)\]\]', lambda m: _file_label(m.group(1)), s)
    else:
        s = re.sub(r'\[\[File:[^\]]*\]\]', '', s)
    s = re.sub(r'\[\[([^\|\]]*)\|([^\]]*)\]\]', r'\2', s)
    s = re.sub(r'\[\[([^\]]*)\]\]', r'\1', s)
    s = re.sub(r"'''?", '', s)
    s = re.sub(r'<br\s*/?>', ' / ', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'\{\{[^}]*\}\}', '', s)
    s = s.replace('\xa0', ' ')
    s = re.sub(r'\s{2,}', ' ', s)
    return s.strip(' ,/')
