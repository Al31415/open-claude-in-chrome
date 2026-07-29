---
name: dashdish-food-run
description: >-
  Place a food delivery order end-to-end on DashDish (the
  evals-dashdish.vercel.app demo delivery site) — find a restaurant, add and
  customize a menu item, and complete checkout with the user's delivery-timing
  and drop-off preferences. Use this skill whenever the user wants to order
  food, do a food run, grab lunch/dinner, reorder, "get me X from Y", or
  otherwise drive the DashDish site — even if they only name a restaurant and a
  dish without saying the word "order". Drives the site with the Claude in
  Chrome browser tools, never with host-level mouse/keyboard clicks.
---

# DashDish food run

This skill places a delivery order on the DashDish demo site
(`evals-dashdish.vercel.app`) from start to finish. It was captured from a
recorded walkthrough, so the steps below reflect how the site actually behaves —
including a few quirks that trip up a naive click-through.

Drive everything through the **Claude in Chrome MCP tools**
(`mcp__claude-in-chrome__*`): `navigate`, `read_page` / `get_page_text` to see
the current state, `find` to locate elements, `computer` to click and type, and
`tabs_context_mcp` / `tabs_create_mcp` to manage tabs. Do not use host-level
screen clicks — the page is the source of truth, so read it and act on it
directly. If these tools are deferred, load them first with a single ToolSearch
call (see the claude-in-chrome skill).

## What you need from the user

At minimum you need a **restaurant** and an **item**. Everything else has a
sensible default, but confirm anything the user cares about:

- Restaurant name (e.g., "Taco Bell")
- Item name (e.g., "Classic Cheeseburger") and any size / customization
- Delivery timing — Standard, Express, or **Schedule for later** (the
  walkthrough scheduled for later; use whatever the user asks)
- Drop-off preference — hand it to me, or leave at door (see the note below
  about clearing boilerplate)
- Address, payment, and tip are usually pre-filled on this demo; just verify
  them at checkout rather than assuming.

If the user only gave a restaurant and a dish, that's enough to start — proceed
and confirm the checkout details before placing the order.

## Workflow

### 1. Open DashDish

Navigate to `https://evals-dashdish.vercel.app`. If a tab is already on the
site, reuse it; otherwise open a new tab. A launch/disclaimer banner may appear
at the top — it's harmless, ignore or dismiss it.

### 2. Find the restaurant — search, don't browse

The homepage has a category rail (Ramen, Pizza, etc.) and scrollable rows. It's
tempting to scroll for the restaurant, but that's slow and unreliable. Instead,
click the **"Search Dashdish"** box, type the restaurant name, and press Enter.
Then click the matching result under "Search Results". This lands you on the
restaurant's store page.

### 3. Add the item to the cart

On the store page, scroll to **"Most Liked Items From The Menu"** (or search
within the menu) to find the item. Two things to know:

- The item **card itself is not a link** — clicking the name/image does nothing.
  Click the **"Add"** button on the card to open the item modal.
- The modal shows size options ("Select Size"), optional removals, and a
  "Preferences (Optional)" note field. Pick the requested size (the walkthrough
  chose **Large**), set any customizations, then click **"Add to cart"** (the
  button shows the running price, e.g. "Add to cart $12.07").

### 4. Get to checkout

A cart preview may pop up with a **"Continue"** button — but on this site that
popup can disappear before you click it. Don't fight it. The reliable path is:
click the **cart icon** (top-right, shows the item count) → **"Go to Cart"** →
**"Checkout"**. That takes you to `/checkout`.

### 5. Set delivery details

At checkout, work top-down and verify each block:

- **Delivery vs Pickup**: make sure the **Delivery** tab is selected (not
  Pickup) unless the user asked for pickup.
- **Delivery Time**: choose what the user wants — Express, Standard, or
  **Schedule for later** (then pick a time if scheduling). The walkthrough
  selected "Schedule for later".
- **Drop-off instructions**: open the address block. The demo often pre-fills a
  verbose, auto-generated note (e.g. "Please ring the bell and drop off at the
  door…"). If the user wants something simple, **clear the existing text first**
  (select all → delete) and type the clean instruction, e.g. "Leave at the
  door", then Save. Don't leave stale boilerplate in place.
- **Address, phone, payment, tip**: confirm they match what the user expects.
  These are usually already set on the demo.

### 6. Place the order and confirm

Review the Order Summary (subtotal, fees, tax, total) so the total is sane, then
click **"Place Order"**. Wait a few seconds for the success confirmation, then
close the confirmation dialog.

Report back to the user what was ordered, the total, and the delivery timing.

## Notes and gotchas

- This is a **demo/eval site** — restaurant and item names don't have to match
  in real life (the walkthrough searched "Taco Bell" but ordered a "Classic
  Cheeseburger"). Order exactly what the user named; don't second-guess
  mismatches.
- Prefer reading the page (`read_page` / `get_page_text` / `find`) to confirm
  state before each click, rather than relying on fixed coordinates — the layout
  shifts as you scroll and as modals open.
- If a step fails 2–3 times (element not found, modal won't open, page won't
  advance), stop and tell the user what happened rather than retrying blindly.
- Placing the order is the one irreversible-feeling step. If anything about the
  cart, address, timing, or total is ambiguous, confirm with the user before
  clicking **Place Order**.