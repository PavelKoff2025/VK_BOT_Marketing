"""Сервис PDF-отчёта маркетингового аудита."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config.settings import BASE_DIR
from models.dialog import Dialog
from models.message import ChatMessage
from services.ai.ai_service import AIService
from services.report.models import AuditReportData
from services.report.pdf_builder import build_audit_pdf
from utils.logging import get_logger

logger = get_logger(__name__)

REPORTS_DIR = BASE_DIR / "reports"

STRUCTURING_PROMPT = (
    "Ты готовишь структурированный отчёт первичного маркетингового аудита для PDF. "
    "На основе ответов клиента на 10 вопросов верни ТОЛЬКО валидный JSON "
    "без markdown и пояснений. Ключи JSON (все строки на русском):\n"
    "company_name, summary, analysis, conclusions, market_position, "
    "marketing_activities, landing_pages, unit_economics, risks, "
    "recommendations, next_steps, missing_data.\n"
    "Правила:\n"
    "— analysis: разбор по блокам стратегия/цифры/клиенты/продукт/процессы;\n"
    "— conclusions: 5–8 чётких выводов;\n"
    "— recommendations: приоритетные действия на 30/60/90 дней;\n"
    "— не выдумывай цифры клиента; если цифр нет — фиксируй как пробел;\n"
    "— отдельно отметь, что цифры «на слух» нужно сверить с CRM/Analytics."
)

VK_SUMMARY_PROMPT = (
    "Ты маркетинг-консультант. По ответам на 10 вопросов первичного аудита "
    "подготовь сообщение для клиента ВКонтакте на русском.\n"
    "Структура строго:\n"
    "1) Краткий анализ (7–12 предложений)\n"
    "2) Выводы (маркированный список 5–8 пунктов)\n"
    "3) Рекомендации (приоритеты: что сделать сначала)\n"
    "Без markdown-заголовков ##. Не выдумывай цифры. Пиши по делу."
)


class AuditReportService:
    def __init__(self, ai: AIService, reports_dir: Path | None = None) -> None:
        self.ai = ai
        self.reports_dir = reports_dir or REPORTS_DIR

    async def create_pdf_from_dialog(
        self,
        *,
        user_id: int,
        dialog: Dialog,
    ) -> tuple[Optional[Path], Optional[str]]:
        """
        Возвращает (path, error_message).
        """
        if len(dialog.messages) < 2:
            return None, (
                "Для PDF-отчёта нужно провести консультацию: "
                "минимум несколько сообщений в диалоге."
            )

        structured = await self._structure_report(dialog)
        if structured is None:
            return None, "Не удалось сформировать структуру отчёта. Попробуйте ещё раз."

        return self._write_pdf(user_id=user_id, dialog=dialog, structured=structured)

    async def create_pdf_from_answers(
        self,
        *,
        user_id: int,
        dialog: Dialog,
        answers: list,
    ) -> tuple[Optional[Path], Optional[str], Optional[AuditReportData]]:
        """PDF по результатам опроса из 10 вопросов."""
        qa_text = self._format_answers(answers)
        structured = await self._structure_from_qa(qa_text)
        if structured is None:
            return None, "Не удалось сформировать структуру отчёта.", None

        structured.qa_section = qa_text
        structured.dialog_title = dialog.title or "Первичный маркетинг-аудит"
        path, error = self._write_pdf(
            user_id=user_id,
            dialog=dialog,
            structured=structured,
        )
        return path, error, structured

    async def build_vk_summary(self, answers: list) -> str:
        qa_text = self._format_answers(answers)
        result = await self.ai.chat(
            mode_id="marketing",
            history=[],
            user_message=f"Ответы клиента:\n{qa_text}",
            system_prompt=VK_SUMMARY_PROMPT,
        )
        if result.ok and result.text.strip():
            return result.text.strip()
        return (
            "Анализ временно недоступен. "
            "PDF-отчёт всё равно будет сформирован по собранным ответам."
        )

    def _write_pdf(
        self,
        *,
        user_id: int,
        dialog: Dialog,
        structured: AuditReportData,
    ) -> tuple[Optional[Path], Optional[str]]:
        structured.dialog_title = structured.dialog_title or dialog.title
        structured.generated_at = datetime.now(timezone.utc).astimezone().strftime(
            "%d.%m.%Y %H:%M"
        )
        safe_name = re.sub(
            r"[^\w\-]+",
            "_",
            structured.company_name,
            flags=re.UNICODE,
        )[:40]
        filename = f"audit_{user_id}_{dialog.id[:8]}_{safe_name}.pdf"
        output_path = self.reports_dir / filename
        try:
            build_audit_pdf(structured, output_path)
            return output_path, None
        except Exception as exc:
            logger.exception("PDF build failed: %s", exc)
            return None, f"Ошибка генерации PDF: {exc}"

    async def _structure_from_qa(self, qa_text: str) -> Optional[AuditReportData]:
        result = await self.ai.chat(
            mode_id="marketing",
            history=[],
            user_message=(
                "Ответы на 10 вопросов первичного аудита:\n"
                f"{qa_text}\n\n"
                "Собери JSON-отчёт по инструкции."
            ),
            system_prompt=STRUCTURING_PROMPT,
        )
        if not result.ok or not result.text:
            logger.warning("AI Q&A structuring failed: %s", result.error)
            return self._fallback_from_qa(qa_text)

        parsed = self._extract_json(result.text)
        if not parsed:
            return self._fallback_from_qa(qa_text)
        data = AuditReportData.from_dict(parsed)
        data.qa_section = qa_text
        return data

    @staticmethod
    def _format_answers(answers: list) -> str:
        lines: list[str] = []
        for item in answers:
            number = getattr(item, "number", None)
            block = getattr(item, "block", "")
            question = getattr(item, "question", "")
            answer = getattr(item, "answer", "")
            if isinstance(item, dict):
                number = item.get("number")
                block = item.get("block", "")
                question = item.get("question", "")
                answer = item.get("answer", "")
            lines.append(
                f"Вопрос {number} [{block}]\n"
                f"Q: {question}\n"
                f"A: {answer}\n"
            )
        return "\n".join(lines)

    @staticmethod
    def _fallback_from_qa(qa_text: str) -> AuditReportData:
        return AuditReportData(
            company_name="Компания (уточнить)",
            dialog_title="Первичный маркетинг-аудит",
            summary="Отчёт собран по ответам опроса. Часть разделов требует уточнения цифр.",
            analysis=qa_text[:2500],
            conclusions="Недостаточно структурированных выводов — повторите генерацию или уточните метрики.",
            market_position="См. ответы на вопросы 1–2.",
            marketing_activities="См. ответы на вопросы 5–6.",
            landing_pages="См. ответы на вопросы 7–8.",
            unit_economics="См. ответы на вопросы 3–4.",
            recommendations="Сверить цифры с CRM/Analytics и приоритизировать каналы с лучшей экономикой.",
            next_steps="1) Проверить метрики в CRM 2) Зафиксировать УТП 3) Пересобрать приоритеты бюджета.",
            risks="Риск решений на цифрах «на слух».",
            missing_data="Нужны подтверждённые CAC/LTV/ROMI и стоимость лида по каналам.",
            qa_section=qa_text,
        )

    async def _structure_report(self, dialog: Dialog) -> Optional[AuditReportData]:
        transcript = self._format_transcript(dialog.messages)
        result = await self.ai.chat(
            mode_id="marketing",
            history=[],
            user_message=(
                "История консультации:\n"
                f"{transcript}\n\n"
                "Собери JSON-отчёт по инструкции."
            ),
            system_prompt=STRUCTURING_PROMPT,
        )
        if not result.ok or not result.text:
            logger.warning("AI structuring failed: %s", result.error)
            return self._fallback_from_history(dialog)

        parsed = self._extract_json(result.text)
        if not parsed:
            logger.warning("Failed to parse report JSON")
            return self._fallback_from_history(dialog)
        return AuditReportData.from_dict(parsed)

    @staticmethod
    def _format_transcript(messages: list[ChatMessage], limit: int = 40) -> str:
        lines: list[str] = []
        for msg in messages[-limit:]:
            role = "Клиент" if msg.role == "user" else "Консультант"
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)

    @staticmethod
    def _extract_json(text: str) -> Optional[dict]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _fallback_from_history(dialog: Dialog) -> AuditReportData:
        assistant_parts = [
            m.content for m in dialog.messages if m.role == "assistant"
        ]
        joined = "\n\n".join(assistant_parts[-5:]) if assistant_parts else ""
        return AuditReportData(
            company_name="Компания (уточнить)",
            dialog_title=dialog.title,
            summary=(
                "Отчёт собран по последним ответам консультанта. "
                "Рекомендуется дополнить диалог цифрами и деталями."
            ),
            market_position=joined or "Недостаточно данных.",
            marketing_activities="См. раздел рыночного положения / историю диалога.",
            landing_pages="Недостаточно данных в структурированном виде.",
            unit_economics="Недостаточно данных для unit-экономики.",
            recommendations="Продолжите консультацию и запросите PDF повторно.",
            next_steps="Собрать недостающие данные и повторить аудит.",
            risks="Высокая неопределённость из-за неполного контекста.",
            missing_data="Нужны: ниша, ЦА, каналы, бюджеты, метрики воронки, данные LP.",
        )
