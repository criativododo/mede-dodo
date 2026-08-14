import re
import unicodedata
from collections import Counter

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


HANDLE_NAME_SEGMENT_PATTERN = re.compile(r"[a-zA-ZÀ-ÿ]+")


def extract_first_name_from_handle(handle):
    """Deriva um candidato a primeiro nome a partir de um @handle/username do
    Instagram (ex.: 'ana_silva92' -> 'ana', '_maria2000' -> 'maria'), sem
    nenhuma chamada de rede extra — só heurística local sobre o username já
    coletado. Usado quando o comentário real não vem com um display name
    próprio (RF-06)."""
    if not handle:
        return ""
    match = HANDLE_NAME_SEGMENT_PATTERN.search(handle)
    return match.group(0) if match else ""


def extract_name_candidates_from_handle(handle):
    """Todos os segmentos alfabéticos de um @handle, na ordem em que aparecem
    (ex.: 'style_by_ana92' -> ['style', 'by', 'ana']). Handles reais de
    moda/lifestyle costumam prefixar ou sufixar o nome com termos genéricos
    ('style', 'by', 'oficial', 'eu'...) — usar só o primeiro segmento (como
    extract_first_name_from_handle) perde o nome real nesses casos."""
    if not handle:
        return []
    return HANDLE_NAME_SEGMENT_PATTERN.findall(handle)


def infer_gender_from_handle(handle, names_db=DEFAULT_NAMES_DB):
    """Tenta cada segmento alfabético do @handle contra a base de nomes, na
    ordem em que aparecem, até achar um que resolva para 'feminino' ou
    'masculino'. Só cai em 'indeterminado' se nenhum segmento corresponder a
    um nome conhecido com viés de gênero claro (RF: demografia de gênero)."""
    for candidate in extract_name_candidates_from_handle(handle):
        gender = infer_gender(candidate, names_db=names_db)
        if gender != "indeterminado":
            return gender
    return "indeterminado"


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
    original_lower = text.lower()
    por_mencao = []
    for keyword, uf in region_keywords.items():
        # "para" sem acento é uma preposição comum, indistinguível de "Pará" após
        # normalizar acentos — só conta como menção ao estado se o acento sobreviver
        # no texto original ("pará").
        if keyword == "para":
            matched = re.search(r"\bpará\b", original_lower)
        else:
            matched = re.search(rf"\b{re.escape(keyword)}\b", normalized)
        if matched and uf not in por_mencao:
            por_mencao.append(uf)

    return {"por_ddd": por_ddd, "por_mencao": por_mencao}


def summarize_region_distribution(detected_ufs):
    """Recebe uma lista de UFs (uma entrada por detecção — ex.: um por
    comentário com região identificada, já deduplicada dentro do próprio
    comentário) e devolve a distribuição proporcional entre os estados
    detectados, da mais para a menos frequente. Lista vazia -> []."""
    if not detected_ufs:
        return []
    total = len(detected_ufs)
    counts = Counter(detected_ufs)
    return [{"uf": uf, "pct": count / total} for uf, count in counts.most_common()]


def format_region_distribution(distribution):
    """Formata a distribuição de summarize_region_distribution como uma lista
    de strings 'UF (XX%)', ex.: ['SP (40%)', 'RJ (25%)', 'MG (15%)']."""
    return [f"{item['uf']} ({item['pct'] * 100:.0f}%)" for item in distribution]


def summarize_gender_distribution(comments, names_db=DEFAULT_NAMES_DB):
    """Demografia expandida com cobertura amostral (BENCHMARK-001.md §4.4,
    §7.3; Sprint 002 Fase 4). Reaproveita a mesma heurística já usada por
    app.py (nome explícito > @handle) sobre uma lista de comentários já
    coletados e devolve contagens, percentuais F/M/indeterminado e a
    cobertura (fração de comentários com gênero identificado — F ou M — sobre
    o total da amostra). Lista vazia -> zeros, nunca lança exceção."""
    total = len(comments)
    counts = {"feminino": 0, "masculino": 0, "indeterminado": 0}

    for comment in comments:
        nome_explicito = comment.get("nome")
        if nome_explicito:
            genero = infer_gender(nome_explicito, names_db=names_db)
        else:
            genero = infer_gender_from_handle(comment.get("username"), names_db=names_db)
        counts[genero] = counts.get(genero, 0) + 1

    identificados = counts["feminino"] + counts["masculino"]
    percentuais = {chave: (valor / total) if total else 0.0 for chave, valor in counts.items()}

    return {
        "counts": counts,
        "percentuais": percentuais,
        "total_identificados": identificados,
        "total_comentarios": total,
        "cobertura": (identificados / total) if total else 0.0,
    }


def summarize_region_distribution_with_coverage(comments, ddd_to_uf=DEFAULT_DDD_TO_UF, region_keywords=DEFAULT_REGION_KEYWORDS):
    """Mesma extração de região por DDD/menção já usada por app.py, mas sobre
    uma lista de comentários já coletados, com a cobertura amostral anexada
    (BENCHMARK-001.md §4.4/§7.3): fração de comentários em que pelo menos uma
    UF foi detectada sobre o total da amostra. Lista vazia -> zeros, nunca
    lança exceção."""
    total = len(comments)
    detected_ufs = []
    comentarios_com_regiao = 0

    for comment in comments:
        resultado = infer_region(comment.get("texto", ""), ddd_to_uf=ddd_to_uf, region_keywords=region_keywords)
        ufs_no_comentario = []
        for uf in resultado["por_ddd"] + resultado["por_mencao"]:
            if uf not in ufs_no_comentario:
                ufs_no_comentario.append(uf)
        if ufs_no_comentario:
            comentarios_com_regiao += 1
        detected_ufs.extend(ufs_no_comentario)

    return {
        "distribuicao": summarize_region_distribution(detected_ufs),
        "total_comentarios": total,
        "comentarios_com_regiao": comentarios_com_regiao,
        "cobertura": (comentarios_com_regiao / total) if total else 0.0,
    }
