@echo off
REM Copy Updated Files to EC2 Instance
REM Updates: .env, test_rds_direct_connection.py, RDS_CREDENTIALS.md

setlocal enabledelayedexpansion

set EC2_HOST=51.20.190.13
set EC2_USER=ec2-user
set KEY_FILE=BankingBackendKey.pem
set REMOTE_PATH=/home/ec2-user/financial-services-website-template

echo.
echo ========================================
echo Uploading Files to EC2 Instance
echo ========================================
echo.
echo Target: %EC2_USER%@%EC2_HOST%:%REMOTE_PATH%
echo.

REM Check if key exists
if not exist "%KEY_FILE%" (
    echo ERROR: %KEY_FILE% not found in current directory
    exit /b 1
)

REM Upload .env
echo [1/3] Uploading .env...
scp -i "%KEY_FILE%" -o StrictHostKeyChecking=no ".env" "%EC2_USER%@%EC2_HOST%:%REMOTE_PATH%/.env"
if errorlevel 1 (
    echo ERROR: Failed to upload .env
    exit /b 1
)
echo ✓ .env uploaded

REM Upload test_rds_direct_connection.py
echo [2/3] Uploading test_rds_direct_connection.py...
scp -i "%KEY_FILE%" -o StrictHostKeyChecking=no "test_rds_direct_connection.py" "%EC2_USER%@%EC2_HOST%:%REMOTE_PATH%/test_rds_direct_connection.py"
if errorlevel 1 (
    echo ERROR: Failed to upload test_rds_direct_connection.py
    exit /b 1
)
echo ✓ test_rds_direct_connection.py uploaded

REM Upload RDS_CREDENTIALS.md
echo [3/3] Uploading RDS_CREDENTIALS.md...
scp -i "%KEY_FILE%" -o StrictHostKeyChecking=no "RDS_CREDENTIALS.md" "%EC2_USER%@%EC2_HOST%:%REMOTE_PATH%/RDS_CREDENTIALS.md"
if errorlevel 1 (
    echo ERROR: Failed to upload RDS_CREDENTIALS.md
    exit /b 1
)
echo ✓ RDS_CREDENTIALS.md uploaded

echo.
echo ========================================
echo ✅ All Files Uploaded Successfully
echo ========================================
echo.
echo Files updated on EC2:
echo   - .env (database configuration)
echo   - test_rds_direct_connection.py (connection test)
echo   - RDS_CREDENTIALS.md (documentation)
echo.
echo Next steps on EC2:
echo   1. SSH into EC2: ssh -i %KEY_FILE% %EC2_USER%@%EC2_HOST%
echo   2. Restart FastAPI: pkill -f 'python main.py'; python main.py &
echo   3. Or: python test_rds_direct_connection.py
echo.
