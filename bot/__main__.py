"""Точка входа: python3 -m bot"""

from __future__ import annotations

from vkbottle.bot import Bot

import bot.context as app_context
from bot.context import AppContext
from bot.handlers import labelers
from config.settings import settings
from services.ai.ai_service import AIService
from services.audit_flow import AuditFlowService
from services.dialog_manager import DialogManager
from services.memory_manager import MemoryManager
from services.report.audit_report_service import AuditReportService
from storage.json_storage import JsonUserStorage
from utils.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


def build_app() -> Bot:
    storage = JsonUserStorage(settings.users_dir)
    memory = MemoryManager(max_messages=settings.max_history_messages)
    dialogs = DialogManager(storage=storage, memory=memory)
    ai = AIService(settings=settings)
    reports = AuditReportService(ai=ai)
    audit = AuditFlowService(dialogs=dialogs, memory=memory)

    app_context.ctx = AppContext(
        dialogs=dialogs,
        memory=memory,
        ai=ai,
        reports=reports,
        audit=audit,
    )

    vk_bot = Bot(token=settings.vk_token)
    for labeler in labelers:
        vk_bot.labeler.load(labeler)

    logger.info(
        "Bot ready | model=%s | history_limit=%s",
        ai.model_name,
        settings.max_history_messages,
    )
    return vk_bot


def main() -> None:
    vk_bot = build_app()
    # run() — актуальный API VKBottle (вместо устаревшего run_forever)
    if hasattr(vk_bot, "run"):
        vk_bot.run()
    else:
        vk_bot.run_forever()


if __name__ == "__main__":
    main()
