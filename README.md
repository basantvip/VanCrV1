
# Thread & Co. - Starter Clothing Storefront (Static)

This is a fully client-side demo storefront you can open locally or host on any static web host.

## Features
- Product catalog with search, filters, and sorting
- Product detail with options (size, color) and Add to Cart
- Shopping cart (localStorage) with quantity updates and summary
- Demo checkout that downloads a JSON order (no real payments)
- Responsive layout with modern CSS

## Run locally
Option A: Just open `index.html` in a modern browser (Chrome/Edge/Firefox).
- Note: Some browsers restrict `fetch()` for `file://` pages; the app embeds product data as a fallback so it will still work.

Option B: Serve with a local static server for best results.
- Python 3: `python -m http.server 8080` then visit `http://localhost:8080/clothing_store_site/index.html`

## Customize
- Update `data/products.json` and corresponding images under `assets/images/`.
- Change branding in HTML headers or `styles.css`.
- Adjust currency and shipping in `app.js`.

## Deploy
- Host the folder on GitHub Pages, Azure Static Web Apps, Netlify, Vercel, etc.

## Limitations
- No backend or real payments included. Integrate Stripe/PayPal on top of this or convert to a framework.
