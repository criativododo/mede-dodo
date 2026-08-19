"""Heurística local (ISSUE-005) — pré-triagem conservadora, dedup e parecer de fallback.

100% Python puro, sem rede/Streamlit e sem recalcular métricas — as métricas
matemáticas pertencem exclusivamente a `metrics.py` (ADR-003, DUMMY.md §4). Só
classifica localmente casos inequívocos de ruído; qualquer coisa fora disso
(inclusive elogios curtos como "linda"/"amei", que podem carregar sinal de
estilo/afinidade) segue para o Gemini — ver
`docs/issues/issue-005-inteligencia-hibrida.md` §4.
"""

import hashlib
import re
import unicodedata

PROVIDER_LOCAL = "local_heuristic"
FALLBACK_LOCAL_PRIMARY = "local_primary"
FALLBACK_LOCAL_FALLBACK = "local_fallback"
FALLBACK_INDISPONIVEL = "indisponivel"
MODEL_VERSION_LOCAL = "local-heuristic-v1"

_VEREDITO_INDISPONIVEL = "indisponivel"

_EMOJI_RANGES = (
    "\U0001F300-\U0001FAFF"  # símbolos/pictogramas (inclui carinhas, corações coloridos)
    "\U00002600-\U000027BF"  # símbolos diversos + dingbats (inclui ❤/♥)
    "\U0001F1E6-\U0001F1FF"  # indicadores regionais (bandeiras)
    + chr(0xFE0F)  # variation selector-16 (força apresentação emoji)
    + chr(0x200D)  # zero-width joiner (emoji combinados, ex.: família/bandeiras)
)
_EMOJI_ONLY_PATTERN = re.compile(f"^[{_EMOJI_RANGES}\\s]+$")

# Padrões de spam evidente v1 — versionado deliberadamente conservador (SPEC §4.1):
# só cobre casos inequívocos (link solto, frase comercial padrão de spam), nunca
# elogio curto ou pergunta comercial legítima (essas seguem para o Gemini).
_SPAM_PATTERNS_V1 = [
    re.compile(r"https?://\S+", re.IGNORECASE),
    re.compile(r"\bcompre agora\b", re.IGNORECASE),
    re.compile(r"promo(ç|c)[aã]o imperd[ií]vel", re.IGNORECASE),
    re.compile(r"\bganhe seguidores\b", re.IGNORECASE),
]

# Reações repetitivas sem conteúdo lexical (risadas, etc.) — lista versionada v1.
_GENERIC_NOISE_PATTERNS_V1 = frozenset({
    "kk", "kkk", "kkkk", "kkkkk", "haha", "hahaha", "rs", "rsrs", "rsrsrs", "uhum",
})


