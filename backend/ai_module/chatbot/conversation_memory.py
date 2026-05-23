"""Conversation memory for recruiter chatbot sessions.

Uses Redis when available, with an in-memory fallback for local development and tests.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import redis  # type: ignore

    REDIS_AVAILABLE = True
except Exception:
    redis = None
    REDIS_AVAILABLE = False


@dataclass
class MemoryRecord:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)


class ConversationMemory:
    """Session-based memory with Redis primary and local fallback."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl_seconds: int = 60 * 60 * 8,
        client: Optional[Any] = None,
    ):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "").strip() or None
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, List[MemoryRecord]] = {}
        self._session_meta: Dict[str, Dict[str, Any]] = {}
        self._client = client

        if self._client is None and REDIS_AVAILABLE and self.redis_url:
            try:
                self._client = redis.from_url(self.redis_url, decode_responses=True)
                self._client.ping()
            except Exception as exc:
                logger.warning("Redis memory unavailable, using in-memory fallback: %s", exc)
                self._client = None

    def available(self) -> bool:
        return True

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to the session history."""
        if not session_id:
            return

        record = MemoryRecord(role=role, content=content)
        if self._client is not None:
            self._add_message_redis(session_id, record)
            return

        self._store.setdefault(session_id, []).append(record)
        self._trim_local(session_id)

    def get_history(self, session_id: str, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Return the latest messages for a session."""
        if not session_id:
            return []

        if self._client is not None:
            return self._get_history_redis(session_id, max_messages)

        history = self._store.get(session_id, [])[-max_messages:]
        return [record.__dict__ for record in history]

    def list_sessions(self) -> List[str]:
        """Return active session ids for the in-memory fallback or Redis."""
        if self._client is not None:
            try:
                pattern = self._messages_key("*")
                keys = self._client.keys(pattern)
                session_ids = []
                for key in keys:
                    prefix = "chat:messages:"
                    if isinstance(key, str) and key.startswith(prefix):
                        session_ids.append(key[len(prefix):])
                return sorted(set(session_ids))
            except Exception:
                return []

        return sorted(set(self._store.keys()) | set(self._session_meta.keys()))

    def set_current_criteria(self, session_id: str, criteria_id: int) -> None:
        if not session_id:
            return

        if self._client is not None:
            key = self._meta_key(session_id)
            self._client.hset(key, mapping={"current_criteria_id": str(criteria_id), "updated_at": str(time.time())})
            self._client.expire(key, self.ttl_seconds)
            return

        self._session_meta.setdefault(session_id, {})["current_criteria_id"] = criteria_id
        self._session_meta[session_id]["updated_at"] = time.time()

    def get_current_criteria(self, session_id: str) -> Optional[int]:
        if not session_id:
            return None

        if self._client is not None:
            key = self._meta_key(session_id)
            value = self._client.hget(key, "current_criteria_id")
            try:
                return int(value) if value is not None else None
            except Exception:
                return None

        meta = self._session_meta.get(session_id, {})
        value = meta.get("current_criteria_id")
        try:
            return int(value) if value is not None else None
        except Exception:
            return None

    def clear(self, session_id: str) -> None:
        if not session_id:
            return

        if self._client is not None:
            self._client.delete(self._messages_key(session_id), self._meta_key(session_id))
            return

        self._store.pop(session_id, None)
        self._session_meta.pop(session_id, None)

    def summarize_context(self, session_id: str) -> Dict[str, Any]:
        """Convenience helper for API payloads."""
        return {
            "history": self.get_history(session_id),
            "current_criteria_id": self.get_current_criteria(session_id),
        }

    def _messages_key(self, session_id: str) -> str:
        return f"chat:messages:{session_id}"

    def _meta_key(self, session_id: str) -> str:
        return f"chat:meta:{session_id}"

    def _add_message_redis(self, session_id: str, record: MemoryRecord) -> None:
        assert self._client is not None
        key = self._messages_key(session_id)
        self._client.rpush(key, json.dumps(record.__dict__, ensure_ascii=False))
        self._client.ltrim(key, -50, -1)
        self._client.expire(key, self.ttl_seconds)

    def _get_history_redis(self, session_id: str, max_messages: int) -> List[Dict[str, Any]]:
        assert self._client is not None
        key = self._messages_key(session_id)
        raw_items = self._client.lrange(key, -max_messages, -1)
        history: List[Dict[str, Any]] = []
        for raw_item in raw_items:
            try:
                history.append(json.loads(raw_item))
            except Exception:
                continue
        return history

    def _trim_local(self, session_id: str, max_messages: int = 50) -> None:
        history = self._store.get(session_id, [])
        if len(history) > max_messages:
            self._store[session_id] = history[-max_messages:]
