#!/usr/bin/env python
"""Test Phase 4 router imports"""

routers_to_test = [
    ("fraud_detection_api", "fraud_detection_api"),
    ("blockchain_api", "blockchain_api"),
    ("reporting_api", "reporting_api"),  
    ("treasury_api", "treasury_api"),
    ("settlement_api", "settlement_api"),
    ("bill_pay_api", "bill_pay_api"),
    ("mobile_deposit_admin", "mobile_deposit_admin"),
]

for module_name, display_name in routers_to_test:
    try:
        module = __import__(f"routers.{module_name}", fromlist=["router"])
        router = getattr(module, "router")
        print(f"✓ {display_name}")
    except Exception as e:
        print(f"✗ {display_name}: {type(e).__name__}: {e}")
