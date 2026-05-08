"""
Training Data Generator — Phase 2

Generates JSONL fine-tuning dataset from the existing Gemini API (while quota lasts)
or from a list of business templates you define below.

Output: training_data.jsonl  (Alpaca-style instruction format)

Usage:
    cd generator/scripts
    pip install google-generativeai
    python generate_training_data.py --samples 500 --output training_data.jsonl

After generation, use finetune.py to train a Llama 3.2 3B model on this data.
"""

import argparse
import json
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ─── Sample Business Templates ───────────────────────────────────────────────
# Add more to increase diversity. The generator picks these randomly.

BUSINESS_TEMPLATES = [
    {"name": "Bella Italia", "desc": "Family Italian restaurant, fresh pasta daily", "keywords": ["pasta", "Italian food", "family dining"]},
    {"name": "Green Leaf Café", "desc": "Organic coffee shop and café", "keywords": ["organic coffee", "healthy food", "vegan options"]},
    {"name": "AutoFix Pro", "desc": "Car repair and maintenance workshop", "keywords": ["car repair", "oil change", "auto service"]},
    {"name": "Sunrise Dental", "desc": "Modern dental clinic for all ages", "keywords": ["dental care", "teeth whitening", "painless dentist"]},
    {"name": "FitZone Gym", "desc": "Full-service fitness center, personal training available", "keywords": ["gym", "personal trainer", "fitness classes"]},
    {"name": "Quick Cuts Barbershop", "desc": "Classic barbershop, walk-ins welcome", "keywords": ["haircut", "barbershop", "beard trim"]},
    {"name": "Paws & Claws Vet", "desc": "Veterinary clinic for pets", "keywords": ["pet care", "veterinarian", "dog grooming"]},
    {"name": "The Book Nook", "desc": "Independent bookshop with rare finds", "keywords": ["bookstore", "rare books", "reading"]},
    {"name": "CloudBite Delivery", "desc": "Fast food delivery service", "keywords": ["food delivery", "fast delivery", "online order"]},
    {"name": "Bliss Spa", "desc": "Day spa offering massages and facials", "keywords": ["massage", "facial", "relaxation spa"]},
    {"name": "ElectroPro Repairs", "desc": "Phone and laptop repair shop", "keywords": ["phone repair", "screen replacement", "laptop fix"]},
    {"name": "Fresh Market Grocery", "desc": "Local grocery store with fresh produce", "keywords": ["grocery", "fresh produce", "local market"]},
    {"name": "Noodle House", "desc": "Asian fusion noodle restaurant", "keywords": ["ramen", "pho", "noodles", "Asian food"]},
    {"name": "Bloom Florist", "desc": "Custom flower arrangements and gifts", "keywords": ["flowers", "bouquet", "wedding flowers"]},
    {"name": "LegalEdge Law", "desc": "General practice law firm", "keywords": ["lawyer", "legal advice", "law firm"]},
]

CUSTOMER_NAMES = [
    "Jake M.", "Sarah T.", "Michael B.", "Emily R.", "David L.",
    "Jessica K.", "Chris P.", "Amanda W.", "Ryan H.", "Natalie S.",
    "Kevin O.", "Melissa C.", "Brian F.", "Laura N.", "Mark D.",
    "Jennifer A.", "Steven G.", "Rachel E.", "Andrew J.", "Stephanie V.",
]

EXPERIENCE_NOTES = {
    5: [
        "Great food and service. Came with family.",
        "Super friendly staff. Waited only 5 mins.",
        "Best I've had in years. Reasonably priced too.",
        "Staff remembered my order from last time.",
        None, None, None,  # No notes sometimes
    ],
    4: [
        "Food was great but parking was a bit tight.",
        "Good overall, maybe a bit pricey.",
        "Staff was helpful but busy.",
        None, None,
    ],
    3: [
        "Some things were good, others average.",
        "Waited longer than expected.",
        None, None,
    ],
    2: [
        "Order was wrong. Staff was slow to fix it.",
        "Not as advertised. Disappointing.",
        None,
    ],
    1: [
        "Very rude staff. Waited 45 mins with no update.",
        "Food was cold and overpriced.",
        None,
    ],
}


@dataclass
class ReviewExample:
    business_name: str
    business_desc: str
    keywords: list[str]
    rating: int
    customer_name: str
    experience: Optional[str]
    review_text: str


