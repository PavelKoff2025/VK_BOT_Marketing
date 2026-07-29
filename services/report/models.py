"""Модели структуры маркетингового PDF-отчёта."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AuditReportData:
    company_name: str = "Компания"
    dialog_title: str = "Диалог"
    summary: str = ""
    analysis: str = ""
    conclusions: str = ""
    market_position: str = ""
    marketing_activities: str = ""
    landing_pages: str = ""
    unit_economics: str = ""
    recommendations: str = ""
    next_steps: str = ""
    risks: str = ""
    missing_data: str = ""
    qa_section: str = ""
    generated_at: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditReportData:
        return cls(
            company_name=str(data.get("company_name") or "Компания").strip()[:120],
            dialog_title=str(data.get("dialog_title") or "Диалог").strip()[:120],
            summary=str(data.get("summary") or "").strip(),
            analysis=str(data.get("analysis") or "").strip(),
            conclusions=str(data.get("conclusions") or "").strip(),
            market_position=str(data.get("market_position") or "").strip(),
            marketing_activities=str(data.get("marketing_activities") or "").strip(),
            landing_pages=str(data.get("landing_pages") or "").strip(),
            unit_economics=str(data.get("unit_economics") or "").strip(),
            recommendations=str(data.get("recommendations") or "").strip(),
            next_steps=str(data.get("next_steps") or "").strip(),
            risks=str(data.get("risks") or "").strip(),
            missing_data=str(data.get("missing_data") or "").strip(),
            qa_section=str(data.get("qa_section") or "").strip(),
            generated_at=str(data.get("generated_at") or "").strip(),
        )

    def sections(self) -> list[tuple[str, str]]:
        return [
            ("Краткое резюме", self.summary),
            ("Анализ", self.analysis),
            ("Выводы", self.conclusions),
            ("1. Рыночное положение и стратегия", self.market_position),
            ("2. Маркетинговые активности и клиенты", self.marketing_activities),
            ("3. Продукт, контент и касания", self.landing_pages),
            ("4. Unit-экономика и метрики", self.unit_economics),
            ("5. Риски", self.risks),
            ("6. Рекомендации", self.recommendations),
            ("7. План действий", self.next_steps),
            ("8. Недостающие данные / что проверить в CRM", self.missing_data),
            ("Приложение: ответы на 10 вопросов", self.qa_section),
        ]
