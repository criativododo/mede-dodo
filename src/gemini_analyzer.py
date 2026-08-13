import json
import os
import time

from dotenv import load_dotenv

from google import genai
from google.genai import types
from google.genai.errors import APIError

load_dotenv()

DEFAULT_MAX_BATCH_SIZE = 100
DEFAULT_MAX_BATCHES = 2
REQUIRED_RESPONSE_FIELDS = {"comentario", "intencao_compra", "faixa_etaria_estimada"}

_RETRYABLE_ERROR_CODES = {429, 503}
_RETRYABLE_MESSAGE_SIGNATURES = ("unavailable", "high demand")
_RETRY_BACKOFF_SECONDS = (2, 4, 8)  # até 3 retries além da tentativa inicial


class GeminiRateLimitError(Exception):
    """Erro de limite de cota da API Gemini."""


def chunk_into_batches(comments, max_batch_size=DEFAULT_MAX_BATCH_SIZE, max_batches=DEFAULT_MAX_BATCHES):
    capacity = max_batch_size * max_batches
    usable = comments[:capacity]
    dropped = comments[capacity:]

    batches = [usable[i : i + max_batch_size] for i in range(0, len(usable), max_batch_size)]

    return {"batches": batches, "dropped": dropped}


def parse_batch_response(raw_text):
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Resposta do Gemini não é um JSON válido: {exc}") from exc

    if not isinstance(parsed, list):
        raise ValueError("Resposta do Gemini deve ser uma lista de itens")

    return [item for item in parsed if REQUIRED_RESPONSE_FIELDS.issubset(item.keys())]


PROMPT_TEMPLATE = """\
Classifique cada comentário abaixo e responda APENAS com uma lista JSON, \
um objeto por comentário, no formato:
[{{"comentario": "<texto original>", "intencao_compra": "alta|media|baixa|nenhuma", \
"faixa_etaria_estimada": "<faixa ou desconhecida>"}}]

Comentários:
{comentarios}
"""


def build_batch_prompt(batch):
    comentarios = "\n".join(f"- {comentario}" for comentario in batch)
    return PROMPT_TEMPLATE.format(comentarios=comentarios)


def _is_retryable_gemini_error(exc):
    """Erros temporários do Gemini (limite de cota ou indisponibilidade por alta
    demanda) valem retry; os demais (ex.: prompt inválido) devem falhar direto."""
    if exc.code in _RETRYABLE_ERROR_CODES:
        return True
    message = str(exc).lower()
    return any(signature in message for signature in _RETRYABLE_MESSAGE_SIGNATURES)


class RealGeminiClient:
    """Client real do Gemini via SDK oficial google.genai, com o mesmo
    contrato duck-typed (generate_content -> objeto com .text) usado por analyze_batch."""

    def __init__(self, model_name="gemini-flash-latest", api_key=None):
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY não definida no ambiente. Defina essa variável com uma "
                "chave válida do Google AI Studio antes de usar RealGeminiClient."
            )

        self._client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def generate_content(self, prompt):
        max_attempts = len(_RETRY_BACKOFF_SECONDS) + 1
        last_exc = None
        for attempt in range(max_attempts):
            try:
                return self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )
            except APIError as exc:
                if not _is_retryable_gemini_error(exc):
                    raise
                last_exc = exc
                if attempt < max_attempts - 1:
                    time.sleep(_RETRY_BACKOFF_SECONDS[attempt])

        raise GeminiRateLimitError(str(last_exc)) from last_exc


def analyze_batch(client, batch):
    prompt = build_batch_prompt(batch)
    try:
        response = client.generate_content(prompt)
    except GeminiRateLimitError:
        return {"status": "quota_exceeded", "batch": batch}

    items = parse_batch_response(response.text)
    return {"status": "ok", "items": items}


def analyze_comments(comments, client, max_batch_size=DEFAULT_MAX_BATCH_SIZE, max_batches=DEFAULT_MAX_BATCHES):
    chunked = chunk_into_batches(comments, max_batch_size=max_batch_size, max_batches=max_batches)

    items = []
    failed_batches = 0
    for batch in chunked["batches"]:
        result = analyze_batch(client, batch)
        if result["status"] == "ok":
            items.extend(result["items"])
        else:
            failed_batches += 1

    return {
        "items": items,
        "dropped": chunked["dropped"],
        "failed_batches": failed_batches,
    }
