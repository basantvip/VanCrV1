// Simple storefront logic (no backend)
const DEFAULT_SHIPPING = 5.00;
const CURRENCY = 'USD';

// Embedded product data (fallback)
const EMBEDDED_PRODUCTS = [
  {
    "id": "p001",
    "name": "Classic Tee",
    "category": "Men",
    "price": 19.99,
    "description": "Soft 100% cotton crew neck t-shirt with a tailored fit.",
    "sizes": [
      "S",
      "M",
      "L",
      "XL"
    ],
    "colors": [
      "Black",
      "White",
      "Navy"
    ],
    "image": "assets/images/p001.png",
    "tags": [
      "t-shirt",
      "cotton",
      "basic"
    ],
    "stock": 120
  },
  {
    "id": "p002",
    "name": "Zip Hoodie",
    "category": "Men",
    "price": 49.0,
    "description": "Mid-weight fleece zip hoodie with kangaroo pockets.",
    "sizes": [
      "S",
      "M",
      "L",
      "XL"
    ],
    "colors": [
      "Heather Gray",
      "Black"
    ],
    "image": "assets/images/p002.png",
    "tags": [
      "hoodie",
      "fleece"
    ],
    "stock": 60
  },
  {
    "id": "p003",
    "name": "Slim Jeans",
    "category": "Men",
    "price": 69.5,
    "description": "Stretch denim slim-fit jeans with 5-pocket styling.",
    "sizes": [
      "28",
      "30",
      "32",
      "34",
      "36"
    ],
    "colors": [
      "Dark Wash",
      "Black"
    ],
    "image": "assets/images/p003.png",
    "tags": [
      "jeans",
      "denim"
    ],
    "stock": 75
  },
  {
    "id": "p004",
    "name": "Everyday Dress",
    "category": "Women",
    "price": 59.0,
    "description": "Knee-length jersey dress with a flattering A-line silhouette.",
    "sizes": [
      "XS",
      "S",
      "M",
      "L",
      "XL"
    ],
    "colors": [
      "Wine",
      "Black",
      "Teal"
    ],
    "image": "assets/images/p004.png",
    "tags": [
      "dress",
      "jersey"
    ],
    "stock": 50
  },
  {
    "id": "p005",
    "name": "Silk Blouse",
    "category": "Women",
    "price": 89.0,
    "description": "100% silk button-up blouse with a relaxed fit.",
    "sizes": [
      "XS",
      "S",
      "M",
      "L"
    ],
    "colors": [
      "Ivory",
      "Navy"
    ],
    "image": "assets/images/p005.png",
    "tags": [
      "blouse",
      "silk"
    ],
    "stock": 35
  },
  {
    "id": "p006",
    "name": "Performance Leggings",
    "category": "Women",
    "price": 39.0,
    "description": "High-waisted leggings with 4-way stretch and pocket.",
    "sizes": [
      "XS",
      "S",
      "M",
      "L",
      "XL"
    ],
    "colors": [
      "Black",
      "Forest"
    ],
    "image": "assets/images/p006.png",
    "tags": [
      "leggings",
      "athleisure"
    ],
    "stock": 90
  },
  {
    "id": "p007",
    "name": "Kids Graphic Tee",
    "category": "Kids",
    "price": 14.99,
    "description": "Soft tee with playful graphic print. Unisex fit.",
    "sizes": [
      "2T",
      "3T",
      "4T",
      "5",
      "6"
    ],
    "colors": [
      "Sky",
      "Sunshine",
      "Mint"
    ],
    "image": "assets/images/p007.png",
    "tags": [
      "kids",
      "tee"
    ],
    "stock": 110
  },
  {
    "id": "p008",
    "name": "Kids Zip Hoodie",
    "category": "Kids",
    "price": 34.0,
    "description": "Cozy fleece hoodie with easy zip for kids on the go.",
    "sizes": [
      "XS",
      "S",
      "M"
    ],
    "colors": [
      "Berry",
      "Navy"
    ],
    "image": "assets/images/p008.png",
    "tags": [
      "kids",
      "hoodie"
    ],
    "stock": 80
  },
  {
    "id": "p009",
    "name": "Baseball Cap",
    "category": "Accessories",
    "price": 22.0,
    "description": "Adjustable cotton twill cap with embroidered logo.",
    "sizes": [
      "OS"
    ],
    "colors": [
      "Khaki",
      "Black"
    ],
    "image": "assets/images/p009.png",
    "tags": [
      "hat",
      "cap"
    ],
    "stock": 140
  },
  {
    "id": "p010",
    "name": "Crew Socks (3-pack)",
    "category": "Accessories",
    "price": 12.0,
    "description": "Breathable cotton blend socks with cushioned sole.",
    "sizes": [
      "S",
      "M",
      "L"
    ],
    "colors": [
      "White",
      "Black"
    ],
    "image": "assets/images/p010.png",
    "tags": [
      "socks",
      "pack"
    ],
    "stock": 200
  },
  {
    "id": "p011",
    "name": "Puffer Jacket",
    "category": "Men",
    "price": 119.0,
    "description": "Lightweight insulated puffer for all-weather warmth.",
    "sizes": [
      "S",
      "M",
      "L",
      "XL"
    ],
    "colors": [
      "Olive",
      "Black"
    ],
    "image": "assets/images/p011.png",
    "tags": [
      "jacket",
      "outerwear"
    ],
    "stock": 40
  },
  {
    "id": "p012",
    "name": "Cardigan Sweater",
    "category": "Women",
    "price": 69.0,
    "description": "Merino blend cardigan with rib cuffs and pockets.",
    "sizes": [
      "XS",
      "S",
      "M",
      "L"
    ],
    "colors": [
      "Oat",
      "Charcoal"
    ],
    "image": "assets/images/p012.png",
    "tags": [
      "sweater",
      "cardigan"
    ],
    "stock": 55
  }
];

