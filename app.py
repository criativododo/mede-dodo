"""métricaDODÔ — Dashboard Streamlit (ISSUE-0004).

Aplicação desktop local: audita perfis de influenciadoras do Instagram para
campanhas de marketing. 100% local, sem servidores/SDKs pagos de terceiros.

Regra inquebrável (DUMMY.md #1): a coleta/raspagem e o pipeline de análise
NUNCA rodam de forma síncrona na thread principal da UI. O botão "Analisar"
dispara `_run_pipeline` em uma `threading.Thread` de background, que escreve
progresso em um dicionário compartilhado (guardado em `st.session_state`); a
thread principal apenas faz polling/rerun para atualizar a barra de progresso,
nunca bloqueia esperando a raspagem terminar.
"""

import functools
import json
import os
import random
import re
import threading
import time
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

from src import data_loaders, database, demographics, exporter, filters, metrics, scoring, scraper
from src import rate_controller
from src.gemini_analyzer import (
    ADERENCIA_INDICADOR_LABELS,
    INTENCAO_COMPRA_NIVEIS,
    PURCHASE_SIGNAL_TYPES,
    SENTIMENT_CATEGORIES,
    THEMATIC_PILLARS,
    RealGeminiClient,
    analyze_comments,
    build_campaign_insights,
    summarize_brand_suitability,
)

BENCHMARK_ER_QUALITATIVO_MIN = 5.0
BENCHMARK_ER_QUALITATIVO_MAX = 8.0

st.set_page_config(page_title="métricaDODÔ", page_icon="📊", layout="wide")

WINDOW_OPTIONS = [30, 60, 90]

RASPAGEM_NAO_IMPLEMENTADA_MSG = (
    "Raspagem real do Instagram ainda não implementada nesta fase "
    "(dívida técnica conhecida — ver docs/issues/ISSUE-0001.md). "
    "Ative o \"Modo demonstração\" abaixo para rodar o pipeline completo "
    "com dados fictícios gerados localmente, sem rede."
)

COLETA_INDISPONIVEL_MSG = (
    "Falha na coleta do Instagram. Verifique o arquivo de sessão local ou "
    "aguarde alguns minutos antes de tentar novamente."
)

# FINDER-003 §6: mensagem mínima obrigatória quando o rate controller para a
# coleta por 429/403/challenge/checkpoint — texto vem de rate_controller para
# não duplicar a string em dois lugares.
SAFE_STOP_MSG = rate_controller.SAFETY_MESSAGE

PIPELINE_STEPS = {
    "coleta": ("Coletando/consultando cache local...", 0.10),
    "filtragem": ("Filtrando comentários rasos...", 0.30),
    "demografia": ("Inferindo demografia da audiência...", 0.50),
    "pods_score": ("Calculando índice de pods e score DODÔ...", 0.70),
    "gemini": ("Análise de intenção (Gemini, se configurado)...", 0.85),
    "relatorio": ("Montando relatório final...", 0.97),
}

# Banda de progresso reservada para a extração dinâmica (post a post) dentro
# da fase "coleta" — FINDER-003 §2.3 (banda 30-85% na tabela de referência;
# aqui usamos a banda já reservada para "coleta" nesta implementação, já que
# renomear a fase não quebra nenhuma asserção de teste existente, mas manter
# o nome reduz o diff sem necessidade).
_COLETA_BAND_START = 0.05
_COLETA_BAND_END = 0.30
_COLETA_MAX_RUNTIME_BUDGET_SECONDS = 300.0


def _compute_eta_seconds(remaining_items, mean_seconds_per_item, max_runtime_budget=_COLETA_MAX_RUNTIME_BUDGET_SECONDS):
    """FINDER-003 §2.3: T_remaining = P_remaining * D_net_mean (aqui D_net_mean
    já inclui o tempo de processamento observado por item, não é um prior fixo)."""
    if mean_seconds_per_item is None or remaining_items <= 0:
        return None
    estimated = remaining_items * mean_seconds_per_item
    return max(0.0, min(estimated, max_runtime_budget))


def _format_eta(seconds):
    seconds = max(0, int(round(seconds)))
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}min {secs}s" if secs else f"{minutes}min"


def _make_coleta_progress_callback(state):
    """Devolve um callback on_progress(processed, total) para injetar em
    scraper.instaloader_fetch_fn — atualiza state (dict puro, nunca st.*)
    com progresso real, mensagem contextual com contagem de posts e ETA
    recalculado pela média móvel observada (substitui o prior inicial assim
    que há pelo menos um item processado, FINDER-003 §2.3)."""
    start_time = time.monotonic()

    def _on_progress(processed, total):
        total = max(total, processed, 1)
        fraction = min(processed / total, 1.0)
        state["etapa"] = "coleta"
        state["progresso"] = _COLETA_BAND_START + fraction * (_COLETA_BAND_END - _COLETA_BAND_START)
        state["mensagem"] = f"Extraindo métricas recentes — post {processed}/{total}..."
        elapsed = time.monotonic() - start_time
        mean_per_item = elapsed / processed if processed else None
        state["eta_seconds"] = _compute_eta_seconds(max(total - processed, 0), mean_per_item)

    return _on_progress


