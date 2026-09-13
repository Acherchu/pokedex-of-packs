"""
Builds price-history.json: what each card sold for on a handful of past dates, for the
Collecting section's "how prices have changed" graph.

pokemontcg.io only has today's prices, and nothing free has card prices from before 2024. tcgcsv.com
keeps a daily snapshot of all TCGplayer prices back to 2024-02-08 (one .7z per day), so this pulls
one snapshot every six months, keeps category 3 (English Pokémon), and matches every product to its
pokemontcg.io card id the same way update-pack-prices.py matches sets: pokemontcg set -> TCGplayer
group, then the card number printed on the product ("199/165" -> sv3pt5-199).

    C:\\Python314\\python.exe update-price-history.py

Needs py7zr (a dev tool only — the site itself doesn't use it):  python -m pip install --user py7zr
Snapshots are cached in .history-cache/ (git-ignored) so re-runs only fetch new dates.

Output: {"d": [dates], "c": {setId: {number: [cents per date, 0 = no price]}}}
Each card's price is its cheapest printing's market price that day, like everywhere else on the site.
"""
import importlib.util, json, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import py7zr

HERE = Path(__file__).parent
CACHE = HERE / ".history-cache"
FIRST = date(2024, 2, 8)          # the oldest snapshot tcgcsv has

# Sets the pack-price matching skips (promos were never sold in packs) or that TCGplayer splits into
# more than one group. pokemontcg.io set id -> extra TCGplayer group names whose cards belong to it.
EXTRA_GROUPS = {
    "basep": ["WoTC Promo"], "np": ["Nintendo Promos"], "dpp": ["Diamond and Pearl Promos"],
    "hsp": ["HGSS Promos"], "bwp": ["Black and White Promos"], "xyp": ["XY Promos"],
    "smp": ["SM Promos"], "swshp": ["SWSH: Sword & Shield Promo Cards"],
    "svp": ["SV: Scarlet & Violet Promo Cards"],
    "mcd11": ["McDonald's Promos 2011"], "mcd12": ["McDonald's Promos 2012"],
    "mcd14": ["McDonald's Promos 2014"], "mcd15": ["McDonald's Promos 2015"],
    "mcd16": ["McDonald's Promos 2016"], "mcd17": ["McDonald's Promos 2017"],
    "mcd18": ["McDonald's Promos 2018"], "mcd19": ["McDonald's Promos 2019"],
    "mcd21": ["McDonald's 25th Anniversary Promos"], "mcd22": ["McDonald's Promos 2022"],
    "g1": ["Generations: Radiant Collection"], "bw11": ["Legendary Treasures: Radiant Collection"],
}


