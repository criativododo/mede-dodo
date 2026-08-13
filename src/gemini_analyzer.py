import json
import os
import time
from collections import Counter, deque

from dotenv import load_dotenv

from google import genai
from google.genai import types
from google.genai.errors import APIError

load_dotenv()

DEFAULT_MAX_BATCH_SIZE = 100
DEFAULT_MAX_BATCHES = 2

# Campos mínimos exigidos de cada item para não quebrar retrocompatibilidade
# com respostas/mocks do schema anterior — categoria_sentimento e
# sinais_compra são enriquecimento opcional (usados quando presentes, nunca
# exigidos para o item ser aceito).
REQUIRED_RESPONSE_FIELDS = {"comentario", "intencao_compra", "faixa_etaria_estimada"}
SENTIMENT_CATEGORIES = {"interesse_comercial", "validacao_pessoal", "duvida_critica", "spam_ruido"}
INTENCAO_COMPRA_NIVEIS = ("alta", "media", "baixa", "nenhuma")
FAIXA_ETARIA_DESCONHECIDA_VALORES = {None, "", "desconhecida"}
PURCHASE_SIGNAL_TYPES = {
    "preco",
    "tamanho",
    "caimento",
    "tecido",
    "onde_comprar",
    "estoque",
    "depoimento_compra",
}
ADERENCIA_INDICADOR_LABELS = {
    "alto": "Alto potencial de conversão",
    "medio": "Potencial de conversão moderado",
    "baixo": "Baixo potencial de conversão",
    "sem_dados": "Sem dados suficientes para avaliar",
}

# Taxonomia de territórios de fala (ISSUE-001 §5.10) — pilar_tematico é
# enriquecimento opcional por comentário, no mesmo padrão de
# categoria_sentimento/sinais_compra: nunca exigido para o item ser aceito.
THEMATIC_PILLARS = {
    "moda_vestuario",
    "beleza_autocuidado",
    "bem_estar_fitness",
    "viagens_lifestyle",
    "familia_maternidade",
    "consumo_varejo",
    "sustentabilidade_valores",
    "conteudo_comercial",
    "ruido_fora_escopo",
}
PILAR_TEMATICO_LABELS = {
    "moda_vestuario": "Moda e vestuário",
    "beleza_autocuidado": "Beleza e autocuidado",
    "bem_estar_fitness": "Bem-estar e fitness",
    "viagens_lifestyle": "Viagens e lifestyle",
    "familia_maternidade": "Família e maternidade",
    "consumo_varejo": "Consumo e varejo",
    "sustentabilidade_valores": "Sustentabilidade e valores",
    "conteudo_comercial": "Conteúdo comercial",
    "ruido_fora_escopo": "Ruído/fora de escopo",
}

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
Você é um(a) analista de marketing de influência avaliando, para uma marca que estuda fechar uma \
campanha paga, se os comentários abaixo indicam interesse comercial real ou só validação afetiva \
à criadora. Os comentários já passaram por um filtro local que removeu emojis soltos, elogios \
genéricos de uma palavra (ex.: "linda", "top", "diva") e spam de bot — cada um já tem algum \
conteúdo próprio. Comentário de qualidade (dúvida específica, opinião fundamentada) vale mais que \
volume: priorize sinais concretos de intenção de compra (pergunta de preço, tamanho, caimento, \
tecido, onde comprar, estoque, ou relato de quem já comprou) sobre elogio vago.

Responda APENAS com uma lista JSON, um objeto por comentário, no formato:
[{{"comentario": "<texto original>", \
"intencao_compra": "alta|media|baixa|nenhuma", \
"faixa_etaria_estimada": "<faixa etária, ex.: 18-24, 25-34, 35+>", \
"categoria_sentimento": "interesse_comercial|validacao_pessoal|duvida_critica|spam_ruido", \
"sinais_compra": ["preco"|"tamanho"|"caimento"|"tecido"|"onde_comprar"|"estoque"|"depoimento_compra", ...], \
"pilar_tematico": "moda_vestuario|beleza_autocuidado|bem_estar_fitness|viagens_lifestyle|familia_maternidade|consumo_varejo|sustentabilidade_valores|conteudo_comercial|ruido_fora_escopo"}}]

