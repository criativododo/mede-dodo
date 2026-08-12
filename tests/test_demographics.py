import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import data_loaders, demographics

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


PARA_REGION_KEYWORDS = {"para": "PA", "bahia": "BA"}


def test_infer_region_does_not_match_preposition_para_as_state():
    result = demographics.infer_region(
        "amei, vim aqui para comprar",
        ddd_to_uf=CUSTOM_DDD_TO_UF,
        region_keywords=PARA_REGION_KEYWORDS,
    )

    assert "PA" not in result["por_mencao"]


def test_infer_region_matches_para_state_when_accented_in_original_text():
    result = demographics.infer_region(
        "moro no Pará, amei a peça",
        ddd_to_uf=CUSTOM_DDD_TO_UF,
        region_keywords=PARA_REGION_KEYWORDS,
    )

    assert "PA" in result["por_mencao"]


FEMALE_NAMES_FROM_SPEC = ["Maria", "Ana", "Camila", "Fernanda", "Juliana", "Patricia", "Sofia"]


def test_infer_gender_classifies_spec_female_names_as_feminino_using_real_ibge_base():
    """Prova de integração: o pipeline real (app.py -> data_loaders.load_names_db())
    usa a base curada do IBGE, não o DEFAULT_NAMES_DB de exemplo. Perfis de
    moda/lifestyle com comentaristas de nomes tipicamente femininos devem
    classificar como 'feminino'."""
    names_db = data_loaders.load_names_db()

    for nome in FEMALE_NAMES_FROM_SPEC:
        assert demographics.infer_gender(nome, names_db=names_db) == "feminino", nome


def test_infer_gender_female_ratio_above_80_percent_for_spec_names_using_real_ibge_base():
    names_db = data_loaders.load_names_db()

    for nome in FEMALE_NAMES_FROM_SPEC:
        counts = names_db[demographics._normalize_name(nome)]
        total = counts["F"] + counts["M"]
        assert counts["F"] / total > 0.80, nome


def test_extract_first_name_from_handle_strips_underscore_suffix():
    assert demographics.extract_first_name_from_handle("ana_silva92") == "ana"


def test_extract_first_name_from_handle_strips_dot_and_digits():
    assert demographics.extract_first_name_from_handle("joao.pedro99") == "joao"


def test_extract_first_name_from_handle_ignores_leading_underscore():
    assert demographics.extract_first_name_from_handle("_maria2000") == "maria"


def test_extract_first_name_from_handle_returns_empty_for_no_letters():
    assert demographics.extract_first_name_from_handle("12345_") == ""


def test_extract_first_name_from_handle_returns_empty_for_falsy_input():
    assert demographics.extract_first_name_from_handle(None) == ""
    assert demographics.extract_first_name_from_handle("") == ""


def test_extract_first_name_from_handle_feeds_infer_gender_correctly():
    names_db = data_loaders.load_names_db()
    nome = demographics.extract_first_name_from_handle("ana_silva92")

    assert demographics.infer_gender(nome, names_db=names_db) == "feminino"
