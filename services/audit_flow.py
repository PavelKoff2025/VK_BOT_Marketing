"""Пошаговый сценарий первичного маркетингового аудита (10 вопросов)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from config.audit_questions import (
    format_question_message,
    get_question,
    total_questions,
)
from models.dialog import Dialog
from models.user import AuditAnswer, UserState
from services.dialog_manager import DialogManager
from services.memory_manager import MemoryManager


@dataclass(slots=True)
class AuditStepResult:
    """Результат обработки шага аудита."""

    message: str
    finished: bool = False
    dialog: Optional[Dialog] = None
    answers: list[AuditAnswer] | None = None


class AuditFlowService:
    def __init__(
        self,
        dialogs: DialogManager,
        memory: MemoryManager,
    ) -> None:
        self.dialogs = dialogs
        self.memory = memory

    async def start(self, user_id: int) -> AuditStepResult:
        state = await self.dialogs.get_user(user_id)
        dialog = Dialog.create(
            title="Первичный маркетинг-аудит",
            mode="marketing",
        )
        state.dialogs.append(dialog)
        state.active_dialog_id = dialog.id
        state.settings.default_mode = "marketing"
        state.settings.clear_audit()
        state.settings.pending_action = "await_audit_answer"
        state.settings.audit_index = 0
        await self.dialogs.save_user(state)

        intro = (
            "🔍 Запускаю первичный маркетинговый аудит.\n\n"
            f"Будет {total_questions()} вопросов — по одному.\n"
            "Отвечайте развёрнуто, как на интервью с владельцем/СМО.\n"
            "После последнего ответа подготовлю анализ, выводы, "
            "рекомендации и PDF-отчёт.\n\n"
            "Чтобы прервать — нажмите «❌ Отменить аудит»."
        )
        question = format_question_message(0)
        self.memory.add_message(dialog, "assistant", f"{intro}\n\n{question}")
        await self.dialogs.save_user(state)

        return AuditStepResult(
            message=f"{intro}\n\n{question}",
            finished=False,
            dialog=dialog,
        )

    async def cancel(self, user_id: int) -> str:
        state = await self.dialogs.get_user(user_id)
        answered = len(state.settings.audit_answers)
        state.clear_audit_session()
        await self.dialogs.save_user(state)
        if answered:
            return (
                f"❌ Аудит отменён. Сохранено ответов: {answered}. "
                "Можете начать заново кнопкой «🔍 Первичный аудит»."
            )
        return "❌ Аудит отменён."

    def is_active(self, state: UserState) -> bool:
        return state.settings.pending_action == "await_audit_answer"

    async def submit_answer(
        self,
        user_id: int,
        answer_text: str,
    ) -> AuditStepResult:
        state = await self.dialogs.get_user(user_id)
        if not self.is_active(state):
            return AuditStepResult(
                message="Сейчас аудит не активен. Нажмите «🔍 Первичный аудит».",
                finished=False,
            )

        index = state.settings.audit_index
        question = get_question(index)
        if not question:
            state.clear_audit_session()
            await self.dialogs.save_user(state)
            return AuditStepResult(
                message="Сессия аудита повреждена. Запустите заново.",
                finished=False,
            )

        dialog = state.get_active_dialog()
        cleaned = answer_text.strip()
        self.memory.add_message(dialog, "user", cleaned)

        state.settings.audit_answers.append(
            AuditAnswer(
                number=question.number,
                block=question.block,
                question=question.text,
                answer=cleaned,
            )
        )

        next_index = index + 1
        if next_index >= total_questions():
            answers = list(state.settings.audit_answers)
            state.settings.pending_action = None
            state.settings.audit_index = next_index
            await self.dialogs.save_user(state)
            return AuditStepResult(
                message=(
                    "✅ Все 10 ответов получены.\n"
                    "Формирую анализ, выводы и рекомендации…"
                ),
                finished=True,
                dialog=dialog,
                answers=answers,
            )

        state.settings.audit_index = next_index
        next_q = format_question_message(next_index)
        self.memory.add_message(dialog, "assistant", next_q)
        await self.dialogs.save_user(state)

        return AuditStepResult(
            message=(
                f"✅ Ответ {question.number}/{total_questions()} сохранён.\n\n"
                f"{next_q}"
            ),
            finished=False,
            dialog=dialog,
        )
