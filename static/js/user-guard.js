(function(){
  // USER REALM GUARD: JWT validation + realm-based access control
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
        return cookie.substring('access_token='.length);
      }
      if (cookie.startsWith('token=')) {
        return cookie.substring('token='.length);
      }
    }
    return null;
  }

  // Step 2: Check authentication
  var token = getToken();
  if (!token) {
    if (!window.location.pathname.startsWith('/signin') && !window.location.pathname.startsWith('/signup')) {
      window.location.href = '/signin';
    }
    return;
  }

  // Step 3: Decode and validate token
  var decoded = parseJwt(token);
  if (!decoded) {
    localStorage.removeItem('token');
    window.location.href = '/signin';
    return;
  }

  var isAdmin = decoded.is_admin === true || decoded.is_admin === 'true';

  // Step 4: Block regular users from admin realm
  var currentPath = window.location.pathname;
  if (!isAdmin && currentPath.includes('/user/admin')) {
    window.location.href = '/user/dashboard';
    return;
  }

  // Step 5: Validate clicks
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
    // Block cross-realm access
    if (!isAdmin && path.includes('/user/admin')) {
      e.preventDefault();
      e.stopPropagation();
      alert('Admin access required');
      return;
    }
    var allowed = ['/user','/api','/js','/css','/logout','/static'];
    var ok = allowed.some(function(p){ return path.startsWith(p); });
    if(!ok && (url.origin === window.location.origin || href.startsWith('/'))){
      e.preventDefault();
      e.stopPropagation();
      alert('Navigation not allowed');
    }
  }, true);

  // ==================================================
  // UNIVERSAL LOGOUT HANDLER
  // Securely clears all session state on logout
  // Applied to ALL pages that link to /logout
  // ==================================================
  document.addEventListener('click', function(e) {
    if (e.target && e.target.getAttribute('href') === '/logout') {
      e.preventDefault();
      if (confirm('Are you sure you want to logout?')) {
        // Clear all client-side storage
        localStorage.clear();
        sessionStorage.clear();
        // Navigate to logout endpoint (server clears cookie)
        window.location.href = '/logout';
      }
    }
  }, true);

  // Prevent back button from restoring cached authenticated pages
  window.addEventListener('pageshow', function(event) {
    if (event.persisted) {  // Page restored from back/forward cache
      // Check both localStorage and cookies for valid token
      var hasLocalToken = localStorage.getItem('token');
      var hasCookie = document.cookie.includes('access_token=') || document.cookie.includes('token=');
      if (!hasLocalToken && !hasCookie) {
        window.location.href = '/signin';
      }
    }
  });
})();
