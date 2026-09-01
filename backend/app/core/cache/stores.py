from cachetools import TTLCache


class CacheStores:
    location_branding = TTLCache(
        maxsize=1000,
        ttl=600,
    )

    permissions = TTLCache(
        maxsize=5000,
        ttl=300,
    )


cache_stores = CacheStores()