Critérios:
- intencao_compra: "alta" para pergunta objetiva de compra (preço/tamanho/onde comprar) ou "vou \
comprar"/"já comprei"; "media" para interesse real sem pergunta objetiva; "baixa" para elogio com \
contexto próprio (não genérico); "nenhuma" para o que não tem relação com intenção de compra.
- categoria_sentimento: "interesse_comercial" quando o foco é o produto/marca; \
"validacao_pessoal" quando é afeto/elogio à criadora sem foco comercial; "duvida_critica" para \
dúvida ou crítica sobre marca ou produto; "spam_ruido" quando não há relação real com o conteúdo \
mesmo tendo passado no filtro local.
- sinais_compra: liste todos os sinais concretos encontrados no comentário; use lista vazia [] \
quando não houver nenhum.
- faixa_etaria_estimada: sempre estime uma faixa plausível (ex.: "18-24", "25-34", "35+") a partir \
do estilo/vocabulário do comentário e do perfil típico da rede social — o campo é obrigatório e \
nunca deve ficar vazio; na dúvida, escolha a faixa mais provável para o contexto observado.
- pilar_tematico: classifique o território de fala do comentário em exatamente uma das opções \
listadas acima; use "ruido_fora_escopo" apenas quando nenhum outro pilar se aplicar.

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


_INDICADOR_ALTO_PCT_COMERCIAL = 0.3
_INDICADOR_MEDIO_PCT_COMERCIAL = 0.1
_ALERTA_POD_INDEX_LIMIAR = 0.3
_ALERTA_SPAM_RUIDO_LIMIAR = 0.3


def summarize_brand_suitability(items, pod_index=None):
    """Parecer agregado de aderência comercial (brand suitability), calculado
    localmente a partir da classificação por comentário já feita pelo Gemini
    (categoria_sentimento/intencao_compra) — sem nenhuma chamada extra de API,
    já que o projeto tem um teto de 2 requisições Gemini por perfil
    (RNF-03)."""
    total = len(items)
    if total == 0:
        return {
            "indicador": "sem_dados",
            "pct_interesse_comercial": 0.0,
            "pct_validacao_pessoal": 0.0,
            "pct_duvida_critica": 0.0,
            "pct_spam_ruido": 0.0,
            "comentarios_alta_intencao": 0,
            "distribuicao_intencao_compra": {nivel: 0.0 for nivel in INTENCAO_COMPRA_NIVEIS},
            "faixa_etaria_predominante": "sem_dados",
            "alertas": [],
            "resumo": "Sem comentários classificados pelo Gemini nesta janela para avaliar aderência comercial.",
        }

    contagem_sentimento = Counter(item.get("categoria_sentimento") for item in items)
    contagem_intencao = Counter(item.get("intencao_compra") for item in items)
    distribuicao_intencao_compra = {
        nivel: contagem_intencao.get(nivel, 0) / total for nivel in INTENCAO_COMPRA_NIVEIS
    }

    faixas_conhecidas = [
        item.get("faixa_etaria_estimada")
        for item in items
        if item.get("faixa_etaria_estimada") not in FAIXA_ETARIA_DESCONHECIDA_VALORES
    ]
    faixa_etaria_predominante = (
        Counter(faixas_conhecidas).most_common(1)[0][0] if faixas_conhecidas else "sem_dados"
    )

    def pct(categoria):
        return contagem_sentimento.get(categoria, 0) / total

    pct_comercial = pct("interesse_comercial")
    pct_pessoal = pct("validacao_pessoal")
    pct_duvida = pct("duvida_critica")
    pct_spam = pct("spam_ruido")
    comentarios_alta_intencao = sum(1 for item in items if item.get("intencao_compra") == "alta")

    alertas = []
    if pod_index is not None and pod_index >= _ALERTA_POD_INDEX_LIMIAR:
        alertas.append(
            f"Índice de pods elevado ({pod_index * 100:.0f}%) — parte do engajamento pode ser "
            "coordenado/artificial."
        )
    if pct_spam >= _ALERTA_SPAM_RUIDO_LIMIAR:
        alertas.append(
            f"{pct_spam * 100:.0f}% dos comentários qualificados ainda são ruído/spam mesmo "
            "após o filtro local."
        )

    if pct_comercial >= _INDICADOR_ALTO_PCT_COMERCIAL or comentarios_alta_intencao >= max(3, round(total * 0.1)):
        indicador = "alto"
    elif pct_comercial >= _INDICADOR_MEDIO_PCT_COMERCIAL or comentarios_alta_intencao > 0:
        indicador = "medio"
    else:
        indicador = "baixo"

    resumo = (
        f"{comentarios_alta_intencao} comentário(s) com intenção de compra alta; "
        f"{pct_comercial * 100:.0f}% do público qualificado com foco comercial vs. "
        f"{pct_pessoal * 100:.0f}% de validação pessoal à criadora."
    )

    return {
        "indicador": indicador,
        "pct_interesse_comercial": pct_comercial,
        "pct_validacao_pessoal": pct_pessoal,
        "pct_duvida_critica": pct_duvida,
        "pct_spam_ruido": pct_spam,
        "comentarios_alta_intencao": comentarios_alta_intencao,
        "distribuicao_intencao_compra": distribuicao_intencao_compra,
        "faixa_etaria_predominante": faixa_etaria_predominante,
        "alertas": alertas,
        "resumo": resumo,
    }


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


