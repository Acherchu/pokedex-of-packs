# Pokédex of Packs

**Live at https://acherchu.github.io/pokedex-of-packs/** — GitHub Pages off `main` in
[Acherchu/pokedex-of-packs](https://github.com/Acherchu/pokedex-of-packs). Pushing to `main`
redeploys it; a build takes about a minute.

A single-file website listing **every Pokémon TCG set ever printed** (174 and counting), newest
to oldest, each showing **what a sealed booster pack of it costs**. Click a set to see every card
in it; click a card for the full card detail and market prices.

Sections, switched from the header:

- **Packs** — the set grid, and one set's cards.
- **Card search** — search every card ever printed by name. Each *printing* comes back as its own
  result (set, number, rarity, price), and the card sheet has a printing picker so you can pin
  down the exact copy you own.
- **View more ›** — not a dropdown. It reveals the remaining tabs *in the same row*, styled
  identically to Packs and Card search, and becomes "Fewer ‹". The row starts collapsed, and
  auto-expands whenever you're in one of the hidden sections so the active tab is never hidden.
  New sections go here — add a button with class `extra` and an entry in `TAB_OF`:
  - **Deck builder** — pick a Pokémon type, add cards to a deck, tick off the ones you own, save it.
  - **My decks** — saved decks, each showing what it's worth and what you still need to find.
  - **My collection** — every card you've ticked off, and what it's worth.

## Files

- `index.html` — the entire site. No build step, no dependencies. Double-click it and it runs.
- `update-pack-prices.py` — dev tool. Refreshes the pack prices baked into `index.html`.
  Not needed to run the site.

## Run it

Open `C:\Users\arche\pokemon-packs\index.html` in any browser. That's it — `file://` works
because the API sends `Access-Control-Allow-Origin: *`.

To serve it over HTTP instead (needed for the Browser pane to render it as a live page rather
than a static snapshot):

```bash
C:\Python314\python.exe -m http.server 8082 --directory C:\Users\arche\pokemon-packs
```

There's a `pokemon-packs` entry in `C:\Users\arche\.claude\launch.json` on port 8082.

## Data source

Live from the free [Pokémon TCG API](https://pokemontcg.io) (`api.pokemontcg.io/v2`), no API key.

- `GET /sets?pageSize=250` — all sets in one call, cached in `localStorage` for 24h (`pkSets`).
- `GET /cards?q=set.id:<id>&pageSize=250&page=N` — one set's cards, paginated, cached in memory
  for the session. Full card objects come back, so the detail modal needs no second request.

## Pack prices

The headline number on each tile is **what one sealed booster pack costs**, not the value of the
cards inside it. pokemontcg.io has no sealed-product data at all, so it comes from
[tcgcsv.com](https://tcgcsv.com) (free TCGplayer market data, no key).

**tcgcsv sends no CORS headers**, so the browser can't fetch it — the prices are baked into
`index.html` as a `PACK_PRICES` blob between `const PACK_PRICES =` and the `// end-pack-prices`
marker. Refresh them with:

```bash
C:\Python314\python.exe C:\Users\arche\pokemon-packs\update-pack-prices.py
```

That script name-matches pokemontcg.io sets to TCGplayer groups (150/174; the rest are promo,
McDonald's and trainer-kit sets that were never sold in packs), then pulls the cheapest
`Booster Pack`, `Booster Box` and `Elite Trainer Box` for each. Gotchas it already handles, so
don't "simplify" them away:

- TCGplayer prefixes group names — `XY - Flashfire`, `SM Base Set`, `SV: Scarlet & Violet 151`.
  `keys()` tries several normalizations; `OVERRIDES` covers the five it can't infer.
- Vintage packs carry an edition qualifier: `Booster Pack [Revised Unlimited Edition]`. The
  trailing bracket is stripped before matching, and the **cheapest** edition wins.
- Sealed vintage often has no `marketPrice`, only `lowPrice` — fall back, or you lose ~8 sets.
- `Art Bundle`, `Blister`, `Sleeved`, `Mini`, `Case` and `Display` products are excluded; they
  aren't the plain pack a person buys.

114 of 174 sets end up with a pack price. The rest show "not sold in packs", which is accurate —
promos, Trainer Galleries, Shiny Vaults and Energies were never sold that way.

Card-level prices (the green chip on each card, and the modal's TCGplayer/Cardmarket blocks) come
free with the card data — no extra requests. There is deliberately **no background price sweep**;
an earlier version summed every card in every set and cost ~460 API calls and 3 minutes per cold
visit.

**The free pokemontcg.io tier throws intermittent 500s** — roughly 1 request in 3 during testing.
`getJSON()` retries 5 times with increasing backoff, and also backs off on 429. Don't remove that;
a bare `fetch` will look broken half the time. Without an API key the limit is 1000 requests/day.

## Layout of index.html

| Section | What it does |
|---|---|
| `loadSets` / `renderSets` / `setTile` | Flat set grid, newest → oldest by default |
| `packPrice` / `priceLabel` / `money` | Sealed pack price for a set, straight from `PACK_PRICES` |
| `cardPrice` / `cardValue` / `warnBox` / `estLegend` | Real price, estimate fallbacks, and the labelling that keeps them apart |
| `priceStats` | Priciest-card stat — real prices only, never estimates |
| `openSet` / `renderSetBody` / `drawCards` | One set: header stats, rarity + type filters, card grid |
| `showSearch` / `runSearch` / `renderSearch` / `findTile` | Card search: query, paging, result grid |
| `openCard` / `priceBlock` / `selectVar` | Card sheet: identification block, printing picker, prices |
| `showBuilder` / `pickType` / `poolTile` / `trayHTML` | Deck builder: type filter, card pool, deck tray |
| `showDecks` / `openDeck` / `saveDeck` / `snapOf` / `snapToCard` | Saved decks and the snapshots that let them stand alone |
| `toggleOwn` / `showOwned` | Ticking off cards you have, and the collection view |
| `ripPack` | Booster-pack simulator — 5 commons, 3 uncommons, 1 rare with an 18% chase pull |

Sorts: newest, oldest, priciest pack, A–Z, most cards. The list is deliberately **flat** (no
series headings) so the chronological order is never broken up.

Escape closes the card sheet, then backs out to the set list.

### Card search

`GET /cards?q=name:"*term*"&orderBy=-set.releaseDate,number&pageSize=60&page=N`. The quoted
wildcard is what makes partial words and names with punctuation (`Mr. Mime`) both work. Typing is
debounced 350ms and every search carries a `searchSeq` so a slow response from an abandoned query
can't overwrite a newer one.

Results are whole card objects, so clicking one needs no second request. Every card seen this
session — from a set or from a search — lands in the `CARDS` map, which is what `openCard` reads.

### Estimated prices

Whole sets ship months before TCGplayer lists anything — the four newest Mega Evolution sets have
661 cards with no price between them. Rather than show a dash, `cardValue()` falls through:

1. **TCGplayer market price** — real, shown plain in green.
2. **Cardmarket (EU) trend price** converted at the baked `PRICE_EST.eur` rate — estimate.
3. **`PRICE_EST.r[rarity]`** — the median price of that rarity across the 15 most recent priced
   sets, baked by `update-pack-prices.py`. Each entry is `[median, sampleSize]`, and a sample
   under 10 sets `weak`, which makes the page hedge harder ("treat it as very rough").
   Mega Hyper Rare is only 2-3 cards per set, hence `MIN_SAMPLE = 2`.
4. `PRICE_EST.any` — the median of everything, when the rarity is unknown.

Estimates are **always** marked: a `~` prefix, gold instead of green, an `EST` tag in search
results, a count in the grid legend, and a yellow box in the card sheet naming the exact basis
("what a typical Double Rare from a recent set sells for, across 199 comparable cards"). The
wording adapts to which fallback was used — don't claim "brand-new sets take a while to sell"
for a 2019 promo priced off Cardmarket. Never show an estimate as if it were a real price.

### Decks and the collection

All of it is `localStorage`, on one browser, no account — `pkOwned` (ticked-off cards),
`pkDecks` (saved decks), `pkDraft` (the deck being built, saved on every change so a reload
doesn't lose work).

Every stored entry keeps a **snapshot** of the card (`snapOf`): name, set, number, rarity, both
image URLs, and its value at save time. That's the point — a saved deck renders completely
without re-fetching 60 cards, and still works when the API is down. `snapToCard` turns one back
into enough of a card object for the card sheet to open after a reload, so `CARDS` gets seeded
from snapshots whenever a deck or the collection is shown.

Store both image URLs, never derive one from the other: older cards are
`images.pokemontcg.io/<set>/<n>.png` with a `_hires` twin, newer ones are `images.scrydex.com/...`
where no such twin exists.

The deck builder filters by **Pokémon type only** — that's deliberate, not an unfinished filter
bar. `q=types:<Type> supertype:Pokémon`, 60 at a time. `loadType` drops a response whose type is
no longer selected, so switching type mid-request can't scramble the grid; that also means
calling it directly with a type that isn't `deckType` silently does nothing — go through
`pickType`.

Add/tick buttons sit on top of a tile that opens the card sheet, so every one of them takes
`event` and calls `stopPropagation`. `refreshView()` redraws whichever section is open after a
change.

### Printing picker

The point of the card sheet is *"is this the card I actually own?"*, so it leads with an
identification block (set symbol + name, number out of the set total, rarity, release date,
illustrator) before any prices.

A card's TCGplayer prices are keyed by printing — `normal`, `reverseHolofoil`,
`1stEditionHolofoil`, `unlimitedHolofoil` and friends — and they differ a lot: Neo Genesis
Ampharos is $91.95 1st edition but $39.28 unlimited. When a card has more than one, the sheet
shows a picker, and `VARIANTS` gives each one a plain-English tell ("shiny everywhere except the
artwork", "1st Edition stamp beside the art") so you can match it against the card in your hand.
Keep those descriptions — they're the difference between a price list and something you can
actually use.

## Conventions

This one is **public** — it is a real site people have the link to. Don't push a broken `main`;
check it in a browser first, because there's no staging step between a push and the live URL.

Same as the browser games: **keep it one self-contained HTML file.** No bundler, no
package.json, no npm dependency. All card art and set logos are hotlinked from
`images.pokemontcg.io`.
