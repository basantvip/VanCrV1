const API_BASE = 'http://localhost:8000';

document.getElementById('signupForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  // Clear previous errors
  clearErrors();
  
  // Get form values
  const firstName = document.getElementById('firstName').value.trim();
  const lastName = document.getElementById('lastName').value.trim();
  const email = document.getElementById('email').value.trim();
  const phone = document.getElementById('phone').value.trim();
  const password = document.getElementById('password').value;
  const confirmPassword = document.getElementById('confirmPassword').value;
  
  // Validate inputs
  if (!validateInputs(firstName, lastName, email, phone, password, confirmPassword)) {
    return;
  }
  
  // Disable submit button
  const submitBtn = document.getElementById('submitBtn');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Creating Account...';
  
  try {
    const response = await fetch(`${API_BASE}/api/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        firstName,
        lastName,
        email,
        phone: phone || null,
        password
      })
    });
    
    const data = await response.json();
    
    if (response.ok && data.ok) {
      showSuccess('Account created successfully! Redirecting to login...');
      setTimeout(() => {
        window.location.href = 'login.html';
      }, 2000);
    } else {
      showError(data.error || 'Failed to create account. Please try again.');
      submitBtn.disabled = false;
      submitBtn.textContent = 'Sign Up';
    }
  } catch (error) {
    console.error('Signup error:', error);
    showError('Network error. Please check your connection and try again.');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Sign Up';
  }
});

function validateInputs(firstName, lastName, email, phone, password, confirmPassword) {
  let isValid = true;
  
  // Validate first name
  if (!firstName || firstName.length < 2) {
    showFieldError('firstNameError', 'First name must be at least 2 characters');
    isValid = false;
  }
  
  // Validate last name
  if (!lastName || lastName.length < 2) {
    showFieldError('lastNameError', 'Last name must be at least 2 characters');
    isValid = false;
  }
  
  // Validate email
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    showFieldError('emailError', 'Please enter a valid email address');
    isValid = false;
  }
  
  // Validate phone (optional but must be valid if provided)
  if (phone) {
    const phoneRegex = /^\+?[\d\s\-()]+$/;
    if (!phoneRegex.test(phone)) {
      showFieldError('phoneError', 'Please enter a valid phone number');
      isValid = false;
    }
  }
  
  // Validate password strength
  const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
  if (!passwordRegex.test(password)) {
    showFieldError('passwordError', 'Password does not meet requirements');
    isValid = false;
  }
  
  // Validate password confirmation
  if (password !== confirmPassword) {
    showFieldError('confirmPasswordError', 'Passwords do not match');
    isValid = false;
  }
  
  return isValid;
}

function showFieldError(elementId, message) {
  const errorElement = document.getElementById(elementId);
  errorElement.textContent = message;
  errorElement.style.display = 'block';
}

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
