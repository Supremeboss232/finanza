"""
Real-Time Price Feed Service
Handles:
1. Live Forex rates from Open ExchangeRate-API / ECB / Fixer.io
2. Live Cryptocurrency prices from Coinbase Exchange API (globally accessible, no HTTP 451)
3. Optional Redis caching with seamless in-memory fallback
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Optional
from datetime import datetime
from decimal import Decimal
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class PriceFeedService:
    def __init__(self, redis_url: str = ""):
        self.redis_url = (redis_url or "").strip()
        self.redis_client = None
        self.forex_rates: Dict[str, Decimal] = {}
        self.crypto_prices: Dict[str, dict] = {}
        self.crypto_task = None

    async def connect(self):
        """Initialize Redis connection only when a valid Redis URL is configured."""
        if not self.redis_url or not self.redis_url.startswith(("redis://", "rediss://", "unix://")):
            logger.info("PriceFeedService running with live in-memory cache (no Redis URL configured)")
            return
        try:
            self.redis_client = await redis.from_url(self.redis_url)
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis unavailable, using in-memory price feed cache: {e}")
            self.redis_client = None

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.close()

    async def sync_forex_rates(
        self,
        api_key: str = "",
        base_currency: str = "USD",
        target_currencies: list = None,
    ) -> Dict[str, Decimal]:
        """Synchronize live forex rates from Open ExchangeRate-API (with Fixer.io option)."""
        if not target_currencies:
            target_currencies = ["EUR", "GBP", "AUD", "CAD", "CHF", "JPY", "CNY", "INR", "NGN", "ZAR"]

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"https://open.er-api.com/v6/latest/{base_currency}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        all_rates = data.get("rates", {})
                        self.forex_rates = {
                            c: Decimal(str(all_rates[c]))
                            for c in target_currencies
                            if c in all_rates and all_rates[c] is not None
                        }
                        if self.redis_client and self.forex_rates:
                            await self.redis_client.setex(
                                f"forex_rates:{base_currency}",
                                2700,
                                json.dumps({k: str(v) for k, v in self.forex_rates.items()}),
                            )
                        logger.info(f"Live forex rates synced: {len(self.forex_rates)} currencies")
                        return self.forex_rates
        except Exception as e:
            logger.warning(f"Forex sync error: {e}")
        return self.forex_rates

    async def get_forex_rate(self, base: str, target: str) -> Optional[Decimal]:
        base = base.upper()
        target = target.upper()
        if base == target:
            return Decimal("1.0")
        if self.redis_client:
            try:
                cached = await self.redis_client.get(f"forex_rates:{base}")
                if cached:
                    rates = json.loads(cached)
                    if target in rates:
                        return Decimal(rates[target])
            except Exception:
                pass
        if target in self.forex_rates:
            return self.forex_rates[target]
        await self.sync_forex_rates(base_currency=base, target_currencies=[target])
        return self.forex_rates.get(target)

    async def connect_crypto_feed(self, symbols: list = None):
        """Fetch live cryptocurrency prices from Coinbase Exchange API."""
        if not symbols:
            symbols = ["BTC", "ETH", "SOL", "BNB", "ADA", "DOGE", "XRP"]
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get("https://api.coinbase.com/v2/exchange-rates?currency=USD") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        usd_rates = data.get("data", {}).get("rates", {})
                        now = datetime.utcnow()
                        for sym in symbols:
                            inv = usd_rates.get(sym)
                            if inv and float(inv) > 0:
                                price = (Decimal("1") / Decimal(str(inv))).quantize(Decimal("0.01"))
                                pair = f"{sym}USD"
                                self.crypto_prices[pair] = {
                                    "price": price,
                                    "timestamp": now,
                                    "bid": price,
                                    "ask": price,
                                }
        except Exception as e:
            logger.debug(f"Crypto price refresh warning: {e}")

    async def get_crypto_price(self, symbol: str) -> Optional[Decimal]:
        symbol = symbol.upper()
        if symbol not in self.crypto_prices:
            await self.connect_crypto_feed()
        if symbol in self.crypto_prices:
            return self.crypto_prices[symbol]["price"]
        return None

    async def get_all_prices(self) -> Dict[str, dict]:
        if not self.forex_rates:
            await self.sync_forex_rates()
        if not self.crypto_prices:
            await self.connect_crypto_feed()
        return {
            "forex": {k: float(v) for k, v in self.forex_rates.items()},
            "crypto": {
                k: {
                    "price": float(v["price"]),
                    "bid": float(v["bid"]),
                    "ask": float(v["ask"]),
                    "timestamp": v["timestamp"].isoformat(),
                }
                for k, v in self.crypto_prices.items()
            },
            "timestamp": datetime.utcnow().isoformat(),
        }


price_feed_service: Optional[PriceFeedService] = None


async def get_price_feed_service(redis_url: str = "") -> PriceFeedService:
    global price_feed_service
    if price_feed_service is None:
        price_feed_service = PriceFeedService(redis_url)
        await price_feed_service.connect()
    return price_feed_service
