import re
import unicodedata

GENDER_THRESHOLD = 0.85

# Subconjunto parcial (capitais e DDDs mais comuns) — não é a tabela oficial
# completa da ANATEL. Ver Notas de Implementação em docs/issues/ISSUE-0002.md.
DEFAULT_DDD_TO_UF = {
    "11": "SP",
    "21": "RJ",
    "31": "MG",
    "41": "PR",
    "48": "SC",
    "51": "RS",
    "61": "DF",
    "62": "GO",
    "71": "BA",
    "81": "PE",
    "85": "CE",
    "91": "PA",
}

DEFAULT_REGION_KEYWORDS = {
    "sao paulo": "SP",
    "rio de janeiro": "RJ",
    "minas gerais": "MG",
    "belo horizonte": "MG",
    "parana": "PR",
    "curitiba": "PR",
    "santa catarina": "SC",
    "rio grande do sul": "RS",
    "porto alegre": "RS",
    "brasilia": "DF",
    "goias": "GO",
    "bahia": "BA",
    "salvador": "BA",
    "pernambuco": "PE",
    "recife": "PE",
    "ceara": "CE",
    "fortaleza": "CE",
    "para": "PA",
    "belem": "PA",
}

DDD_PATTERN = re.compile(r"\(?\b(\d{2})\)?[\s.-]?9?\d{4}[\s.-]?\d{4}\b")

DEFAULT_NAMES_DB = {
    "maria": {"F": 1000, "M": 2},
    "ana": {"F": 900, "M": 3},
    "juliana": {"F": 800, "M": 1},
    "camila": {"F": 750, "M": 1},
    "joao": {"F": 1, "M": 1000},
    "pedro": {"F": 1, "M": 850},
    "lucas": {"F": 2, "M": 900},
    "gabriel": {"F": 1, "M": 800},
}


def _normalize_name(name):
    decomposed = unicodedata.normalize("NFKD", name)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return without_accents.strip().lower()


def infer_gender(full_name, names_db=DEFAULT_NAMES_DB):
    first_name = full_name.strip().split()[0]
    key = _normalize_name(first_name)
    counts = names_db.get(key)
    if not counts:
        return "indeterminado"

    total = counts.get("F", 0) + counts.get("M", 0)
    if total == 0:
        return "indeterminado"

    female_ratio = counts.get("F", 0) / total
    if female_ratio >= GENDER_THRESHOLD:
        return "feminino"
    if (1 - female_ratio) >= GENDER_THRESHOLD:
        return "masculino"
    return "indeterminado"


def _normalize_text(text):
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return without_accents.strip().lower()


def infer_region(text, ddd_to_uf=DEFAULT_DDD_TO_UF, region_keywords=DEFAULT_REGION_KEYWORDS):
    por_ddd = []
    for match in DDD_PATTERN.finditer(text):
        ddd = match.group(1)
        uf = ddd_to_uf.get(ddd)
        if uf and uf not in por_ddd:
            por_ddd.append(uf)

    normalized = _normalize_text(text)
    por_mencao = []
    for keyword, uf in region_keywords.items():
        if re.search(rf"\b{re.escape(keyword)}\b", normalized) and uf not in por_mencao:
            por_mencao.append(uf)

    return {"por_ddd": por_ddd, "por_mencao": por_mencao}
