"""
Regenerates the sealed booster-pack prices and the rarity price baselines embedded in index.html.

pokemontcg.io has no sealed-product data and tcgcsv.com sends no CORS headers, so the
browser can't fetch pack prices itself. This script pulls them here and rewrites the
PACK_PRICES block inside index.html, keeping the site a single double-clickable file.

    C:\\Python314\\python.exe update-pack-prices.py

Prices come from TCGplayer market data via tcgcsv.com (free, no key).
"""
import html as htmllib, json, re, statistics, sys, time, unicodedata, urllib.request, difflib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PTCG = "https://api.pokemontcg.io/v2"
TCGCSV = "https://tcgcsv.com/tcgplayer/3"          # category 3 = Pokemon
HERE = Path(__file__).parent

# pokemontcg.io set id -> tcgcsv group name, for the ones name-matching can't get right
OVERRIDES = {
    "base1":  "Base Set",
    "sv3pt5": "SV: Scarlet & Violet 151",   # pokemontcg.io calls it just "151"
    "sm1":    "SM Base Set",                # "Sun & Moon"
    "xy1":    "XY Base Set",
    "bp":     "Best of Promos",             # "Best of Game"
}


def get(url, tries=10):
    # both APIs 403 a bare urllib user-agent
    req = urllib.request.Request(url, headers={"User-Agent": "pokedex-of-packs/1.0"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(0.4 * (i + 1))


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))   # Pok\u00e9mon -> Pokemon
    s = s.lower().replace("&", "and")
    s = re.sub(r"[^a-z0-9 ]", " ", s)                # em dashes, colons, apostrophes -> space
    s = re.sub(r"\bbase set\b", "", s)               # "SWSH: Sword & Shield Base Set" -> "sword and shield"
    return " ".join(s.split())


# series codes that prefix a TCGplayer group name: "XY - Flashfire", "HS\u2014Unleashed", "SV08: ..."
PREFIX = re.compile(r"^(xy|sm|hs|hgss|bw|dp|pl|ex|np|sv|sve|svp|swsh|me)\d*\s+")


def keys(name):
    """Every spelling a set/group might be matched under, most specific first."""
    k, out = norm(name), []
    for v in (k, PREFIX.sub("", k), re.sub(r"^pokemon\s+", "", k)):
        if v and v not in out:
            out.append(v)
    return out


# "Booster Pack Art Bundle [Set of 4]", "3 Pack Blister", "Sleeved Booster Pack" etc. are not
# the plain pack a person would buy, so they never count.
EXCLUDE = ("code card", "art bundle", "blister", "sleeved", "mini", "case", "display",
           "bundle", "pack of", " tin", "collection")
QUALIFIER = re.compile(r"\s*\[[^\]]*\]\s*$")     # "Booster Pack [Unlimited Edition]"


def candidates(products, suffix):
    """Products that are exactly `suffix` (e.g. 'booster pack') — one plain item, not a bundle.

    Vintage packs carry an edition qualifier — Base Set's is "Booster Pack [Revised Unlimited
    Edition]" — so the trailing bracket is stripped before matching.
    """
    out = []
    for p in products:
        n = p["name"].lower()
        if any(x in n for x in EXCLUDE):
            continue
        while QUALIFIER.search(n):
            n = QUALIFIER.sub("", n)
        if n.endswith(suffix):
            out.append(p)
    return out


def pick(products, prices, suffix):
    """Cheapest market price among the matching products; the cheapest edition wins (unlimited
    over 1st edition), matching how card prices are picked."""
    vals = [prices[p["productId"]] for p in candidates(products, suffix) if prices.get(p["productId"])]
    return min(vals) if vals else None


def in_stock(products, rows, suffix):
    """The cheapest single item you can buy right now on TCGplayer.

    lowPrice is the lowest listing currently in stock from any TCGplayer seller (every order is
    covered by TCGplayer's guarantee); directLowPrice is the lowest from TCGplayer Direct sellers,
    which TCGplayer vets and ships itself. Either is None when nothing is listed.
    -> {"l": price, "lu": productId, "d": price, "du": productId} (only the keys that exist)
    """
    out = {}
    for p in candidates(products, suffix):
        for r in rows.get(p["productId"], []):
            for key, field in (("l", "lowPrice"), ("d", "directLowPrice")):
                v = r.get(field)
                if v and v > 0 and (key not in out or v < out[key]):
                    out[key], out[key + "u"] = round(v, 2), p["productId"]
    return out


