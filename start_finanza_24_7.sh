#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# FINANZA BANK — 24/7 MULTI-ENGINE SECURE LAUNCHER
# Fixed 'bankfinanza' Domain + Ngrok (bankfinanza.ngrok.app) + Cloudflare
# ==============================================================================
# What Runs Automatically:
#  1. Fixed Subdomain Tunnel (Pure Python): https://bankfinanza.loca.lt
#     - Always claims 'bankfinanza' with zero external binaries or signup
#  2. Enterprise Edge Tunnel:
#     - If NGROK_AUTHTOKEN is set: connects https://bankfinanza.ngrok.app (or NGROK_DOMAIN)
#     - If CLOUDFLARE_TUNNEL_TOKEN is set: connects https://bankfinanza.com via Cloudflare
#     - Otherwise: connects a direct zero-warning Let's Encrypt HTTPS tunnel (*.lhr.life)
#  3. Android Hardware Wake-Lock + 24/7 FastAPI Uvicorn Supervisor
# ==============================================================================

PORT="${PORT:-8000}"
SUBDOMAIN="${SUBDOMAIN:-bankfinanza}"
TUNNEL_PROVIDER="${TUNNEL_PROVIDER:-lhr}"
NGROK_AUTHTOKEN="${NGROK_AUTHTOKEN:-}"
NGROK_DOMAIN="${NGROK_DOMAIN:-bankfinanza.ngrok.app}"
CLOUDFLARE_TUNNEL_TOKEN="${CLOUDFLARE_TUNNEL_TOKEN:-}"

# Load NGROK_AUTHTOKEN / CLOUDFLARE_TUNNEL_TOKEN from .env if present
if [ -f ".env" ]; then
    ENV_NGROK_TOKEN=$(grep -E "^NGROK_AUTHTOKEN=" .env | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d '\r')
    ENV_NGROK_DOMAIN=$(grep -E "^NGROK_DOMAIN=" .env | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d '\r')
    ENV_CF_TOKEN=$(grep -E "^CLOUDFLARE_TUNNEL_TOKEN=" .env | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d '\r')
    [ -z "${NGROK_AUTHTOKEN}" ] && [ -n "${ENV_NGROK_TOKEN}" ] && NGROK_AUTHTOKEN="${ENV_NGROK_TOKEN}"
    [ -n "${ENV_NGROK_DOMAIN}" ] && NGROK_DOMAIN="${ENV_NGROK_DOMAIN}"
    [ -z "${CLOUDFLARE_TUNNEL_TOKEN}" ] && [ -n "${ENV_CF_TOKEN}" ] && CLOUDFLARE_TUNNEL_TOKEN="${ENV_CF_TOKEN}"
fi

if [ -n "${NGROK_AUTHTOKEN}" ]; then
    TUNNEL_PROVIDER="ngrok"
elif [ -n "${CLOUDFLARE_TUNNEL_TOKEN}" ]; then
    TUNNEL_PROVIDER="cloudflare_named"
fi

echo "============================================================"
echo "  FINANZA DIGITAL BANK — 24/7 SECURE LAUNCHER"
echo "  Primary Fixed Subdomain: https://${SUBDOMAIN}.loca.lt"
echo "  Edge Tunnel Mode:        ${TUNNEL_PROVIDER^^}"
echo "============================================================"

# 1. Prevent Android from sleeping or killing Termux in the background
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
    echo "[OK] Android Hardware Wake-Lock acquired (Termux stays alive with screen off)"
else
    echo "[INFO] Tip: Run 'pkg install termux-api' for hardware wake-lock."
fi

