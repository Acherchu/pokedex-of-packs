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
  - **My collection** — every card you've ticked off, and what it's worth.

## Files

- `index.html` — the entire site. No build step, no dependencies. Double-click it and it runs.
- `update-pack-prices.py` — dev tool. Refreshes the pack prices baked into `index.html`.
  Not needed to run the site.

## Run it

Open `C:\Users\arche\pokemon-packs\index.html` in any browser. That's it — `file://` works
because the API sends `Access-Control-Allow-Origin: *`. (Note `file://` and `localhost` have
separate localStorage, so signed-in names and collections don't carry between them.)

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
| `evoOrder` / `species` | Set card grid order: number order, but each evolution line pulled together at its first card |
| `showSearch` / `runSearch` / `renderSearch` / `findTile` | Card search: query, paging, result grid |
| `openCard` / `priceBlock` / `selectVar` | Card sheet: identification block, printing picker, prices |
| `toggleOwn` / `ownBtn` / `showOwned` / `renderOwned` / `drawOwned` / `sortOwned` / `ownedTile` | Ticking off cards (from the card sheet), and the collection view |
| `binderBlock` / `setSlot` / `clearSlot` / `binderTo` / `setBinderSize` / `slotLabel` | Binder slot picker in the card sheet, for cards in the collection |
| `snapOf` / `snapToCard` | The card snapshots that let the collection render without re-fetching |
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

### Accounts

**Making a collection requires signing in** — the user asked for that explicitly, and for the site
to say why: "you have to sign in so we can save your stuff". Browsing sets, prices and card search
never needs signing in.

Signing in is **a name and a password** — no Google, no outside service. This replaced a
Firebase (Google sign-in + Firestore) version on purpose: setting up Firebase needs an adult's
Google account, which the owner doesn't have. Don't reintroduce Firebase or any login provider
unless the user asks for it again. All of it is localStorage on one device:

- `pkProfiles` = `{<lowercased name>: {name, owned: {cardId: snapshot}, binder: 4|9|12, pw: {salt, hash, it}}}`
- `pkUser` = the lowercased name currently signed in (so a reload keeps you signed in)

Names are matched case-insensitively and trimmed ("  aSH " signs in as Ash), max 24 characters.

**Passwords** (the user asked for "a protective password thing"): the password is never stored.
`pw` is PBKDF2-SHA256, 150,000 iterations, 16-byte random salt, via `crypto.subtle` (`hashPw`), and
`it` is stored so the count can be raised later without breaking old names. Minimum 4 characters.
The box adapts as you type a name (`signMode`): an existing name just asks for its password; a new
name — or one made in the few minutes the site was live without passwords — must pick one and type
it twice. `saveCollection` merges into the profile with `Object.assign` so it never drops `pw`.
Be honest about what this is: it keeps other people using the same device out of a collection
**through the site**. It is not encryption — the collection is plain JSON in localStorage that dev
tools can read — and there's **no password reset** (no server), which the box says. Don't add a
"forgot password" that bypasses it. Names used on this device are listed as buttons ("Signed in
here before?"); tapping one fills the name and focuses the password box. The sign-in box and
the signed-out collection page both say the collection saves on this device; keep that honest —
never claim it syncs or follows you to other devices.

**Never lose an account in an update.** The user explicitly asked for this. A deploy only replaces
`index.html`; localStorage survives it — so the danger is only ever *code* that mishandles the data.
Rules for any change:

- Keep the keys `pkProfiles` and `pkUser` and the profile shape. If the shape must change, convert
  old profiles when they're **read**; never rename, clear or rewrite them in place.
- All reads go through `readProfiles()` and all writes through `writeProfiles()`. Don't touch
  `localStorage` for accounts anywhere else.
- `writeProfiles` copies the current value to `pkProfilesBackup` before every save.
  `readProfiles` restores from that backup if `pkProfiles` is missing or unreadable, and stashes an
  unreadable value in `pkProfilesRescue` first. With no usable backup it returns `ok:false`, and
  `writeProfiles` then refuses to save rather than overwrite what's there.
- `writeProfiles` refuses any save that leaves out a name already stored (there's no delete-a-name
  feature, so that can only be a bug). If you ever add one, change this deliberately.
- `keepStorage()` calls `navigator.storage.persist()` so the browser doesn't evict the data when
  space runs low.
- What code can't protect against, and the user was told: clearing browser/site data, another
  browser or device, private/incognito windows.

Tested: a name made on the previous live version still signed in and kept its cards and binder
slot after the update deployed; missing, damaged and no-backup cases; a save dropping a name.

The same origin (`acherchu.github.io`) would also host FOREST RUN if its Pages were enabled; it only
uses `fr_*` keys and never calls `localStorage.clear()`, so it can't touch these. Keep it that way.

How it hangs together (`initAccounts`, run after `loadSets`):

- `needSignIn(id)` is the gate every change calls first (`toggleOwn`, `setSlot`, `clearSlot`,
  `setBinderSize`). Signed out, it opens the sign-in box (`showSignIn`) and remembers the card in
  `pendingOwn`, which is added straight after signing in. Closing the box without signing in clears it.
- `signIn()` (async — hashing) reads `#signname`, `#signpw`, `#signpw2`; errors show inline in
  `#signerr`. Each input has its own Enter handler (with `preventDefault`) as well as the form's
  `onsubmit` — in testing, Enter didn't submit the form on its own.
- `saveCollection()` writes the signed-in profile back to `pkProfiles` immediately; `writeProfiles`
  toasts if storage is full or blocked.
- **Migration:** a pre-sign-in `pkOwned` / `pkBinder` is merged into the first name signed in on
  that browser (profile entries win; a clashing binder pocket drops the incoming card's slot), then
  the old keys are deleted — only after the write succeeds.
- `signOut()` clears `pkUser` and empties `OWNED`; the profile itself stays.

### The collection

Saved under the signed-in name (above). There used to be a deck builder and saved decks; they were
removed on purpose, so don't bring them back unasked. Old `pkDecks` / `pkDraft` keys may still sit
in visitors' browsers — nothing reads them.

Cards go in from a **card search result** (`+ Add to collection` on each `findTile`) or the
**card sheet** (`ownBtn`, beside the "See the whole set" link), and come out from either of those
or a collection tile. **Sorting** (`#osort`, `sortOwned`, remembered in `pkOwnedSort`): Newest added
(default), Price high→low, Price low→high, Name A–Z, Set & card number, Binder order, Oldest added.
"Added" order is `OWNED` key insertion order — card ids aren't integer-like, so object key order holds.
Price sorts use the value saved with the card (`snap.v`) — what it was worth when added, the same
number the tile shows — with unpriced cards last in both directions. The collection page leads with the tagline "An online way to keep track of
your Pokémon" in both its empty and filled states. Its search box (`#oq`, `drawOwned`) filters the
snapshots in `OWNED` locally — name, set or rarity contains the term, or the number matches
exactly (`199` or `#199`) — no API call. `ownedTerm` survives `renderOwned` redraws, so removing a
card mid-search keeps the filter; `showOwned` resets it. `showOwned` closes
the sheet and switches view; `refreshView` calls `renderOwned` instead, so un-ticking from an open
sheet redraws the collection behind it without closing the sheet.

**Binder slots.** A card in the collection can be given a place in the owner's real binder:
`OWNED[id].slot = {p: page, s: pocket}`, pockets counted left to right, top to bottom. The card
sheet shows a "Binder slot" block (`binderBlock`, `#binderpane`) only for collected cards: a
picture of one binder page, page ‹ › and a page-number box, a 4 / 9 / 12-pocket layout select
(saved to the account as `binder`, default 9), and "Remove from slot". Pockets holding another card show
that card and aren't clickable — **one card per pocket**, never silently overwrite. The sheet opens
on the card's own page. Collection tiles show "Binder: Page N · Slot N". Removing a card from the
collection drops its slot with it.

Every stored entry keeps a **snapshot** of the card (`snapOf`): name, set, number, rarity, both
image URLs, and its value at save time. That's the point — the collection renders completely
without re-fetching every card, and still works when the API is down. `snapToCard` turns one back
into enough of a card object for the card sheet to open after a reload, so `CARDS` gets seeded
from snapshots whenever the collection is shown.

Store both image URLs, never derive one from the other: older cards are
`images.pokemontcg.io/<set>/<n>.png` with a `_hires` twin, newer ones are `images.scrydex.com/...`
where no such twin exists.

Tick buttons on search and collection tiles sit on top of a tile that opens the card sheet, so
they take `event` and call `stopPropagation`. `.find` is a flex column with the button bar at
`margin-top:auto`, so buttons line up across a row when a rarity name wraps. `refreshView()` redraws whichever section is open after a
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

**Theme is Pokémon blue and yellow** — navy/blue panels (`--bg`, `--panel`, `--panel2`, `--line`),
`--gold` #ffcb05 for accents and the active tab, a blue header with a yellow bottom edge.
Prices stay green (`#7ee38a`) and estimates stay gold; those colours carry meaning.

Same as the browser games: **keep it one self-contained HTML file.** No bundler, no
package.json, no npm dependency. All card art and set logos are hotlinked from
`images.pokemontcg.io`.