DEMO_COMMENT_TEMPLATES_QUALIFIED = [
    "Qual o preço desse vestido?",
    "Vocês têm no tamanho M?",
    "Qual o prazo de entrega para SP?",
    "De que tecido é feito?",
    "Onde fica a loja física?",
    "Chega até Belo Horizonte?",
]
DEMO_COMMENT_TEMPLATES_SHALLOW = [
    "Linda",
    "Top demais",
    "😍😍😍",
    "Perfeita",
    "Arrasou",
    "Gata",
]
DEMO_FIRST_NAMES_F = ["Maria", "Ana", "Juliana", "Camila"]
DEMO_FIRST_NAMES_M = ["Joao", "Pedro", "Lucas", "Gabriel"]
DEMO_CAPTION_TEMPLATES_ORGANIC = [
    "Bom dia! Look de hoje ✨",
    "Feliz com esse ensaio 💛 sem filtro",
]
DEMO_CAPTION_TEMPLATES_SPONSORED = [
    "Parceria com @marca_fashion_demo — usem o cupom DODO10 #publi",
    "Amei esse vestido da @outra_marca_demo, super confortável #ad",
]


def _normalize_username(raw_input):
    """Aceita '@perfil', 'perfil' ou uma URL do Instagram e devolve só o username."""
    text = (raw_input or "").strip()
    match = re.search(r"instagram\.com/([A-Za-z0-9_.]+)", text)
    if match:
        return match.group(1).strip("/")
    return text.lstrip("@").strip()


def _make_demo_comment(rng, username_hint=None):
    is_qualified = rng.random() < 0.35
    texto = rng.choice(DEMO_COMMENT_TEMPLATES_QUALIFIED if is_qualified else DEMO_COMMENT_TEMPLATES_SHALLOW)
    genero = rng.choice(["F", "M"])
    nome = rng.choice(DEMO_FIRST_NAMES_F if genero == "F" else DEMO_FIRST_NAMES_M)
    username = username_hint or f"seguidor_{rng.randint(1000, 9999)}"
    respondido = is_qualified and rng.random() < 0.5
    return {"username": username, "nome": nome, "texto": texto, "respondido": respondido}


def demo_fetch_fn(username, cookies=None):
    """`fetch_fn` de demonstração: 100% determinístico (seed = username) e sem rede.

    Simula um pequeno "pod" de comentaristas (contas que repetem em vários posts)
    para que o índice de pods (RF-08) tenha algo interessante para mostrar.
    """
    rng = random.Random(f"demo-{username}")
    pod_accounts = [f"fa_fiel_{i}" for i in range(3)]
    posts = []
    for i in range(6):
        num_comments = rng.randint(8, 20)
        comments = []
        repeaters_here = pod_accounts if i % 2 == 0 else []
        for repeater in repeaters_here:
            comments.append(_make_demo_comment(rng, username_hint=repeater))
        for _ in range(max(num_comments - len(repeaters_here), 0)):
            comments.append(_make_demo_comment(rng))
        is_sponsored = i % 3 == 0
        caption = rng.choice(DEMO_CAPTION_TEMPLATES_SPONSORED if is_sponsored else DEMO_CAPTION_TEMPLATES_ORGANIC)
        shortcode = f"demo{username}{i}"
        posts.append(
            {
                "post_id": f"demo_post_{i}",
                "likes_count": rng.randint(200, 2000),
                "comments_count": len(comments),
                "raw": {"comments": comments, "caption": caption, "shortcode": shortcode},
            }
        )
    return {
        "bio": f"[DEMO] Conta fictícia de @{username} — dados gerados localmente, sem rede.",
        "followers_count": rng.randint(5000, 50000),
        "posts": posts,
    }


class _DemoGeminiResponse:
    def __init__(self, text):
        self.text = text


