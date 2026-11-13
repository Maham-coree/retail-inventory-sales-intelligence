"""Small deterministic intent and entity matching helpers."""

import re
from difflib import SequenceMatcher

INTENT_PHRASES: dict[str, tuple[str, ...]] = {
    "greeting": ("hello", "hi", "hey", "salam", "assalam o alaikum", "good morning"),
    "help": ("help", "madad", "what can you do", "what can i ask", "capabilities"),
    "product_availability": (
        "stock of",
        "stock for",
        "stock hai",
        "kitna stock",
        "how many are available",
        "is available",
        "availability",
        "in stock",
    ),
    "product_price": ("price", "qeemat", "cost of", "how much is", "barcode", "category of"),
    "out_of_stock_list": ("out of stock", "no stock", "zero stock", "stock khatam"),
    "low_stock_list": ("low stock", "low inventory", "running low", "below reorder"),
    "reorder_list": ("reorder", "reorder alerts", "what should we reorder"),
    "sales_summary": (
        "sales",
        "revenue",
        "top products",
        "top selling",
        "sales today",
        "sales this month",
        "kitni sale",
    ),
    "supplier_info": ("supplier", "lead time", "vendor"),
    "purchase_orders_status": ("purchase order", "purchase orders", "open orders", "po status"),
    "troubleshooting": (
        "error",
        "not working",
        "does not work",
        "doesn't work",
        "why did",
        "why can't",
        "why can t",
        "sale rejected",
        "insufficient stock",
        "login error",
        "401",
        "403",
        "404",
        "409",
        "422",
        "page not load",
        "page does not load",
    ),
    "role_permissions": ("my role", "permissions", "what can i do", "access", "why is this hidden"),
    "how_to": (
        "how to",
        "how do i",
        "how can i",
        "steps to",
        "guide me",
        "show me how",
        "stock status",
        "reorder level",
        "what do statuses mean",
        "kaise",
    ),
}

INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "greeting": ("hello", "hi", "hey", "salam"),
    "help": ("help", "madad", "capabilities"),
    "product_availability": ("stock", "available", "availability", "quantity", "kitna", "hai"),
    "product_price": ("price", "qeemat", "cost", "barcode", "category"),
    "out_of_stock_list": ("out", "zero", "khatam"),
    "low_stock_list": ("low", "shortage", "kam"),
    "reorder_list": ("reorder", "restock"),
    "sales_summary": ("sale", "sales", "revenue", "invoice", "selling"),
    "supplier_info": ("supplier", "vendor", "lead"),
    "purchase_orders_status": ("purchase", "orders", "po"),
    "troubleshooting": ("error", "failed", "issue", "problem", "load", "conflict"),
    "role_permissions": ("role", "permission", "access", "hidden"),
    "how_to": ("how", "guide", "steps", "kaise"),
}

MIN_INTENT_SCORE = 0.45
STOP_WORDS = {
    "a", "an", "and", "are", "available", "do", "for", "from", "i", "in",
    "is", "it", "me", "of", "on", "please", "show", "the", "to", "what",
    "where", "which", "with", "hai", "ka", "ki", "ko", "mein", "mujhe",
}


def normalize_text(value: str) -> str:
    """Lowercase text and reduce punctuation/whitespace to word boundaries."""
    return " ".join(re.sub(r"[^\w]+", " ", value.lower(), flags=re.UNICODE).split())


def score_intents(message: str) -> dict[str, float]:
    normalized = normalize_text(message)
    if not normalized:
        return {}
    scores: dict[str, float] = {}
    for intent, phrases in INTENT_PHRASES.items():
        score = 0.0
        for phrase in phrases:
            normalized_phrase = normalize_text(phrase)
            if re.search(rf"(?:^| ){re.escape(normalized_phrase)}(?: |$)", normalized):
                score = max(score, 0.78 if " " in normalized_phrase else 0.62)
        words = set(normalized.split())
        keyword_hits = words.intersection(INTENT_KEYWORDS[intent])
        if keyword_hits:
            score = max(score, min(0.7, 0.3 + 0.22 * len(keyword_hits)))
        if score:
            scores[intent] = min(score, 1.0)
    return scores


def detect_intent(message: str) -> str | None:
    scores = score_intents(message)
    if not scores:
        return None
    intent, score = max(scores.items(), key=lambda item: (item[1], _intent_priority(item[0])))
    return intent if score >= MIN_INTENT_SCORE else None


def _intent_priority(intent: str) -> int:
    return {
        "out_of_stock_list": 12,
        "low_stock_list": 11,
        "reorder_list": 10,
        "product_price": 9,
        "product_availability": 8,
        "purchase_orders_status": 7,
        "supplier_info": 6,
        "sales_summary": 5,
        "troubleshooting": 4,
        "role_permissions": 3,
        "how_to": 2,
        "help": 1,
        "greeting": 0,
    }.get(intent, -1)


def match_names(message: str, candidates: list[dict[str, object]], cutoff: float = 0.46) -> list[dict[str, object]]:
    """Return best fuzzy matches for a name inside a short natural-language question."""
    normalized_message = normalize_text(message)
    message_words = [word for word in normalized_message.split() if word not in STOP_WORDS]
    matches: list[tuple[float, dict[str, object]]] = []
    for candidate in candidates:
        name = normalize_text(str(candidate.get("product_name") or candidate.get("store_name") or ""))
        sku = normalize_text(str(candidate.get("sku") or ""))
        if not name:
            continue
        if name in normalized_message or (sku and sku in normalized_message):
            matches.append((1.0, candidate))
            continue
        name_words = name.split()
        overlap = len(set(name_words).intersection(message_words)) / max(1, len(set(name_words)))
        has_exact_name_word = bool(set(name_words).intersection(message_words))
        width = max(1, len(name_words))
        windows = (
            " ".join(message_words[index:index + width])
            for index in range(max(1, len(message_words) - width + 1))
        )
        similarity = max(
            (SequenceMatcher(None, name, window).ratio() for window in windows),
            default=0.0,
        )
        score = max(overlap, 0.78 if has_exact_name_word else 0.0, similarity)
        if score >= cutoff:
            matches.append((score, candidate))
    matches.sort(key=lambda item: (-item[0], str(item[1].get("product_name", ""))))
    if not matches:
        return []
    top_score = matches[0][0]
    return [candidate for score, candidate in matches if score >= max(cutoff, top_score - 0.12)]


def redact_sensitive_text(message: str) -> str:
    """Remove common credential-shaped values before persistence or optional LLM use."""
    redacted = re.sub(
        r"(?i)\b(password|passcode|token|secret|api[\s_-]?key)\b\s*(?::|=|\bis\b)\s*\S+",
        r"\1=[redacted]",
        message,
    )
    redacted = re.sub(r"(?i)\bbearer\s+\S+", "Bearer [redacted]", redacted)
    redacted = re.sub(
        r"\b[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
        "[redacted]",
        redacted,
    )
    redacted = re.sub(
        r"(?i)\bpostgres(?:ql)?://[^/\s:@]+:[^@\s/]+@",
        "postgresql://[redacted]@",
        redacted,
    )
    return re.sub(r"\bsk-[A-Za-z0-9_-]{12,}\b", "[redacted]", redacted)
