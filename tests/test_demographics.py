"""Testes unitários da ISSUE-003: motor de demografia local (gênero e DDD)."""

from src.features.analise import demographics


# --- estimate_gender_distribution -----------------------------------------------------------


def test_common_female_name_classified_as_female():
    result = demographics.estimate_gender_distribution(["Maria"])
    assert result == {"female_pct": 100.0, "male_pct": 0.0, "unknown_pct": 0.0, "coverage_pct": 100.0}


def test_common_male_name_classified_as_male():
    result = demographics.estimate_gender_distribution(["Joao"])
    assert result == {"female_pct": 0.0, "male_pct": 100.0, "unknown_pct": 0.0, "coverage_pct": 100.0}


def test_unknown_name_classified_as_indeterminado():
    result = demographics.estimate_gender_distribution(["xerferaldozz"])
    assert result == {"female_pct": 0.0, "male_pct": 0.0, "unknown_pct": 100.0, "coverage_pct": 0.0}


def test_mixed_sample_percentages_sum_to_100():
    names = ["Maria", "Joao", "Ana", "xerferaldozz"]
    result = demographics.estimate_gender_distribution(names)

    assert result["female_pct"] == 50.0  # Maria, Ana
    assert result["male_pct"] == 25.0  # Joao
    assert result["unknown_pct"] == 25.0  # xerferaldozz
    assert round(result["female_pct"] + result["male_pct"] + result["unknown_pct"], 1) == 100.0
    assert result["coverage_pct"] == 75.0


def test_empty_list_returns_zeroed_contract():
    result = demographics.estimate_gender_distribution([])
    assert result == {"female_pct": 0.0, "male_pct": 0.0, "unknown_pct": 0.0, "coverage_pct": 0.0}


def test_extracts_first_name_from_full_name():
    result = demographics.estimate_gender_distribution(["Maria Clara Souza"])
    assert result["female_pct"] == 100.0


def test_extracts_first_name_from_instagram_style_username():
    result = demographics.estimate_gender_distribution(["maria.santos92"])
    assert result["female_pct"] == 100.0


def test_accented_name_matches_unaccented_dataset():
    result = demographics.estimate_gender_distribution(["João"])
    assert result["male_pct"] == 100.0


# --- estimate_location_by_ddd -----------------------------------------------------------


def test_extracts_valid_ddd_with_parentheses():
    result = demographics.estimate_location_by_ddd(["Amei! sou de SP (11) 91234-5678"])
    assert result["top_estados"] == [{"uf": "SP", "mencoes": 1}]
    assert result["amostra_com_ddd_n"] == 1
    assert result["coverage_pct"] == 100.0


def test_extracts_valid_ddd_without_parentheses():
    result = demographics.estimate_location_by_ddd(["Contato: 21 98765-4321"])
    assert result["top_estados"] == [{"uf": "RJ", "mencoes": 1}]


def test_ignores_false_positive_numbers():
    result = demographics.estimate_location_by_ddd(
        ["Nasci em 1998, moro em BH", "CEP 04578-000 apaixonada por moda", "sem numero nenhum aqui"]
    )
    assert result["top_estados"] == []
    assert result["amostra_com_ddd_n"] == 0
    assert result["coverage_pct"] == 0.0


def test_ranks_top_3_states_by_frequency():
    text_samples = [
        "(11) 91111-1111",
        "(11) 92222-2222",
        "(21) 93333-3333",
        "(31) 94444-4444",
        "sem contato aqui",
    ]
    result = demographics.estimate_location_by_ddd(text_samples)

    assert result["top_estados"][0] == {"uf": "SP", "mencoes": 2}
    assert {"uf": "RJ", "mencoes": 1} in result["top_estados"]
    assert {"uf": "MG", "mencoes": 1} in result["top_estados"]
    assert len(result["top_estados"]) == 3
    assert result["amostra_n"] == 5
    assert result["amostra_com_ddd_n"] == 4
    assert result["coverage_pct"] == 80.0


def test_empty_list_returns_zeroed_contract_for_location():
    result = demographics.estimate_location_by_ddd([])
    assert result == {"top_estados": [], "amostra_n": 0, "amostra_com_ddd_n": 0, "coverage_pct": 0.0}
