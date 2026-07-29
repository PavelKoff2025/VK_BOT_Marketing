"""Клавиатуры ВКонтакте (русский UX)."""

from __future__ import annotations

from vkbottle import Keyboard, KeyboardButtonColor, Text

from config.prompts import MODES
from models.dialog import Dialog


def main_menu_keyboard() -> str:
    """Постоянная клавиатура внизу чата."""
    keyboard = (
        Keyboard(one_time=False, inline=False)
        .add(Text("📋 Меню"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("❓ Помощь"), color=KeyboardButtonColor.SECONDARY)
        .row()
        .add(Text("🆕 Новый диалог"), color=KeyboardButtonColor.POSITIVE)
        .add(Text("💬 Список диалогов"), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text("🎭 Сменить режим"), color=KeyboardButtonColor.SECONDARY)
        .add(Text("⚙️ Настройки"), color=KeyboardButtonColor.SECONDARY)
        .row()
        .add(Text("🔍 Первичный аудит"), color=KeyboardButtonColor.POSITIVE)
        .add(Text("📄 PDF-отчёт"), color=KeyboardButtonColor.PRIMARY)
    )
    return keyboard.get_json()


def menu_inline_keyboard() -> str:
    """Красивое inline-меню под сообщением."""
    keyboard = (
        Keyboard(inline=True)
        .add(
            Text("🆕 Новый диалог", payload={"cmd": "new_dialog"}),
            color=KeyboardButtonColor.POSITIVE,
        )
        .add(
            Text("💬 Диалоги", payload={"cmd": "list_dialogs"}),
            color=KeyboardButtonColor.PRIMARY,
        )
        .row()
        .add(
            Text("🎭 Режим", payload={"cmd": "choose_mode"}),
            color=KeyboardButtonColor.SECONDARY,
        )
        .add(
            Text("⚙️ Настройки", payload={"cmd": "open_settings"}),
            color=KeyboardButtonColor.SECONDARY,
        )
        .row()
        .add(
            Text("🔍 Аудит", payload={"cmd": "start_audit"}),
            color=KeyboardButtonColor.POSITIVE,
        )
        .add(
            Text("📄 PDF", payload={"cmd": "pdf_report"}),
            color=KeyboardButtonColor.PRIMARY,
        )
    )
    return keyboard.get_json()


def audit_keyboard() -> str:
    """Клавиатура во время пошагового аудита."""
    keyboard = (
        Keyboard(one_time=False, inline=False)
        .add(
            Text("❌ Отменить аудит"),
            color=KeyboardButtonColor.NEGATIVE,
        )
    )
    return keyboard.get_json()


def pdf_offer_keyboard() -> str:
    """Кнопка под ответом маркетинг-консультанта."""
    keyboard = (
        Keyboard(inline=True)
        .add(
            Text("📄 Скачать PDF-отчёт", payload={"cmd": "pdf_report"}),
            color=KeyboardButtonColor.POSITIVE,
        )
    )
    return keyboard.get_json()


def dialogs_list_keyboard(dialogs: list[Dialog], active_id: str | None) -> str:
    """
    Inline: максимум 5 диалогов + ряд «В меню».
    У VK лимит ~6 рядов для inline-клавиатуры.
    """
    keyboard = Keyboard(inline=True)
    visible = dialogs[:5]
    for index, dialog in enumerate(visible):
        if index > 0:
            keyboard.row()
        mark = "✅ " if dialog.id == active_id else ""
        title = f"{mark}{dialog.title}"[:40]
        keyboard.add(
            Text(
                title,
                payload={"cmd": "open_dialog", "id": dialog.id},
            ),
            color=(
                KeyboardButtonColor.POSITIVE
                if dialog.id == active_id
                else KeyboardButtonColor.PRIMARY
            ),
        )
    keyboard.row()
    keyboard.add(Text("🏠 В меню", payload={"cmd": "main_menu"}))
    return keyboard.get_json()


def dialog_actions_keyboard(dialog_id: str) -> str:
    keyboard = (
        Keyboard(inline=True)
        .add(
            Text("🔀 Переключить", payload={"cmd": "switch_dialog", "id": dialog_id}),
            color=KeyboardButtonColor.POSITIVE,
        )
        .add(
            Text("✏️ Переименовать", payload={"cmd": "rename_dialog", "id": dialog_id}),
            color=KeyboardButtonColor.PRIMARY,
        )
        .row()
        .add(
            Text("🗑 Удалить", payload={"cmd": "delete_dialog", "id": dialog_id}),
            color=KeyboardButtonColor.NEGATIVE,
        )
        .add(Text("◀️ К списку", payload={"cmd": "list_dialogs"}))
    )
    return keyboard.get_json()


def modes_keyboard() -> str:
    """
    Режимы по 2 в ряд — иначе VK ошибка 911 (слишком много рядов).
    6 режимов = 3 ряда + «В меню» = 4 ряда (лимит inline ≈ 6).
    """
    keyboard = Keyboard(inline=True)
    items = list(MODES.items())
    for index, (mode_id, meta) in enumerate(items):
        if index > 0 and index % 2 == 0:
            keyboard.row()
        # Короткие подписи, чтобы две кнопки влезали в ряд
        label = f'{meta["emoji"]} {meta["title"]}'[:36]
        keyboard.add(
            Text(label, payload={"cmd": "set_mode", "mode": mode_id}),
            color=KeyboardButtonColor.PRIMARY,
        )
    keyboard.row()
    keyboard.add(Text("🏠 В меню", payload={"cmd": "main_menu"}))
    return keyboard.get_json()


def settings_keyboard() -> str:
    keyboard = (
        Keyboard(inline=True)
        .add(
            Text("🎭 Выбрать режим", payload={"cmd": "choose_mode"}),
            color=KeyboardButtonColor.PRIMARY,
        )
        .row()
        .add(
            Text("ℹ️ О модели", payload={"cmd": "model_info"}),
            color=KeyboardButtonColor.SECONDARY,
        )
        .row()
        .add(
            Text("🧹 Очистить историю", payload={"cmd": "clear_history"}),
            color=KeyboardButtonColor.NEGATIVE,
        )
        .row()
        .add(Text("🏠 В меню", payload={"cmd": "main_menu"}))
    )
    return keyboard.get_json()


def help_keyboard() -> str:
    keyboard = (
        Keyboard(inline=True)
        .add(
            Text("📋 Открыть меню", payload={"cmd": "main_menu"}),
            color=KeyboardButtonColor.PRIMARY,
        )
    )
    return keyboard.get_json()


def cancel_keyboard() -> str:
    keyboard = (
        Keyboard(inline=True)
        .add(
            Text("❌ Отмена", payload={"cmd": "cancel"}),
            color=KeyboardButtonColor.NEGATIVE,
        )
    )
    return keyboard.get_json()
