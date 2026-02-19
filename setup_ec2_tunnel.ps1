# SSH Tunnel Setup for EC2 Bastion Host (PowerShell)
# This script creates an SSH tunnel to reach RDS database through EC2

# Configuration
$EC2_HOST = "ec2-51-20-190-13.eu-north-1.compute.amazonaws.com"
$EC2_IP = "51.20.190.13"
$EC2_USER = "ec2-user"
$EC2_KEY_PATH = "BankingBackendKey.pem"
$RDS_HOST = "finbank-db.cxo2eume87bz.eu-north-1.rds.amazonaws.com"
$RDS_PORT = 5432
$LOCAL_PORT = 5432

Write-Host "`n========================================================================" -ForegroundColor Cyan
Write-Host "FINANZA BANK - EC2 BASTION TUNNEL SETUP" -ForegroundColor Cyan
Write-Host "========================================================================`n" -ForegroundColor Cyan

# Check if .pem file exists
if (-not (Test-Path $EC2_KEY_PATH)) {
    Write-Host "❌ Error: $EC2_KEY_PATH not found!" -ForegroundColor Red
    Write-Host "   Please ensure the .pem file is in the current directory.`n" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Found $EC2_KEY_PATH" -ForegroundColor Green

# Check if SSH is available
try {
    $sshVersion = ssh -V 2>&1
    Write-Host "✅ SSH is available: $sshVersion`n" -ForegroundColor Green
} catch {
    Write-Host "❌ SSH not found! Windows 10/11 users need to install OpenSSH:" -ForegroundColor Red
    Write-Host "   Settings → Apps → Optional Features → Add OpenSSH Client" -ForegroundColor Red
    Write-Host "   Or download: https://www.microsoft.com/en-us/p/openssh/9mzd3tgd5oci`n" -ForegroundColor Red
    exit 1
}

# Create SSH tunnel
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "SSH TUNNEL SETUP" -ForegroundColor Cyan
Write-Host "========================================================================`n" -ForegroundColor Cyan

Write-Host "📡 Creating SSH tunnel..." -ForegroundColor Yellow
Write-Host "   EC2 Host: $EC2_HOST" -ForegroundColor Gray
Write-Host "   EC2 IP: $EC2_IP" -ForegroundColor Gray
Write-Host "   RDS Host: $RDS_HOST" -ForegroundColor Gray
Write-Host "   Local Port: $LOCAL_PORT`n" -ForegroundColor Gray

Write-Host "Command:" -ForegroundColor Gray
Write-Host "ssh -i `"$EC2_KEY_PATH`" -L $LOCAL_PORT`:$RDS_HOST`:$RDS_PORT $EC2_USER@$EC2_HOST -N" -ForegroundColor Gray
Write-Host ""

try {
    # Start SSH tunnel in background
    $process = Start-Process -FilePath "ssh" `
        -ArgumentList "-i", $EC2_KEY_PATH, "-L", "$LOCAL_PORT`:$RDS_HOST`:$RDS_PORT", "$EC2_USER@$EC2_HOST", "-N" `
        -NoNewWindow `
        -PassThru `
        -ErrorAction Stop
    
    # Wait a moment for tunnel to establish
    Start-Sleep -Seconds 2
    
    # Check if process is still running
    if ($process.HasExited) {
        Write-Host "❌ Tunnel failed to establish. Check your EC2 credentials." -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ SSH tunnel established successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🔗 Database is now accessible at:" -ForegroundColor Cyan
    Write-Host "   Host: localhost" -ForegroundColor Yellow
    Write-Host "   Port: $LOCAL_PORT" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "📝 Connection string for .env:" -ForegroundColor Cyan
    Write-Host "   DATABASE_URL=postgresql+asyncpg://postgres_admin:Supposedbe5@localhost:$LOCAL_PORT/finbank" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "💡 IMPORTANT: Keep this window OPEN while developing" -ForegroundColor Magenta
    Write-Host "   The tunnel will stay active as long as this PowerShell window is open." -ForegroundColor Magenta
    Write-Host "   Press Ctrl+C to close the tunnel when done.`n" -ForegroundColor Magenta
    
    # Wait for tunnel to be closed
    $process.WaitForExit()
    Write-Host "🛑 SSH tunnel closed." -ForegroundColor Red
    
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    exit 1
}