async function loadProducts() {
  // Try to fetch JSON; fallback to embedded
  try {
    const res = await fetch('data/products.json');
    if (!res.ok) throw new Error('Fetch failed');
    return await res.json();
  } catch (e) {
    console.warn('Using embedded products:', e.message);
    return EMBEDDED_PRODUCTS;
  }
}

function formatPrice(n) { return new Intl.NumberFormat('en-US', { style: 'currency', currency: CURRENCY }).format(n); }

function getCart() { return JSON.parse(localStorage.getItem('cart') || '[]'); }
function setCart(items) { localStorage.setItem('cart', JSON.stringify(items)); updateCartCount(); }
function updateCartCount() { const c = getCart().reduce((sum, i) => sum + i.qty, 0); const el = document.getElementById('cart-count'); if (el) el.textContent = c; }

function addToCart(item) {
  const cart = getCart();
  const key = `${item.id}-${item.color}-${item.size}`;
  const existing = cart.find(i => `${i.id}-${i.color}-${i.size}` === key);
  if (existing) existing.qty += item.qty; else cart.push(item);
  setCart(cart);
  alert('Added to cart');
}

function removeFromCart(index) {
  const cart = getCart();
  cart.splice(index, 1);
  setCart(cart);
  renderCart();
}

function updateQty(index, qty) {
  const cart = getCart();
  cart[index].qty = Math.max(1, qty);
  setCart(cart);
  renderCart();
}

function calcSubtotal(cart, products) {
  const map = Object.fromEntries(products.map(p => [p.id, p]));
  return cart.reduce((sum, i) => sum + (map[i.id]?.price || 0) * i.qty, 0);
}

// Page initializers
async function initIndex() {
  updateCartCount();
  const products = await loadProducts();
  const featured = [products[0], products[3], products[5], products[10]].filter(Boolean);
  const grid = document.getElementById('featured-grid');
  if (!grid) return;
  grid.innerHTML = featured.map(p => cardHTML(p)).join('');
}

function cardHTML(p) {
  return `<article class="card">
    <a href="product.html?id=${p.id}"><img loading="lazy" src="${p.image}" alt="${p.name}"></a>
    <div class="card-body">
      <div class="title"><a href="product.html?id=${p.id}">${p.name}</a></div>
      <div class="price">${formatPrice(p.price)}</div>
      <div class="meta">${p.category}</div>
    </div>
  </article>`;
}

async function initCatalog() {
  updateCartCount();
  const products = await loadProducts();
  const grid = document.getElementById('catalog-grid');
  const search = document.getElementById('search');
  const category = document.getElementById('category');
  const size = document.getElementById('size');
  const color = document.getElementById('color');
  const sort = document.getElementById('sort');

  function apply() {
    let list = [...products];
    const q = (search.value || '').toLowerCase();
    if (q) list = list.filter(p => p.name.toLowerCase().includes(q) || (p.tags || []).join(' ').toLowerCase().includes(q));
    if (category.value) list = list.filter(p => p.category === category.value);
    if (size.value) list = list.filter(p => (p.sizes || []).includes(size.value));
    if (color.value) list = list.filter(p => (p.colors || []).includes(color.value));
    switch (sort.value) {
      case 'price-asc': list.sort((a,b)=>a.price-b.price); break;
      case 'price-desc': list.sort((a,b)=>b.price-a.price); break;
      case 'name-asc': list.sort((a,b)=>a.name.localeCompare(b.name)); break;
      case 'name-desc': list.sort((a,b)=>b.name.localeCompare(a.name)); break;
    }
    grid.innerHTML = list.map(cardHTML).join('');
  }

  [search, category, size, color, sort].forEach(el => el && el.addEventListener('input', apply));
  apply();
}

