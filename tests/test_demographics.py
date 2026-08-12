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


def test_extract_name_candidates_from_handle_returns_all_alpha_segments_in_order():
    assert demographics.extract_name_candidates_from_handle("style_by_ana92") == ["style", "by", "ana"]


def test_extract_name_candidates_from_handle_returns_empty_list_for_falsy_input():
    assert demographics.extract_name_candidates_from_handle(None) == []
    assert demographics.extract_name_candidates_from_handle("") == []


def test_infer_gender_from_handle_uses_first_segment_when_it_is_a_known_name():
    assert demographics.infer_gender_from_handle("maria_silva92", names_db=CUSTOM_NAMES_DB) == "feminino"


def test_infer_gender_from_handle_falls_back_to_later_segment_when_first_is_not_a_name():
    """Handles reais de moda/lifestyle costumam prefixar o nome com termos
    genéricos ('style', 'eu', 'oficial'...) — pegar só o primeiro segmento
    (comportamento antigo) classificaria erroneamente como indeterminado."""
    assert demographics.infer_gender_from_handle("style_by_maria", names_db=CUSTOM_NAMES_DB) == "feminino"
    assert demographics.infer_gender_from_handle("its_joao_oficial", names_db=CUSTOM_NAMES_DB) == "masculino"


def test_infer_gender_from_handle_returns_indeterminado_when_no_segment_matches():
    assert demographics.infer_gender_from_handle("xyz_qwerty123", names_db=CUSTOM_NAMES_DB) == "indeterminado"


def test_infer_gender_from_handle_returns_indeterminado_for_falsy_input():
    assert demographics.infer_gender_from_handle(None, names_db=CUSTOM_NAMES_DB) == "indeterminado"


FEMALE_FASHION_HANDLES = [
    "style_by_maria",
    "its_ana_oficial",
    "camila.moda92",
    "eu_juliana_looks",
    "fernanda_style_",
    "look.by.patricia",
]


def test_infer_gender_from_handle_classifies_prefixed_fashion_handles_as_feminino_using_real_ibge_base():
    """Prova de integração RF: perfis femininos de moda/lifestyle devem
    classificar a amostragem como predominantemente feminina (>80%) mesmo
    quando os @handles reais trazem prefixos genéricos antes do nome."""
    names_db = data_loaders.load_names_db()

    resultados = [demographics.infer_gender_from_handle(h, names_db=names_db) for h in FEMALE_FASHION_HANDLES]

    feminino_ratio = resultados.count("feminino") / len(resultados)
    assert feminino_ratio > 0.8, resultados


def test_summarize_region_distribution_returns_proportional_breakdown_sorted_descending():
    detected_ufs = ["SP", "SP", "SP", "SP", "RJ", "RJ", "RJ", "MG", "MG", "BA"]

    distribution = demographics.summarize_region_distribution(detected_ufs)

    assert distribution == [
        {"uf": "SP", "pct": 0.4},
        {"uf": "RJ", "pct": 0.3},
        {"uf": "MG", "pct": 0.2},
        {"uf": "BA", "pct": 0.1},
    ]


def test_summarize_region_distribution_returns_empty_list_for_no_detections():
    assert demographics.summarize_region_distribution([]) == []


def test_format_region_distribution_renders_uf_with_rounded_percentage():
    distribution = [{"uf": "SP", "pct": 0.4}, {"uf": "RJ", "pct": 0.25}, {"uf": "MG", "pct": 0.15}]

    assert demographics.format_region_distribution(distribution) == ["SP (40%)", "RJ (25%)", "MG (15%)"]


def test_format_region_distribution_returns_empty_list_for_empty_distribution():
    assert demographics.format_region_distribution([]) == []
