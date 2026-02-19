#!/bin/bash
# Run migration on EC2 instance

cd /home/ec2-user/financial-services-website-template

# Stop the FastAPI server
echo "Stopping FastAPI server..."
pkill -f "uvicorn main:app" || true
sleep 2

# Run migration
echo "Running migration to add user fields..."
python3 migrate_add_user_fields.py

# Restart the FastAPI server
echo "Restarting FastAPI server..."
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/fastapi.log 2>&1 &
sleep 2

echo "Migration complete! FastAPI server restarted."
