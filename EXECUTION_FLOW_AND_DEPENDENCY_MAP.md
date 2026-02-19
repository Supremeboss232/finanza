# 🎯 EXECUTION FLOW & DEPENDENCY MAP

**Created**: February 14, 2026  
**Purpose**: Visual guide to implementation sequence  
**Status**: Ready to execute

---

## EXECUTION DEPENDENCY CHAIN

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION READINESS FIX                      │
│                         (4-6 hours)                              │
└─────────────────────────────────────────────────────────────────┘

START
  │
  ├─────────────────────────────────────────────────────────────────
  │
  ├─► PHASE 1: Navigation Guards (1 hour) 🔴 P0 CRITICAL
  │   │
  │   ├─ Read: /static/js/user-guard.js
  │   ├─ Rewrite: Add JWT decode + is_admin check + realm validation
  │   ├─ Verify: Syntax correct
  │   │
  │   ├─ Read: /static/js/admin-guard.js
  │   ├─ Rewrite: Same improvements
  │   ├─ Verify: Syntax correct
  │   │
  │   └─ Test: Guard blocks cross-realm access ✓
  │
  │   BLOCKS IF FAILS: Everything else (users can escalate privilege)
  │   
  ├─────────────────────────────────────────────────────────────────
  │   PHASE 1 COMPLETE → Can proceed to Phase 2
  │
  │
  ├─► PHASE 2: Logout & Session Clearing (1 hour) 🔴 P0 CRITICAL
  │   │
  │   ├─ Update: /routers/private.py logout endpoint
  │   │  (Add token to blacklist placeholder comment)
  │   │
  │   ├─ Update: ALL 38 user pages logout handler
  │   │  └─ Clear localStorage, sessionStorage
  │   │  └─ Prevent back button restore
  │   │
  │   ├─ Update: ALL 22 admin pages logout handler
  │   │  └─ Same as user pages
  │   │
  │   └─ Test: Logout clears state + back button doesn't restore ✓
  │
  │   BLOCKS IF FAILS: Session security, logout doesn't work
  │   
  ├─────────────────────────────────────────────────────────────────
  │   PHASE 2 COMPLETE → Can proceed to Phase 3
  │
  │
  ├─► PHASE 3: Navbar Links & Routes (1.5 hours) 🟡 P1 HIGH
  │   │
  │   ├─ Fix Navbar Links (15 HTML files)
  │   │  ├─ Settings: /user/profile → /user/settings
  │   │  ├─ Notifications: /user/analytics → /user/notifications
  │   │  ├─ Transactions: /user/analytics → /user/transactions
  │   │  ├─ Security: /user/profile → /user/security
  │   │  ├─ Alerts: /user/analytics → /user/alerts
  │   │  └─ Contact: /user/dashboard → /user/support
  │   │
  │   ├─ Create Missing Routes in /routers/private.py (6 routes)
  │   │  ├─ GET /user/settings
  │   │  ├─ GET /user/notifications
  │   │  ├─ GET /user/transactions
  │   │  ├─ GET /user/security
  │   │  ├─ GET /user/alerts
  │   │  └─ GET /user/support
  │   │
  │   ├─ Verify: HTML files exist in /private/user/ (should exist)
  │   │
  │   └─ Test: All navbar links work, routes return 200 ✓
  │
  │   BLOCKS IF FAILS: UX broken, users navigate to wrong pages
  │   
  ├─────────────────────────────────────────────────────────────────
  │   PHASE 3 COMPLETE → Can proceed to Phase 4
  │
  │
  ├─► PHASE 4: Token Blacklist (1.5 hours) 🟢 P2 MEDIUM
  │   │
  │   ├─ Add Model to /models.py
  │   │  └─ TokenBlacklist(id, token, expires_at, created_at)
  │   │
  │   ├─ Update /routers/private.py logout
  │   │  └─ Insert expired token into blacklist table
  │   │
  │   ├─ Update /auth.py decode_access_token
  │   │  └─ Check if token in blacklist
  │   │  └─ Raise exception if blacklisted
  │   │
  │   └─ Test: Logout invalidates token, reuse fails ✓
  │
  │   BLOCKS IF FAILS: Token reuse after logout (security risk)
  │   
  ├─────────────────────────────────────────────────────────────────
  │   PHASE 4 COMPLETE → Can proceed to Phase 5
  │
  │
  ├─► PHASE 5: Backend Route Protection (0.75 hours) 🟡 P1 HIGH
  │   │
  │   ├─ Audit: /routers/private.py ALL routes
  │   │
  │   ├─ Add: Depends(get_current_user) to user routes
  │   │  └─ Find routes missing auth
  │   │  └─ Add dependency
  │   │
  │   ├─ Add: Depends(get_current_admin_user) to admin routes
  │   │  └─ Same process
  │   │
  │   └─ Test: Unauth access returns 401 ✓
  │
  │   BLOCKS IF FAILS: Unauthenticated users can access pages
  │   
  └─────────────────────────────────────────────────────────────────
      PHASE 5 COMPLETE → ALL FIXES DONE ✓

  ╔════════════════════════════════════════════════════════════════╗
  ║              🎉 PRODUCTION READY (Session 1)                  ║
  ║                                                                ║
  ║  Navigation Security: ✅ FIXED                                ║
  ║  Auth/Session: ✅ FIXED                                       ║
  ║  UX/Links: ✅ FIXED                                           ║
  ║  Token Security: ✅ FIXED                                     ║
  ║  Route Protection: ✅ FIXED                                   ║
  ║                                                                ║
  ║  REMAINING (Session 2):                                       ║
  ║  - Issue #1: Balance systems consolidation (4-6h)            ║
  ║  - Issue #3: System reserve account (1h)                      ║
  ║  - Issue #4: Account ownership validation (2-3h)             ║
  ║  - Issue #5: Read-only balance enforcement (2-3h)            ║
  ║                                                                ║
  ╚════════════════════════════════════════════════════════════════╝
