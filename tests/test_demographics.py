import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import demographics

CUSTOM_NAMES_DB = {
    "maria": {"F": 950, "M": 5},
    "joao": {"F": 2, "M": 900},
    "alex": {"F": 480, "M": 520},
}


def test_infer_gender_from_predominantly_female_name():
    assert demographics.infer_gender("Maria", names_db=CUSTOM_NAMES_DB) == "feminino"


def test_infer_gender_from_predominantly_male_name():
    assert demographics.infer_gender("João", names_db=CUSTOM_NAMES_DB) == "masculino"


def test_infer_gender_returns_indeterminado_for_ambiguous_name():
    assert demographics.infer_gender("Alex", names_db=CUSTOM_NAMES_DB) == "indeterminado"


def test_infer_gender_returns_indeterminado_for_unknown_name():
    assert demographics.infer_gender("Zyxabc", names_db=CUSTOM_NAMES_DB) == "indeterminado"


def test_infer_gender_extracts_first_name_from_full_name():
    assert demographics.infer_gender("Maria Silva Souza", names_db=CUSTOM_NAMES_DB) == "feminino"


CUSTOM_DDD_TO_UF = {"11": "SP", "21": "RJ", "71": "BA"}
CUSTOM_REGION_KEYWORDS = {"bahia": "BA", "rio de janeiro": "RJ", "sao paulo": "SP"}


def test_infer_region_extracts_uf_from_phone_number_ddd():
    result = demographics.infer_region(
        "me chama no (11) 91234-5678",
        ddd_to_uf=CUSTOM_DDD_TO_UF,
        region_keywords=CUSTOM_REGION_KEYWORDS,
    )

    assert result["por_ddd"] == ["SP"]


def test_infer_region_extracts_uf_from_keyword_mention():
    result = demographics.infer_region(
        "moro na Bahia, adorei a peça",
        ddd_to_uf=CUSTOM_DDD_TO_UF,
        region_keywords=CUSTOM_REGION_KEYWORDS,
    )

    assert result["por_mencao"] == ["BA"]


def test_infer_region_returns_empty_lists_when_no_match():
    result = demographics.infer_region(
        "muito linda a foto",
        ddd_to_uf=CUSTOM_DDD_TO_UF,
        region_keywords=CUSTOM_REGION_KEYWORDS,
    )

    assert result == {"por_ddd": [], "por_mencao": []}
