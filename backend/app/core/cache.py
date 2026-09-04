"""
IBVAP — High-Performance Distributed Caching & In-Memory Fallback Layer
Supports Redis cluster/standalone with automatic degradation to local thread-safe TTL LRU cache.
"""

import functools
import json
import logging
import threading
import time
from typing import Any, Callable, Optional

from backend.app.core.config import settings

logger = logging.getLogger("ibvap.cache")


class MemoryCache:
    """Thread-safe in-memory key-value cache with per-item TTL expiration."""

    def __init__(self, max_size: int = 1024):
        self.max_size = max_size
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        now = time.time()
        with self._lock:
            if key in self._cache:
                val, expires_at = self._cache[key]
                if expires_at > now:
                    return val
                del self._cache[key]
        return None

    def set(self, key: str, value: str, ttl_seconds: int = 60) -> None:
        now = time.time()
        with self._lock:
            # Simple eviction if max capacity exceeded
            if len(self._cache) >= self.max_size:
                # Remove expired keys first
                expired = [k for k, (_, exp) in self._cache.items() if exp <= now]
                for k in expired:
                    del self._cache[k]
                # If still full, pop first inserted key
                if len(self._cache) >= self.max_size:
                    first_key = next(iter(self._cache))
                    del self._cache[first_key]
            self._cache[key] = (value, now + ttl_seconds)

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def delete_pattern(self, pattern_prefix: str) -> None:
        with self._lock:
            keys_to_del = [k for k in self._cache if k.startswith(pattern_prefix)]
            for k in keys_to_del:
                del self._cache[k]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class CacheClient:
    """Unified cache facade with Redis client and MemoryCache fallback."""

    def __init__(self):
        self._memory = MemoryCache()
        self._redis = None
        self._redis_available = False
        self._last_redis_check = 0.0
        self._connect_redis()

    def _connect_redis(self) -> None:
        try:
            import redis
            client = redis.from_url(settings.redis_url, socket_timeout=1.0)
            client.ping()
            self._redis = client
            self._redis_available = True
            logger.info("Connected to Redis cache backend", extra={"url": settings.redis_url})
        except Exception:
            self._redis = None
            self._redis_available = False

    def is_redis_active(self) -> bool:
        now = time.time()
        # Periodically retry connecting to Redis if it was down
        if not self._redis_available and now - self._last_redis_check > 30.0:
            self._last_redis_check = now
            self._connect_redis()
        return self._redis_available

    def get(self, key: str) -> Optional[str]:
        if self.is_redis_active() and self._redis:
            try:
                val = self._redis.get(key)
                if val is not None:
                    return val.decode("utf-8") if isinstance(val, bytes) else str(val)
                return None
            except Exception as e:
                logger.warning(f"Redis get error, falling back to memory: {e}")
                self._redis_available = False
        return self._memory.get(key)

    def set(self, key: str, value: str, ttl_seconds: int = 60) -> None:
        if self.is_redis_active() and self._redis:
            try:
                self._redis.set(key, value, ex=ttl_seconds)
                return
            except Exception as e:
                logger.warning(f"Redis set error, falling back to memory: {e}")
                self._redis_available = False
        self._memory.set(key, value, ttl_seconds)

    def delete(self, key: str) -> None:
        if self.is_redis_active() and self._redis:
            try:
                self._redis.delete(key)
            except Exception:
                self._redis_available = False
        self._memory.delete(key)

    def delete_pattern(self, pattern_prefix: str) -> None:
        if self.is_redis_active() and self._redis:
            try:
                keys = self._redis.keys(f"{pattern_prefix}*")
                if keys:
                    self._redis.delete(*keys)
            except Exception:
                self._redis_available = False
        self._memory.delete_pattern(pattern_prefix)

    def clear(self) -> None:
        if self.is_redis_active() and self._redis:
            try:
                self._redis.flushdb()
            except Exception:
                self._redis_available = False
        self._memory.clear()


# Global cache client instance
cache = CacheClient()


def cached(ttl_seconds: int = 30, key_prefix: str = ""):
    """
    Decorator for caching function return values (JSON serializable).
    Generates cache key from prefix + arguments.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Exclude non-serializable objects like SQLAlchemy db sessions
            clean_args = [a for a in args if not hasattr(a, "execute") and not hasattr(a, "query")]
            clean_kwargs = {k: v for k, v in kwargs.items() if not hasattr(v, "execute") and not hasattr(v, "query")}
            
            pfx = key_prefix or f"{func.__module__}.{func.__name__}"
            key_suffix = f"{clean_args}:{sorted(clean_kwargs.items())}"
            cache_key = f"ibvap:cache:{pfx}:{key_suffix}"

            cached_val = None
            try:
                cached_val = cache.get(cache_key)
            except Exception as e:
                logger.warning(f"Cache read exception bypassed: {e}")

            if cached_val is not None:
                try:
                    return json.loads(cached_val)
                except Exception:
                    pass

            result = func(*args, **kwargs)
            try:
                # Handle Pydantic models or primitives
                if hasattr(result, "model_dump"):
                    serializable = result.model_dump()
                elif isinstance(result, list) and result and hasattr(result[0], "model_dump"):
                    serializable = [item.model_dump() for item in result]
                else:
                    serializable = result
                cache.set(cache_key, json.dumps(serializable), ttl_seconds=ttl_seconds)
            except Exception as e:
                logger.debug(f"Cache serialization skipped for {cache_key}: {e}")

            return result
        return wrapper
    return decorator


def invalidate_cache(pattern_prefix: str) -> None:
    """Invalidate all cache entries matching prefix."""
    cache.delete_pattern(f"ibvap:cache:{pattern_prefix}")
