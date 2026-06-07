from __future__ import annotations

import json
from typing import Any

import redis
from pydantic import TypeAdapter

from app.config import get_settings
from app.schemas import ProductRead

settings = get_settings()


class Cache:
    """Small Redis-backed cache wrapper for response payloads."""

    def __init__(self) -> None:
        self._client: redis.Redis | None = None

    def _get_client(self) -> redis.Redis | None:
        if not settings.cache_enabled:
            return None
        if self._client is None:
            try:
                self._client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
                self._client.ping()
            except redis.RedisError:
                self._client = None
        return self._client

    def get_json(self, key: str) -> Any | None:
        client = self._get_client()
        if client is None:
            return None
        try:
            raw = client.get(key)
        except redis.RedisError:
            return None
        if raw is None:
            return None
        return json.loads(raw)

    def set_json(self, key: str, value: Any) -> None:
        client = self._get_client()
        if client is None:
            return
        try:
            client.setex(key, settings.cache_ttl_seconds, json.dumps(value, default=str))
        except redis.RedisError:
            return

    def invalidate_products(self) -> None:
        client = self._get_client()
        if client is None:
            return
        try:
            for key in client.scan_iter("products:*"):
                client.delete(key)
        except redis.RedisError:
            return


cache = Cache()
product_adapter = TypeAdapter(ProductRead)
products_adapter = TypeAdapter(list[ProductRead])