def _classify_demo_comment(texto):
    """Classificação determinística (seed = texto do comentário) no mesmo
    formato exigido pelo PROMPT_TEMPLATE do Gemini real — permite que
    DemoGeminiClient produza itens plausíveis sem rede nem chave de API."""
    rng = random.Random(texto)
    categoria = rng.choice(sorted(SENTIMENT_CATEGORIES))
    sinais_compra = (
        rng.sample(sorted(PURCHASE_SIGNAL_TYPES), k=rng.randint(0, 2)) if categoria != "spam_ruido" else []
    )
    return {
        "comentario": texto,
        "intencao_compra": rng.choice(INTENCAO_COMPRA_NIVEIS),
        "faixa_etaria_estimada": rng.choice(["18-24", "25-34", "35+"]),
        "categoria_sentimento": categoria,
        "sinais_compra": sinais_compra,
        "pilar_tematico": rng.choice(sorted(THEMATIC_PILLARS)),
    }


class DemoGeminiClient:
    """Client Gemini fake do Modo Demonstração — mesmo contrato duck-typed
    (generate_content -> objeto com .text) usado por RealGeminiClient, sem
    rede nem custo. Extrai os comentários do prompt (mesma formatação de
    build_batch_prompt: uma linha "- <texto>" por comentário) e devolve uma
    classificação determinística por comentário, para que a seção "Insights
    acionáveis de campanha" seja demonstrável de ponta a ponta sem
    GEMINI_API_KEY (decisão de produto de 13/08/2026)."""

    def generate_content(self, prompt):
        comentarios = [linha[2:] for linha in prompt.splitlines() if linha.startswith("- ")]
        itens = [_classify_demo_comment(texto) for texto in comentarios]
        return _DemoGeminiResponse(json.dumps(itens))


def _genero_percentuais(contagem):
    total = sum(contagem.values())
    if total == 0:
        return {"feminino": 0.0, "masculino": 0.0, "indeterminado": 0.0}
    return {chave: valor / total for chave, valor in contagem.items()}


def _genero_predominante(contagem):
    feminino = contagem.get("feminino", 0)
    masculino = contagem.get("masculino", 0)
    if feminino == 0 and masculino == 0:
        return "indeterminado"
    if feminino > masculino:
        return "feminino"
    if masculino > feminino:
        return "masculino"
    return "misto"


def _post_within_window(post, window_days):
    published_at = (post.get("raw") or {}).get("published_at")
    if not published_at:
        # Sem data real conhecida (Modo Demonstração, ou cache legado anterior a
        # esse campo) — mantém o post, não descarta por falta de informação.
        return True
    try:
        post_dt = datetime.fromisoformat(published_at)
    except ValueError:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    return post_dt >= cutoff


def _filter_posts_in_window(posts, window_days):
    """RF-02: a janela de análise (30/60/90 dias) deve refletir a data real de
    publicação dos posts no Instagram, não apenas quando foram raspados/cacheados
    (isso já é tratado à parte por database.get_cached_data)."""
    return [post for post in posts if _post_within_window(post, window_days)]


