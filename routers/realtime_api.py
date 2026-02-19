"""
Real-Time API Router - Phase 3C
Endpoints for WebSocket connections and streaming updates
"""

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging
import json

from deps import get_db
from realtime_service import (
    WebSocketManager,
    StreamingRates,
    RealtimeConnectionStatus,
    SubscriptionType
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/realtime", tags=["realtime"])


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time updates"""
    try:
        await websocket.accept()
        
        # Default subscriptions
        subscriptions = [
            SubscriptionType.EXCHANGE_RATES.value,
            SubscriptionType.TRANSFER_STATUS.value
        ]
        
        # Connect client
        result = await WebSocketManager.connect_client(db, client_id, subscriptions)
        
        if result["success"]:
            await websocket.send_json(result["data"])
        
        # Keep connection alive and handle messages
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
                elif message.get("type") == "subscribe":
                    subscription = message.get("subscription")
                    log.info(f"Client {client_id} subscribed to {subscription}")
                    
                elif message.get("type") == "unsubscribe":
                    subscription = message.get("subscription")
                    log.info(f"Client {client_id} unsubscribed from {subscription}")
        
        except Exception as e:
            log.error(f"WebSocket error for client {client_id}: {e}")
        
        finally:
            await WebSocketManager.disconnect_client(db, client_id, subscriptions)
    
    except Exception as e:
        log.error(f"Error in websocket endpoint: {e}")
        raise


@router.post("/subscribe/rates", summary="Subscribe to Exchange Rates")
async def subscribe_to_rates(
    client_id: str = Query(..., description="Client identifier"),
    currency_pairs: str = Query(..., description="Comma-separated currency pairs (e.g., USD/EUR,GBP/USD)"),
    db: Session = Depends(get_db)
):
    """Subscribe to real-time exchange rate updates"""
    try:
        pairs = [p.strip() for p in currency_pairs.split(",")]
        
        result = await StreamingRates.subscribe_to_rates(db, client_id, pairs)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error subscribing to rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rates/{from_currency}/{to_currency}/stream", summary="Stream Exchange Rates")
async def stream_exchange_rates(
    from_currency: str,
    to_currency: str,
    db: Session = Depends(get_db)
):
    """Get stream of exchange rate updates for a currency pair"""
    try:
        result = await StreamingRates.stream_rate_updates(db, from_currency, to_currency)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error streaming rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", summary="Get Real-Time Connection Status")
async def get_realtime_status(db: Session = Depends(get_db)):
    """Get current real-time connection status"""
    try:
        result = await RealtimeConnectionStatus.get_connection_status(db)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting realtime status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unsubscribe/rates", summary="Unsubscribe from Exchange Rates")
async def unsubscribe_from_rates(
    client_id: str = Query(..., description="Client identifier"),
    currency_pairs: Optional[str] = Query(None, description="Comma-separated currency pairs (optional)"),
    db: Session = Depends(get_db)
):
    """Unsubscribe from exchange rate updates"""
    try:
        pairs = None
        if currency_pairs:
            pairs = [p.strip() for p in currency_pairs.split(",")]
        
        result = await StreamingRates.unsubscribe_from_rates(db, client_id, pairs)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error unsubscribing from rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))
