#!/usr/bin/env python3
"""
EC2 Bastion Host Setup Guide for RDS Access
Complete instructions for connecting to your PostgreSQL RDS via EC2
"""

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║            EC2 BASTION HOST - DATABASE ACCESS SETUP GUIDE                  ║
║                    FINBANK RDS DATABASE                                    ║
╚════════════════════════════════════════════════════════════════════════════╝

YOUR RDS DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Host:       finbank-db.cxo2eume87bz.eu-north-1.rds.amazonaws.com
  Port:       5432
  Database:   finbank
  Username:   postgres_admin
  Password:   Supposedbe5
  Region:     eu-north-1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 1: LAUNCH AN EC2 INSTANCE (BASTION HOST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1.1 Go to AWS Console:
    https://console.aws.amazon.com/

1.2 Navigate to EC2 Dashboard:
    Services → EC2 → Instances

1.3 Click "Launch Instances" button

1.4 Configure Instance:
    • Name: finbank-bastion
    • AMI: Select "Amazon Linux 2" (free tier eligible)
    • Instance Type: t2.micro (free tier)
    • Key Pair: Create or select an existing key pair
      ⚠️  IMPORTANT: Download and save the .pem file securely!
    
1.5 Network Configuration:
    • VPC: Select the SAME VPC as your RDS instance
      (Usually "finbank-vpc" or similar)
    • Subnet: Any subnet in that VPC
    • Auto-assign Public IP: Enable
    • Security Group: Create new or select existing
      - Inbound Rule: SSH (22) from your IP
      - Allow traffic from your current IP

1.6 Launch the Instance
    - Wait for "State: Running"
    - Note the Public IPv4 address (e.g., 54.234.123.45)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2: CONNECT TO EC2 INSTANCE VIA SSH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2.1 On Windows (using PowerShell or Command Prompt):

    Navigate to where you saved your .pem file:
    cd C:\\Users\\YourUsername\\Downloads
    
    Connect using SSH:
    ssh -i your-key-pair.pem ec2-user@<PUBLIC_IPv4>
    
    Example:
    ssh -i finbank-key.pem ec2-user@54.234.123.45

2.2 On Mac/Linux:
    
    Make key file readable only by you:
    chmod 400 ~/Downloads/your-key-pair.pem
    
    Connect:
    ssh -i ~/Downloads/your-key-pair.pem ec2-user@<PUBLIC_IPv4>

2.3 If you see "Welcome to Amazon Linux" → SUCCESS! ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3: INSTALL POSTGRESQL CLIENT ON EC2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Once connected to EC2, run these commands:

3.1 Update package manager:
    sudo yum update -y

3.2 Install PostgreSQL client:
    sudo yum install postgresql -y

3.3 Verify installation:
    psql --version
    
    Output should show: psql (PostgreSQL) 12.x or higher ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4: CONNECT TO YOUR RDS DATABASE FROM EC2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Still on the EC2 instance, run:

4.1 Basic connection:
    psql -h finbank-db.cxo2eume87bz.eu-north-1.rds.amazonaws.com \\
         -U postgres_admin \\
         -d finbank \\
         -p 5432

4.2 Enter password when prompted:
    Password: Supposedbe5

4.3 You should see the PostgreSQL prompt:
    finbank=>

    If you see this → SUCCESS! ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5: VIEW YOUR DATABASE DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Now at the finbank=> prompt, you can run SQL queries:

5.1 List all tables:
    \\dt

5.2 View users:
    SELECT * FROM users LIMIT 5;

5.3 View accounts:
    SELECT * FROM accounts LIMIT 5;

5.4 View transactions:
    SELECT * FROM transactions LIMIT 5;

5.5 View deposits:
    SELECT * FROM deposits LIMIT 5;

5.6 View loans:
    SELECT * FROM loans LIMIT 5;

5.7 Get database statistics:
    SELECT 
      (SELECT COUNT(*) FROM users) as users,
      (SELECT COUNT(*) FROM accounts) as accounts,
      (SELECT COUNT(*) FROM transactions) as transactions,
      (SELECT COUNT(*) FROM deposits) as deposits,
      (SELECT COUNT(*) FROM loans) as loans;

5.8 Exit PostgreSQL:
    \\q

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ Problem: "Host key verification failed"
   Solution: 
   - Make sure the .pem file permissions are correct (chmod 400)
   - Use the correct username (ec2-user for Amazon Linux)

❌ Problem: "Could not resolve hostname"
   Solution:
   - Check Public IPv4 address is correct
   - EC2 instance is running (check status in AWS Console)

❌ Problem: "Connection refused" when connecting to RDS
   Solution:
   - Make sure EC2 is in the SAME VPC as RDS
   - Check RDS security group allows inbound from EC2 security group
   - Verify RDS endpoint is correct

❌ Problem: "psql: password authentication failed"
   Solution:
   - Verify password is: Supposedbe5
   - Make sure username is: postgres_admin
   - Check RDS wasn't modified

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUICK REFERENCE - SSH COMMAND
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Save this as a command you can run locally:

Windows (PowerShell):
ssh -i "C:\\Path\\To\\your-key.pem" ec2-user@<EC2_PUBLIC_IP>

Mac/Linux:
ssh -i ~/path/to/your-key.pem ec2-user@<EC2_PUBLIC_IP>

Replace:
- <EC2_PUBLIC_IP> with your actual EC2 public IPv4 address
- ~/path/to/your-key.pem with actual path to your .pem file

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADVANCED: SSH TUNNEL (Access RDS from your local computer)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If you want to connect to RDS from your Windows machine through EC2:

Create SSH tunnel (keep this open in a terminal):
ssh -i "C:\\Path\\To\\key.pem" \\
    -L 5432:finbank-db.cxo2eume87bz.eu-north-1.rds.amazonaws.com:5432 \\
    ec2-user@<EC2_PUBLIC_IP>

Then in another terminal, connect locally:
psql -h localhost -U postgres_admin -d finbank -p 5432

Password: Supposedbe5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ✅ Launch EC2 instance in same VPC as RDS
2. ✅ SSH into EC2
3. ✅ Install PostgreSQL client
4. ✅ Connect to RDS from EC2
5. ✅ Run SQL queries to view data

For support or questions about your database, run:
python DATABASE_ACCESS_GUIDE.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
