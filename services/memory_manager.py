"""Менеджер краткосрочной памяти диалога (sliding window)."""

from __future__ import annotations

from models.dialog import Dialog
from models.message import ChatMessage, Role


class MemoryManager:
    def __init__(self, max_messages: int = 100) -> None:
        self.max_messages = max_messages

    def add_message(self, dialog: Dialog, role: Role, content: str) -> ChatMessage:
        message = ChatMessage.create(role=role, content=content)
        dialog.messages.append(message)
        dialog.updated_at = message.timestamp
        self.trim(dialog)
        return message

    def trim(self, dialog: Dialog) -> None:
        if len(dialog.messages) > self.max_messages:
            dialog.messages = dialog.messages[-self.max_messages :]

    def get_history(self, dialog: Dialog) -> list[ChatMessage]:
        self.trim(dialog)
        return list(dialog.messages)

    def clear(self, dialog: Dialog) -> None:
        dialog.messages.clear()
        dialog.updated_at = ChatMessage.now_iso()

    def build_context_window(
        self,
        dialog: Dialog,
        system_prompt: str,
    ) -> list[dict[str, str]]:
        """
        Формирует context window для LLM:
        system + history (user/assistant).
        """
        context: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]
        for message in self.get_history(dialog):
            if message.role in {"user", "assistant"}:
                context.append(
                    {"role": message.role, "content": message.content}
                )
        return context
