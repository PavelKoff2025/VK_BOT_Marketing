"""Gemini через Google GenAI SDK и ProxyAPI.ru."""

from __future__ import annotations

from typing import Sequence

from google import genai
from google.genai import types

from services.ai.base import AIResponse, BaseAIProvider
from utils.logging import get_logger

logger = get_logger(__name__)


class GeminiProxyProvider(BaseAIProvider):
    """
    ProxyAPI совместим с официальным Gemini API / Google GenAI SDK.

    Endpoint: https://api.proxyapi.ru/google
    Auth: Authorization: Bearer <ключ> (+ x-goog-api-key от SDK)
    Docs: https://proxyapi.ru/docs/gemini-text-generation
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
    ) -> None:
        self.model_name = model.removeprefix("models/")
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                base_url=base_url.rstrip("/"),
                api_version="v1beta",
                headers={"Authorization": f"Bearer {api_key}"},
            ),
        )

    def _to_contents(
        self,
        messages: Sequence[dict[str, str]],
        user_message: str,
    ) -> list[types.Content]:
        contents: list[types.Content] = []

        for item in messages:
            role = item.get("role")
            content = (item.get("content") or "").strip()
            if not content or role not in {"user", "assistant"}:
                continue
            gemini_role = "user" if role == "user" else "model"
            contents.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part.from_text(text=content)],
                )
            )

        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_message)],
            )
        )
        return contents

    async def generate(
        self,
        *,
        system_prompt: str,
        messages: Sequence[dict[str, str]],
        user_message: str,
    ) -> AIResponse:
        contents = self._to_contents(messages, user_message)
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
        )

        try:
            response = await self._client.aio.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )
            text = (response.text or "").strip()
            if not text:
                return AIResponse(
                    text="",
                    ok=False,
                    error="empty_response",
                    model=self.model_name,
                )
            return AIResponse(text=text, ok=True, model=self.model_name)
        except Exception as exc:
            logger.exception("Gemini ProxyAPI error: %s", exc)
            return AIResponse(
                text="",
                ok=False,
                error=str(exc),
                model=self.model_name,
            )
