#!/bin/bash
set -e

echo "======================================================"
echo "  Deploying Finanza Banking Platform on Google Cloud  "
echo "======================================================"

# 1. Update OS and install dependencies
sudo apt-get update -y
sudo apt-get install -y python3-pip python3-venv git curl

# 2. Setup app directory
APP_DIR="/opt/finanza"
sudo mkdir -p "$APP_DIR"
sudo chown -R "$USER":"$USER" "$APP_DIR"

# 3. Clone or pull repository
if [ -d "$APP_DIR/.git" ]; then
    echo "[*] Updating existing repository..."
    cd "$APP_DIR"
    git fetch origin
    git reset --hard origin/master
else
    echo "[*] Cloning repository..."
    git clone https://github.com/Supremeboss232/finanza.git "$APP_DIR"
    cd "$APP_DIR"
fi

# 4. Set up Python virtual environment
echo "[*] Setting up Python virtual environment..."
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# 5. Configure systemd service for 24/7 uptime & auto-restart
echo "[*] Configuring systemd background service..."
sudo tee /etc/systemd/system/finanza.service > /dev/null <<EOF
[Unit]
Description=Finanza Banking Platform API
After=network.target

[Service]
User=$USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 80 --workers 1
Restart=always
RestartSec=5
Environment=ENVIRONMENT=production
Environment=USE_LOCAL_DB=true
Environment=SECRET_KEY=finanza-production-secret-key-2026-google-cloud

[Install]
WantedBy=multi-user.target
EOF

# 6. Enable and start service
echo "[*] Starting Finanza service..."
sudo systemctl daemon-reload
sudo systemctl enable finanza
sudo systemctl restart finanza

# 7. Print status and public IP
sleep 3
sudo systemctl status finanza --no-pager

EXTERNAL_IP=$(curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip 2>/dev/null || curl -s ifconfig.me 2>/dev/null || echo "YOUR-SERVER-IP")

echo ""
echo "======================================================"
echo "  SUCCESS! Finanza is now running 24/7 online!        "
echo "  Visit your website at: http://$EXTERNAL_IP          "
echo "======================================================"