def _run_pipeline(username, window_days, demo_mode, gemini_client, state):
    """Roda em thread de background. Só mexe em `state` (dict puro), nunca em widgets `st.*`."""
    try:
        state["status"] = "rodando"
        state["etapa"] = "coleta"
        state["progresso"] = PIPELINE_STEPS["coleta"][1]

        fetch_fn = demo_fetch_fn if demo_mode else scraper.instaloader_fetch_fn
        # DUMMY.md #3 (throttling 2-5s) só faz sentido para requisições de rede reais.
        # Em modo demonstração não há nenhuma requisição a proteger, então usamos um
        # throttle_fn instantâneo; a raspagem real usa o jitter padrão de src/scraper.py.
        throttle_fn = scraper.throttle if not demo_mode else (lambda: None)
        # Caminho de um arquivo de sessão local salvo via Instaloader (login manual
        # único, fora deste código) — sem isso, a coleta real ainda tenta rodar sem
        # sessão e cai no fallback de cache/erro tratado abaixo se falhar.
        cookies = None if demo_mode else os.environ.get("INSTAGRAM_SESSION_FILE")
        if not demo_mode:
            # Pacing real por post + SafeStop em 429/403/challenge (FINDER-003 §4) —
            # nunca ligado em modo demonstração (sem rede, sem jitter, §2.2).
            fetch_fn = functools.partial(
                fetch_fn,
                rate_controller=rate_controller.RateController(),
                on_progress=_make_coleta_progress_callback(state),
            )
        try:
            cached = scraper.scrape_profile(
                username,
                window_days=window_days,
                fetch_fn=fetch_fn,
                throttle_fn=throttle_fn,
                cookies=cookies,
                source="demo" if demo_mode else "real",
            )
        except NotImplementedError:
            state["status"] = "erro_scraping_nao_implementado"
            return
        except rate_controller.SafeStop as exc:
            state["status"] = "pausado_seguranca"
            state["erro"] = str(exc)
            return
        except scraper.ScraperUnavailableError as exc:
            state["status"] = "erro_coleta_indisponivel"
            state["erro"] = str(exc)
            return

        posts = _filter_posts_in_window(cached.get("posts", []), window_days)
        followers_count = cached.get("profile", {}).get("followers_count") or 0

        state["etapa"] = "filtragem"
        state["progresso"] = PIPELINE_STEPS["filtragem"][1]

        all_comments_flat = []
        metrics_posts = []
        engagement_posts = []
        content_posts = []
        for post in posts:
            raw_comments = (post.get("raw") or {}).get("comments", [])
            metrics_posts.append(
                {"post_id": post.get("post_id"), "commenters": [c.get("username") for c in raw_comments]}
            )
            engagement_posts.append(
                {"likes_count": post.get("likes_count") or 0, "comments_count": post.get("comments_count") or 0}
            )
            content_posts.append(
                {
                    "post_id": post.get("post_id"),
                    "likes_count": post.get("likes_count") or 0,
                    "comments_count": post.get("comments_count") or 0,
                    "link": (post.get("raw") or {}).get("shortcode"),
                    "caption": (post.get("raw") or {}).get("caption"),
                }
            )
            # post_id vai junto de cada comentário (não muda nenhum uso existente
            # de all_comments_flat) para permitir, mais adiante, recompor qual
            # comentário classificado pelo Gemini pertence a qual post — sem isso
            # o PostScore_i canônico (ISSUE-001 §5.9) não teria como calcular
            # componentes por post, já que a classificação roda sobre o pool
            # global de comentários qualificados do perfil.
            all_comments_flat.extend({**c, "post_id": post.get("post_id")} for c in raw_comments)

        qualified_comments = [c for c in all_comments_flat if not filters.is_shallow_comment(c.get("texto", ""))]
        total_comentarios = len(all_comments_flat)
        publis_detectadas = filters.detect_sponsored_posts(posts)

        state["etapa"] = "demografia"
        state["progresso"] = PIPELINE_STEPS["demografia"][1]

        names_db = data_loaders.load_names_db()
        ddd_to_uf = data_loaders.load_ddd_to_uf()

        genero_contagem = {"feminino": 0, "masculino": 0, "indeterminado": 0}
        regiao_detections = []
        for c in all_comments_flat:
            # Comentários com 'nome' explícito (ex.: Modo Demonstração) usam o
            # nome direto; comentários reais (instaloader_fetch_fn) só trazem
            # 'username' — tenta cada segmento alfabético do @handle contra a
            # base IBGE até achar um nome conhecido (prefixos genéricos como
            # 'style_by_', 'its_', 'eu_' não devem virar indeterminado só por
            # aparecerem antes do nome real).
            nome_explicito = c.get("nome")
            if nome_explicito:
                genero = demographics.infer_gender(nome_explicito, names_db=names_db)
            else:
                genero = demographics.infer_gender_from_handle(c.get("username"), names_db=names_db)
            genero_contagem[genero] = genero_contagem.get(genero, 0) + 1

            regiao_result = demographics.infer_region(c.get("texto", ""), ddd_to_uf=ddd_to_uf)
            ufs_no_comentario = []
            for uf in regiao_result["por_ddd"] + regiao_result["por_mencao"]:
                if uf not in ufs_no_comentario:
                    ufs_no_comentario.append(uf)
            regiao_detections.extend(ufs_no_comentario)

        regioes = demographics.format_region_distribution(
            demographics.summarize_region_distribution(regiao_detections)
        )

        state["etapa"] = "pods_score"
        state["progresso"] = PIPELINE_STEPS["pods_score"][1]

        pod_result = metrics.calc_pod_index(metrics_posts)
        engagement_rate = scoring.calc_engagement_rate(engagement_posts, followers_count)
        average_engagement = metrics.calc_average_engagement(engagement_posts)
        fake_followers_estimate = metrics.estimate_fake_followers_risk(
            engagement_rate, followers_count, pod_result["pod_index"]
        )
        qualified_ratio = (len(qualified_comments) / total_comentarios) if total_comentarios else 0.0
        response_rate = (
            sum(1 for c in all_comments_flat if c.get("respondido")) / total_comentarios
        ) if total_comentarios else 0.0
        score_dodo = scoring.calc_dodo_score(
            engagement_rate,
            qualified_ratio,
            response_rate,
            pod_result["pod_index"],
            followers_count=followers_count,
        )

        state["etapa"] = "gemini"
        state["progresso"] = PIPELINE_STEPS["gemini"][1]

        # DUMMY.md #2: só comentários já filtrados localmente (qualified) vão ao Gemini.
        if gemini_client is not None:
            qualified_texts = [c.get("texto", "") for c in qualified_comments]
            gemini_result = analyze_comments(qualified_texts, gemini_client)
            gemini_items = gemini_result["items"]
            parecer_comercial = summarize_brand_suitability(gemini_items, pod_index=pod_result["pod_index"])
            campaign_insights = build_campaign_insights(
                gemini_items,
                posts=content_posts,
                qualified_comments=qualified_comments,
                followers_count=followers_count,
                pod_index=pod_result["pod_index"],
            )
        else:
            gemini_items = []
            parecer_comercial = None
            campaign_insights = None

        state["etapa"] = "relatorio"
        state["progresso"] = PIPELINE_STEPS["relatorio"][1]

        analysis = {
            "username": username,
            "window_days": window_days,
            "score_dodo": score_dodo,
            "engagement_rate": engagement_rate,
            "followers_count": followers_count,
            "average_likes": average_engagement["average_likes"],
            "average_comments": average_engagement["average_comments"],
            "fake_followers_estimate": fake_followers_estimate,
            "demografia": {
                "genero_predominante": _genero_predominante(genero_contagem),
                "genero_pct": _genero_percentuais(genero_contagem),
                "regioes": regioes,
            },
            "antifraude": {
                "pod_index": pod_result["pod_index"],
                "top_repetidores": pod_result["top_repetidores"],
                "taxa_resposta_criadora": response_rate,
            },
            "publis": publis_detectadas,
            "comentarios_analisados": {
                "total": total_comentarios,
                "qualificados": len(qualified_comments),
                "gemini_items": gemini_items,
                "parecer_comercial": parecer_comercial,
            },
            "campaign_insights": campaign_insights,
        }

        state["analysis"] = analysis
        state["demo_mode"] = demo_mode
        state["gemini_configurado"] = gemini_client is not None
        state["status"] = "concluido"
        state["progresso"] = 1.0
    except Exception as exc:  # nunca deixa a thread morrer silenciosamente
        state["status"] = "erro"
        state["erro"] = str(exc)