def normalize_comment_text(text: str) -> str:
    """Normaliza unicode (NFKC), colapsa espaços e remove bordas — mesmo
    tratamento usado como base do hash de dedup e da checagem de evidência."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", normalized).strip()


def hash_comment(text: str) -> str:
    """Hash estável (sha256) do texto normalizado — chave de dedup/cache
    (SPEC §5.3, §12): o mesmo comentário nunca é reenviado ao Gemini duas vezes."""
    normalized = normalize_comment_text(text).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def is_empty_after_normalization(text: str) -> bool:
    return normalize_comment_text(text) == ""


def is_emoji_only(text: str) -> bool:
    normalized = normalize_comment_text(text)
    return bool(normalized) and bool(_EMOJI_ONLY_PATTERN.fullmatch(normalized))


def is_spam_pattern(text: str) -> bool:
    normalized = normalize_comment_text(text)
    return any(pattern.search(normalized) for pattern in _SPAM_PATTERNS_V1)


def is_generic_noise(text: str) -> bool:
    normalized = normalize_comment_text(text).lower()
    return normalized in _GENERIC_NOISE_PATTERNS_V1


def _local_result(comment_id, label: str, reason_code: str, status: str = "classified",
                   confidence: str = "high", evidence: str = "") -> dict:
    return {
        "comment_id": comment_id,
        "label": label,
        "status": status,
        "confidence": confidence,
        "evidence": evidence,
        "reason_code": reason_code,
        "provider_used": PROVIDER_LOCAL,
        "fallback_level": FALLBACK_LOCAL_PRIMARY,
    }


def classify_locally(comment: dict) -> dict | None:
    """Classifica localmente só os casos inequívocos de ruído (D). Qualquer
    outro caso (inclusive elogio curto ou pergunta comercial) retorna `None`
    — sinal explícito para o chamador encaminhar ao Gemini (SPEC §4.1/§4.2)."""
    comment_id = comment.get("comment_id")
    text = comment.get("text", "")
    normalized = normalize_comment_text(text)

    if is_empty_after_normalization(text):
        return _local_result(comment_id, "D", "noise")
    if is_emoji_only(text):
        return _local_result(comment_id, "D", "noise", evidence=normalized)
    if is_spam_pattern(text):
        return _local_result(comment_id, "D", "noise", evidence=normalized)
    if is_generic_noise(text):
        return _local_result(comment_id, "D", "noise", evidence=normalized)
    return None


def build_local_fallback_classification(comment_id) -> dict:
    """Estado explícito para comentário ambíguo que não pôde ser resolvido
    localmente e que o Gemini não conseguiu classificar (indisponível, rate
    limit, schema inválido) — nunca força uma categoria (SPEC §7.1)."""
    return {
        "comment_id": comment_id,
        "label": None,
        "status": "uncertain",
        "confidence": "low",
        "evidence": "",
        "reason_code": "insufficient_context",
        "provider_used": PROVIDER_LOCAL,
        "fallback_level": FALLBACK_LOCAL_FALLBACK,
    }


# --- Parecer local de fallback (SPEC §7.2, §8.2) -----------------------------------------------------------

def _bqi_band(value: float) -> str:
    if value >= 80:
        return "excelente"
    if value >= 65:
        return "saudavel"
    if value >= 50:
        return "alerta"
    return "nao_recomendado"


def _ci_band(value: float) -> str:
    if value >= 75:
        return "consistente"
    if value >= 60:
        return "aceitavel"
    return "instavel"


def _sd_band(value: float) -> str:
    if value <= 20:
        return "saudavel"
    if value <= 25:
        return "toleravel"
    if value <= 33:
        return "alerta"
    return "nao_recomendado"


def _veredito_from_bands(bqi_band: str, ci_band: str, sd_band: str) -> str:
    if bqi_band == "nao_recomendado" or sd_band == "nao_recomendado":
        return "nao_recomendada"
    if bqi_band == "excelente" and ci_band == "consistente" and sd_band in {"saudavel", "toleravel"}:
        return "recomendada"
    return "recomendada_com_ressalvas"


def build_local_opinion(metrics_summary: dict) -> dict:
    """Parecer templateado local (sem Gemini) — só preenche o veredito quando
    BQI/CI/SD estão disponíveis; caso contrário retorna `indisponivel` com a
    lacuna explícita (SPEC §7.2). Sempre exatamente 3 pontos fortes e 2
    alertas quando utilizável (§8.2), montados a partir de dados recebidos —
    nunca inventados."""
    er_branding = metrics_summary.get("er_branding")
    bqi = metrics_summary.get("bqi")
    ci = metrics_summary.get("ci")
    sd = metrics_summary.get("sd")

    if bqi is None or ci is None or sd is None:
        lacunas = []
        if bqi is None:
            lacunas.append("BQI indisponível")
        if ci is None:
            lacunas.append("Consistência (CI) indisponível")
        if sd is None:
            lacunas.append("Saturação de publis (SD) indisponível")
        return {
            "veredito": _VEREDITO_INDISPONIVEL,
            "pontos_fortes": [],
            "alertas": [],
            "formato_ideal": "indisponivel",
            "confianca": "baixa",
            "lacunas_de_dados": lacunas,
            "provider_used": "local_template",
            "fallback_level": FALLBACK_INDISPONIVEL,
        }

    bqi_band = _bqi_band(bqi)
    ci_band = _ci_band(ci)
    sd_band = _sd_band(sd)
    veredito = _veredito_from_bands(bqi_band, ci_band, sd_band)

    pontos_fortes = [
        {
            "texto": f"BQI de {bqi}/100 ({bqi_band.replace('_', ' ')})",
            "evidencia_metricas": ["bqi"],
            "confidence": "media",
        },
        {
            "texto": f"Consistência editorial (CI) de {ci}% ({ci_band.replace('_', ' ')})",
            "evidencia_metricas": ["ci"],
            "confidence": "media",
        },
        {
            "texto": (
                f"ER Branding de {er_branding}% observado no período" if er_branding is not None
                else f"Saturação de publis (SD) de {sd}% ({sd_band.replace('_', ' ')})"
            ),
            "evidencia_metricas": ["er_branding"] if er_branding is not None else ["sd"],
            "confidence": "media",
        },
    ]
    alertas = [
        {
            "texto": "Parecer gerado localmente (Gemini indisponível ou não configurado) — recomenda-se revisão humana.",
            "evidencia_metricas": [],
            "confidence": "baixa",
        },
        {
            "texto": f"Saturação de publis (SD) de {sd}% ({sd_band.replace('_', ' ')})",
            "evidencia_metricas": ["sd"],
            "confidence": "media",
        },
    ]

    return {
        "veredito": veredito,
        "pontos_fortes": pontos_fortes,
        "alertas": alertas,
        "formato_ideal": "indisponivel",
        "confianca": "media",
        "lacunas_de_dados": ["Parecer templateado local — sem interpretação linguística do Gemini"],
        "provider_used": "local_template",
        "fallback_level": FALLBACK_LOCAL_FALLBACK,
    }
