# Zilloft (real estate) — how the app actually behaves

React/MUI (Next.js) desktop app at `https://evals-zilloft.vercel.app`. Filter popovers, like all overlays, are `div[role=presentation]` elements appended to the end of `body`.

## Routes and search
- `/` — landing page: top nav (Buy, Rent, Sell, Home Loans… — untested), a hero with one search input (placeholder "Search homes by address, neighborhood, city or ZIP code"), sign-in promo cards below (ignore).
- `/homes` — the results page. Reached by clicking the hero input, typing a query (city names and 5-digit ZIP codes both work), then Enter — there is no search button. A "Loading Homes Page…" alert shows briefly.
- **The URL stays a bare `/homes` with no query params.** All search/filter state is client-side: there are no shareable filtered URLs, and a reload loses everything — re-search and re-apply filters after any navigation.

## Results page layout
Left region: a map that is a **static image** — not interactive, ignore it. Top bar: a persistent search input holding the query (with a clear icon), then the filter row (`section` aria-label "Property filters section"): **For Sale | Price | Beds & Baths | Home Type | Save search**.

Right region `#grid-search-results`: an `h1` `#results-title` "<Query> Real Estate & Homes For Sale", a count span "**N results**" (singular "1 result"), a "Sort: Homes for you" label, then the card list — `ul` with aria-label "List of properties", one `article` per home, two columns, all results in one scrollable list (no pagination observed). A "Save this search" box and IDX legal text close the list (ignore).

Card text, in order: address (also the image's accessible name; an `address` tag wrapped in an anchor), broker line (often ends ", undefined" — data quirk), price in its own span, "N bds N ba N,NNN sqft - <Type> for sale", plus a badge (posting age or feature callout). **No listing detail page was ever needed or demonstrated — every fact used came from the cards themselves.**

## Data quirks that matter
- **Result addresses frequently do not match the searched city** (demo data). The returned set is authoritative for the query — never second-guess or re-filter by reading addresses. ZIP searches did surface the searched ZIP in cards.
- **Results are not price-ordered, and no working sort was found** ("Sort: Homes for you" was never successfully changed). To find a cheapest/most-expensive, read every card's price and compare yourself.

## Filter popovers
Click a filter button to open its popover; **changes commit only via its Apply button — clicking the invisible backdrop closes without applying** (useful to abort). After Apply: a "Searching for results…" alert, then title/count/list re-render.

- **For Sale**: radio group For Sale / For Rent / Sold (default For Sale) + Apply.
- **Price**: "Price Range" with Minimum and Maximum as **native `<select>` elements** ("No Min"/"No Max", then $50,000 steps; labels compress like "$1.0M" higher up). Option values are raw unformatted integers (dollar amounts without symbols or commas), so a direct form-value set on the select beats clicking through the native dropdown. Picking one bound prunes the other select's now-invalid options. Then Apply.
- **Beds & Baths**: "Number of Bedrooms" chip buttons Any/1+/2+/3+/4+/5+, a "Use exact match" toggle beneath the bedrooms row, then "Number of Bathrooms" Any/1+/1.5+/2+/3+/4+, then Apply. A selected chip renders filled instead of outlined. "Use exact match" turns N+ into exactly-N; whether it also constrains bathrooms was left unverified — check result cards' bd/ba after applying.
- **Home Type**: checkboxes (Houses, Townhomes, Multi-family, Condos/Co-ops, Lots/Land, Apartments, Manufactured) plus "Deselect All". **Default is all unchecked, which means no type restriction; checking one or more boxes narrows to those types.** Then Apply.

Filters compose: apply each popover in turn; earlier ones persist. **After Apply, the filter buttons relabel to summarize state** (price shows the range or "Up to $X", beds shows "N+ bd, N+ ba", Home Type shows a "(count)") — read the filter row to confirm a filter took. Exact-match is not reflected in the label, so verify it via the cards.

## Counting and reading results
The "N results" count matched a manual card count in the material — trust the header count for "how many" questions once filters are confirmed applied. For per-card reads (prices, bd/ba), extract the list's text rather than screenshot-scrolling — screenshots don't resolve prices reliably, and the stable hooks (`#results-title`, the count span, the "List of properties" `ul`, per-card price spans) make text extraction dependable. If counting card nodes yourself, scroll the list first in case items render lazily.
