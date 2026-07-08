import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.db.models import UserBusiness
from app.services.llm_provider import QuotaExceededError, get_provider

logger = logging.getLogger(__name__)

_provider = get_provider()

_SHORT_REVIEWS_PER_FIVE = 2

# Each variant gets a different writing angle so outputs are diverse
_VARIANT_ANGLES = [
    "Open with how the visit made you feel — not with the business name.",
    "Lead with one specific thing that stood out (good or bad). Be concrete.",
    "Write as if telling a close friend — casual, direct, one clear point.",
    "Focus on the staff or service experience rather than the product/place.",
    "Start with the outcome — would you return or recommend? Then explain why.",
]

# Each scan shuffles these so the five review options do not share the same opener.
_OPENING_STYLES = [
    "Start with a plain reaction, like something felt easy, helpful, disappointing, or worth it.",
    "Start with a specific detail first, such as staff behavior, service speed, quality, ambience, or value.",
    "Start with the outcome first, such as whether you would return, recommend it, or expected better.",
    "Start like a casual note to a friend, using simple everyday wording and no polished intro.",
    "Start with a balanced observation, then explain the main reason in the next sentence.",
    "Start with what changed your mind during the visit, without using dramatic language.",
    "Start with the strongest positive or negative point, not a generic review phrase.",
    "Start with a small moment from the experience, then connect it to the overall feeling.",
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

_SHORT_EXP_TEMPLATES = {
    "high": [
        "{detail}. Smooth experience overall.",
        "{detail}. Really happy with it.",
        "{detail}. Would go again.",
        "Good service and {detail}.",
        "{detail}. Simple and worth it.",
    ],
    "mid": [
        "{detail}. Decent, but not amazing.",
        "{detail}. Okay overall.",
        "{detail}. Some parts could improve.",
        "Mixed experience, especially {detail}.",
        "{detail}. Fine for a quick visit.",
    ],
    "low": [
        "{detail}. Not a great experience.",
        "{detail}. Expected better.",
        "{detail}. Needs improvement.",
        "Disappointed, especially with {detail}.",
        "{detail}. Would not rush back.",
    ],
}

_SHORT_FALLBACKS = {
    5: [
        "Really smooth experience and the staff were genuinely helpful.",
        "Loved how easy everything felt from start to finish.",
        "Great quality, quick service, and a very comfortable visit.",
        "Honestly better than expected. I would happily come back.",
        "Simple, pleasant, and worth recommending.",
    ],
    4: [
        "Good experience overall, with just a little room to improve.",
        "Helpful staff and a smooth visit for the most part.",
        "Pretty satisfied. A few small things could be better.",
        "Worth visiting, especially for the service.",
        "Nice overall experience and I would consider going again.",
    ],
    3: [
        "Decent visit, but nothing really stood out.",
        "Okay overall. Some parts worked better than others.",
        "Not bad, just fairly average.",
        "Fine experience, though it could feel more polished.",
        "Mixed feelings. It was acceptable, not memorable.",
    ],
    2: [
        "Expected better. A few things felt poorly handled.",
        "Not very satisfied with the overall experience.",
        "Service felt off and the visit could improve.",
        "Below average experience, unfortunately.",
        "Some basics need more attention here.",
    ],
    1: [
        "Really disappointing experience overall.",
        "Would not recommend based on this visit.",
        "Too many things went wrong.",
        "Very let down by the service.",
        "Not a place I would return to.",
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


def _profile_tone_instruction(tone: str | None, rating: int) -> str:
    tone = tone or "Professional"
    if tone == "Friendly":
        style = "friendly, natural, and conversational"
    elif tone == "Enthusiastic":
        style = "energetic, expressive, and memorable"
    else:
        style = "professional, clear, and polished"

    if rating <= 2:
        return f"{style}, but keep the criticism honest and do not make the review sound fake-positive"
    if rating == 3:
        return f"{style}, while staying balanced about both positives and improvements"
    return style


def _language_instruction(language: str | None, tone: str | None) -> str:
    language = language or "English"
    tone = tone or "Professional"
    if language == "English" and tone == "Professional":
        return ""
    if language == "Hindi":
        return """- Write the review in Hindi using Devanagari script only.
- Do not use Roman Hindi or Hinglish.
- Avoid English words like "service", "team", "recommend", and "solution" unless they are part of the business name.
- Use simple, everyday Hindi. Avoid heavy, bookish, or formal Hindi."""
    if language == "Hinglish":
        return """- Write the review in natural Hinglish.
- Mix Hindi and English only where it feels normal; do not force translation for common words."""
    return "- Write the review in English."


def _style_instruction(language: str | None, tone: str | None, rating: int) -> str:
    language = language or "English"
    tone = tone or "Professional"
    if language == "English" and tone == "Professional":
        return ""

    tone_line = ""
    if tone == "Friendly":
        tone_line = "- Friendly tone: sound warm and personal, not like an ad."
    elif tone == "Enthusiastic":
        tone_line = "- Enthusiastic tone: show genuine excitement, but avoid over-the-top marketing words."

    rating_line = ""
    if rating <= 2:
        rating_line = "- For low ratings, stay honest and calm. Do not make it sound positive."
    elif rating == 3:
        rating_line = "- For a 3-star review, keep it mixed and believable."

    lines = [
        _language_instruction(language, tone),
        tone_line,
        rating_line,
        "- Use 1 to 2 short complete sentences.",
        "- Do not write a long paragraph.",
        "- Do not end with an incomplete sentence.",
        "- Do not mention exact numbers, days, dates, prices, or timelines unless the customer wrote them.",
        "- Prefer plain customer words over polished AI-style phrasing.",
    ]
    return "\n".join(line for line in lines if line)


def _build_prompt(
    business: UserBusiness,
    rating: int,
    customer_name: str,
    experience: str | None,
    variant_idx: int = 0,
    short_review: bool = False,
    opening_style: str | None = None,
) -> str:
    seo_keywords = ", ".join(business.seo_keyword) if business.seo_keyword else "none"
    profile_language = getattr(business, "language", None) or "English"
    profile_tone_name = getattr(business, "tone", None) or "Professional"
    rating_tone = _tone_for_rating(rating)
    profile_tone = _profile_tone_instruction(profile_tone_name, rating)
    extra_style = _style_instruction(profile_language, profile_tone_name, rating)
    angle = _VARIANT_ANGLES[variant_idx % len(_VARIANT_ANGLES)]
    opening_style = opening_style or _OPENING_STYLES[variant_idx % len(_OPENING_STYLES)]

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
Do not invent exact numbers, dates, durations, prices, or timelines.
Don't list everything — one focused angle makes reviews sound more human."""

    if profile_language == "English" and profile_tone_name == "Professional":
        brief_block = f"- Tone: {rating_tone}"
    else:
        brief_block = f"""- Rating sentiment: {rating_tone}
- Selected tone style: {profile_tone}
- Selected language: {profile_language}

STYLE REQUIREMENTS
{extra_style}"""

    length_rule = (
        "- SHORT REVIEW: 1 natural sentence, or 2 very short sentences. Keep it under 18 words."
        if short_review
        else "- NORMAL REVIEW: 2 to 3 short sentences. Casual, phone-typed feel."
    )

    return f"""You are {customer_name}, a real customer writing a {rating}-star Google review for a local business.

BUSINESS
- Name: {business.business_name}
- About: {business.business_desc or "(no description provided)"}
- SEO keywords (weave in ONLY if natural, never force): {seo_keywords}

REVIEW BRIEF
- Rating: {rating}/5
{brief_block}
- Writing angle for THIS review: {angle}
- Opening style for THIS review: {opening_style}

{context_block}

RULES
{length_rule}
- Sound human. Avoid corporate words like "establishment", "patronize", "exemplary".
- Do not mention exact numbers, days, dates, prices, or timelines unless the customer explicitly wrote them.
- Do NOT start with the business name or "I" — vary the opening.
- Vary the first words. Do not repeat common openings like "Great experience", "Really happy", "I had", or the business name.
- Start from a detail, a feeling, an outcome, or a casual reaction so each review sounds written by a different person.
- Follow the opening style above exactly enough that this review begins differently from the other four options.
- Avoid using the same first 4 words as any other review option in this batch.
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
    if cleaned and cleaned[-1] not in ".!?।॥!?":
        last_end = max(cleaned.rfind("."), cleaned.rfind("!"), cleaned.rfind("?"), cleaned.rfind("।"), cleaned.rfind("॥"))
        if last_end > 0:
            cleaned = cleaned[: last_end + 1].strip()
    return cleaned


def _fallback_review(
    business: UserBusiness,
    rating: int,
    experience: str | None,
    variant_idx: int = 0,
    short_review: bool = False,
) -> str:
    name = business.business_name

    if experience and experience.strip():
        exp     = experience.strip()
        bucket = "high" if rating >= 4 else ("mid" if rating == 3 else "low")

        if short_review:
            detail = exp[:55].rstrip(",. ")
            templates = _SHORT_EXP_TEMPLATES[bucket]
            return templates[variant_idx % len(templates)].format(detail=detail)

        snippet = exp[:120].rstrip(",. ") + ("..." if len(exp) > 120 else "")
        templates = _EXP_TEMPLATES[bucket]
        opener, closer = templates[variant_idx % len(templates)]
        opener = opener.format(name=name)
        return f"{opener} {snippet}. {closer}"

    if short_review:
        return _SHORT_FALLBACKS[rating][variant_idx % len(_SHORT_FALLBACKS[rating])]

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


def _short_review_indexes(count: int) -> set[int]:
    if count <= 0:
        return set()
    short_count = min(_SHORT_REVIEWS_PER_FIVE, count)
    return set(random.sample(range(count), short_count))


def _opening_styles_for_count(count: int) -> list[str]:
    styles = _OPENING_STYLES[:]
    random.shuffle(styles)
    return [styles[i % len(styles)] for i in range(count)]


def _generate_one(
    business: UserBusiness,
    rating: int,
    customer_name: str,
    experience: str | None,
    temperature: float,
    variant_idx: int,
    short_review: bool,
    opening_style: str,
) -> tuple[int, str | None]:
    """Returns (variant_idx, text | None)."""
    prompt = _build_prompt(
        business,
        rating,
        customer_name,
        experience,
        variant_idx,
        short_review=short_review,
        opening_style=opening_style,
    )
    language = getattr(business, "language", None) or "English"
    tone = getattr(business, "tone", None) or "Professional"
    max_tokens = 90 if short_review else (240 if (language != "English" or tone != "Professional") else 220)
    try:
        # Small stagger so concurrent calls don't all hit the API at the same millisecond
        time.sleep(variant_idx * 0.15)
        raw     = _provider.generate(prompt, max_tokens=max_tokens, temperature=temperature)
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
    short_indexes = _short_review_indexes(count)
    opening_styles = _opening_styles_for_count(count)

    # Map index → result so order is preserved
    results: dict[int, str | None] = {}

    with ThreadPoolExecutor(max_workers=count) as pool:
        futures = {
            pool.submit(
                _generate_one,
                business,
                rating,
                customer_name,
                experience,
                t,
                i,
                i in short_indexes,
                opening_styles[i],
            ): i
            for i, t in enumerate(temperatures)
        }
        for future in as_completed(futures):
            idx, text = future.result()
            results[idx] = text

    reviews = []
    for i in range(count):
        text = results.get(i)
        reviews.append(
            text
            if text
            else _fallback_review(
                business,
                rating,
                experience,
                variant_idx=i,
                short_review=i in short_indexes,
            )
        )

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
    language      = getattr(business, "language", None) or "English"
    tone          = getattr(business, "tone", None) or "Professional"
    max_tokens    = 240 if (language != "English" or tone != "Professional") else 200

    try:
        raw = _provider.generate(prompt, max_tokens=max_tokens, temperature=0.8)
    except QuotaExceededError:
        logger.warning("LLM quota exhausted for business_id=%s — using fallback", business.id)
        return _fallback_review(business, rating, experience, variant_idx=0)
    except RuntimeError as e:
        logger.exception("LLM provider error for business_id=%s: %s", business.id, e)
        raise

    cleaned = _clean_output(raw)
    return cleaned if cleaned else _fallback_review(business, rating, experience, variant_idx=0)
