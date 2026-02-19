# Open RDS SSH Tunnel - PowerShell Version
# Run this once, tunnel will stay open in background

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RDS SSH Tunnel Starter" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check SSH key
if (-not (Test-Path "BankingBackendKey.pem")) {
    Write-Host "ERROR: BankingBackendKey.pem not found" -ForegroundColor Red
    exit 1
}

# Kill existing tunnels on port 5432
Write-Host "Cleaning up existing connections on port 5432..." -ForegroundColor Yellow
Get-NetTCPConnection -LocalPort 5432 -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}

Write-Host "Opening tunnel..." -ForegroundColor Green
Write-Host "  Local Port: 5432" -ForegroundColor Cyan
Write-Host "  EC2 Host: 51.20.190.13" -ForegroundColor Cyan
Write-Host "  RDS Host: finanza-bank.cluster-cxo2eume87bz.eu-north-1.rds.amazonaws.com" -ForegroundColor Cyan
Write-Host ""

# Start SSH tunnel - use -f to fork and -N to not execute command
$sshProcess = Start-Process -FilePath "ssh" `
    -ArgumentList "-i BankingBackendKey.pem", `
        "-L 5432:finanza-bank.cluster-cxo2eume87bz.eu-north-1.rds.amazonaws.com:5432", `
        "-f", "-N", `
        "ec2-user@51.20.190.13" `
    -PassThru -NoNewWindow -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2

# Check if tunnel is established
Write-Host "Verifying tunnel connection..." -ForegroundColor Yellow
$portCheck = Get-NetTCPConnection -LocalPort 5432 -State Established -ErrorAction SilentlyContinue

if ($portCheck) {
    Write-Host "✓ SSH Tunnel is OPEN" -ForegroundColor Green
    Write-Host "✓ Port 5432 is listening" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now:" -ForegroundColor Cyan
    Write-Host "  1. Run database tests" -ForegroundColor White
    Write-Host "  2. Connect FastAPI app" -ForegroundColor White
    Write-Host "  3. Use psql to query RDS" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "⚠ Tunnel may still be initializing..." -ForegroundColor Yellow
    Write-Host "  If tunnel fails to open, check:" -ForegroundColor Yellow
    Write-Host "    - BankingBackendKey.pem exists and is readable" -ForegroundColor Gray
    Write-Host "    - EC2 instance is running (51.20.190.13)" -ForegroundColor Gray
    Write-Host "    - SSH key has correct permissions" -ForegroundColor Gray
}

Write-Host "Tunnel process ID: $($sshProcess.Id)" -ForegroundColor Gray
Write-Host ""
