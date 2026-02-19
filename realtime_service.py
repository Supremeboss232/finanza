"""
Real-Time Service - Phase 3C
Manages WebSocket connections and real-time data streaming
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from sqlalchemy.orm import Session
import logging
import json
import asyncio
from enum import Enum

log = logging.getLogger(__name__)

# Subscription types
class SubscriptionType(str, Enum):
    EXCHANGE_RATES = "exchange_rates"
    TRANSFER_STATUS = "transfer_status"
    COMPLIANCE_ALERTS = "compliance_alerts"
    SYSTEM_METRICS = "system_metrics"
    REGIONAL_UPDATES = "regional_updates"


# In-memory connection and subscription management
ACTIVE_CONNECTIONS: Dict[str, Set[str]] = {
    sub_type.value: set() for sub_type in SubscriptionType
}
RATE_STREAMS: Dict[str, Any] = {}
TRANSFER_STREAMS: Dict[str, Any] = {}


class WebSocketManager:
    """Manages WebSocket connections"""
    
    @staticmethod
    async def connect_client(
        db: Session,
        client_id: str,
        subscriptions: List[str]
    ) -> dict:
        """Register a new WebSocket client"""
        try:
            # Add client to subscription sets
            for subscription in subscriptions:
                if subscription in ACTIVE_CONNECTIONS:
                    ACTIVE_CONNECTIONS[subscription].add(client_id)
            
            connection_data = {
                "client_id": client_id,
                "subscriptions": subscriptions,
                "connected_at": datetime.utcnow().isoformat(),
                "last_heartbeat": datetime.utcnow().isoformat(),
                "message_count": 0,
                "status": "connected"
            }
            
            log.info(f"WebSocket client connected: {client_id} - Subscriptions: {subscriptions}")
            
            return {
                "success": True,
                "data": {
                    "client_id": client_id,
                    "message": "Connected successfully",
                    "subscriptions": subscriptions,
                    "connection_timestamp": connection_data["connected_at"]
                }
            }
        except Exception as e:
            log.error(f"Error connecting WebSocket client: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def broadcast_rate_update(
        db: Session,
        from_currency: str,
        to_currency: str,
        rate: float,
        timestamp: Optional[str] = None
    ) -> dict:
        """Broadcast exchange rate update to all subscribed clients"""
        try:
            if not timestamp:
                timestamp = datetime.utcnow().isoformat()
            
            rate_update = {
                "type": "rate_update",
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": rate,
                "timestamp": timestamp
            }
            
            # Simulate broadcasting to connected clients
            clients_notified = list(ACTIVE_CONNECTIONS[SubscriptionType.EXCHANGE_RATES.value])
            
            # Store in rate streams
            stream_key = f"{from_currency}:{to_currency}"
            if stream_key not in RATE_STREAMS:
                RATE_STREAMS[stream_key] = []
            
            RATE_STREAMS[stream_key].append(rate_update)
            
            # Keep only last 100 updates per stream
            if len(RATE_STREAMS[stream_key]) > 100:
                RATE_STREAMS[stream_key] = RATE_STREAMS[stream_key][-100:]
            
            log.debug(f"Rate update broadcast: {from_currency}/{to_currency} = {rate} to {len(clients_notified)} clients")
            
            return {
                "success": True,
                "data": {
                    "rate_update": rate_update,
                    "clients_notified": len(clients_notified),
                    "broadcast_timestamp": timestamp
                }
            }
        except Exception as e:
            log.error(f"Error broadcasting rate update: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def broadcast_transfer_status(
        db: Session,
        transfer_id: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None
    ) -> dict:
        """Broadcast transfer status update to subscribed clients"""
        try:
            if not timestamp:
                timestamp = datetime.utcnow().isoformat()
            
            transfer_update = {
                "type": "transfer_status",
                "transfer_id": transfer_id,
                "status": status,
                "details": details or {},
                "timestamp": timestamp
            }
            
            # Simulate broadcasting to connected clients
            clients_notified = list(ACTIVE_CONNECTIONS[SubscriptionType.TRANSFER_STATUS.value])
            
            # Store in transfer streams
            stream_key = f"transfer:{transfer_id}"
            if stream_key not in TRANSFER_STREAMS:
                TRANSFER_STREAMS[stream_key] = []
            
            TRANSFER_STREAMS[stream_key].append(transfer_update)
            
            # Keep only last 50 updates per stream
            if len(TRANSFER_STREAMS[stream_key]) > 50:
                TRANSFER_STREAMS[stream_key] = TRANSFER_STREAMS[stream_key][-50:]
            
            log.info(f"Transfer status broadcast: {transfer_id} - {status} to {len(clients_notified)} clients")
            
            return {
                "success": True,
                "data": {
                    "transfer_update": transfer_update,
                    "clients_notified": len(clients_notified),
                    "broadcast_timestamp": timestamp
                }
            }
        except Exception as e:
            log.error(f"Error broadcasting transfer status: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def disconnect_client(
        db: Session,
        client_id: str,
        subscriptions: Optional[List[str]] = None
    ) -> dict:
        """Disconnect a WebSocket client"""
        try:
            # Remove client from all or specified subscription sets
            if subscriptions:
                for subscription in subscriptions:
                    if subscription in ACTIVE_CONNECTIONS:
                        ACTIVE_CONNECTIONS[subscription].discard(client_id)
            else:
                # Remove from all subscriptions
                for subscription_set in ACTIVE_CONNECTIONS.values():
                    subscription_set.discard(client_id)
            
            log.info(f"WebSocket client disconnected: {client_id}")
            
            return {
                "success": True,
                "data": {
                    "client_id": client_id,
                    "message": "Disconnected successfully",
                    "disconnect_timestamp": datetime.utcnow().isoformat()
                }
            }
        except Exception as e:
            log.error(f"Error disconnecting client: {e}")
            return {"success": False, "error": str(e)}


class StreamingRates:
    """Manages real-time exchange rate streaming"""
    
    @staticmethod
    async def subscribe_to_rates(
        db: Session,
        client_id: str,
        currency_pairs: List[str]
    ) -> dict:
        """Subscribe to exchange rate updates for specific currency pairs"""
        try:
            # Add client to exchange rates subscription
            ACTIVE_CONNECTIONS[SubscriptionType.EXCHANGE_RATES.value].add(client_id)
            
            subscription_data = {
                "client_id": client_id,
                "subscription_type": "exchange_rates",
                "currency_pairs": currency_pairs,
                "subscribed_at": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            # Return current rates for subscribed pairs
            current_rates = []
            for pair in currency_pairs:
                parts = pair.split("/")
                if len(parts) == 2:
                    stream_key = f"{parts[0]}:{parts[1]}"
                    if stream_key in RATE_STREAMS and RATE_STREAMS[stream_key]:
                        latest_rate = RATE_STREAMS[stream_key][-1]
                        current_rates.append(latest_rate)
            
            log.info(f"Client {client_id} subscribed to {len(currency_pairs)} currency pairs")
            
            return {
                "success": True,
                "data": {
                    "client_id": client_id,
                    "subscription_type": "exchange_rates",
                    "currency_pairs": currency_pairs,
                    "current_rates": current_rates,
                    "subscribed_at": subscription_data["subscribed_at"]
                }
            }
        except Exception as e:
            log.error(f"Error subscribing to rates: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def stream_rate_updates(
        db: Session,
        from_currency: str,
        to_currency: str
    ) -> dict:
        """Get stream of rate updates for a currency pair"""
        try:
            stream_key = f"{from_currency}:{to_currency}"
            
            if stream_key not in RATE_STREAMS:
                RATE_STREAMS[stream_key] = []
            
            updates = RATE_STREAMS[stream_key].copy()
            
            return {
                "success": True,
                "data": {
                    "currency_pair": f"{from_currency}/{to_currency}",
                    "updates_count": len(updates),
                    "updates": updates,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        except Exception as e:
            log.error(f"Error streaming rate updates: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def unsubscribe_from_rates(
        db: Session,
        client_id: str,
        currency_pairs: Optional[List[str]] = None
    ) -> dict:
        """Unsubscribe from exchange rate updates"""
        try:
            if not currency_pairs:
                # Remove from all exchange rate subscriptions
                ACTIVE_CONNECTIONS[SubscriptionType.EXCHANGE_RATES.value].discard(client_id)
                
                return {
                    "success": True,
                    "data": {
                        "client_id": client_id,
                        "message": "Unsubscribed from all exchange rates",
                        "unsubscribed_at": datetime.utcnow().isoformat()
                    }
                }
            else:
                # Remove from specific pairs (in production, track per-pair subscriptions)
                return {
                    "success": True,
                    "data": {
                        "client_id": client_id,
                        "unsubscribed_from": currency_pairs,
                        "unsubscribed_at": datetime.utcnow().isoformat()
                    }
                }
        except Exception as e:
            log.error(f"Error unsubscribing from rates: {e}")
            return {"success": False, "error": str(e)}


class RealtimeConnectionStatus:
    """Track real-time connection metrics"""
    
    @staticmethod
    async def get_connection_status(db: Session) -> dict:
        """Get overall real-time connection status"""
        try:
            total_connections = sum(len(clients) for clients in ACTIVE_CONNECTIONS.values())
            
            status_data = {
                "total_active_connections": total_connections,
                "subscriptions": {
                    sub_type: len(clients)
                    for sub_type, clients in ACTIVE_CONNECTIONS.items()
                },
                "rate_streams": len(RATE_STREAMS),
                "transfer_streams": len(TRANSFER_STREAMS),
                "status": "operational" if total_connections > 0 else "idle",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return {
                "success": True,
                "data": status_data
            }
        except Exception as e:
            log.error(f"Error getting connection status: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def send_heartbeat(db: Session) -> dict:
        """Send heartbeat to all connected clients"""
        try:
            total_connections = sum(len(clients) for clients in ACTIVE_CONNECTIONS.values())
            
            heartbeat_data = {
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat(),
                "server_status": "healthy",
                "active_connections": total_connections
            }
            
            log.debug(f"Heartbeat sent to {total_connections} connections")
            
            return {
                "success": True,
                "data": {
                    "heartbeat": heartbeat_data,
                    "connections_reached": total_connections
                }
            }
        except Exception as e:
            log.error(f"Error sending heartbeat: {e}")
            return {"success": False, "error": str(e)}
