"""Модель диалога пользователя."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from models.message import ChatMessage


@dataclass(slots=True)
class Dialog:
    id: str
    title: str
    mode: str
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def create(
        cls,
        title: str = "Новый диалог",
        mode: str = "assistant",
    ) -> Dialog:
        now = ChatMessage.now_iso()
        return cls(
            id=str(uuid4()),
            title=title,
            mode=mode,
            messages=[],
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Dialog:
        messages = [
            ChatMessage.from_dict(item)
            for item in data.get("messages", [])
        ]
        return cls(
            id=data["id"],
            title=data.get("title", "Диалог"),
            mode=data.get("mode", "assistant"),
            messages=messages,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "mode": self.mode,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
