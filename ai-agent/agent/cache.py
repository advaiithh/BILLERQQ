import time
import hashlib
import logging
import threading
from typing import Any, Optional

logger = logging.getLogger("billerq-cache")

class BillerQCache:
    """Thread-safe, tenant-aware in-memory cache with TTL support."""
    
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()

    def _hash_key(self, company_id: str, category: str, key_string: str) -> str:
        """Generate a tenant-safe cache key hash."""
        raw_key = f"billerq:{company_id}:{category}:{key_string.lower().strip()}"
        digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        return f"billerq:{company_id}:{category}:{digest}"

    def get(self, company_id: str, category: str, key_string: str) -> Optional[Any]:
        """Retrieve an item from the cache if it exists and is not expired."""
        full_key = self._hash_key(company_id, category, key_string)
        with self._lock:
            if full_key in self._cache:
                entry = self._cache[full_key]
                expiry = entry["expiry"]
                if expiry is None or time.time() < expiry:
                    logger.debug("Cache hit for: %s", full_key)
                    return entry["value"]
                else:
                    # Expired, clean it up
                    logger.debug("Cache expired for: %s", full_key)
                    del self._cache[full_key]
        return None

    def set(self, company_id: str, category: str, key_string: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store an item in the cache with a tenant-safe key and TTL."""
        full_key = self._hash_key(company_id, category, key_string)
        expiry = time.time() + ttl_seconds if ttl_seconds is not None else None
        with self._lock:
            self._cache[full_key] = {
                "value": value,
                "expiry": expiry
            }
            logger.debug("Cached key %s with TTL %s", full_key, ttl_seconds)

    def clear_tenant(self, company_id: str) -> None:
        """Evict all cached entries for a specific tenant/company."""
        prefix = f"billerq:{company_id}:"
        with self._lock:
            keys_to_del = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_del:
                del self._cache[k]
            logger.info("Evicted %d cache keys for company: %s", len(keys_to_del), company_id)

# Singleton cache instance
billerq_cache = BillerQCache()
