# PowerShell script to upload updated files to EC2
# EC2 Instance: ec2-user@51.20.190.13
# Remote Path: /home/ec2-user/financial-services-website-template/

$EC2_HOST = "51.20.190.13"
$EC2_USER = "ec2-user"
$EC2_PATH = "/home/ec2-user/financial-services-website-template"
$KEY_PATH = "BankingBackendKey.pem"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Uploading Files to EC2 Instance" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "EC2 Instance: $EC2_USER@$EC2_HOST" -ForegroundColor Yellow
Write-Host "Remote Path: $EC2_PATH" -ForegroundColor Yellow
Write-Host ""

# Function to upload files
function Upload-Files {
    param(
        [string[]]$Files,
        [string]$Description
    )
    
    Write-Host "📤 $Description" -ForegroundColor Green
    foreach ($file in $Files) {
        if (Test-Path $file) {
            Write-Host "   ↳ $file" -ForegroundColor Gray
            & scp -i $KEY_PATH $file "$EC2_USER@$EC2_HOST:$EC2_PATH/" 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "      ✓ Uploaded" -ForegroundColor Green
            } else {
                Write-Host "      ✗ Failed" -ForegroundColor Red
            }
        } else {
            Write-Host "   ✗ Not found: $file" -ForegroundColor Red
        }
    }
    Write-Host ""
}

# Core Python files
$coreFiles = @(
    "config.py",
    "models.py",
    "main.py",
    "crud.py",
    "database.py",
    "auth.py",
    "auth_utils.py",
    "deps.py",
    "schemas.py"
)
Upload-Files $coreFiles "Core Python files"

# Setup and migration scripts
$setupFiles = @(
    "start_with_migrations.py",
    "start_with_tunnel.py",
    "ssh_tunnel.py",
    "rds_data_api.py",
    "fix_accounts_updated_at.py",
    "run_migration_add_columns.py"
)
Upload-Files $setupFiles "Setup and migration scripts"

# Configuration files
$configFiles = @(
    ".env",
    ".env.example",
    "alembic.ini"
)
Upload-Files $configFiles "Configuration files"

# Routers
$routerFiles = @(
    "routers/private.py",
    "routers/users.py",
    "routers/admin.py",
    "routers/user_pages.py",
    "routers/api_users.py",
    "routers/kyc.py",
    "routers/cards.py",
    "routers/deposits.py",
    "routers/loans.py",
    "routers/investments.py",
    "routers/realtime.py",
    "routers/account.py",
    "routers/financial_planning.py",
    "routers/insurance.py",
    "routers/notifications.py",
    "routers/settings.py"
)
Upload-Files $routerFiles "Router modules"

# Services
$serviceFiles = @(
    "admin_service.py",
    "admin_audit_service.py",
    "kyc_service.py",
    "ledger_service.py",
    "balance_service.py",
    "balance_service_ledger.py",
    "system_fund_service.py",
    "transaction_gate.py",
    "transaction_gate_ledger.py",
    "transaction_validator.py",
    "email_utils.py",
    "email_templates.py",
    "payment_utils.py",
    "ses_service.py",
    "sns_service.py"
)
Upload-Files $serviceFiles "Service modules"

# Utility files
$utilityFiles = @(
    "user_account_invariants.py",
    "account_id_enforcement.py",
    "ws_manager.py",
    "requirements.txt"
)
Upload-Files $utilityFiles "Utility files"

# Documentation
$docFiles = @(
    "SSH_TUNNEL_SETUP.md",
    "RDS_CREDENTIALS.md",
    "READ-ME.txt"
)
Upload-Files $docFiles "Documentation"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ Upload Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. SSH into EC2:" -ForegroundColor Yellow
Write-Host "   ssh -i BankingBackendKey.pem ec2-user@51.20.190.13" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Navigate to project:" -ForegroundColor Yellow
Write-Host "   cd /home/ec2-user/financial-services-website-template" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Pull latest from routers and static:" -ForegroundColor Yellow
Write-Host "   scp -r routers templates static css js lib img admin_static ec2-user@51.20.190.13:/home/ec2-user/financial-services-website-template/" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Start the application:" -ForegroundColor Yellow
Write-Host "   python3 start_with_migrations.py" -ForegroundColor Cyan
Write-Host ""
