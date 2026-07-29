"""Модель сообщения в истории диалога."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Literal

Role = Literal["user", "assistant", "system"]


@dataclass(slots=True)
class ChatMessage:
    role: Role
    content: str
    timestamp: str

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def create(cls, role: Role, content: str) -> ChatMessage:
        return cls(role=role, content=content, timestamp=cls.now_iso())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChatMessage:
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp") or cls.now_iso(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