```

---

## PARALLEL WORK OPPORTUNITIES

Some tasks in each phase can run in parallel (but we'll do them sequentially for clarity):

### Phase 1 Parallelizable
- ✓ Fix user-guard.js
- ✓ Fix admin-guard.js
(Not parallel because they follow same pattern)

### Phase 2 Parallelizable
- ✗ These are sequential (must fix endpoint before page handlers)

### Phase 3 Parallelizable
- ✓ Fix navbar links (15 pages) - Can do all at once with multi-replace
- ✓ Create routes - Independent, can do after links

### Phase 4 Parallelizable
- ✗ Must add model first, then update endpoints

### Phase 5 Parallelizable
- ✓ Multiple routes can be updated simultaneously

---

## DETAILED STEP-BY-STEP PHASE 1

### Step 1: Read Current user-guard.js
```
FILE: /static/js/user-guard.js
GOAL: Understand current implementation
ACTION: Read entire file to see what we're working with
```

### Step 2: Analyze Current Code
```
CURRENT: Simple path prefix check
MISSING: JWT decode, is_admin read, realm validation
ISSUE: Allows /admin paths for non-admins
```

### Step 3: Write New user-guard.js
```
NEW: 
1. Decode JWT token
2. Extract is_admin boolean
3. Validate page access based on role
4. Block cross-realm clicks
5. Error handling for invalid tokens
```

### Step 4: Verify Syntax
```
VALIDATE: JavaScript syntax is correct
CHECK: No undefined variables
VERIFY: All functions have return statements
```

### Step 5: Read Current admin-guard.js
```
Same process as Steps 1-4
Goal: Same improvements for admin realm
```

### Step 6: Write New admin-guard.js
```
Same pattern as user-guard.js
For admin users (is_admin=true)
```

### Step 7: Test Guards Work
```
Login as regular user:
- Try /user/admin/dashboard manually → Redirected ✓
- Try clicking /user/admin/* link → Blocked with alert ✓

Login as admin:
- Can access /user/* and /user/admin/* → Works ✓
```

---

## CRITICAL DECISION POINTS

### Decision 1: After Phase 1
**Question**: Do the guards work correctly?  
**If YES**: Proceed to Phase 2  
**If NO**: Debug and fix before continuing

### Decision 2: After Phase 2
**Question**: Do logout handlers clear all state?  
**If YES**: Proceed to Phase 3  
**If NO**: Debug and fix before continuing

### Decision 3: After Phase 3
**Question**: Do all navbar links work and no routes missing?  
**If YES**: Proceed to Phase 4  
**If NO**: Verify HTML files exist, routes correct before continuing

### Decision 4: After Phase 4
**Question**: Does token blacklist prevent reuse?  
**If YES**: Proceed to Phase 5  
**If NO**: Check database, auth decode flow

### Decision 5: After Phase 5
**Question**: Are all routes protected with proper auth?  
**If YES**: ALL DONE ✓  
**If NO**: Re-audit routes, add missing Depends

---

## ROLLBACK POINTS

If something breaks, we can rollback at any point:

```
ROLLBACK PHASE 1: Restore original guard files
ROLLBACK PHASE 2: Revert private.py logout + all page handlers
ROLLBACK PHASE 3: Revert navbar links + route handlers
ROLLBACK PHASE 4: Revert models.py, auth.py, private.py + drop table
ROLLBACK PHASE 5: Revert private.py auth dependencies
```

Each phase is independent enough to rollback without affecting others.

---

## TIME BREAKDOWN

```
PHASE 1: Read guards (5) + Write (40) + Verify (15) = 60 min
PHASE 2: Update endpoint (5) + Update 60 pages (50) + Test (5) = 60 min
PHASE 3: Fix links (20) + Create routes (20) + Verify (10) = 50 min
         (+ Verify HTML files: 10 min) = 60 min
PHASE 4: Add model (10) + Update endpoints (20) + Update auth (10) + Test (10) = 50 min
         (+ Database migration: 10 min) = 60 min total
PHASE 5: Audit (15) + Add dependencies (30) + Test (20) = 65 min
         (Round to 45 min with efficiency) = 45 min

TOTAL: 60 + 60 + 60 + 60 + 45 = 285 minutes = 4h 45min
```

---

## SUCCESS CRITERIA

### After All Phases Complete:

✅ **Security**: Guards prevent cross-realm access  
✅ **Session**: Logout clears all state, back button doesn't restore  
✅ **UX**: All navbar links work, users navigate correctly  
✅ **Token**: Logout invalidates tokens, replay prevented  
✅ **Auth**: All routes require proper authentication  

**Result**: Application is production-ready for navigation/session fixes

---

## WHO DOES WHAT

### Me (Assistant):
- Read files
- Analyze code
- Make changes
- Test changes
- Track progress
- Keep you informed

### You (User):
- Approve phase to start
- Review changes if needed
- Tell me to continue or stop
- Provide feedback

---

## READY?

When you say **"start phase 1"**, I will:

1. Read /static/js/user-guard.js
2. Analyze current implementation
3. Build new secure version
4. Replace the file
5. Read /static/js/admin-guard.js
6. Build new secure version
7. Replace the file
8. Mark Phase 1 complete

Then wait for your "proceed to phase 2" command.

Would you like me to **start phase 1**?

