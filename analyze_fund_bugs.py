"""
Code analysis: Look for bugs in the fund transfer code
"""
import ast
import inspect

print("Analyzing fund transfer code for potential bugs...")
print("=" * 70)

# Read the fund.py file
with open('routers/fund.py', 'r', encoding='utf-8', errors='ignore') as f:
    fund_code = f.read()

# Read the system_fund_service.py file
with open('system_fund_service.py', 'r', encoding='utf-8', errors='ignore') as f:
    service_code = f.read()

# Check for potential issues
print("\n[1] Checking fund.py for issues...")
print("-" * 70)

# Look for the fund_user_transfer function
if 'async def fund_user_transfer' in fund_code:
    print("✅ Found fund_user_transfer function")
    
    # Check if account_number is being set
    if 'account_number=' in fund_code:
        print("✅ account_number is being set when creating account")
    else:
        print("⚠️  account_number might not be set!")
    
    # Check if flush is being called after account creation
    if 'await db_session.flush()' in fund_code:
        print("✅ db_session.flush() is being called")
    else:
        print("⚠️  db_session.flush() might not be called!")
        
    # Check for the SystemFundService call
    if 'SystemFundService.fund_user_from_system' in fund_code:
        print("✅ SystemFundService.fund_user_from_system is being called")
    else:
        print("❌ SystemFundService.fund_user_from_system is NOT being called!")

print("\n[2] Checking system_fund_service.py for issues...")
print("-" * 70)

if 'async def fund_user_from_system' in service_code:
    print("✅ Found fund_user_from_system function")
    
    # Check for commit
    if 'await db.commit()' in service_code:
        print("✅ db.commit() is being called")
    else:
        print("⚠️  db.commit() might not be called!")
    
    # Check for exception handling
    if 'except Exception' in service_code:
        print("✅ Exception handling is in place")
    else:
        print("⚠️  No exception handling!")

print("\n[3] Looking for specific potential bugs...")
print("-" * 70)

# Check for the transaction creation with duplicate kwargs issue
if "Transaction(**transaction.model_dump(), user_id=user_id, account_id=account_id)" in service_code:
    print("❌ FOUND BUG: Duplicate kwargs in Transaction creation!")
else:
    print("✅ Transaction creation looks correct")

# Check for KYCSubmission.created_at issue
if ".created_at" in service_code:
    import re
    matches = re.findall(r'\.created_at', service_code)
    if matches:
        print(f"⚠️  Found {len(matches)} uses of .created_at in system_fund_service.py")
    else:
        print("✅ No .created_at references found")

# Check if description field is set for Ledger
if 'description=' in service_code:
    print("✅ Ledger description field is being set")
else:
    print("⚠️  Ledger description might not be set!")

# Check if status field is set for Ledger
if '"status=' in service_code or "'status=" in service_code:
    print("✅ Ledger status field is being set")
else:
    print("⚠️  Ledger status might not be set!")

print("\n[4] Checking model requirements...")
print("-" * 70)

# Read models to see what's required
with open('models.py', 'r', encoding='utf-8', errors='ignore') as f:
    models_code = f.read()

# Find Ledger class definition
if 'class Ledger(Base):' in models_code:
    print("✅ Ledger model found")
    
    # Check what fields are required (not nullable)
    ledger_section = models_code[models_code.find('class Ledger'):models_code.find('class Ledger') + 2000]
    
    required_fields = []
    for line in ledger_section.split('\n'):
        if 'nullable=False' in line and '=' in line:
            field_name = line.split('=')[0].strip()
            required_fields.append(field_name)
    
    print(f"   Required fields (nullable=False): {required_fields}")
    
    # Check if all required fields are being set
    missing = []
    for field in required_fields:
        if field not in service_code and field not in ['id']:
            missing.append(field)
    
    if missing:
        print(f"⚠️  These required fields might not be set: {missing}")
    else:
        print("✅ All required fields appear to be set")

print("\n" + "=" * 70)
print("Analysis complete!")
