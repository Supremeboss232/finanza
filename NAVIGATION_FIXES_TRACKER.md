# 📋 NAVIGATION SECURITY FIXES - IMPLEMENTATION TRACKER

**Last Updated**: February 13, 2026  
**Status**: Ready for implementation  
**Estimated Time**: 4-6 hours  

---

## CRITICAL FIXES (P0) - Must Fix Before Deployment

### Fix #1: Navigation Guard - User Realm (`user-guard.js`)

**Current File**: `/static/js/user-guard.js`  
**Issue**: Allows navigation to /admin paths for non-admin users  
**Status**: ⏳ NOT STARTED  

**Current Code (Lines 1-20)**:
```javascript
(function(){
  var allowed = ['/user','/api','/js','/css','/lib','/img','/auth','/logout','/static','/admin'];
  // ↑ Problem: '/admin' in list allows /user/admin paths!
})();
```

**Fixed Code**:
```javascript
(function(){
  // 1. Check token
  const token = localStorage.getItem('token');
  if (!token) {
    window.location.href = '/signin';
    return;
  }

  // 2. Decode JWT to check role
  function parseJwt(token) {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64).split('').map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join('')
      );
      return JSON.parse(jsonPayload);
    } catch(e) {
      localStorage.removeItem('token');
      window.location.href = '/signin';
      return null;
    }
  }

  const decoded = parseJwt(token);
  if (!decoded) return;
  
  const isAdmin = decoded.is_admin || false;

  // 3. Validate current page access
  const path = window.location.pathname;
  
  // Regular users CANNOT access /user/admin/*
  if (!isAdmin && path.includes('/user/admin')) {
    window.location.href = '/user/dashboard';
    return;
  }

  // 4. Prevent cross-realm navigation on clicks
  document.addEventListener('click', function(e) {
    let el = e.target;
    while(el && el.nodeName !== 'A') el = el.parentElement;
    if(!el) return;
    
    let href = el.getAttribute('href');
    if(!href || href.startsWith('#') || href.startsWith('javascript:')) return;

    let clickPath = new URL(href, window.location.origin).pathname;
    
    // DENY: Regular user tries to access /user/admin/*
    if (!isAdmin && clickPath.includes('/user/admin')) {
      e.preventDefault();
      alert('Admin access required');
      return;
    }

    // Allow only safe paths
    const allowedPrefixes = ['/user', '/api', '/logout', '/static', '/js', '/css'];
    const isAllowed = allowedPrefixes.some(p => clickPath.startsWith(p));
    
    if (!isAllowed && (clickPath.startsWith('/') || href.includes(window.location.origin))) {
      e.preventDefault();
      alert('Navigation not allowed');
    }
  }, true);
})();
```

