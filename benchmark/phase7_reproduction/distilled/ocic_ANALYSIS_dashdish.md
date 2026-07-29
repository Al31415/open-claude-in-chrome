# Dashdish (food delivery) — how the app actually behaves

React/MUI (Next.js) desktop app at `https://evals-dashdish.vercel.app`. All modals/drawers/popovers are `div[role=presentation]` appended to the end of `body`. A "Version 2.0 launches soon" banner is decorative.

## Routes
- `/` — homepage, and also the search-results view (searching does not change the URL).
- `/store/card.store:store:<numeric-id>` — store page; real deep links, store-card clicks navigate here.
- `/checkout` — checkout.
Cart/search state is client-side; the header cart badge persists across navigation. Return home via the logo (top-left) or by navigating to `/`.

## Homepage
Header: logo, search input (placeholder "Search Dashdish"), city label, a Delivery|Pickup toggle (unexercised), cart button whose badge shows total item count. Below: a left icon sidebar, a cuisine-icon strip, a filter-chip row (Delivery Fees, Offers, Pickup, Over 4.5, Under 30 min, Price — none exercised), promo banners, then the main content: a vertical stack of **category bands**.

A band = an `h6` category title + an inline row of restaurant cards + a "See all" button and arrows. **"See all" and the arrows are inert — clicking them does nothing.** The inline cards are the band's complete set; horizontal scrolling revealed nothing extra. The same store can appear in several bands; category membership means "under that band's heading" only. Card contents: image (accessible name "Image <Store>"), store name (`h6`), "rating • distance • time", and a delivery-fee promo line. **The fee line is a promo, not a delivery-availability signal.**

## Search (fastest route to a store)
Click the search input, type, press Enter. The homepage content is replaced in place by `Search Results for "<query>"` with matching store cards under band-style headings; click a card to open its store. This beats scrolling the bands. Reset by navigating to `/`.

## Store page
Info block: name (`h3`), ratings, fee promo, distance, time, "Open now • Closes at …", and a **Delivery|Pickup toggle at top right — its presence is the signal that the store supports both modes**. Per-store facts (this, hours, address, phone) live only here, not on cards. Items sit in a horizontally scrollable "Most Liked Items From The Menu" row. Item card: image, name, "$price • like% (count)", maybe a "#N Most Liked" badge. **Clicking the item name/card is inert** — click the card's "Add" button (overlaid on the image) to open the config modal. The same item name can exist at multiple stores with different prices — always enter via the required store. Reviews, address, phone are further down.

## Item modal
Top to bottom: "Select Size" radio rows ("<Size> • <cal> • +$X" surcharges); a "Remove from <item>" checkbox group; "Preferences (Optional)" with an "Add Special Instructions" textarea; a quantity stepper (−, count, +) bottom-left; "Add to cart $total" bottom-right; X to close. **A size arrives pre-selected, not necessarily the first/cheapest option — read the radios and click the required size explicitly.** The button total = qty × (base + surcharge); use it to verify size and quantity before committing. Set quantity by clicking + repeatedly. After "Add to cart", a confirmation popover (Go to Cart / Continue) **self-dismisses within seconds — don't chase it**; verify via the header cart badge instead.

## Cart and checkout
Click the header cart button → drawer "Your cart from <store>" listing lines as "<Item> - <Size>" with −/qty/+ steppers and a "Checkout $total" button → `/checkout`.

Checkout sections: 1. Account details (prefilled). 2. Shipping details — Delivery|Pickup tabs (Delivery default). Delivery shows three side-by-side time-option buttons (Express +fee / Standard / "Schedule for later — Choose a time"; clicking one selects it, and an order with "Schedule for later" selected and no explicit time succeeded), the saved address, and a drop-off preference (e.g. "Leave it at my door") with an instructions preview. **To edit the note, click the instructions text itself** → modal with a prefilled textarea (placeholder "Instructions for delivery"): select-all (cmd+a), type the replacement, click Save. Switching to Pickup swaps in ready-time, store address and phone, and changes the total (fees drop). 3. Payment details (prefilled). Right sidebar: "Order Summary (N items)" and "Place Order $total" → "Processing your order…" → "Order Successful! Your order ID: ORD-…" modal → Close.

## Tactics
- Prefer reading page text (band headings group the cards) over screenshot-scrolling when enumerating or counting cards; screenshots don't resolve prices reliably.
- Verify every mutation by its signal: header badge count, "Add to cart $X" total, cart-drawer line "<Item> - <Size>", "Order Summary (N items)".
- Per-store questions ("which stores in a category do X") require visiting each store page: collect the band's card list, then open each store URL in turn.