_INTENCAO_COMPRA_PESOS = {"nenhuma": 0, "baixa": 1, "media": 2, "alta": 3}
_QUALITATIVE_ENGAGEMENT_PESOS = {
    "interesse_comercial": 3,
    "duvida_critica": 2,
    "validacao_pessoal": 1,
    "spam_ruido": 0,
}


def calc_qualitative_engagement_rate(items):
    """Taxa de engajamento qualitativo (0-100): pondera cada comentário \
    classificado pelo Gemini por categoria_sentimento (interesse comercial e \
    dúvida/crítica pesam mais que validação pessoal ou spam), em vez de tratar \
    todo comentário qualificado como equivalente."""
    total = len(items)
    if total == 0:
        return 0.0
    pontos = sum(_QUALITATIVE_ENGAGEMENT_PESOS.get(item.get("categoria_sentimento"), 0) for item in items)
    maximo = total * max(_QUALITATIVE_ENGAGEMENT_PESOS.values())
    return (pontos / maximo) * 100 if maximo else 0.0


def calc_purchase_intent_index(items):
    """Índice de intenção de compra (0-100) — PurchaseIntentScore de \
    ISSUE-001 §5.7: média ponderada nenhuma=0/baixa=1/media=2/alta=3 sobre o \
    máximo possível."""
    total = len(items)
    if total == 0:
        return 0.0
    pontos = sum(_INTENCAO_COMPRA_PESOS.get(item.get("intencao_compra"), 0) for item in items)
    maximo = total * max(_INTENCAO_COMPRA_PESOS.values())
    return (pontos / maximo) * 100 if maximo else 0.0


def rank_top_content(posts, top_n=3):
    """Ranking dos posts mais engajados da janela coletada, ponderando \
    comentários acima de curtidas: comentário exige esforço do seguidor e é \
    sinal de interação mais forte que curtida, então ordena primeiro por \
    comments_count e usa likes_count só como critério de desempate."""
    ranked = sorted(
        posts,
        key=lambda post: ((post.get("comments_count") or 0), (post.get("likes_count") or 0)),
        reverse=True,
    )
    return ranked[:top_n]


# PostScore canônico (ISSUE-001 §5.9) — pesos definidos por quem conduz o
# produto em 13/08/2026, orientados a conversão/qualidade de influência.
POST_SCORE_WEIGHTS = {"er": 0.20, "quality": 0.30, "intent": 0.35, "sentiment": 0.15}
POST_SCORE_ER_BENCHMARK = 0.08  # ER_i satura em 1.0 ao atingir/superar 8% (ISSUE-001 §4.2)
POST_SCORE_RISK_SPAM_PESO = 0.50
POST_SCORE_RISK_POLEMICA_PESO = 0.50

