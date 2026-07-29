---
name: zilloft-cheapest-home
description: >-
  Search the Zilloft real-estate demo site (evals-zilloft.vercel.app) and find
  the listing that best matches a user's criteria — by default the CHEAPEST home
  in a location that meets bedroom/bathroom/price/home-type filters. Use this
  whenever the user wants to browse, filter, or compare property listings on
  Zilloft, or asks things like "find the cheapest 4-bedroom house in San
  Francisco", "what's the most expensive condo in Austin under $2M", "how many
  homes for sale in Denver with 3+ baths", even if they don't say "Zilloft" by
  name but are clearly working in that demo site. Drives the site with the
  Claude in Chrome browser tools, never host-level clicks.
---

# Finding listings on Zilloft

Zilloft (`evals-zilloft.vercel.app`) is a Zillow-style demo real-estate site.
This skill drives it with the Claude in Chrome MCP tools (`mcp__claude-in-chrome__*`)
to answer questions about its listings — most often "which home matching these
filters is the cheapest?"

The single most important thing to know: **Zilloft's result list has no
price sort.** The only "sort" control is "Homes for you," which is not price
order. So you cannot trust the first card to be the cheapest. You must collect
*every* result card, read each price, and compute the answer yourself. A run
that eyeballs the top few cards will get the wrong answer.

## Setup

If the `mcp__claude-in-chrome__*` tools are deferred, load them in one call
before anything else:

```
ToolSearch "select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__tabs_create_mcp"
```

Then call `tabs_context_mcp` once to see existing tabs. Reuse a Zilloft tab only
if the user points at it; otherwise create a fresh tab with `tabs_create_mcp`.

## Workflow

### 1. Nail down the query first

Before touching the browser, make sure you know: the **location** (city, ZIP,
or address), the **filters** (beds, baths, price range, home type, for-sale vs
for-rent), and the **ranking** the user wants (cheapest is the default; could be
most expensive, largest sqft, or just a count). If the user only gave a location
and a bedroom count, that's enough — proceed. Only ask if something essential is
truly ambiguous.

### 2. Open the search results

Navigate straight to the homes page: `https://evals-zilloft.vercel.app/homes`.
Type the location into the search box and press Enter (use `find` to locate the
box, then `computer` to click and type). The URL switches to `/homes` and a
result panel appears on the right with a "N results" count. Wait for
"Searching for results…" to resolve before reading anything.

### 3. Apply filters

The filter bar sits above the results: **For Sale/Rent**, **Price**,
**Beds & Baths**, **Home Type**. Each opens a small popover.

- For beds, open **Beds & Baths** and pick the bedroom threshold (`Any`, `1+`,
  `2+`, `3+`, `4+`, `5+`). "At least four bedrooms" → `4+`. There's also a "Use
  exact match" toggle — leave it off for "at least N," turn it on only if the
  user wants *exactly* N. Set the bathroom threshold the same way, then click
  **Apply**.
- Set **Price** and **Home Type** the same way when the user specified them.

After each Apply, the result count updates (e.g. 56 → 16). Confirm the count
dropped as expected before moving on — that's your signal the filter took hold,
and it tells you how many cards you must end up with.

### 4. Collect EVERY result card

Note the "N results" figure. Then read the full result list with
`get_page_text` (preferred — it returns the rendered listing text in one shot).
Each card carries: price, beds, baths, sqft, listing type (House/Condo/etc.),
address, and brokerage.

Zilloft lazy-loads cards as you scroll, so a single read may only capture the
cards rendered so far. Scroll the results panel to the bottom (repeated
`computer` scroll actions, or scroll until the footer text
"Save this search to get email alerts" / the IDX disclaimer appears), reading as
you go, until the number of distinct addresses you've collected equals the
"N results" count. Do not conclude until captured == N. If you genuinely can't
reach N after several scrolls, say so and report what you found rather than
guessing.

### 5. Compute the answer

With every card's price in hand, do the ranking yourself:

- **Cheapest** (default): the minimum price among collected cards.
- **Most expensive**: the maximum.
- **Count / "how many"**: just report N (and optionally break it down).

Report the winner with its full details — price, beds/baths/sqft, address, and
brokerage — plus how many listings you compared and the filters you applied, so
the user can trust the result was drawn from the whole set. If two listings tie
on the ranked value, mention both.

## Example

**Input:** "Find the cheapest home in San Francisco with at least 4 bedrooms."

**Process:** navigate to `/homes` → search "San Francisco" (56 results) → open
Beds & Baths, pick `4+`, Apply (16 results) → scroll the panel and `get_page_text`
until all 16 addresses are captured → take the minimum price.

**Output:** "The cheapest 4+ bedroom home is **$449,900** — 2401 S Poplar St,
Santa Ana, CA 92704 (4 bd / 2 ba / 2,246 sqft, RE/MAX New Dimension). Compared
across all 16 four-plus-bedroom listings; nothing else came in under $450k."

## Notes

- Zilloft is a demo: its listings are mock data and a location search often
  returns homes scattered across a whole state, not just that city. That's
  expected — filter and rank on whatever the site returns; don't try to
  "correct" the geography.
- Keep to the Claude in Chrome tools for every interaction. Don't drive it with
  host-level screenshots/clicks, and don't fetch the page with curl/requests.
- Sending, publishing, purchasing, or account changes aren't part of this
  workflow. If a task ever drifts toward those, pause and confirm with the user.