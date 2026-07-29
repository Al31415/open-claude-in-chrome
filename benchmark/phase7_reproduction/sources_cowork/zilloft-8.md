---
name: search-zilloft
description: >-
  Search for homes on Zilloft (the evals-zilloft.vercel.app demo real-estate
  app, a Zillow-style site) by ZIP code, neighborhood, city, or address, apply
  beds/baths, price, and listing-status filters, and report how many listings
  match and what they are. Use this skill whenever the user wants to look up
  homes on Zilloft, count listings in a ZIP code, filter by bedrooms/bathrooms
  or price range, check what's for sale/rent/sold in an area, or drive the
  Zilloft site in the browser — even if they only give a ZIP and some criteria
  without saying "search". Drives the site with the Claude in Chrome browser
  tools, not host-level clicks.
compatibility: >-
  Requires the Claude in Chrome MCP tools (mcp__claude-in-chrome__*). Load them
  with ToolSearch before starting. Does not require host-level computer use.
---

# Search homes on Zilloft

This skill searches for homes on the Zilloft demo app at
`https://evals-zilloft.vercel.app`. It is a Zillow-style real-estate site: you
enter a location (ZIP code, city, neighborhood, or address), then narrow the
results with filter dropdowns for listing status, price, and beds/baths. The end
state is a results list with a count like "**1 result**" next to the location
heading — that count, plus the matching listing cards, is what the user is after,
so always read it back.

The whole flow happens inside the page, so drive it with the Claude in Chrome
browser tools (`navigate`, `read_page`/`get_page_text`, `find`, `computer` for
clicks). Do **not** use host-level mouse/keyboard control — operating on the page
directly is faster and far more reliable than clicking screen coordinates, and it
survives the window moving or resizing.

## Inputs

Gather these before you start. Only the location is essential; ask for it if
missing, but for the filters pick sensible defaults or leave them unset rather
than stalling.

- **Location** (required): what to type into the search box — a ZIP code
  (e.g. `92114`), city, neighborhood, or street address.
- **Bedrooms** (optional): a minimum like "3+", or an exact count. Zilloft's
  bedroom buttons are Any / 1+ / 2+ / 3+ / 4+ / 5+.
- **Bathrooms** (optional): Any / 1+ / 1.5+ / 2+ / 3+ / 4+.
- **Exact match** (optional): the beds/baths panel has a "Use exact match"
  toggle. When on, the selected bedroom/bathroom counts are treated as *exactly*
  that number rather than "or more" (e.g. exactly 3 beds, not 3+). Turn it on
  only when the user wants an exact count; leave it off for "at least" searches.
- **Price range** (optional): a minimum and/or maximum from the Price dropdown's
  preset values (No Min, $50K, $100K, … stepping up through the millions).
- **Listing status** (optional): For Sale / For Rent / Sold. Defaults to
  **For Sale** on the site, which is right for most "homes for sale" requests.

If the user only gives a location, just run the search with no filters and report
what comes back — that's a valid request on its own.

## Workflow

Load the browser tools first, in one ToolSearch call:

```
ToolSearch "select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__find,mcp__claude-in-chrome__computer"
```

Then call `tabs_context_mcp` to see current tabs. Open a **new** tab for this task
with `tabs_create_mcp` rather than hijacking one the user is already using, unless
they point you at an existing Zilloft tab.

### 1. Open the site and search the location

Navigate the new tab to `https://evals-zilloft.vercel.app/`. Type the location
into the "Enter an address, neighborhood, city or ZIP code" box on the hero
section and press Enter. An autocomplete list may appear as you type; pressing
Enter on a plain ZIP works without picking a suggestion. The page navigates to
`/homes` and shows a map on the left and a results panel on the right, headed
"<location> Real Estate & Homes For Sale" with a result count.

If a city name is ambiguous, the autocomplete offers specific options (e.g.
"San Francisco, CA"); prefer the exact match the user meant, and mention which
one you picked if it was unclear.

### 2. Apply the filters

The filter bar sits above the results: **For Sale**, **Price**, **Beds & Baths**,
and **Home Type** dropdowns, plus a "Save search" button. Open each dropdown you
need, make the selection, and click its **APPLY** button — the results re-query
(a brief "Searching for results…" spinner) and the dropdown's chip updates to
reflect the choice.

Apply only the filters the user asked for. Order doesn't matter, but a natural
sequence is:

- **Beds & Baths**: open the dropdown. Under "Number of Bedrooms" click the count
  (Any / 1+ / 2+ / 3+ / 4+ / 5+); under "Number of Bathrooms" click the count
  (Any / 1+ / 1.5+ / 2+ / 3+ / 4+). If the user wants an *exact* count, click the
  "Use exact match" radio so it's selected — this makes both the bed and bath
  selections exact rather than "or more". Click **APPLY**.
- **Price**: open the Price dropdown. Pick a **Minimum** and/or **Maximum** from
  the preset dropdown lists, then click **APPLY**. The chip shows e.g.
  "$600K - $800K".
- **For Sale / For Rent / Sold**: open the leftmost dropdown, select the radio,
  click **APPLY**. Leave it on "For Sale" unless the user wants rentals or sold
  comps.

After each apply, let the spinner settle before reading the new count — the
result total can change (e.g. from "2 results" to "1 result") as filters narrow.

### 3. Read and report the results

Read the results panel with `get_page_text` or `read_page`. Report back:

- the **result count** shown next to the "<location> Real Estate & Homes For Sale"
  heading (this is the headline answer), and
- a short rundown of the matching **listing cards** — each shows a price, beds /
  baths / square footage, address, and listing brokerage, e.g.
  "$625,000 — 3 bds, 2 ba, 1,375 sqft — 174 Coolwater Dr, San Diego, CA 92114".

State which filters you applied so the count is unambiguous (e.g. "1 home for
sale in 92114 with exactly 3 beds / 2 baths, priced $600K–$800K"). If zero
listings match, say so plainly rather than implying the search failed.

## Notes and failure handling

- This is a demo/eval site with a small fixed catalog, so tight filters often
  leave just one or two results — a low count is usually correct, not a bug.
- "Use exact match" changes the meaning of the bed/bath counts; double-check the
  user actually wants exact counts before enabling it, since it can drop the
  result count sharply (an exact "3 beds" excludes 4- and 5-bed homes that a "3+"
  search would include).
- The Price presets are fixed increments; if the user's number falls between
  presets, pick the nearest sensible bound and mention it.
- If a browser tool fails or the page doesn't respond after 2–3 tries, stop and
  tell the user what you attempted and what you saw, rather than retrying the same
  action or wandering the site.
- Never trigger native JS `alert`/`confirm` dialogs; they freeze the browser
  extension. Prefer reading page text over interacting with elements that pop
  modal browser dialogs.
- Don't reuse tab IDs from a previous session; if a tool reports an invalid tab,
  call `tabs_context_mcp` for fresh IDs.