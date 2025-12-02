// API Base URL - use production backend when on GitHub Pages, otherwise local
const API_BASE = window.location.hostname.includes('github.io') 
  ? 'https://vancr-backend.azurewebsites.net' 
  : (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://localhost:8000' 
    : `http://${window.location.hostname}:8000`);
let products = [];
let productToDelete = null;
let productToEdit = null;

// Get user info
function getUser() {
  const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
  return userStr ? JSON.parse(userStr) : null;
}

// Load all products
async function loadProducts() {
  try {
    const response = await fetch(`${API_BASE}/api/products`);
    const data = await response.json();
    
    if (response.ok && data.ok) {
      products = data.products || [];
      renderProducts();
    } else {
      showStatus('Failed to load products', 'error');
    }
  } catch (error) {
    console.error('Error loading products:', error);
    showStatus('Network error. Could not load products.', 'error');
  }
}

// Render products table
function renderProducts() {
  const tbody = document.getElementById('productsBody');
  
  if (products.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="no-products">No products found. <a href="add-product.html">Add your first product</a></td></tr>';
    return;
  }
  
  tbody.innerHTML = products.map(product => `
    <tr>
      <td><img src="${product.imageUrl}" alt="Product" class="product-image-thumb" onerror="this.src='assets/images/placeholder.png'"></td>
      <td>₹${product.price.toFixed(2)}</td>
      <td>${product.categories.join(', ')}</td>
      <td>${product.ageGroups.join(', ')}</td>
      <td>${product.seasons.join(', ')}</td>
      <td>${product.occasions.join(', ')}</td>
      <td>
        <div class="action-buttons">
          <button class="btn-edit" onclick="openEditModal('${product.id}')">Edit</button>
          <button class="btn-delete" onclick="openDeleteModal('${product.id}')">Delete</button>
        </div>
      </td>
    </tr>
  `).join('');
}

// Show status message
function showStatus(message, type) {
  const statusDiv = document.getElementById('statusMessage');
  statusDiv.textContent = message;
  statusDiv.className = `status-message ${type}`;
  statusDiv.style.display = 'block';
  
  setTimeout(() => {
    statusDiv.style.display = 'none';
  }, 5000);
}

// Delete product functions
function openDeleteModal(productId) {
  productToDelete = productId;
  document.getElementById('deleteModal').classList.add('active');
}

function closeDeleteModal() {
  productToDelete = null;
  document.getElementById('deleteModal').classList.remove('active');
}

async function confirmDelete() {
  if (!productToDelete) return;
  
  const user = getUser();
  if (!user) {
    showStatus('Please login to delete products', 'error');
    closeDeleteModal();
    return;
  }
  
  try {
    const response = await fetch(`${API_BASE}/api/products/${productToDelete}`, {
      method: 'DELETE',
      headers: {
        'X-User-Id': user.userId
      }
    });
    
    const data = await response.json();
    
    if (response.ok && data.ok) {
      showStatus('Product deleted successfully', 'success');
      closeDeleteModal();
      loadProducts(); // Reload products
    } else {
      showStatus(data.error || 'Failed to delete product', 'error');
      closeDeleteModal();
    }
  } catch (error) {
    console.error('Error deleting product:', error);
    showStatus('Network error. Could not delete product.', 'error');
    closeDeleteModal();
  }
}

// Edit product functions
function openEditModal(productId) {
  productToEdit = products.find(p => p.id === productId);
  if (!productToEdit) return;
  
  // Set price
  document.getElementById('editPrice').value = productToEdit.price;
  
  // Set categories
  document.querySelectorAll('input[name="categories"]').forEach(checkbox => {
    checkbox.checked = productToEdit.categories.includes(checkbox.value);
  });
  
  // Set age groups
  document.querySelectorAll('input[name="ageGroups"]').forEach(checkbox => {
    checkbox.checked = productToEdit.ageGroups.includes(checkbox.value);
  });
  
  // Set seasons
  document.querySelectorAll('input[name="seasons"]').forEach(checkbox => {
    checkbox.checked = productToEdit.seasons.includes(checkbox.value);
  });
  
  // Set occasions
  document.querySelectorAll('input[name="occasions"]').forEach(checkbox => {
    checkbox.checked = productToEdit.occasions.includes(checkbox.value);
  });
  
  document.getElementById('editModal').classList.add('active');
}

function closeEditModal() {
  productToEdit = null;
  document.getElementById('editForm').reset();
  document.getElementById('editModal').classList.remove('active');
}

document.getElementById('editForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  if (!productToEdit) return;
  
  const user = getUser();
  if (!user) {
    showStatus('Please login to edit products', 'error');
    closeEditModal();
    return;
  }
  
  // Get form values
  const newPrice = parseFloat(document.getElementById('editPrice').value);
  
  const categories = Array.from(document.querySelectorAll('input[name="categories"]:checked'))
    .map(cb => cb.value);
  
  const ageGroups = Array.from(document.querySelectorAll('input[name="ageGroups"]:checked'))
    .map(cb => cb.value);
  
  const seasons = Array.from(document.querySelectorAll('input[name="seasons"]:checked'))
    .map(cb => cb.value);
  
  const occasions = Array.from(document.querySelectorAll('input[name="occasions"]:checked'))
    .map(cb => cb.value);
  
  // Validate at least one option is selected for each field
  if (categories.length === 0) {
    showStatus('Please select at least one category', 'error');
    return;
  }
  if (ageGroups.length === 0) {
    showStatus('Please select at least one age group', 'error');
    return;
  }
  if (seasons.length === 0) {
    showStatus('Please select at least one season', 'error');
    return;
  }
  if (occasions.length === 0) {
    showStatus('Please select at least one occasion', 'error');
    return;
  }
  
  try {
    const response = await fetch(`${API_BASE}/api/products/${productToEdit.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Id': user.userId
      },
      body: JSON.stringify({
        price: newPrice,
        categories: categories,
        ageGroups: ageGroups,
        seasons: seasons,
        occasions: occasions
      })
    });
    
    const data = await response.json();
    
    if (response.ok && data.ok) {
      showStatus('Product updated successfully', 'success');
      closeEditModal();
      loadProducts(); // Reload products
    } else {
      showStatus(data.error || 'Failed to update product', 'error');
    }
  } catch (error) {
    console.error('Error updating product:', error);
    showStatus('Network error. Could not update product.', 'error');
  }
});

// Load products on page load
loadProducts();
