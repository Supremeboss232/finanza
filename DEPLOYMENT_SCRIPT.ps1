# Admin Panel Deployment Script
# Deploys all admin files to production server via SSH/SCP
# Usage: .\DEPLOYMENT_SCRIPT.ps1

param(
    [string]$EC2_HOST = "51.20.190.13",
    [string]$EC2_USER = "ec2-user",
    [string]$EC2_KEY = "BankingBackendKey.pem",
    [string]$REMOTE_PATH = "/home/ec2-user/app",
    [switch]$DryRun = $false
)

# Colors for output
$GREEN = "`e[32m"
$RED = "`e[31m"
$YELLOW = "`e[33m"
$BLUE = "`e[34m"
$RESET = "`e[0m"

Write-Host "${BLUE}╔═══════════════════════════════════════════╗${RESET}"
Write-Host "${BLUE}║  Admin Panel Production Deployment Script  ║${RESET}"
Write-Host "${BLUE}╚═══════════════════════════════════════════╝${RESET}`n"

# Check if SSH key exists
if (-not (Test-Path $EC2_KEY)) {
    Write-Host "${RED}✗ Error: SSH key not found at $EC2_KEY${RESET}"
    exit 1
}

Write-Host "${GREEN}✓ SSH key found: $EC2_KEY${RESET}`n"

# Files to deploy
$FILES_TO_DEPLOY = @(
    # Admin HTML Pages
    "private/admin/admin_navbar.html",
    "private/admin/admin_dashboard_hub.html",
    "private/admin/admin_users.html",
    "private/admin/admin_transactions.html",
    "private/admin/admin_kyc.html",
    "private/admin/admin_lending.html",
    "private/admin/admin_hmda.html",
    "private/admin/admin_lending_compliance.html",
    "private/admin/admin_ach_management.html",
    "private/admin/admin_settlement.html",
    "private/admin/admin_webhooks.html",
    "private/admin/admin_fraud_detection.html",
    "private/admin/admin_reporting.html",
    "private/admin/admin_mobile_deposit.html",
    "private/admin/admin_bill_pay.html",
    
    # Admin Static Files
    "admin_static/js/admin-utils.js",
    "admin_static/css/",
    "admin_static/img/",
    "admin_static/lib/",
    "admin_static/scss/",
    
    # Documentation Files
    "ADMIN_DOCUMENTATION_INDEX.md",
    "ADMIN_PANEL_COMPLETION_REPORT.md",
    "DEPLOYMENT_VERIFICATION_CHECKLIST.md",
    "ADMIN_UPGRADE_DELIVERY.md",
    "ADMIN_QUICK_REFERENCE.md",
    "ADMIN_UPGRADE_FINAL_SUMMARY.md"
)

# Count files
$FILE_COUNT = $FILES_TO_DEPLOY.Count
Write-Host "${YELLOW}Files to deploy: $FILE_COUNT${RESET}`n"

# Display deployment plan
Write-Host "${BLUE}Deployment Plan:${RESET}"
Write-Host "  Source:       Current directory"
Write-Host "  Destination:  $EC2_USER@$EC2_HOST:$REMOTE_PATH"
Write-Host "  SSH Key:      $EC2_KEY"
Write-Host "  Dry Run:      $($DryRun ? 'YES' : 'NO')`n"

# Verify connectivity
Write-Host "${BLUE}Testing SSH connection...${RESET}"
$ssh_test = ssh -i $EC2_KEY "$EC2_USER@$EC2_HOST" "echo 'SSH connection successful'" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "${RED}✗ SSH connection failed${RESET}"
    Write-Host "Error: $ssh_test"
    exit 1
}
Write-Host "${GREEN}✓ SSH connection successful${RESET}`n"

# Create remote directories
Write-Host "${BLUE}Creating remote directories...${RESET}"
$DIRS = @(
    "$REMOTE_PATH/private/admin",
    "$REMOTE_PATH/admin_static/js",
    "$REMOTE_PATH/admin_static/css",
    "$REMOTE_PATH/admin_static/img",
    "$REMOTE_PATH/admin_static/lib",
    "$REMOTE_PATH/admin_static/scss"
)

