import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import data_loaders, demographics

VALID_UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}


def test_load_ddd_to_uf_returns_known_capital_ddds():
    ddd_to_uf = data_loaders.load_ddd_to_uf()

    assert ddd_to_uf["11"] == "SP"
    assert ddd_to_uf["21"] == "RJ"
    assert ddd_to_uf["31"] == "MG"
    assert ddd_to_uf["61"] == "DF"


def test_load_ddd_to_uf_covers_all_67_official_ddds_with_valid_ufs():
    ddd_to_uf = data_loaders.load_ddd_to_uf()

    assert len(ddd_to_uf) == 67
    assert all(re.fullmatch(r"\d{2}", ddd) for ddd in ddd_to_uf)
    assert all(uf in VALID_UFS for uf in ddd_to_uf.values())


def test_load_names_db_returns_dict_in_expected_format():
    names_db = data_loaders.load_names_db()

    assert isinstance(names_db, dict)
    assert len(names_db) > 500
    counts = names_db["maria"]
    assert isinstance(counts["F"], int)
    assert isinstance(counts["M"], int)


def test_load_names_db_keys_are_normalized_without_accents():
    names_db = data_loaders.load_names_db()

    assert "jose" in names_db
    assert all(key == key.lower() for key in names_db)
    assert all(not re.search(r"[áàâãéêíóôõúç]", key) for key in names_db)


def test_load_names_db_reflects_real_gender_skew_for_common_names():
    names_db = data_loaders.load_names_db()

    maria = names_db["maria"]
    assert maria["F"] > maria["M"]
    joao = names_db["joao"]
    assert joao["M"] > joao["F"]


def test_infer_gender_integration_with_loaded_names_db():
    names_db = data_loaders.load_names_db()

    assert demographics.infer_gender("Maria Aparecida Silva", names_db=names_db) == "feminino"
    assert demographics.infer_gender("Joao Pedro Souza", names_db=names_db) == "masculino"


def test_infer_region_integration_with_loaded_ddd_to_uf():
    ddd_to_uf = data_loaders.load_ddd_to_uf()

    result = demographics.infer_region(
        "chama no whats (11) 91234-5678", ddd_to_uf=ddd_to_uf, region_keywords={}
    )

    assert result["por_ddd"] == ["SP"]
