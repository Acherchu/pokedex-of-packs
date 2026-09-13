# Pokédex of Packs

**Live site → https://acherchu.github.io/pokedex-of-packs/**

Every Pokémon TCG set ever printed — newest to oldest — with what a sealed booster pack of each
one costs. Click a set to see every card in it, or search any card by name to find out what your
copy is worth.

![Every Pokémon set, newest first](https://images.pokemontcg.io/sv8pt5/logo.png)

## What it does

**Packs** — all 174 sets in one chronological grid, each with its logo, release date, card count
and current sealed booster-pack price. Sort by newest, oldest, priciest pack, A–Z or most cards.
Open a set for its full card list with rarity and type filters, and a booster-pack simulator that
deals you a realistic 9-card pull.

**Card search** — search every card ever printed by name. Each *printing* comes back separately
with its set, card number, rarity and price, because the same Charizard exists in dozens of sets
at wildly different values.

**Knowing which card you actually have** — open any card and you get an identification panel
first: set symbol, card number out of the set total, rarity, release date, illustrator. Then a
printing picker, because the printing is what decides the price. Neo Genesis Ampharos is $91.95
as a 1st Edition holofoil but $39.28 unlimited, so each option spells out how to tell them apart
("1st Edition stamp and shiny art", "shiny everywhere except the artwork"). Pick yours and you
get its market price plus low / mid / high, and the European Cardmarket figures.

**Cards nobody has sold yet** still get a number. Brand-new sets take months to appear on
TCGplayer, so those cards fall back to their European market price, or to what that rarity
typically sells for in recent sets. Every estimate is clearly marked — a `~`, an amber colour,
an `EST` tag, and a note in the card sheet explaining exactly where the figure came from.

**My collection** (under *View more*) — an online way to keep track of your Pokémon. Hit
*+ Add to collection* on any card search result, or open any card and hit *✓ I have this card*.
Everything you add collects in one place with its total value, and you can search it and sort it —
newest, price high to low or low to high, name, set, or binder order. Click a
card in your collection to record which page and pocket it's in in your real binder.

**Scan a card** — point your camera at a card (or pick a photo of it) and the site reads its name
and number, finds that exact card, and lets you add it with one tap. You can fix what it read if it
gets it wrong.

You have to **sign in** to make a collection so it can be saved — pick a name and a password.
Your collection saves on that device under your name. Browsing sets, prices and card search never
needs signing in.

## Running it

It's one HTML file with no build step and no dependencies — open `index.html` in a browser and it
works. Card data is fetched live from the Pokémon TCG API, so it needs an internet connection.

## Data

- Cards, sets and card prices: the free [Pokémon TCG API](https://pokemontcg.io) (no key needed).
- Sealed booster-pack prices: TCGplayer market data via [tcgcsv.com](https://tcgcsv.com), baked
  into `index.html` because tcgcsv sends no CORS headers. Refresh them with
  `python update-pack-prices.py`.

Card images and names are © The Pokémon Company. This is a fan project and is not affiliated with
or endorsed by Nintendo, Creatures Inc., GAME FREAK, or The Pokémon Company.
