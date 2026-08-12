import json

DEFAULT_MAX_BATCH_SIZE = 100
DEFAULT_MAX_BATCHES = 2
REQUIRED_RESPONSE_FIELDS = {"comentario", "intencao_compra", "faixa_etaria_estimada"}


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
