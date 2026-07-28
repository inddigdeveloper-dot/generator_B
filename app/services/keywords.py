import re


_LOCATION_WORDS = (
    "ahmedabad",
    "amdavad",
    "gandhinagar",
    "surat",
    "vadodara",
    "baroda",
    "rajkot",
    "bhavnagar",
    "jamnagar",
    "junagadh",
    "anand",
    "nadiad",
    "mehsana",
    "bharuch",
    "valsad",
    "vapi",
    "navsari",
    "gujarat",
    "mumbai",
    "delhi",
    "pune",
    "bangalore",
    "bengaluru",
    "hyderabad",
    "chennai",
    "kolkata",
    "india",
)

_LOCATION_PATTERN = "|".join(re.escape(word) for word in _LOCATION_WORDS)

_LOCATION_PHRASE_RE = re.compile(
    rf"\b(?:in|near|at|from|around)\s+(?:the\s+)?(?:{_LOCATION_PATTERN})(?:\s+(?:{_LOCATION_PATTERN}))*\b",
    re.IGNORECASE,
)
_NEAR_ME_RE = re.compile(r"\bnear\s+me\b", re.IGNORECASE)
_TRAILING_LOCATION_RE = re.compile(
    rf"(?:\s+|-|,)+(?:{_LOCATION_PATTERN})(?:\s+(?:{_LOCATION_PATTERN}))*\s*$",
    re.IGNORECASE,
)
_SPACES_RE = re.compile(r"\s+")


def clean_keyword(keyword: str) -> str:
    cleaned = str(keyword or "").strip()
    cleaned = _NEAR_ME_RE.sub("", cleaned)
    cleaned = _LOCATION_PHRASE_RE.sub("", cleaned)
    cleaned = _TRAILING_LOCATION_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+[-,]\s*$", "", cleaned).strip(" ,-")
    return _SPACES_RE.sub(" ", cleaned).strip()


def clean_keywords(keywords: list[str] | None) -> list[str]:
    cleaned_keywords: list[str] = []
    seen: set[str] = set()
    for keyword in keywords or []:
        cleaned = clean_keyword(keyword)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            cleaned_keywords.append(cleaned)
            seen.add(key)
    return cleaned_keywords
