# Zilloft — Operating Recipe

Zillow-style demo real-estate app at `https://evals-zilloft.vercel.app`. Mock catalog: a city search returns listings scattered across the whole state — expected; count and rank whatever the site returns, don't "correct" geography. Tight filters legitimately leave one, two, or zero results.

## Search
- Go straight to `/homes`, or use the home-page hero box ("Enter an address, neighborhood, city or ZIP code"). Type the location, press Enter. A plain ZIP works without picking an autocomplete suggestion; for ambiguous city names pick the exact autocomplete option.
- Results page: map left; results panel right, headed "<location> Real Estate & Homes For Sale" with a live "N results" count.
- Wait for the "Searching for results…" spinner to resolve before reading anything.

## Filters
- Filter bar above the results: For Sale/Rent/Sold, Price, Beds & Baths, Home Type. Each opens a popover; nothing takes effect until you click its APPLY.
- Beds: Any/1+/2+/3+/4+/5+. Baths: Any/1+/1.5+/2+/3+/4+. The "Use exact match" toggle flips BOTH beds and baths to exactly-N — leave off for "at least N", enable only for "exactly N" (it excludes higher counts and can shrink results sharply).
- Price: Minimum and Maximum preset dropdowns. "Under $X" = leave Minimum at No Min, set Maximum. Presets are fixed increments — if the user's bound falls between, pick the nearest sensible one and say so.
- Home Type: a checklist (Houses, Townhomes, Multi-family, Condos/Co-ops, Lots/Land, Apartments, Manufactured) with Deselect All. Check exactly the named type(s).
- Status defaults to For Sale — right unless the user wants rentals or sold comps.
- After APPLY the chip relabels (price-range text, a count on Home Type) and "N results" changes as the spinner resolves. If neither happened, the filter didn't register — reopen and reapply.

## Counting questions
- The final "N results" counter IS the answer — but only after ALL requested filters are applied and the spinner has settled. A partially-filtered count is a wrong answer; the number changes with every filter.
- Cross-check small counts (roughly ≤25) by scrolling the panel to the bottom and confirming distinct addresses equal N. For large counts, trust the counter and say so. If cards and counter disagree, report the discrepancy.

## Ranking questions (cheapest / most expensive)
- There is NO price sort — the only sort, "Homes for you", is not price order. Never trust the top cards; collect every card and compute min/max yourself.
- Cards lazy-load on scroll: one text read captures only rendered cards. Scroll the panel repeatedly, reading as you go, until distinct collected addresses equal "N results". The footer ("Save this search…" / IDX disclaimer) marks the bottom.
- Do not conclude until captured == N. If you can't reach N after several scrolls, say so and report what you have.
- Cards carry price, beds/baths, sqft, home type, address, brokerage — enough to rank without opening listings.
- Report the winner with full card details, how many listings you compared, and the live filters; mention ties.

## Tool tactics
- Drive the page with browser tools (navigate, find, click, type) — never host-level screen coordinates.
- Text extraction (get_page_text / read_page) beats screenshots for counts, card fields, and chip state; use find to locate the search box and filter buttons.
- If a filter control is a native select, set its value directly with the form-input tool rather than clicking through options; verify the chip afterward.
- Never trigger native alert/confirm dialogs — they freeze browser tooling.
- After 2–3 failed tries on one step, stop and report what you attempted and saw.
- Stay read-only: don't save searches or touch account actions while counting or ranking.