function qs(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

async function initProduct() {
  updateCartCount();
  const products = await loadProducts();
  const id = qs('id');
  const p = products.find(x => x.id === id) || products[0];
  const el = document.getElementById('product-detail');
  if (!el) return;
  el.innerHTML = `
    <div>
      <img src="${p.image}" alt="${p.name}">
    </div>
    <div>
      <h1>${p.name}</h1>
      <div class="price">${formatPrice(p.price)}</div>
      <p>${p.description}</p>
      <div class="option-row"><label>Color</label>
        <select id="opt-color">${(p.colors||[]).map(c=>`<option>${c}</option>`).join('')}</select>
      </div>
      <div class="option-row"><label>Size</label>
        <select id="opt-size">${(p.sizes||[]).map(s=>`<option>${s}</option>`).join('')}</select>
      </div>
      <div class="option-row"><label>Qty</label>
        <input id="opt-qty" type="number" min="1" value="1" style="width:80px" />
      </div>
      <button class="btn primary" id="add-btn">Add to Cart</button>
    </div>`;
  document.getElementById('add-btn').addEventListener('click', () => {
    const item = { id: p.id, name: p.name, price: p.price, image: p.image,
                   color: document.getElementById('opt-color').value,
                   size: document.getElementById('opt-size').value,
                   qty: parseInt(document.getElementById('opt-qty').value) || 1 };
    addToCart(item);
  });
}

async function renderCart() {
  updateCartCount();
  const products = await loadProducts();
  const cart = getCart();
  const map = Object.fromEntries(products.map(p => [p.id, p]));
  const container = document.getElementById('cart-items');
  if (!container) return;
  container.innerHTML = cart.map((i, idx) => `
    <div class="cart-item">
      <img src="${map[i.id]?.image || ''}" alt="${i.name}">
      <div>
        <div><strong>${i.name}</strong></div>
        <div class="meta">${i.color} · ${i.size}</div>
        <div>${formatPrice(map[i.id]?.price || 0)}</div>
      </div>
      <div>
        <input type="number" min="1" value="${i.qty}" onchange="updateQty(${idx}, parseInt(this.value))" />
        <button class="btn" onclick="removeFromCart(${idx})">Remove</button>
      </div>
    </div>`).join('');

  const subtotal = calcSubtotal(cart, products);
  document.getElementById('subtotal').textContent = formatPrice(subtotal);
  document.getElementById('shipping').textContent = formatPrice(cart.length ? DEFAULT_SHIPPING : 0);
  document.getElementById('total').textContent = formatPrice(subtotal + (cart.length ? DEFAULT_SHIPPING : 0));
}

function download(filename, data) {
  const blob = new Blob([data], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function initCheckout() {
  updateCartCount();
  const form = document.getElementById('checkout-form');
  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    const products = await loadProducts();
    const cart = getCart();
    const subtotal = calcSubtotal(cart, products);
    const order = {
      id: 'ORD-' + Math.random().toString(36).slice(2, 8).toUpperCase(),
      createdAt: new Date().toISOString(),
      items: cart,
      pricing: { subtotal, shipping: cart.length ? DEFAULT_SHIPPING : 0, total: subtotal + (cart.length ? DEFAULT_SHIPPING : 0), currency: CURRENCY },
      customer: data
    };
    download(`${order.id}.json`, JSON.stringify(order, null, 2));
    alert('Order placed! (demo) A JSON file was downloaded.');
    localStorage.removeItem('cart');
    window.location.href = 'index.html';
  });
}

// Boot per page
window.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;
  if (path.endsWith('index.html') || path.endsWith('/')) initIndex();
  else if (path.endsWith('catalog.html')) initCatalog();
  else if (path.endsWith('product.html')) initProduct();
  else if (path.endsWith('cart.html')) renderCart();
  else if (path.endsWith('checkout.html')) initCheckout();
  else updateCartCount();
});
