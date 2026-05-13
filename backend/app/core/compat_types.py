"""
Cross-dialect type compatibility — supports PostgreSQL (production) and SQLite (development).
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from sqlalchemy import String, Text, Integer, BigInteger, TypeDecorator, types


class CompatBigInt(TypeDecorator):
    """BigInteger that renders as INTEGER on SQLite (required for autoincrement PKs)."""
    impl = BigInteger
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(Integer())
        return dialect.type_descriptor(BigInteger())


class CompatUUID(TypeDecorator):
    """UUID type that works with both PostgreSQL and SQLite."""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(str(value)))

    def process_result_value(self, value: Any, dialect: Any) -> Optional[uuid.UUID]:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class CompatJSON(TypeDecorator):
    """JSON type that works with both PostgreSQL (JSONB) and SQLite (TEXT)."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value, default=str)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        return json.loads(value)


class CompatARRAY(TypeDecorator):
    """ARRAY type that works with both PostgreSQL and SQLite (stored as JSON)."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, list):
            return value
        return json.loads(value)


class CompatINET(TypeDecorator):
    """INET type that works with both PostgreSQL and SQLite."""
    impl = String(45)  # IPv6 max length
    cache_ok = True