# Boxes that are just packs (plus extras), for "is a box cheaper per pack than single packs?".
# code, name ending (after dropping [..] and (..) qualifiers), packs when the description doesn't say
BOX_KINDS = (
    ("h", "half booster box", 18),
    ("b", "booster box", 36),
    ("c", "pokemon center elite trainer box", None),
    ("e", "elite trainer box", None),
    ("u", "booster bundle", 6),
)
BOX_SKIP = ("case", "display", "set of", "sleeved", "art bundle", "code card", "bulk")


def box_kind(name):
    n = name.lower()
    if any(x in n for x in BOX_SKIP):
        return None
    n = re.sub(r"\s*[\[(][^\])]*[\])]", "", n).strip()
    for code, suffix, _ in BOX_KINDS:
        if n.endswith(suffix):
            return code
    return None


def packs_in(product):
    """Pack count from TCGplayer's description: "Each ... booster box contains 36 booster packs",
    "• 9 Pokémon TCG: Scarlet & Violet—151 booster packs". None when it doesn't say."""
    text = next((e["value"] for e in product.get("extendedData", []) if e["name"] == "CardText"), "")
    text = htmllib.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    m = re.search(r"\b(\d{1,2})\s+(?:[^\d.;]{0,90}?)\bbooster packs?\b", text, re.I)
    return int(m.group(1)) if m else None


def boxes(products, prices, released):
    """Cheapest-per-pack product of each box kind -> {kind: [price, packs, productId]}.

    When the description has no count, fall back only where the count is certain: booster boxes 36,
    half boxes 18, bundles 6; Elite Trainer Boxes 9 (Pokémon Center 11) from Scarlet & Violet on,
    and 8 before that only for main sets (ones with a booster box) — special-set ETBs vary (10)."""
    new_era = (released or "") >= "2023/03/31"
    main_set = any(box_kind(p["name"]) == "b" for p in products)
    out = {}
    for p in products:
        kind, price = box_kind(p["name"]), prices.get(p["productId"])
        if not kind or not price:
            continue
        n = packs_in(p) or dict((k, d) for k, _, d in BOX_KINDS)[kind]
        if n is None and kind == "e":
            n = 9 if new_era else (8 if main_set else None)
        if n is None and kind == "c" and new_era:
            n = 11
        if not n:
            continue
        if kind not in out or price / n < out[kind][0] / out[kind][1]:
            out[kind] = [round(price, 2), n, p["productId"]]
    return out


SAMPLE_SETS = 15        # how many recent priced sets feed the rarity baselines
MIN_SAMPLE = 2          # a rarity needs this many real prices before it becomes a baseline
                        # (Mega Hyper Rare is genuinely only 2-3 cards per set)


def card_market(c):
    """Cheapest TCGplayer market price across a card's printings."""
    p = (c.get("tcgplayer") or {}).get("prices") or {}
    vals = [v.get("market") for v in p.values() if v and v.get("market")]
    return min(vals) if vals else None


def eur_usd():
    try:
        r = get("https://api.frankfurter.app/latest?from=EUR&to=USD")
        return round(r["rates"]["USD"], 4)
    except Exception:
        print("  ! couldn't fetch EUR/USD, using 1.08")
        return 1.08


def rarity_baselines(sets):
    """Median price per rarity across the most recent sets that actually have prices.

    Whole sets ship before TCGplayer lists anything — the four newest Mega Evolution sets had
    661 cards with no price between them — so an estimate can only come from comparable cards
    in other recent sets.
    """
    recent = sorted(sets, key=lambda s: s.get("releaseDate") or "", reverse=True)
    buckets, used = {}, []
    for s in recent:
        if len(used) >= SAMPLE_SETS:
            break
        try:
            cards = get(f"{PTCG}/cards?q=set.id:{s['id']}&select=id,rarity,tcgplayer&pageSize=250")["data"]
        except Exception:
            continue
        priced = [c for c in cards if card_market(c)]
        if len(priced) < 10:
            continue                      # unpriced or tiny set, skip it
        used.append(s["name"])
        for c in priced:
            r = c.get("rarity")
            if r:
                buckets.setdefault(r, []).append(card_market(c))

    # [median, how many real prices it came from] — the count drives how strongly the page
    # hedges the estimate it shows
    table = {r: [round(statistics.median(v), 2), len(v)]
             for r, v in buckets.items() if len(v) >= MIN_SAMPLE}
    every = [x for v in buckets.values() for x in v]
    fallback = round(statistics.median(every), 2) if every else 0.25
    print(f"  baselines from {len(used)} sets: {', '.join(used[:4])}…")
    print(f"  {len(table)} rarities, fallback {fallback}")
    thin = [r for r, (m, n) in table.items() if n < 10]
    if thin:
        print(f"  thin samples (<10 cards): {', '.join(thin)}")
    return {"r": table, "any": fallback, "sets": len(used)}


