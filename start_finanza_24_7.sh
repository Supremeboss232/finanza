#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# FINANZA BANK — 24/7 SECURE KEEP-ALIVE LAUNCHER (LHR.LIFE / NGROK / PINGGY)
# ==============================================================================
# Security & Stability Highlights:
#  1. Genuine Let's Encrypt TLS 1.3 HTTPS with ZERO browser phishing warnings
#  2. Supports:
#     - Localhost.run (*.lhr.life)  [DEFAULT — Instant, zero signup, no interstitial]
#     - Ngrok v3 (*.ngrok-free.app) [Set NGROK_AUTHTOKEN=... & optional NGROK_DOMAIN=...]
#     - Pinggy (*.a.pinggy.link)    [Automatic HTTPS port-443 fallback]
#  3. Auto-generates SSH keys if missing so tunnels never prompt for a password
#  4. Android Termux Hardware Wake-Lock (stays online with screen off)
#  5. Automatic 24/7 background restart supervisor for FastAPI + Tunnel
# ==============================================================================

PORT="${PORT:-8000}"
TUNNEL_PROVIDER="${TUNNEL_PROVIDER:-lhr}"   # "lhr" (default), "ngrok", or "pinggy"
NGROK_AUTHTOKEN="${NGROK_AUTHTOKEN:-}"
NGROK_DOMAIN="${NGROK_DOMAIN:-}"

# If user provided an Ngrok token, automatically use Ngrok
if [ -n "${NGROK_AUTHTOKEN}" ]; then
    TUNNEL_PROVIDER="ngrok"
fi

echo "============================================================"
echo "  FINANZA DIGITAL BANK — 24/7 SECURE LAUNCHER"
echo "  Active Tunnel Engine: ${TUNNEL_PROVIDER^^} (TLS 1.3 Encrypted)"
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

# 3. Ensure SSH key exists (required by localhost.run & pinggy for instant auth)
if [ ! -f "$HOME/.ssh/id_ed25519" ] && [ ! -f "$HOME/.ssh/id_rsa" ]; then
    echo "[SSH] Generating Termux SSH keypair for encrypted tunnel authentication..."
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    ssh-keygen -t ed25519 -N "" -f "$HOME/.ssh/id_ed25519" >/dev/null 2>&1 || true
    echo "[OK] SSH keypair ready."
fi

# 4. Clean up any old stuck uvicorn or tunnel processes
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "localhost.run" 2>/dev/null || true
pkill -f "pinggy.io" 2>/dev/null || true
pkill -f "ngrok http" 2>/dev/null || true
pkill -f "cloudflared" 2>/dev/null || true
pkill -f "serveo.net" 2>/dev/null || true
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

# Cleanup trap when user presses Ctrl+C
cleanup() {
    echo ""
    echo "[SHUTDOWN] Stopping Finanza 24/7 Launcher..."
    kill "${BACKEND_PID}" 2>/dev/null || true
    pkill -f "uvicorn main:app" 2>/dev/null || true
    pkill -f "localhost.run" 2>/dev/null || true
    pkill -f "pinggy.io" 2>/dev/null || true
    pkill -f "ngrok http" 2>/dev/null || true
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

# Helper to install Official Ngrok ARM64 binary in Termux if requested
ensure_ngrok() {
    if ! command -v ngrok >/dev/null 2>&1; then
        echo "[NGROK] Downloading official Ngrok v3 Linux ARM64 binary..."
        curl -sSL "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz" -o ngrok.tgz
        tar -xzf ngrok.tgz -C "${PREFIX}/bin" 2>/dev/null || tar -xzf ngrok.tgz
        chmod +x "${PREFIX}/bin/ngrok" 2>/dev/null || chmod +x ./ngrok
        rm -f ngrok.tgz
        echo "[OK] Ngrok installed."
    fi
    if [ -n "${NGROK_AUTHTOKEN}" ]; then
        ngrok config add-authtoken "${NGROK_AUTHTOKEN}" >/dev/null 2>&1 || true
    fi
}

# Helper to watch tunnel.log and print a prominent banner with the live URL
watch_and_print_url() {
    (
        for attempt in $(seq 1 25); do
            sleep 1
            if [ -f tunnel.log ]; then
                LIVE_URL=$(grep -oE "https://[a-zA-Z0-9.-]+\.(lhr\.life|a\.pinggy\.link|pinggy\.link|ngrok-free\.app|ngrok\.io)" tunnel.log | tail -n 1)
                if [ -n "${LIVE_URL}" ]; then
                    echo "${LIVE_URL}" > LIVE_URL.txt
                    echo ""
                    echo "************************************************************"
                    echo "  SUCCESS! YOUR SECURE FINANZA DOMAIN IS LIVE:"
                    echo "  >> ${LIVE_URL} <<"
                    echo ""
                    echo "  Saved to: ~/finanza/LIVE_URL.txt"
                    echo "  PWA Mobile App: Open the link above in Chrome or Safari,"
                    echo "  then tap 'Install App' or 'Add to Home Screen'!"
                    echo "************************************************************"
                    echo ""
                    break
                fi
            fi
        done
    ) &
}

# 6. Start 24/7 Auto-Reconnecting Secure Tunnel Loop
FAIL_COUNT=0
while true; do
    rm -f tunnel.log

    if [ "${TUNNEL_PROVIDER}" = "ngrok" ]; then
        ensure_ngrok
        echo "============================================================"
        echo "  CONNECTING TO NGROK SECURE EDGE TUNNEL..."
        echo "============================================================"
        if [ -n "${NGROK_DOMAIN}" ]; then
            echo "  Static Domain: https://${NGROK_DOMAIN}"
            ngrok http --url="${NGROK_DOMAIN}" "${PORT}"
        else
            ngrok http "${PORT}" --log=stdout | tee tunnel.log
        fi
    elif [ "${TUNNEL_PROVIDER}" = "pinggy" ]; then
        echo "============================================================"
        echo "  CONNECTING TO PINGGY SECURE HTTPS TUNNEL (PORT 443)..."
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
        # Default: Localhost.run (*.lhr.life) — Clean Let's Encrypt TLS 1.3, no warnings, no signup
        echo "============================================================"
        echo "  CONNECTING TO LOCALHOST.RUN (*.lhr.life) SECURE TUNNEL..."
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

        # If localhost.run failed in under 5 seconds twice in a row, auto-switch to Pinggy (port 443)
        if [ $((END_TS - START_TS)) -lt 5 ]; then
            FAIL_COUNT=$((FAIL_COUNT + 1))
            if [ "${FAIL_COUNT}" -ge 2 ]; then
                echo "[AUTO-SWITCH] Port 22 blocked by mobile carrier; switching to Pinggy (HTTPS Port 443)..."
                TUNNEL_PROVIDER="pinggy"
                FAIL_COUNT=0
            fi
        else
            FAIL_COUNT=0
        fi
    fi

    echo "[TUNNEL] Connection reset. Re-establishing secure tunnel in 3 seconds..."
    sleep 3
done
