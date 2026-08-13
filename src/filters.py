import re
import unicodedata

GENERIC_PRAISE_WORDS = {
    "linda",
    "lindona",
    "linda demais",
    "lindo",
    "lindao",
    "gata",
    "gatona",
    "gato",
    "gatao",
    "top",
    "top demais",
    "diva",
    "musa",
    "perfeita",
    "perfeito",
    "poderosa",
    "poderoso",
    "arrasou",
    "incrivel",
    "demais",
    "maravilhosa",
    "maravilhoso",
    "deusa",
    "princesa",
    "rainha",
}

# palavras de preenchimento sem conteúdo próprio: ignoradas ao avaliar se um
# comentário decorado (ex.: "vc é linda", "que gata") é, na essência, só um
# elogio genérico de uma palavra da lista acima.
_FILLER_WORDS = {
    "que",
    "muito",
    "mt",
    "mto",
    "tao",
    "super",
    "vc",
    "voce",
    "ce",
    "e",
    "eh",
    "ta",
    "esta",
    "a",
    "o",
    "ai",
    "aii",
    "aiii",
    "mesmo",
    "msm",
}

# sinais de spam/bot validados por pesquisa de mercado (auto-promoção,
# troca de curtida/seguidor, links externos em comentário) — ver
# docs/issues/ISSUE-0003.md, seção "Refinamento de qualidade (2026-08-13)".
_BOT_SPAM_PATTERNS = (
    re.compile(r"confira (o\s+)?meu perfil", re.IGNORECASE),
    re.compile(r"\bd\.?m\b.{0,15}(parceria|promo|divulga)", re.IGNORECASE),
    re.compile(r"chama(r)?\s+no\s+(direct|inbox)", re.IGNORECASE),
    re.compile(r"\bs4s\b", re.IGNORECASE),
    re.compile(r"sigo de volta|siga de volta|curtida por curtida", re.IGNORECASE),
)

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


def _content_words(text):
    normalized = normalize_text(text)
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    return [word for word in normalized.split() if word and word not in _FILLER_WORDS]


def is_generic_praise(text):
    if normalize_text(text) in GENERIC_PRAISE_WORDS:
        return True
    words = _content_words(text)
    return bool(words) and all(word in GENERIC_PRAISE_WORDS for word in words)


def is_bot_like_comment(text):
    """Sinais de spam/bot validados por pesquisa de mercado: comentário só
    com link externo, ou frases típicas de troca de engajamento/autopromoção
    (ver docs/issues/ISSUE-0003.md)."""
    stripped = text.strip()
    if not stripped:
        return False
    if EXTERNAL_LINK_PATTERN.search(stripped):
        return True
    return any(pattern.search(stripped) for pattern in _BOT_SPAM_PATTERNS)


def is_shallow_comment(text):
    return is_emoji_only(text) or is_generic_praise(text) or is_bot_like_comment(text)


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


SPONSORED_PATTERNS = {
    "#publi": re.compile(r"#publi\w*", re.IGNORECASE),
    "#ad": re.compile(r"#ad\b", re.IGNORECASE),
    "parceria": re.compile(r"\bparceria\b", re.IGNORECASE),
    "patrocinado": re.compile(r"\bpatrocinad[oa]\b", re.IGNORECASE),
    "cupom": re.compile(r"\bcupom\b", re.IGNORECASE),
    "desconto": re.compile(r"\bdesconto\b", re.IGNORECASE),
    "provador": re.compile(r"\bprovador\b", re.IGNORECASE),
    "use_o_codigo": re.compile(r"\buse\s+o\s+c[oó]digo\b", re.IGNORECASE),
    "colecao": re.compile(r"\bcole[çc][ãa]o\b", re.IGNORECASE),
}
BRAND_MENTION_PATTERN = re.compile(r"@([A-Za-z0-9_.]+)")
EXTERNAL_LINK_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)


def detect_sponsored_posts(posts):
    """RF-09: varre as legendas já coletadas em busca de indícios de conteúdo
    comercial (publi/parceria/patrocínio), só regex local sobre texto já
    raspado — sem nenhuma chamada externa."""
    sponsored = []
    for post in posts:
        raw = post.get("raw") or {}
        caption = raw.get("caption") or ""
        if not caption:
            continue

        termos = [nome for nome, pattern in SPONSORED_PATTERNS.items() if pattern.search(caption)]
        marcas = BRAND_MENTION_PATTERN.findall(caption)
        if marcas:
            termos.append("mencao_marca")
        if EXTERNAL_LINK_PATTERN.search(caption):
            termos.append("link_externo")

        if not termos:
            continue

        shortcode = raw.get("shortcode")
        sponsored.append(
            {
                "post_id": post.get("post_id"),
                "shortcode": shortcode,
                "link": f"https://www.instagram.com/p/{shortcode}/" if shortcode else None,
                "termos": termos,
                "marcas": marcas,
            }
        )
    return sponsored
