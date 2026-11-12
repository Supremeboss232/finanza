#!/usr/bin/env python3
"""
Finanza Pure-Python Fixed-Subdomain Tunnel Client (https://bankfinanza.loca.lt)
Allocates the fixed 'bankfinanza' subdomain on localtunnel.me and bridges
incoming TLS traffic directly to local FastAPI (127.0.0.1:8000) using asyncio.
Requires ZERO external binaries (no nodejs, no npm, no ssh).
"""

import asyncio
import json
import os
import sys
import urllib.request

LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = int(os.environ.get("PORT", "8000"))
SUBDOMAIN = os.environ.get("SUBDOMAIN", "bankfinanza")
TUNNEL_SERVER = "localtunnel.me"


def request_subdomain(subdomain: str) -> dict:
    url = f"https://{TUNNEL_SERVER}/{subdomain}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Finanza-Bank-Tunnel/2.0"},
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))


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


async def tunnel_worker(remote_host: str, remote_port: int, local_host: str, local_port: int):
    """Maintain a persistent socket slot to the tunnel server and bridge to local FastAPI."""
    while True:
        remote_reader = None
        remote_writer = None
        try:
            remote_reader, remote_writer = await asyncio.wait_for(
                asyncio.open_connection(remote_host, remote_port),
                timeout=12.0,
            )
            # Wait for the first chunk of incoming HTTP request from the public internet
            first_chunk = await remote_reader.read(65536)
            if not first_chunk:
                remote_writer.close()
                await asyncio.sleep(0.5)
                continue

            # Connect to local FastAPI server
            local_reader, local_writer = await asyncio.wait_for(
                asyncio.open_connection(local_host, local_port),
                timeout=5.0,
            )
            local_writer.write(first_chunk)
            await local_writer.drain()

            # Bridge remaining bytes in both directions until connection closes
            await asyncio.gather(
                pipe_stream(remote_reader, local_writer),
                pipe_stream(local_reader, remote_writer),
            )
        except asyncio.CancelledError:
            if remote_writer:
                try:
                    remote_writer.close()
                except Exception:
                    pass
            break
        except Exception:
            await asyncio.sleep(1.5)


async def run_tunnel_forever():
    while True:
        try:
            info = await asyncio.to_thread(request_subdomain, SUBDOMAIN)
            allocated_id = info.get("id", "")
            remote_port = int(info["port"])
            max_conn = min(int(info.get("max_conn_count", 4)), 6)
            public_url = info.get("url", f"https://{allocated_id}.loca.lt")

            # If 'bankfinanza' is still cooling down from a previous disconnect, wait 6s and retry once
            if allocated_id != SUBDOMAIN:
                await asyncio.sleep(6)
                info2 = await asyncio.to_thread(request_subdomain, SUBDOMAIN)
                if info2.get("id") == SUBDOMAIN:
                    info = info2
                    allocated_id = info["id"]
                    remote_port = int(info["port"])
                    max_conn = min(int(info.get("max_conn_count", 4)), 6)
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

            workers = [
                asyncio.create_task(
                    tunnel_worker(TUNNEL_SERVER, remote_port, LOCAL_HOST, LOCAL_PORT)
                )
                for _ in range(max_conn)
            ]
            # Keep workers running; refresh tunnel lease if all workers exit
            await asyncio.gather(*workers)
        except Exception as exc:
            print(f"[FINANZA-TUNNEL] Reconnecting fixed tunnel ({exc})...", flush=True)
            await asyncio.sleep(4)


if __name__ == "__main__":
    try:
        asyncio.run(run_tunnel_forever())
    except KeyboardInterrupt:
        sys.exit(0)
