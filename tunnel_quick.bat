@echo off
REM Quick RDS Tunnel Opener with Background Process
REM This opens the tunnel and returns immediately

setlocal enabledelayedexpansion

echo Opening RDS SSH Tunnel...

REM Check if key exists
if not exist "BankingBackendKey.pem" (
    echo ERROR: BankingBackendKey.pem not found
    exit /b 1
)

REM Kill any existing tunnels on port 5432
for /f "tokens=5" %%a in ('netstat -ano ^| find ":5432"') do (
    taskkill /PID %%a /F 2>nul
)

REM Start SSH tunnel in background
REM Using -f to go to background after authentication
start "" ssh -i BankingBackendKey.pem ^
    -L 5432:finanza-bank.cluster-cxo2eume87bz.eu-north-1.rds.amazonaws.com:5432 ^
    -f -N ^
    ec2-user@51.20.190.13

REM Wait 2 seconds for tunnel to establish
timeout /t 2 /nobreak

REM Test tunnel
echo Testing tunnel connection...
for /f "tokens=*" %%a in ('netstat -ano ^| find ":5432"') do (
    echo ✓ Tunnel established
    exit /b 0
)

echo Waiting for tunnel...
timeout /t 3 /nobreak
exit /b 0
