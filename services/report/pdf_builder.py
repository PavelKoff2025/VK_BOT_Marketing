"""Генерация PDF-отчёта маркетингового аудита (кириллица)."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

from services.report.models import AuditReportData

# DejaVu — надёжная кириллица для fpdf2; системный Arial Unicode — запасной
DEFAULT_FONT_CANDIDATES = [
    Path(__file__).resolve().parents[2] / "assets" / "fonts" / "DejaVuSans.ttf",
    Path("/Library/Fonts/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
]


class AuditPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("ReportFont", size=9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Стр. {self.page_no()}/{{nb}}", align="C")


def _resolve_font() -> Path:
    for path in DEFAULT_FONT_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError(
        "Не найден TTF-шрифт с кириллицей. "
        "Положите DejaVuSans.ttf в assets/fonts/"
    )


def build_audit_pdf(data: AuditReportData, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    font_path = _resolve_font()

    pdf = AuditPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_margins(left=15, top=15, right=15)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_font("ReportFont", fname=str(font_path))
    pdf.add_page()
    pdf.set_x(pdf.l_margin)

    # Титул
    pdf.set_font("ReportFont", size=18)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(0, 10, "Отчёт по маркетинговому аудиту")
    pdf.ln(3)

    pdf.set_font("ReportFont", size=11)
    pdf.set_text_color(60, 60, 60)
    meta_lines = [
        f"Компания: {data.company_name}",
        f"Диалог: {data.dialog_title}",
        f"Дата: {data.generated_at or '—'}",
    ]
    for line in meta_lines:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 7, line)
    pdf.ln(5)

    for title, body in data.sections():
        content = (body or "").strip() or "Недостаточно данных в диалоге для заполнения раздела."
        pdf.set_x(pdf.l_margin)
        pdf.set_font("ReportFont", size=13)
        pdf.set_text_color(25, 55, 95)
        pdf.multi_cell(0, 8, title)
        pdf.ln(1)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("ReportFont", size=10)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 6, content)
        pdf.ln(4)

    pdf.set_x(pdf.l_margin)
    pdf.set_font("ReportFont", size=8)
    pdf.set_text_color(110, 110, 110)
    pdf.multi_cell(
        0,
        5,
        "Документ сформирован AI-маркетинг-консультантом на основе диалога. "
        "Проверьте цифры и факты перед принятием решений.",
    )

    pdf.output(str(output_path))
    return output_path