def _build_prompt(business_name, business_desc, keywords, rating, customer_name, experience):
    """Same prompt structure as production review.py."""
    tones = {
        5: "warm, enthusiastic, and specific about what stood out",
        4: "warm, enthusiastic, and specific about what stood out",
        3: "balanced and fair — acknowledge strengths but mention what could be better",
        2: "disappointed but professional — explain what fell short without being hostile",
        1: "frustrated but constructive — clearly state what went wrong, no insults or threats",
    }
    seo = ", ".join(keywords) if keywords else "none"
    tone = tones[rating]

    if experience and experience.strip():
        context_block = f"""The customer shared this about their visit:
\"\"\"{experience.strip()}\"\"\"
Build the review around what they actually said."""
    else:
        context_block = f"""The customer didn't share specifics, so write a believable review using only what a real {rating}-star visitor would plausibly say.
Pick ONE or TWO concrete things (e.g. service speed, ambience, a menu item, staff, value)."""

    return f"""You are {customer_name}, a real customer writing a {rating}-star Google review for a local business.

BUSINESS
- Name: {business_name}
- About: {business_desc}
- SEO keywords (weave in ONLY if natural): {seo}

REVIEW BRIEF
- Rating: {rating}/5
- Tone: {tone}

{context_block}

RULES
- 2 to 3 sentences. Casual, phone-typed feel.
- Sound human. No corporate words.
- Don't start with the business name or "I" every time.
- No quotes, no markdown, no preamble.
- Output ONLY the review text."""


def generate_with_gemini(prompt: str, api_key: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    resp = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=0.85,
            max_output_tokens=200,
        ),
    )
    return resp.text.strip()


def clean(text: str) -> str:
    t = text.strip()
    for pair in ('""', "''", "``"):
        if len(t) >= 2 and t[0] == pair[0] and t[-1] == pair[1]:
            t = t[1:-1].strip()
    for prefix in ("Here's the review:", "Review:", "Here is the review:"):
        if t.lower().startswith(prefix.lower()):
            t = t[len(prefix):].strip()
    return t


def build_alpaca_entry(example: ReviewExample) -> dict:
    """
    Alpaca instruction format — most fine-tuning frameworks accept this directly.
    instruction = the task
    input = the business context
    output = the generated review
    """
    instruction = (
        f"Write a {example.rating}-star Google review for a local business. "
        f"You are {example.customer_name}. "
        "Be casual, 2-3 sentences, sound human. Output only the review text."
    )
    input_text = (
        f"Business: {example.business_name}\n"
        f"Description: {example.business_desc}\n"
        f"Keywords: {', '.join(example.keywords)}\n"
        f"Customer experience notes: {example.experience or 'none provided'}"
    )
    return {
        "instruction": instruction,
        "input": input_text,
        "output": example.review_text,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=300, help="Total samples to generate")
    parser.add_argument("--output", default="training_data.jsonl")
    parser.add_argument("--api-key", default=os.getenv("GEMINI_API_KEY"))
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between API calls")
    args = parser.parse_args()

    if not args.api_key:
        print("ERROR: Set GEMINI_API_KEY env var or pass --api-key")
        return

    output_path = Path(args.output)
    existing = 0
    if output_path.exists():
        with open(output_path) as f:
            existing = sum(1 for _ in f)
        print(f"Resuming — {existing} samples already in {output_path}")

    samples_needed = args.samples - existing
    if samples_needed <= 0:
        print(f"Already have {existing} samples. Done.")
        return

    print(f"Generating {samples_needed} samples → {output_path}")

    with open(output_path, "a", encoding="utf-8") as out:
        for i in range(samples_needed):
            biz = random.choice(BUSINESS_TEMPLATES)
            rating = random.choice([1, 2, 3, 4, 4, 5, 5, 5])  # weight toward positive
            customer = random.choice(CUSTOMER_NAMES)
            experience = random.choice(EXPERIENCE_NOTES.get(rating, [None]))

            prompt = _build_prompt(
                biz["name"], biz["desc"], biz["keywords"],
                rating, customer, experience,
            )

            try:
                raw = generate_with_gemini(prompt, args.api_key)
                review_text = clean(raw)
                if not review_text or len(review_text) < 20:
                    print(f"  [{i+1}] Skipped — empty/short response")
                    continue

                example = ReviewExample(
                    business_name=biz["name"],
                    business_desc=biz["desc"],
                    keywords=biz["keywords"],
                    rating=rating,
                    customer_name=customer,
                    experience=experience,
                    review_text=review_text,
                )

                record = build_alpaca_entry(example)
                out.write(json.dumps(record) + "\n")
                out.flush()
                print(f"  [{existing + i + 1}/{args.samples}] ★{rating} {biz['name']}: {review_text[:60]}...")

            except Exception as e:
                print(f"  [{i+1}] ERROR: {e} — skipping")

            time.sleep(args.delay)

    print(f"\nDone. Total: {output_path}")
    print("Next step: run  python finetune.py --data training_data.jsonl")


if __name__ == "__main__":
    main()