def _init_state():
    if "pipeline_state" not in st.session_state:
        st.session_state.pipeline_state = {"status": "ocioso"}
    if "pipeline_thread" not in st.session_state:
        st.session_state.pipeline_thread = None
    if "mostrar_relatorio" not in st.session_state:
        st.session_state.mostrar_relatorio = False


def _render_metric_cards(analysis):
    # Ordem alinhada ao catálogo P0 do benchmark da concorrência
    # (SPRINT-002/BENCHMARK-001.md §4.1/§13): leva com os números observados/
    # derivados do perfil (seguidores, engajamento, seguidores potencialmente
    # inautênticos, curtidas/comentários médios) antes de qualquer score
    # proprietário — o benchmark é explícito que abrir com um "score de
    # influenciador" opaco e só depois explicar os componentes é o maior erro
    # a evitar (BENCHMARK-001.md §13).
    col1, col2, col3 = st.columns(3)
    col1.metric("Seguidores", f"{analysis['followers_count']:,}".replace(",", "."))
    col2.metric("Taxa de engajamento", f"{analysis['engagement_rate'] * 100:.2f}%")
    col2.caption(
        "Referência de mercado (nano/micro-influenciadoras de moda e lifestyle): "
        "engajamento saudável costuma ficar entre ~1,2% e 5%, dependendo do porte do perfil."
    )
    fake_estimate = analysis["fake_followers_estimate"]
    col3.metric("Seguidores potencialmente inautênticos (estimativa)", f"{fake_estimate['value']:.1f}%")
    col3.caption(
        "Estimativa heurística local (confiança: "
        f"{fake_estimate['confidence']}), não equivalente a detectores comerciais "
        "(Modash/HypeAuditor). Método: déficit de engajamento vs. benchmark do porte + índice de pods."
    )

    col4, col5 = st.columns(2)
    col4.metric("Curtidas médias por post", f"{analysis['average_likes']:.0f}")
    col5.metric("Comentários médios por post", f"{analysis['average_comments']:.0f}")

    col6, col7, col8, col9 = st.columns(4)
    col6.metric("Score DODÔ (0-10)", f"{analysis['score_dodo']:.2f}")
    col7.metric("Índice de pods", f"{analysis['antifraude']['pod_index'] * 100:.1f}%")
    col8.metric("Taxa de resposta da criadora", f"{analysis['antifraude']['taxa_resposta_criadora'] * 100:.1f}%")
    comentarios = analysis["comentarios_analisados"]
    total_comentarios = comentarios["total"]
    taxa_qualificados = (comentarios["qualificados"] / total_comentarios) if total_comentarios else 0.0
    col9.metric("Taxa de comentários qualificados", f"{taxa_qualificados * 100:.1f}%")
    col9.caption("Comentários com conteúdo próprio, descontados emojis soltos, elogio genérico e spam/bot.")


