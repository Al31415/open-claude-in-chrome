# zilloft — operating recipe

MUI/React real-estate clone (Zillow-style). No login needed; ignore sign-in prompts.

## Layout
- Home `/`: hero search input — "Search homes by address, neighborhood, city or ZIP code". City names and ZIP codes both work.
- Results `/homes`: filter bar on top (search input with current query + buttons: For Sale ▾, Price ▾, Beds & Baths ▾, Home Type ▾, Save search). Left half = map (static image — ignore it, it is not a working control). Right half = results panel: h1 title "<query> Real Estate & Homes For Sale", a "N results" count, "Sort:" control, then a two-column card list that scrolls independently.

## Search
- Click the search input, type city or ZIP, press Enter. A "Loading Homes Page…" alert shows; wait for it to clear before reading anything.
- Card street addresses often name other cities than the one searched — demo-data quirk. The searched location defines the result set; do NOT re-filter or second-guess membership by address text.

## Filters — general mechanics
- Each filter button opens a popover. **Nothing takes effect until you click the popover's Apply button.** Apply closes it, shows a "Searching for results…" alert, and re-queries — wait for the alert to clear, then re-read the count.
- While a popover is open, an invisible backdrop swallows every click outside it: the first such click only dismisses the popover (even if aimed at another filter button). Dismiss first, then click the next filter.
- After applying, the filter button labels re-render to encode state ("Up to $X", "$X - $Y", "N+ bd, N+ ba", "Home Type (1)"). Read them to verify the filter actually stuck.
- Reopening a filter button shows current selections for adjustment.

## Individual filters
- **For Sale** ▾: radio list For Sale / For Rent / Sold + Apply. Default is For Sale. Counts differ per status — make sure it matches the task.
- **Beds & Baths** ▾: chip rows — Bedrooms: Any 1+ 2+ 3+ 4+ 5+; Bathrooms: Any 1+ 1.5+ 2+ 3+ 4+. Chips mean **at least N**. A "Use exact match" toggle sits under the bedroom chips — click it when the task means exactly N. The button label still reads "N+ bd" even with exact match on, so verify exactness by reading card "N bds" text, not the label.
- **Price** ▾: "Price Range" with Minimum and Maximum dropdowns — these are **native `<select>` elements**. Fastest reliable route: set the select value directly (form-value set), using **raw integer values** (e.g. 250000); the option labels are display-formatted ("$250K", "$1.2M", "No Min/No Max") but values are plain numbers. Clicking through the native dropdown is screenshot-invisible and flaky. Note: the Maximum option list re-bases to start above the chosen Minimum. Then Apply.
- **Home Type** ▾: one checkbox per type (Houses, Townhomes, Multi-family, Condos/Co-ops, Lots/Land, Apartments, Manufactured) + "Deselect All". Unchecked = unfiltered; check only the wanted type(s), Apply; the button shows "(n)".

## Reading results
- The header "N results" count is authoritative and matches the card list exactly — for "how many" questions, apply filters, wait, read the count. Counting cards by scrolling is only a spot-check.
- Default order ("Homes for you") is NOT sorted by price; do not derive min/max from position. For cheapest/priciest: filter first to shrink the set, then read **every** card's price and compare. Page-text extraction of the "List of properties" beats screenshot-scrolling — all cards' price, address, and "N bds / N ba / N sqft — <type>" lines are present in text.
- Verify filtered semantics from card meta lines (beds/baths/price) on a few cards before trusting a count.