**Changes**:
- ✅ Decode JWT to check is_admin
- ✅ Block /user/admin/* for non-admin users
- ✅ Remove '/admin' from allowed list for regular users
- ✅ Add token validation on page load

**Testing**:
```
1. Login as regular user
2. Try to access /user/admin/dashboard manually
   → Should redirect to /user/dashboard
3. Try to click link to /user/admin/*
   → Should show alert "Admin access required"
```

---

### Fix #2: Navigation Guard - Admin Realm (`admin-guard.js`)

**Current File**: `/static/js/admin-guard.js`  
**Issue**: Allows navigation to /user paths for admin users (should allow, but with caution)  
**Status**: ⏳ NOT STARTED  

**Current Code (Lines 1-20)**:
```javascript
(function(){
  var allowed = ['/admin','/api','/js','/css','/lib','/img','/auth','/logout','/static','/user'];
  // ↑ '/user' is allowed (OK - admins should see user pages)
})();
```

**Fixed Code** (similar to user-guard.js):
```javascript
(function(){
  // 1. Check token
  const token = localStorage.getItem('token');
  if (!token) {
    window.location.href = '/signin';
    return;
  }

  // 2. Decode JWT
  function parseJwt(token) {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64).split('').map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join('')
      );
      return JSON.parse(jsonPayload);
    } catch(e) {
      localStorage.removeItem('token');
      window.location.href = '/signin';
      return null;
    }
  }

  const decoded = parseJwt(token);
  if (!decoded) return;
  
  const isAdmin = decoded.is_admin || false;

  // 3. REQUIRE admin role
  const path = window.location.pathname;
  if (!isAdmin && path.includes('/user/admin')) {
    window.location.href = '/user/dashboard';
    return;
  }

  // 4. Prevent unauthorized navigation
  document.addEventListener('click', function(e) {
    let el = e.target;
    while(el && el.nodeName !== 'A') el = el.parentElement;
    if(!el) return;
    
    let href = el.getAttribute('href');
    if(!href || href.startsWith('#') || href.startsWith('javascript:')) return;

    let clickPath = new URL(href, window.location.origin).pathname;
    
    // DENY: Non-admin tries to access /user/admin/*
    if (!isAdmin && clickPath.includes('/user/admin')) {
      e.preventDefault();
      alert('Admin access required');
      return;
    }

    // Allow all prefixes for admin
    const allowedPrefixes = ['/user', '/api', '/logout', '/static', '/js', '/css'];
    const isAllowed = allowedPrefixes.some(p => clickPath.startsWith(p));
    
    if (!isAllowed && (clickPath.startsWith('/') || href.includes(window.location.origin))) {
      e.preventDefault();
      alert('Navigation not allowed');
    }
  }, true);
})();
```

---

### Fix #3: Secure Logout Handler

**Files to update**:
- `/private/user/dashboard.html` (lines ~900)
- `/private/admin/admin_dashboard.html` (lines ~600)
- ALL other user/admin pages with logout link

**Current Code**:
```javascript
// Logout link handler - current (INSECURE)
document.addEventListener('click', function(e) {
    if (e.target && e.target.getAttribute('href') === '/logout') {
        if (confirm('Are you sure?')) {
            window.location.href = '/logout';  // Only clears cookie
        }
    }
});
```

**Fixed Code**:
```javascript
// Logout link handler - SECURE
document.addEventListener('click', function(e) {
    if (e.target && e.target.getAttribute('href') === '/logout') {
        if (confirm('Are you sure you want to logout?')) {
            // 1. Clear all client-side storage IMMEDIATELY
            localStorage.clear();
            sessionStorage.clear();
            
            // 2. Navigate to logout (server clears cookie)
            window.location.href = '/logout';
        }
    }
});

// 3. Prevent back button from restoring cached pages
window.addEventListener('pageshow', function(event) {
    if (event.persisted) {  // Page restored from back/forward cache
        if (!localStorage.getItem('token')) {
            window.location.href = '/signin';
        }
    }
});

// 4. Clear data before page unload  
window.addEventListener('beforeunload', function() {
    localStorage.removeItem('token');
});
```

**Impact**: Applied to ALL 38 user pages + ALL 22 admin pages

---

## HIGH PRIORITY FIXES (P1) - Fix This Week

### Fix #4: Navbar Link Corrections

**Affected Pages**: 15+ user pages with dropdown navbars  
**Status**: ⏳ NOT STARTED  

#### Dashboard.html (Line 49)

**Current**:
```html
<div class="dropdown-menu border-light m-0">
    <a href="/user/profile" class="dropdown-item">Profile</a>
    <a href="/user/profile" class="dropdown-item">Settings</a>         ❌ WRONG
    <a href="/user/analytics" class="dropdown-item">Notifications</a>  ❌ WRONG
    <a href="/user/analytics" class="dropdown-item">Transactions</a>   ❌ WRONG
    <a href="/user/profile" class="dropdown-item">Security</a>         ❌ WRONG
    <a href="/user/analytics" class="dropdown-item">Alerts</a>         ❌ WRONG
    <a href="/user/dashboard" class="dropdown-item">Contact/Support</a>❌ WRONG
    <a href="/logout" class="nav-link">Logout</a>                     ✓ CORRECT
</div>
```

**Fixed**:
```html
<div class="dropdown-menu border-light m-0">
    <a href="/user/profile" class="dropdown-item">Profile</a>
    <a href="/user/settings" class="dropdown-item">Settings</a>         ✓ FIXED
    <a href="/user/notifications" class="dropdown-item">Notifications</a>  ✓ FIXED
    <a href="/user/transactions" class="dropdown-item">Transactions</a>   ✓ FIXED
    <a href="/user/security" class="dropdown-item">Security</a>         ✓ FIXED
    <a href="/user/alerts" class="dropdown-item">Alerts</a>         ✓ FIXED
    <a href="/user/support" class="dropdown-item">Contact/Support</a>✓ FIXED
    <a href="/logout" class="nav-link">Logout</a>                     ✓ CORRECT
</div>
```

**Files with same issue** (copy-paste to all):
- transactions.html (Line 76)
- transfers.html (Line 65)
- purchases.html (Line 42)
- loans.html (Line 88)
- deposits.html (Line 105)
- cards.html (Line 120)
- investments.html (Line 95)
- bill_pay.html (Line 60)
- kyc_form.html (Line 45)
- accounts.html (Line 78)
- cryptocurrency.html (Line 112)
- money_management.html (Line 85)
- fund_transfer.html (Line 68)
- (... 2 more similar files)

**Search & Replace Pattern**:
```
OLD: <a href="/user/profile" class="dropdown-item">Settings</a>
NEW: <a href="/user/settings" class="dropdown-item">Settings</a>

OLD: <a href="/user/analytics" class="dropdown-item">Notifications</a>
NEW: <a href="/user/notifications" class="dropdown-item">Notifications</a>

OLD: <a href="/user/analytics" class="dropdown-item">Transactions</a>
NEW: <a href="/user/transactions" class="dropdown-item">Transactions</a>

OLD: <a href="/user/profile" class="dropdown-item">Security</a>
NEW: <a href="/user/security" class="dropdown-item">Security</a>

OLD: <a href="/user/analytics" class="dropdown-item">Alerts</a>
NEW: <a href="/user/alerts" class="dropdown-item">Alerts</a>

OLD: <a href="/user/dashboard" class="dropdown-item">Contact/Support</a>
NEW: <a href="/user/support" class="dropdown-item">Contact/Support</a>
```

---

### Fix #5: Create Missing Backend Routes

**File**: `/routers/private.py`  
**Status**: ⏳ NOT STARTED  

**Missing Routes** (add after existing routes):

```python
@private_router.get("/settings")
async def settings_page(request: Request, current_user: User = Depends(get_current_user)):
    """User settings page"""
    return templates.TemplateResponse("user/settings.html", {
        "request": request,
        "user": current_user
    })

@private_router.get("/notifications")
async def notifications_page(request: Request, current_user: User = Depends(get_current_user)):
    """User notifications page"""
    return templates.TemplateResponse("user/notifications.html", {
        "request": request,
        "user": current_user
    })

@private_router.get("/transactions")
async def transactions_page(request: Request, current_user: User = Depends(get_current_user)):
    """User transactions page"""
    return templates.TemplateResponse("user/transactions.html", {
        "request": request,
        "user": current_user
    })

@private_router.get("/security")
async def security_page(request: Request, current_user: User = Depends(get_current_user)):
    """User security settings page"""
    return templates.TemplateResponse("user/security.html", {
        "request": request,
        "user": current_user
    })

@private_router.get("/alerts")
async def alerts_page(request: Request, current_user: User = Depends(get_current_user)):
    """User alerts page"""
    return templates.TemplateResponse("user/alerts.html", {
        "request": request,
        "user": current_user
    })

@private_router.get("/support")
async def support_page(request: Request, current_user: User = Depends(get_current_user)):
    """User support/contact page"""
    return templates.TemplateResponse("user/support.html", {
        "request": request,
        "user": current_user
    })
```

**Note**: These are just route handlers. The HTML files should already exist at:
- `/private/user/settings.html`
- `/private/user/notifications.html`
- `/private/user/transactions.html`
- `/private/user/security.html`
- `/private/user/alerts.html`
- `/private/user/support.html`

---

## MEDIUM PRIORITY FIXES (P2) - Fix This Month

### Fix #6: Add Token Blacklist Table

**File**: `/models.py`  
**Status**: ⏳ NOT STARTED  

**Add Model**:

```python
class TokenBlacklist(Base):
    """Token blacklist for invalidated tokens after logout"""
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(500), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Update database.py**:
```python
# In create_db_and_tables() function
engine.echo = True
Base.metadata.create_all(bind=engine)
```

---

### Fix #7: Check Token Against Blacklist in Auth

**File**: `/auth.py`  
**Status**: ⏳ NOT STARTED  

**Update `decode_access_token`**:

```python
def decode_access_token(token: str):
    """Decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        
        # ⭐ NEW: Check if token is blacklisted
        # db_session = SessionLocal()
        # blacklisted = db_session.query(TokenBlacklist).filter(
        #     TokenBlacklist.token == token,
        #     TokenBlacklist.expires_at > datetime.utcnow()
        # ).first()
        # if blacklisted:
        #     raise credentials_exception
        
        return email
    except JWTError:
        raise credentials_exception
```

---

### Fix #8: Update Logout to Add Token to Blacklist

**File**: `/routers/private.py`  
**Status**: ⏳ NOT STARTED  

**Update logout endpoint** (lines 345-352):

```python
@private_router.get("/logout")
async def logout(request: Request, db: SessionDep):
    """Logs out user"""
    token = request.cookies.get("access_token")
    
    # Add token to blacklist if it exists
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            # Calculate expiry (token valid for 30 min, expire from now + buffer)
            expires_at = datetime.utcnow() + timedelta(hours=1)
            
            blacklist_entry = TokenBlacklist(
                token=token,
                expires_at=expires_at
            )
            db.add(blacklist_entry)
            db.commit()
        except:
            pass  # If token invalid/expired, just continue
    
    # Clear cookie
    response = RedirectResponse(url="/signin", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token", path="/")
    
    return response
```

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Critical Fixes (2-3 hours)

- [ ] Fix `/static/js/user-guard.js`
  - [ ] Add JWT decode function
  - [ ] Check is_admin in token
  - [ ] Block /user/admin/* for non-admins
  - [ ] Test with regular user

- [ ] Fix `/static/js/admin-guard.js`
  - [ ] Add JWT decode function
  - [ ] Check is_admin in token
  - [ ] Block /user/admin/* for non-admins (if not admin)
  - [ ] Test with admin user

- [ ] Add secure logout handler to ALL pages
  - [ ] Clear localStorage
  - [ ] Clear sessionStorage
  - [ ] Prevent back button restore
  - [ ] Test logout flow

**Testing**: 
```
1. Login as regular user → /user/dashboard
2. Try /user/admin/dashboard manually → Redirect to /user/dashboard
3. Click on /user/admin link in navbar → Alert "Admin access required"
4. Logout → localStorage cleared → Back button doesn't restore
5. Login as admin → /user/admin/dashboard
6. Can visit both /user/* and /user/admin/* pages
```

---

### Phase 2: Link Fixes (1 hour)

- [ ] Fix navbar links in all 15 pages
  - Settings: /user/profile → /user/settings
  - Notifications: /user/analytics → /user/notifications
  - Transactions: /user/analytics → /user/transactions
  - Security: /user/profile → /user/security
  - Alerts: /user/analytics → /user/alerts
  - Contact: /user/dashboard → /user/support

- [ ] Verify no duplicate links in dropdowns

**Testing**:
```
1. Login to user dashboard
2. Click each dropdown item
3. Verify lands on correct page
4. Verify navbar is present on new page (no redirect loop)
```

---

### Phase 3: Route Creation (1-1.5 hours)

- [ ] Add `/user/settings` route
- [ ] Add `/user/notifications` route
- [ ] Add `/user/transactions` route
- [ ] Add `/user/security` route
- [ ] Add `/user/alerts` route
- [ ] Add `/user/support` route

- [ ] Verify HTML files exist at `/private/user/`
- [ ] Test each route returns 200 with get_current_user dependency

**Testing**:
```
1. curl http://localhost:8000/user/settings (without token) → 401
2. curl http://localhost:8000/user/settings (with token) → 200 + HTML
3. Navigate via navbar → Each link works without redirect
```

---

### Phase 4: Token Blacklist (1-1.5 hours)

- [ ] Add TokenBlacklist model to models.py
- [ ] Create migration (alembic)
- [ ] Update logout to add token to blacklist
- [ ] Update decode_access_token to check blacklist
- [ ] Test logout prevents token reuse

**Testing**:
```
1. Get token by logging in
2. Use token to call API → Works
3. Logout (token added to blacklist)
4. Use same token to call API → 401 Unauthorized
```

---

## VERIFICATION STEPS

### After all fixes:

```bash
# 1. Verify guard scripts load
curl -s http://localhost:8000/static/js/user-guard.js | grep "parseJwt"
curl -s http://localhost:8000/static/js/admin-guard.js | grep "parseJwt"

# 2. Verify routes exist
curl -s http://localhost:8000/user/settings -H "Authorization: Bearer <token>"
curl -s http://localhost:8000/user/notifications -H "Authorization: Bearer <token>"
curl -s http://localhost:8000/user/transactions -H "Authorization: Bearer <token>"

# 3. Test navigation
# - Login as regular user
# - Click Settings → /user/settings (NOT /user/profile)
# - Click Notifications → /user/notifications (NOT /user/analytics)
# - Try to manually access /user/admin/dashboard → Redirect to /user/dashboard

# 4. Test logout
# - Login as user
# - Open DevTools → Application → localStorage → See "token"
# - Click logout → localStorage cleared
# - Click back button → Redirected to /signin (NOT cached page)

# 5. Test admin access
# - Login as admin
# - Can access both /user/* and /user/admin/* pages
# - Regular user accessing /user/admin/* → Blocked
```

---

## NOTES FOR IMPLEMENTATION

1. **All user pages** follow same navbar pattern - use find/replace carefully
2. **localStorage** must be cleared BEFORE page unload, not after
3. **Guards run on every page** - make sure JWT decode is efficient
4. **Back button** can restore pages from browser cache - use pageshow event
5. **Token blacklist** needs cleanup job to remove expired entries
6. **Admin users** should be able to navigate to /user/* pages (for support/debugging)

---

## ESTIMATED TIMELINE

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Fix navigation guards | 1-1.5 hrs | 🔴 P0 |
| 1 | Fix logout handler | 0.5 hrs | 🔴 P0 |
| 2 | Fix navbar links | 1 hr | 🟡 P1 |
| 3 | Create missing routes | 1-1.5 hrs | 🟡 P1 |
| 4 | Add token blacklist | 1-1.5 hrs | 🟢 P2 |
| | **TOTAL** | **4-6 hrs** | |

**Recommended**: Complete Phase 1 + 2 + 3 before next deployment (4-5 hours)

