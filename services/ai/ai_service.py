"""Централизованный AIService с возможностью смены провайдера/модели."""

from __future__ import annotations

from typing import Optional, Sequence

from config.prompts import get_mode_prompt
from config.settings import Settings
from services.ai.base import AIResponse, BaseAIProvider
from services.ai.gemini_service import GeminiProxyProvider
from utils.logging import get_logger

logger = get_logger(__name__)


class AIService:
    def __init__(
        self,
        settings: Settings,
        provider: Optional[BaseAIProvider] = None,
    ) -> None:
        self.settings = settings
        self._provider = provider or GeminiProxyProvider(
            api_key=settings.proxy_api_key,
            model=settings.gemini_model,
            base_url=settings.proxyapi_google_base_url,
        )

    @property
    def model_name(self) -> str:
        return self._provider.model_name

    def set_provider(self, provider: BaseAIProvider) -> None:
        """Позволяет в будущем подключить Claude/GPT/OpenRouter и т.д."""
        self._provider = provider
        logger.info("AI provider switched to %s", provider.__class__.__name__)

    async def chat(
        self,
        *,
        mode_id: str,
        history: Sequence[dict[str, str]],
        user_message: str,
        system_prompt: Optional[str] = None,
    ) -> AIResponse:
        prompt = system_prompt or get_mode_prompt(mode_id)
        # history может уже содержать system — отфильтруем
        clean_history = [
            item
            for item in history
            if item.get("role") in {"user", "assistant"}
        ]

        result = await self._provider.generate(
            system_prompt=prompt,
            messages=clean_history,
            user_message=user_message,
        )

        if not result.ok:
            logger.warning("AI fallback used: %s", result.error)
            return AIResponse(
                text=self.settings.fallback_reply,
                ok=False,
                error=result.error,
                model=result.model or self.model_name,
            )
        return result
