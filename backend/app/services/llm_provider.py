"""
LLM Provider abstraction.

Supported providers (set via LLM_PROVIDER in .env):
  openrouter   → OpenRouter free-tier models, auto-rotates on rate limit  ← default
  gemini       → Google Gemini direct API
  ollama       → Self-hosted Ollama on private VPS
  openai_compat → Any OpenAI-compatible endpoint (vLLM, LM Studio, etc.)
"""

import logging
import time
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)


class QuotaExceededError(RuntimeError):
    """All models/quotas exhausted — caller should use fallback text."""


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 200, temperature: float = 0.8) -> str:
        ...


# ─── OpenRouter Provider ──────────────────────────────────────────────────────

class OpenRouterProvider(LLMProvider):
    """
    Uses OpenRouter's free-tier models.
    Automatically rotates to the next model when a rate-limit (429) is hit.

    Free models tried in order of quality:
      1. google/gemini-2.0-flash-exp:free      — best quality, Gemini 2.0
      2. meta-llama/llama-3.1-8b-instruct:free — very strong instruction following
      3. qwen/qwen-2.5-7b-instruct:free        — reliable, good quality
      4. google/gemma-3-4b-it:free             — fast Google model
      5. mistralai/mistral-7b-instruct:free    — battle-tested baseline

    Each model has its own rate-limit bucket — rotating gives effectively
    unlimited free throughput for low-to-mid request volumes.
    """

    _BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    _FREE_MODELS = [
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.1-8b-instruct:free",
        "qwen/qwen-2.5-7b-instruct:free",
        "google/gemma-3-4b-it:free",
        "mistralai/mistral-7b-instruct:free",
    ]

    _SYSTEM_PROMPT = (
        "You are a review-writing assistant for local businesses. "
        "Write short, authentic-sounding Google reviews exactly as instructed. "
        "Output ONLY the review text — no preamble, no quotes, no markdown."
    )

    def __init__(self, api_key: str, site_url: str = "", app_name: str = "GMB Review Generator"):
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": site_url or "http://localhost:5173",
            "X-Title": app_name,
        }
        self._client = httpx.Client(timeout=45.0)

    def _call(self, model: str, prompt: str, max_tokens: int, temperature: float) -> str | None:
        """
        Make a single model call.
        Returns the text on success, None if the response is empty/filtered.
        Raises QuotaExceededError on 429, RuntimeError on other HTTP errors.
        """
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": self._SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.95,
        }

        try:
            resp = self._client.post(self._BASE_URL, json=payload, headers=self._headers)
        except httpx.RequestError as e:
            raise RuntimeError(f"OpenRouter network error: {e}") from e

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After", "")
            logger.warning("OpenRouter 429 on model=%s  Retry-After=%s", model, retry_after)
            raise _RateLimitError(model)

        if resp.status_code == 503:
            logger.warning("OpenRouter 503 (model unavailable): %s", model)
            raise _ModelUnavailableError(model)

        if not resp.is_success:
            body = resp.text[:300]
            raise RuntimeError(f"OpenRouter HTTP {resp.status_code} for {model}: {body}")

        data = resp.json()

        # OpenRouter surfaces per-model errors inside a 200 body
        if "error" in data:
            err = data["error"]
            code = err.get("code") or err.get("status") or 0
            msg = err.get("message", str(err))
            if str(code) == "429" or "rate" in msg.lower() or "quota" in msg.lower():
                logger.warning("OpenRouter model-level rate limit: %s — %s", model, msg)
                raise _RateLimitError(model)
            raise RuntimeError(f"OpenRouter model error ({model}): {msg}")

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            logger.warning("OpenRouter empty/malformed response for model=%s", model)
            return None

        return text.strip() if text else None

    def generate(self, prompt: str, max_tokens: int = 200, temperature: float = 0.8) -> str:
        last_exc: Exception = RuntimeError("No models attempted")

        for model in self._FREE_MODELS:
            try:
                text = self._call(model, prompt, max_tokens, temperature)
                if text:
                    logger.info("OpenRouter success: model=%s  chars=%d", model, len(text))
                    return text
                # Empty response — try next model
                logger.warning("OpenRouter empty content from model=%s, trying next", model)

            except (_RateLimitError, _ModelUnavailableError) as e:
                last_exc = e
                continue

            except RuntimeError:
                raise  # real errors bubble up immediately

        raise QuotaExceededError(
            f"All OpenRouter free models exhausted or unavailable: {self._FREE_MODELS}"
        ) from last_exc


