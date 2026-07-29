---
name: zilloft-listing-count
description: >-
  Count how many listings on the Zilloft real-estate demo site
  (evals-zilloft.vercel.app) match a set of filters — a home type, a price cap
  or range, a location, and optionally beds/baths. Use this whenever the user
  asks a "how many" / "count" question about Zilloft inventory, such as "how
  many manufactured homes are for sale in San Francisco under $1M", "count the
  condos in Austin between $500k and $900k", or "how many 3+ bedroom houses are
  listed in Denver", even if they don't say "Zilloft" by name but are clearly
  working in that demo site. The answer is a NUMBER (a count), not a specific
  listing — that's what sets this apart from finding the cheapest/best home.
  Drives the site with the Claude in Chrome browser tools, never host-level
  clicks.
---

# Counting listings on Zilloft

Zilloft (`evals-zilloft.vercel.app`) is a Zillow-style demo real-estate site.
This skill drives it with the Claude in Chrome MCP tools (`mcp__claude-in-chrome__*`)
to answer **"how many listings match these filters?"** — for example, how many
manufactured homes in San Francisco are priced under $1M.

The whole task hinges on one thing the site does for you: the results panel
shows a live **"N results"** counter that updates every time a filter is
applied. When the question is purely a count, that final counter *is* your
answer — you do not need to read the price of every card the way a
cheapest-home search does. The skill is therefore mostly about applying the
filters correctly and reading the counter at the right moment.

## The one trap to avoid: read the count only after the LAST filter settles

Each filter updates the count independently, so a partially-filtered count is
**not** the answer. In the reference workflow, checking "Manufactured" alone
showed **38**, and only after the "under $1M" price cap was applied did it
settle to **24**. If you report the number before every requested filter is in
place — or while the panel still says "Searching for results…" — you'll report
a wrong, larger count. Always apply *all* the user's filters first, wait for the
spinner to resolve, and only then read "N results."

## Setup

If the `mcp__claude-in-chrome__*` tools are deferred, load them in one call
before anything else:

```
ToolSearch "select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__tabs_create_mcp"
```

Then call `tabs_context_mcp` once to see existing tabs. Reuse a Zilloft tab only
if the user points at it; otherwise create a fresh tab with `tabs_create_mcp`.

## Workflow

### 1. Pin down the filters

Before touching the browser, be clear on exactly what defines a match: the
**location**, the **home type(s)** (Houses, Townhomes, Multi-family,
Condos/Co-ops, Lots/Land, Apartments, Manufactured), the **price** bound
(a max, a min, or a range), and any **beds/baths** threshold. For-sale is the
default; switch to For Rent only if the user asks. A location plus one filter is
enough to proceed — only ask if something essential is genuinely ambiguous.

### 2. Open the search results

Navigate to `https://evals-zilloft.vercel.app/homes`. Type the location into the
search box and press Enter (use `find` to locate the box, then `computer` to
click and type). A result panel appears on the right with an initial
"N results" count. Wait for "Searching for results…" to resolve before reading
anything.

### 3. Apply every requested filter

The filter bar sits above the results: **For Sale/Rent**, **Price**,
**Beds & Baths**, **Home Type**. Each opens a small popover.

- **Home Type** opens a checklist. Check exactly the type(s) the user named
  (e.g. "Manufactured") and click **Apply**. There's a "Deselect All" link if
  you need to clear a preset. The filter button then shows a count like
  "Home Type (1)" confirming it took hold.
- **Price** has **Minimum** and **Maximum** dropdowns. For "under $1M," leave
  Minimum at "No Min" and set Maximum to "$1.0M," then **Apply**. For a range,
  set both ends. The button relabels to e.g. "Up to $1M."
- **Beds & Baths** offers thresholds (`Any`, `1+` … `5+`) plus a "Use exact
  match" toggle — leave it off for "at least N," turn it on for "exactly N."

After each **Apply**, watch the "N results" figure change and the spinner
resolve. The count dropping is your signal the filter registered.

### 4. Read the final count — and sanity-check it

Once all filters are applied and the panel has settled, read the **"N results"**
line (use `get_page_text` or `read_page`). That number is the answer.

For a trustworthy result, cross-check it against the cards when it's cheap to do
so: for small counts (roughly ≤ 25), scroll the results panel and confirm the
number of distinct listing addresses matches "N results." Zilloft lazy-loads
cards on scroll, so scroll to the bottom (until the "Save this search…" / IDX
disclaimer footer appears) before concluding they match. For large counts,
trust the counter rather than enumerating everything, but say that's what you
did. If the counter and the cards disagree, report the discrepancy instead of
picking one silently.

### 5. Report the number with its filters

State the count and the exact filters it reflects, so the user can trust it:
"**24** manufactured homes are for sale in San Francisco under $1M." If useful,
add a one-line breakdown (e.g. how the count changed as filters were applied),
but the headline is the number.

## Example

**Input:** "How many manufactured homes are for sale in San Francisco under $1M?"

**Process:** navigate to `/homes` → search "San Francisco" (56 results) → open
**Home Type**, check **Manufactured**, Apply (38 results) → open **Price**, set
Maximum **$1.0M**, Apply (24 results) → wait for the spinner, read "24 results"
→ scroll the panel and confirm 24 distinct addresses render.

**Output:** "There are **24** manufactured homes for sale in San Francisco
priced under $1M. (Filtering to Manufactured alone gave 38; the under-$1M cap
brought it to 24, which I confirmed against the listing cards.)"

## Notes

- Zilloft is a demo: its listings are mock data, and a city search often returns
  homes scattered across the whole state, not just that city. That's expected —
  count whatever the site returns for the filters; don't try to "correct" the
  geography.
- Keep to the Claude in Chrome tools for every interaction. Don't drive it with
  host-level screenshots/clicks, and don't fetch the page with curl/requests.
- This skill only reads and counts. Saving searches, publishing, purchasing, or
  account changes aren't part of it — if a task drifts that way, pause and
  confirm with the user.