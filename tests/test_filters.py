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


def test_detect_sponsored_posts_matches_hashtag_publi():
    posts = [
        {"post_id": "1", "raw": {"shortcode": "abc123", "caption": "Look de hoje #publi com a @marca_x"}},
    ]

    result = filters.detect_sponsored_posts(posts)

    assert len(result) == 1
    assert result[0]["post_id"] == "1"
    assert result[0]["link"] == "https://www.instagram.com/p/abc123/"
    assert "#publi" in result[0]["termos"]
    assert "mencao_marca" in result[0]["termos"]
    assert result[0]["marcas"] == ["marca_x"]


def test_detect_sponsored_posts_matches_ad_hashtag_and_parceria_and_patrocinado():
    posts = [
        {"post_id": "2", "raw": {"shortcode": "sc2", "caption": "Amei esse produto #ad"}},
        {"post_id": "3", "raw": {"shortcode": "sc3", "caption": "Em parceria com a marca"}},
        {"post_id": "4", "raw": {"shortcode": "sc4", "caption": "Post patrocinado pela marca"}},
    ]

    result = filters.detect_sponsored_posts(posts)

    assert {item["post_id"] for item in result} == {"2", "3", "4"}
    by_id = {item["post_id"]: item for item in result}
    assert "#ad" in by_id["2"]["termos"]
    assert "parceria" in by_id["3"]["termos"]
    assert "patrocinado" in by_id["4"]["termos"]


def test_detect_sponsored_posts_ignores_organic_posts():
    posts = [
        {"post_id": "5", "raw": {"shortcode": "sc5", "caption": "Bom dia! Look de hoje, sem parcerias."}},
        {"post_id": "6", "raw": {"caption": None}},
        {"post_id": "7", "raw": {}},
        {"post_id": "8", "raw": None},
    ]

    result = filters.detect_sponsored_posts(posts)

    assert result == []


def test_detect_sponsored_posts_link_is_none_without_shortcode():
    posts = [{"post_id": "9", "raw": {"caption": "Parceria com a marca"}}]

    result = filters.detect_sponsored_posts(posts)

    assert result[0]["link"] is None
    assert result[0]["post_id"] == "9"
