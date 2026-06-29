from __future__ import annotations
import re
import logging

logger = logging.getLogger(__name__)

# ── Block list ────────────────────────────────────────────────────────────────
# Posts matching any of these strings are rejected outright.
_BLOCK_WORDS: list[str] = [
    # ── Spanish profanity ─────────────────────────────────────────────────────
    "hdp", "hijo de puta", "hija de puta", "concha tu madre", "concha de tu madre",
    "hijo de p", "hija de p", "puta madre", "la concha",
    "pelotudo", "pelotuda", "boludo", "boluda", "gil", "gila",
    "forro", "forra", "culo", "culero", "culera", "mierda", "maldito", "maldita",
    "carajo", "jodete", "vete al carajo", "que te jodan", "te cago",
    "marica", "maricón", "maricon", "travesti",
    "puto", "puta", "putas", "prostituta",
    "bastardo", "bastarda", "cretino", "cretina", "imbecil", "imbécil",
    "idióta", "idiota", "estupido", "estúpido", "estupida", "estúpida",
    "retrasado", "retrasada",
    # ── English profanity ─────────────────────────────────────────────────────
    "fuck", "fucking", "fucked", "fucker", "motherfucker",
    "shit", "shitty", "bullshit",
    "asshole", "ass hole", "bitch", "bitches", "bastard",
    "cock", "dick", "pussy", "cunt",
    "nigger", "nigga", "faggot",
    "retard", "retarded",
    # ── Spam / scam phrases (ES) ──────────────────────────────────────────────
    "gana dinero", "ganá dinero", "gana dinero fácil", "dinero fácil",
    "trabaja desde casa", "trabajá desde casa",
    "inversión rentable", "inversion rentable",
    "haz clic aquí", "click aquí", "hace clic",
    "gana plata", "ganá plata", "plata fácil",
    "negocio redondo", "ganancia garantizada",
    "sin inversión", "sin inversion",
    "crypto", "bitcoin", "ethereum", "criptomonedas",
    "forex", "trading automático", "trading automatico",
    "esquema ponzi", "marketing multinivel", "multinivel",
    "doble tu dinero", "duplica tu dinero",
    "oportunidad única", "oportunidad unica",
    # ── Spam / scam phrases (EN) ──────────────────────────────────────────────
    "make money fast", "work from home", "easy money",
    "guaranteed income", "passive income", "earn from home",
    "click here", "limited time offer", "act now",
    "100% free", "no investment needed",
    "double your money", "risk free",
    # ── Illegal animal trading (ES) ───────────────────────────────────────────
    "precio por cachorro", "precio por gatito", "precio por perro",
    "vendo cachorro", "vendo perro", "vendo gato", "vendo mascota",
    "venta de cachorros", "venta de perros", "venta de gatos",
    "en venta cachorro", "en venta perro",
    "pago por cachorro", "pago por mascota",
    "$ por cachorro", "usd por cachorro",
    "raza pura en venta", "pedigree en venta",
    "criadero de venta",
    # ── Illegal animal trading (EN) ───────────────────────────────────────────
    "puppy for sale", "dog for sale", "cat for sale", "kitten for sale",
    "pet for sale", "selling puppies", "selling dogs",
    "buy puppy", "buy dog", "buy cat",
    # ── Violence / threats ────────────────────────────────────────────────────
    "te voy a matar", "te voy a cagar", "te voy a romper",
    "lo voy a matar", "los voy a matar",
    "i will kill", "i'll kill", "gonna kill",
]

# ── Flag patterns ─────────────────────────────────────────────────────────────
# Posts matching these patterns are published but held for moderator review.
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
    # Social media handles
    re.compile(r"@[a-zA-Z0-9_]{3,}", re.IGNORECASE),
    # Instagram / TikTok / FB references
    re.compile(r"\b(instagram|facebook|tiktok|snapchat|twitter|x\.com)\b", re.IGNORECASE),
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