def _render_demografia_card(analysis):
    st.subheader("Demografia da audiência")
    demografia = analysis["demografia"]
    pct_feminino = demografia.get("genero_pct", {}).get("feminino", 0.0) * 100
    st.write(
        f"**Gênero predominante:** {demografia['genero_predominante']} "
        f"({pct_feminino:.1f}% feminino na amostra)"
    )
    regioes = demografia["regioes"]
    st.write(f"**Regiões detectadas:** {', '.join(regioes) if regioes else 'Nenhuma região detectada'}")


def _render_antifraude_card(analysis):
    st.subheader("Antifraude — possíveis pods")
    top_repetidores = analysis["antifraude"]["top_repetidores"]
    if top_repetidores:
        st.table(
            [{"conta": user, "comentários": count} for user, count in top_repetidores.items()]
        )
    else:
        st.caption("Nenhum repetidor relevante identificado.")


def _render_publis_card(analysis):
    st.subheader("Publis")
    publis = analysis.get("publis", [])
    if not publis:
        st.caption(exporter.PUBLIS_VAZIO_MSG)
        return
    st.table(
        [
            {
                "post": item.get("link") or item.get("post_id"),
                "indícios": ", ".join(item.get("termos", [])),
                "marca(s)": ", ".join(item.get("marcas", [])) or "—",
            }
            for item in publis
        ]
    )


def _render_parecer_comercial(parecer):
    label = ADERENCIA_INDICADOR_LABELS.get(parecer["indicador"], parecer["indicador"])
    st.markdown(f"**Parecer de aderência comercial (brand suitability):** {label}")
    st.write(parecer["resumo"])
    for alerta in parecer.get("alertas", []):
        st.warning(alerta)


INTENCAO_COMPRA_LABELS = {"alta": "Alta", "media": "Média", "baixa": "Baixa", "nenhuma": "Nenhuma"}

SENTIMENTO_LABELS = {
    "pct_interesse_comercial": "Interesse comercial",
    "pct_validacao_pessoal": "Validação pessoal",
    "pct_duvida_critica": "Dúvida/crítica",
    "pct_spam_ruido": "Spam/ruído",
}


def _render_intencao_compra_card(parecer):
    distribuicao = parecer.get("distribuicao_intencao_compra") or {}
    if not distribuicao:
        return
    st.markdown("**Distribuição de intenção de compra**")
    st.table(
        [
            {"Nível": INTENCAO_COMPRA_LABELS.get(nivel, nivel), "% dos comentários": f"{pct * 100:.1f}%"}
            for nivel, pct in distribuicao.items()
        ]
    )


def _render_sentimento_card(parecer):
    st.markdown("**Sentimento dos comentários (comercial x afetivo x crítica)**")
    st.table(
        [
            {"Categoria": label, "% dos comentários": f"{parecer.get(campo, 0.0) * 100:.1f}%"}
            for campo, label in SENTIMENTO_LABELS.items()
        ]
    )


def _render_faixa_etaria_card(parecer):
    faixa = parecer.get("faixa_etaria_predominante")
    if not faixa or faixa == "sem_dados":
        st.caption("Faixa etária predominante: sem dados suficientes para estimar.")
        return
    st.markdown(f"**Faixa etária predominante da audiência:** {faixa}")


def _render_comentarios_card(analysis, gemini_configurado):
    st.subheader("Comentários analisados")
    comentarios = analysis["comentarios_analisados"]
    st.write(f"Total coletado: **{comentarios['total']}** — Qualificados (não rasos): **{comentarios['qualificados']}**")
    if not gemini_configurado:
        st.caption(exporter.GEMINI_NAO_CONFIGURADO_MSG)
        return
    parecer = comentarios.get("parecer_comercial")
    if parecer:
        _render_parecer_comercial(parecer)
        _render_intencao_compra_card(parecer)
        _render_sentimento_card(parecer)
        _render_faixa_etaria_card(parecer)
    if comentarios["gemini_items"]:
        st.dataframe(comentarios["gemini_items"], width="stretch")


def _render_campaign_insights_metric_cards(campaign_insights):
    st.subheader("Insights acionáveis de campanha")
    col1, col2 = st.columns(2)
    col1.metric(
        "Taxa de engajamento qualitativo",
        f"{campaign_insights['qualitative_engagement_rate']:.1f}%",
    )
    col1.caption(
        f"Benchmark editorial nano/micro: ~{BENCHMARK_ER_QUALITATIVO_MIN:.0f}%–"
        f"{BENCHMARK_ER_QUALITATIVO_MAX:.0f}% (ISSUE-001 §4.2). Pondera comentários por "
        "categoria de sentimento, não é a taxa de engajamento bruta."
    )
    col2.metric("Índice de intenção de compra", f"{campaign_insights['purchase_intent_index']:.1f}%")
    col2.caption("Média ponderada da intenção de compra classificada pelo Gemini nos comentários qualificados.")


