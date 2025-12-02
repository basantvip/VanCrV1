// API Base URL - use production backend when on GitHub Pages, otherwise local
const API_BASE = window.location.hostname.includes('github.io') 
  ? 'https://vancr-backend.azurewebsites.net' 
  : (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://localhost:8000' 
    : `http://${window.location.hostname}:8000`);

document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  // Clear previous errors
  clearErrors();
  
  // Get form values
  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;
  const rememberMe = document.getElementById('rememberMe').checked;
  
  // Basic validation
  if (!email || !password) {
    showError('Please enter both email and password');
    return;
  }
  
  // Disable submit button
  const submitBtn = document.getElementById('submitBtn');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Logging in...';
  
  try {
    const response = await fetch(`${API_BASE}/api/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        email,
        password
      })
    });
    
    const data = await response.json();
    
    if (response.ok && data.ok) {
      // Store user info in localStorage/sessionStorage
      const storage = rememberMe ? localStorage : sessionStorage;
      storage.setItem('user', JSON.stringify({
        userId: data.userId,
        email: data.email,
        firstName: data.firstName,
        lastName: data.lastName,
        accessLevel: data.accessLevel
      }));
      
      showSuccess('Login successful! Redirecting...');
      
      // Redirect based on access level
      setTimeout(() => {
        if (data.accessLevel === 'Admin') {
          window.location.href = 'index.html';
        } else {
          window.location.href = 'catalog.html';
        }
      }, 1500);
    } else {
      showError(data.error || 'Invalid email or password');
      submitBtn.disabled = false;
      submitBtn.textContent = 'Login';
    }
  } catch (error) {
    console.error('Login error:', error);
    showError('Network error. Please check your connection and try again.');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Login';
  }
});

// Forgot password handler
document.getElementById('forgotPassword').addEventListener('click', (e) => {
  e.preventDefault();
  alert('Password reset functionality will be implemented soon. Please contact support.');
});

function showError(message) {
  const errorElement = document.getElementById('generalError');
  errorElement.textContent = message;
  errorElement.style.display = 'block';
}

function showSuccess(message) {
  const successElement = document.getElementById('successMessage');
  successElement.textContent = message;
  successElement.style.display = 'block';
}

function clearErrors() {
  const errorElements = document.querySelectorAll('.error-message, .success-message');
  errorElements.forEach(el => {
    el.style.display = 'none';
    el.textContent = '';
  });
}
