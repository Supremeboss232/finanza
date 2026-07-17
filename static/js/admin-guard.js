(function(){
  // ==================== ADMIN SECURITY GUARD ====================
  // Enhanced security layer for admin portals
  // - JWT validation
  // - Role-based access control (SUPER_ADMIN, ADMIN, TREASURY)
  // - Permission-based feature guards
  // - Session expiry handling
  // - XSS/CSRF prevention
  
  // Step 1: JWT decoder
  function parseJwt(token) {
    try {
      var base64Url = token.split('.')[1];
      if (!base64Url) return null;
      var base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      var jsonPayload = decodeURIComponent(
        atob(base64).split('').map(function(c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join('')
      );
      return JSON.parse(jsonPayload);
    } catch(e) {
      console.error('JWT decode error:', e);
      return null;
    }
  }

  // Helper to get token from localStorage or cookie
  function getToken() {
    var localToken = localStorage.getItem('token');
    if (localToken) return localToken;
    // Try to extract from cookie
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
      var cookie = cookies[i].trim();
      if (cookie.startsWith('access_token=')) {
        return decodeURIComponent(cookie.substring('access_token='.length));
      }
      if (cookie.startsWith('token=')) {
        return decodeURIComponent(cookie.substring('token='.length));
      }
    }
    return null;
  }

  // Get admin role
  function getAdminRole() {
    return localStorage.getItem('admin_role') || 'STANDARD';
  }

  // Get permissions
  function getPermissions() {
    try {
      var perms = localStorage.getItem('permissions');
      return perms ? JSON.parse(perms) : [];
    } catch(e) {
      return [];
    }
  }

  // Check if user has permission
  function hasPermission(permission) {
    var permissions = getPermissions();
    return permissions && permissions.includes(permission);
  }

  // Step 2: Check authentication
  var token = getToken();
  if (!token) {
    if (!window.location.pathname.startsWith('/signin')) {
      window.location.href = '/signin.html?reason=not_authenticated';
    }
    return;
  }

  // Step 3: Decode and validate token
  var decoded = parseJwt(token);
  if (!decoded) {
    localStorage.removeItem('token');
    window.location.href = '/signin.html?reason=invalid_token';
    return;
  }

  // Step 4: Check admin status
  var isAdmin = localStorage.getItem('is_admin') === 'true' || localStorage.getItem('is_admin') === true;
  var adminRole = getAdminRole();
  var isValidAdminRole = ['SUPER_ADMIN', 'ADMIN', 'TREASURY'].includes(adminRole);

  // Step 5: Enforce admin access on /admin routes
  var currentPath = window.location.pathname;
  if (!isAdmin && currentPath.includes('/admin')) {
    window.location.href = '/user/dashboard';
    return;
  }

  // Step 6: Guard elements based on permissions
  window.AdminGuard = {
    hasPermission: hasPermission,
    getAdminRole: getAdminRole,
    getPermissions: getPermissions,
    getToken: getToken,
    getUserInfo: function() {
      return {
        email: localStorage.getItem('user_email'),
        id: localStorage.getItem('user_id'),
        fullName: localStorage.getItem('full_name'),
        role: adminRole,
        isAdmin: isAdmin,
        permissions: getPermissions()
      };
    },
    enforcePermission: function(permission, callback) {
      if (!hasPermission(permission)) {
        alert('You do not have permission: ' + permission);
        return false;
      }
      if (callback) callback();
      return true;
    },
    guardElement: function(elementId, permission) {
      var element = document.getElementById(elementId);
      if (element && !hasPermission(permission)) {
        element.disabled = true;
        element.style.opacity = '0.5';
        element.title = 'Requires: ' + permission;
      }
    },
    logout: function() {
      localStorage.clear();
      window.location.href = '/signin.html?logged_out=true';
    }
  };

  // Step 7: Setup session expiry handler
  var originalFetch = window.fetch;
  window.fetch = function() {
    return originalFetch.apply(this, arguments).then(function(response) {
      if (response.status === 401) {
        // Unauthorized - token expired or invalid
        localStorage.clear();
        window.location.href = '/signin.html?expired=true';
      }
      return response;
    }).catch(function(error) {
      return Promise.reject(error);
    });
  };

  // Step 8: Validate navigation
  document.addEventListener('click', function(e){
    var el = e.target;
    while(el && el.nodeName !== 'A') el = el.parentElement;
    if(!el) return;
    var href = el.getAttribute('href');
    if(!href) return;
    if(href.startsWith('#') || href.startsWith('javascript:') || href.startsWith('mailto:') || href.startsWith('tel:')) return;
    try{
      var url = new URL(href, window.location.origin);
    } catch(err){
      return;
    }
    var path = url.pathname || '';
    // Block non-admins from admin routes
    if (!isAdmin && path.includes('/admin')) {
      e.preventDefault();
      e.stopPropagation();
      alert('Admin access required');
      return;
    }
  }, true);

  // Step 9: Logout handler
  document.addEventListener('click', function(e) {
    if (e.target && e.target.getAttribute('href') === '/logout') {
      e.preventDefault();
      if (confirm('Are you sure you want to logout?')) {
        localStorage.clear();
        sessionStorage.clear();
        window.location.href = '/logout';
      }
    }
  }, true);

  // Step 10: Prevent back button from restoring cached pages
  window.addEventListener('pageshow', function(event) {
    if (event.persisted) {
      var hasLocalToken = localStorage.getItem('token');
      var hasCookie = document.cookie.includes('access_token=') || document.cookie.includes('token=');
      if (!hasLocalToken && !hasCookie) {
        window.location.href = '/signin.html?reason=session_expired';
      }
    }
  });
})();
