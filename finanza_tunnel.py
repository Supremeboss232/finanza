#!/usr/bin/env python3
"""
Finanza Pure-Python Fixed-Subdomain Tunnel Client (https://bankfinanza.loca.lt)
Allocates the fixed 'bankfinanza' subdomain on localtunnel.me and bridges
incoming TLS traffic directly to local FastAPI (127.0.0.1:8000) using asyncio.
Includes TCP keepalive + active end-to-end 503 watchdog recovery for Android NAT.
"""

import asyncio
import json
import os
import socket
import sys
import urllib.error
import urllib.request

LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = int(os.environ.get("PORT", "8000"))
SUBDOMAIN = os.environ.get("SUBDOMAIN", "bankfinanza")
TUNNEL_SERVER = "localtunnel.me"


def request_subdomain(subdomain: str) -> dict:
    url = f"https://{TUNNEL_SERVER}/{subdomain}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "localtunnel"},
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))


def check_tunnel_live(public_url: str) -> bool:
    """Verify the public .loca.lt endpoint is actively routing (not 503/502/404)."""
    target = f"{public_url.rstrip('/')}/health"
    req = urllib.request.Request(
        target,
        headers={
            "Bypass-Tunnel-Reminder": "true",
            "User-Agent": "Finanza-Tunnel-Watchdog/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return 200 <= resp.status < 500
    except urllib.error.HTTPError as e:
        # 503 Tunnel Unavailable / 502 Bad Gateway / 404 Not Found means tunnel dropped
        if e.code in (404, 502, 503, 504):
            return False
        return True
    except Exception:
        return True  # Transient client-side network error; let socket layer handle


def enable_tcp_keepalive(writer: asyncio.StreamWriter) -> None:
    try:
        sock = writer.get_extra_info("socket")
        if sock is not None:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            if hasattr(socket, "TCP_KEEPIDLE"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 20)
            if hasattr(socket, "TCP_KEEPINTVL"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
            if hasattr(socket, "TCP_KEEPCNT"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
    except Exception:
        pass


async def pipe_stream(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def tunnel_worker(
    remote_host: str,
    remote_port: int,
    local_host: str,
    local_port: int,
    stop_event: asyncio.Event,
):
    """Maintain a persistent socket slot to the tunnel server and bridge to local FastAPI."""
    consecutive_conn_errors = 0
    while not stop_event.is_set():
        remote_writer = None
        try:
            remote_reader, remote_writer = await asyncio.wait_for(
                asyncio.open_connection(remote_host, remote_port),
                timeout=12.0,
            )
            enable_tcp_keepalive(remote_writer)
            consecutive_conn_errors = 0

            # Recycle idle half-open sockets every 90s if no traffic arrived
            first_chunk = await asyncio.wait_for(remote_reader.read(65536), timeout=90.0)
            if not first_chunk:
                remote_writer.close()
                await asyncio.sleep(0.3)
                continue

            local_reader, local_writer = await asyncio.wait_for(
                asyncio.open_connection(local_host, local_port),
                timeout=5.0,
            )
            local_writer.write(first_chunk)
            await local_writer.drain()

            await asyncio.gather(
                pipe_stream(remote_reader, local_writer),
                pipe_stream(local_reader, remote_writer),
            )
        except asyncio.TimeoutError:
            if remote_writer:
                try:
                    remote_writer.close()
                except Exception:
                    pass
            await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            if remote_writer:
                try:
                    remote_writer.close()
                except Exception:
                    pass
            break
        except Exception:
            consecutive_conn_errors += 1
            if remote_writer:
                try:
                    remote_writer.close()
                except Exception:
                    pass
            if consecutive_conn_errors >= 4:
                # Port likely expired on localtunnel.me; trigger full re-registration
                stop_event.set()
                break
            await asyncio.sleep(1.5)


async def tunnel_watchdog(public_url: str, allocated_id: str, stop_event: asyncio.Event):
    """Ensure https://bankfinanza.loca.lt stays reachable; trigger reset on 503."""
    await asyncio.sleep(8)
    bad_checks = 0
    while not stop_event.is_set():
        is_live = await asyncio.to_thread(check_tunnel_live, public_url)
        if not is_live:
            bad_checks += 1
            if bad_checks >= 2:
                print(f"[FINANZA-TUNNEL] {public_url} returned 503; re-registering...", flush=True)
                stop_event.set()
                break
        else:
            bad_checks = 0

        # If we temporarily fell back to a random ID while waiting for old slot to release, retry claiming SUBDOMAIN
        if allocated_id != SUBDOMAIN:
            try:
                probe = await asyncio.to_thread(request_subdomain, SUBDOMAIN)
                if probe.get("id") == SUBDOMAIN:
                    print(f"[FINANZA-TUNNEL] Reclaiming fixed subdomain {SUBDOMAIN}.loca.lt...", flush=True)
                    stop_event.set()
                    break
            except Exception:
                pass

        await asyncio.sleep(25)


async def claim_preferred_subdomain():
    """Retry up to 4 times so an expiring previous socket slot doesn't force a random URL."""
    info = await asyncio.to_thread(request_subdomain, SUBDOMAIN)
    for wait_sec in (4, 6, 8):
        if info.get("id") == SUBDOMAIN:
            return info
        await asyncio.sleep(wait_sec)
        info2 = await asyncio.to_thread(request_subdomain, SUBDOMAIN)
        if info2.get("id") == SUBDOMAIN:
            return info2
        info = info2
    return info


async def run_tunnel_forever():
    logged_err = False
    while True:
        try:
            info = await claim_preferred_subdomain()
            logged_err = False
            allocated_id = info.get("id", "")
            remote_port = int(info["port"])
            max_conn = max(2, min(int(info.get("max_conn_count", 4)), 6))
            public_url = info.get("url", f"https://{allocated_id}.loca.lt")

            try:
                with open("LIVE_URL.txt", "w", encoding="utf-8") as f:
                    f.write(public_url + "\n")
            except Exception:
                pass

            print("\n************************************************************", flush=True)
            print("  FIXED SUBDOMAIN TUNNEL ACTIVE:", flush=True)
            print(f"  >> {public_url} <<", flush=True)
            print("************************************************************\n", flush=True)

            stop_event = asyncio.Event()
            tasks = [
                asyncio.create_task(
                    tunnel_worker(TUNNEL_SERVER, remote_port, LOCAL_HOST, LOCAL_PORT, stop_event)
                )
                for _ in range(max_conn)
            ]
            tasks.append(asyncio.create_task(tunnel_watchdog(public_url, allocated_id, stop_event)))

            await stop_event.wait()
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(2)
        except Exception as e:
            if not logged_err:
                print(f"[FINANZA-TUNNEL] Retrying connection ({e})...", flush=True)
                logged_err = True
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(run_tunnel_forever())
    except KeyboardInterrupt:
        sys.exit(0)
