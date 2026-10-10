from typing import Any, Protocol

import httpx

from doc_holler.core.config import Settings
from doc_holler.core.errors import LLMConfigurationError, LLMProviderError


class OpenRouterClientProtocol(Protocol):
    def complete_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
    ) -> str: ...


class OpenRouterClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def complete_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
    ) -> str:
        api_key = self.settings.openrouter_api_key.strip()
        model = self.settings.openrouter_model.strip()

        if not api_key:
            raise LLMConfigurationError("OPENROUTER_API_KEY is not configured")
        if not model:
            raise LLMConfigurationError("OPENROUTER_MODEL is not configured")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/doc-holler",
            "X-Title": "Doc Holler",
        }

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        url = f"{self.settings.openrouter_base_url.rstrip('/')}/chat/completions"

        try:
            with httpx.Client(timeout=self.settings.openrouter_timeout_seconds) as client:
                response = client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise LLMProviderError("OpenRouter request timed out") from exc
        except httpx.RequestError as exc:
            raise LLMProviderError(f"Network error contacting OpenRouter: {exc}") from exc

        if response.status_code == 401 or response.status_code == 403:
            raise LLMProviderError("OpenRouter authentication failed: invalid API key")
        if response.status_code == 429:
            raise LLMProviderError("OpenRouter rate limit exceeded")
        if response.status_code >= 400:
            error_detail = ""
            try:
                err_data = response.json()
                if isinstance(err_data, dict) and "error" in err_data:
                    err_obj = err_data["error"]
                    if isinstance(err_obj, dict) and "message" in err_obj:
                        error_detail = f": {err_obj['message']}"
                    elif isinstance(err_obj, str):
                        error_detail = f": {err_obj}"
            except Exception:
                pass
            msg = f"OpenRouter returned HTTP error {response.status_code}{error_detail}"
            raise LLMProviderError(msg)

        try:
            data = response.json()
        except Exception as exc:
            raise LLMProviderError("Failed to parse OpenRouter response JSON") from exc

        choices = data.get("choices")
        if not choices or not isinstance(choices, list):
            raise LLMProviderError("OpenRouter response did not contain any completion choices")

        first_choice = choices[0]
        message = first_choice.get("message", {})
        content = message.get("content")
        if not content or not isinstance(content, str):
            raise LLMProviderError("OpenRouter response did not contain message content")

        return content.strip()
