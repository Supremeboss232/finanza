#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# FINANZA BANK — 24/7 KEEP-ALIVE SERVER & AUTO-RECONNECTING PRIVATE TUNNEL
# ==============================================================================
# Fixes:
#  1. Android killing Termux when screen turns off -> acquires termux-wake-lock
#  2. Serveo / SSH tunnel dropping after a few minutes -> TCP keep-alives every
#     15 seconds + instant 3-second auto-reconnect loop
#  3. Optional Cloudflare Tunnel support for your own custom private domain
#
# Usage inside Termux:
#   cp -r /sdcard/finanza/* ~/finanza/
#   cd ~/finanza
#   bash start_finanza_24_7.sh
# ==============================================================================

PORT="${PORT:-8000}"
SUBDOMAIN="${SUBDOMAIN:-bankfinanza}"
TUNNEL_PROVIDER="${TUNNEL_PROVIDER:-serveo}"   # "serveo", "cloudflare", or "localhostrun"
CLOUDFLARE_TUNNEL_TOKEN="${CLOUDFLARE_TUNNEL_TOKEN:-}"

echo "============================================================"
echo "  FINANZA DIGITAL BANK — 24/7 KEEP-ALIVE LAUNCHER"
echo "============================================================"

# 1. Prevent Android from sleeping or killing Termux in the background
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
    echo "[OK] Android Wake-Lock acquired (Termux will stay alive with screen off)"
else
    echo "[INFO] Tip: Run 'pkg install termux-api' for hardware wake-lock support"
fi

# 2. Sync latest files from /sdcard/finanza if available
if [ -d "/sdcard/finanza" ]; then
    echo "[SYNC] Copying latest updates from /sdcard/finanza/ to $(pwd)..."
    cp -rf /sdcard/finanza/* . 2>/dev/null || true
    echo "[OK] Workspace synchronized."
fi

# 3. Clean up any old stuck uvicorn or tunnel processes on this port
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "serveo.net" 2>/dev/null || true
sleep 1

# 4. Start FastAPI / Uvicorn in an auto-restarting background supervisor
start_backend_loop() {
    while true; do
        echo "[BACKEND] Starting Finanza FastAPI server on 0.0.0.0:${PORT}..."
        uvicorn main:app --host 0.0.0.0 --port "${PORT}" --timeout-keep-alive 75 2>&1 | tee -a finanza_server.log
        EXIT_CODE=$?
        echo "[BACKEND] Uvicorn exited (code ${EXIT_CODE}). Restarting in 3 seconds..."
        sleep 3
    done
}

start_backend_loop &
BACKEND_PID=$!

# Cleanup trap when user presses Ctrl+C
cleanup() {
    echo ""
    echo "[SHUTDOWN] Stopping Finanza 24/7 Launcher..."
    kill "${BACKEND_PID}" 2>/dev/null || true
    pkill -f "uvicorn main:app" 2>/dev/null || true
    if command -v termux-wake-unlock >/dev/null 2>&1; then
        termux-wake-unlock
    fi
    exit 0
}
trap cleanup INT TERM

# Wait until port 8000 is listening before opening the public tunnel
echo "[WAIT] Waiting for FastAPI to finish startup..."
for i in $(seq 1 25); do
    if curl -s "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
        echo "[OK] Finanza API is healthy on http://127.0.0.1:${PORT}"
        break
    fi
    sleep 1
done

echo "============================================================"
echo "  ACTIVE DOMAIN: https://${SUBDOMAIN}.serveousercontent.com"
echo "  PWA INSTALL:   Open the link in Chrome/Safari -> Install App"
echo "============================================================"

# 5. Start 24/7 Auto-Reconnecting Tunnel Loop
while true; do
    if [ -n "${CLOUDFLARE_TUNNEL_TOKEN}" ]; then
        # Private Custom Domain via Cloudflare Zero Trust Tunnel
        if ! command -v cloudflared >/dev/null 2>&1; then
            echo "[CLOUDFLARE] Installing cloudflared..."
            pkg install cloudflared -y
        fi
        echo "[TUNNEL] Connecting Private Cloudflare Domain Tunnel..."
        cloudflared tunnel --no-autoupdate run --token "${CLOUDFLARE_TUNNEL_TOKEN}"
    elif [ "${TUNNEL_PROVIDER}" = "cloudflare" ]; then
        # Free Cloudflare Quick Tunnel (*.trycloudflare.com)
        if ! command -v cloudflared >/dev/null 2>&1; then
            echo "[CLOUDFLARE] Installing cloudflared..."
            pkg install cloudflared -y
        fi
        echo "[TUNNEL] Starting Cloudflare Quick Tunnel to http://127.0.0.1:${PORT}..."
        cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:${PORT}"
    else
        # Hardened Serveo Tunnel with 15s heartbeat & instant reconnect
        echo "[TUNNEL] Connecting https://${SUBDOMAIN}.serveousercontent.com -> localhost:${PORT} ..."
        ssh -o ServerAliveInterval=15 \
            -o ServerAliveCountMax=3 \
            -o ExitOnForwardFailure=yes \
            -o ConnectTimeout=10 \
            -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -R "${SUBDOMAIN}:80:localhost:${PORT}" serveo.net
    fi

    echo "[TUNNEL] Connection dropped or reset by network. Reconnecting in 3 seconds..."
    sleep 3
done
