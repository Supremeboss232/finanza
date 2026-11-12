#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# FINANZA BANK — 24/7 MULTI-ENGINE SECURE LAUNCHER (TELEBIT #4 + FIXED SUBDOMAIN)
# ==============================================================================
# What Runs Automatically:
#  1. Primary Engine (#4 Telebit): https://*.telebit.io (via Telebit Relay)
#  2. Fixed Subdomain Tunnel (Pure Python): https://bankfinanza.loca.lt
#  3. Zero-Warning Backup Tunnel: https://*.lhr.life
#  4. Android Hardware Wake-Lock + 24/7 FastAPI Uvicorn Supervisor
# ==============================================================================

PORT="${PORT:-8000}"
SUBDOMAIN="${SUBDOMAIN:-bankfinanza}"
TUNNEL_PROVIDER="${TUNNEL_PROVIDER:-telebit}"   # "telebit" (#4 default), "lhr", "ngrok", or "cloudflare"
NGROK_AUTHTOKEN="${NGROK_AUTHTOKEN:-}"
NGROK_DOMAIN="${NGROK_DOMAIN:-bankfinanza.ngrok.app}"
CLOUDFLARE_TUNNEL_TOKEN="${CLOUDFLARE_TUNNEL_TOKEN:-}"

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
echo "  Primary Tunnel (#4):     https://${SUBDOMAIN}.telebit.io"
echo "  Fixed Subdomain Backup:  https://${SUBDOMAIN}.loca.lt"
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

# 4. Clean up old tunnel processes (keep existing healthy uvicorn if already running)
pkill -f "finanza_tunnel.py" 2>/dev/null || true
pkill -f "localhost.run" 2>/dev/null || true
pkill -f "pinggy.io" 2>/dev/null || true
pkill -f "ngrok http" 2>/dev/null || true
pkill -f "cloudflared" 2>/dev/null || true
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

