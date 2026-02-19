# ⚡ QUICK REFERENCE - PRIORITY CHECKLIST

**Status**: 🔴 BLOCKED - 5 Critical Issues  
**Estimated Fix Time**: 8-16 hours  
**Production Ready**: NO

---

## 🚨 CRITICAL - MUST FIX TODAY (P0)

### 1. **KYC Approval Broken** ⏱️ 30 minutes
- **What**: Admin approves KYC but User.kyc_status not updated
- **Where**: `routers/admin.py` → POST `/api/admin/kyc/{id}/approve`
- **Fix**: Add `user.kyc_status = "approved"` when approving
- **Impact**: HIGH - Approved users still can't transact

### 2. **System Reserve Account Missing** ⏱️ 1 hour  
- **What**: Funding operations fail (account not found)
- **Where**: `main.py` → `create_admin_user()` function
- **Fix**: Create account with `account_number="SYS-RESERVE-0001"`, `owner_id=1`
- **Impact**: HIGH - All admin funding broken

### 3. **Dual Balance Systems** ⏱️ 4-6 hours
- **What**: User shows $100, admin shows $500 (different calculations)
- **Where**: `balance_service.py` (OLD) vs `balance_service_ledger.py` (NEW)
- **Fix**: Remove OLD system, use NEW Ledger-based balance everywhere
- **Impact**: CRITICAL - Money disappears

### 4. **Account Balance Not Read-Only** ⏱️ 2-3 hours
- **What**: Manual balance updates in 3+ places, can drift
- **Where**: `system_fund_service.py:140`, `fund_ledger.py`, `deposits.py`
- **Fix**: Remove manual updates, calculate from ledger on read
- **Impact**: HIGH - Balance inconsistency

### 5. **Account Ownership Not Enforced** ⏱️ 2-3 hours
- **What**: User can access another user's loans/investments/cards
- **Where**: `routers/loans.py`, `routers/investments.py`, `routers/cards.py`
- **Fix**: Add ownership check: `if resource.user_id != current_user.id: 403`
- **Impact**: CRITICAL - Privilege escalation

---

## 📦 WHAT TO INSTALL

```bash
pip install boto3 aiohttp requests slowapi pytest pytest-asyncio
```

**Update `requirements.txt` with versions:**
```txt
boto3==1.28.85
aiohttp==3.9.1
requests==2.31.0
slowapi==0.1.9
pytest==7.4.0
pytest-asyncio==0.21.0
```

---

## ➕ WHAT TO ADD

| Component | File | Size | Time |
|-----------|------|------|------|
| Reconciliation Service | `reconciliation_service.py` | NEW | 3-4 hrs |
| Reversal Service | `reversal_service.py` | NEW | 4-5 hrs |
| Rate Limiter | `main.py` (middleware) | UPDATE | 1-2 hrs |
| Security Headers | `main.py` (middleware) | UPDATE | 1 hr |
| CLI Tools | `cli_commands.py` | NEW | 2-3 hrs |

---

## 🔧 WHAT TO FIX

| Issue | File(s) | Change | Lines |
|-------|---------|--------|-------|
| KYC Sync | `routers/admin.py` | Add `user.kyc_status = approved` | +3 |
| System Reserve | `main.py` | Create SYS-RESERVE-0001 account | +15 |
| Balance System | `routers/`, `transaction_gate.py` | Replace BalanceService calls | Varies |
| Account Real-Only | `system_fund_service.py`, `fund_ledger.py`, `deposits.py` | Remove balance assignment | -10 |
| Ownership Check | `routers/loans.py`, etc. | Add ownership validation | +5 per endpoint |

---

## ✅ DEPLOYMENT CHECKLIST

### Before Production Launch:

```
CRITICAL FIXES:
[ ] KYC approval syncs User.kyc_status
[ ] System Reserve Account auto-created at startup  
[ ] Balance consolidation complete (only Ledger used)
[ ] Account.balance read-only (calculated from ledger)
[ ] Account ownership enforced on all operations

DATA INTEGRITY:
[ ] Reconciliation job runs nightly
[ ] No balance mismatches in logs
[ ] All pending transactions reviewed

TESTING:
[ ] E2E: Register → Fund → Transfer → Approve KYC → Transact
[ ] Balance consistency check passes
[ ] Ownership tests pass (can't access other accounts)

MONITORING:
[ ] Alerts set for balance mismatches
[ ] KYC approval latency tracked
[ ] Transaction failure rate tracked
```

---

## 🗂️ FILE LOCATIONS (QUICK REFERENCE)

| Component | Location |
|-----------|----------|
| User Model | `models.py` (line 11) |
| Account Model | `models.py` (line 57) |
| Transaction Model | `models.py` (line 86) |
| Ledger Model | `models.py` (line 355) |
| Audit Log | `models.py` (line 401) |
| KYC Info | `models.py` (line 150) |
| Balance Service (OLD) | `balance_service.py` - DEPRECATE |
| Balance Service (NEW) | `balance_service_ledger.py` - USE THIS |
| Transaction Gate | `transaction_gate.py` |
| Auth Logic | `auth.py` |
| Admin Routes | `routers/admin.py` |
| KYC Routes | `routers/kyc.py` |
| App Startup | `main.py` |
| Database Config | `database.py` |
| Dependencies | `deps.py` |

---

## 🎯 TODAY'S FOCUS

### Must Complete:
1. Install missing dependencies
2. Fix KYC approval (Issue #2)
3. Create System Reserve Account (Issue #3)  
4. Update requirements.txt

### If Time Permits:
5. Start removing manual balance updates (Issue #4)
6. Begin consolidating balance systems (Issue #1)

---

## 🚀 NEXT STEPS

```
1. Run: pip install boto3 aiohttp requests slowapi
2. Fix Issue #2 (30 min): routers/admin.py KYC approval
3. Fix Issue #3 (1 hour): main.py System Reserve
4. Fix Issue #4 (2 hours): Remove balance assignments  
5. Fix Issue #1 (5 hours): Consolidate balance system
6. Fix Issue #5 (2 hours): Add ownership checks everywhere
7. TEST everything
8. READY FOR PRODUCTION
```

**Total**: 10-16 hours of focused work

---

## 🆘 TROUBLESHOOTING

| Problem | Check |
|---------|-------|
| KYC still blocking after approval | Is `User.kyc_status` updated? Check DB: `SELECT kyc_status FROM users WHERE id=X` |
| System Reserve account not found | Run: `SELECT * FROM accounts WHERE account_number='SYS-RESERVE-0001'` |
| Balance mismatch in logs | Run reconciliation: `python reconcile.py --verify-all` |
| User can access other's resources | Is ownership check in place? Search: `if resource.user_id != current_user.id` |

---

**See `CORE_ARCHITECTURE_ANALYSIS.md` for detailed implementation steps.**
