# DashDish — Operating Recipe

DoorDash-style demo delivery app at `https://evals-dashdish.vercel.app`. Small fixed catalog; account, address, and payment come pre-filled. A launch banner may appear — ignore it.

## Layout
- Home: "Search Dashdish" box, Delivery/Pickup toggle near the top (Delivery is default), a cuisine icon strip, then titled horizontal category rows of restaurant cards.
- A row renders only a handful of cards, with arrows and a "See all" link. Arrows often don't advance — never treat visible cards as the full set.
- Cards carry name, rating, distance, ETA, and a delivery-fee line.

## Counting / category questions
- Read the home page as text to see every row title. The same restaurant appears in multiple rows — answer only about the named row.
- Get full row membership via the row's "See all" link; read the whole category page as text. If a row has no "See all", confirm the arrows reveal nothing new; then the visible cards are the complete set.
- "Offers delivery": with the Delivery toggle selected, every card shown is delivery-capable (fee line + ETA), so the card count is the answer — don't open each store. Open a store only to resolve one ambiguous card; store pages have their own Delivery/Pickup toggle and time estimate.
- For rating/time/distance conditions, read values off card text and tally yourself.
- Never add to cart while counting.

## Ordering
- Open the restaurant via its homepage card if visible; otherwise search its name, press Enter, click the match under "Search Results". Don't scroll-browse.
- Item cards are NOT links — clicking the name or image does nothing. Click the card's "Add" button to open the customization modal.
- In the modal: pick a size under "Select Size" only if requested (otherwise keep the pre-selected default); set removals or the special-instructions note only if asked; set quantity with the −/+ stepper. The "Add to cart $X" button shows the running total and updates per step — use it to verify quantity before clicking.
- Confirm the header cart counter incremented. Repeat per distinct item before checkout.
- Cart → checkout: the cart popover's "Continue" can vanish before you click. Reliable path: cart icon (top-right) → "Go to Cart" → "Checkout". Fallback: navigate to `/checkout`.
- Checkout sections: Account, Shipping (Delivery/Pickup toggle + map), Payment; Order Summary and "Place Order" sit in the right panel.
- Pickup: click the Pickup tab — the panel switches to a pickup time and the store's address, and the summary's delivery fee drops to zero. Confirm the tab reads Pickup before placing.
- Delivery: set speed (Express / Standard / Schedule for later — pick a time when scheduling) only if asked. The drop-off instructions field pre-fills verbose boilerplate — select all, delete, type the user's note, Save. Never leave stale boilerplate.
- Keep pre-filled account/address/payment; verify rather than invent; change only what was requested.
- Click "Place Order" → "Processing your order…" → confirmation dialog. That confirmation is the only proof of success — read it (and any order ID) back; never claim success without it.

## Tool tactics
- Drive the page with browser tools (navigate, find, click, type) — never host-level screen coordinates; layout shifts as modals open.
- Text extraction (get_page_text / read_page) beats screenshots for row titles, card fields, counts, and totals. Re-read state before each click.
- If a click has no visible effect, re-read the page instead of re-clicking blind; for items, fall back to the "Add" button.
- Never trigger native alert/confirm dialogs — they freeze browser tooling.
- After 2–3 failed tries on one step, stop and report what you saw.
- Searches for names outside the catalog return nothing — report, don't substitute. Order exactly what was named even if restaurant and dish seem mismatched.