def _render_top_content_card(campaign_insights):
    st.markdown("**Top 3 por alcance/volume**")
    top_content = campaign_insights.get("top_3_content_ranking") or []
    if not top_content:
        st.caption("Sem posts na janela selecionada para ranquear.")
        return
    st.table(
        [
            {
                "post": item.get("link") or item.get("post_id"),
                "comentários": item.get("comments_count", 0),
                "curtidas": item.get("likes_count", 0),
            }
            for item in top_content
        ]
    )


def _render_top_content_by_quality_card(campaign_insights):
    st.markdown("**Top 3 por qualidade/conversão**")
    st.caption("Ranqueado pelo PostScore_i canônico (ISSUE-001 §5.9): engajamento, qualidade do comentário, intenção de compra e sentimento, descontado risco de marca.")
    top_quality = campaign_insights.get("top_3_by_quality") or []
    if not top_quality:
        st.caption("Sem posts na janela selecionada para ranquear.")
        return
    st.table(
        [
            {
                "post": item.get("link") or item.get("post_id"),
                "PostScore": f"{item.get('post_score', 0.0):.2f}",
                "comentários": item.get("comments_count", 0),
                "curtidas": item.get("likes_count", 0),
            }
            for item in top_quality
        ]
    )


def _render_top_pilares_card(campaign_insights):
    st.markdown("**Top 3 pilares temáticos**")
    top_pilares = campaign_insights.get("top_3_thematic_pillars") or []
    if not top_pilares:
        st.caption("Sem pilares temáticos suficientes para ranquear nesta janela.")
        return
    st.table(
        [
            {"pilar": item["label"], "comentários": item["count"], "% dos comentários": f"{item['pct'] * 100:.1f}%"}
            for item in top_pilares
        ]
    )


def _render_brand_suitability_panel(campaign_insights):
    st.markdown("**Brand suitability**")
    veredito = campaign_insights.get("brand_suitability_verdict") or {}
    st.write(f"**Veredito:** {veredito.get('veredito', 'Sem dados suficientes para avaliar')}")
    if veredito.get("justificativa"):
        st.write(veredito["justificativa"])
    for alerta in veredito.get("alertas", []):
        st.warning(alerta)


def _render_campaign_insights_section(analysis, gemini_configurado):
    campaign_insights = analysis.get("campaign_insights")
    if not gemini_configurado or not campaign_insights:
        return
    _render_campaign_insights_metric_cards(campaign_insights)
    col_left, col_right = st.columns(2)
    with col_left:
        _render_top_content_card(campaign_insights)
        _render_top_content_by_quality_card(campaign_insights)
        _render_brand_suitability_panel(campaign_insights)
    with col_right:
        _render_top_pilares_card(campaign_insights)


def _render_export_buttons(analysis):
    st.subheader("Exportar relatório")
    html_report = exporter.generate_html_report(analysis)
    pdf_report = exporter.generate_pdf_report(analysis)
    col1, col2 = st.columns(2)
    col1.download_button(
        "Baixar relatório (HTML)",
        data=html_report,
        file_name=f"relatorio_{analysis['username']}.html",
        mime="text/html",
        key="download_html_button",
    )
    col2.download_button(
        "Baixar relatório (PDF)",
        data=pdf_report,
        file_name=f"relatorio_{analysis['username']}.pdf",
        mime="application/pdf",
        key="download_pdf_button",
    )


def _start_pipeline_thread(username, window_days, demo_mode):
    if demo_mode:
        # Modo Demonstração simula o Gemini localmente (DemoGeminiClient) para
        # que a seção "Insights acionáveis de campanha" seja demonstrável de
        # ponta a ponta sem GEMINI_API_KEY nem qualquer chamada de rede.
        gemini_client = DemoGeminiClient()
    else:
        gemini_client = None
        try:
            gemini_client = RealGeminiClient()
        except RuntimeError:
            # GEMINI_API_KEY ausente: segue sem Gemini, tratado graciosamente
            # na UI via GEMINI_NAO_CONFIGURADO_MSG — nunca derruba o pipeline.
            gemini_client = None
    st.session_state.pipeline_state = {"status": "rodando", "etapa": "coleta", "progresso": 0.0}
    st.session_state.mostrar_relatorio = False
    thread = threading.Thread(
        target=_run_pipeline,
        args=(username, window_days, demo_mode, gemini_client, st.session_state.pipeline_state),
        daemon=True,
    )
    st.session_state.pipeline_thread = thread
    thread.start()
    st.rerun()


