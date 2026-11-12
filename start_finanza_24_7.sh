#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# FINANZA BANK — 24/7 5-ENGINE SIMULTANEOUS SECURE LAUNCHER
# ==============================================================================
# Runs 5 Simultaneous Tunnels to http://127.0.0.1:8000:
#  1. PageKite Fixed Domain:    https://bankfinanza.pagekite.me
#  2. Serveo SSH Tunnel:        https://bankfinanza.serveousercontent.com
#  3. Pinggy Port 443 Tunnel:   https://*.run.pinggy-free.link
#  4. Localhost.run Tunnel:     https://*.lhr.life
#  5. LocalTunnel Fixed Domain: https://bankfinanza.loca.lt
# ==============================================================================

PORT="${PORT:-8000}"
SUBDOMAIN="${SUBDOMAIN:-bankfinanza}"

echo "============================================================"
echo "  FINANZA DIGITAL BANK — 24/7 5-TUNNEL SECURE LAUNCHER"
echo "  1) PageKite:      https://${SUBDOMAIN}.pagekite.me"
echo "  2) Serveo:        https://${SUBDOMAIN}.serveousercontent.com"
echo "  3) Pinggy (443):  https://*.run.pinggy-free.link"
echo "  4) Localhost.run: https://*.lhr.life"
echo "  5) LocalTunnel:   https://${SUBDOMAIN}.loca.lt"
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

# 3. Ensure SSH key exists for Serveo, Pinggy, and Localhost.run
if [ ! -f "$HOME/.ssh/id_ed25519" ] && [ ! -f "$HOME/.ssh/id_rsa" ]; then
    echo "[SSH] Generating Termux SSH keypair..."
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    ssh-keygen -t ed25519 -N "" -f "$HOME/.ssh/id_ed25519" >/dev/null 2>&1 || true
fi
SSH_KEY_ARG=""
if [ -f "$HOME/.ssh/id_ed25519" ]; then
    SSH_KEY_ARG="-i $HOME/.ssh/id_ed25519"
elif [ -f "$HOME/.ssh/id_rsa" ]; then
    SSH_KEY_ARG="-i $HOME/.ssh/id_rsa"
fi

# 4. Clean up old tunnel processes (keep existing healthy uvicorn if already running)
pkill -f "finanza_tunnel.py" 2>/dev/null || true
pkill -f "pagekite.py" 2>/dev/null || true
pkill -f "serveo.net" 2>/dev/null || true
pkill -f "localhost.run" 2>/dev/null || true
pkill -f "pinggy.io" 2>/dev/null || true
sleep 1

# 5. Start FastAPI / Uvicorn in a quiet, non-duplicating background supervisor
start_backend_loop() {
    while true; do
        if curl -s --max-time 3 "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
            sleep 8
            continue
        fi
        echo "[BACKEND] Starting Finanza FastAPI server on 0.0.0.0:${PORT} (logs -> finanza_server.log)..."
        uvicorn main:app --host 0.0.0.0 --port "${PORT}" --timeout-keep-alive 75 >> finanza_server.log 2>&1
        sleep 3
    done
}

start_backend_loop &
BACKEND_PID=$!

# Wait until port 8000 is listening before opening tunnels
echo "[WAIT] Checking FastAPI backend health on port ${PORT}..."
for i in $(seq 1 30); do
    if curl -s "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
        echo "[OK] Finanza API is healthy on http://127.0.0.1:${PORT}"
        break
    fi
    sleep 1
done

