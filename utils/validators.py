"""Валидация и нормализация пользовательского ввода."""

from __future__ import annotations

from typing import Optional


def sanitize_user_text(
    text: Optional[str],
    *,
    max_length: int,
) -> tuple[bool, str, Optional[str]]:
    """
    Возвращает (ok, cleaned_text, error_message).
    """
    if text is None:
        return False, "", "Пустое сообщение. Напишите текст или выберите кнопку меню."

    cleaned = text.strip()
    if not cleaned:
        return False, "", "Пустое сообщение. Напишите текст или выберите кнопку меню."

    if len(cleaned) > max_length:
        return (
            False,
            "",
            f"Сообщение слишком длинное. Максимум {max_length} символов.",
        )

    return True, cleaned, None


def truncate_for_vk(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20].rstrip() + "\n\n…(обрезано)"
