# DashDish — site behavior reference

DoorDash-style demo delivery app at `https://evals-dashdish.vercel.app`. Small fixed catalog; pre-filled demo account (address, phone, payment, tip). Menus can be incoherent with a restaurant's real-world brand — do exactly what the task names, never substitute.

## Page map
- **Home `/`**: harmless dismissible launch banner; "Search Dashdish" box; a **Delivery / Pickup toggle** near the top (Delivery is default); a cuisine icon strip (Ramen, Pizza, …); horizontal **category rows** ("Under $1 delivery fee", "Best of lunch", "The Infatuation's picks", "Light & fresh", "National favorites", …), each a band of restaurant cards with left/right arrows and a "See all" link.
- **Category page** (via "See all"): the complete membership of one row.
- **Store page** (via search result or card click): menu with a "Most Liked Items From The Menu" section; its own Delivery/Pickup toggle and delivery-time estimate confirm delivery capability.
- **`/checkout`**: directly navigable. Numbered sections — Account, Shipping (Delivery/Pickup tabs plus map), Payment — with the Order Summary and **Place Order** in a right-hand panel.

## Real vs. inert controls
- Row **arrows often don't advance** (inert when the row already fits); carousel scrolling is unreliable for seeing a row's contents.
- A row renders only ~5 cards but may contain more. **"See all" is the only reliable way to get a row's full set.** If a row has no "See all", the visible cards are the whole set (verify the arrows reveal nothing).
- On store pages the **item card/name/image is not a link** — clicking does nothing. Only the card's **"Add" button** opens the item modal.
- The post-add **cart popover is flaky** and can vanish before you click "Continue". Reliable path: cart icon (top-right, shows item count) → "Go to Cart" → "Checkout" — or navigate straight to `/checkout`.

## Finding restaurants
Search beats browsing: click "Search Dashdish", type the name, press Enter, click the match under "Search Results" (a visible home-page card also works). An empty search means it isn't in the catalog — report that.

## Category / counting questions
- With **Delivery** toggled (default), every card shown is delivery-capable and carries a delivery-fee line plus an ETA — "how many offer delivery" is simply that row's card count under the Delivery view. Open a store only to resolve an ambiguity (a card missing the delivery line).
- Cards carry name, rating, distance, ETA, and fee — enough for filters and comparisons from card text alone. The same restaurant appears in multiple rows; answer about the row asked about.
- Route: confirm toggle → page text for row titles → the row's "See all" → read full listing → count distinct names → apply the condition.

## Item modal and cart
The modal holds "Select Size" options, optional removals, a per-item notes field ("Preferences" / "Special Instructions"), and a −/+ quantity stepper. The **"Add to cart $X" button shows a live running total** updating with quantity and size — use it to verify quantity before clicking. Confirm the header cart count incremented after adding; repeat per distinct item. Touch only requested options.

## Checkout mechanics
- **Delivery vs Pickup tabs**: verify the right tab. Pickup swaps the panel to a pickup-time estimate plus the store's address/phone, and Delivery Fee drops to $0 — a good confirmation signal.
- **Delivery time**: Express / Standard / Schedule for later (scheduling opens a time picker).
- **Drop-off instructions**: pre-filled with verbose boilerplate. **Clear it (select-all → delete) before typing** the requested note, then Save.
- Account, address, payment, tip are pre-filled: verify, never invent, change only on request.
- Sanity-check the summary, click **Place Order** → "Processing your order…" → confirmation dialog. **The confirmation is the only proof of success** — read back the order/total; never claim success without it.

## Tool tactics
- Drive the page with in-page browser tools, never host-level coordinates; layout shifts as you scroll and modals open, so re-read state before each click.
- Page-text extraction beats screenshots for rows, menus, and counts — one call returns all card text.
- Load the browser toolset in one ToolSearch batch; fetch tab context first; fresh tab unless pointed at one; stale tab IDs error — refresh context.
- Never trigger native JS alert/confirm dialogs (they freeze the extension); don't fetch the site with curl.
- After 2–3 failed tries at a step, stop and report instead of retrying blindly.
