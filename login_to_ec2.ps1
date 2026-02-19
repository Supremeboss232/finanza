# Login to EC2 Instance
# This script connects to your Finanza Bank EC2 instance via SSH

$EC2_HOST = "ec2-51-20-190-13.eu-north-1.compute.amazonaws.com"
$EC2_IP = "51.20.190.13"
$EC2_USER = "ec2-user"
$EC2_KEY_PATH = "BankingBackendKey.pem"

Write-Host "`n" -ForegroundColor Cyan
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         EC2 INSTANCE LOGIN - FINANZA BANK                   ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Check if .pem file exists
if (-not (Test-Path $EC2_KEY_PATH)) {
    Write-Host "❌ Error: $EC2_KEY_PATH not found!" -ForegroundColor Red
    Write-Host "   Please ensure the .pem file is in the current directory.`n" -ForegroundColor Red
    exit 1
}

Write-Host "✅ SSH Key found: $EC2_KEY_PATH" -ForegroundColor Green
Write-Host "📡 Connecting to: $EC2_HOST" -ForegroundColor Cyan
Write-Host "   IP: $EC2_IP" -ForegroundColor Cyan
Write-Host "   User: $EC2_USER`n" -ForegroundColor Cyan

# Connect via SSH
Write-Host "🔑 Opening SSH connection...`n" -ForegroundColor Yellow

ssh -i $EC2_KEY_PATH "$EC2_USER@$EC2_HOST"

Write-Host "`n✅ SSH session closed." -ForegroundColor Green
