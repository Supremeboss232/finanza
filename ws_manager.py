from typing import List, Dict, Set, Optional
from fastapi import WebSocket
import asyncio
import json


class WebSocketManager:
    """
    Enhanced WebSocket Manager with subscription support.
    
    Supports:
    - Broadcast to all connections
    - Send to specific channels (user, device, operation type)
    - Per-connection subscriptions
    - Automatic cleanup of dead connections
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[int, List[WebSocket]] = {}  # user_id -> connections
        self.device_connections: Dict[str, List[WebSocket]] = {}  # device_id -> connections
        self.subscriptions: Dict[WebSocket, Set[str]] = {}  # WebSocket -> set of channel names
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: Optional[int] = None, device_id: Optional[str] = None):
        """Connect WebSocket and optionally subscribe to channels"""
        await websocket.accept()
        
        async with self.lock:
            self.active_connections.append(websocket)
            self.subscriptions[websocket] = set()
            
            if user_id:
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = []
                self.user_connections[user_id].append(websocket)
                self.subscriptions[websocket].add(f"user:{user_id}")
            
            if device_id:
                if device_id not in self.device_connections:
                    self.device_connections[device_id] = []
                self.device_connections[device_id].append(websocket)
                self.subscriptions[websocket].add(f"device:{device_id}")

    async def disconnect(self, websocket: WebSocket):
        """Disconnect WebSocket and remove from all channels"""
        async with self.lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            
            # Remove from user connections
            for user_id, conns in list(self.user_connections.items()):
                if websocket in conns:
                    conns.remove(websocket)
                    if not conns:
                        del self.user_connections[user_id]
            
            # Remove from device connections
            for device_id, conns in list(self.device_connections.items()):
                if websocket in conns:
                    conns.remove(websocket)
                    if not conns:
                        del self.device_connections[device_id]
            
            # Remove subscriptions
            if websocket in self.subscriptions:
                del self.subscriptions[websocket]

    async def subscribe(self, websocket: WebSocket, channel: str):
        """Subscribe websocket to specific channel"""
        async with self.lock:
            if websocket in self.subscriptions:
                self.subscriptions[websocket].add(channel)

    async def broadcast(self, message: str):
        """Send message to all connected clients"""
        async with self.lock:
            conns = list(self.active_connections)
        
        for conn in conns:
            try:
                await conn.send_text(message)
            except Exception:
                await self.disconnect(conn)

    async def broadcast_to_channel(self, channel: str, message: str):
        """Send message to all subscribers of a channel"""
        async with self.lock:
            subscribers = []
            for ws, subs in self.subscriptions.items():
                if channel in subs:
                    subscribers.append(ws)
        
        for ws in subscribers:
            try:
                await ws.send_text(message)
            except Exception:
                await self.disconnect(ws)

    async def send_to_user(self, user_id: int, message: str):
        """Send message to all connections of a user"""
        async with self.lock:
            conns = self.user_connections.get(user_id, [])
            conns = list(conns)
        
        for conn in conns:
            try:
                await conn.send_text(message)
            except Exception:
                await self.disconnect(conn)

    async def send_to_users(self, user_ids: List[int], message: str):
        """Send message to multiple users"""
        for user_id in user_ids:
            await self.send_to_user(user_id, message)

    async def send_to_device(self, device_id: str, message: str):
        """Send message to all connections from a device"""
        async with self.lock:
            conns = self.device_connections.get(device_id, [])
            conns = list(conns)
        
        for conn in conns:
            try:
                await conn.send_text(message)
            except Exception:
                await self.disconnect(conn)

    async def send_json(self, message: Dict, channel: Optional[str] = None, user_id: Optional[int] = None, device_id: Optional[str] = None):
        """Send JSON message to appropriate targets"""
        json_str = json.dumps(message)
        
        if channel:
            await self.broadcast_to_channel(channel, json_str)
        elif user_id:
            await self.send_to_user(user_id, json_str)
        elif device_id:
            await self.send_to_device(device_id, json_str)
        else:
            await self.broadcast(json_str)

    def get_connection_count(self) -> int:
        """Get total active connections"""
        return len(self.active_connections)

    def get_user_connection_count(self, user_id: int) -> int:
        """Get connection count for a user"""
        return len(self.user_connections.get(user_id, []))

    def get_status(self) -> Dict:
        """Get manager status"""
        return {
            "total_connections": len(self.active_connections),
            "users": len(self.user_connections),
            "devices": len(self.device_connections),
            "channels": sum(len(subs) for subs in self.subscriptions.values())
        }


manager = WebSocketManager()
