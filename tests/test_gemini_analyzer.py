import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import gemini_analyzer


def test_chunk_into_batches_splits_small_list_into_single_batch():
    comments = ["a", "b", "c"]

    result = gemini_analyzer.chunk_into_batches(comments, max_batch_size=100, max_batches=2)

    assert result["batches"] == [["a", "b", "c"]]
    assert result["dropped"] == []


def test_chunk_into_batches_never_exceeds_max_batches():
    comments = [f"comentario {i}" for i in range(250)]

    result = gemini_analyzer.chunk_into_batches(comments, max_batch_size=100, max_batches=2)

    assert len(result["batches"]) == 2
    assert all(len(batch) <= 100 for batch in result["batches"])
    assert len(result["dropped"]) == 250 - 200


def test_parse_batch_response_returns_valid_structured_items():
    raw_text = """
    [
        {"comentario": "Qual o preço?", "intencao_compra": "alta", "faixa_etaria_estimada": "25-34"},
        {"comentario": "Tem tamanho M?", "intencao_compra": "media", "faixa_etaria_estimada": "18-24"}
    ]
    """

    result = gemini_analyzer.parse_batch_response(raw_text)

    assert result == [
        {"comentario": "Qual o preço?", "intencao_compra": "alta", "faixa_etaria_estimada": "25-34"},
        {"comentario": "Tem tamanho M?", "intencao_compra": "media", "faixa_etaria_estimada": "18-24"},
    ]


def test_parse_batch_response_skips_items_missing_required_fields():
    raw_text = '[{"comentario": "oi"}, {"comentario": "Qual o preço?", "intencao_compra": "alta", "faixa_etaria_estimada": "25-34"}]'

    result = gemini_analyzer.parse_batch_response(raw_text)

    assert result == [
        {"comentario": "Qual o preço?", "intencao_compra": "alta", "faixa_etaria_estimada": "25-34"},
    ]


def test_parse_batch_response_raises_value_error_for_invalid_json():
    try:
        gemini_analyzer.parse_batch_response("isso nao e json")
        assert False, "esperava ValueError"
    except ValueError:
        pass


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeGeminiClient:
    def __init__(self, response_text=None, raise_rate_limit=False):
        self.response_text = response_text
        self.raise_rate_limit = raise_rate_limit
        self.calls = []

    def generate_content(self, prompt):
        self.calls.append(prompt)
        if self.raise_rate_limit:
            raise gemini_analyzer.GeminiRateLimitError("cota excedida")
        return FakeResponse(self.response_text)


def test_build_batch_prompt_includes_all_comments():
    prompt = gemini_analyzer.build_batch_prompt(["Qual o preço?", "Tem tamanho M?"])

    assert "Qual o preço?" in prompt
    assert "Tem tamanho M?" in prompt


def test_analyze_batch_returns_parsed_items_on_success():
    client = FakeGeminiClient(
        response_text='[{"comentario": "Qual o preço?", "intencao_compra": "alta", "faixa_etaria_estimada": "25-34"}]'
    )

    result = gemini_analyzer.analyze_batch(client, ["Qual o preço?"])

    assert result["status"] == "ok"
    assert result["items"] == [
        {"comentario": "Qual o preço?", "intencao_compra": "alta", "faixa_etaria_estimada": "25-34"}
    ]
    assert len(client.calls) == 1


def test_analyze_batch_handles_rate_limit_gracefully():
    client = FakeGeminiClient(raise_rate_limit=True)

    result = gemini_analyzer.analyze_batch(client, ["Qual o preço?"])

    assert result["status"] == "quota_exceeded"
    assert result["batch"] == ["Qual o preço?"]


class SequencedFakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate_content(self, prompt):
        self.calls.append(prompt)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return FakeResponse(response)


def test_analyze_comments_never_calls_client_more_than_twice():
    comments = [f"comentario {i}" for i in range(250)]
    client = SequencedFakeClient(
        [
            '[{"comentario": "c1", "intencao_compra": "alta", "faixa_etaria_estimada": "25-34"}]',
            '[{"comentario": "c2", "intencao_compra": "media", "faixa_etaria_estimada": "18-24"}]',
        ]
    )

    result = gemini_analyzer.analyze_comments(comments, client, max_batch_size=100, max_batches=2)

    assert len(client.calls) == 2
    assert len(result["items"]) == 2
    assert len(result["dropped"]) == 50
    assert result["failed_batches"] == 0


def test_analyze_comments_reports_quota_exceeded_batch_without_raising():
    comments = ["c1", "c2"]
    client = SequencedFakeClient([gemini_analyzer.GeminiRateLimitError("cota excedida")])

    result = gemini_analyzer.analyze_comments(comments, client, max_batch_size=100, max_batches=2)

    assert result["items"] == []
    assert result["failed_batches"] == 1
    assert result["dropped"] == []
