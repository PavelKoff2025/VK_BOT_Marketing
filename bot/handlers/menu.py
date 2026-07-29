"""Обработчики главного меню и помощи."""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message, rules

from bot.context import get_ctx
from keyboards.menus import (
    help_keyboard,
    main_menu_keyboard,
    menu_inline_keyboard,
    modes_keyboard,
    settings_keyboard,
)
from utils.logging import get_logger

logger = get_logger(__name__)
labeler = BotLabeler()

START_TEXTS = [
    "Начать",
    "начать",
    "/start",
    "start",
    "меню",
    "Меню",
    "📋 Меню",
    "🏠 В меню",
    "команды",
    "Команды",
]

HELP_TEXTS = [
    "❓ Помощь",
    "помощь",
    "Помощь",
    "/help",
    "help",
    "что ты умеешь",
    "Что ты умеешь",
    "что умеешь",
    "Что умеешь",
]

MENU_TEXTS = set(START_TEXTS + HELP_TEXTS + [
    "🆕 Новый диалог",
    "💬 Список диалогов",
    "🎭 Сменить режим",
    "⚙️ Настройки",
    "📄 PDF-отчёт",
    "pdf",
    "PDF",
    "отчёт",
    "отчет",
    "/pdf",
    "/report",
    "🔍 Первичный аудит",
    "первичный аудит",
    "Первичный аудит",
    "/audit",
    "аудит",
    "❌ Отменить аудит",
    "отменить аудит",
    "Отменить аудит",
])


def build_menu_text(status: str) -> str:
    return (
        "📋 Главное меню\n\n"
        "Я AI-помощник ВКонтакте. Пишите обычным текстом — "
        "или выбирайте кнопки ниже.\n\n"
        "Что умею:\n"
        "• 🔍 Первичный аудит — 10 вопросов, затем отчёт и PDF\n"
        "• 🆕 Новый диалог — отдельный контекст\n"
        "• 💬 Список диалогов — переключение и удаление\n"
        "• 🎭 Сменить режим — помощник, программист, маркетинг…\n"
        "• 📄 PDF-отчёт — отчёт по текущему диалогу\n"
        "• ⚙️ Настройки — модель и очистка истории\n"
        "• ❓ Помощь — подсказки\n\n"
        f"{status}"
    )


def build_help_text() -> str:
    return (
        "❓ Помощь\n\n"
        "Как пользоваться:\n"
        "1. Напишите вопрос обычным текстом\n"
        "2. Или нажмите кнопки меню внизу экрана\n\n"
        "Первичный маркетинг-аудит:\n"
        "1. Нажмите «🔍 Первичный аудит»\n"
        "2. Ответьте на 10 вопросов по одному\n"
        "3. Получите анализ, выводы, рекомендации и PDF\n\n"
        "Команды:\n"
        "• меню / Начать\n"
        "• аудит / /audit\n"
        "• отчёт / pdf\n\n"
        "Память: до 100 последних сообщений активного диалога."
    )


@labeler.private_message(text=START_TEXTS)
async def cmd_start(message: Message) -> None:
    await show_main_menu(message)


@labeler.private_message(text=HELP_TEXTS)
async def help_menu(message: Message) -> None:
    await message.answer(
        build_help_text(),
        keyboard=help_keyboard(),
    )
    # Подкрепляем постоянную клавиатуру внизу
    await message.answer(
        "Кнопки меню закреплены внизу чата 👇",
        keyboard=main_menu_keyboard(),
    )


@labeler.private_message(rules.PayloadContainsRule({"cmd": "help"}))
async def payload_help(message: Message) -> None:
    await help_menu(message)


@labeler.private_message(text="🆕 Новый диалог")
async def new_dialog(message: Message) -> None:
    ctx = get_ctx()
    await ctx.dialogs.set_pending(message.from_id, "await_new_dialog_title")
    await message.answer(
        "Как назвать новый диалог?\n"
        "Отправьте название сообщением или напишите «Пропустить».",
        keyboard=main_menu_keyboard(),
    )


@labeler.private_message(rules.PayloadContainsRule({"cmd": "new_dialog"}))
async def payload_new_dialog(message: Message) -> None:
    await new_dialog(message)


@labeler.private_message(text="🎭 Сменить режим")
async def change_mode_menu(message: Message) -> None:
    await message.answer(
        "Выберите режим общения для текущего диалога:",
        keyboard=modes_keyboard(),
    )


@labeler.private_message(text="⚙️ Настройки")
async def settings_menu(message: Message) -> None:
    ctx = get_ctx()
    status = await ctx.dialogs.status_text(message.from_id)
    await message.answer(
        f"⚙️ Настройки\n\n{status}\nМодель: {ctx.ai.model_name}",
        keyboard=settings_keyboard(),
    )


@labeler.private_message(rules.PayloadContainsRule({"cmd": "open_settings"}))
async def payload_open_settings(message: Message) -> None:
    await settings_menu(message)


async def show_main_menu(message: Message, prefix: str | None = None) -> None:
    ctx = get_ctx()
    state = await ctx.dialogs.get_user(message.from_id)
    # выход в меню прерывает незавершённый опрос
    if state.settings.pending_action == "await_audit_answer":
        state.clear_audit_session()
        await ctx.dialogs.save_user(state)
        prefix = (prefix + "\n\n" if prefix else "") + "Активный аудит был прерван."
    else:
        await ctx.dialogs.clear_pending(message.from_id)
    status = await ctx.dialogs.status_text(message.from_id)
    text = build_menu_text(status)
    if prefix:
        text = f"{prefix}\n\n{text}"
    await message.answer(text, keyboard=menu_inline_keyboard())
    await message.answer(
        "Постоянные кнопки меню внизу 👇",
        keyboard=main_menu_keyboard(),
    )


async def send_main_menu(message: Message, text: str | None = None) -> None:
    await show_main_menu(message, prefix=text)