# categoria_sentimento não tem valência positivo/negativo/neutro nativa (o
# schema do Gemini classifica por foco de intenção, não por sentimento —
# ISSUE-001 §5.8 pede um NSS de verdade). Em vez de acrescentar um 7º campo
# ao prompt só para o PostScore, reaproveitamos a categoria já classificada
# como proxy de valência: interesse comercial e validação pessoal contam
# como positivos, dúvida/crítica como negativo, spam/ruído fica fora do
# denominador (mesma regra do NSS canônico). Documentado aqui para não virar
# "mágica" na leitura de calc_post_score.
_SENTIMENT_VALENCE_POSITIVA = {"interesse_comercial", "validacao_pessoal"}
_SENTIMENT_VALENCE_NEGATIVA = {"duvida_critica"}


def group_items_by_post(items, qualified_comments):
    """Associa cada item classificado pelo Gemini ao post_id do comentário de
    origem, casando por texto exato — o prompt instrui o Gemini a ecoar
    'comentario' verbatim, então esse é o único vínculo disponível sem exigir
    um campo novo no schema ou uma chamada extra de API. `qualified_comments`
    é a lista de dicts (com 'texto' e 'post_id') enviada ao Gemini, na mesma
    ordem/forma usada para montar os textos do prompt.

    Comentários com texto idêntico em posts diferentes são distribuídos em
    ordem de chegada (fila por texto) — atribuição aproximada nesse caso raro,
    mas nunca inventa post_id para um item sem correspondência real."""
    filas_por_texto = {}
    for comentario in qualified_comments:
        filas_por_texto.setdefault(comentario.get("texto", ""), deque()).append(comentario.get("post_id"))

    agrupado = {}
    for item in items:
        fila = filas_por_texto.get(item.get("comentario", ""))
        if not fila:
            continue
        post_id = fila.popleft()
        agrupado.setdefault(post_id, []).append(item)
    return agrupado


def calc_post_score(post_items, likes_count=0, comments_count=0, followers_count=0):
    """PostScore_i canônico (ISSUE-001 §5.9), clampado em [0.0, 1.0]:

    PostScore_i = ER_i*0.20 + Quality_i*0.30 + Intent_i*0.35 + Sentiment_i*0.15 - RiskPenalty_i

    - ER_i: engajamento do post (likes+comments/seguidores) normalizado pelo
      benchmark de 8% (satura em 1.0).
    - Quality_i: proporção de comentários do post que não são spam/ruído.
    - Intent_i: proporção de comentários do post com algum sinal de compra
      (sinais_compra não vazio — preço, tamanho, onde comprar, estoque etc.).
    - Sentiment_i: NSS do post normalizado para [0.0, 1.0] via (NSS+1)/2.
    - RiskPenalty_i: 0.5*taxa_spam_do_post + 0.5 se houver ao menos um
      comentário 'duvida_critica' no post (proxy de menção a polêmica/risco
      de marca — não há campo dedicado no schema atual)."""
    engajamento_post = (likes_count + comments_count) / followers_count if followers_count else 0.0
    er_component = min(engajamento_post / POST_SCORE_ER_BENCHMARK, 1.0)

    total = len(post_items)
    if total == 0:
        quality_component = 0.0
        intent_component = 0.0
        sentiment_component = 0.5  # sem dados -> ponto neutro do NSS, não "muito negativo"
        risk_penalty = 0.0
    else:
        spam_share = sum(1 for item in post_items if item.get("categoria_sentimento") == "spam_ruido") / total
        quality_component = 1 - spam_share
        intent_component = sum(1 for item in post_items if item.get("sinais_compra")) / total

        positivos = sum(
            1 for item in post_items if item.get("categoria_sentimento") in _SENTIMENT_VALENCE_POSITIVA
        )
        negativos = sum(
            1 for item in post_items if item.get("categoria_sentimento") in _SENTIMENT_VALENCE_NEGATIVA
        )
        qualificados_sentimento = positivos + negativos
        nss = (positivos - negativos) / qualificados_sentimento if qualificados_sentimento else 0.0
        sentiment_component = (nss + 1) / 2

        tem_polemica = any(item.get("categoria_sentimento") == "duvida_critica" for item in post_items)
        risk_penalty = POST_SCORE_RISK_SPAM_PESO * spam_share + (
            POST_SCORE_RISK_POLEMICA_PESO if tem_polemica else 0.0
        )

    raw_score = (
        er_component * POST_SCORE_WEIGHTS["er"]
        + quality_component * POST_SCORE_WEIGHTS["quality"]
        + intent_component * POST_SCORE_WEIGHTS["intent"]
        + sentiment_component * POST_SCORE_WEIGHTS["sentiment"]
        - risk_penalty
    )
    return max(0.0, min(1.0, raw_score))


