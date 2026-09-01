from functools import wraps
from inspect import signature
from collections.abc import Callable, MutableMapping
import logging
from typing import TypeVar


logger = logging.getLogger(__name__)

T = TypeVar("T")


def cached(
    *,
    cache: MutableMapping,
    key_by: str | Callable[..., str],
):
    def decorator(func: Callable[..., T]):
        func_signature = signature(func)

        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            bound = func_signature.bind_partial(*args, **kwargs)
            bound.apply_defaults()

            cache_key = (
                key_by(**bound.arguments)
                if callable(key_by)
                else bound.arguments[key_by]
            )

            cached_value = cache.get(cache_key)

            if cached_value is not None:
                logger.info(
                    "Returning cached response",
                    extra={
                        "event": "cache_lookup",
                        "result": "hit",
                    },
                )

                return cached_value

            logger.info(
                "No cached response found",
                extra={
                    "event": "cache_lookup",
                    "result": "miss",
                },
            )

            value = func(*args, **kwargs)

            cache[cache_key] = value

            return value

        return wrapper

    return decorator