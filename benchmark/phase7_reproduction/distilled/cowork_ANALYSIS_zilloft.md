# Zilloft — site behavior reference

Zillow-style demo real-estate app at `https://evals-zilloft.vercel.app`. Small fixed mock catalog. A city search returns homes scattered across the whole state — expected; filter and count whatever the site returns, never "correct" the geography. Tight filters legitimately leave one, two, or zero results; a low count is usually right, not a bug.

## Page map
- **Home `/`**: hero search box "Enter an address, neighborhood, city or ZIP code". Typing shows autocomplete; Enter on a plain ZIP works without picking a suggestion; for an ambiguous city pick the exact suggestion.
- **`/homes`**: the results page, directly navigable (search box present there too). Map on the left; results panel on the right headed "<location> Real Estate & Homes For Sale" with a live **"N results"** count; filter bar above the results: **For Sale (status)**, **Price**, **Beds & Baths**, **Home Type**, plus a Save-search button.
- Each result card carries: price, beds, baths, sqft, listing type (House/Condo/…), street address, brokerage.

## Filter mechanics
All four filters are popovers; **nothing takes effect until the popover's APPLY is clicked**. After Apply: a "Searching for results…" spinner runs, the count updates, and the filter button relabels (a selected-type count, "Up to $X", "$X - $Y") — relabel plus count movement confirm it registered. Always wait for the spinner to settle before reading.

- **Status**: For Sale / For Rent / Sold radios; For Sale is default — switch only when asked.
- **Price**: separate **Minimum** and **Maximum** preset dropdowns in fixed increments from "No Min". "Under $X" → leave Minimum at No Min, set only Maximum. If a bound falls between presets, pick the nearest and say so.
- **Beds & Baths**: bedroom buttons Any/1+/2+/3+/4+/5+; bathrooms Any/1+/1.5+/2+/3+/4+. A **"Use exact match" toggle** flips BOTH from "at least N" to "exactly N" — enable only for explicit "exactly" requests (exact-3 excludes the 4s and 5s a "3+" search includes, so counts can drop sharply).
- **Home Type**: checklist (Houses, Townhomes, Multi-family, Condos/Co-ops, Lots/Land, Apartments, Manufactured) with "Deselect All". Check exactly the named type(s), Apply.

## Counting questions
The live **"N results" counter is itself the answer** to "how many" questions — but only after **every** requested filter is applied and the spinner settles. Each filter changes the number independently, so a partially-filtered count is a wrong (larger) answer. Sanity-check when cheap: for small counts, scroll and confirm distinct addresses equal N; for large counts, trust the counter and say so. If counter and cards disagree, report the discrepancy.

## Ranking questions (cheapest / most expensive / largest)
**There is no price sort.** The only sort control, "Homes for you", is not price order — the first card proves nothing. Collect every card and compute the answer yourself:
1. Apply all filters; the "N results" figure is how many cards you must capture.
2. Cards **lazy-load on scroll**: one text extraction captures only cards rendered so far. Scroll the results panel repeatedly, extracting as you go, until the footer appears ("Save this search to get email alerts" / the IDX disclaimer).
3. Track distinct addresses; **do not conclude until captured == N**. If N stays out of reach after several scrolls, report the shortfall instead of guessing.
4. Rank on the requested field yourself; mention ties.

## Fastest reliable route
Navigate straight to `/homes` → type the location, Enter → wait for the spinner → apply each needed filter with APPLY, letting the count settle after each → for counts read "N results"; for rankings do the full scroll-and-collect. Report the answer with the filters applied and set size so it's auditable.

## Tool tactics
- Page-text extraction is the workhorse: one call returns the heading, count, and every rendered card — far better than screenshots for listings. Use element-find for the search box and filter buttons; click/type with in-page tools, never host-level coordinates.
- Load the browser toolset in one ToolSearch batch; fetch tab context first; fresh tab unless pointed at one; stale tab IDs error — refresh context.
- Never trigger native JS alert/confirm dialogs (they freeze the extension); don't fetch the site with curl.
- After 2–3 failed tries, stop and report rather than retry-looping. Read-only tasks must not save searches or drift into account actions.