class _RateLimitError(Exception):
    pass

class _ModelUnavailableError(Exception):
    pass


# ─── Gemini Provider ──────────────────────────────────────────────────────────

class GeminiProvider(LLMProvider):
    _MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash-8b"]

    def __init__(self, api_key: str):
        from google import genai
        from google.genai import types as genai_types
        self._types = genai_types
        self._client = genai.Client(api_key=api_key)

    def generate(self, prompt: str, max_tokens: int = 200, temperature: float = 0.8) -> str:
        from google.genai import errors as genai_errors

        last_err = None
        for model in self._MODELS:
            try:
                response = self._client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=self._types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                        top_p=0.95,
                    ),
                )
                return response.text
            except genai_errors.APIError as e:
                code = getattr(e, "status_code", None) or getattr(e, "code", None)
                is_quota = code == 429 or "429" in str(e)[:30] or "RESOURCE_EXHAUSTED" in str(e)
                if is_quota:
                    logger.warning("Gemini quota on model=%s, trying next...", model)
                    last_err = e
                    continue
                raise RuntimeError(f"Gemini API error ({model}): {e}") from e

        raise QuotaExceededError("All Gemini models quota exhausted") from last_err


# ─── Ollama Provider ──────────────────────────────────────────────────────────

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str):
        self._url = base_url.rstrip("/") + "/api/generate"
        self._model = model
        self._client = httpx.Client(timeout=60.0)

    def generate(self, prompt: str, max_tokens: int = 200, temperature: float = 0.8) -> str:
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": 0.95,
                "stop": ["\n\n", "###"],
            },
        }
        try:
            resp = self._client.post(self._url, json=payload)
            resp.raise_for_status()
            return resp.json()["response"]
        except Exception as e:
            raise RuntimeError(f"Ollama error: {e}") from e


# ─── OpenAI-Compatible Provider ───────────────────────────────────────────────

class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str):
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._model = model
        self._client = httpx.Client(timeout=30.0)

    def generate(self, prompt: str, max_tokens: int = 200, temperature: float = 0.8) -> str:
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.95,
        }
        try:
            resp = self._client.post(self._url, json=payload, headers=self._headers)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"OpenAI-compat error: {e}") from e


# ─── Factory ──────────────────────────────────────────────────────────────────

def get_provider() -> LLMProvider:
    from app.core.settings import settings

    provider_name = (settings.llm_provider or "openrouter").lower()

    if provider_name == "openrouter":
        if not settings.openrouter_api_key:
            raise RuntimeError("LLM_PROVIDER=openrouter but OPENROUTER_API_KEY is not set")
        logger.info("LLM provider: OpenRouter (free model rotation)")
        return OpenRouterProvider(
            api_key=settings.openrouter_api_key,
            site_url=settings.frontend_url,
            app_name=settings.app_title,
        )

    if provider_name == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError("LLM_PROVIDER=gemini but GEMINI_API_KEY is not set")
        logger.info("LLM provider: Gemini")
        return GeminiProvider(api_key=settings.gemini_api_key)

    if provider_name == "ollama":
        if not settings.ollama_base_url:
            raise RuntimeError("LLM_PROVIDER=ollama but OLLAMA_BASE_URL is not set")
        model = settings.ollama_model or "llama3.2:3b"
        logger.info("LLM provider: Ollama @ %s  model=%s", settings.ollama_base_url, model)
        return OllamaProvider(base_url=settings.ollama_base_url, model=model)

    if provider_name == "openai_compat":
        if not settings.openai_compat_url:
            raise RuntimeError("LLM_PROVIDER=openai_compat but OPENAI_COMPAT_URL is not set")
        logger.info("LLM provider: OpenAI-compat @ %s", settings.openai_compat_url)
        return OpenAICompatibleProvider(
            base_url=settings.openai_compat_url,
            api_key=settings.openai_compat_key or "none",
            model=settings.openai_compat_model or "local-model",
        )

    raise RuntimeError(
        f"Unknown LLM_PROVIDER: {provider_name!r}. "
        "Valid options: openrouter | gemini | ollama | openai_compat"
    )