def load_pack_script():
    spec = importlib.util.spec_from_file_location("packs", HERE / "update-pack-prices.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def snapshot_dates(today):
    """The first snapshot, then the 1st of every February and August since."""
    out = [FIRST]
    y = 2024
    while True:
        for m in (8, 2) if y == 2024 else (2, 8):
            d = date(y, m, 1)
            if d <= FIRST:
                continue
            if d > today:
                return sorted(set(out))
            out.append(d)
        y += 1


def fetch_snapshot(d):
    """category 3's price files for one day -> {productId: cheapest market price}"""
    CACHE.mkdir(exist_ok=True)
    ds = d.isoformat()
    done = CACHE / (ds + ".json")
    if done.exists():
        return {int(k): v for k, v in json.loads(done.read_text()).items()}
    arc = CACHE / (ds + ".7z")
    if not arc.exists():
        url = f"https://tcgcsv.com/archive/tcgplayer/prices-{ds}.ppmd.7z"
        req = urllib.request.Request(url, headers={"User-Agent": "pokedex-of-packs/1.0"})
        for i in range(6):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    arc.write_bytes(r.read())
                break
            except Exception as e:
                if i == 5:
                    raise
                time.sleep(2 * (i + 1))
    out_dir = CACHE / ds
    with py7zr.SevenZipFile(arc) as z:
        targets = [n for n in z.getnames() if n.startswith(ds + "/3/") and n.endswith("/prices")]
    with py7zr.SevenZipFile(arc) as z:
        z.extract(path=out_dir, targets=targets)
    prices = {}
    for f in (out_dir / ds / "3").glob("*/prices"):
        try:
            rows = json.loads(f.read_text(encoding="utf-8")).get("results", [])
        except Exception:
            continue
        for p in rows:
            m = p.get("marketPrice")
            if m and m > 0:
                pid = p["productId"]
                prices[pid] = min(m, prices.get(pid, m))
    done.write_text(json.dumps(prices))
    return prices


def card_number(product):
    for e in product.get("extendedData") or []:
        if e.get("name") == "Number":
            n = str(e.get("value", "")).split("/")[0].strip().replace(" ", "")
            n = re.sub(r"^SVP", "", n, flags=re.I)          # SV promos print "SVP 047"; pokemontcg.io calls it 47
            return str(int(n)) if n.isdigit() else n
    return None


def main():
    packs = load_pack_script()
    today = date.today()
    dates = snapshot_dates(today)
    print("snapshots:", ", ".join(d.isoformat() for d in dates))

    print("fetching pokemontcg.io sets and TCGplayer groups…")
    sets = packs.get(f"{packs.PTCG}/sets?pageSize=250")["data"]
    groups = packs.get(f"{packs.TCGCSV}/groups")["results"]
    by_norm = {}
    for g in groups:
        for k in packs.keys(g["name"]):
            by_norm.setdefault(k, g)
    matched = {}
    for s in sets:
        g = None
        if s["id"] in packs.OVERRIDES:
            g = next((x for x in groups if x["name"] == packs.OVERRIDES[s["id"]]), None)
        if g is None:
            for k in packs.keys(s["name"]):
                g = by_norm.get(k)
                if g:
                    break
        if g is None:
            near = packs.difflib.get_close_matches(packs.norm(s["name"]), list(by_norm), n=1, cutoff=0.88)
            g = by_norm[near[0]] if near else None
        found = [g] if g else []
        for name in EXTRA_GROUPS.get(s["id"], []):
            x = next((x for x in groups if x["name"] == name), None)
            if x and x not in found:
                found.append(x)
            elif not x:
                print(f"  ! no TCGplayer group called {name!r}")
        if found:
            matched[s["id"]] = found
    print(f"  {len(matched)}/{len(sets)} sets matched to TCGplayer groups")

    print("fetching products (card numbers)…")
    def products(item):
        sid, g = item
        try:
            return sid, packs.get(f"{packs.TCGCSV}/{g['groupId']}/products")["results"]
        except Exception as e:
            print(f"  ! {g['name']}: {e}")
            return sid, []
    pairs = [(sid, g) for sid, gs in matched.items() for g in gs]
    pid_to_card = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for sid, prods in ex.map(products, pairs):
            for p in prods:
                num = card_number(p)
                if num:
                    pid_to_card[p["productId"]] = (sid, num)
    print(f"  {len(pid_to_card)} card products")

    snaps = []
    for d in dates:
        print(f"snapshot {d}…", end=" ", flush=True)
        prices = fetch_snapshot(d)
        print(f"{len(prices)} Pokémon prices")
        snaps.append(prices)

    cards = {}
    for pid, (sid, num) in pid_to_card.items():
        row = [round(snap.get(pid, 0) * 100) for snap in snaps]
        if not any(row):
            continue
        cur = cards.setdefault(sid, {}).get(num)
        # one card can be several TCGplayer products (a stamped or special variant): keep the cheapest per date
        if cur:
            row = [min(a, b) if a and b else (a or b) for a, b in zip(cur, row)]
        cards[sid][num] = row

    n = sum(len(v) for v in cards.values())
    out = {"d": [d.isoformat() for d in dates], "made": today.isoformat(), "c": cards}
    blob = json.dumps(out, separators=(",", ":"))
    (HERE / "price-history.json").write_text(blob, encoding="utf-8")
    print(f"price-history.json: {n} cards, {len(blob) // 1024} KB")


if __name__ == "__main__":
    main()
