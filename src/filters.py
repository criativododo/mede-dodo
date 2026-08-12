import re
import unicodedata

GENERIC_PRAISE_WORDS = {
    "linda",
    "lindona",
    "linda demais",
    "gata",
    "gatona",
    "top",
    "top demais",
    "diva",
    "musa",
    "perfeita",
    "poderosa",
    "arrasou",
    "incrivel",
    "demais",
    "maravilhosa",
}

INTENT_KEYWORDS = {
    "preco": [r"pre[çc]o", r"\bvalor\b", r"quanto (custa|é|fica|sai)"],
    "tecido": [r"tecido", r"\bmaterial\b", r"\bmalha\b"],
    "tamanho": [r"tamanho", r"numera[çc][ãa]o", r"\bserve\b", r"\bveste\b"],
    "envio": [r"\bfrete\b", r"\benvio\b", r"\bentrega\b", r"prazo"],
    "loja": [r"\bloja\b", r"onde (compro|compra|encontro|fica)"],
}

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "❤️"
    "]+",
    flags=re.UNICODE,
)


def is_emoji_only(text):
    stripped = text.strip()
    if not stripped:
        return False
    without_emoji = EMOJI_PATTERN.sub("", stripped)
    return without_emoji.strip() == ""


def normalize_text(text):
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return without_accents.strip().lower()


def is_generic_praise(text):
    return normalize_text(text) in GENERIC_PRAISE_WORDS


def is_shallow_comment(text):
    return is_emoji_only(text) or is_generic_praise(text)


def filter_comments(comments):
    qualified = []
    shallow = []
    for comment in comments:
        if is_shallow_comment(comment):
            shallow.append(comment)
        else:
            qualified.append(comment)
    return {"qualified": qualified, "shallow": shallow}


def classify_intent(text):
    normalized = normalize_text(text)
    matched = set()
    for category, patterns in INTENT_KEYWORDS.items():
        if any(re.search(pattern, normalized) for pattern in patterns):
            matched.add(category)
    return matched


def is_high_intent_comment(text):
    return bool(classify_intent(text))


def isolate_high_intent(comments):
    return [comment for comment in comments if is_high_intent_comment(comment)]
