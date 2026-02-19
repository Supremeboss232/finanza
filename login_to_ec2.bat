@echo off
REM Login to EC2 Instance via Command Prompt
REM This script connects to your Finanza Bank EC2 instance via SSH

setlocal enabledelayedexpansion

set EC2_HOST=ec2-51-20-190-13.eu-north-1.compute.amazonaws.com
set EC2_IP=51.20.190.13
set EC2_USER=ec2-user
set EC2_KEY_PATH=BankingBackendKey.pem

echo.
echo ============================================================
echo         EC2 INSTANCE LOGIN - FINANZA BANK
echo ============================================================
echo.

REM Check if .pem file exists
if not exist "%EC2_KEY_PATH%" (
    echo Error: %EC2_KEY_PATH% not found!
    echo Please ensure the .pem file is in the current directory.
    echo.
    pause
    exit /b 1
)

echo [OK] SSH Key found: %EC2_KEY_PATH%
echo [*] Connecting to: %EC2_HOST%
echo     IP: %EC2_IP%
echo     User: %EC2_USER%
echo.
echo [*] Opening SSH connection...
echo.

REM Connect via SSH
ssh -i "%EC2_KEY_PATH%" "%EC2_USER%@%EC2_HOST%"

echo.
echo [OK] SSH session closed.
echo.
pause
