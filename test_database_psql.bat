@echo off
REM Direct PostgreSQL Connection Test using psql
REM Tests database without going through Python

setlocal enabledelayedexpansion

echo.
echo ========================================================================
echo              DIRECT PostgreSQL CONNECTION TEST (psql)
echo ========================================================================
echo.

echo Prerequisites:
echo  1. PostgreSQL psql CLI must be installed
echo  2. SSH tunnel must be OPEN (run setup_ec2_tunnel.ps1 in separate terminal)
echo.

REM Check if psql is available
where psql >nul 2>nul
if errorlevel 1 (
    echo.
    echo ❌ psql command not found!
    echo.
    echo PostgreSQL is not installed or not in PATH.
    echo.
    echo To install psql:
    echo  • Download PostgreSQL from: https://www.postgresql.org/download/windows/
    echo  • Or install just the tools: https://www.pgadmin.org/
    echo.
    echo Or use the Python test instead:
    echo  • Run: test_database_access.bat
    echo.
    pause
    exit /b 1
)

echo ✅ psql found. Testing connection...
echo.

REM Test connection
echo Testing connection to RDS through SSH tunnel...
echo Database: finbank
echo Host: localhost:5432
echo User: postgres_admin
echo.

REM Run psql with password
echo Connecting...
psql -h localhost -p 5432 -U postgres_admin -d finbank -c "SELECT 1 as connection_test;"

if errorlevel 1 (
    echo.
    echo ❌ Connection failed!
    echo.
    echo Troubleshooting:
    echo  1. Is SSH tunnel open? Look for setup_ec2_tunnel.ps1 window
    echo  2. Is RDS running? Check AWS Console
    echo  3. Are credentials correct?
    echo     Host: localhost
    echo     Port: 5432
    echo     Database: finbank
    echo     User: postgres_admin
    echo     Password: Supposedbe5
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo ========================================================================
    echo                      CONNECTION SUCCESSFUL!
    echo ========================================================================
    echo.
    echo ✅ Database is accessible via psql
    echo.
    echo You can now run SQL queries interactively.
    echo Type '\q' to exit psql
    echo.
    
    REM Open interactive psql
    echo Opening interactive PostgreSQL prompt...
    echo.
    psql -h localhost -p 5432 -U postgres_admin -d finbank
)

pause
