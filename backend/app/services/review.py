import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.db.models import UserBusiness
from app.services.llm_provider import QuotaExceededError, get_provider

logger = logging.getLogger(__name__)

_provider = get_provider()

# Each variant gets a different writing angle so outputs are diverse
_VARIANT_ANGLES = [
    "Open with how the visit made you feel — not with the business name.",
    "Lead with one specific thing that stood out (good or bad). Be concrete.",
    "Write as if telling a close friend — casual, direct, one clear point.",
    "Focus on the staff or service experience rather than the product/place.",
    "Start with the outcome — would you return or recommend? Then explain why.",
]

# Varied openers/closers for fallback reviews that include experience text
_EXP_TEMPLATES = {
    "high": [   # rating 4-5
        ("Really happy with my visit to {name}.", "Would definitely come back."),
        ("Great experience at {name}.", "Highly recommend."),
        ("{name} delivered.", "Really impressed overall."),
        ("Solid visit to {name}.", "Worth every bit."),
        ("Had a great time at {name}.", "Will be back for sure."),
    ],
    "mid": [    # rating 3
        ("My visit to {name} was decent.", "Some things were good, a few areas could improve."),
        ("Mixed feelings about {name}.", "Not bad, but room for improvement."),
        ("{name} was okay overall.", "Had its highs and lows."),
        ("Average visit to {name}.", "Some things impressed me, others not so much."),
        ("Decent experience at {name}.", "Would consider returning if a few things improve."),
    ],
    "low": [    # rating 1-2
        ("Wasn't fully satisfied with my visit to {name}.", "Hoping they address these issues going forward."),
        ("Disappointed with {name}.", "Some clear things need to be fixed."),
        ("{name} fell short of expectations.", "Hope they take feedback seriously."),
        ("Not the best experience at {name}.", "There's definitely room to do better."),
        ("Had some issues at {name}.", "Would need to see real improvement before returning."),
    ],
}


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
    variant_idx: int = 0,
) -> str:
    seo_keywords = ", ".join(business.seo_keyword) if business.seo_keyword else "none"
    tone   = _tone_for_rating(rating)
    angle  = _VARIANT_ANGLES[variant_idx % len(_VARIANT_ANGLES)]

    if experience and experience.strip():
        context_block = f"""The customer shared this about their visit:
\"\"\"
{experience.strip()}
\"\"\"
Use this as the basis of the review. Paraphrase naturally — do NOT copy their words verbatim.
Reframe what they said into a genuine-sounding review. Do not invent facts beyond what they shared."""
    else:
        context_block = f"""The customer didn't share specifics. Write a believable {rating}-star review for this business.
Pick ONE concrete detail a real visitor might mention (service speed, staff, ambience, value, product quality).
Don't list everything — one focused angle makes reviews sound more human."""

    return f"""You are {customer_name}, a real customer writing a {rating}-star Google review for a local business.

BUSINESS
- Name: {business.business_name}
- About: {business.business_desc or "(no description provided)"}
- SEO keywords (weave in ONLY if natural, never force): {seo_keywords}

REVIEW BRIEF
- Rating: {rating}/5
- Tone: {tone}
- Writing angle for THIS review: {angle}

{context_block}

RULES
- 2 to 3 sentences. Casual, phone-typed feel.
- Sound human. Avoid corporate words like "establishment", "patronize", "exemplary".
- Do NOT start with the business name or "I" — vary the opening.
- No quotes, no markdown, no bullets, no preamble like "Here's the review:".
- Output ONLY the review text."""


def _clean_output(text: str) -> str:
    cleaned = text.strip()
    for pair in ('""', "''", "``"):
        if len(cleaned) >= 2 and cleaned[0] == pair[0] and cleaned[-1] == pair[1]:
            cleaned = cleaned[1:-1].strip()
    for prefix in ("Here's the review:", "Review:", "Here is the review:"):
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = cleaned[len(prefix):].strip()
    return cleaned


