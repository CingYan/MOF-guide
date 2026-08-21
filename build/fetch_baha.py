#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
從 Wayback Machine 撈「天空之城 Online (MOF)」巴哈姆特看板精華區（bsn=11434）內容，
整理成 private/baha/digest.json。

背景與踩過的坑（為什麼程式長這樣）：

1. 巴哈本站有 Cloudflare，直連一定 403，所以一律走
   http://web.archive.org/web/<snapshot>/<原始網址> 這種 Wayback 代理網址。

2. 精華區分類頁 G1.php?bsn=11434&parent=N 這種帶查詢字串的頁面，Wayback 幾乎沒有
   成功爬到過。實測結果：整個 bsn=11434 的 G1.php 系列，全站歷史上只有
   parent=0 / parent=2 / parent=3 / parent=8（加上不帶 parent 的首頁）這幾個
   曾經被 200 存檔，其餘全部只有 2007~2008 年的 302（重導到登入頁之類的殘骸，
   直接用 curl -L 跟過去會落到完全無關的頁面）。所以「先查 CDX 找最接近目標時間
   且 statuscode=200 的快照，找不到就承認抓不到」是唯一可靠的作法，不能只是
   把網址接上 Wayback 前綴後盲目請求、依賴 Wayback 自動轉址到最近快照——
   那個「最近」不保證是 200，會給出垃圾內容。

3. 文章清單頁裡的文章連結是 G2.php?bsn=11434&parent=N&sn=M&lorder=K&ptitle=...，
   這是一支「轉址腳本」，本身永遠回 302，不是文章內容。命中 CDX 之後才發現，
   即使是三個能抓到的分類頁（parent=2/3/8），裡面連到的每一篇文章 G2.php
   連結，在 Wayback 歷史上一次都沒被存過（CDX 查全部是空陣列）。也就是說
   2020 年當下的文章「清單」（標題／作者／日期）可以從分類頁的表格列直接讀到，
   但點進去的實際內文，Wayback 上沒有東西可還原——這是巴哈精華區這個轉址式
   設計 + Wayback 涵蓋率不足共同造成的真實侷限，不是程式沒抓對。

4. 曾經嘗試「反正 C.php / Co.php 也是這個 bsn 底下的頁面，乾脆整批撈」，
   但實測發現 bsn=11434 是整個一般討論板的板號，不是精華區專用，隨便挑一篇
   C.php 存檔開出來是「情人節告白活動」這種完全跟遊戲攻略無關的一般文章。
   在沒有精華區索引頁可以核對「這篇是不是精華」的情況下，整批撈 C.php 只會
   混入大量雜訊，所以本程式只收錄「確實出現在某個精華分類頁清單裡」的文章，
   寧可 text 是空的，也不要收錄不相關內容。

5. Wayback 本身這段時間也常常自己回 503（Temporarily Offline）或 429，
   跟我們送出的請求頻率無關，所以重試要對這兩種都重試。

