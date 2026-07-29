---
name: dashdish-category-analysis
description: >-
  Answer questions about the restaurants grouped into a category row on DashDish
  (the evals-dashdish.vercel.app demo delivery app) — most often "how many
  restaurants in a given category offer delivery?", but also counts,
  filters, and comparisons like "which places under Best of lunch are rated 4.8+"
  or "list the National favorites within 1 mile." Use this skill whenever the
  user wants to count, filter, tally, or compare DashDish restaurants inside one
  of the home-page category rows (Under $1 delivery fee, Best of lunch, The
  Infatuation's picks, Light & fresh, National favorites, and the cuisine rows),
  even if they don't say "DashDish" by name but are clearly working in that demo
  site. Drives the site with the Claude in Chrome browser tools, never
  host-level clicks.
compatibility: >-
  Requires the Claude in Chrome MCP tools (mcp__claude-in-chrome__*). Load them
  with ToolSearch before starting. Does not require host-level computer use.
---

# Analyzing a DashDish category row

DashDish (`https://evals-dashdish.vercel.app`) is a DoorDash-style demo delivery
site. Its home page arranges restaurants into horizontal **category rows** —
each a titled band of restaurant cards, e.g. "Under $1 delivery fee",
"Best of lunch", "The Infatuation's picks", "Light & fresh", "National
favorites", plus the cuisine rows reachable from the icon strip at the top
(Ramen, Pizza, Chinese, …). This skill answers questions *about the restaurants
in one of those rows*: how many there are, how many meet a condition (offers
delivery, rating ≥ X, under N minutes, within N miles), or which one wins on some
attribute.

Drive everything with the Claude in Chrome browser tools (`navigate`,
`get_page_text`/`read_page`, `find`, `computer` for clicks). Do **not** use
host-level mouse/keyboard control — reading and clicking the page directly is
faster and far more reliable than screen coordinates, and it survives the window
moving or resizing.

## The two things that make this easy to get wrong

**1. A row shows only a handful of cards, but the row may contain more.** Each
band renders ~5 cards with a "See all" link and left/right arrows. The arrows
often don't advance (when the row already fits), so scrolling the carousel is
not a reliable way to see the whole set. To get the *complete* membership of a
category, click its **"See all"** link and read the full category page. Counting
only the ~5 visible cards is the classic mistake — confirm you have the full set
before you tally.

**2. "Offers delivery" has a signal on the page — you rarely need to open each
store.** The home page has a **Delivery / Pickup** toggle near the top. With
**Delivery** selected (the default), every card shown is a delivery-capable
restaurant, and each card carries a delivery line like "$0 delivery fee, first
order" plus an ETA (e.g. "28 min"). So for a plain "how many offer delivery"
question, the answer is the count of cards in that category under the Delivery
view — you do **not** have to click into all five stores one by one. Open an
individual store page only to resolve a genuine ambiguity (a card missing the
delivery line, or the user asking about a specific place); there the
Delivery/Pickup toggle and a "Delivery 45–60 min" estimate confirm it.

## Setup

If the `mcp__claude-in-chrome__*` tools are deferred, load them in one call
before anything else:

```
ToolSearch "select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__tabs_create_mcp"
```

Then call `tabs_context_mcp` once to see existing tabs. Reuse a DashDish tab only
if the user points at it; otherwise create a fresh tab with `tabs_create_mcp`.

## Workflow

### 1. Pin down the category and the condition

Know two things before touching the browser: **which category row** the user
means (match their words to a row title — "light and fresh" → "Light & fresh"),
and **what you're measuring** — a simple count, a filter ("offer delivery",
"rated 4.8+", "under 30 min", "within 1 mile"), or a comparison ("cheapest
delivery fee", "fastest"). "How many offer delivery" is the common default. If
the row name is ambiguous or doesn't exist on the page, say what rows you *do*
see rather than guessing.

### 2. Open the site and set the mode

Navigate the tab to `https://evals-dashdish.vercel.app/`. Confirm the
**Delivery** toggle is selected (it is by default) — for delivery questions this
is what makes the card set meaningful. If the user is asking about pickup
instead, switch to **Pickup** first.

### 3. Get the FULL membership of the category

Scroll down to the category row by its title (`get_page_text` to see all row
titles at once, then scroll to the one you want). Click that row's **"See all"**
link to open the complete category listing. Read the whole listing with
`get_page_text` — each card gives name, rating, distance, ETA, and the delivery
line. If a row has no "See all" (small rows sometimes don't), the ~5 cards shown
are the whole set; verify by checking that the arrows don't reveal more.

Count the distinct restaurant names you collect. That count is your denominator.

### 4. Apply the condition and compute the answer

Work from the card text you collected:

- **Offers delivery** (default): under the Delivery view, that's every card with
  a delivery line / ETA — normally all of them. Report the count, and note if
  any card lacked the delivery signal (open just that store to confirm before
  excluding it).
- **Rating / time / distance filter**: read the value off each card
  (e.g. "4.8 ★ · 0.3 mi · 28 min") and count those that pass.
- **Comparison** (cheapest fee, fastest, closest): rank the collected cards on
  that field yourself and name the winner.

### 5. Report back

Give the number, then show your work briefly: the category, the full set size,
and the names that met the condition (or the winner with its stats). Something
like: "In **Light & fresh**, all **5** restaurants offer delivery — Pokebola,
Sarku Japan, Schlok's Bagels & Lox, Souvla, and Freshroll (each shows a delivery
ETA and $0 first-order delivery fee)." Listing the names lets the user trust the
count came from the whole row, not just the cards that happened to be visible.

## Notes and failure handling

- DashDish is a demo/eval site with a small fixed catalog. The same restaurant
  can appear in several rows (e.g. Souvla in both "The Infatuation's picks" and
  "Light & fresh") — that's expected; answer about the row the user named.
- This skill only *reads* the site. Placing an order is a different job — use the
  `order-dashdish` skill for that. Don't add anything to a cart while counting.
- If a browser tool fails or the page doesn't respond after 2–3 tries, stop and
  tell the user what you attempted and what you saw, rather than retrying the
  same action or wandering the site.
- Never trigger native JS `alert`/`confirm` dialogs; they freeze the browser
  extension. Prefer reading page text over poking elements that pop modal
  dialogs.
- Don't reuse tab IDs from a previous session; if a tool reports an invalid tab,
  call `tabs_context_mcp` for fresh IDs. And don't fetch the page with
  curl/requests — drive it through the Claude in Chrome tools.