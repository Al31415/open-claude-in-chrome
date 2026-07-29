---
name: dashdish-order
description: >-
  Order food on DashDish (the evals-dashdish.vercel.app demo delivery app, a
  DoorDash-style site) from start to finish and place the order: open a
  restaurant, add a menu item at the requested quantity, choose pickup or
  delivery at checkout, and click Place Order. Use this skill whenever the user
  wants to order food on DashDish, "get me lunch/dinner", reorder a usual, or
  drive the DashDish site in the browser — even if they only name a restaurant
  and a dish without saying the word "order", and even when they want pickup
  rather than delivery. Drives the site with the Claude in Chrome browser tools,
  never host-level mouse/keyboard clicks.
compatibility: >-
  Requires the Claude in Chrome MCP tools (mcp__claude-in-chrome__*). Load them
  with ToolSearch before starting. Does not require host-level computer use.
---

# Order food on DashDish

This skill places a food order on the DashDish demo app at
`https://evals-dashdish.vercel.app`. It's a DoorDash-style site: open a
restaurant, open a menu item, set its quantity/options, add it to the cart, then
check out choosing **pickup or delivery**. The end state is a
"Processing your order…" dialog followed by an order confirmation — that
confirmation is the only proof the order actually went through, so always read
it back to the user and never claim success without it.

Everything happens inside the page, so drive it with the Claude in Chrome
browser tools. Do **not** use host-level mouse/keyboard control or screen
coordinates — operating on the page directly is faster, far more reliable, and
survives the window moving or resizing.

## Worked example (the demonstrated flow)

The reference workflow this skill was built from: order **3 Loaded Bacon Cheese
Fries** from **Man vs. Fries**, for **pickup**, and place the order. That
example threads through every step below (find restaurant → open item → set
quantity 3 → add to cart → checkout → switch to Pickup → Place Order). Treat it
as the canonical path; the inputs below let you retarget it to any restaurant,
item, quantity, and fulfillment method.

## Inputs

Gather these before starting. Only the first two are essential — ask for those
if missing, but pick sensible defaults for the rest rather than stalling.

- **Restaurant** (required): name to open, e.g. "Man vs. Fries", "Wingstop".
- **Menu item** (required): the dish, e.g. "Loaded Bacon Cheese Fries".
- **Quantity** (optional): default 1. In the worked example it's 3.
- **Fulfillment** (optional): `pickup` or `delivery`. The demo defaults to
  Delivery; the worked example uses Pickup. If the user says "pick up" / "I'll
  grab it" / "pickup", switch to the Pickup tab at checkout.
- **Size / options** (optional): e.g. Large, or removals like "No Salt". If the
  user doesn't care about size (as in the worked example — "the sizes don't
  matter"), leave whatever is pre-selected and don't ask.
- **Per-item notes** (optional): text for "Add Special Instructions".

The demo site pre-fills a saved account, address, and payment card. Do **not**
invent an address or payment detail — rely on the pre-filled data and change
only what the user explicitly asks for.

## Workflow

Load the browser tools first, in a single ToolSearch call:

```
ToolSearch "select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__find,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__form_input"
```

Then call `tabs_context_mcp` to see current tabs. Open a **new** tab for this
task with `tabs_create_mcp` rather than taking over one the user is using, unless
they point you at an existing DashDish tab.

### 1. Open the restaurant

Navigate the new tab to `https://evals-dashdish.vercel.app/`. The homepage lists
restaurants in rows like "Under $1 delivery fee" and "Best of lunch". If the
target restaurant is already visible on the homepage, just click its card — no
search needed (in the worked example, "Man vs. Fries" is right there on the
front page). Otherwise type the name into the "Search Dashdish" box and press
Enter, then click the matching result card.

If several match, prefer an exact name match; if the user was vague, pick the
closest and say which one you chose. If nothing matches, tell the user what the
catalog returned rather than substituting — the demo catalog is small.

### 2. Add the item at the right quantity

On the store page, find the requested dish with `find` or `get_page_text` rather
than scrolling blindly — it's often under "Most Liked Items From The Menu".

Open the item's customization modal by clicking its **"Add" button**. Note a
quirk seen in the demo: clicking the item's *image/card* may do nothing — the
"Add" button is what reliably opens the modal. If a click seems to have no
effect, fall back to the Add button.

In the modal:
- **Quantity**: use the `−` / `+` stepper at the bottom to reach the requested
  count (e.g. click `+` twice to go from 1 to 3). The "Add to cart" button shows
  the running total and updates as you step — e.g. it reads "Add to cart $20.00"
  at quantity 1 and "Add to cart $40.00" at quantity 2, so use it to confirm the
  quantity is right before adding.
- **Size**: select it only if the user specified one; otherwise leave the
  pre-selected default untouched.
- **Removals** (e.g. "No Salt") and **special instructions**: set only what the
  user asked for.
- Click **"Add to cart $X"**.

Confirm the cart counter in the header incremented (e.g. it now shows the item
count). For multiple different items, repeat this step for each before checkout.

### 3. Open the cart and go to checkout

Click the cart icon in the top-right header. A cart popover appears; click
**"Go to Cart"** (or "Continue") to open the cart sidebar, then click
**"Checkout"**. If a click misses (the demo's popover can be finicky), reopen the
cart and try the checkout button again, or navigate directly to
`https://evals-dashdish.vercel.app/checkout`.

### 4. Choose pickup or delivery

The checkout page has numbered sections: Account details, Shipping details (with
a **Delivery / Pickup** toggle and a map), and Payment details. The order summary
and a **Place Order** button sit in the right-hand panel.

- If the user wants **pickup**: click the **Pickup** tab in the Shipping details
  section. The panel switches to a pickup time (~20 min) and the restaurant's
  pickup address and phone — and the Delivery Fee in the summary drops to $0.
  Verify the tab now reads Pickup before placing.
- If the user wants **delivery** (the default): leave the Delivery tab selected.
  Optionally pick a delivery speed (Express / Standard / Schedule for later) and
  set delivery instructions ("Leave it at my door") only if the user asked.
- Leave the pre-filled account, address, and payment card as-is unless the user
  asked to change them.

### 5. Place the order

Click **Place Order** in the right-hand panel. A "Processing your order…" dialog
appears, then an order confirmation. Read the confirmation (and any order ID)
back to the user along with what was ordered, the fulfillment method, and the
total.

If the confirmation never appears, do **not** claim the order went through —
describe exactly where it stalled (which button, what the page showed) so the
user can decide what to do. Placing an order is a real action on the demo site.

## Notes and failure handling

- Demo/eval site with a small fixed catalog and pre-filled account data. Searches
  for real restaurants not in the catalog come up empty — report that rather than
  substituting something else.
- Prefer reading page text (`get_page_text` / `read_page` / `find`) to locate
  elements over guessing coordinates; the layout shifts as modals and popovers
  open.
- Never trigger native JS `alert`/`confirm` dialogs — they freeze the browser
  extension. Prefer reading page text over interacting with elements that pop
  modal browser dialogs.
- If a browser tool fails or the page doesn't respond after 2–3 tries, stop and
  tell the user what you attempted and what you saw, rather than retrying the
  same action or wandering the site.
- Don't reuse tab IDs from a previous session; if a tool reports an invalid tab,
  call `tabs_context_mcp` for fresh IDs.