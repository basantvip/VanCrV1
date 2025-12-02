// Navigation menu authentication state management
(function() {
  function updateNavMenu() {
    const user = getUserFromStorage();
    const nav = document.querySelector('.nav');
    
    if (!nav) return;
    
    // Remove existing auth links
    const existingAuthLinks = nav.querySelectorAll('.auth-link');
    existingAuthLinks.forEach(link => link.remove());
    
    // Add Manage Products link for admin users (if not already present)
    const existingManageLink = nav.querySelector('a[href="manage-products.html"]');
    if (user && user.accessLevel === 'Admin' && !existingManageLink) {
      const manageProductsLink = document.createElement('a');
      manageProductsLink.href = 'manage-products.html';
      manageProductsLink.textContent = 'Manage Products';
      manageProductsLink.className = 'auth-link';
      
      // Insert after catalog link or before Contact Us
      const contactLink = nav.querySelector('a[href="contact.html"], a[href="contact.html"]');
      if (contactLink) {
        nav.insertBefore(manageProductsLink, contactLink);
      } else {
        nav.appendChild(manageProductsLink);
      }
    } else if (existingManageLink && (!user || user.accessLevel !== 'Admin')) {
      existingManageLink.remove();
    }
    
    if (user) {
      // User is logged in - show Logout
      const logoutLink = document.createElement('a');
      logoutLink.href = '#';
      logoutLink.className = 'auth-link logout-btn';
      logoutLink.textContent = 'Logout';
      logoutLink.addEventListener('click', (e) => {
        e.preventDefault();
        logout();
      });
      nav.appendChild(logoutLink);
      
      // Show user name (after logout button, as last item)
      const userInfo = document.createElement('span');
      userInfo.className = 'auth-link user-info';
      userInfo.textContent = `Hello, ${user.firstName}`;
      userInfo.style.color = '#2d7a3f';
      userInfo.style.fontWeight = '600';
      nav.appendChild(userInfo);
    } else {
      // User is logged out - show Login and Sign Up
      const loginLink = document.createElement('a');
      loginLink.href = 'login.html';
      loginLink.className = 'auth-link';
      loginLink.textContent = 'Login';
      nav.appendChild(loginLink);
      
      const signupLink = document.createElement('a');
      signupLink.href = 'signup.html';
      signupLink.className = 'auth-link';
      signupLink.textContent = 'Sign Up';
      nav.appendChild(signupLink);
    }
  }
  
  function getUserFromStorage() {
    // Check both localStorage and sessionStorage
    const userFromLocal = localStorage.getItem('user');
    const userFromSession = sessionStorage.getItem('user');
    
    const userStr = userFromLocal || userFromSession;
    if (userStr) {
      try {
        return JSON.parse(userStr);
      } catch (e) {
        return null;
      }
    }
    return null;
  }
  
  function logout() {
    // Clear user data
    localStorage.removeItem('user');
    sessionStorage.removeItem('user');
    
    // Redirect to home page
    window.location.href = 'index.html';
  }
  
  // Update menu on page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateNavMenu);
  } else {
    updateNavMenu();
  }
  
  // Make logout function globally available
  window.logoutUser = logout;
})();
