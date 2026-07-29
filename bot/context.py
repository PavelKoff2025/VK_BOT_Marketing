"""Общий контейнер зависимостей для хендлеров."""

from __future__ import annotations

from dataclasses import dataclass

from services.ai.ai_service import AIService
from services.audit_flow import AuditFlowService
from services.dialog_manager import DialogManager
from services.memory_manager import MemoryManager
from services.report.audit_report_service import AuditReportService


@dataclass(slots=True)
class AppContext:
    dialogs: DialogManager
    memory: MemoryManager
    ai: AIService
    reports: AuditReportService
    audit: AuditFlowService


# Заполняется при старте
ctx: AppContext | None = None


def get_ctx() -> AppContext:
    if ctx is None:
        raise RuntimeError("AppContext не инициализирован")
    return ctx
