#!/bin/bash
# Verify files and restart FastAPI on EC2

echo "=========================================="
echo "Verifying Updated Files on EC2"
echo "=========================================="
echo ""

# Check files
echo "Checking uploaded files..."
ls -lh /home/ec2-user/financial-services-website-template/.env
ls -lh /home/ec2-user/financial-services-website-template/test_rds_direct_connection.py
ls -lh /home/ec2-user/financial-services-website-template/RDS_CREDENTIALS.md

echo ""
echo "Files verified!"
echo ""
echo "=========================================="
echo "Restarting FastAPI with Updated Config"
echo "=========================================="
echo ""

# Kill existing FastAPI process
pkill -f "python main.py" || true
sleep 2

# Restart FastAPI in background
cd /home/ec2-user/financial-services-website-template
nohup python main.py > /tmp/fastapi.log 2>&1 &

sleep 3

# Check if running
if pgrep -f "python main.py" > /dev/null; then
    echo "✅ FastAPI restarted successfully"
    echo ""
    echo "Access your application:"
    echo "  - Admin Dashboard: http://51.20.190.13:8000"
    echo "  - API Docs: http://51.20.190.13:8000/docs"
    echo ""
    tail -20 /tmp/fastapi.log
else
    echo "❌ FastAPI failed to start"
    echo ""
    echo "Check logs:"
    tail -50 /tmp/fastapi.log
fi
