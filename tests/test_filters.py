import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import filters


def test_filter_comments_separates_emoji_only_as_shallow():
    result = filters.filter_comments(["😍😍😍", "Quanto custa esse vestido?"])

    assert result["shallow"] == ["😍😍😍"]
    assert result["qualified"] == ["Quanto custa esse vestido?"]


def test_filter_comments_treats_generic_short_praise_as_shallow():
    result = filters.filter_comments(["Linda", "top demais", "Qual o tamanho disponível?"])

    assert result["shallow"] == ["Linda", "top demais"]
    assert result["qualified"] == ["Qual o tamanho disponível?"]


def test_classify_intent_detects_all_categories():
    assert filters.classify_intent("Qual o preço desse vestido?") == {"preco"}
    assert filters.classify_intent("De que tecido é feito?") == {"tecido"}
    assert filters.classify_intent("Tem no tamanho M?") == {"tamanho"}
    assert filters.classify_intent("Qual o prazo de entrega?") == {"envio"}
    assert filters.classify_intent("Onde fica a loja?") == {"loja"}
    assert filters.classify_intent("Muito linda a foto!") == set()


def test_isolate_high_intent_filters_only_commercial_comments():
    comments = [
        "Qual o preço?",
        "Linda demais essa foto",
        "Vocês têm tamanho G?",
    ]

    result = filters.isolate_high_intent(comments)

    assert result == ["Qual o preço?", "Vocês têm tamanho G?"]
