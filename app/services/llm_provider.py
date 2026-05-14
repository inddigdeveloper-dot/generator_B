"""
LLM Provider abstraction with automatic fallback chain.

Priority order (first available wins):
  1. Gemini free  — google/gemini-2.0-flash (direct Google API, free tier)
  2. Groq free    — llama-3.1-8b-instant  (very fast, generous free tier)
  3. OpenRouter paid — gemini-2.0-flash   (~$9/month at 1K users/day)
  4. OpenRouter free — rotating free models (fallback of last resort)
"""
import logging
import httpx

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = ( 
    "You are a review-writing assistant for local businesses. "
    "Write short, authentic-sounding Google reviews exactly as instructed. "
    "Output ONLY the review text — no preamble, no quotes, no markdown."
)


class QuotaExceededError(RuntimeError):
    """All models/quotas exhausted — caller should use fallback text."""


class LLMProvider:
    def generate(self, prompt: str, max_tokens: int = 200, temperature: float = 0.8) -> str:
        raise NotImplementedError


class _RateLimitError(Exception):
    pass

class _ModelUnavailableError(Exception):
    pass


# ─── Gemini (Google direct API — free tier) ───────────────────────────────────

class GeminiProvider(LLMProvider):
    _MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash-8b"]

    def __init__(self, api_key: str):
        from google import genai
        from google.genai import types as genai_types
        self._types  = genai_types
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
                        system_instruction=_SYSTEM_PROMPT,
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                        top_p=0.95,
                    ),
                )
                return response.text.strip()
            except genai_errors.APIError as e:
                code = getattr(e, "status_code", None) or getattr(e, "code", None)
                if code == 429 or "RESOURCE_EXHAUSTED" in str(e):
                    logger.warning("Gemini quota on %s, trying next model", model)
                    last_err = e
                    continue
                raise RuntimeError(f"Gemini API error ({model}): {e}") from e
        raise QuotaExceededError("All Gemini models quota exhausted") from last_err


# ─── Groq (free tier — OpenAI-compatible, very fast) ─────────────────────────

class GroqProvider(LLMProvider):
    _BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
    _MODELS = [
        "llama-3.1-8b-instant",
        "gemma2-9b-it",
        "llama3-8b-8192",
    ]

    def __init__(self, api_key: str):
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, prompt: str, max_tokens: int = 200, temperature: float = 0.8) -> str:
        last_err = None
        for model in self._MODELS:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                "max_tokens":  max_tokens,
                "temperature": temperature,
                "top_p": 0.95,
            }
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(self._BASE_URL, json=payload, headers=self._headers)
                if resp.status_code == 429:
                    logger.warning("Groq 429 on %s, trying next model", model)
                    last_err = _RateLimitError(model)
                    continue
                if not resp.is_success:
                    raise RuntimeError(f"Groq HTTP {resp.status_code}: {resp.text[:200]}")
                text = resp.json()["choices"][0]["message"]["content"]
                if text:
                    logger.info("Groq success: model=%s", model)
                    return text.strip()
            except _RateLimitError:
                continue
            except httpx.RequestError as e:
                raise RuntimeError(f"Groq network error: {e}") from e
        raise QuotaExceededError("All Groq models exhausted") from last_err


# ─── OpenRouter (paid models first, free as fallback) ────────────────────────

