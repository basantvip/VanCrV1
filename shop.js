// Simple shop script: loads data/products.json and shows products filtered by ?category=...
async function loadProducts() {
  try {
    const res = await fetch('data/products.json');
    const data = await res.json();
    return data;
  } catch (e) {
    console.error('Failed to load products', e);
    return [];
  }
}

function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

function renderSubcategories(mainCategory) {
  const subs = {
    'Girls': ['T-Shirts', 'Shirts', 'Blouses', 'Pants', 'Jeans', 'Shorts', 'Skirts', 'Dresses & Rompers', 'Jackets', 'Hoodies', 'Coats', 'Pajamas', 'Night Suits', 'Tracksuits', 'Leggings', 'Swimwear', 'School Uniforms'],
    'Boys': ['T-Shirts', 'Shirts', 'Pants', 'Jeans', 'Shorts', 'Outerwear', 'Pajamas', 'Tracksuits', 'Swimwear', 'School Uniforms'],
    'Baby': ['Bodysuits', 'Rompers', 'Sleepwear', 'Outerwear'],
    'Accessories': ['Hats & Caps', 'Socks & Tights', 'Scarves & Gloves', 'Hair Accessories'],
    'Footwear': ['Shoes', 'Sandals', 'Boots', 'Sneakers']
  };
  const container = document.getElementById('subcategories');
  container.innerHTML = '';
  const list = subs[mainCategory] || [];
  list.forEach(s => {
    const el = document.createElement('a');
    el.href = `#`;
    el.className = 'subcat';
    el.textContent = s;
    el.addEventListener('click', (ev) => {
      ev.preventDefault();
      filterBySubcategory(s);
    });
    container.appendChild(el);
  });
}

let PRODUCTS = [];
let CURRENT_MAIN = null;
let CURRENT_SUB = null;

function renderProducts(list) {
  const target = document.getElementById('products');
  if (!list || list.length === 0) {
    target.innerHTML = '<p>No products found.</p>';
    return;
  }
  target.innerHTML = '';
  list.forEach(p => {
    const card = document.createElement('div');
    card.className = 'product-card';
    card.innerHTML = `
      <img src="${p.image || 'assets/images/p001.png'}" alt="${p.name}" />
      <h4>${p.name}</h4>
      <p class="price">$${p.price}</p>
      <p class="desc">${p.description || ''}</p>
    `;
    target.appendChild(card);
  });
}

function applyFilters() {
  const ageChecks = Array.from(document.querySelectorAll('.filter-age:checked')).map(i => i.value);
  const seasonChecks = Array.from(document.querySelectorAll('.filter-season:checked')).map(i => i.value);
  const occChecks = Array.from(document.querySelectorAll('.filter-occasion:checked')).map(i => i.value);

  let filtered = PRODUCTS.slice();
  if (CURRENT_MAIN) filtered = filtered.filter(p => p.mainCategory === CURRENT_MAIN);
  if (CURRENT_SUB) filtered = filtered.filter(p => p.subCategory === CURRENT_SUB);
  if (ageChecks.length) filtered = filtered.filter(p => ageChecks.includes(p.ageGroup));
  if (seasonChecks.length) filtered = filtered.filter(p => seasonChecks.includes(p.season));
  if (occChecks.length) filtered = filtered.filter(p => occChecks.includes(p.occasion));

  renderProducts(filtered);
}

function filterBySubcategory(sub) {
  CURRENT_SUB = sub;
  applyFilters();
}

document.addEventListener('DOMContentLoaded', async () => {
  const main = getQueryParam('category') || 'All';
  CURRENT_MAIN = main === 'All' ? null : main;
  document.getElementById('current-category').textContent = main;
  renderSubcategories(main);

  PRODUCTS = await loadProducts();
  // Normalize some fields for backward compatibility
  PRODUCTS = PRODUCTS.map(p => ({
    ...p,
    mainCategory: p.mainCategory || p.category || 'Uncategorized',
    subCategory: p.subCategory || p.subcategory || p.type || ''
  }));

  renderProducts(PRODUCTS.filter(p => !CURRENT_MAIN || p.mainCategory === CURRENT_MAIN));

  document.querySelectorAll('.filter-age, .filter-season, .filter-occasion').forEach(el => {
    el.addEventListener('change', applyFilters);
  });
});
