// Shop script: loads products from backend API and shows products filtered by ?category=...
const API_BASE = 'http://localhost:8000';

async function loadProducts() {
  try {
    // Try loading from backend API first
    const res = await fetch(`${API_BASE}/api/products`);
    const data = await res.json();
    if (data.ok && data.products) {
      // Transform backend products to match expected format
      return data.products.map(p => {
        // Normalize age groups to remove descriptions like "(5-12y)"
        const normalizedAgeGroups = (p.ageGroups || []).map(ag => {
          if (ag.includes('(')) return ag.split('(')[0].trim();
          return ag;
        });
        
        return {
          id: p.id,
          name: p.itemName || `${p.categories && p.categories.length > 0 ? p.categories.join('/') : 'Item'} - ₹${p.price || 0}`,
          image: p.imageUrl,
          price: p.price || 0,
          description: p.description || '',
          mainCategory: p.categories && p.categories.length > 0 ? p.categories[0] : 'Uncategorized',
          categories: p.categories || [],
          subCategory: p.subCategory || '',
          ageGroup: normalizedAgeGroups.length > 0 ? normalizedAgeGroups[0] : '',
          ageGroups: normalizedAgeGroups,
          season: p.seasons && p.seasons.length > 0 ? p.seasons[0] : '',
          seasons: p.seasons || [],
          occasion: p.occasions && p.occasions.length > 0 ? p.occasions[0] : '',
          occasions: p.occasions || []
        };
      });
    }
    // Fallback to static JSON if API fails
    const fallbackRes = await fetch('data/products.json');
    return await fallbackRes.json();
  } catch (e) {
    console.error('Failed to load products', e);
    // Try fallback to static JSON
    try {
      const fallbackRes = await fetch('data/products.json');
      return await fallbackRes.json();
    } catch (fallbackError) {
      console.error('Fallback also failed', fallbackError);
      return [];
    }
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
    const displayName = p.name || (p.categories && p.categories.length > 0 ? p.categories.join('/') : 'Product');
    card.innerHTML = `
      <div class="product-image-container">
        <img src="${p.image || 'assets/images/p001.png'}" alt="${displayName}" class="product-image" />
        <div class="zoom-icon">🔍</div>
      </div>
      <p class="price" style="font-size: 1.4rem; font-weight: 700; color: #2d7a3f; margin: 8px 0;">₹${p.price || 0}</p>
      ${p.description ? `<p class="desc" style="font-size: 0.9rem; color: #666;">${p.description}</p>` : ''}
    `;
    
    // Add mouse move event for zoom effect
    const container = card.querySelector('.product-image-container');
    const img = card.querySelector('.product-image');
    
    container.addEventListener('mousemove', (e) => {
      const rect = container.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      img.style.transformOrigin = `${x}% ${y}%`;
      img.style.transform = 'scale(2.5)';
    });
    
    container.addEventListener('mouseleave', () => {
      img.style.transform = 'scale(1)';
      img.style.transformOrigin = 'center center';
    });
    
    target.appendChild(card);
  });
}

function applyFilters() {
  const ageChecks = Array.from(document.querySelectorAll('.filter-age:checked')).map(i => i.value);
  const seasonChecks = Array.from(document.querySelectorAll('.filter-season:checked')).map(i => i.value);
  const occChecks = Array.from(document.querySelectorAll('.filter-occasion:checked')).map(i => i.value);

  let filtered = PRODUCTS.slice();
  
  // Filter by main category
  if (CURRENT_MAIN) {
    filtered = filtered.filter(p => 
      p.mainCategory === CURRENT_MAIN || 
      (p.categories && p.categories.includes(CURRENT_MAIN))
    );
  }
  
  // Filter by subcategory
  if (CURRENT_SUB) {
    filtered = filtered.filter(p => p.subCategory === CURRENT_SUB);
  }
  
  // Filter by age groups (check if product has any of the selected age groups)
  if (ageChecks.length) {
    filtered = filtered.filter(p => {
      if (p.ageGroups && p.ageGroups.length > 0) {
        return p.ageGroups.some(age => ageChecks.includes(age));
      }
      return ageChecks.includes(p.ageGroup);
    });
  }
  
  // Filter by seasons
  if (seasonChecks.length) {
    filtered = filtered.filter(p => {
      if (p.seasons && p.seasons.length > 0) {
        return p.seasons.some(season => seasonChecks.includes(season));
      }
      return seasonChecks.includes(p.season);
    });
  }
  
  // Filter by occasions
  if (occChecks.length) {
    filtered = filtered.filter(p => {
      if (p.occasions && p.occasions.length > 0) {
        return p.occasions.some(occ => occChecks.includes(occ));
      }
      return occChecks.includes(p.occasion);
    });
  }

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
