import logging
import secrets
import random
import time
from typing import Optional

log = logging.getLogger(__name__)

_OTP_PREFIX   = "finanza:otp:"
_RESET_PREFIX = "finanza:rst:"
OTP_TTL_SECONDS   = 600
RESET_TTL_SECONDS = 1800
MAX_OTP_ATTEMPTS  = 5


class _MemoryStore:
    def __init__(self):
        self._data = {}

    def _prune(self):
        now = time.monotonic()
        dead = [k for k, (_, exp) in list(self._data.items()) if now > exp]
        for k in dead:
            del self._data[k]

    def set(self, key, value, ttl):
        self._prune()
        self._data[key] = (value, time.monotonic() + ttl)

    def get(self, key):
        self._prune()
        entry = self._data.get(key)
        if entry is None:
            return None
        value, exp = entry
        if time.monotonic() > exp:
            del self._data[key]
            return None
        return value

    def delete(self, key):
        self._data.pop(key, None)


class OTPService:
    def __init__(self):
        self._redis = None
        self._mem = _MemoryStore()
        self._redis_ok = None

    def _get_redis(self):
        if self._redis_ok is False:
            return None
        if self._redis is not None:
            return self._redis
        try:
            from config import settings
            redis_url = getattr(settings, "REDIS_URL", "") or ""
            if not redis_url:
                self._redis_ok = False
                return None
            import redis as redis_lib
            self._redis = redis_lib.from_url(redis_url, decode_responses=True)
            self._redis.ping()
            self._redis_ok = True
            log.info("OTPService: Redis connected")
            return self._redis
        except Exception as e:
            self._redis_ok = False
            log.warning("OTPService: Redis unavailable (%s), using in-memory store", e)
            return None

    def _set(self, key, value, ttl):
        r = self._get_redis()
        if r:
            r.setex(key, ttl, value)
        else:
            self._mem.set(key, value, ttl)

    def _get(self, key):
        r = self._get_redis()
        if r:
            return r.get(key)
        return self._mem.get(key)

    def _delete(self, key):
        r = self._get_redis()
        if r:
            r.delete(key)
        else:
            self._mem.delete(key)

    async def create_email_otp(self, email: str) -> str:
        code = str(random.SystemRandom().randint(100000, 999999))
        key = _OTP_PREFIX + email.lower().strip()
        self._set(key, code + ":0", OTP_TTL_SECONDS)
        log.info("OTP created for %s", email)
        return code

    async def verify_email_otp(self, email: str, code: str) -> bool:
        key = _OTP_PREFIX + email.lower().strip()
        raw = self._get(key)
        if raw is None:
            return False
        stored_code, attempts_str = raw.split(":", 1)
        attempts = int(attempts_str)
        if attempts >= MAX_OTP_ATTEMPTS:
            self._delete(key)
            log.warning("OTP max attempts exceeded for %s", email)
            return False
        if secrets.compare_digest(stored_code, code.strip()):
            self._delete(key)
            log.info("OTP verified for %s", email)
            return True
        r = self._get_redis()
        if r:
            ttl_rem = r.ttl(key)
            if ttl_rem > 0:
                r.setex(key, ttl_rem, stored_code + ":" + str(attempts + 1))
        else:
            self._mem.set(key, stored_code + ":" + str(attempts + 1), OTP_TTL_SECONDS)
        return False

    async def create_reset_token(self, user_id: int) -> str:
        token = secrets.token_urlsafe(48)
        key = _RESET_PREFIX + token
        self._set(key, str(user_id), RESET_TTL_SECONDS)
        log.info("Reset token created for user %s", user_id)
        return token

    async def verify_reset_token(self, token: str):
        key = _RESET_PREFIX + token
        raw = self._get(key)
        if raw is None:
            return None
        try:
            user_id = int(raw)
        except ValueError:
            return None
        self._delete(key)
        log.info("Reset token consumed for user %s", user_id)
        return user_id


otp_service = OTPService()
