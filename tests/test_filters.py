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


def test_filter_comments_treats_decorated_short_praise_as_shallow():
    result = filters.filter_comments(
        ["vc é linda", "que gata", "Qual o preço desse vestido?"]
    )

    assert result["shallow"] == ["vc é linda", "que gata"]
    assert result["qualified"] == ["Qual o preço desse vestido?"]


def test_is_generic_praise_does_not_flag_longer_genuine_comment_containing_praise_word():
    assert filters.is_generic_praise("Muito linda, mas achei o tecido meio fino") is False


def test_is_bot_like_comment_detects_self_promo_and_link_swap_phrases():
    assert filters.is_bot_like_comment("Confira meu perfil, sigo de volta!") is True
    assert filters.is_bot_like_comment("Chama no direct pra parceria") is True
    assert filters.is_bot_like_comment("Olha esse link https://bit.ly/promo123") is True
    assert filters.is_bot_like_comment("s4s?") is True


def test_is_bot_like_comment_does_not_flag_genuine_question():
    assert filters.is_bot_like_comment("Qual o preço desse vestido?") is False


def test_filter_comments_treats_bot_spam_as_shallow():
    result = filters.filter_comments(
        ["Confira meu perfil, sigo de volta!", "Vocês têm tamanho G?"]
    )

    assert result["shallow"] == ["Confira meu perfil, sigo de volta!"]
    assert result["qualified"] == ["Vocês têm tamanho G?"]


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


def test_detect_sponsored_posts_matches_cupom_desconto_provador_and_codigo():
    posts = [
        {"post_id": "10", "raw": {"caption": "Cupom especial pra vocês"}},
        {"post_id": "11", "raw": {"caption": "Desconto de 20% só hoje"}},
        {"post_id": "12", "raw": {"caption": "Já foi no provador virtual?"}},
        {"post_id": "13", "raw": {"caption": "Use o código DODO10 no checkout"}},
    ]

    result = filters.detect_sponsored_posts(posts)

    by_id = {item["post_id"]: item for item in result}
    assert {"10", "11", "12", "13"} == set(by_id)
    assert "cupom" in by_id["10"]["termos"]
    assert "desconto" in by_id["11"]["termos"]
    assert "provador" in by_id["12"]["termos"]
    assert "use_o_codigo" in by_id["13"]["termos"]


def test_detect_sponsored_posts_matches_colecao_and_external_link():
    posts = [
        {"post_id": "14", "raw": {"caption": "Chegou a nova coleção de verão"}},
        {"post_id": "15", "raw": {"caption": "Compre aqui: https://loja-exemplo.com/produto"}},
        {"post_id": "16", "raw": {"caption": "Saiba mais em www.loja-exemplo.com/promo"}},
    ]

    result = filters.detect_sponsored_posts(posts)

    by_id = {item["post_id"]: item for item in result}
    assert {"14", "15", "16"} == set(by_id)
    assert "colecao" in by_id["14"]["termos"]
    assert "link_externo" in by_id["15"]["termos"]
    assert "link_externo" in by_id["16"]["termos"]


def test_detect_sponsored_posts_still_ignores_organic_posts_with_new_keywords():
    posts = [
        {"post_id": "17", "raw": {"caption": "Bom dia! Look de hoje, sem parcerias, sem cupons de ninguém."}},
    ]

    result = filters.detect_sponsored_posts(posts)

    assert result == []