foreach ($dir in $DIRS) {
    if ($DryRun) {
        Write-Host "  [DRY RUN] mkdir -p $dir"
    } else {
        ssh -i $EC2_KEY "$EC2_USER@$EC2_HOST" "mkdir -p $dir"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "${GREEN}✓ Created: $dir${RESET}"
        } else {
            Write-Host "${RED}✗ Failed to create: $dir${RESET}"
        }
    }
}
Write-Host ""

# Deploy files
Write-Host "${BLUE}Deploying files...${RESET}`n"
$DEPLOYED = 0
$FAILED = 0

foreach ($file in $FILES_TO_DEPLOY) {
    if (Test-Path $file) {
        $REMOTE_FILE = "$REMOTE_PATH/$file"
        
        if ($DryRun) {
            Write-Host "  [DRY RUN] scp -i $EC2_KEY -r '$file' '$EC2_USER@$EC2_HOST:$REMOTE_FILE'"
            $DEPLOYED++
        } else {
            scp -i $EC2_KEY -r "$file" "$EC2_USER@$EC2_HOST`:$REMOTE_FILE" 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "${GREEN}✓${RESET} $file"
                $DEPLOYED++
            } else {
                Write-Host "${RED}✗${RESET} $file (failed)"
                $FAILED++
            }
        }
    } else {
        Write-Host "${YELLOW}⊘${RESET} $file (not found locally)"
        $FAILED++
    }
}

Write-Host "`n"

# Set permissions
Write-Host "${BLUE}Setting file permissions...${RESET}"
if ($DryRun) {
    Write-Host "  [DRY RUN] chmod -R 755 $REMOTE_PATH/private/admin"
    Write-Host "  [DRY RUN] chmod -R 755 $REMOTE_PATH/admin_static"
} else {
    ssh -i $EC2_KEY "$EC2_USER@$EC2_HOST" "chmod -R 755 $REMOTE_PATH/private/admin"
    ssh -i $EC2_KEY "$EC2_USER@$EC2_HOST" "chmod -R 755 $REMOTE_PATH/admin_static"
    Write-Host "${GREEN}✓ Permissions set${RESET}"
}

# Verify deployment
Write-Host "`n${BLUE}Verifying deployment...${RESET}`n"
if ($DryRun) {
    Write-Host "  [DRY RUN] Verification skipped"
} else {
    $REMOTE_FILES = ssh -i $EC2_KEY "$EC2_USER@$EC2_HOST" "find $REMOTE_PATH/private/admin -type f -name '*.html' | wc -l" 2>&1
    $DOCS = ssh -i $EC2_KEY "$EC2_USER@$EC2_HOST" "find $REMOTE_PATH -maxdepth 1 -name '*.md' | wc -l" 2>&1
    
    Write-Host "${GREEN}✓ Admin HTML files on server: $REMOTE_FILES${RESET}"
    Write-Host "${GREEN}✓ Documentation files on server: $DOCS${RESET}"
}

# Summary
Write-Host "`n${BLUE}╔═══════════════════════════════════════════╗${RESET}"
Write-Host "${BLUE}║         Deployment Summary                ║${RESET}"
Write-Host "${BLUE}╚═══════════════════════════════════════════╝${RESET}`n"

if ($DryRun) {
    Write-Host "${YELLOW}DRY RUN - No files were actually deployed${RESET}"
} else {
    Write-Host "${GREEN}Files deployed:   $DEPLOYED${RESET}"
    Write-Host "${RED}Files failed:      $FAILED${RESET}"
    
    if ($FAILED -eq 0) {
        Write-Host "`n${GREEN}✓ Deployment completed successfully!${RESET}`n"
        Write-Host "Next steps:"
        Write-Host "  1. SSH to server: ssh -i $EC2_KEY $EC2_USER@$EC2_HOST"
        Write-Host "  2. Restart FastAPI app: systemctl restart banking-api"
        Write-Host "  3. Check logs: tail -f /var/log/banking-api.log"
        Write-Host "  4. Access admin: https://yourdomain.com/admin/dashboard"
    } else {
        Write-Host "`n${RED}✗ Deployment completed with errors${RESET}"
    }
}

Write-Host ""