def main():
    print("fetching pokemontcg.io sets…")
    sets = get(f"{PTCG}/sets?pageSize=250")["data"]
    print(f"  {len(sets)} sets")

    print("fetching tcgplayer groups…")
    groups = get(f"{TCGCSV}/groups")["results"]
    print(f"  {len(groups)} groups")

    by_norm = {}
    for g in groups:
        for k in keys(g["name"]):
            by_norm.setdefault(k, g)

    matched, unmatched, released = {}, [], {}
    for s in sets:
        g = None
        if s["id"] in OVERRIDES:
            g = next((x for x in groups if x["name"] == OVERRIDES[s["id"]]), None)
        if g is None:
            for k in keys(s["name"]):
                g = by_norm.get(k)
                if g:
                    break
        if g is None:
            near = difflib.get_close_matches(norm(s["name"]), list(by_norm), n=1, cutoff=0.88)
            g = by_norm[near[0]] if near else None
        if g is None:
            unmatched.append(s["name"])
        else:
            matched[s["id"]] = g
            released[s["id"]] = s.get("releaseDate")

    print(f"matched {len(matched)}/{len(sets)}; unmatched: {', '.join(unmatched) or 'none'}")

    def one(item):
        set_id, g = item
        gid = g["groupId"]
        try:
            products = get(f"{TCGCSV}/{gid}/products")["results"]
            raw = get(f"{TCGCSV}/{gid}/prices")["results"]
        except Exception as e:
            print(f"  ! {g['name']}: {e}")
            return set_id, None
        # sealed vintage often has no marketPrice, only a lowPrice from live listings
        prices, rows = {}, {}
        for p in raw:
            rows.setdefault(p["productId"], []).append(p)
            m = p.get("marketPrice") or p.get("lowPrice")
            if m:
                prices[p["productId"]] = min(m, prices.get(p["productId"], m))
        out = {}
        for key, suffix in (("p", "booster pack"), ("b", "booster box"), ("e", "elite trainer box")):
            v = pick(products, prices, suffix)
            if v:
                out[key] = round(v, 2)
        # one single pack, in stock right now: l/lu = cheapest listing, d/du = cheapest TCGplayer Direct
        out.update(in_stock(products, rows, "booster pack"))
        # boxes of packs, to show when one works out cheaper per pack
        o = boxes(products, prices, released.get(set_id))
        if o:
            out["o"] = o
        return set_id, (out or None)

    print("fetching sealed prices…")
    result = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for i, (set_id, data) in enumerate(ex.map(one, matched.items()), 1):
            if data:
                result[set_id] = data
            if i % 20 == 0:
                print(f"  {i}/{len(matched)}")

    packs = sum(1 for v in result.values() if "p" in v)
    stocked = sum(1 for v in result.values() if "l" in v)
    direct = sum(1 for v in result.values() if "d" in v)
    boxed = sum(1 for v in result.values() if "o" in v)
    print(f"done: {packs} sets with a booster-pack price, {len(result)} with any sealed price")
    print(f"      {stocked} with a single pack in stock on TCGplayer, {direct} from TCGplayer Direct")
    print(f"      {boxed} with a box of packs (booster box, ETB, bundle) priced")

    print("building rarity baselines for cards with no price…")
    est = rarity_baselines(sets)
    est["eur"] = eur_usd()

    today = time.strftime("%Y-%m-%d")
    html = (HERE / "index.html").read_text(encoding="utf-8")
    blocks = {
        "PACK_PRICES": {"d": today, "s": result},
        "PRICE_EST":   dict(est, d=today),
    }
    for name, data in blocks.items():
        blob = json.dumps(data, separators=(",", ":"))
        marker = "// end-" + name.lower().replace("_", "-")
        html, n = re.subn("const " + name + r" = .*?; " + re.escape(marker),
                          "const " + name + " = " + blob + "; " + marker,
                          html, flags=re.S)
        if not n:
            print(f"!! {name} marker not found in index.html", file=sys.stderr)
            (HERE / (name.lower() + ".json")).write_text(blob, encoding="utf-8")
            sys.exit(1)
    (HERE / "index.html").write_text(html, encoding="utf-8")
    print("index.html updated")


if __name__ == "__main__":
    main()