class OpenRouterProvider(LLMProvider):
    _BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    _PAID_MODELS = [
        "google/gemini-2.0-flash",
        "google/gemini-2.0-flash-lite",
    ]

    _FREE_MODELS = [
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.1-8b-instruct:free",
        "qwen/qwen-2.5-7b-instruct:free",
        "google/gemma-3-4b-it:free",
        "mistralai/mistral-7b-instruct:free",
    ]

    def __init__(self, api_key: str, site_url: str = "", app_name: str = "GMB Review Generator", use_paid: bool = False):
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  site_url or "http://localhost:5173",
            "X-Title":       app_name,
        }
        self._model_chain = (self._PAID_MODELS + self._FREE_MODELS) if use_paid else self._FREE_MODELS

    def _call(self, model: str, prompt: str, max_tokens: int, temperature: float) -> str | None:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.95,
        }
        try:
            with httpx.Client(timeout=45.0) as client:
                resp = client.post(self._BASE_URL, json=payload, headers=self._headers)
        except httpx.RequestError as e:
            raise RuntimeError(f"OpenRouter network error: {e}") from e

        if resp.status_code == 429:
            raise _RateLimitError(model)
        if resp.status_code == 503:
            raise _ModelUnavailableError(model)
        if not resp.is_success:
            raise RuntimeError(f"OpenRouter HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        if "error" in data:
            err  = data["error"]
            code = err.get("code") or err.get("status") or 0
            msg  = err.get("message", str(err))
            if str(code) == "429" or "rate" in msg.lower() or "quota" in msg.lower():
                raise _RateLimitError(model)
            raise RuntimeError(f"OpenRouter model error ({model}): {msg}")

        try:
            text = data["choices"][0]["message"]["content"]
            return text.strip() if text else None
        except (KeyError, IndexError, TypeError):
            return None

    def generate(self, prompt: str, max_tokens: int = 200, temperature: float = 0.8) -> str:
        last_exc: Exception = RuntimeError("No models attempted")
        for model in self._model_chain:
            try:
                text = self._call(model, prompt, max_tokens, temperature)
                if text:
                    logger.info("OpenRouter success: model=%s", model)
                    return text
                logger.warning("OpenRouter empty response from %s", model)
            except (_RateLimitError, _ModelUnavailableError) as e:
                last_exc = e
                continue
            except RuntimeError:
                raise
        raise QuotaExceededError("All OpenRouter models exhausted") from last_exc


# ─── Ollama (local / private VPS) ────────────────────────────────────────────

class OllamaProvider(LLMProvider):
    """Calls a local Ollama instance via its OpenAI-compatible endpoint."""

    def __init__(self, base_url: str, model: str):
        self._url   = base_url.rstrip("/") + "/api/generate"
        self._model = model

    def generate(self, prompt: str, max_tokens: int = 200, temperature: float = 0.8) -> str:
        payload = {
            "model":  self._model,
            "prompt": f"{_SYSTEM_PROMPT}\n\n{prompt}",
            "stream": False,
            "options": {
                "temperature":   temperature,
                "num_predict":   max_tokens,
            },
        }
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(self._url, json=payload)
            if not resp.is_success:
                raise RuntimeError(f"Ollama HTTP {resp.status_code}: {resp.text[:200]}")
            text = resp.json().get("response", "").strip()
            if not text:
                raise RuntimeError("Ollama returned empty response")
            return text
        except httpx.RequestError as e:
            raise RuntimeError(f"Ollama network error ({self._url}): {e}") from e


# ─── Chained provider — tries each provider in order ─────────────────────────

class ChainedProvider(LLMProvider):
    def __init__(self, providers: list[LLMProvider]):
        self._providers = providers

    def generate(self, prompt: str, max_tokens: int = 200, temperature: float = 0.8) -> str:
        last_exc: Exception = RuntimeError("No providers configured")
        for provider in self._providers:
            try:
                return provider.generate(prompt, max_tokens, temperature)
            except (QuotaExceededError, RuntimeError) as e:
                logger.warning("Provider %s failed: %s, trying next", type(provider).__name__, e)
                last_exc = e
        raise QuotaExceededError("All providers exhausted") from last_exc


# ─── Factory — build the fallback chain from settings ────────────────────────

def get_provider() -> LLMProvider:
    from app.core.settings import settings

    chain: list[LLMProvider] = []

    if settings.gemini_api_key:
        try:
            chain.append(GeminiProvider(api_key=settings.gemini_api_key))
            logger.info("LLM chain: +Gemini")
        except Exception as e:
            logger.warning("Gemini init failed: %s", e)

    if getattr(settings, "groq_api_key", None):
        chain.append(GroqProvider(api_key=settings.groq_api_key))
        logger.info("LLM chain: +Groq")

    if settings.openrouter_api_key:
        chain.append(OpenRouterProvider(
            api_key=settings.openrouter_api_key,
            site_url=settings.frontend_url,
            app_name=settings.app_title,
            use_paid=getattr(settings, "openrouter_use_paid", False),
        ))
        logger.info("LLM chain: +OpenRouter (paid=%s)", getattr(settings, "openrouter_use_paid", False))

    if settings.ollama_base_url:
        chain.append(OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model or "llama3.2:3b",
        ))
        logger.info("LLM chain: +Ollama (%s @ %s)", settings.ollama_model, settings.ollama_base_url)

    if not chain:
        raise RuntimeError(
            "No LLM provider configured. Set GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, or OLLAMA_BASE_URL."
        )

    return ChainedProvider(chain)
