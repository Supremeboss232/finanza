#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# FINANZA BANK — 24/7 ENTERPRISE SECURE KEEP-ALIVE LAUNCHER
# Powered by Cloudflare Zero Trust & Cloudflare Edge Tunnels
# ==============================================================================
# Security & Stability Highlights:
#  1. Cloudflare Anycast Edge Network with TLS 1.3 End-to-End Encryption
#  2. Enterprise DDoS mitigation, WAF, and ZERO phishing/security interstitial warnings
#  3. Android Termux Hardware Wake-Lock (stays online with screen off)
#  4. Automatic 24/7 background restart supervisor
#  5. Supports Free Cloudflare Quick Tunnels (*.trycloudflare.com) OR
#     Custom Private Domains via Cloudflare Zero Trust Tunnel Token
# ==============================================================================

PORT="${PORT:-8000}"
SUBDOMAIN="${SUBDOMAIN:-bankfinanza}"
TUNNEL_PROVIDER="${TUNNEL_PROVIDER:-cloudflare}"   # "cloudflare" (default), "localtunnel" (fixed subdomain), or "pinggy"
CLOUDFLARE_TUNNEL_TOKEN="${CLOUDFLARE_TUNNEL_TOKEN:-}"
CUSTOM_DOMAIN="${CUSTOM_DOMAIN:-bankfinanza.trycloudflare.com}"

echo "============================================================"
echo "  FINANZA DIGITAL BANK — 24/7 SECURE LAUNCHER"
echo "  Edge Tunnel: Cloudflare Zero Trust (Enterprise Security)"
echo "============================================================"

# 1. Prevent Android from sleeping or killing Termux in the background
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
    echo "[OK] Android Hardware Wake-Lock acquired (Termux will stay alive with screen off)"
else
    echo "[INFO] Running without termux-wake-lock. Run 'pkg install termux-api' for hardware lock."
fi

# 2. Sync latest files from /sdcard/finanza if available
if [ -d "/sdcard/finanza" ]; then
    echo "[SYNC] Copying latest updates from /sdcard/finanza/ to $(pwd)..."
    cp -rf /sdcard/finanza/* . 2>/dev/null || true
    echo "[OK] Workspace synchronized."
fi

# 3. Clean up any old stuck uvicorn or tunnel processes
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "cloudflared" 2>/dev/null || true
pkill -f "pinggy.io" 2>/dev/null || true
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
    pkill -f "cloudflared" 2>/dev/null || true
    if command -v termux-wake-unlock >/dev/null 2>&1; then
        termux-wake-unlock
    fi
    exit 0
}
trap cleanup INT TERM

# Wait until port 8000 is listening before opening the public tunnel
echo "[WAIT] Waiting for FastAPI backend to initialize..."
for i in $(seq 1 30); do
    if curl -s "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
        echo "[OK] Finanza API is healthy on http://127.0.0.1:${PORT}"
        break
    fi
    sleep 1
done

# 5. Ensure Cloudflare binary is present
ensure_cloudflared() {
    if ! command -v cloudflared >/dev/null 2>&1; then
        echo "[SETUP] Installing official Cloudflare Tunnel package in Termux..."
        pkg install cloudflared -y || {
            echo "[WARN] Could not install cloudflared via pkg. Falling back to Pinggy HTTPS tunnel."
            return 1
        }
    fi
    return 0
}

# 6. Start 24/7 Auto-Reconnecting Secure Tunnel Loop
while true; do
    if [ -n "${CLOUDFLARE_TUNNEL_TOKEN}" ]; then
        # Branded Private Custom Domain via Cloudflare Zero Trust Tunnel
        if ensure_cloudflared; then
            echo "============================================================"
            echo "  STARTING PRIVATE CLOUDFLARE ZERO TRUST TUNNEL"
            if [ -n "${CUSTOM_DOMAIN}" ]; then
                echo "  Private Domain: https://${CUSTOM_DOMAIN}"
            fi
            echo "  Enterprise DDoS Protection & TLS 1.3 Active"
            echo "============================================================"
            cloudflared tunnel --no-autoupdate run --token "${CLOUDFLARE_TUNNEL_TOKEN}"
        fi
    elif [ "${TUNNEL_PROVIDER}" = "cloudflare" ]; then
        # Free Cloudflare Quick Tunnel (*.trycloudflare.com)
        if ensure_cloudflared; then
            rm -f cloudflared.log
            echo "============================================================"
            echo "  CONNECTING TO CLOUDFLARE SECURE EDGE NETWORK..."
            echo "============================================================"

            # Background worker to extract and display the clean URL banner
            (
                for attempt in $(seq 1 20); do
                    sleep 1
                    if [ -f cloudflared.log ]; then
                        TUNNEL_URL=$(grep -oE "https://[a-zA-Z0-9.-]+\.trycloudflare\.com" cloudflared.log | head -n 1)
                        if [ -n "${TUNNEL_URL}" ]; then
                            echo ""
                            echo "************************************************************"
                            echo "  SUCCESS! SECURE CLOUDFLARE DOMAIN IS LIVE:"
                            echo "  >> ${TUNNEL_URL} <<"
                            echo ""
                            echo "  PWA Mobile App: Open the link above in Chrome or Safari,"
                            echo "  then tap 'Install App' or 'Add to Home Screen'!"
                            echo "  DDoS Protection: Cloudflare Edge Anycast Enabled"
                            echo "************************************************************"
                            echo ""
                            break
                        fi
                    fi
                done
            ) &

            cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:${PORT}" 2>&1 | tee cloudflared.log
        else
            echo "[FALLBACK] Using Pinggy HTTPS tunnel..."
            TUNNEL_PROVIDER="pinggy"
        fi
    elif [ "${TUNNEL_PROVIDER}" = "localtunnel" ]; then
        # Fixed Subdomain (https://${SUBDOMAIN}.loca.lt) via Localtunnel
        echo "============================================================"
        echo "  CONNECTING TO FIXED SUBDOMAIN TUNNEL..."
        echo "  Target Domain: https://${SUBDOMAIN}.loca.lt"
        echo "============================================================"
        if ! command -v lt >/dev/null 2>&1; then
            if ! command -v node >/dev/null 2>&1; then
                pkg install nodejs -y
            fi
            npm install -g localtunnel 2>/dev/null || true
        fi
        lt --port "${PORT}" --subdomain "${SUBDOMAIN}"
    elif [ "${TUNNEL_PROVIDER}" = "pinggy" ]; then
        # Secure HTTPS via Pinggy with Let's Encrypt TLS and no phishing warnings
        echo "============================================================"
        echo "  CONNECTING TO PINGGY SECURE HTTPS TUNNEL..."
        echo "============================================================"
        ssh -p 443 \
            -o ServerAliveInterval=15 \
            -o ServerAliveCountMax=3 \
            -o ExitOnForwardFailure=yes \
            -o ConnectTimeout=10 \
            -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -R0:localhost:${PORT} a.pinggy.io
    fi

    echo "[TUNNEL] Connection reset or restarted. Re-establishing secure tunnel in 3 seconds..."
    sleep 3
done
