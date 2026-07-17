#!/usr/bin/env python3
"""
Analyze missing API endpoints from logs
"""

missing_endpoints = {
    "Settlement API": [
        "/api/v1/settlement/dashboard",
        "/api/v1/settlement/pending",
        "/api/v1/settlement/recent",
        "/api/v1/settlement/audit-log",
        "/api/v1/settlement/ach/metrics",
        "/api/v1/settlement/ach/files",
        "/api/v1/settlement/ach/entries",
        "/api/v1/settlement/ach/returns",
        "/api/v1/settlement/ach/nsf",
        "/api/v1/settlement/ach/contacts",
    ],
    "Loans API": [
        "/api/v1/loans/metrics",
        "/api/v1/loans",
        "/api/v1/loans/schedules",
        "/api/v1/loans/payments",
        "/api/v1/loans/compliance/metrics",
        "/api/v1/loans/delinquencies",
        "/api/v1/loans/collections",
        "/api/v1/loans/holds",
        "/api/v1/loans/forbearance",
        "/api/v1/loans/chargeoffs",
    ],
    "HMDA API": [
        "/api/v1/hmda/metrics",
        "/api/v1/hmda/applications",
        "/api/v1/hmda/applicants",
        "/api/v1/hmda/submissions",
    ],
    "Compliance API": [
        "/api/v1/compliance/flagged-transactions",  # 500 error
        "/api/v1/compliance/country-risks",
        "/api/v1/compliance/high-risk-users",
        "/api/v1/compliance/chart-data",
        "/api/v1/compliance/metrics",
    ],
    "Treasury API": [
        "/api/v1/treasury/portfolios",
        "/api/v1/treasury/strategies",
        "/api/v1/treasury/rebalancing",
        "/api/v1/treasury/liquidity",
    ],
    "Currency Exchange API": [
        "/api/v1/currency-exchange/metrics",
        "/api/v1/currency-exchange/chart-data",
        "/api/v1/currency-exchange/rates",
        "/api/v1/currency-exchange/transactions",
    ],
    "Static Files": [
        "/admin_static/js/admin-utils.js",
    ],
}

error_summary = {
    "404 Not Found": "Endpoint or resource doesn't exist",
    "422 Unprocessable Content": "Request validation error (missing/invalid query params)",
    "500 Internal Server Error": "Server error in endpoint processing",
}

print("\n" + "="*100)
print("MISSING API ENDPOINTS ANALYSIS")
print("="*100 + "\n")

total_missing = 0
for category, endpoints in missing_endpoints.items():
    count = len(endpoints)
    total_missing += count
    print(f"\n📍 {category}: {count} endpoints")
    print("-" * 100)
    for ep in endpoints:
        print(f"   ❌ {ep}")

print("\n" + "="*100)
print(f"TOTAL MISSING ENDPOINTS: {total_missing}")
print("="*100)

print("\n" + "="*100)
print("ERROR TYPE SUMMARY")
print("="*100)
for error_type, description in error_summary.items():
    print(f"\n{error_type}")
    print(f"  └─ {description}")

print("\n" + "="*100)
print("RECOMMENDATIONS")
print("="*100)
print("""
1. Settlement endpoints:
   - Check if settlement_service.py has route definitions
   - May need to register settlement router in main.py
   - ACH-specific endpoints may need separate module

2. Loans endpoints:
   - Check if lending_servicing_service.py / loans.py has route definitions
   - Verify query parameter validation (422 errors suggest missing 'limit' param)
   - May need query parameter defaults

3. HMDA endpoints:
   - Check if hmda_compliance_service.py has route definitions
   - Register HMDA router in main.py

4. Compliance endpoints:
   - Check if compliance_aml_service.py has route definitions
   - /api/v1/compliance/flagged-transactions returns 500 (needs debugging)

5. Treasury endpoints:
   - Check if treasury_service.py has route definitions
   - /api/v1/treasury/dashboard returns 200 OK (good), but sub-endpoints missing

6. Currency Exchange endpoints:
   - Check if currency_exchange_service.py has route definitions

7. Static files:
   - Ensure /admin_static/js/admin-utils.js exists
   - Check FastAPI static files mounting in main.py

""")
