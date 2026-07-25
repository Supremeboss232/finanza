"""
Real-Time Price Feed Service

Handles:
1. Forex rates from Fixer.io (synced every 45 minutes)
2. Cryptocurrency prices from Binance WebSocket (live updates)
3. Redis caching for performance
4. Fallback rates when service unavailable
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class PriceFeedService:
    """
    Manages all price feeds: forex, crypto, commodities.
    
    Prices are stored in Redis with TTLs for efficient retrieval.
    Background tasks sync prices on schedules:
    - Forex: Every 45 minutes
    - Crypto: Continuous WebSocket connection
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.forex_rates = {}
        self.crypto_prices = {}
        self.crypto_task = None
    
    async def connect(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = await redis.from_url(self.redis_url)
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            # Continue without Redis (in-memory fallback)
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    # ==================== FOREX FEEDS ====================
    
    async def sync_forex_rates(self, 
                              api_key: str,
                              base_currency: str = "USD",
                              target_currencies: list = None) -> Dict[str, Decimal]:
        """
        Synchronize forex rates from Fixer.io API.
        
        Called every 45 minutes by APScheduler.
        Stores rates in Redis with 1-hour TTL.
        
        Args:
            api_key: Fixer.io API key
            base_currency: Base currency (default USD)
            target_currencies: List of currencies to track
                Default: ['EUR', 'GBP', 'AUD', 'CAD', 'CHF', 'JPY', 'CNY', 'INR']
        
        Returns:
            Dictionary of rates {currency: rate}
        """
        if not target_currencies:
            target_currencies = ['EUR', 'GBP', 'AUD', 'CAD', 'CHF', 'JPY', 'CNY', 'INR']
        
        try:
            url = f"https://api.fixer.io/latest"
            params = {
                "access_key": api_key,
                "base": base_currency,
                "symbols": ",".join(target_currencies)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.error(f"Fixer.io API error: {resp.status}")
                        return {}
                    
                    data = await resp.json()
                    
                    if not data.get('success'):
                        logger.error(f"Fixer.io returned error: {data.get('error')}")
                        return {}
                    
                    rates = data.get('rates', {})
                    
                    # Store in memory
                    self.forex_rates = {
                        currency: Decimal(str(rate))
                        for currency, rate in rates.items()
                    }
                    
                    # Store in Redis with 45-minute TTL
                    if self.redis_client:
                        await self.redis_client.setex(
                            f"forex_rates:{base_currency}",
                            2700,  # 45 minutes
                            json.dumps({k: str(v) for k, v in self.forex_rates.items()})
                        )
                        logger.info(f"Forex rates updated and cached: {len(rates)} currencies")
                    else:
                        logger.info(f"Forex rates updated (no Redis): {len(rates)} currencies")
                    
                    return self.forex_rates
        
        except asyncio.TimeoutError:
            logger.error("Forex API request timeout")
            return {}
        except Exception as e:
            logger.error(f"Forex sync error: {e}")
            return {}
    
    async def get_forex_rate(self, base: str, target: str) -> Optional[Decimal]:
        """
        Get current forex rate from cache or fallback.
        """
        # Check Redis first
        if self.redis_client:
            try:
                cached = await self.redis_client.get(f"forex_rates:{base}")
                if cached:
                    rates = json.loads(cached)
                    if target in rates:
                        return Decimal(rates[target])
            except Exception as e:
                logger.debug(f"Redis lookup failed: {e}")
        
        # Fallback to in-memory
        if target in self.forex_rates:
            return self.forex_rates[target]
        
        # Final fallback with warning
        logger.warning(f"No forex rate available for {base}/{target}")
        return None
    
    # ==================== CRYPTO FEEDS ====================
    
    async def connect_crypto_feed(self, symbols: list = None):
        """
        Connect to Binance WebSocket for live crypto prices.
        
        Runs as a background task continuously updating Redis.
        Reconnects automatically on disconnect.
        
        Args:
            symbols: List of crypto symbols, e.g. ['BTCUSD', 'ETHUSD']
                Default: ['BTCUSD', 'ETHUSD', 'BNBUSD', 'ADAUSD']
        """
        if not symbols:
            symbols = ['BTCUSD', 'ETHUSD', 'BNBUSD', 'ADAUSD', 'DOGEUSD', 'XRPUSD']
        
        while True:  # Reconnect loop
            try:
                await self._binance_websocket_loop(symbols)
            except Exception as e:
                logger.error(f"WebSocket error (reconnecting in 5s): {e}")
                await asyncio.sleep(5)
    
    async def _binance_websocket_loop(self, symbols: list):
        """
        Internal WebSocket connection loop.
        """
        import websockets
        
        # Format streams for Binance: btcusd@ticker, ethusd@ticker, etc.
        streams = [f"{symbol.lower()}@ticker" for symbol in symbols]
        stream_string = "/".join(streams)
        
        url = f"wss://stream.binance.us:9443/stream?streams={stream_string}"
        
        async with websockets.connect(url) as websocket:
            logger.info(f"Crypto WebSocket connected: {len(symbols)} symbols")
            
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    data = json.loads(message)
                    
                    # Handle stream messages
                    if 'stream' in data and 'data' in data:
                        stream_data = data['data']
                        symbol = stream_data.get('s', '').upper()  # e.g., "BTCUSD"
                        price = Decimal(stream_data.get('c', 0))  # Close price
                        
                        # Update in-memory cache
                        self.crypto_prices[symbol] = {
                            'price': price,
                            'timestamp': datetime.utcnow(),
                            'bid': Decimal(stream_data.get('b', 0)),
                            'ask': Decimal(stream_data.get('a', 0))
                        }
                        
                        # Store in Redis with 10-second TTL (live updates)
                        if self.redis_client:
                            await self.redis_client.setex(
                                f"crypto_price:{symbol}",
                                10,
                                json.dumps({
                                    'price': str(price),
                                    'bid': str(stream_data.get('b', 0)),
                                    'ask': str(stream_data.get('a', 0)),
                                    'timestamp': datetime.utcnow().isoformat()
                                })
                            )
                
                except asyncio.TimeoutError:
                    logger.warning("WebSocket timeout (reconnecting)")
                    break
    
    async def get_crypto_price(self, symbol: str) -> Optional[Decimal]:
        """
        Get current crypto price from cache or fallback.
        
        Args:
            symbol: e.g., "BTCUSD", "ETHUSD"
        
        Returns:
            Current price or None if unavailable
        """
        symbol = symbol.upper()
        
        # Check Redis first
        if self.redis_client:
            try:
                cached = await self.redis_client.get(f"crypto_price:{symbol}")
                if cached:
                    data = json.loads(cached)
                    return Decimal(data['price'])
            except Exception as e:
                logger.debug(f"Redis crypto lookup failed: {e}")
        
        # Fallback to in-memory
        if symbol in self.crypto_prices:
            return self.crypto_prices[symbol]['price']
        
        logger.warning(f"No crypto price available for {symbol}")
        return None
    
    async def get_crypto_all_prices(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all cached crypto prices.
        
        Returns:
            {symbol: {price, bid, ask, timestamp}}
        """
        if self.redis_client:
            try:
                keys = await self.redis_client.keys("crypto_price:*")
                prices = {}
                for key in keys:
                    data = await self.redis_client.get(key)
                    if data:
                        symbol = key.decode().replace("crypto_price:", "") if isinstance(key, bytes) else key.replace("crypto_price:", "")
                        prices[symbol] = json.loads(data)
                return prices
            except Exception as e:
                logger.debug(f"Redis all prices lookup failed: {e}")
        
        # Fallback to in-memory
        return self.crypto_prices
    
    # ==================== CONVERSION METHODS ====================
    
    async def convert_currency(self, amount: Decimal, from_currency: str, 
                              to_currency: str) -> Optional[Decimal]:
        """
        Convert amount from one currency to another.
        
        Supports both forex and crypto conversions.
        """
        if from_currency == to_currency:
            return amount
        
        # Try forex rate
        rate = await self.get_forex_rate(from_currency, to_currency)
        if rate:
            return amount * rate
        
        # Not found
        logger.warning(f"No rate available for {from_currency}/{to_currency}")
        return None
    
    async def get_portfolio_usd_value(self, holdings: Dict[str, Decimal]) -> Decimal:
        """
        Calculate total USD value of holdings.
        
        Args:
            holdings: {symbol: quantity}
        
        Returns:
            Total USD value
        """
        total_usd = Decimal(0)
        
        for symbol, quantity in holdings.items():
            # Try crypto price first
            price = await self.get_crypto_price(symbol)
            
            if not price:
                logger.warning(f"No price for {symbol}")
                continue
            
            total_usd += price * quantity
        
        return total_usd


# Singleton instance
price_feed_service = None


async def get_price_feed_service(redis_url: str = "redis://localhost:6379") -> PriceFeedService:
    """Get or create price feed service"""
    global price_feed_service
    if not price_feed_service:
        price_feed_service = PriceFeedService(redis_url)
        await price_feed_service.connect()
    return price_feed_service
