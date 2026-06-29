from __future__ import annotations
import re
import logging

logger = logging.getLogger(__name__)

# ── Profanity filter (glin-profanity) ─────────────────────────────────────────
# Handles word-level profanity in Spanish and English, including leetspeak and
# Unicode obfuscation variants, without maintaining a huge manual wordlist.
try:
    from glin_profanity import Filter as _GlinFilter
    _profanity_filter = _GlinFilter({"languages": ["english", "spanish"]})
    _GLIN_AVAILABLE = True
except Exception as _import_err:
    logger.warning("[Moderation] glin-profanity unavailable (%s) — falling back to wordlist", _import_err)
    _GLIN_AVAILABLE = False

# ── Fallback block list (used only when glin-profanity is not installed) ───────
_FALLBACK_BLOCK_WORDS: list[str] = [
    # Spanish profanity
    "hdp", "hijo de puta", "hija de puta", "concha tu madre", "concha de tu madre",
    "pelotudo", "pelotuda", "boludo", "boluda", "puto", "puta",
    "mierda", "carajo", "culo", "forro",
    # English profanity
    "fuck", "fucking", "shit", "asshole", "bitch",
    "cock", "dick", "cunt", "nigger", "faggot",
    # Illegal animal trading (ES)
    "precio por cachorro", "vendo cachorro", "vendo perro", "venta de cachorros",
    "pago por cachorro", "raza pura en venta", "criadero de venta",
    # Illegal animal trading (EN)
    "puppy for sale", "dog for sale", "cat for sale", "selling puppies",
    # Violence / threats
    "te voy a matar", "i will kill", "i'll kill", "gonna kill",
    # Spam / scam
    "gana dinero", "trabaja desde casa", "inversión rentable",
    "make money fast", "easy money", "guaranteed income",
    "crypto", "bitcoin", "forex", "esquema ponzi", "multinivel",
]

# ── Flag patterns ─────────────────────────────────────────────────────────────
# Posts matching these patterns are published but held for moderator review.
# glin-profanity does not cover structural commercial signals (URLs, phones, etc.)
# so these patterns remain regardless of library availability.
_FLAG_PATTERNS: list[re.Pattern] = [
    # External URLs
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"\bwww\.", re.IGNORECASE),
    re.compile(r"\.(com|net|org|ar|uy|cl|mx|es|io|co)\b", re.IGNORECASE),
    # Phone-number-like strings (8–12 consecutive or spaced digits)
    re.compile(r"\b(?:\d[\s\-.]?){8,11}\d\b"),
    # WhatsApp / Telegram handles
    re.compile(r"\bwh?a?ts?[_\s]?app\b", re.IGNORECASE),
    re.compile(r"\btelegram\b", re.IGNORECASE),
    # Email addresses
    re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
    # Explicit pricing ($100+ or U$S 100+)
    re.compile(r"(\$|USD?|u\$s)\s*\d{2,}", re.IGNORECASE),
    re.compile(r"\d{3,}\s*(pesos|ARS|USD|dolares|dólares)", re.IGNORECASE),
    # Social media handles / platforms
    re.compile(r"@[a-zA-Z0-9_]{3,}", re.IGNORECASE),
    re.compile(r"\b(instagram|facebook|tiktok|snapchat|twitter|x\.com)\b", re.IGNORECASE),
]


def _is_profane(text: str) -> tuple[bool, str | None]:
    """Returns (is_blocked, matched_word_or_None)."""
    if _GLIN_AVAILABLE:
        try:
            if _profanity_filter.is_profane(text):
                return True, "profanity detected"
        except Exception as exc:
            logger.warning("[Moderation] glin-profanity check failed: %s", exc)

    # Fallback wordlist check
    lower = text.lower()
    for word in _FALLBACK_BLOCK_WORDS:
        if word in lower:
            return True, word

    return False, None


def check_content(title: str, description: str) -> dict[str, object]:
    """
    Returns {"blocked": bool, "flagged": bool, "reason": str | None}
    blocked → post should be rejected outright.
    flagged → post can be published but needs moderator review.
    """
    combined = f"{title} {description}"

    blocked, matched = _is_profane(combined)
    if blocked:
        logger.info("[Moderation] Blocked post — %s", matched)
        return {"blocked": True, "flagged": False, "reason": f"Contenido no permitido: '{matched}'"}

    for pattern in _FLAG_PATTERNS:
        if pattern.search(combined):
            logger.info("[Moderation] Flagged post — matched pattern: %s", pattern.pattern)
            return {"blocked": False, "flagged": True, "reason": pattern.pattern}

    return {"blocked": False, "flagged": False, "reason": None}
