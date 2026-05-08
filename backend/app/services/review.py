import logging
import random

from app.db.models import UserBusiness
from app.services.llm_provider import QuotaExceededError, get_provider

logger = logging.getLogger(__name__)

# Initialized once at import time — thread-safe, no lazy race condition.
_provider = get_provider()

def _tone_for_rating(rating: int) -> str:
    if rating >= 4:
        return "warm, enthusiastic, and specific about what stood out"
    if rating == 3:
        return "balanced and fair — acknowledge strengths but mention what could be better"
    if rating == 2:
        return "disappointed but professional — explain what fell short without being hostile"
    return "frustrated but constructive — clearly state what went wrong, no insults or threats"


def _build_prompt(
    business: UserBusiness,
    rating: int,
    customer_name: str,
    experience: str | None,
) -> str:
    seo_keywords = ", ".join(business.seo_keyword) if business.seo_keyword else "none"
    tone = _tone_for_rating(rating)

    if experience and experience.strip():
        context_block = f"""The customer shared this about their visit:
\"\"\"
{experience.strip()}
\"\"\"

Build the review around what they actually said. Don't invent details that contradict their notes."""
    else:
        context_block = f"""The customer didn't share specifics, so write a believable review using only what a real {rating}-star visitor to this business would plausibly say.
Pick ONE or TWO concrete things a customer might mention (e.g. service speed, ambience, a menu item, the staff, value, cleanliness) — don't list everything.
Vary the angle so reviews don't all sound the same."""

    return f"""You are {customer_name}, a real customer writing a {rating}-star Google review for a local business.

BUSINESS
- Name: {business.business_name}
- About: {business.business_desc or "(no description provided)"}
- SEO keywords (weave in ONLY if they fit naturally — never force them): {seo_keywords}

REVIEW BRIEF
- Rating: {rating}/5
- Tone: {tone}

{context_block}

RULES
- 2 to 3 sentences. Casual, phone-typed feel — contractions are fine, perfect grammar isn't required.
- Sound human. Avoid corporate words like "establishment", "patronize", "exemplary".
- Don't start with the business name or "I" every time — vary the opening.
- No quotes, no markdown, no bullets, no preamble like "Here's the review:".
- Output ONLY the review text, nothing else."""


def _clean_output(text: str) -> str:
    cleaned = text.strip()
    for pair in ('""', "''", "``"):
        if len(cleaned) >= 2 and cleaned[0] == pair[0] and cleaned[-1] == pair[1]:
            cleaned = cleaned[1:-1].strip()
    for prefix in ("Here's the review:", "Review:", "Here is the review:"):
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = cleaned[len(prefix):].strip()
    return cleaned


def _fallback_review(business: UserBusiness, rating: int, experience: str | None = None) -> str:
    name = business.business_name

    # If the customer shared notes, build a simple template around their words
    # so the review isn't completely disconnected from their actual experience.
    if experience and experience.strip():
        exp = experience.strip()
        # Keep only the first 120 chars to avoid awkward run-ons
        snippet = exp[:120].rstrip(",. ") + ("..." if len(exp) > 120 else "")
        if rating >= 4:
            return (
                f"Had a great visit to {name}. {snippet}. "
                f"Really happy with the overall experience — would definitely come back."
            )
        if rating == 3:
            return (
                f"My visit to {name} was decent overall. {snippet}. "
                f"Some things were good, a few areas could still use improvement."
            )
        if rating == 2:
            return (
                f"Wasn't fully satisfied with my visit to {name}. {snippet}. "
                f"Hoping they address these issues going forward."
            )
        return (
            f"Really disappointed with my experience at {name}. {snippet}. "
            f"Didn't meet my expectations at all."
        )

    pools = {
        5: [
            f"Really happy with my visit to {name}. Friendly staff and everything was on point — will be back for sure.",
            f"{name} exceeded my expectations. Quick service and great quality, can't recommend it enough.",
        ],
        4: [
            f"Solid experience at {name}. A couple of small things could be better but overall really good.",
            f"Enjoyed my time at {name} — good service and worth the visit.",
        ],
        3: [
            f"{name} was okay. Some things were good, others were just average — nothing that stood out either way.",
            f"Mixed feelings about {name}. Not bad, but not memorable either.",
        ],
        2: [
            f"{name} didn't really meet my expectations. The service felt rushed and a few things were off.",
            f"Was hoping for more from {name}. Some issues with the experience that I think they should look into.",
        ],
        1: [
            f"Pretty disappointed with {name}. The visit didn't go well and I don't think I'll be coming back.",
            f"Bad experience at {name}. Several things went wrong and it wasn't handled well.",
        ],
    }
    return random.choice(pools[rating])


_INJECTION_PATTERNS = [
    "ignore", "disregard", "forget", "override", "system prompt",
    "new instruction", "jailbreak", "act as", "pretend you",
]


def _sanitize_user_input(text: str | None) -> str | None:
    if not text:
        return text
    lowered = text.lower()
    for pattern in _INJECTION_PATTERNS:
        if pattern in lowered:
            logger.warning("Possible prompt injection attempt detected: %r", text[:80])
            return None
    return text


def generate_review_text(
    business: UserBusiness,
    rating: int,
    customer_name: str = "a customer",
    experience: str | None = None,
) -> str:
    if rating not in (1, 2, 3, 4, 5):
        raise ValueError(f"rating must be 1-5, got {rating}")

    customer_name = (customer_name or "a customer").strip()
    experience = _sanitize_user_input(experience)
    prompt = _build_prompt(business, rating, customer_name, experience)

    try:
        raw = _provider.generate(prompt, max_tokens=200, temperature=0.8)
    except QuotaExceededError:
        logger.warning("LLM quota exhausted for business_id=%s — using fallback review", business.id)
        return _fallback_review(business, rating, experience)
    except RuntimeError as e:
        logger.exception("LLM provider error for business_id=%s: %s", business.id, e)
        raise

    cleaned = _clean_output(raw)
    if not cleaned:
        return _fallback_review(business, rating, experience)

    return cleaned
