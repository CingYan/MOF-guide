#!/usr/bin/env python3
"""任務裡的地城名稱是原始韓文，這裡換成與地圖名稱一致的中文。"""
import json, os

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'data')
BASE = {'포세이도스': '波賽多斯', '고스트캐슬': '幽靈城堡', '어둠의 던전': '黑暗地城',
        '어둠의던전': '黑暗地城', '마족의 집결지': '魔族集結地', '화산동굴': '火山洞窟',
        '암흑나무숲': '黑暗樹林', '대나무숲': '竹林', '지식의탑': '知識之塔',
        '지식의 탑': '知識之塔', '지혜의 탑': '智慧之塔', '해적선': '海盜船'}
PREFIX = {'무한': '無限', '다중': '多重', '미궁': '迷宮'}

def zh(name):
    for k, v in PREFIX.items():
        if name.startswith(k + ' '):
            return v + zh(name[len(k) + 1:])
    return BASE.get(name, name)

p = os.path.join(DATA, 'quests.json')
qs = json.load(open(p, encoding='utf-8'))
n = 0
for q in qs:
    for d in q['indun']:
        new = zh(d['dungeon'])
        if new != d['dungeon']:
            d['dungeon'] = new
            n += 1
json.dump(qs, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('translated', n, 'dungeon names')
