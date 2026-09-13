# Pokédex of Packs

**Live at https://acherchu.github.io/pokedex-of-packs/** — GitHub Pages off `main` in
[Acherchu/pokedex-of-packs](https://github.com/Acherchu/pokedex-of-packs). Pushing to `main`
redeploys it; a build takes about a minute.

A single-file website listing **every Pokémon TCG set ever printed** (174 and counting), newest
to oldest, each showing **what a sealed booster pack of it costs**. Click a set to see every card
in it; click a card for the full card detail and market prices.

Sections, switched from the header:

- **Packs** — the set grid, and one set's cards.
- **Energy** — every Energy card (~394), filtered by energy type, Basic / Special, name or set,
  and sorted by price — for finding what an Energy card is worth or adding it to the collection.
- **Card search** — search every card ever printed by name and/or **Pokémon type**. Each *printing*
  comes back as its own result (set, number, rarity, price), and the card sheet has a printing
  picker so you can pin down the exact copy you own.
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

- `GET /sets?pageSize=250` — all sets in one call.
- `GET /cards?q=set.id:<id>&pageSize=250&page=N` — one set's cards, paginated. Full card objects
  come back, so the detail modal needs no second request.

### Saved copies (cache) — show instantly, check every time

The user asked for a cache that still "checks every time to see if there's been an update".
`cachedFetch(key, fetcher, onUpdate)` does stale-while-revalidate for the sets list (`sets`), each
set's cards (`set:<id>`) and every search page (`search:<type>|<term>|<page>`):

- A saved copy (memory for this visit, else IndexedDB `pokedex-cache`) is returned immediately.
- Every use also asks the API in the background; if the JSON differs, the saved copy is replaced
  and `onUpdate` redraws in place — `refreshSetBody` keeps the set's filter values and scroll (and
  leaves a booster-pack pull alone), search swaps just that page into `searchHits`, the set list
  re-renders keeping scroll. No saved copy → it waits for the API as before.
- Failed background checks retry at 4s / 15s / 45s (`CACHE_RETRY`) — the free API fails outright
  often enough that without this a stale copy just stays (seen in testing).
- The same key isn't re-checked within 60s in one visit (`CACHE_RECHECK_MS`), for the ~1000/day limit.
- **IndexedDB, never localStorage** — set data is hundreds of KB and localStorage holds the accounts.
  The old `pkSets` localStorage copy is moved into IndexedDB once and deleted. LRU cap 250 entries.
  If IndexedDB is unavailable, everything simply loads from the network.

Measured: set list ~8s → instant (2ms read), 151 set 7.3s → 13ms, a Pikachu search 10.9s → 4ms.
A planted wrong price ($1.23) corrected itself on screen to $368.78 once the check came back, with the
filter and scroll kept.

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
| `binderBlock` / `editSlot` / `saveSlot` / `clearSlot` / `slotNumber` | Binder slot (one number, set with a + button) in the card sheet, for cards in the collection |
| `snapOf` / `snapToCard` | The card snapshots that let the collection render without re-fetching |
| `ripPack` | Booster-pack simulator — 5 commons, 3 uncommons, 1 rare with an 18% chase pull |

Sorts: newest, oldest, priciest pack, A–Z, most cards. The list is deliberately **flat** (no
series headings) so the chronological order is never broken up.

Escape closes the card sheet, then backs out to the set list.

### Card search

`GET /cards?q=name:"*term*" types:<Type>&orderBy=-set.releaseDate,number&pageSize=60&page=N`. The
quoted wildcard is what makes partial words and names with punctuation (`Mr. Mime`) both work.
Typing is debounced 350ms and every search carries a `searchSeq` so a slow response from an
abandoned query can't overwrite a newer one.

