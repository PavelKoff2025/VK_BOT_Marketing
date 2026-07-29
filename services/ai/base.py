"""Абстракция AI-провайдера — легко подключать другие модели."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(slots=True)
class AIResponse:
    text: str
    ok: bool = True
    error: Optional[str] = None
    model: Optional[str] = None


class BaseAIProvider(ABC):
    model_name: str

    @abstractmethod
    async def generate(
        self,
        *,
        system_prompt: str,
        messages: Sequence[dict[str, str]],
        user_message: str,
    ) -> AIResponse:
        """messages — история без текущего user_message."""
        raise NotImplementedError
