"""Генерация и отправка PDF-отчёта маркетингового аудита."""

from __future__ import annotations

from pathlib import Path

from vkbottle import DocMessagesUploader
from vkbottle.bot import BotLabeler, Message, rules

from bot.context import get_ctx
from keyboards.menus import main_menu_keyboard, modes_keyboard
from utils.logging import get_logger

logger = get_logger(__name__)
labeler = BotLabeler()

PDF_TEXTS = [
    "📄 PDF-отчёт",
    "pdf",
    "PDF",
    "отчёт",
    "отчет",
    "отчёт pdf",
    "отчет pdf",
    "/pdf",
    "/report",
]


@labeler.private_message(text=PDF_TEXTS)
async def pdf_report_command(message: Message) -> None:
    await generate_and_send_pdf(message)


@labeler.private_message(rules.PayloadContainsRule({"cmd": "pdf_report"}))
async def pdf_report_payload(message: Message) -> None:
    await generate_and_send_pdf(message)


async def generate_and_send_pdf(message: Message) -> None:
    ctx = get_ctx()
    state = await ctx.dialogs.get_user(message.from_id)
    dialog = state.get_active_dialog()

    if dialog.mode != "marketing":
        await message.answer(
            "📄 PDF-отчёт доступен в режиме «🎯 Маркетинг-консультант».\n"
            "Сначала смените режим, проведите аудит, затем запросите отчёт.",
            keyboard=modes_keyboard(),
        )
        return

    await message.answer(
        "⏳ Формирую PDF-отчёт по аудиту...\n"
        "Это может занять немного времени.",
        keyboard=main_menu_keyboard(),
    )

    path, error = await ctx.reports.create_pdf_from_dialog(
        user_id=message.from_id,
        dialog=dialog,
    )
    if error or path is None:
        await message.answer(
            error or "Не удалось создать отчёт.",
            keyboard=main_menu_keyboard(),
        )
        return

    try:
        attachment = await _upload_pdf(message, path)
        await message.answer(
            "📄 Готово! Отчёт по маркетинговому аудиту во вложении.\n"
            f"Диалог: «{dialog.title}»",
            attachment=attachment,
            keyboard=main_menu_keyboard(),
        )
    except Exception as exc:
        logger.exception("PDF upload/send failed: %s", exc)
        await message.answer(
            "Отчёт создан, но не удалось отправить файл в VK. "
            "Проверьте права сообщества на документы и попробуйте снова.",
            keyboard=main_menu_keyboard(),
        )
    finally:
        _safe_unlink(path)


async def _upload_pdf(message: Message, path: Path) -> str:
    uploader = DocMessagesUploader(message.ctx_api)
    return await uploader.upload(
        file_source=str(path),
        peer_id=message.peer_id,
        title=path.name,
    )


def _safe_unlink(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError as exc:
        logger.debug("Could not remove temp PDF %s: %s", path, exc)