def _fallback_review(business: UserBusiness, rating: int, experience: str | None, variant_idx: int = 0) -> str:
    name = business.business_name

    if experience and experience.strip():
        exp     = experience.strip()
        snippet = exp[:120].rstrip(",. ") + ("..." if len(exp) > 120 else "")

        bucket = "high" if rating >= 4 else ("mid" if rating == 3 else "low")
        templates = _EXP_TEMPLATES[bucket]
        opener, closer = templates[variant_idx % len(templates)]
        opener = opener.format(name=name)
        return f"{opener} {snippet}. {closer}"

    pools = {
        5: [
            f"Really happy with my visit to {name}. Friendly staff and everything was on point — will be back for sure.",
            f"{name} exceeded my expectations. Quick service and great quality, can't recommend it enough.",
            f"Honestly one of the best experiences I've had. {name} really delivers — highly recommend.",
            f"Great visit overall. The team at {name} made everything smooth and easy.",
            f"So glad I found {name}. Everything was spot on and the service was genuinely impressive.",
        ],
        4: [
            f"Solid experience at {name}. A couple of small things could be better but overall really good.",
            f"Enjoyed my time at {name} — good service and worth the visit.",
            f"Pretty happy with {name}. Not perfect but definitely above average and I'd come back.",
            f"Good experience at {name}. Staff were helpful and things ran smoothly for the most part.",
            f"Would recommend {name}. Quality was good and the whole visit felt well worth it.",
        ],
        3: [
            f"{name} was okay. Some things were good, others were just average — nothing that stood out either way.",
            f"Mixed feelings about {name}. Not bad, but not memorable either.",
            f"Decent enough visit to {name}. Had its highs and lows but nothing too extreme.",
            f"Average experience at {name}. Some parts were good, some felt a bit lacking.",
            f"{name} is fine for what it is. Not my first choice but would consider it again.",
        ],
        2: [
            f"{name} didn't really meet my expectations. The service felt rushed and a few things were off.",
            f"Was hoping for more from {name}. Some issues with the experience that I think they should look into.",
            f"Disappointed with my visit to {name}. Things that should've been simple weren't handled well.",
            f"Below average experience at {name}. Felt like they weren't paying attention to the details.",
            f"Not great. {name} has some work to do before I'd feel comfortable recommending them.",
        ],
        1: [
            f"Pretty disappointed with {name}. The visit didn't go well and I don't think I'll be coming back.",
            f"Bad experience at {name}. Several things went wrong and it wasn't handled well.",
            f"Really let down by {name}. Expected much better and got the opposite.",
            f"Wouldn't recommend {name} based on my experience. A lot of things fell short.",
            f"Unfortunate visit to {name}. The issues were too significant to overlook.",
        ],
    }
    return pools[rating][variant_idx % len(pools[rating])]


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
            logger.warning("Possible prompt injection attempt: %r", text[:80])
            return None
    return text


def _generate_one(
    business: UserBusiness,
    rating: int,
    customer_name: str,
    experience: str | None,
    temperature: float,
    variant_idx: int,
) -> tuple[int, str | None]:
    """Returns (variant_idx, text | None)."""
    prompt = _build_prompt(business, rating, customer_name, experience, variant_idx)
    try:
        # Small stagger so concurrent calls don't all hit the API at the same millisecond
        time.sleep(variant_idx * 0.15)
        raw     = _provider.generate(prompt, max_tokens=220, temperature=temperature)
        cleaned = _clean_output(raw)
        return variant_idx, (cleaned if cleaned else None)
    except (QuotaExceededError, RuntimeError) as e:
        logger.warning("Variant %d generation failed (temp=%.2f): %s", variant_idx, temperature, e)
        return variant_idx, None


def generate_review_variants(
    business: UserBusiness,
    rating: int,
    customer_name: str = "a customer",
    experience: str | None = None,
    count: int = 5,
) -> list[str]:
    if rating not in (1, 2, 3, 4, 5):
        raise ValueError(f"rating must be 1-5, got {rating}")

    customer_name = (customer_name or "a customer").strip()
    experience    = _sanitize_user_input(experience)

    temperatures = [0.72, 0.78, 0.84, 0.88, 0.93][:count]

    # Map index → result so order is preserved
    results: dict[int, str | None] = {}

    with ThreadPoolExecutor(max_workers=count) as pool:
        futures = {
            pool.submit(_generate_one, business, rating, customer_name, experience, t, i): i
            for i, t in enumerate(temperatures)
        }
        for future in as_completed(futures):
            idx, text = future.result()
            results[idx] = text

    reviews = []
    for i in range(count):
        text = results.get(i)
        reviews.append(text if text else _fallback_review(business, rating, experience, variant_idx=i))

    return reviews


def generate_review_text(
    business: UserBusiness,
    rating: int,
    customer_name: str = "a customer",
    experience: str | None = None,
) -> str:
    if rating not in (1, 2, 3, 4, 5):
        raise ValueError(f"rating must be 1-5, got {rating}")

    customer_name = (customer_name or "a customer").strip()
    experience    = _sanitize_user_input(experience)
    prompt        = _build_prompt(business, rating, customer_name, experience, variant_idx=0)

    try:
        raw = _provider.generate(prompt, max_tokens=200, temperature=0.8)
    except QuotaExceededError:
        logger.warning("LLM quota exhausted for business_id=%s — using fallback", business.id)
        return _fallback_review(business, rating, experience, variant_idx=0)
    except RuntimeError as e:
        logger.exception("LLM provider error for business_id=%s: %s", business.id, e)
        raise

    cleaned = _clean_output(raw)
    return cleaned if cleaned else _fallback_review(business, rating, experience, variant_idx=0)