def rank_top_content_by_quality(posts, items_by_post, followers_count=0, top_n=3):
    """top3_by_quality (ISSUE-001 §5.9): ranking dos posts pelo PostScore_i
    canônico, em vez do volume bruto de comments/likes usado por rank_top_content."""
    scored = [
        {
            **post,
            "post_score": calc_post_score(
                items_by_post.get(post.get("post_id"), []),
                likes_count=post.get("likes_count") or 0,
                comments_count=post.get("comments_count") or 0,
                followers_count=followers_count,
            ),
        }
        for post in posts
    ]
    scored.sort(key=lambda post: post["post_score"], reverse=True)
    return scored[:top_n]


def top_thematic_pillars(items, top_n=3):
    """Os `top_n` territórios de fala (ISSUE-001 §5.10) mais frequentes entre \
    os comentários classificados, com contagem e participação percentual."""
    total = len(items)
    if total == 0:
        return []
    contagem = Counter(
        item.get("pilar_tematico") for item in items if item.get("pilar_tematico") in THEMATIC_PILLARS
    )
    return [
        {
            "pilar": pilar,
            "label": PILAR_TEMATICO_LABELS.get(pilar, pilar),
            "count": count,
            "pct": count / total,
        }
        for pilar, count in contagem.most_common(top_n)
    ]


def build_brand_suitability_verdict(items, pod_index=None):
    """Veredito de aderência comercial (brand suitability): reaproveita \
    summarize_brand_suitability (sem chamada extra de API) e reduz o \
    resultado a veredito + justificativa para exibição direta em painel."""
    parecer = summarize_brand_suitability(items, pod_index=pod_index)
    return {
        "veredito": ADERENCIA_INDICADOR_LABELS.get(parecer["indicador"], parecer["indicador"]),
        "justificativa": parecer["resumo"],
        "indicador": parecer["indicador"],
        "alertas": parecer["alertas"],
    }


def build_campaign_insights(items, posts=None, qualified_comments=None, followers_count=0, pod_index=None):
    """Agrega os indicadores acionáveis de campanha (ISSUE-001 §4.1/§5.9/§5.10) \
    a partir dos itens já classificados pelo Gemini e, opcionalmente, dos posts \
    da janela coletada — sem nenhuma chamada extra de API (RNF-03: teto de 2 \
    requisições Gemini por perfil).

    `qualified_comments` (dicts com 'texto'/'post_id', mesma lista enviada ao \
    Gemini) e `followers_count` são opcionais e só afetam top_3_by_quality: \
    sem eles, o PostScore_i cai para os componentes calculáveis sem contexto \
    de post (ER_i=0, listas de item por post vazias)."""
    posts = posts or []
    items_by_post = group_items_by_post(items, qualified_comments or [])
    return {
        "qualitative_engagement_rate": calc_qualitative_engagement_rate(items),
        "purchase_intent_index": calc_purchase_intent_index(items),
        "top_3_content_ranking": rank_top_content(posts, top_n=3),
        "top_3_by_quality": rank_top_content_by_quality(posts, items_by_post, followers_count=followers_count, top_n=3),
        "top_3_thematic_pillars": top_thematic_pillars(items, top_n=3),
        "brand_suitability_verdict": build_brand_suitability_verdict(items, pod_index=pod_index),
    }
