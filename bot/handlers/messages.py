"""Обработка обычных сообщений и pending-действий + AI."""

from __future__ import annotations

import asyncio

from vkbottle.bot import BotLabeler, Message

from bot.context import get_ctx
from bot.handlers.menu import MENU_TEXTS, send_main_menu
from config.prompts import get_mode_prompt, get_mode_title
from config.settings import settings
from keyboards.menus import main_menu_keyboard, pdf_offer_keyboard
from utils.logging import get_logger
from utils.validators import sanitize_user_text, truncate_for_vk

logger = get_logger(__name__)
labeler = BotLabeler()


async def _set_typing(message: Message) -> None:
    try:
        await message.ctx_api.messages.set_activity(
            peer_id=message.peer_id,
            type="typing",
            group_id=message.group_id,
        )
    except Exception as exc:
        logger.debug("typing failed: %s", exc)


@labeler.private_message()
async def handle_text(message: Message) -> None:
    """
    Универсальный хендлер текста.
    Payload-кнопки и пункты меню обрабатываются другими labelers —
    сюда попадают обычные сообщения и ответы на pending.
    """
    if message.payload:
        return

    text = message.text or ""
    if text in MENU_TEXTS:
        return

    # Дополнительный перехват команд меню (регистр не важен)
    lowered = text.strip().lower()
    if lowered in {
        "меню",
        "начать",
        "/start",
        "start",
        "команды",
        "помощь",
        "/help",
        "help",
        "что ты умеешь",
        "что умеешь",
    }:
        if "помощ" in lowered or "умеешь" in lowered or lowered in {"/help", "help"}:
            from bot.handlers.menu import help_menu

            await help_menu(message)
        else:
            await send_main_menu(message)
        return

    if lowered in {"pdf", "отчёт", "отчет", "/pdf", "/report", "отчёт pdf", "отчет pdf"}:
        from bot.handlers.report import generate_and_send_pdf

        await generate_and_send_pdf(message)
        return

    if lowered in {"аудит", "/audit", "первичный аудит"}:
        from bot.handlers.audit import start_audit

        await start_audit(message)
        return

    ctx = get_ctx()
    state = await ctx.dialogs.get_user(message.from_id)
    pending = state.settings.pending_action

    if pending == "await_audit_answer":
        ok, cleaned, error = sanitize_user_text(
            text,
            max_length=settings.max_message_length,
        )
        if not ok:
            from keyboards.menus import audit_keyboard

            await message.answer(
                error or "Напишите ответ на текущий вопрос.",
                keyboard=audit_keyboard(),
            )
            return
        from bot.handlers.audit import handle_audit_answer

        await handle_audit_answer(message, cleaned)
        return

    if pending == "await_new_dialog_title":
        title = text.strip()
        if title.lower() in {"пропустить", "skip", "-"}:
            title = "Новый диалог"
        dialog = await ctx.dialogs.create_dialog(message.from_id, title=title)
        await message.answer(
            f"🆕 Создан диалог «{dialog.title}»\n"
            f"Режим: {get_mode_title(dialog.mode)}\n"
            "Можете начинать общение.",
            keyboard=main_menu_keyboard(),
        )
        return

    if pending == "await_rename_title":
        dialog_id = state.settings.pending_dialog_id
        if not dialog_id:
            await ctx.dialogs.clear_pending(message.from_id)
            await send_main_menu(message, "Не удалось переименовать диалог.")
            return
        dialog = await ctx.dialogs.rename_dialog(
            message.from_id,
            dialog_id,
            text,
        )
        if not dialog:
            await message.answer("Диалог не найден.", keyboard=main_menu_keyboard())
            return
        await message.answer(
            f"✏️ Диалог переименован: «{dialog.title}»",
            keyboard=main_menu_keyboard(),
        )
        return

    ok, cleaned, error = sanitize_user_text(
        text,
        max_length=settings.max_message_length,
    )
    if not ok:
        await message.answer(error or "Некорректное сообщение.", keyboard=main_menu_keyboard())
        return

    await _chat_with_ai(message, cleaned)


async def _chat_with_ai(message: Message, user_text: str) -> None:
    ctx = get_ctx()
    state = await ctx.dialogs.get_user(message.from_id)
    dialog = state.get_active_dialog()
    system_prompt = get_mode_prompt(dialog.mode)

    history = ctx.memory.build_context_window(dialog, system_prompt)
    think_msg = await message.answer("⏳ Бот думает...")
    await _set_typing(message)

    typing_task = asyncio.create_task(_typing_loop(message))
    try:
        result = await ctx.ai.chat(
            mode_id=dialog.mode,
            history=history,
            user_message=user_text,
            system_prompt=system_prompt,
        )
        await ctx.dialogs.append_exchange(
            message.from_id,
            user_text,
            result.text,
        )
        reply = truncate_for_vk(result.text)
        keyboard = (
            pdf_offer_keyboard()
            if dialog.mode == "marketing"
            else main_menu_keyboard()
        )
        await message.answer(reply, keyboard=keyboard)
        if dialog.mode == "marketing":
            await message.answer(
                "Можно сформировать PDF-отчёт по аудиту кнопкой выше "
                "или «📄 PDF-отчёт» в меню.",
                keyboard=main_menu_keyboard(),
            )
    except Exception as exc:
        logger.exception("Chat pipeline failed: %s", exc)
        await message.answer(
            settings.fallback_reply,
            keyboard=main_menu_keyboard(),
        )
    finally:
        typing_task.cancel()
        if think_msg:
            try:
                await message.ctx_api.messages.delete(
                    peer_id=message.peer_id,
                    message_ids=[think_msg],
                    delete_for_all=1,
                )
            except Exception:
                pass


async def _typing_loop(message: Message) -> None:
    try:
        while True:
            await _set_typing(message)
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        return