**Search narrows by energy type, not by set** (the user asked for this; there used to be an "All
sets" dropdown over the loaded results — don't bring it back). `energyBar()` draws All types +
the 11 energy types (`ENERGY`, coloured from `TYPE_COLORS`) above every search state, including
the empty hint, "no results" and the API-error screen, so the type can always be changed.
`pickEnergy(t)` toggles `searchType` (tap the chosen type again for All types) and re-runs the
search. The type goes into the **API query** (`types:Fire`), so `totalCount` and Load more stay
correct — a name, a type, or both is a valid search (`searchReady`); a type alone browses every card
of that type, newest first. Trainers and Energy cards have no `types`, so they drop out once a type
is chosen.

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

### Pop-up sheets

All modals are centred with `.modal > .sheet{margin:auto}` rather than `align-items:center`, which
clipped the top of any sheet taller than the screen (like the card sheet) where it couldn't be
scrolled back to.

### Energy tab

The user asked for "a tab for specifically finding energies" where you pick the energy type to
narrow it down. `showEnergy()` (header tab `tab-energy`, `VIEW = "energy"`) loads **all** Energy
cards once — `supertype:Energy`, 2 pages of 250 — through `cachedFetch("energy:all")`, then every
filter is local and instant (`energyMatches` / `drawEnergy`):

- type buttons with live counts (`ENERGY_TYPES`); a type with 0 matches is dimmed but clickable;
- All energy / Basic / Special (`subtypes`);
- the header search box filters by card name or set name;
- sort: newest, price high→low, low→high (unpriced last).

**Basic Energy cards have no `types` in the API** (237 of 394 have none), so `energyIsType` also
matches the type word in the name — "Fire Energy", "Basic Fire Energy", "Unit Energy
GrassFireWater", "Blend Energy GrassFirePsychicDarkness". Rainbow / Prism Energy name no type, so
they only appear under All types. Tiles are the shared `findTile`, so Add to collection and the
card sheet work the same as in Card search. Card search's own type buttons are *Pokémon* types
(Energy cards have no types, so they drop out there once a type is picked).

### No camera

There was a camera card scanner (Tesseract.js text reading, picture matching, auto-snap); the user
had it **removed entirely**. Don't add camera, photo-scanning or OCR features back unasked.

### Accounts

**Making a collection requires signing in** — the user asked for that explicitly, and for the site
to say why: "you have to sign in so we can save your stuff". Browsing sets, prices and card search
never needs signing in.

Signing in is **a name and a password** — no Google, no outside service. This replaced a
Firebase (Google sign-in + Firestore) version on purpose: setting up Firebase needs an adult's
Google account, which the owner doesn't have. Don't reintroduce Firebase or any login provider
unless the user asks for it again. All of it is localStorage on one device:

- `pkProfiles` = `{<lowercased name>: {name, owned: {cardId: snapshot incl. slot number}, pw: {salt, hash, it}}}`
  (older profiles may also carry `binder: 4|9|12` and `{p, s}` slots — converted on read, see Binder slots)
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

**Binder slots.** A card in the collection can be given a place in the owner's real binder as **one
number**: `OWNED[id].slot = 12`. The user asked for it to be simple — "press a + and put in a
number" — replacing an earlier page/pocket grid picker; don't bring the grid back unasked. The card
sheet's "Binder slot" block (`binderBlock`, `#binderpane`, collected cards only) is: a round **+**
when empty → a number box with Save / Cancel (Enter saves, Escape closes just the box) → **#12**
with Change / Remove. Whole numbers ≥ 1 only. **One card per number**: a taken number shows "Slot 12
already has Charizard ex (151)" and doesn't save — never silently overwrite. Collection tiles show
"Binder slot 12"; the "Binder order" sort goes by the number, unslotted last. Removing a card from
the collection drops its slot with it.

Old saves have `slot: {p, s}` plus a profile-level `binder` (4/9/12 pockets a page). `slotNumber()`
converts those to `(p−1)·perPage + s` when a profile is read (`useProfile`) and when a pre-sign-in
collection is merged — the position is kept, never dropped. The old `binder` field is left in
stored profiles untouched (harmless; `saveCollection` merges with `Object.assign`). Tested: page 2
pocket 3 on 12-pocket pages → slot 15, and slot 1 stayed 1, after reload.

**How many (quantity).** The user asked to "select if you have multiple of a Pokémon". The card
sheet's **"How many do you have?"** block (`qtyBlock`, `#qtypane`, above Your copy) is − / number /
+ ; `setQty` stores `OWNED[id].qty` (clamped 1–999, whole numbers; **missing = 1**, so every older
save is one copy, and qty is deleted at 1). − stops at 1 — removing the card stays the "In your
collection" button, so a slip can't delete it. All copies share the card's picked printing. Worth =
`v × qty` in the collection total, the tile's "3 copies · $1.05" line, and "n × $0.35 = $1.05" in
the sheet. **The price sorts use one card's price, not × qty** — the user asked that having multiples
doesn't move a card's place when sorting high→low or low→high. The stats add "Copies, counting doubles" when any card has more
than one. The green owned badge on every tile (`ownMark`) shows "×3" instead of ✓. Tested with real
clicks and typing, invalid values (0, 5000, 3.6), and a reload.

**Your copy (which printing).** The user asked to "select in the collection if your card is a holo
or not so it's more accurate". A collected card's value starts as its **cheapest** printing
(`cardPrice`). The card sheet's **"Your copy — which one do you have?"** block (`copyBlock`,
`#copypane`, above the binder slot) lists the card's printings in `PRINT_ORDER` (normal → holofoil →
reverse → 1st edition…) with their prices; tapping one sets `OWNED[id].pr` and `v = vs[pr]`
(`applyCopy`), tapping it again un-picks back to the cheapest (`clearCopy`). One printing only →
it just says so. Tiles show the picked printing ("Reverse holofoil"), or "Printing not picked
yet" when there's a choice; collection search matches the printing name too. If you pick a printing
in the price list first and then tap "I have this card", that printing is saved (`modalPicked`,
set only by a real `selectVar` click — adding from a tile never guesses). For owned cards the price
list's heading becomes "Prices by printing" so there aren't two "which do you have" questions.