PUB_IP=$(curl -s --max-time 5 https://loca.lt/mytunnelpassword || curl -s --max-time 5 https://api.ipify.org || echo "")

# 6. Start Background Tunnel Supervisors (#2 Serveo, #3 Pinggy, #4 Localhost.run, #5 LocalTunnel)
rm -f serveo.log pinggy.log lhr.log localtunnel.log LIVE_URL.txt
touch serveo.log pinggy.log lhr.log localtunnel.log

# Tunnel #2: Serveo (serveo.net)
start_serveo_loop() {
    while true; do
        ssh -T ${SSH_KEY_ARG} \
            -o ServerAliveInterval=15 \
            -o ServerAliveCountMax=3 \
            -o ExitOnForwardFailure=yes \
            -o ConnectTimeout=12 \
            -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -R "${SUBDOMAIN}:80:localhost:${PORT}" serveo.net > serveo.log 2>&1
        sleep 4
    done
}
start_serveo_loop &
SERVEO_PID=$!

# Tunnel #3: Pinggy Port 443 (a.pinggy.io)
start_pinggy_loop() {
    while true; do
        ssh -T -p 443 ${SSH_KEY_ARG} \
            -o ServerAliveInterval=15 \
            -o ServerAliveCountMax=3 \
            -o ExitOnForwardFailure=yes \
            -o ConnectTimeout=12 \
            -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -R0:localhost:${PORT} a.pinggy.io > pinggy.log 2>&1
        sleep 4
    done
}
start_pinggy_loop &
PINGGY_PID=$!

# Tunnel #4: Localhost.run (nokey@localhost.run)
start_lhr_loop() {
    while true; do
        ssh -T \
            -o ServerAliveInterval=15 \
            -o ServerAliveCountMax=3 \
            -o ExitOnForwardFailure=yes \
            -o ConnectTimeout=12 \
            -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -R 80:localhost:${PORT} nokey@localhost.run > lhr.log 2>&1
        sleep 5
    done
}
start_lhr_loop &
LHR_PID=$!

# Tunnel #5: LocalTunnel Fixed Subdomain (https://bankfinanza.loca.lt)
if [ -f "finanza_tunnel.py" ]; then
    PORT="${PORT}" SUBDOMAIN="${SUBDOMAIN}" python finanza_tunnel.py > localtunnel.log 2>&1 &
    PY_TUNNEL_PID=$!
fi

# Cleanup trap when user presses Ctrl+C
cleanup() {
    echo ""
    echo "[SHUTDOWN] Stopping all 5 Finanza tunnels & backend supervisor..."
    kill "${BACKEND_PID}" "${SERVEO_PID}" "${PINGGY_PID}" "${LHR_PID}" "${PY_TUNNEL_PID}" "${DASH_PID}" 2>/dev/null || true
    pkill -f "finanza_tunnel.py" 2>/dev/null || true
    pkill -f "pagekite.py" 2>/dev/null || true
    pkill -f "serveo.net" 2>/dev/null || true
    pkill -f "localhost.run" 2>/dev/null || true
    pkill -f "pinggy.io" 2>/dev/null || true
    if command -v termux-wake-unlock >/dev/null 2>&1; then
        termux-wake-unlock
    fi
    exit 0
}
trap cleanup INT TERM

# Helper to print all 5 live URLs once PageKite configuration exists
print_5_tunnel_dashboard() {
    (
        # Wait until first-time PageKite wizard finishes creating ~/.pagekite.rc so we don't interrupt typing
        while [ ! -f "$HOME/.pagekite.rc" ]; do
            sleep 2
        done
        sleep 8
        SERVEO_URL=$(grep -i "Forwarding HTTP" serveo.log 2>/dev/null | grep -oE "https://[a-zA-Z0-9.-]+" | tail -n 1)
        if [ -z "${SERVEO_URL}" ]; then
            SERVEO_URL=$(grep -oE "https://[a-zA-Z0-9.-]+\.serveousercontent\.com" serveo.log 2>/dev/null | tail -n 1)
        fi
        PINGGY_URL=$(grep -oE "https://[a-zA-Z0-9.-]+\.(run\.pinggy-free\.link|free\.pinggy\.net|a\.pinggy\.link)" pinggy.log 2>/dev/null | tail -n 1)
        LHR_URL=$(grep -oE "https://[a-zA-Z0-9.-]+\.lhr\.life" lhr.log 2>/dev/null | tail -n 1)
        LOCA_URL=$(grep -oE "https://[a-zA-Z0-9.-]+\.loca\.lt" LIVE_URL.txt 2>/dev/null | tail -n 1)

        [ -z "${SERVEO_URL}" ] && SERVEO_URL="connecting (check serveo.log)..."
        [ -z "${PINGGY_URL}" ] && PINGGY_URL="connecting (check pinggy.log)..."
        [ -z "${LHR_URL}" ] && LHR_URL="connecting (check lhr.log)..."
        [ -z "${LOCA_URL}" ] && LOCA_URL="https://${SUBDOMAIN}.loca.lt (check localtunnel.log)"

        echo ""
        echo "********************************************************************"
        echo "  ALL 5 FINANZA PUBLIC HTTPS TUNNELS ACTIVE:"
        echo "  1) PageKite (Fixed):    https://${SUBDOMAIN}.pagekite.me"
        echo "  2) Serveo (Zero-Wait):  ${SERVEO_URL}"
        echo "  3) Pinggy (Zero-Warn):  ${PINGGY_URL}"
        echo "  4) Localhost.run:       ${LHR_URL}"
        echo "  5) LocalTunnel (Fixed): ${LOCA_URL}"
        if [ -n "${PUB_IP}" ]; then
            echo "     (LocalTunnel 1-Time Password if asked: ${PUB_IP})"
        fi
        echo "********************************************************************"
        echo ""
    ) &
    DASH_PID=$!
}

print_5_tunnel_dashboard

# 7. Tunnel #1: PageKite (https://bankfinanza.pagekite.me) in foreground (supports interactive 1st-time setup)
ensure_pagekite() {
    if [ ! -f "pagekite.py" ]; then
        echo "[PAGEKITE] Downloading PageKite pure-Python client..."
        curl -sSL "https://pagekite.net/pk/pagekite.py" -o pagekite.py || return 1
        chmod +x pagekite.py 2>/dev/null || true
    fi
    return 0
}

while true; do
    if ensure_pagekite; then
        echo "============================================================"
        echo "  STARTING #1 PAGEKITE: https://${SUBDOMAIN}.pagekite.me"
        echo "  (While #2 Serveo, #3 Pinggy, #4 LHR, #5 LocalTunnel run in background)"
        echo "============================================================"
        if [ ! -f "$HOME/.pagekite.rc" ]; then
            echo "[FIRST-TIME SETUP] Answer PageKite's 2 quick prompts below:"
            echo "  1) 'Use the PageKite.net service? [Y/n]' -> Type Y and press Enter"
            echo "  2) 'What is your e-mail address?'        -> Enter your email and press Enter"
            echo ""
        fi
        python pagekite.py "${PORT}" "${SUBDOMAIN}.pagekite.me"
    fi
    echo "[PAGEKITE] Reconnecting https://${SUBDOMAIN}.pagekite.me in 5 seconds..."
    sleep 5
done
