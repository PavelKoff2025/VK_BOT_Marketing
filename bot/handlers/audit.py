"""Обработчики первичного маркетингового аудита (10 вопросов)."""

from __future__ import annotations

from pathlib import Path

from vkbottle import DocMessagesUploader
from vkbottle.bot import BotLabeler, Message, rules

from bot.context import get_ctx
from keyboards.menus import audit_keyboard, main_menu_keyboard
from utils.logging import get_logger
from utils.validators import truncate_for_vk

logger = get_logger(__name__)
labeler = BotLabeler()

AUDIT_START_TEXTS = [
    "🔍 Первичный аудит",
    "первичный аудит",
    "Первичный аудит",
    "/audit",
    "аудит",
]

AUDIT_CANCEL_TEXTS = [
    "❌ Отменить аудит",
    "отменить аудит",
    "Отменить аудит",
]


@labeler.private_message(text=AUDIT_START_TEXTS)
async def start_audit(message: Message) -> None:
    ctx = get_ctx()
    result = await ctx.audit.start(message.from_id)
    await message.answer(result.message, keyboard=audit_keyboard())


@labeler.private_message(rules.PayloadContainsRule({"cmd": "start_audit"}))
async def start_audit_payload(message: Message) -> None:
    await start_audit(message)


@labeler.private_message(text=AUDIT_CANCEL_TEXTS)
async def cancel_audit(message: Message) -> None:
    ctx = get_ctx()
    text = await ctx.audit.cancel(message.from_id)
    await message.answer(text, keyboard=main_menu_keyboard())


@labeler.private_message(rules.PayloadContainsRule({"cmd": "cancel_audit"}))
async def cancel_audit_payload(message: Message) -> None:
    await cancel_audit(message)


async def handle_audit_answer(message: Message, answer_text: str) -> None:
    ctx = get_ctx()
    step = await ctx.audit.submit_answer(message.from_id, answer_text)

    if not step.finished:
        await message.answer(step.message, keyboard=audit_keyboard())
        return

    await message.answer(step.message, keyboard=main_menu_keyboard())
    await _finish_audit_and_report(
        message,
        dialog=step.dialog,
        answers=step.answers or [],
    )


async def _finish_audit_and_report(message: Message, dialog, answers: list) -> None:
    ctx = get_ctx()
    if dialog is None:
        await message.answer(
            "Не удалось найти диалог аудита.",
            keyboard=main_menu_keyboard(),
        )
        return

    try:
        summary = await ctx.reports.build_vk_summary(answers)
        await ctx.dialogs.append_exchange(
            message.from_id,
            "Завершение первичного аудита (10/10)",
            summary,
        )
        await message.answer(
            truncate_for_vk(summary),
            keyboard=main_menu_keyboard(),
        )
    except Exception as exc:
        logger.exception("Audit VK summary failed: %s", exc)
        await message.answer(
            "Не удалось сформировать текстовый анализ, готовлю PDF…",
            keyboard=main_menu_keyboard(),
        )

    await message.answer("⏳ Формирую PDF-отчёт…", keyboard=main_menu_keyboard())
    path, error, _structured = await ctx.reports.create_pdf_from_answers(
        user_id=message.from_id,
        dialog=dialog,
        answers=answers,
    )
    if error or path is None:
        await message.answer(
            error or "Не удалось создать PDF.",
            keyboard=main_menu_keyboard(),
        )
        return

    try:
        attachment = await _upload_pdf(message, path)
        await message.answer(
            "📄 PDF-отчёт первичного маркетингового аудита готов.",
            attachment=attachment,
            keyboard=main_menu_keyboard(),
        )
    except Exception as exc:
        logger.exception("Audit PDF upload failed: %s", exc)
        await message.answer(
            "Отчёт создан, но не удалось отправить файл в VK.",
            keyboard=main_menu_keyboard(),
        )
    finally:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass

    # очистка сессии аудита после завершения
    state = await ctx.dialogs.get_user(message.from_id)
    state.clear_audit_session()
    await ctx.dialogs.save_user(state)


async def _upload_pdf(message: Message, path: Path) -> str:
    uploader = DocMessagesUploader(message.ctx_api)
    return await uploader.upload(
        file_source=str(path),
        peer_id=message.peer_id,
        title=path.name,
    )
