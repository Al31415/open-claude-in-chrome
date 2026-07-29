# dashdish — operating recipe

MUI/React food-delivery clone. Pre-authenticated: account, address, payment are already filled. No login step ever.

## Layout
- Header: logo (click = back to home `/`), search box, location, Delivery|Pickup toggle, cart button (badge = item count).
- Home feed: category icon strip on top, then themed horizontal rows ("bands") of restaurant cards, each with a title heading.
- URLs are stable: home `/`, store pages `/store/<id>`, checkout `/checkout`. Reuse store URLs to revisit directly instead of re-scrolling the feed.

## Finding a restaurant
- Fastest: click header search, type the name, press Enter. A "Search Results for …" section renders in the feed; click the restaurant card (card click here navigates to the store page).
- Scrolling the feed for a name is slow and unreliable — search instead.

## Category rows (counting/membership questions)
- Rows overflow horizontally. Wheel-scroll left/right while hovering the row to pan it.
- "See all" buttons and the row arrow chevrons are dead — clicks silently do nothing. The row itself (panned fully) is the complete set.
- Prefer page-text extraction over screenshots here: clipped off-screen cards are already present in page text, so you can enumerate a row without panning.
- Card metadata (rating • distance • time, delivery-fee promo text) is ambiguous evidence for "offers delivery?". Confirm on the store page: it has its own Delivery|Pickup toggle in the header block (top right). Open each store, read the toggle, go back (logo or direct URL). Returning home resets scroll.

## Adding an item to the cart
- On a store page: a "Most Liked Items From The Menu" row sits above the full menu. Item cards and item names are NOT clickable — clicks silently do nothing. The only working control is the card's **Add** button; click it to open the item modal.
- Item modal mechanics:
  - "Select Size" radios: one size comes **pre-selected, and not necessarily the first/cheapest** — never assume the default. Click the required size row explicitly.
  - Quantity: use the − / + stepper (bottom left). One click per increment.
  - Optional: removal checkboxes and a "Preferences" instructions textarea.
  - Verify before committing: the **"Add to cart $X" button price = (base + size surcharge) × quantity**. If it doesn't match your intent, the size/qty is wrong.
  - Click "Add to cart $X".
- After adding, a small "Go to Cart / Continue" popover appears and **auto-vanishes within seconds** — don't chase it. Use the header cart button instead.

## Cart → checkout
- Click the header cart button → drawer lists "Your cart from <store>", line items as "<Item> - <Size>" with prices. Verify size/qty here. Click **Checkout** → `/checkout`.
- Checkout sections: 1. Account details; 2. Shipping details with a **Delivery | Pickup** tab pair. Switching to Pickup removes delivery-only sections and shows pickup time, store address, phone. Switching is instant, no confirmation.
- Delivery time: three option cards — Express (+fee), Standard (default), **Schedule for later**. Click the card to select; set a time inside it if the task specifies one.
- Delivery note: click the drop-off row (shows current option + instructions preview) → dialog with radios ("Hand it to me" / "Leave it at my door") and an instructions textarea that is **pre-filled with existing text**. To set a note: click textarea, select all (cmd+a), type the replacement, then **Save**. Don't append to the old text.
- Right sidebar: order summary, tip pills, item steppers, **Place Order $total**. Click it → "Processing your order…" → "Order Successful! Your order ID: ORD-…" dialog → Close.
- Re-read the page after every step that mutates state; nothing here confirms loudly.
