/* 巴哈精華區匯出 —— 貼進瀏覽器主控台執行
 *
 * 用你自己的瀏覽器分頁跑，所以 Cloudflare 那關本來就過了，不需要繞任何驗證。
 * 每次請求之間會停 1.2 秒，速度跟人工點閱差不多，不會給對方的站造成負擔。
 * 跑完會自動下載一個 JSON 檔。
 *
 * 用法：
 *   1. 開 https://forum.gamer.com.tw/G1.php?bsn=11434
 *   2. F12 → Console → 貼上整段 → Enter
 *   3. 等它跑完，瀏覽器會自動下載 baha-digest-11434.json
 *   4. 把那個檔案丟給我
 */
(async () => {
  const BSN = 11434;
  const DELAY = 1200;               // 每次請求間隔（毫秒）
  const MAX_ARTICLES = 0;           // 0 = 不限；想先小規模試跑就改成例如 5

  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const parse = html => new DOMParser().parseFromString(html, 'text/html');

  async function get(url) {
    await sleep(DELAY);
    const res = await fetch(url, { credentials: 'include' });
    if (!res.ok) throw new Error(res.status + ' ' + url);
    return { html: await res.text(), finalUrl: res.url };
  }

  /* 子資料夾只會出現在它自己的父頁裡，首頁看不到
     （例如「職業心得」底下的 ●戰士系列／●聖職者系列，再底下還有 聖職者Q&A）。
     所以分類要用廣度優先一路挖到底，不能只讀首頁那一層。 */
  function foldersIn(doc) {
    return [...doc.querySelectorAll('a[href*="G1.php"][href*="parent="]')]
      .map(a => {
        const m = a.getAttribute('href').match(/parent=(\d+)/);
        const name = a.textContent.trim();
        return m && name ? { id: m[1], name } : null;
      })
      .filter(Boolean);
  }

  /* 文章列的欄位順序：序號 / 標題連結 / 作者帳號 / 作者暱稱 / 日期 */
  function rowsOf(doc) {
    return [...doc.querySelectorAll('tr')].map(tr => {
      const a = tr.querySelector('a[href*="G2.php"]');
      if (!a) return null;
      const td = [...tr.querySelectorAll('td')].map(x => x.textContent.trim());
      return {
        title: a.textContent.trim(),
        url: new URL(a.getAttribute('href'), location.href).href,
        authorId: td[2] || '',
        author: td[3] || '',
        date: td[4] || '',
      };
    }).filter(Boolean);
  }

  /* 文章內文的容器在不同版型下 class 不同，依序試，最後退回頁面裡最長的那塊文字 */
  const BODY_SEL = ['.c-article__content', '.MSG-CONTENT', '.forum-content',
                    '#BH-master .c-article', 'article'];
  function bodyOf(doc) {
    for (const sel of BODY_SEL) {
      const n = doc.querySelector(sel);
      if (n && n.innerText && n.innerText.trim().length > 40) return n.innerText.trim();
    }
    const blocks = [...doc.querySelectorAll('div,section,td')]
      .map(n => n.innerText || '').filter(t => t.length > 100);
    return blocks.sort((a, b) => b.length - a.length)[0]?.trim() || '';
  }

  const out = { bsn: BSN, exportedAt: new Date().toISOString(), categories: [], failed: [] };
  let done = 0;

  const seen = new Set();
  const queue = [{ id: '0', name: '根目錄' }];

  while (queue.length) {
    const c = queue.shift();
    if (seen.has(c.id)) continue;
    seen.add(c.id);

    let doc, list = [];
    try {
      const page = await get(`https://forum.gamer.com.tw/G1.php?bsn=${BSN}&parent=${c.id}`);
      doc = parse(page.html);
      list = rowsOf(doc);

      // 這一頁裡新出現的資料夾排進佇列，繼續往下挖
      for (const f of foldersIn(doc)) {
        if (!seen.has(f.id) && !queue.some(q => q.id === f.id)) queue.push(f);
      }

      // 文章多的分類會分頁，把後續頁的文章一併收進來
      const pages = [...new Set([...doc.querySelectorAll('a[href*="G1.php"][href*="page="]')]
        .map(a => a.getAttribute('href')))];
      for (const href of pages) {
        try {
          const more = await get(new URL(href, location.href).href);
          list = list.concat(rowsOf(parse(more.html)));
        } catch (e) {
          out.failed.push({ url: href, reason: String(e.message) });
        }
      }
      // 同一篇可能在分頁之間重複出現，用網址去重
      list = [...new Map(list.map(a => [a.url, a])).values()];
    } catch (e) {
      out.failed.push({ url: `parent=${c.id}`, reason: String(e.message) });
      console.warn('分類讀取失敗', c.name, e.message);
      continue;
    }
    console.log(`【${c.name}】${list.length} 篇　（待掃分類還剩 ${queue.length}）`);

    const articles = [];
    for (const a of list) {
      if (MAX_ARTICLES && done >= MAX_ARTICLES) break;
      try {
        const art = await get(a.url);
        const doc = parse(art.html);
        articles.push(Object.assign({}, a, {
          finalUrl: art.finalUrl,
          text: bodyOf(doc),
          images: [...doc.querySelectorAll('img')]
            .map(i => i.src).filter(s => s && !/spacer|icon|emotion/i.test(s)),
        }));
        done++;
        if (done % 10 === 0) console.log(`  ⋯已抓 ${done} 篇`);
      } catch (e) {
        out.failed.push({ url: a.url, reason: String(e.message) });
      }
    }
    out.categories.push({ id: c.id, name: c.name, articles });
  }

  const empty = out.categories.flatMap(c => c.articles).filter(a => !a.text).length;
  console.log(`完成：${out.categories.length} 分類（含子資料夾）/ ${done} 篇 / 失敗 ${out.failed.length} / 空內文 ${empty}`);

  const blob = new Blob([JSON.stringify(out, null, 1)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `baha-digest-${BSN}.json`;
  link.click();
  URL.revokeObjectURL(url);
  console.log('已觸發下載 baha-digest-' + BSN + '.json');
})();
