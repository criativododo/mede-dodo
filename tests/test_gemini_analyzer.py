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


def test_prompt_template_requests_sentiment_and_purchase_signal_fields():
    prompt = gemini_analyzer.build_batch_prompt(["Qual o preço?"])

    assert "categoria_sentimento" in prompt
    assert "sinais_compra" in prompt
    for categoria in gemini_analyzer.SENTIMENT_CATEGORIES:
        assert categoria in prompt


def test_prompt_template_never_offers_desconhecida_as_faixa_etaria_default():
    prompt = gemini_analyzer.build_batch_prompt(["Qual o preço?"])

    assert "ou desconhecida" not in prompt
    assert "desconhecida" not in prompt
    assert "faixa_etaria_estimada" in prompt


def test_parse_batch_response_keeps_legacy_three_field_items_for_backward_compatibility():
    raw_text = '[{"comentario": "Qual o preço?", "intencao_compra": "alta", "faixa_etaria_estimada": "25-34"}]'

    result = gemini_analyzer.parse_batch_response(raw_text)

    assert result == [
        {"comentario": "Qual o preço?", "intencao_compra": "alta", "faixa_etaria_estimada": "25-34"}
    ]


def test_parse_batch_response_preserves_extra_enrichment_fields():
    raw_text = (
        '[{"comentario": "Qual o preço?", "intencao_compra": "alta", '
        '"faixa_etaria_estimada": "25-34", "categoria_sentimento": "interesse_comercial", '
        '"sinais_compra": ["preco"]}]'
    )

    result = gemini_analyzer.parse_batch_response(raw_text)

    assert result[0]["categoria_sentimento"] == "interesse_comercial"
    assert result[0]["sinais_compra"] == ["preco"]


def test_summarize_brand_suitability_with_no_items_returns_sem_dados():
    result = gemini_analyzer.summarize_brand_suitability([])

    assert result["indicador"] == "sem_dados"
    assert result["alertas"] == []
    assert result["faixa_etaria_predominante"] == "sem_dados"
    assert result["distribuicao_intencao_compra"] == {
        "alta": 0.0,
        "media": 0.0,
        "baixa": 0.0,
        "nenhuma": 0.0,
    }


def test_summarize_brand_suitability_computes_percentages_and_high_indicador():
    items = [
        {"intencao_compra": "alta", "categoria_sentimento": "interesse_comercial"},
        {"intencao_compra": "alta", "categoria_sentimento": "interesse_comercial"},
        {"intencao_compra": "alta", "categoria_sentimento": "interesse_comercial"},
        {"intencao_compra": "nenhuma", "categoria_sentimento": "validacao_pessoal"},
    ]

    result = gemini_analyzer.summarize_brand_suitability(items, pod_index=0.05)

    assert result["indicador"] == "alto"
    assert result["comentarios_alta_intencao"] == 3
    assert result["pct_interesse_comercial"] == 0.75
    assert result["pct_validacao_pessoal"] == 0.25
    assert result["alertas"] == []


def test_summarize_brand_suitability_computes_intencao_compra_distribution():
    items = [
        {"intencao_compra": "alta", "categoria_sentimento": "interesse_comercial"},
        {"intencao_compra": "alta", "categoria_sentimento": "interesse_comercial"},
        {"intencao_compra": "media", "categoria_sentimento": "interesse_comercial"},
        {"intencao_compra": "baixa", "categoria_sentimento": "validacao_pessoal"},
    ]

    result = gemini_analyzer.summarize_brand_suitability(items)

    assert result["distribuicao_intencao_compra"] == {
        "alta": 0.5,
        "media": 0.25,
        "baixa": 0.25,
        "nenhuma": 0.0,
    }


def test_summarize_brand_suitability_picks_predominant_faixa_etaria_ignoring_unknown():
    items = [
        {"intencao_compra": "alta", "categoria_sentimento": "interesse_comercial", "faixa_etaria_estimada": "18-24"},
        {"intencao_compra": "media", "categoria_sentimento": "interesse_comercial", "faixa_etaria_estimada": "18-24"},
        {"intencao_compra": "baixa", "categoria_sentimento": "validacao_pessoal", "faixa_etaria_estimada": "25-34"},
        {"intencao_compra": "nenhuma", "categoria_sentimento": "spam_ruido", "faixa_etaria_estimada": "desconhecida"},
    ]

    result = gemini_analyzer.summarize_brand_suitability(items)

    assert result["faixa_etaria_predominante"] == "18-24"


