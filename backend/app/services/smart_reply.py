import logging

from app.services.llm_provider import QuotaExceededError, get_provider

logger = logging.getLogger(__name__)

_provider = get_provider()

_SYSTEM_PROMPT = (
    "You are a local business owner replying to a customer review on Google. "
    "Write a short, warm, professional response. "
    "Output ONLY the reply text — no preamble, no quotes, no markdown."
)

_FALLBACKS = {
    "Professional": (
        "Thank you for taking the time to share your feedback. "
        "We truly value your experience and look forward to serving you again."
    ),
    "Friendly": (
        "Thanks so much for your kind words! It means the world to our team. "
        "We can't wait to welcome you back!"
    ),
    "Enthusiastic": (
        "Wow, thank you for this amazing review! "
        "Our team works so hard every day and this truly makes it worthwhile. "
        "Can't wait to see you again!"
    ),
}

_INJECTION_PATTERNS = [
    "ignore", "disregard", "forget", "override", "system prompt",
    "new instruction", "jailbreak", "act as", "pretend you",
]


def _sanitize(text: str) -> str:
    lowered = text.lower()
    for pattern in _INJECTION_PATTERNS:
        if pattern in lowered:
            logger.warning("Possible prompt injection in smart reply input: %r", text[:80])
            return text[:200]
    return text


def _build_prompt(review_text: str, business_name: str, tone: str, language: str) -> str:
    tone_desc = {
        "Professional": "formal, professional, and appreciative",
        "Friendly": "warm, friendly, and conversational",
        "Enthusiastic": "enthusiastic, energetic, and grateful",
    }.get(tone, "professional and courteous")

    lang_note = f"Write the reply in {language}." if language != "English" else ""

    return f"""You are the owner of {business_name}, responding to a customer review on Google.

CUSTOMER REVIEW:
\"\"\"{review_text}\"\"\"

REQUIREMENTS:
- Tone: {tone_desc}
- {lang_note}
- 2–4 sentences maximum
- If a name appears in the review, address them by name
- Address the specific points they mentioned
- End with an invitation to return or a thank you
- Sound human, not corporate
- No markdown, no bullets, no quotes around the reply

Output ONLY the reply text."""


def generate_smart_reply(
    review_text: str,
    business_name: str,
    tone: str = "Professional",
    language: str = "English",
) -> str:
    review_text = _sanitize(review_text)
    prompt = _build_prompt(review_text, business_name, tone, language)
    fallback = _FALLBACKS.get(tone, _FALLBACKS["Professional"])

    try:
        raw = _provider.generate(prompt, max_tokens=200, temperature=0.7)
        cleaned = raw.strip() if raw else ""
        return cleaned if cleaned else fallback
    except (QuotaExceededError, RuntimeError) as e:
        logger.warning("SmartReply LLM failed: %s — using fallback", e)
        return fallback