def _render_session_status_sidebar():
    session_username = scraper.detect_available_session_username()
    with st.sidebar:
        st.subheader("Sessão do Instagram")
        if session_username:
            st.success(f"Sessão ativa: {session_username}")
        else:
            st.warning(
                "Nenhum arquivo de sessão detectado em "
                f"{scraper.SESSION_DIR}{os.sep}{scraper.SESSION_FILE_PREFIX}<usuario>. "
                "Faça login uma vez via `instaloader -l <usuario>` para coletar "
                "perfis reais (fora do Modo demonstração)."
            )


def main():
    _init_state()

    st.title("métricaDODÔ")
    st.caption("Auditoria local de perfis do Instagram para campanhas de marketing — custo zero, 100% offline.")
    _render_session_status_sidebar()

    with st.form("form_analise", clear_on_submit=False):
        username_input = st.text_input(
            "Perfil do Instagram (@perfil ou URL)",
            key="username_input",
            placeholder="@perfil ou https://instagram.com/perfil",
        )
        window_days = st.selectbox(
            "Janela de análise (dias)",
            options=WINDOW_OPTIONS,
            index=WINDOW_OPTIONS.index(90),
            key="window_days_select",
        )
        demo_mode = st.toggle(
            "Modo demonstração (dados fictícios gerados localmente, sem raspagem real)",
            key="demo_mode_toggle",
            value=False,
        )
        pipeline_running = st.session_state.pipeline_state.get("status") == "rodando"
        col_analisar, col_limpar = st.columns(2)
        analisar_clicked = col_analisar.form_submit_button("Analisar", disabled=pipeline_running)
        limpar_cache_clicked = col_limpar.form_submit_button(
            "Limpar Cache e Re-analisar Perfil", disabled=pipeline_running
        )

    if analisar_clicked or limpar_cache_clicked:
        username = _normalize_username(username_input)
        if not username:
            st.warning("Informe um @perfil ou URL do Instagram válido antes de analisar.")
        else:
            if limpar_cache_clicked:
                database.clear_profile_cache(username)
            _start_pipeline_thread(username, window_days, demo_mode)

    state = st.session_state.pipeline_state
    status = state.get("status", "ocioso")

    if status == "rodando":
        etapa = state.get("etapa", "coleta")
        texto_etapa_padrao, progresso_padrao = PIPELINE_STEPS.get(etapa, ("Processando...", 0.0))
        texto_etapa = state.get("mensagem") or texto_etapa_padrao
        progresso = state.get("progresso", progresso_padrao)
        eta_seconds = state.get("eta_seconds")
        label = f"{texto_etapa} (~{_format_eta(eta_seconds)} restantes)" if eta_seconds is not None else texto_etapa
        st.progress(progresso, text=label)
        time.sleep(0.3)
        st.rerun()
    elif status == "pausado_seguranca":
        st.warning(state.get("erro", SAFE_STOP_MSG))
    elif status == "erro_scraping_nao_implementado":
        st.warning(RASPAGEM_NAO_IMPLEMENTADA_MSG)
    elif status == "erro_coleta_indisponivel":
        st.error(COLETA_INDISPONIVEL_MSG)
        st.caption(f"Detalhe técnico: {state.get('erro', 'erro desconhecido')}")
    elif status == "erro":
        st.error(f"Falha ao processar o pipeline: {state.get('erro', 'erro desconhecido')}")
    elif status == "concluido":
        analysis = state["analysis"]
        if state.get("demo_mode"):
            st.info("Resultado gerado em MODO DEMONSTRAÇÃO — dados fictícios, apenas para validar o pipeline fim-a-fim.")
        _render_metric_cards(analysis)
        _render_campaign_insights_section(analysis, state.get("gemini_configurado", False))
        col_left, col_right = st.columns(2)
        with col_left:
            _render_demografia_card(analysis)
            _render_publis_card(analysis)
        with col_right:
            _render_antifraude_card(analysis)
            _render_comentarios_card(analysis, state.get("gemini_configurado", False))

        if not st.session_state.mostrar_relatorio:
            st.success("Relatório pronto! Clique abaixo para liberar a exportação em HTML/PDF/JSON.")
            if st.button("Ver Relatório"):
                st.session_state.mostrar_relatorio = True
                st.rerun()
        else:
            _render_export_buttons(analysis)
            if st.button("Gerar novo relatório"):
                # Limpa só o estado da tela, nunca o cache global (FINDER-003 §2.4) —
                # quem quiser limpar o cache usa o botão "Limpar Cache e Re-analisar
                # Perfil" no formulário, de forma explícita.
                st.session_state.pipeline_state = {"status": "ocioso"}
                st.session_state.mostrar_relatorio = False
                st.rerun()


main()