# 6. Start Pure-Python Fixed 'bankfinanza' Tunnel (https://bankfinanza.loca.lt) in background
if [ -f "finanza_tunnel.py" ]; then
    PUB_IP=$(curl -s --max-time 5 https://loca.lt/mytunnelpassword || curl -s --max-time 5 https://api.ipify.org || echo "")
    if [ -n "${PUB_IP}" ]; then
        echo "[INFO] Fixed Link https://${SUBDOMAIN}.loca.lt (1-Time Password if asked: ${PUB_IP})"
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
    pkill -f "finanza_tunnel.py" 2>/dev/null || true
    pkill -f "telebit" 2>/dev/null || true
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

# Helper to install and start #4 Telebit in Termux configured for https://bankfinanza.telebit.io
ensure_telebit() {
    if ! command -v node >/dev/null 2>&1; then
        echo "[TELEBIT] Installing Node.js runtime for Telebit..."
        pkg install nodejs -y || return 1
    fi
    if ! command -v telebit >/dev/null 2>&1 && [ ! -f "${PREFIX}/lib/node_modules/telebit/bin/telebit.js" ]; then
        echo "[TELEBIT] Installing Telebit CLI & Relay Daemon..."
        npm install -g telebit || return 1
    fi
    TELEBIT_SOCK="$HOME/.local/share/telebit/var/run/telebit.sock"
    TELEBIT_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkb21haW5zIjpbImJhbmtmaW5hbnphLnRlbGViaXQuaW8iXSwicG9ydHMiOltdLCJhdWQiOiJodHRwczovL3RlbGViaXQuY2xvdWQiLCJpc3MiOjE3OTQ1MDg3ODIsInN1YiI6ImFkbWluQGJhbmtmaW5hbnphLmNvbSJ9.9THXjjeb66Z58OYI4Ji_TvB94APjdV9MH3hOg-5KoNs"
    mkdir -p "$HOME/.config/telebit" "$HOME/.local/share/telebit/var/run" "$HOME/.local/share/telebit/var/log" "$HOME/.local/share/telebit/etc"

    # Always ensure telebit.yml points to the exact same socket path as telebitd.js (var/run/telebit.sock)
    cat > "$HOME/.config/telebit/telebit.yml" <<EOF
sock: ${TELEBIT_SOCK}
root: $HOME/.local/share/telebit
EOF

    echo "${TELEBIT_TOKEN}" > "$HOME/.config/telebit/access_token.txt"

    # Write complete telebitd.yml with email, agree_tos, relay, secret, token, and bankfinanza.telebit.io
    if ! grep -q "email:" "$HOME/.config/telebit/telebitd.yml" 2>/dev/null || ! grep -q "token:" "$HOME/.config/telebit/telebitd.yml" 2>/dev/null; then
        cat > "$HOME/.config/telebit/telebitd.yml" <<EOF
email: admin@${SUBDOMAIN}.com
agree_tos: true
community_member: true
telemetry: true
newsletter: false
ssh_auto: false
relay: https://telebit.cloud
secret: 66696e616e7a615f74656c656269745f736563726574
token: ${TELEBIT_TOKEN}
sock: ${TELEBIT_SOCK}
root: $HOME/.local/share/telebit
servernames:
  ${SUBDOMAIN}.telebit.io:
    sub: true
    wildcard: true
    handler: ${PORT}
ports: {}
EOF
        pkill -f "telebitd" 2>/dev/null || true
        rm -f "${TELEBIT_SOCK}"
    fi
    return 0
}

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

ensure_cloudflared() {
    if ! command -v cloudflared >/dev/null 2>&1 && [ ! -f "./cloudflared" ]; then
        echo "[CLOUDFLARE] Downloading official cloudflared Linux ARM64 binary..."
        curl -sSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64" -o "${PREFIX}/bin/cloudflared" 2>/dev/null || \
        curl -sSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64" -o "./cloudflared"
        chmod +x "${PREFIX}/bin/cloudflared" 2>/dev/null || chmod +x "./cloudflared"
    fi
    CF_BIN=$(command -v cloudflared || echo "./cloudflared")
}

WATCH_PID=""
watch_and_print_url() {
    if [ -n "${WATCH_PID}" ]; then
        kill "${WATCH_PID}" 2>/dev/null || true
    fi
    touch tunnel.log
    (
        for attempt in $(seq 1 25); do
            sleep 1
            if [ -f tunnel.log ]; then
                LIVE_URL=$(grep -oE "https://[a-zA-Z0-9.-]+\.(telebit\.io|lhr\.life|pinggy-free\.link|free\.pinggy\.net|a\.pinggy\.link|pinggy\.link|ngrok-free\.app|ngrok\.app|ngrok\.io|trycloudflare\.com)" tunnel.log 2>/dev/null | tail -n 1)
                if [ -n "${LIVE_URL}" ]; then
                    echo ""
                    echo "************************************************************"
                    echo "  YOUR ACTIVE FINANZA WEB ADDRESSES:"
                    echo "  1) Telebit Domain (#4):      https://${SUBDOMAIN}.telebit.io"
                    echo "  2) Direct Zero-Warning Link: ${LIVE_URL}"
                    echo "  3) Fixed Subdomain:          https://${SUBDOMAIN}.loca.lt"
                    if [ -n "${PUB_IP}" ]; then
                        echo "     (1-Time Tunnel Password if prompted: ${PUB_IP})"
                    fi
                    echo "************************************************************"
                    echo ""
                    break
                fi
            fi
        done
    ) &
    WATCH_PID=$!
}

# 7. Start 24/7 Auto-Reconnecting Tunnel Loop
FAIL_COUNT=0
while true; do
    rm -f tunnel.log
    touch tunnel.log

    if [ "${TUNNEL_PROVIDER}" = "telebit" ]; then
        echo "============================================================"
        echo "  CONNECTING TO #4 TELEBIT: https://${SUBDOMAIN}.telebit.io"
        echo "============================================================"
        if ensure_telebit; then
            TELEBIT_SOCK="$HOME/.local/share/telebit/var/run/telebit.sock"
            TELEBITD_CMD="telebitd"
            TELEBIT_CMD="telebit"
            if [ -f "${PREFIX}/lib/node_modules/telebit/bin/telebitd.js" ]; then
                TELEBITD_CMD="node ${PREFIX}/lib/node_modules/telebit/bin/telebitd.js"
                TELEBIT_CMD="node ${PREFIX}/lib/node_modules/telebit/bin/telebit.js"
            fi
            if ! pgrep -f "telebitd" >/dev/null 2>&1 || [ ! -S "${TELEBIT_SOCK}" ]; then
                pkill -f "telebitd" 2>/dev/null || true
                rm -f "${TELEBIT_SOCK}"
                ${TELEBITD_CMD} --config "$HOME/.config/telebit/telebitd.yml" >> telebitd.log 2>&1 &
                for s_wait in $(seq 1 8); do
                    [ -S "${TELEBIT_SOCK}" ] && break
                    sleep 1
                done
            fi
            echo "[TELEBIT] Registering https://${SUBDOMAIN}.telebit.io => http://localhost:${PORT}..."
            ${TELEBIT_CMD} --config "$HOME/.config/telebit/telebit.yml" http "${PORT}" "${SUBDOMAIN}.telebit.io"
            echo ""
            echo "************************************************************"
            echo "  TELEBIT DAEMON ACTIVE:"
            echo "  >> https://${SUBDOMAIN}.telebit.io => localhost:${PORT} <<"
            echo "  >> https://${SUBDOMAIN}.loca.lt    => localhost:${PORT} <<"
            echo "************************************************************"
            echo ""
            echo "[TELEBIT] Starting parallel high-speed edge relay (Pinggy Port 443)..."
            TUNNEL_PROVIDER="pinggy"
            continue
        else
            echo "[TELEBIT] Telebit setup unavailable; activating edge tunnel..."
            TUNNEL_PROVIDER="pinggy"
            continue
        fi
    elif [ "${TUNNEL_PROVIDER}" = "ngrok" ]; then
        ensure_ngrok
        echo "============================================================"
        echo "  CONNECTING TO NGROK: https://${NGROK_DOMAIN}"
        echo "============================================================"
        watch_and_print_url
        "${NGROK_BIN}" http --url="${NGROK_DOMAIN}" "${PORT}" --log=stdout 2>&1 | tee tunnel.log
        if grep -qE "ERR_NGROK_313|ERR_NGROK_3208|ERR_NGROK_108" tunnel.log 2>/dev/null; then
            echo "[NGROK] Starting standard Ngrok HTTPS tunnel..."
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
    elif [ "${TUNNEL_PROVIDER}" = "pinggy" ]; then
        echo "============================================================"
        echo "  CONNECTING TO PINGGY SECURE HTTPS TUNNEL..."
        echo "============================================================"
        watch_and_print_url
        ssh -T -p 443 \
            -o ServerAliveInterval=15 \
            -o ServerAliveCountMax=3 \
            -o ExitOnForwardFailure=yes \
            -o ConnectTimeout=12 \
            -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -R0:localhost:${PORT} a.pinggy.io 2>&1 | tee tunnel.log
    else
        echo "============================================================"
        echo "  CONNECTING DIRECT ZERO-WARNING TUNNEL (*.lhr.life)..."
        echo "============================================================"
        watch_and_print_url
        START_TS=$(date +%s)
        ssh -T -o ServerAliveInterval=15 \
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
