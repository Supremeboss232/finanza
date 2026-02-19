@echo off
REM Test Admin API Connection
REM This script verifies if the admin is connected to the database API

setlocal enabledelayedexpansion

echo.
echo ========================================================================
echo                    ADMIN API CONNECTION TEST
echo ========================================================================
echo.

REM Run the Python test script
python test_admin_connection.py

if errorlevel 1 (
    echo.
    echo Troubleshooting:
    echo   1. Is FastAPI running? python main.py
    echo   2. Is EC2 instance running? Check AWS Console
    echo   3. Is SSH tunnel open? Run setup_ec2_tunnel.ps1
    echo   4. Is database accessible? Check .env DATABASE_URL
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo Press any key to continue...
    pause
    exit /b 0
)
