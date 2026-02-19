@echo off
REM SSH Tunnel for RDS Access
REM Run this FIRST in a separate terminal before running database tests

echo.
echo ========================================
echo RDS SSH Tunnel Setup
echo ========================================
echo.
echo This will create an SSH tunnel from your local machine to EC2
echo Once connected, your FastAPI app can access RDS at localhost:5432
echo.
echo Keep this terminal OPEN - the tunnel will stay active in background
echo.

REM Check if BankingBackendKey.pem exists
if not exist "BankingBackendKey.pem" (
    echo ERROR: BankingBackendKey.pem not found in current directory
    echo Please copy the key file to: %cd%
    pause
    exit /b 1
)

echo Starting SSH tunnel...
echo EC2 Host: 51.20.190.13
echo RDS Host: finanza-bank.cluster-cxo2eume87bz.eu-north-1.rds.amazonaws.com
echo.

REM Create SSH tunnel
REM -i: Identity file (private key)
REM -L: Local port forwarding (local:EC2:remote)
REM -N: Don't execute remote command
REM -v: Verbose for debugging

ssh -i BankingBackendKey.pem ^
    -L 5432:finanza-bank.cluster-cxo2eume87bz.eu-north-1.rds.amazonaws.com:5432 ^
    -N -v ^
    ec2-user@51.20.190.13

echo.
echo If you see "Authentications that can continue: publickey" - connection successful!
echo Keep this window open. Open a NEW terminal to run database tests.
pause