# 2. Sync latest files from /sdcard/finanza if available
if [ -d "/sdcard/finanza" ]; then
    echo "[SYNC] Copying latest updates from /sdcard/finanza/ to $(pwd)..."
    cp -rf /sdcard/finanza/* . 2>/dev/null || true
    echo "[OK] Workspace synchronized."
fi

# 3. Ensure SSH key exists for encrypted SSH tunnels
if [ ! -f "$HOME/.ssh/id_ed25519" ] && [ ! -f "$HOME/.ssh/id_rsa" ]; then
    echo "[SSH] Generating Termux SSH keypair..."
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    ssh-keygen -t ed25519 -N "" -f "$HOME/.ssh/id_ed25519" >/dev/null 2>&1 || true
fi

# 4. Clean up any old stuck processes
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "finanza_tunnel.py" 2>/dev/null || true
pkill -f "localhost.run" 2>/dev/null || true
pkill -f "pinggy.io" 2>/dev/null || true
pkill -f "ngrok http" 2>/dev/null || true
pkill -f "cloudflared" 2>/dev/null || true
sleep 1

# 5. Start FastAPI / Uvicorn in an auto-restarting background supervisor
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

# Wait until port 8000 is listening before opening tunnels
echo "[WAIT] Waiting for FastAPI backend to initialize..."
for i in $(seq 1 30); do
    if curl -s "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
        echo "[OK] Finanza API is healthy on http://127.0.0.1:${PORT}"
        break
    fi
    sleep 1
done

# 6. Start Pure-Python Fixed 'bankfinanza' Tunnel (https://bankfinanza.loca.lt) in background
if [ -f "finanza_tunnel.py" ]; then
    PUB_IP=$(curl -s --max-time 5 https://loca.lt/mytunnelpassword || curl -s --max-time 5 https://api.ipify.org || echo "")
    if [ -n "${PUB_IP}" ]; then
        echo "[INFO] If https://${SUBDOMAIN}.loca.lt asks for a 1-time Tunnel Password, enter: ${PUB_IP}"
    fi
    PORT="${PORT}" SUBDOMAIN="${SUBDOMAIN}" python finanza_tunnel.py &
    PY_TUNNEL_PID=$!
fi

# Cleanup trap when user presses Ctrl+C
cleanup() {
    echo ""
    echo "[SHUTDOWN] Stopping Finanza 24/7 Launcher..."
    kill "${BACKEND_PID}" 2>/dev/null || true
    kill "${PY_TUNNEL_PID}" 2>/dev/null || true
    pkill -f "uvicorn main:app" 2>/dev/null || true
    pkill -f "finanza_tunnel.py" 2>/dev/null || true
    pkill -f "localhost.run" 2>/dev/null || true
    pkill -f "pinggy.io" 2>/dev/null || true
    pkill -f "ngrok http" 2>/dev/null || true
    pkill -f "cloudflared" 2>/dev/null || true
    if command -v termux-wake-unlock >/dev/null 2>&1; then
        termux-wake-unlock
    fi
    exit 0
}
trap cleanup INT TERM

# Helper to install Official Ngrok ARM64 binary in Termux
ensure_ngrok() {
    if ! command -v ngrok >/dev/null 2>&1 && [ ! -f "./ngrok" ]; then
        echo "[NGROK] Downloading official Ngrok v3 Linux ARM64 binary..."
        curl -sSL "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz" -o ngrok.tgz
        tar -xzf ngrok.tgz -C "${PREFIX}/bin" 2>/dev/null || tar -xzf ngrok.tgz
        chmod +x "${PREFIX}/bin/ngrok" 2>/dev/null || chmod +x ./ngrok
        rm -f ngrok.tgz
    fi
    NGROK_BIN=$(command -v ngrok || echo "./ngrok")
    if [ -n "${NGROK_AUTHTOKEN}" ]; then
        "${NGROK_BIN}" config add-authtoken "${NGROK_AUTHTOKEN}" >/dev/null 2>&1 || true
    fi
}

# Helper to install Official Cloudflared ARM64 binary directly from GitHub
ensure_cloudflared() {
    if ! command -v cloudflared >/dev/null 2>&1 && [ ! -f "./cloudflared" ]; then
        echo "[CLOUDFLARE] Downloading official cloudflared Linux ARM64 binary..."
        curl -sSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64" -o "${PREFIX}/bin/cloudflared" 2>/dev/null || \
        curl -sSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64" -o "./cloudflared"
        chmod +x "${PREFIX}/bin/cloudflared" 2>/dev/null || chmod +x "./cloudflared"
    fi
    CF_BIN=$(command -v cloudflared || echo "./cloudflared")
}

watch_and_print_url() {
    (
        for attempt in $(seq 1 25); do
            sleep 1
            if [ -f tunnel.log ]; then
                LIVE_URL=$(grep -oE "https://[a-zA-Z0-9.-]+\.(lhr\.life|a\.pinggy\.link|pinggy\.link|ngrok-free\.app|ngrok\.app|ngrok\.io|trycloudflare\.com)" tunnel.log | tail -n 1)
                if [ -n "${LIVE_URL}" ]; then
                    echo ""
                    echo "************************************************************"
                    echo "  YOUR ACTIVE FINANZA WEB ADDRESSES:"
                    echo "  1) Fixed Subdomain: https://${SUBDOMAIN}.loca.lt"
                    if [ -n "${PUB_IP}" ]; then
                        echo "     (1-Time Tunnel Password if prompted: ${PUB_IP})"
                    fi
                    echo "  2) Direct Zero-Warning Link: ${LIVE_URL}"
                    echo "************************************************************"
                    echo ""
                    break
                fi
            fi
        done
    ) &
}

# 7. Start 24/7 Auto-Reconnecting Edge Tunnel Loop
FAIL_COUNT=0
while true; do
    rm -f tunnel.log

    if [ "${TUNNEL_PROVIDER}" = "ngrok" ]; then
        ensure_ngrok
        echo "============================================================"
        echo "  CONNECTING TO NGROK: https://${NGROK_DOMAIN}"
        echo "============================================================"
        watch_and_print_url
        # Try requested domain (e.g. bankfinanza.ngrok.app) first; fallback to automatic domain if not claimed on account yet
        "${NGROK_BIN}" http --url="${NGROK_DOMAIN}" "${PORT}" --log=stdout 2>&1 | tee tunnel.log
        if grep -qE "ERR_NGROK_313|ERR_NGROK_3208|ERR_NGROK_108" tunnel.log 2>/dev/null; then
            echo "[NGROK] Note: '${NGROK_DOMAIN}' is not claimed on this token yet; starting standard Ngrok HTTPS tunnel..."
            rm -f tunnel.log
            watch_and_print_url
            "${NGROK_BIN}" http "${PORT}" --log=stdout 2>&1 | tee tunnel.log
        fi
    elif [ "${TUNNEL_PROVIDER}" = "cloudflare_named" ]; then
        ensure_cloudflared
        echo "============================================================"
        echo "  CONNECTING PRIVATE CLOUDFLARE DOMAIN (bankfinanza.com)..."
        echo "============================================================"
        "${CF_BIN}" tunnel --no-autoupdate run --token "${CLOUDFLARE_TUNNEL_TOKEN}"
    elif [ "${TUNNEL_PROVIDER}" = "cloudflare" ]; then
        ensure_cloudflared
        echo "============================================================"
        echo "  CONNECTING TO CLOUDFLARE EDGE NETWORK..."
        echo "============================================================"
        watch_and_print_url
        "${CF_BIN}" tunnel --no-autoupdate --url "http://127.0.0.1:${PORT}" 2>&1 | tee tunnel.log
    elif [ "${TUNNEL_PROVIDER}" = "pinggy" ]; then
        echo "============================================================"
        echo "  CONNECTING TO PINGGY SECURE HTTPS TUNNEL..."
        echo "============================================================"
        watch_and_print_url
        ssh -p 443 \
            -o ServerAliveInterval=15 \
            -o ServerAliveCountMax=3 \
            -o ExitOnForwardFailure=yes \
            -o ConnectTimeout=12 \
            -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -R0:localhost:${PORT} a.pinggy.io 2>&1 | tee tunnel.log
    else
        echo "============================================================"
        echo "  CONNECTING DIRECT HTTPS TUNNEL (*.lhr.life)..."
        echo "============================================================"
        watch_and_print_url
        START_TS=$(date +%s)
        ssh -o ServerAliveInterval=15 \
            -o ServerAliveCountMax=3 \
            -o ExitOnForwardFailure=yes \
            -o ConnectTimeout=12 \
            -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -R 80:localhost:${PORT} nokey@localhost.run 2>&1 | tee tunnel.log
        END_TS=$(date +%s)

        if [ $((END_TS - START_TS)) -lt 5 ]; then
            FAIL_COUNT=$((FAIL_COUNT + 1))
            if [ "${FAIL_COUNT}" -ge 2 ]; then
                echo "[AUTO-SWITCH] Switching backup tunnel to Pinggy (Port 443)..."
                TUNNEL_PROVIDER="pinggy"
                FAIL_COUNT=0
            fi
        else
            FAIL_COUNT=0
        fi
    fi

    echo "[TUNNEL] Re-establishing edge tunnel in 3 seconds..."
    sleep 3
done