`snapOf` now also stores `vs` — every printing's price (`printPrices`: market, else mid, else low).
**Old saved cards have no `vs`**: `renderOwned` fills it from full card data already loaded, and a
sheet opened from a bare snapshot (after a reload) fetches the card (`upgradeCard`,
`cachedFetch("card:<id>")`), fills `vs`, and redraws the sheet with real prices. `pr` and `vs` are
additive fields on the snapshot — nothing old is renamed. Tested: an old-style Nidoking with no `vs`
got its printings after reload; picking Reverse holofoil took it $0.27 → $1.76 and the total $0.54 →
$2.03; un-picking went back to $0.27.

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

**Missing holofoil.** Commons, uncommons and plain rares are only printed normal and reverse holo
in their own set, so TCGplayer has no `holofoil` price for them (all 128 Common/Uncommon cards in
151, for example). The user saw only "Normal" and "Reverse holofoil" and reported holo as missing.
`lacksHolo(kinds)` detects that case (has normal or reverseHolofoil, no other *holofoil key) and
the picker adds a dashed **Holofoil — "not in this set"** choice (`HOLO_MISSING`), ordered Normal →
Holofoil → Reverse. Choosing it explains why and `loadHoloAlts` lists the holo printings of the
**exact same name** from anywhere (`name:"<name>"` via `cachedFetch("holo:<name>")`, filtered to
`name ===` and a holofoil price, cheapest first, up to 12) — for 151 Bulbasaur: Detective Pikachu
$1.16, SV promo $2.29, McDonald's 2021 $8.04 … Stellar Crown IR $99.37. Those tiles show the
**holofoil** price (`tileHolo` flag in `findTile`), not the card's general price, and tapping one
opens that printing. If none exist it says so and mentions blister "cosmos holo" cards, which this
price data doesn't cover.

## Conventions

This one is **public** — it is a real site people have the link to. Don't push a broken `main`;
check it in a browser first, because there's no staging step between a push and the live URL.

**Theme is Pokémon blue and yellow** — navy/blue panels (`--bg`, `--panel`, `--panel2`, `--line`),
`--gold` #ffcb05 for accents and the active tab, a blue header with a yellow bottom edge.
Prices stay green (`#7ee38a`) and estimates stay gold; those colours carry meaning.

Same as the browser games: **keep it one self-contained HTML file.** No bundler, no
package.json, no npm dependency. All card art and set logos are hotlinked from
`images.pokemontcg.io`.
