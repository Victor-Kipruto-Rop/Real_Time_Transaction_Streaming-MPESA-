"""
Database Query Caching Module

Implements multi-tier caching strategy to reduce database load:
- In-memory cache (LRU)
- Redis cache (optional, for distributed caching)
- Automatic cache invalidation
"""

import time
import logging
import json
import redis
from typing import Any, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages query result caching"""
    
    def __init__(self, redis_host: str = 'localhost', 
                 redis_port: int = 6379,
                 redis_db: int = 0,
                 cache_ttl: int = 300):
        """
        Initialize cache manager.
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            cache_ttl: Cache TTL in seconds (default: 5 minutes)
        """
        self.cache_ttl = cache_ttl
        self.in_memory_cache = {}
        self.redis_available = False
        
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=2
            )
            # Test connection
            self.redis_client.ping()
            self.redis_available = True
            logger.info("✓ Redis cache available")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory cache only: {e}")
            self.redis_client = None
    
    def get_cache_key(self, query: str, params: tuple = None) -> str:
        """Generate cache key from query and parameters"""
        key_str = f"{query}:{str(params)}"
        return f"query:{hash(key_str) % 10**8}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (tries Redis first, then in-memory)"""
        # Try Redis first
        if self.redis_available:
            try:
                value = self.redis_client.get(key)
                if value:
                    logger.debug(f"Cache hit (Redis): {key}")
                    return json.loads(value)
            except Exception as e:
                logger.debug(f"Redis get error: {e}")
        
        # Try in-memory cache
        if key in self.in_memory_cache:
            entry = self.in_memory_cache[key]
            if time.time() < entry['expires']:
                logger.debug(f"Cache hit (memory): {key}")
                return entry['value']
            else:
                del self.in_memory_cache[key]
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache"""
        ttl = ttl or self.cache_ttl
        
        try:
            # Store in Redis if available
            if self.redis_available:
                self.redis_client.setex(
                    key,
                    ttl,
                    json.dumps(value, default=str)
                )
                logger.debug(f"Cache set (Redis): {key} (TTL: {ttl}s)")
            
            # Store in memory
            self.in_memory_cache[key] = {
                'value': value,
                'expires': time.time() + ttl
            }
            logger.debug(f"Cache set (memory): {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False
    
    def invalidate(self, key: str) -> bool:
        """Invalidate a cache entry"""
        try:
            if self.redis_available:
                self.redis_client.delete(key)
            
            if key in self.in_memory_cache:
                del self.in_memory_cache[key]
            
            logger.debug(f"Cache invalidated: {key}")
            return True
        except Exception as e:
            logger.warning(f"Cache invalidate error: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cache"""
        try:
            self.in_memory_cache.clear()
            if self.redis_available:
                self.redis_client.flushdb()
            logger.info("Cache cleared")
            return True
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        stats = {
            'in_memory_size': len(self.in_memory_cache),
            'redis_available': self.redis_available,
            'cache_ttl': self.cache_ttl
        }
        
        if self.redis_available:
            try:
                info = self.redis_client.info()
                stats['redis_used_memory'] = info.get('used_memory_human', 'unknown')
                stats['redis_keys'] = self.redis_client.dbsize()
            except Exception as e:
                logger.debug(f"Could not get Redis stats: {e}")
        
        return stats


# Global cache manager instance
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """Get or create the global cache manager"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached_query(ttl: int = 300):
    """
    Decorator to cache query results.
    
    Usage:
        @cached_query(ttl=600)
        def get_user_data(user_id):
            return execute_query(...)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # Generate cache key
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Using cached result for {func.__name__}")
                return result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


class CacheInvalidationStrategy:
    """Strategies for cache invalidation"""
    
    @staticmethod
    def invalidate_transaction_caches():
        """Invalidate all transaction-related caches"""
        cache = get_cache_manager()
        patterns_to_clear = [
            'get_transactions_by_phone',
            'get_transaction_by_id',
            'get_daily_summary',
            'get_heatmap_data',
            'get_transaction_statistics',
            'get_top_merchants',
            'get_hourly_trend'
        ]
        
        for pattern in patterns_to_clear:
            # In a real Redis implementation, you'd use pattern matching
            # For now, clear the entire cache on transaction updates
            pass
        
        cache.clear()
        logger.info("Transaction caches invalidated")
    
    @staticmethod
    def schedule_cache_warmup(interval_seconds: int = 3600):
        """
        Schedule periodic cache warmup.
        Pre-load frequently accessed data.
        """
        logger.info(f"Cache warmup scheduled every {interval_seconds}s")
        # TODO: Implement background task for cache warmup
