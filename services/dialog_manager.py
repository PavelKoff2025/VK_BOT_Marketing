"""Менеджер диалогов: CRUD, переключение, режимы."""

from __future__ import annotations

from typing import Optional

from config.prompts import DEFAULT_MODE, get_mode_title
from models.dialog import Dialog
from models.message import ChatMessage
from models.user import UserState
from services.memory_manager import MemoryManager
from storage.json_storage import JsonUserStorage


class DialogManager:
    def __init__(
        self,
        storage: JsonUserStorage,
        memory: MemoryManager,
    ) -> None:
        self.storage = storage
        self.memory = memory

    async def get_user(self, user_id: int) -> UserState:
        return await self.storage.load(user_id)

    async def save_user(self, state: UserState) -> None:
        await self.storage.save(state)

    async def create_dialog(
        self,
        user_id: int,
        title: str = "Новый диалог",
        mode: Optional[str] = None,
    ) -> Dialog:
        state = await self.get_user(user_id)
        dialog_mode = mode or state.settings.default_mode or DEFAULT_MODE
        dialog = Dialog.create(title=title.strip() or "Новый диалог", mode=dialog_mode)
        state.dialogs.append(dialog)
        state.active_dialog_id = dialog.id
        state.clear_pending()
        await self.save_user(state)
        return dialog

    async def list_dialogs(self, user_id: int) -> list[Dialog]:
        state = await self.get_user(user_id)
        return list(state.dialogs)

    async def switch_dialog(self, user_id: int, dialog_id: str) -> Optional[Dialog]:
        state = await self.get_user(user_id)
        dialog = state.get_dialog(dialog_id)
        if not dialog:
            return None
        state.active_dialog_id = dialog.id
        state.clear_pending()
        await self.save_user(state)
        return dialog

    async def rename_dialog(
        self,
        user_id: int,
        dialog_id: str,
        title: str,
    ) -> Optional[Dialog]:
        state = await self.get_user(user_id)
        dialog = state.get_dialog(dialog_id)
        if not dialog:
            return None
        dialog.title = title.strip()[:64] or dialog.title
        dialog.updated_at = ChatMessage.now_iso()
        state.clear_pending()
        await self.save_user(state)
        return dialog

    async def delete_dialog(self, user_id: int, dialog_id: str) -> bool:
        state = await self.get_user(user_id)
        if len(state.dialogs) <= 1:
            return False

        before = len(state.dialogs)
        state.dialogs = [d for d in state.dialogs if d.id != dialog_id]
        if len(state.dialogs) == before:
            return False

        if state.active_dialog_id == dialog_id:
            state.active_dialog_id = state.dialogs[0].id

        state.clear_pending()
        await self.save_user(state)
        return True

    async def set_mode(self, user_id: int, mode_id: str) -> Dialog:
        state = await self.get_user(user_id)
        dialog = state.get_active_dialog()
        dialog.mode = mode_id
        dialog.updated_at = ChatMessage.now_iso()
        state.settings.default_mode = mode_id
        state.clear_pending()
        await self.save_user(state)
        return dialog

    async def clear_active_history(self, user_id: int) -> Dialog:
        state = await self.get_user(user_id)
        dialog = state.get_active_dialog()
        self.memory.clear(dialog)
        state.clear_pending()
        await self.save_user(state)
        return dialog

    async def append_exchange(
        self,
        user_id: int,
        user_text: str,
        assistant_text: str,
    ) -> Dialog:
        state = await self.get_user(user_id)
        dialog = state.get_active_dialog()
        self.memory.add_message(dialog, "user", user_text)
        self.memory.add_message(dialog, "assistant", assistant_text)
        await self.save_user(state)
        return dialog

    async def set_pending(
        self,
        user_id: int,
        action: str,
        dialog_id: Optional[str] = None,
    ) -> None:
        state = await self.get_user(user_id)
        state.settings.pending_action = action
        state.settings.pending_dialog_id = dialog_id
        await self.save_user(state)

    async def clear_pending(self, user_id: int) -> None:
        state = await self.get_user(user_id)
        state.clear_pending()
        await self.save_user(state)

    async def status_text(self, user_id: int) -> str:
        state = await self.get_user(user_id)
        dialog = state.get_active_dialog()
        return (
            f"Активный диалог: «{dialog.title}»\n"
            f"Режим: {get_mode_title(dialog.mode)}\n"
            f"Сообщений в памяти: {len(dialog.messages)}"
        )
