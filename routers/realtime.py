from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ws_manager import manager
import auth_utils
from database import SessionLocal
import crud
from http import cookies as http_cookies
import json

realtime_router = APIRouter()


async def _resolve_user_from_websocket(websocket: WebSocket):
    """Attempt to resolve an authenticated user from WS cookies or query param 'token'."""
    # Try query param token first
    token = websocket.query_params.get('token')

    # Try cookie header
    if not token:
        cookie_header = websocket.headers.get('cookie', '')
        if cookie_header:
            c = http_cookies.SimpleCookie()
            try:
                c.load(cookie_header)
                m = c.get('access_token')
                if m:
                    token = m.value
            except Exception:
                token = None

    if not token:
        return None

    email = auth_utils.decode_access_token(token)
    if not email:
        return None

    # Retrieve user from DB
    try:
        async with SessionLocal() as db:
            user = await crud.get_user_by_email(db, email=email)
            return user
    except Exception:
        return None


@realtime_router.websocket("/ws/users")
async def users_ws(websocket: WebSocket):
    # Validate user before accepting connection
    user = await _resolve_user_from_websocket(websocket)
    if not user:
        # politely refuse connection
        await websocket.accept()
        await websocket.send_text(json.dumps({"error": "unauthorized"}))
        await websocket.close(code=1008)
        return

    # Connection accepted and authenticated
    await manager.connect(websocket)
    try:
        # Send initial presence message
        await websocket.send_text(json.dumps({"event": "connected", "user_id": user.id}))
        while True:
            data = await websocket.receive_text()
            # Simple echo ack for client pings
            await websocket.send_text(f"ack:{data}")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
