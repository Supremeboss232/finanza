(function(){
  // USER REALM GUARD: JWT validation + realm-based access control
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
      return null;
    }
  }

  function getToken() {
    var localToken = localStorage.getItem('token') || localStorage.getItem('access_token');
    if (localToken && localToken !== 'null' && localToken !== 'undefined') return localToken;
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

  // Universal Logout Helper
  function executeCleanLogout(e) {
    if (e && e.preventDefault) e.preventDefault();
    if (window.FinanzaShell && typeof window.FinanzaShell.logout === 'function') {
      window.FinanzaShell.logout(e);
      return;
    }
    try {
      fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'include' }).catch(function(){});
      fetch('/user/logout', { method: 'GET', credentials: 'include' }).catch(function(){});
    } catch (err) {}
    localStorage.clear();
    sessionStorage.clear();
    document.cookie = 'access_token=; Max-Age=0; path=/';
    document.cookie = 'token=; Max-Age=0; path=/';
    window.location.href = '/logout';
  }

  window.handleLogout = executeCleanLogout;

  var token = getToken();
  // Note: HttpOnly cookie may not be visible to document.cookie; only redirect if localStorage has no session hints AND we are not authenticated
  if (token) {
    var decoded = parseJwt(token);
    if (!decoded && token !== 'cookie-session') {
      localStorage.removeItem('token');
      localStorage.removeItem('access_token');
    }
  }

  var isAdmin = localStorage.getItem('is_admin') === 'true' || localStorage.getItem('is_admin') === true;
  var currentPath = window.location.pathname;

  if (!isAdmin && currentPath.includes('/user/admin')) {
    window.location.href = '/user/dashboard';
    return;
  }

  // Intercept any click on a logout link or button (including nested <i> or <span> tags)
  document.addEventListener('click', function(e) {
    var link = e.target && e.target.closest ? e.target.closest('a[href="/logout"], a[href="/user/logout"], a[href="/auth/logout"], [data-action="logout"]') : null;
    if (link) {
      executeCleanLogout(e);
    }
  }, true);

  window.addEventListener('pageshow', function(event) {
    if (event.persisted) {
      var hasLocalToken = localStorage.getItem('token') || localStorage.getItem('access_token') || localStorage.getItem('user_email');
      var hasCookie = document.cookie.includes('access_token=') || document.cookie.includes('token=');
      if (!hasLocalToken && !hasCookie) {
        window.location.href = '/signin?logged_out=1';
      }
    }
  });
})();