可重跑：raw/ 底下已經快取的頁面（含 CDX 查詢結果）直接讀檔，不重新連網路。
"""

import os
import re
import sys
import json
import time
import html
import hashlib
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# 常數：抓取禮節相關全部集中在這裡，方便之後調整
# ---------------------------------------------------------------------------

TARGET_SNAPSHOT = "20201204212321"           # 使用者指定的起點存檔時間
BSN = "11434"                                 # 看板代號
ORIGIN = "https://forum.gamer.com.tw"
WAYBACK_WEB = "http://web.archive.org/web"
CDX_API = "http://web.archive.org/cdx/search/cdx"

REQUEST_SLEEP_SECONDS = 2.5                   # 每次「真正打網路」之間至少睡這麼久
MAX_RETRIES = 3                               # 429 / 5xx 的重試上限
RETRY_BACKOFF_BASE_SECONDS = 6                # 指數退避基準：6, 12, 24 秒（加一點隨機抖動）
MAX_TOTAL_REQUESTS = 400                      # 總請求數上限（CDX 查詢 + 內容頁都算）

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "private", "baha", "raw")
OUTPUT_PATH = os.path.join(ROOT, "private", "baha", "digest.json")

# 使用者指定優先抓取的分類（用「名稱包含」比對，不用猜 id）
PRIORITY_NAMES = ["寵物精靈", "職業心得", "武防及合成", "新手專區", "任務錦囊", "專攻技術", "學年資料"]

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(os.path.join(RAW_DIR, "cdx"), exist_ok=True)
os.makedirs(os.path.join(RAW_DIR, "pages"), exist_ok=True)

request_count = 0
failed = []


def _key(url):
    """把任意網址轉成安全的檔名（原始網址常有中文/特殊字元，不能直接當檔名）。"""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def _sleep_and_count():
    global request_count
    request_count += 1
    if request_count > MAX_TOTAL_REQUESTS:
        raise RuntimeError(f"已達請求數上限 {MAX_TOTAL_REQUESTS}，停止繼續抓取")
    time.sleep(REQUEST_SLEEP_SECONDS)


def _http_get(url):
    """單次 HTTP GET，回傳 (bytes, final_url)。呼叫端負責重試。"""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read(), resp.geturl()


def _get_with_retry(url):
    """帶指數退避重試的 GET。429 / 5xx 才重試，其他錯誤直接放棄。"""
    last_err = None
    for attempt in range(MAX_RETRIES):
        _sleep_and_count()
        try:
            data, final_url = _http_get(url)
            return data, final_url
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            if e.code == 429 or 500 <= e.code < 600:
                wait = RETRY_BACKOFF_BASE_SECONDS * (2 ** attempt)
                time.sleep(wait)
                continue
            else:
                break
        except Exception as e:  # noqa: BLE001 - 網路層各種例外都當失敗處理
            last_err = str(e)
            wait = RETRY_BACKOFF_BASE_SECONDS * (2 ** attempt)
            time.sleep(wait)
            continue
    return None, last_err


# ---------------------------------------------------------------------------
# CDX：查某個原始網址在 Wayback 上有哪些快照，藉此挑「最接近目標時間、且
# statuscode=200」的那一筆，而不是相信 Wayback 的自動最近轉址（見檔頭說明 2）。
# ---------------------------------------------------------------------------

def cdx_lookup(original_url):
    """查 CDX，回傳 200 狀態碼的快照清單 [(timestamp, status), ...]（可能是空的）。"""
    cache_path = os.path.join(RAW_DIR, "cdx", _key(original_url) + ".json")
    if os.path.exists(cache_path):
        return json.load(open(cache_path, encoding="utf-8"))

    q = (f"{CDX_API}?url={urllib.request.quote(original_url, safe='')}"
         f"&matchType=exact&output=json&filter=statuscode:200&limit=200"
         f"&fl=timestamp,statuscode")
    data, err = _get_with_retry(q)
    if data is None:
        failed.append({"url": original_url, "reason": f"CDX 查詢失敗：{err}"})
        result = []
    else:
        try:
            rows = json.loads(data.decode("utf-8"))
            result = [r[0] for r in rows[1:]] if len(rows) > 1 else []
        except Exception as e:  # noqa: BLE001
            failed.append({"url": original_url, "reason": f"CDX 回應解析失敗：{e}"})
            result = []

    json.dump(result, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
    return result


def best_snapshot(original_url):
    """從 CDX 結果裡挑離 TARGET_SNAPSHOT 最近的一筆（早於或晚於都接受）。"""
    snaps = cdx_lookup(original_url)
    if not snaps:
        return None
    return min(snaps, key=lambda ts: abs(int(ts) - int(TARGET_SNAPSHOT)))


# ---------------------------------------------------------------------------
# 抓頁面（含快取）
# ---------------------------------------------------------------------------

def fetch_page(original_url):
    """
    抓取某個原始網址在 Wayback 上「離目標時間最近的 200 快照」。
    回傳 dict{html, snapshot, final_url} 或 None（找不到可用快照 / 抓取失敗）。
    已快取的頁面直接讀檔，不重新連網路。
    """
    meta_path = os.path.join(RAW_DIR, "pages", _key(original_url) + ".meta.json")
    html_path = os.path.join(RAW_DIR, "pages", _key(original_url) + ".html")
    if os.path.exists(meta_path) and os.path.exists(html_path):
        meta = json.load(open(meta_path, encoding="utf-8"))
        raw = open(html_path, "rb").read()
        return {"html": _decode(raw), "snapshot": meta["snapshot"],
                "final_url": meta["final_url"], "original_url": original_url}

    snap = best_snapshot(original_url)
    if snap is None:
        failed.append({"url": original_url, "reason": "Wayback 全歷史上沒有這個網址的 200 快照"})
        # 仍然寫一個空 meta，避免重跑時對同一個死網址重複查 CDX
        json.dump({"snapshot": None, "final_url": None},
                   open(meta_path, "w", encoding="utf-8"), ensure_ascii=False)
        return None

    wb_url = f"{WAYBACK_WEB}/{snap}/{original_url}"
    data, final_url = _get_with_retry(wb_url)
    if data is None:
        failed.append({"url": original_url, "reason": f"下載失敗：{final_url}"})
        return None

    open(html_path, "wb").write(data)
    json.dump({"snapshot": snap, "final_url": final_url},
               open(meta_path, "w", encoding="utf-8"), ensure_ascii=False)
    return {"html": _decode(data), "snapshot": snap, "final_url": final_url,
            "original_url": original_url}


def _decode(raw_bytes):
    """巴哈老頁面（2007~2009 左右）是 cp950，新頁面是 utf-8，兩種都試。"""
    for enc in ("utf-8", "cp950"):
        try:
            return raw_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# HTML 處理小工具
# ---------------------------------------------------------------------------

TAG_TREE_CHARS = "┌├└─ 　\xa0"


def clean_category_name(raw_name):
    return raw_name.strip(TAG_TREE_CHARS).strip()


def strip_html(fragment):
    """去標籤、還原實體、保留段落換行（不是完美的 HTML 解析，但夠用且穩定）。"""
    if not fragment:
        return ""
    frag = re.sub(r"(?is)<(script|style).*?</\1>", "", fragment)
    # 區塊級標籤轉成換行，避免整段黏在一起
    frag = re.sub(r"(?i)<(br|p|div|tr|li|/p|/div|/tr|/li)\s*/?>", "\n", frag)
    frag = re.sub(r"(?s)<[^>]+>", "", frag)
    text = html.unescape(frag)
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def extract_title_from_html(page_html):
    m = re.search(r"(?is)<title>(.*?)</title>", page_html)
    if not m:
        return ""
    t = html.unescape(m.group(1)).strip()
    # 標題格式常見是「名稱 @天空之城 Online(MOF) 精華區 - 巴哈姆特」
    t = re.split(r"\s*@天空之城|\s*-\s*巴哈姆特", t)[0].strip()
    return clean_category_name(t)


IMG_SKIP_HINTS = ("spacer.gif", "icon", "avatar", "gamercard", "IMG-E", "button")


def extract_images(fragment):
    urls = re.findall(r'(?i)<img[^>]+src="([^"]+)"', fragment)
    out = []
    for u in urls:
        if any(h in u for h in IMG_SKIP_HINTS):
            continue
        # 去掉 Wayback 的 /web/<ts>im_/ 前綴，只留原始圖片網址
        u2 = re.sub(r"https?://web\.archive\.org/web/\d+(?:im_)?/", "", u)
        if u2 not in out:
            out.append(u2)
    return out


# ---------------------------------------------------------------------------
# 分類樹解析
# ---------------------------------------------------------------------------

CATEGORY_LINK_RE = re.compile(
    r'<a href="G1\.php\?bsn=11434&amp;parent=(\d+)">([^<]*)</a>'
)

ARTICLE_ROW_RE = re.compile(
    r'<a href="G2\.php\?bsn=11434&amp;parent=(?P<parent>\d+)&amp;sn=(?P<sn>\d+)'
    r'&amp;lorder=(?P<lorder>\d+)&amp;ptitle=(?P<ptitle>[^"]*)">(?P<title>[^<]*)</a>'
    r'[^<]*</td>\s*<td>(?P<author>[^<]*)</td>\s*<td>(?P<editor>[^<]*)</td>\s*'
    r'<td>(?P<date>[0-9-]*)</td>'
)


def parse_category_links(page_html):
    """解析頁面裡的 G1.php?parent=N 子分類連結，回傳 [(id, name), ...]，去重。"""
    seen = {}
    for cid, name in CATEGORY_LINK_RE.findall(page_html):
        name = clean_category_name(html.unescape(name))
        if name and cid not in seen:
            seen[cid] = name
    return seen


def parse_article_stubs(page_html):
    """解析分類頁裡的文章列表（標題／作者／日期），文章本身連結是轉址用的 G2.php。"""
    stubs = []
    for m in ARTICLE_ROW_RE.finditer(page_html):
        d = m.groupdict()
        stubs.append({
            "parent": d["parent"],
            "sn": d["sn"],
            "lorder": d["lorder"],
            "title": html.unescape(d["title"]).strip(),
            "author": html.unescape(d["author"]).strip(),
            "editor": html.unescape(d["editor"]).strip(),
            "date": d["date"].strip(),
            "g2_url": (f"{ORIGIN}/G2.php?bsn={BSN}&parent={d['parent']}&sn={d['sn']}"
                       f"&lorder={d['lorder']}&ptitle={d['ptitle']}"),
        })
    return stubs


def try_resolve_article(stub):
    """
    嘗試把 G2.php 轉址連結還原成真正的文章內容。
    現實中（見檔頭說明 3）這幾乎必然失敗，因為 Wayback 沒存過這些轉址請求；
    仍然嘗試是因為之後如果 Wayback 補了新快照，程式不用改就能撿到。
    回傳 dict{url, text, images} 或 None。
    """
    page = fetch_page(stub["g2_url"])
    if page is None:
        return None
    # 如果拿到的頁面其實還是「找標題／找作者」那種搜尋介面或分類頁，
    # 代表轉址沒有指到真正文章，視為解析失敗，不要硬湊內容。
    if "找標題" in page["html"] and "找作者" in page["html"]:
        return None
    body_text = strip_html(page["html"])
    if len(body_text) < 20:
        return None
    final_original = re.sub(r"^https?://web\.archive\.org/web/\d+(?:im_|cs_|js_)?/", "",
                             page["final_url"])
    return {
        "url": final_original,
        "text": body_text,
        "images": extract_images(page["html"]),
        "snapshot": page["snapshot"],
    }


def _strip_bracket_prefix(title):
    """去掉常見的『【心得】【攻略】【情報】』這類前綴，方便比對標題核心字串。"""
    return re.sub(r"^【[^】]*】", "", title).strip()


def cdx_collapsed_prefix(prefix_url, cache_name):
    """
    查某個網址前綴在全站歷史上有哪些 200 快照（不限特定 sn），並依 urlkey 去重。
    用在「精華分類頁本身沒被存過，但文章的實際內容頁可能剛好被獨立存過」這種
    補救性搜尋（見檔頭說明 4）。
    """
    cache_path = os.path.join(RAW_DIR, "cdx", cache_name + ".json")
    if os.path.exists(cache_path):
        return json.load(open(cache_path, encoding="utf-8"))
    q = (f"{CDX_API}?url={urllib.request.quote(prefix_url, safe='')}&matchType=prefix"
         f"&filter=statuscode:200&output=json&limit=2000&collapse=urlkey"
         f"&fl=timestamp,original")
    data, err = _get_with_retry(q)
    rows = []
    if data is None:
        failed.append({"url": prefix_url, "reason": f"CDX 前綴查詢失敗：{err}"})
    else:
        try:
            parsed = json.loads(data.decode("utf-8"))
            rows = [{"timestamp": r[0], "url": r[1]} for r in parsed[1:]]
        except Exception as e:  # noqa: BLE001
            failed.append({"url": prefix_url, "reason": f"CDX 前綴查詢解析失敗：{e}"})
    json.dump(rows, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
    return rows


def supplement_unresolved_articles(categories):
    """
    最後一道補救：G2.php 轉址在 Wayback 上幾乎必死（見檔頭說明 3），但整個看板
    （bsn=11434）底下用 C.php / Co.php 這種舊式網址直接開的頁面，偶爾有獨立被存到。
    這些頁面涵蓋整個討論板（不只精華區），所以不能整批收錄——只有在頁面內文裡
    同時比對到某篇「已知精華文章」的作者帳號與標題主要字串時，才視為同一篇，
    把還原出來的全文接回去；比對不到的，維持原樣（text 留空，不亂猜）。
    """
    unresolved = []
    for cat in categories.values():
        for art in cat["articles"]:
            if not art["text"]:
                unresolved.append(art)
    if not unresolved:
        return

    candidates = (cdx_collapsed_prefix(f"{ORIGIN}/C.php?bsn={BSN}", "sweep_Cphp")
                  + cdx_collapsed_prefix(f"{ORIGIN}/Co.php?bsn={BSN}", "sweep_Cophp"))

    for cand in candidates:
        if not unresolved:
            break
        try:
            page = fetch_page(cand["url"])
        except RuntimeError as e:
            failed.append({"url": cand["url"], "reason": str(e)})
            break
        if page is None:
            continue
        body_text = strip_html(page["html"])
        if len(body_text) < 20:
            continue
        for art in list(unresolved):
            core_title = _strip_bracket_prefix(art["title"])
            if len(core_title) < 4:
                continue
            if core_title in body_text and art["author"] and art["author"] in body_text:
                final_original = re.sub(
                    r"^https?://web\.archive\.org/web/\d+(?:im_|cs_|js_)?/", "",
                    page["final_url"])
                art["url"] = final_original
                art["snapshot"] = page["snapshot"]
                art["text"] = body_text
                art["images"] = extract_images(page["html"])
                unresolved.remove(art)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    categories = {}   # id -> {"id","name","parentId","articles":[...]}
    visited_category_ids = set()

    def ensure_category(cid, name, parent_id):
        if cid not in categories:
            categories[cid] = {"id": cid, "name": name, "parentId": parent_id, "articles": []}
        elif name and not categories[cid]["name"]:
            categories[cid]["name"] = name
        if parent_id and not categories[cid].get("parentId"):
            categories[cid]["parentId"] = parent_id

    # 1) 抓精華區首頁，取得頂層分類樹
    root_url = f"{ORIGIN}/G1.php?bsn={BSN}"
    root_page = fetch_page(root_url)
    top_level = {}
    if root_page:
        top_level = parse_category_links(root_page["html"])
        for cid, name in top_level.items():
            ensure_category(cid, name, "0")
    else:
        failed.append({"url": root_url, "reason": "首頁抓取失敗，無法取得分類樹"})

    # 2) 額外用 CDX 掃描全站歷史上「曾經有 200 快照」的 G1.php?parent=N 頁面，
    #    這樣即使某分類不是從已知父頁連過去發現的（例如巢狀子分類），
    #    只要 Wayback 真的存過，也不會漏掉（見檔頭說明 2 的 parent=8 案例）。
    extra_q = (f"{CDX_API}?url=forum.gamer.com.tw/G1.php%3Fbsn%3D{BSN}&matchType=prefix"
               f"&filter=statuscode:200&output=json&limit=2000&fl=original,statuscode")
    extra_cache = os.path.join(RAW_DIR, "cdx", "all_parent_pages.json")
    if os.path.exists(extra_cache):
        extra_rows = json.load(open(extra_cache, encoding="utf-8"))
    else:
        data, err = _get_with_retry(extra_q)
        extra_rows = []
        if data is not None:
            try:
                rows = json.loads(data.decode("utf-8"))
                extra_rows = [r[0] for r in rows[1:]]
            except Exception as e:  # noqa: BLE001
                failed.append({"url": extra_q, "reason": f"CDX 掃描解析失敗：{e}"})
        json.dump(extra_rows, open(extra_cache, "w", encoding="utf-8"), ensure_ascii=False)

    discovered_ids = set(top_level.keys())
    for orig in extra_rows:
        m = re.search(r"parent=(\d+)", orig)
        if m:
            discovered_ids.add(m.group(1))
    discovered_ids.discard("0")  # parent=0 就是首頁本身，不是獨立分類

    # 排序：優先處理使用者指定的重點分類（含它們目前已知的名稱比對）
    def sort_key(cid):
        name = categories.get(cid, {}).get("name", "")
        is_priority = any(p in name for p in PRIORITY_NAMES)
        return (0 if is_priority else 1, cid)

    ordered_ids = sorted(discovered_ids, key=sort_key)

    # 3) 逐一處理每個分類頁：抓內容、解析子分類、解析文章清單、嘗試還原文章內文
    to_process = list(ordered_ids)
    processed = set()
    while to_process:
        cid = to_process.pop(0)
        if cid in processed:
            continue
        processed.add(cid)
        visited_category_ids.add(cid)

        cat_url = f"{ORIGIN}/G1.php?bsn={BSN}&parent={cid}"
        try:
            page = fetch_page(cat_url)
        except RuntimeError as e:
            # 達到請求數上限，剩下的分類原樣保留（articles 為空），並記錄原因
            failed.append({"url": cat_url, "reason": str(e)})
            ensure_category(cid, categories.get(cid, {}).get("name", ""), "")
            break

        if page is None:
            ensure_category(cid, categories.get(cid, {}).get("name", ""), "")
            continue

        page_name = extract_title_from_html(page["html"])
        ensure_category(cid, categories.get(cid, {}).get("name") or page_name, "")

        # 子分類（用來補上 parentId，也讓還沒發現的子分類排進佇列）
        for sub_id, sub_name in parse_category_links(page["html"]).items():
            ensure_category(sub_id, sub_name, cid)
            if sub_id not in processed and sub_id not in to_process:
                to_process.append(sub_id)

        # 文章清單
        stubs = parse_article_stubs(page["html"])
        for stub in stubs:
            resolved = None
            try:
                resolved = try_resolve_article(stub)
            except RuntimeError as e:
                failed.append({"url": stub["g2_url"], "reason": str(e)})

            article = {
                "title": stub["title"],
                "author": stub["author"],
                "date": stub["date"],
                "url": resolved["url"] if resolved else "",
                "snapshot": resolved["snapshot"] if resolved else "",
                "text": resolved["text"] if resolved else "",
                "images": resolved["images"] if resolved else [],
            }
            if resolved is None:
                failed.append({
                    "url": stub["g2_url"],
                    "reason": "文章轉址頁（G2.php）在 Wayback 上沒有任何存檔，"
                              "無法還原成實際內文；標題／作者／日期取自分類頁列表。",
                })
            categories[cid]["articles"].append(article)

    # 3.5) 對還沒有內文的文章，最後試著用作者＋標題比對舊式 C.php／Co.php 頁面
    try:
        supplement_unresolved_articles(categories)
    except RuntimeError as e:
        failed.append({"url": "(supplement pass)", "reason": str(e)})

    # 4) 輸出
    fetched_pages = len([f for f in os.listdir(os.path.join(RAW_DIR, "pages"))
                          if f.endswith(".html")])
    out = {
        "source": "wayback",
        "snapshot": TARGET_SNAPSHOT,
        "fetchedPages": fetched_pages,
        "failed": failed,
        "categories": list(categories.values()),
    }
    json.dump(out, open(OUTPUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    total_articles = sum(len(c["articles"]) for c in categories.values())
    print(f"完成。分類數：{len(categories)}，文章數：{total_articles}，"
          f"失敗筆數：{len(failed)}，總請求數：{request_count}")
    print(f"輸出：{OUTPUT_PATH}")


if __name__ == "__main__":
    main()
