from __future__ import annotations
import re
import logging

logger = logging.getLogger(__name__)

# Content that is immediately rejected (extreme / clearly off-platform).
_BLOCK_WORDS: list[str] = [
    # Spam / scam phrases
    "gana dinero", "trabaja desde casa", "inversión rentable",
    "inversion rentable", "haz clic aquí", "click aquí",
    # Explicit profanity — keep list minimal, just the clearest cases
    "hdp", "hijo de puta", "concha tu madre",
    # Clearly commercial animal trading
    "precio por cachorro", "precio por gatito",
]

# Content that raises a flag for human review but is still published.
_FLAG_PATTERNS: list[re.Pattern] = [
    re.compile(r"https?://", re.IGNORECASE),          # external URLs
    re.compile(r"\b(?:\d[\s\-.]?){8,11}\d\b"),        # phone-number-like strings
    re.compile(r"\$\s*\d{3,}", re.IGNORECASE),        # explicit pricing
]


def check_content(title: str, description: str) -> dict[str, object]:
    """
    Returns {"blocked": bool, "flagged": bool, "reason": str | None}
    blocked → post should be rejected outright.
    flagged → post can be published but needs moderator review.
    """
    text = f"{title} {description}".lower()

    for word in _BLOCK_WORDS:
        if word in text:
            logger.info("[Moderation] Blocked post — matched word: %s", word)
            return {"blocked": True, "flagged": False, "reason": f"Contenido no permitido: '{word}'"}

    for pattern in _FLAG_PATTERNS:
        if pattern.search(text):
            logger.info("[Moderation] Flagged post — matched pattern: %s", pattern.pattern)
            return {"blocked": False, "flagged": True, "reason": pattern.pattern}

    return {"blocked": False, "flagged": False, "reason": None}
