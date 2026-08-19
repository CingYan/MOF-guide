# -*- coding: utf-8 -*-
"""從 Master of Fantasy Wiki 重新抓取全部條目 -> data/raw.json"""
import json, subprocess, urllib.parse, os
B = "https://master-of-fantasy.fandom.com/api.php"

def curl(url=None, post=None):
    if post is not None:
        open('/tmp/_mofpost.txt','w').write(post)
        cmd = ["curl","-s","-m","60","-X","POST","--data-binary","@/tmp/_mofpost.txt",
               "-H","Content-Type: application/x-www-form-urlencoded", B]
    else:
        cmd = ["curl","-s","-m","30", url]
    return subprocess.run(cmd, capture_output=True, text=True).stdout

titles, cont = [], None
while True:
    u = f"{B}?action=query&list=allpages&aplimit=500&apnamespace=0&format=json"
    if cont: u += "&apcontinue=" + urllib.parse.quote(cont)
    d = json.loads(curl(url=u))
    titles += [p['title'] for p in d['query']['allpages']]
    if 'continue' in d: cont = d['continue']['apcontinue']
    else: break
print("條目數:", len(titles))

pages = {}
for i in range(0, len(titles), 40):
    batch = titles[i:i+40]
    post = ("action=query&format=json&prop=revisions|categories&rvprop=content"
            "&rvslots=main&cllimit=max&titles=" + "|".join(batch))
    try: d = json.loads(curl(post=post))
    except Exception: print("  批次失敗", i); continue
    for p in d.get('query', {}).get('pages', {}).values():
        if 'revisions' not in p: continue
        pages[p['title']] = {
            'text': p['revisions'][0]['slots']['main']['*'],
            'cats': [c['title'].replace('Category:','') for c in p.get('categories', [])],
        }
    print(f"  {min(i+40,len(titles))}/{len(titles)}")

os.makedirs('data', exist_ok=True)
json.dump(pages, open('data/raw.json','w'), ensure_ascii=False)
print("完成:", len(pages), "頁 ->", "data/raw.json")
