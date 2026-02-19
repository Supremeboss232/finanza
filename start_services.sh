#!/bin/bash
# Deploy both services on EC2

echo "================================"
echo "Starting Financial Services..."
echo "================================"

# Kill any existing processes
sudo killall -9 python3 2>/dev/null || true
sleep 2

# Start Financial Services on port 8000
cd /home/ec2-user
nohup python3 -c "
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title='Financial Services', version='2.0')

# Mount static files
admin_dir = Path('/home/ec2-user/private/admin')
if admin_dir.exists():
    app.mount('/private/admin', StaticFiles(directory=str(admin_dir)), name='admin')

@app.get('/')
def root():
    return {'service': 'Financial Services', 'port': 8000, 'status': 'running'}

@app.get('/health')
def health():
    return {'status': 'healthy'}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000, workers=2)
" > /tmp/financial.log 2>&1 & 

sleep 3

echo "Financial Services started on port 8000"
echo ""
echo "================================"
echo "Starting Stocker (Static Site)..."
echo "================================"

# Start simple HTTP server for Stocker on port 3300
cd /home/ec2-user/Stocker
nohup python3 -m http.server 3300 > /tmp/stocker.log 2>&1 &

sleep 2

echo "Stocker started on port 3300"
echo ""
echo "================================"
echo "Services Status:"
echo "================================"
sudo ss -tlnp | grep -E '3300|8000'

echo ""
echo "Financial Services: http://51.20.190.13:8000"
echo "Stocker: http://51.20.190.13:3300"
