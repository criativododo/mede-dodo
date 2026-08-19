"""Demografia local (ISSUE-003): matching de nome (IBGE) e DDD/UF.

100% algorítmico, puro e local — nenhuma chamada de rede ou banco, apenas os
datasets estáticos em `data/`. Ver SPEC-01-MEDE-DODO.md §3.4.
"""

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parents[3] / "data"

with open(_DATA_DIR / "names_seed.json", encoding="utf-8") as _f:
    _NAMES_SEED = json.load(_f)

with open(_DATA_DIR / "ddd_uf.json", encoding="utf-8") as _f:
    _DDD_UF = json.load(_f)

# Exige um "rabo" telefone-símile (8-9 dígitos) após o DDD — aceita tanto
# "(XX)" quanto "XX" soltos, mas rejeita números de 2 dígitos avulsos
# (datas, anos, CEP) que não têm essa cauda.
_DDD_PATTERN = re.compile(r"\(?([1-9]\d)\)?[\s.-]?9?\d{4}[\s.-]?\d{4}")


def _normalize_first_name(raw_name: str) -> str:
    if not raw_name:
        return ""
    text = unicodedata.normalize("NFKD", raw_name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.strip().lower()
    first_token = re.split(r"[\s._-]+", text)[0] if text else ""
    return re.sub(r"[^a-z]", "", first_token)


def _classify_name(first_name: str) -> str:
    counts = _NAMES_SEED.get(first_name)
    if not counts:
        return "indeterminado"
    feminino = counts.get("F", 0)
    masculino = counts.get("M", 0)
    if feminino == 0 and masculino == 0:
        return "indeterminado"
    if feminino > masculino:
        return "feminino"
    if masculino > feminino:
        return "masculino"
    return "indeterminado"


def estimate_gender_distribution(names_list: list) -> dict:
    """Classifica cada nome de `names_list` (primeiro nome extraído e
    normalizado) por matching contra o dataset IBGE local
    (`data/names_seed.json`).

    Retorna `{"female_pct", "male_pct", "unknown_pct", "coverage_pct"}` —
    os três primeiros somam 100% da amostra; `coverage_pct` é a fração
    reconhecida (`female_pct + male_pct`), exposta separadamente para nunca
    mascarar amostras com pouquíssimo reconhecimento como zero silencioso.
    """
    total = len(names_list)
    if total == 0:
        return {"female_pct": 0.0, "male_pct": 0.0, "unknown_pct": 0.0, "coverage_pct": 0.0}

    tally = Counter(_classify_name(_normalize_first_name(name)) for name in names_list)
    female_pct = round(100 * tally["feminino"] / total, 1)
    male_pct = round(100 * tally["masculino"] / total, 1)
    unknown_pct = round(100 * tally["indeterminado"] / total, 1)

    return {
        "female_pct": female_pct,
        "male_pct": male_pct,
        "unknown_pct": unknown_pct,
        "coverage_pct": round(female_pct + male_pct, 1),
    }


def estimate_location_by_ddd(text_samples_list: list) -> dict:
    """Extrai padrões de DDD ("(XX)" ou "XX", seguidos de um número
    telefone-símile) em `text_samples_list`, valida cada DDD contra o
    dataset local (`data/ddd_uf.json`) e retorna o Top 3 estados por
    menções, com amostra e cobertura explícitas."""
    counts = Counter()
    amostra_com_ddd_n = 0

    for text in text_samples_list:
        if not text:
            continue
        sample_matched = False
        for match in _DDD_PATTERN.finditer(text):
            uf = _DDD_UF.get(match.group(1))
            if uf:
                counts[uf] += 1
                sample_matched = True
        if sample_matched:
            amostra_com_ddd_n += 1

    total = len(text_samples_list)
    top_estados = [{"uf": uf, "mencoes": n} for uf, n in counts.most_common(3)]

    return {
        "top_estados": top_estados,
        "amostra_n": total,
        "amostra_com_ddd_n": amostra_com_ddd_n,
        "coverage_pct": round(100 * amostra_com_ddd_n / total, 1) if total else 0.0,
    }
