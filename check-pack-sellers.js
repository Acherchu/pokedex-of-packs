/*
  check-pack-sellers.js — refreshes PACK_PICKS in index.html: the cheapest single booster pack per set
  from a TCGplayer seller whose reviews hold up. Not part of the site; run it by hand.

  TCGplayer's listing data has no public feed (its listing API refuses scripts), so this reads the
  product pages the way a person would, politely (one page at a time, 1.5s apart):

  1. Open https://www.tcgplayer.com/product/565604 in a normal browser tab and let it load.
  2. In that tab's developer console, set the packs to check — [setId, TCGplayer productId, usual price]
     for every set with a pack — which you can print from the site's own console with:
        copy(JSON.stringify(Object.entries(PACK_PRICES.s).filter(([k,v]) => v.lu).map(([k,v]) => [k, v.lu, v.p])))
     then paste:  window.PACKS_TO_CHECK = <pasted>;
  3. Paste this whole file. Progress: window.__packRun. Results survive a reload (sessionStorage).
  4. When it finishes it logs the new PACK_PICKS object — replace the one in index.html with it.

  A listing passes when it's the plain catalog pack marked Unopened (no custom photo listing, no seller
  name hinting at foreign / weighed / resealed packs), the seller has 99%+ feedback from 500+ sales, and
  price + shipping is at least half the usual price. The first passing listing, cheapest first, wins.
*/

(async () => {
  const items = window.PACKS_TO_CHECK;
  const sl = ms => new Promise(r => setTimeout(r, ms));
  const results = JSON.parse(sessionStorage.packPicks || "{}");
  window.__packRun = {done: Object.keys(results).length, total: items.length, current: "", finished: false};
  const num = t => { const m = String(t || "").replace(/,/g, "").match(/\d+(\.\d+)?/); return m ? parseFloat(m[0]) : null; };
  const F = /korean|japanese|chinese|thai|indonesian|german|french|spanish|italian|portuguese|\b(jp|jpn|kr|cn|chn|ger)\b|asia|simplified|traditional/i;
  const B = /weigh|opened|resealed|empty|light|heavy|mystery|repack|damaged|no code|read desc/i;
  for(const [sid, pid, avg] of items){
    if(results[sid]) continue;
    window.__packRun.current = sid;
    const fr = document.createElement("iframe");
    fr.style.cssText = "position:fixed;left:0;top:0;width:1200px;height:900px;opacity:0.01;pointer-events:none;z-index:-1";
    fr.src = "/product/" + pid + "?Language=English";
    document.body.appendChild(fr);
    let doc = null;
    for(let i = 0; i < 75; i++){
      await sl(400);
      try{ doc = fr.contentDocument; }catch(e){ doc = null; }
      if(doc && (doc.querySelector("section.listing-item") || /\b0 Listings\b|No listings/i.test(doc.body ? doc.body.innerText : ""))) break;
    }
    const sk = {foreignOrCustom: 0, sellerReviews: 0, tooCheap: 0, notSealed: 0};
    let n = 0, pick = null;
    if(doc && doc.querySelector("section.listing-item")){
      const rd = () => [...doc.querySelectorAll("section.listing-item")].map(el => {
        const st = el.querySelector(".listing-item__listing-data__info__shipping-message")?.textContent || "";
        const sp = [...el.querySelectorAll(".seller-info__rating span")].map(s => s.textContent.trim());
        return {price: num(el.querySelector(".listing-item__listing-data__info__price")?.textContent),
          ship: /\+\s*\$/.test(st) ? num(st.split("Shipping")[0]) : 0,
          cond: (el.querySelector(".listing-item__condition")?.textContent || "").trim(),
          custom: el.querySelector(".listing-item__listing-data__listo__title")?.textContent.trim() || "",
          seller: el.querySelector(".seller-info__name")?.textContent.trim() || "",
          url: el.querySelector(".seller-info__name")?.getAttribute("href") || "",
          rating: num(sp.find(t => /%/.test(t))), sales: num(sp.find(t => /Sales/i.test(t))),
          gold: !!el.querySelector(".seller-info__gold-star")};
      });
      outer: for(let pg = 1; pg <= 12; pg++){
        for(const l of rd()){
          n++;
          if(l.price == null) continue;
          if(!/unopened|sealed/i.test(l.cond)){ sk.notSealed++; continue; }
          if(l.custom || F.test(l.seller) || B.test(l.seller)){ sk.foreignOrCustom++; continue; }
          if(!(l.rating >= 99) || !(l.sales >= 500)){ sk.sellerReviews++; continue; }
          if(avg && l.price + l.ship < avg * 0.5){ sk.tooCheap++; continue; }
          pick = l; break outer;
        }
        const nx = [...doc.querySelectorAll('[class*="pagination"] a, [class*="pagination"] button')].find(a => a.textContent.trim() === String(pg + 1));
        if(!nx) break;
        const fb = doc.querySelector("section.listing-item")?.textContent;
        nx.click();
        for(let i = 0; i < 30 && doc.querySelector("section.listing-item")?.textContent === fb; i++) await sl(300);
        await sl(600);
      }
    }
    const listings = doc ? num((doc.body.innerText.match(/(\d[\d,]*) Listings/) || [])[1]) : null;
    results[sid] = pick
      ? {pid, pr: pick.price, sh: pick.ship, se: pick.seller, su: pick.url, ra: pick.rating, sa: pick.sales, g: pick.gold, sk, n, listings}
      : {pid, none: 1, sk, n, listings, loaded: !!doc};
    sessionStorage.packPicks = JSON.stringify(results);
    window.__packRun.done = Object.keys(results).length;
    fr.remove();
    await sl(1500);                      // be polite to TCGplayer
  }
  window.__packRun.finished = true;
  const rows = {};
  for(const [k, v] of Object.entries(results)) rows[k] = v.none ? [0, v.sk.foreignOrCustom, v.sk.sellerReviews, v.sk.tooCheap]
    : [v.pr, v.sh, v.se, v.su.replace(/^\/sellers\//, ""), v.ra, v.sa, v.sk.foreignOrCustom, v.sk.sellerReviews, v.sk.tooCheap];
  console.log("PACK_PICKS for index.html:\n" + JSON.stringify({d: new Date().toISOString().slice(0, 10), s: rows}));
})();
"started"