def test_summarize_brand_suitability_faixa_etaria_sem_dados_when_all_unknown():
    items = [
        {"intencao_compra": "nenhuma", "categoria_sentimento": "spam_ruido", "faixa_etaria_estimada": "desconhecida"},
    ]

    result = gemini_analyzer.summarize_brand_suitability(items)

    assert result["faixa_etaria_predominante"] == "sem_dados"


def test_summarize_brand_suitability_flags_high_pod_index_and_spam_ratio():
    items = [
        {"intencao_compra": "nenhuma", "categoria_sentimento": "spam_ruido"},
        {"intencao_compra": "nenhuma", "categoria_sentimento": "spam_ruido"},
        {"intencao_compra": "nenhuma", "categoria_sentimento": "validacao_pessoal"},
    ]

    result = gemini_analyzer.summarize_brand_suitability(items, pod_index=0.42)

    assert result["indicador"] == "baixo"
    assert any("pods" in alerta.lower() for alerta in result["alertas"])
    assert any("spam" in alerta.lower() or "ruído" in alerta.lower() for alerta in result["alertas"])


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


def test_real_gemini_client_without_api_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    try:
        gemini_analyzer.RealGeminiClient()
        assert False, "esperava erro por falta de GEMINI_API_KEY"
    except RuntimeError as exc:
        assert "GEMINI_API_KEY" in str(exc)


def test_real_gemini_client_converts_sdk_rate_limit_error(monkeypatch):
    from google.genai.errors import APIError

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr(gemini_analyzer.time, "sleep", lambda seconds: None)

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            raise APIError(code=429, response_json={"message": "cota gratuita excedida"})

    class FakeSdkClient:
        def __init__(self, *args, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr(gemini_analyzer.genai, "Client", FakeSdkClient)

    client = gemini_analyzer.RealGeminiClient()

    try:
        client.generate_content("prompt qualquer")
        assert False, "esperava GeminiRateLimitError"
    except gemini_analyzer.GeminiRateLimitError:
        pass


def test_real_gemini_client_retries_on_503_high_demand_and_recovers(monkeypatch):
    from google.genai.errors import APIError

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    sleep_calls = []
    monkeypatch.setattr(gemini_analyzer.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    call_count = {"n": 0}

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise APIError(
                    code=503,
                    response_json={
                        "status": "UNAVAILABLE",
                        "message": (
                            "This model is currently experiencing high demand. "
                            "Spikes in demand are usually temporary. Please try again later."
                        ),
                    },
                )
            return FakeResponse("[]")

    class FakeSdkClient:
        def __init__(self, *args, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr(gemini_analyzer.genai, "Client", FakeSdkClient)

    client = gemini_analyzer.RealGeminiClient()
    response = client.generate_content("prompt qualquer")

    assert response.text == "[]"
    assert call_count["n"] == 3
    assert sleep_calls == [2, 4]


def test_real_gemini_client_raises_rate_limit_error_after_exhausting_503_retries(monkeypatch):
    from google.genai.errors import APIError

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    sleep_calls = []
    monkeypatch.setattr(gemini_analyzer.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            raise APIError(
                code=503,
                response_json={"status": "UNAVAILABLE", "message": "high demand"},
            )

    class FakeSdkClient:
        def __init__(self, *args, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr(gemini_analyzer.genai, "Client", FakeSdkClient)

    client = gemini_analyzer.RealGeminiClient()

    try:
        client.generate_content("prompt qualquer")
        assert False, "esperava GeminiRateLimitError"
    except gemini_analyzer.GeminiRateLimitError:
        pass

    assert sleep_calls == [2, 4, 8]


def test_real_gemini_client_does_not_retry_non_retryable_api_error(monkeypatch):
    from google.genai.errors import APIError

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    sleep_calls = []
    monkeypatch.setattr(gemini_analyzer.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    call_count = {"n": 0}

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            call_count["n"] += 1
            raise APIError(code=400, response_json={"status": "INVALID_ARGUMENT", "message": "prompt inválido"})

    class FakeSdkClient:
        def __init__(self, *args, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr(gemini_analyzer.genai, "Client", FakeSdkClient)

    client = gemini_analyzer.RealGeminiClient()

    try:
        client.generate_content("prompt qualquer")
        assert False, "esperava APIError propagado sem retry"
    except APIError:
        pass

    assert call_count["n"] == 1
    assert sleep_calls == []


def test_real_gemini_client_requests_structured_json_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    captured = {}

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            captured["kwargs"] = {"model": model, "contents": contents, "config": config}
            return FakeResponse("[]")

    class FakeSdkClient:
        def __init__(self, *args, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr(gemini_analyzer.genai, "Client", FakeSdkClient)

    gemini_analyzer.RealGeminiClient().generate_content("prompt qualquer")

    config = captured["kwargs"]["config"]
    assert config.response_mime_type == "application/json"
