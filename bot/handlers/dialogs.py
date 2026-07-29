"""Обработчики списка диалогов и payload-кнопок."""

from __future__ import annotations

import json
from typing import Any

from vkbottle.bot import BotLabeler, Message, rules

from bot.context import get_ctx
from bot.handlers.menu import send_main_menu
from config.prompts import get_mode_title
from keyboards.menus import (
    cancel_keyboard,
    dialog_actions_keyboard,
    dialogs_list_keyboard,
    main_menu_keyboard,
    modes_keyboard,
    settings_keyboard,
)
from utils.logging import get_logger

logger = get_logger(__name__)
labeler = BotLabeler()


def _parse_payload(message: Message) -> dict[str, Any]:
    raw = message.payload
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}


@labeler.private_message(text="💬 Список диалогов")
async def list_dialogs(message: Message) -> None:
    await _show_dialogs(message)


async def _show_dialogs(message: Message) -> None:
    ctx = get_ctx()
    state = await ctx.dialogs.get_user(message.from_id)
    lines = ["💬 Ваши диалоги:\n"]
    for dialog in state.dialogs:
        mark = "→ " if dialog.id == state.active_dialog_id else "• "
        lines.append(
            f"{mark}«{dialog.title}» — {get_mode_title(dialog.mode)} "
            f"({len(dialog.messages)} сообщ.)"
        )
    lines.append("\nНажмите на диалог, чтобы открыть действия.")
    await message.answer(
        "\n".join(lines),
        keyboard=dialogs_list_keyboard(state.dialogs, state.active_dialog_id),
    )


@labeler.private_message(rules.PayloadContainsRule({"cmd": "list_dialogs"}))
async def payload_list_dialogs(message: Message) -> None:
    await _show_dialogs(message)


@labeler.private_message(rules.PayloadContainsRule({"cmd": "main_menu"}))
async def payload_main_menu(message: Message) -> None:
    await get_ctx().dialogs.clear_pending(message.from_id)
    await send_main_menu(message)


@labeler.private_message(rules.PayloadContainsRule({"cmd": "cancel"}))
async def payload_cancel(message: Message) -> None:
    await get_ctx().dialogs.clear_pending(message.from_id)
    await send_main_menu(message, "Действие отменено.")


@labeler.private_message(rules.PayloadContainsRule({"cmd": "open_dialog"}))
async def payload_open_dialog(message: Message) -> None:
    payload = _parse_payload(message)
    dialog_id = payload.get("id")
    if not dialog_id:
        await message.answer("Диалог не найден.")
        return

    ctx = get_ctx()
    state = await ctx.dialogs.get_user(message.from_id)
    dialog = state.get_dialog(dialog_id)
    if not dialog:
        await message.answer("Диалог не найден.")
        return

    active = "да" if dialog.id == state.active_dialog_id else "нет"
    await message.answer(
        f"Диалог «{dialog.title}»\n"
        f"Режим: {get_mode_title(dialog.mode)}\n"
        f"Активен: {active}\n"
        f"Сообщений: {len(dialog.messages)}",
        keyboard=dialog_actions_keyboard(dialog.id),
    )


@labeler.private_message(rules.PayloadContainsRule({"cmd": "switch_dialog"}))
async def payload_switch_dialog(message: Message) -> None:
    payload = _parse_payload(message)
    dialog_id = payload.get("id")
    ctx = get_ctx()
    dialog = await ctx.dialogs.switch_dialog(message.from_id, dialog_id)
    if not dialog:
        await message.answer("Не удалось переключить диалог.")
        return
    await message.answer(
        f"✅ Активный диалог: «{dialog.title}»\n"
        f"Режим: {get_mode_title(dialog.mode)}\n"
        "Контекст и история обновлены.",
        keyboard=main_menu_keyboard(),
    )


@labeler.private_message(rules.PayloadContainsRule({"cmd": "rename_dialog"}))
async def payload_rename_dialog(message: Message) -> None:
    payload = _parse_payload(message)
    dialog_id = payload.get("id")
    if not dialog_id:
        return
    await get_ctx().dialogs.set_pending(
        message.from_id,
        "await_rename_title",
        dialog_id=dialog_id,
    )
    await message.answer(
        "Введите новое название диалога:",
        keyboard=cancel_keyboard(),
    )


@labeler.private_message(rules.PayloadContainsRule({"cmd": "delete_dialog"}))
async def payload_delete_dialog(message: Message) -> None:
    payload = _parse_payload(message)
    dialog_id = payload.get("id")
    ctx = get_ctx()
    ok = await ctx.dialogs.delete_dialog(message.from_id, dialog_id)
    if not ok:
        await message.answer(
            "Нельзя удалить единственный диалог или диалог не найден.",
            keyboard=main_menu_keyboard(),
        )
        return
    await message.answer("🗑 Диалог удалён.", keyboard=main_menu_keyboard())
    await _show_dialogs(message)


@labeler.private_message(rules.PayloadContainsRule({"cmd": "set_mode"}))
async def payload_set_mode(message: Message) -> None:
    payload = _parse_payload(message)
    mode = payload.get("mode")
    if not mode:
        return
    ctx = get_ctx()
    dialog = await ctx.dialogs.set_mode(message.from_id, mode)
    extra = ""
    if mode == "marketing":
        extra = (
            "\n\nПосле аудита нажмите «📄 PDF-отчёт» — "
            "пришлю файл с результатами консультации."
        )
    await message.answer(
        f"✅ Режим обновлён: {get_mode_title(dialog.mode)}\n"
        f"Применяется к диалогу «{dialog.title}».{extra}",
        keyboard=main_menu_keyboard(),
    )


@labeler.private_message(rules.PayloadContainsRule({"cmd": "choose_mode"}))
async def payload_choose_mode(message: Message) -> None:
    await message.answer(
        "Выберите режим общения:",
        keyboard=modes_keyboard(),
    )


@labeler.private_message(rules.PayloadContainsRule({"cmd": "model_info"}))
async def payload_model_info(message: Message) -> None:
    ctx = get_ctx()
    await message.answer(
        "ℹ️ Информация о модели\n\n"
        f"Провайдер: ProxyAPI.ru (Gemini)\n"
        f"Модель: {ctx.ai.model_name}\n"
        "История: до 100 сообщений на диалог\n"
        "Хранилище: JSON (папка users/)",
        keyboard=settings_keyboard(),
    )


@labeler.private_message(rules.PayloadContainsRule({"cmd": "clear_history"}))
async def payload_clear_history(message: Message) -> None:
    ctx = get_ctx()
    dialog = await ctx.dialogs.clear_active_history(message.from_id)
    await message.answer(
        f"🧹 История диалога «{dialog.title}» очищена.",
        keyboard=settings_keyboard(),
    )
