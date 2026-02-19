#!/usr/bin/env python3
"""
AWS RDS Database Access Guide
Shows you how to connect and view your database data
"""

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                     AWS RDS DATABASE ACCESS GUIDE                          ║
║                           FINBANK DATABASE                                 ║
╚════════════════════════════════════════════════════════════════════════════╝

YOUR DATABASE DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Host:       finbank-db.cxo2eume87bz.eu-north-1.rds.amazonaws.com
  Port:       5432
  Database:   finbank
  Username:   postgres_admin
  Password:   Supposedbe5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  CURRENT ISSUE:
Your computer cannot reach the RDS instance. This is likely due to:
  • Security Group not allowing your IP
  • RDS not accessible from outside AWS VPC
  • Network timeout

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPTION 1: Use AWS RDS Query Editor (EASIEST - Recommended) ✨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Steps:
1. Go to AWS Console: https://console.aws.amazon.com/
2. Navigate to: RDS → Databases
3. Click on your database: "finbank-db"
4. Click on the "Query Editor" tab
5. Run SQL commands to see your data

Example queries to run:

-- See all tables
SELECT table_name FROM information_schema.tables WHERE table_schema='public';

-- View users
SELECT * FROM users LIMIT 10;

-- View accounts
SELECT * FROM accounts LIMIT 10;

-- View transactions
SELECT * FROM transactions LIMIT 10;

-- View deposits
SELECT * FROM deposits LIMIT 10;

-- View loans
SELECT * FROM loans LIMIT 10;

-- View KYC info
SELECT * FROM kyc_info LIMIT 10;

-- Get statistics
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'accounts', COUNT(*) FROM accounts
UNION ALL
SELECT 'transactions', COUNT(*) FROM transactions
UNION ALL
SELECT 'deposits', COUNT(*) FROM deposits
UNION ALL
SELECT 'loans', COUNT(*) FROM loans;

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPTION 2: Use DBeaver (Desktop Tool) 🖥️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Download: https://dbeaver.io/download/
2. Create new connection → PostgreSQL
3. Enter your connection details above
4. Test Connection → If it fails, continue to Option 3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPTION 3: Fix AWS Security Group (If you need external access) 🔒
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Go to AWS Console → RDS → Databases → finbank-db
2. Click "Connectivity & security" tab
3. Under "VPC security group rules", click the security group
4. Click "Edit inbound rules"
5. Add a new rule:
   • Type: PostgreSQL (5432)
   • Source: Your IP (or 0.0.0.0/0 for anywhere - NOT RECOMMENDED)
6. Click Save

To find your IP: https://www.whatismyipaddress.com/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPTION 4: Use EC2 Bastion Host (Most Secure) 🛡️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Launch an EC2 instance in the same VPC as your RDS
2. SSH into the EC2 instance
3. Install PostgreSQL client:
   sudo yum install postgresql -y

4. Connect to RDS from EC2:
   psql -h finbank-db.cxo2eume87bz.eu-north-1.rds.amazonaws.com \\
        -U postgres_admin \\
        -d finbank \\
        -p 5432

5. Enter password: Supposedbe5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR DATABASE TABLES & STRUCTURE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 TABLE: users
   Columns: id, full_name, email, hashed_password, account_number, 
           is_active, is_admin, created_at, updated_at

📋 TABLE: accounts
   Columns: id, account_number, balance, currency, owner_id, 
           created_at, updated_at

📋 TABLE: transactions
   Columns: id, user_id, account_id, amount, transaction_type, 
           status, description, reference_number, created_at, updated_at

📋 TABLE: deposits
   Columns: id, user_id, amount, currency, interest_rate, maturity_date,
           balance, status, withdrawal_amount, created_at

📋 TABLE: loans
   Columns: id, user_id, amount, interest_rate, duration_months,
           monthly_payment, status, disbursement_date, created_at

📋 TABLE: kyc_info
   Columns: id, user_id, document_type, document_number, status,
           submitted_at, approved_at

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ RECOMMENDED: Start with Option 1 (AWS RDS Query Editor)
   It requires no setup and no security group changes!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
