@echo off
REM Test Database Accessibility
REM This script verifies if the RDS database is accessible through EC2

setlocal enabledelayedexpansion

echo.
echo ========================================================================
echo                   DATABASE ACCESSIBILITY TEST
echo ========================================================================
echo.

REM Check if SSH tunnel is likely open (indirectly by checking if we can connect)
echo Verifying prerequisites...
echo.

REM Run the Python test script
echo Running database tests...
echo.

python test_database_access.py

if errorlevel 1 (
    echo.
    echo ========================================================================
    echo                           TROUBLESHOOTING
    echo ========================================================================
    echo.
    echo Error detected! Common solutions:
    echo.
    echo 1. SSH Tunnel Not Open:
    echo    - Run: setup_ec2_tunnel.ps1
    echo    - Keep the tunnel window OPEN
    echo.
    echo 2. Database Not Running:
    echo    - Check AWS Console for RDS instance status
    echo    - Verify it shows "Available" status
    echo.
    echo 3. Wrong Connection String:
    echo    - Check .env DATABASE_URL setting
    echo    - Should be: postgresql+asyncpg://...@localhost:5432/finbank
    echo.
    echo 4. Python Dependencies:
    echo    - Run: pip install -r requirements.txt
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo Database test completed successfully!
    echo.
    pause
    exit /b 0
)
