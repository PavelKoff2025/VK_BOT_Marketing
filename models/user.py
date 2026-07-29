"""Состояние пользователя: диалоги, настройки, pending-действия, аудит."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from config.prompts import DEFAULT_MODE
from models.dialog import Dialog


@dataclass(slots=True)
class AuditAnswer:
    number: int
    block: str
    question: str
    answer: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditAnswer:
        return cls(
            number=int(data.get("number", 0)),
            block=str(data.get("block", "")),
            question=str(data.get("question", "")),
            answer=str(data.get("answer", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "block": self.block,
            "question": self.question,
            "answer": self.answer,
        }


@dataclass(slots=True)
class UserSettings:
    default_mode: str = DEFAULT_MODE
    pending_action: Optional[str] = None
    pending_dialog_id: Optional[str] = None
    # Первичный аудит (пошаговый опрос)
    audit_index: int = 0
    audit_answers: list[AuditAnswer] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> UserSettings:
        data = data or {}
        answers = [
            AuditAnswer.from_dict(item)
            for item in data.get("audit_answers", [])
            if isinstance(item, dict)
        ]
        return cls(
            default_mode=data.get("default_mode", DEFAULT_MODE),
            pending_action=data.get("pending_action"),
            pending_dialog_id=data.get("pending_dialog_id"),
            audit_index=int(data.get("audit_index", 0) or 0),
            audit_answers=answers,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_mode": self.default_mode,
            "pending_action": self.pending_action,
            "pending_dialog_id": self.pending_dialog_id,
            "audit_index": self.audit_index,
            "audit_answers": [a.to_dict() for a in self.audit_answers],
        }

    def clear_audit(self) -> None:
        self.audit_index = 0
        self.audit_answers = []

    def clear_pending(self) -> None:
        self.pending_action = None
        self.pending_dialog_id = None


@dataclass(slots=True)
class UserState:
    user_id: int
    dialogs: list[Dialog] = field(default_factory=list)
    active_dialog_id: Optional[str] = None
    settings: UserSettings = field(default_factory=UserSettings)

    @classmethod
    def create_default(cls, user_id: int) -> UserState:
        dialog = Dialog.create(title="Основной диалог", mode=DEFAULT_MODE)
        return cls(
            user_id=user_id,
            dialogs=[dialog],
            active_dialog_id=dialog.id,
            settings=UserSettings(default_mode=DEFAULT_MODE),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserState:
        dialogs = [Dialog.from_dict(d) for d in data.get("dialogs", [])]
        state = cls(
            user_id=int(data["user_id"]),
            dialogs=dialogs,
            active_dialog_id=data.get("active_dialog_id"),
            settings=UserSettings.from_dict(data.get("settings")),
        )
        if not state.dialogs:
            default = Dialog.create(title="Основной диалог", mode=DEFAULT_MODE)
            state.dialogs.append(default)
            state.active_dialog_id = default.id
        elif not state.active_dialog_id or not state.get_dialog(state.active_dialog_id):
            state.active_dialog_id = state.dialogs[0].id
        return state

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "dialogs": [d.to_dict() for d in self.dialogs],
            "active_dialog_id": self.active_dialog_id,
            "settings": self.settings.to_dict(),
        }

    def get_dialog(self, dialog_id: str) -> Optional[Dialog]:
        for dialog in self.dialogs:
            if dialog.id == dialog_id:
                return dialog
        return None

    def get_active_dialog(self) -> Dialog:
        dialog = self.get_dialog(self.active_dialog_id or "")
        if dialog:
            return dialog
        if self.dialogs:
            self.active_dialog_id = self.dialogs[0].id
            return self.dialogs[0]
        new_dialog = Dialog.create()
        self.dialogs.append(new_dialog)
        self.active_dialog_id = new_dialog.id
        return new_dialog

    def clear_pending(self) -> None:
        self.settings.clear_pending()

    def clear_audit_session(self) -> None:
        self.settings.clear_pending()
        self.settings.clear_audit()
