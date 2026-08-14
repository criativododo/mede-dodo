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
import html
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

# Design System Criativo Dodô (SPRINT-002/SPEC-001.md §8) — tokens canônicos.
# Não inventar hex/fonte/raio/sombra novos: só os valores abaixo.
DS_CREME_CANNOLI = "#EDEBDD"
DS_BRANCO_BRILHANTE = "#F5F4EC"
DS_ONIX = "#1B1717"
DS_VERMELHO_HAUTE = "#810100"
DS_DALIA_VERMELHA = "#630000"
DS_CINZA_ESPUMA = "#E4D8CB"
DS_SOMBRA_NEUTRA = "0 10px 24px rgba(27,23,23,.07)"


def _inject_design_system_css():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {DS_CREME_CANNOLI};
        }}
        .stApp, .stApp p, .stApp span, .stApp label {{
            color: {DS_ONIX};
        }}
        [data-testid="stVerticalBlockBorderWrapper"] {{
            background-color: {DS_BRANCO_BRILHANTE};
            border-radius: 8px;
            box-shadow: {DS_SOMBRA_NEUTRA};
        }}
        [data-testid="stExpander"] summary {{
            background-color: {DS_BRANCO_BRILHANTE};
            border-radius: 8px;
        }}
        .stButton button, .stFormSubmitButton button, .stDownloadButton button {{
            background-color: {DS_VERMELHO_HAUTE} !important;
            color: {DS_CREME_CANNOLI} !important;
            border-radius: 999px !important;
            border: 1px solid {DS_VERMELHO_HAUTE} !important;
            height: 48px;
            font-weight: 700;
        }}
        .stButton button:hover, .stFormSubmitButton button:hover, .stDownloadButton button:hover {{
            background-color: {DS_BRANCO_BRILHANTE} !important;
            color: {DS_VERMELHO_HAUTE} !important;
        }}
        .stButton button:focus-visible, .stFormSubmitButton button:focus-visible {{
            outline: 2px solid {DS_VERMELHO_HAUTE} !important;
        }}
        .dodo-decision-card {{
            background-color: {DS_BRANCO_BRILHANTE};
            border-left: 6px solid {DS_VERMELHO_HAUTE};
            border-radius: 8px;
            padding: 20px 24px;
            margin-bottom: 16px;
        }}
        .dodo-badge {{
            display: inline-block;
            font-family: "IBM Plex Mono", monospace;
            font-size: 12px;
            padding: 1px 8px;
            border-radius: 999px;
            background-color: {DS_CINZA_ESPUMA};
            color: {DS_ONIX};
        }}
        .dodo-badge-estimado {{
            background-color: {DS_DALIA_VERMELHA};
            color: {DS_CREME_CANNOLI};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


_BADGE_LABELS = {
    "observed": "observado",
    "derived": "derivado",
    "estimated": "estimado",
    "model_output": "modelo",
    "unavailable": "indisponível",
    "partial": "parcial",
    "warning": "revisar",
    None: "—",
}


def _badge_caption(kind, extra=""):
    """Legenda textual de procedência (observado/derivado/estimado/...) — usada
    como st.caption() logo abaixo de cada KPI, já que st.metric não aceita
    markup HTML no valor. Formato: `` `<badge>` — <extra> ``."""
    label = _BADGE_LABELS.get(kind, kind or "—")
    return f"`{label}`" + (f" — {extra}" if extra else "")


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
    "Bom dia! Look de hoje ✨ #lookdodia #moda",
    "Feliz com esse ensaio 💛 sem filtro #tendencia",
    "Sextou com esse conjunto novo, amei a produção com @estudioela 📸 #moda #lookdodia",
    "Inspiração de look pra essa semana #tendencia #moda #lookdodia",
]
DEMO_CAPTION_TEMPLATES_SPONSORED = [
    "Parceria com @marca_fashion_demo — usem o cupom DODO10 #publi #moda",
    "Amei esse vestido da @outra_marca_demo, super confortável #ad #lookdodia",
    "Nova coleção em parceria com @marca_parceira, glow total #publi #tendencia",
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
        # Alterna os 3 formatos do benchmark (BENCHMARK-001.md §4.2) para que o
        # Modo Demonstração exercite engagement_rate_by_views (Reels) fim a fim,
        # sem depender de credenciais reais: 2 Reels em cada janela de 6 posts.
        media_type = ("CAROUSEL", "REEL", "IMAGE")[i % 3]
        is_video = media_type == "REEL"
        posts.append(
            {
                "post_id": f"demo_post_{i}",
                "likes_count": rng.randint(200, 2000),
                "comments_count": len(comments),
                "raw": {
                    "comments": comments,
                    "caption": caption,
                    "shortcode": shortcode,
                    "media_type": media_type,
                    "is_video": is_video,
                    "video_view_count": rng.randint(3000, 20000) if is_video else None,
                },
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
        # Sprint 002 SPEC-001 §6.1: cabeçalho do perfil exibe a data de coleta —
        # campo puramente aditivo/apresentacional, lido do cache já existente
        # (database.profiles.updated_at), sem alterar nenhuma heurística de coleta.
        data_coleta = cached.get("profile", {}).get("updated_at")

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
        # Contrato canônico de auditoria (Sprint 002 §6/§7, ISSUE-001.md §6.2) —
        # aditivo: usa os `posts` originais (com `raw.is_video`/`raw.video_view_count`
        # já populados por scraper.instaloader_fetch_fn/demo_fetch_fn), não os
        # `engagement_posts` simplificados de cima. Não substitui `engagement_rate`
        # (float legado consumido por app.py/src/exporter.py).
        audit_report = metrics.build_audit_report(posts, followers_count, names_db=names_db, ddd_to_uf=ddd_to_uf)
        database.save_audit_report(username, audit_report)
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
            "audit_report": audit_report,
            "data_coleta": data_coleta,
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


def _classify_perfil_porte(followers_count):
    """Classificação apresentacional de porte para o cabeçalho do perfil
    (SPEC-001 §6.1) — não é uma heurística de coleta/score, só um agrupamento
    de exibição sobre `followers_count`, que já existe em `analysis`."""
    if not followers_count:
        return "Porte indeterminado"
    if followers_count < 10_000:
        return "Nano-influenciadora"
    if followers_count < 100_000:
        return "Micro-influenciadora"
    if followers_count < 500_000:
        return "Influenciadora de médio porte"
    return "Macro-influenciadora"


def _format_data_coleta(iso_value):
    if not iso_value:
        return "indisponível"
    try:
        parsed = datetime.fromisoformat(iso_value)
    except ValueError:
        return "indisponível"
    return parsed.strftime("%d/%m/%Y %H:%M")


def _render_profile_header(analysis, state):
    """SPEC-001 §6.1: handle e identidade primeiro, nenhum número bruto antes
    dela; porte e janela ao lado; data de coleta e modo no rodapé."""
    username = analysis.get("username", "")
    porte = _classify_perfil_porte(analysis.get("followers_count"))
    window_days = analysis.get("window_days", "N/D")
    data_coleta = _format_data_coleta(analysis.get("data_coleta"))
    modo_label = "Demonstração" if state.get("demo_mode") else "Real"

    col_identidade, col_porte = st.columns([1.35, 1], gap="large")
    with col_identidade:
        st.markdown(f"### @{username}")
    with col_porte:
        st.write(f"**{porte}** · janela de {window_days} dias")
    st.caption(f"Coletado em {data_coleta} · Modo {modo_label}")


_LEITURA_CONTRATACAO_DISCLAIMER = (
    "Estimativas e alertas exigem revisão humana antes de qualquer decisão de contratação."
)


def _render_decision_summary(analysis, gemini_configurado):
    """SPEC-001 §6.2: Score DODÔ, parecer de adequação comercial, resumo e
    até três sinais de suporte, numa faixa Branco Brilhante com acento
    Vermelho Haute. Nunca sugere aprovação automática (UI-10)."""
    score = analysis.get("score_dodo")
    parecer = (analysis.get("comentarios_analisados") or {}).get("parecer_comercial")

    st.markdown('<div class="dodo-decision-card">', unsafe_allow_html=True)
    st.subheader("Leitura para contratação")
    st.metric(
        "Score DODÔ",
        f"{score:.2f}" if score is not None else "N/D",
        help=(
            "Índice de 0 a 10 que combina engajamento, qualidade de comentários, "
            "resposta da criadora e sinal de interação coordenada. Fórmula completa "
            "em Detalhes da auditoria."
        ),
    )
    st.caption(_badge_caption("derived"))
    if gemini_configurado and parecer:
        label = ADERENCIA_INDICADOR_LABELS.get(parecer["indicador"], parecer["indicador"])
        st.markdown(f"**Parecer de adequação comercial:** {label}")
        st.write(parecer.get("resumo", ""))
        for sinal in (parecer.get("alertas") or [])[:3]:
            st.markdown(f"- {sinal}")
    else:
        st.caption(exporter.GEMINI_NAO_CONFIGURADO_MSG)
    st.caption(_LEITURA_CONTRATACAO_DISCLAIMER)
    st.markdown("</div>", unsafe_allow_html=True)


_MICROCOPY_ENGAJAMENTO_SEGUIDORES = (
    "Interações médias por conteúdo divididas pelo número de seguidores. É um sinal "
    "comparável entre perfis, não uma garantia de conversão."
)
_MICROCOPY_AUTENTICIDADE_AUDIENCIA = (
    "Estimativa heurística baseada nos sinais observados nesta amostra. Não equivale a "
    "uma auditoria comercial externa e não deve ser lida como prova isolada."
)
_MICROCOPY_RESPOSTAS_CRIADORA = (
    "Percentual de comentários da amostra que receberam resposta da autora no período analisado."
)


def _render_primary_kpis(analysis):
    """SPEC-001 §6.3/§11 UI-01/UI-03: só os 4 KPIs de decisão, em grade 2x2 —
    nunca st.columns(3)/st.columns(4) nesta faixa. Curtidas/comentários
    médios, pods e comentários qualificados saem daqui (vão para Detalhes da
    auditoria / Qualidade da audiência / Comentários e intenção)."""
    st.subheader("KPIs principais")
    audit_metrics = (analysis.get("audit_report") or {}).get("metrics") or {}

    linha1_col1, linha1_col2 = st.columns(2, gap="large")
    with linha1_col1:
        st.metric("Seguidores", f"{analysis.get('followers_count', 0):,}".replace(",", "."))
        st.caption(_badge_caption("observed"))
    with linha1_col2:
        st.metric(
            "Engajamento por seguidores",
            f"{analysis.get('engagement_rate', 0.0) * 100:.2f}%",
            help=_MICROCOPY_ENGAJAMENTO_SEGUIDORES,
        )
        st.caption(_badge_caption("derived", "denominador: seguidores"))

    linha2_col1, linha2_col2 = st.columns(2, gap="large")
    with linha2_col1:
        autenticidade = audit_metrics.get("audience_authenticity_signal") or {}
        if autenticidade.get("status") == "ok":
            valor = f"{autenticidade['value']:.1f}%"
            confianca = autenticidade.get("confidence") or "N/D"
        else:
            fallback = analysis.get("fake_followers_estimate") or {}
            valor = f"{fallback['value']:.1f}%" if fallback.get("value") is not None else "indisponível"
            confianca = fallback.get("confidence", "N/D")
        st.metric("Autenticidade da audiência (estimativa)", valor, help=_MICROCOPY_AUTENTICIDADE_AUDIENCIA)
        st.caption(_badge_caption("estimated", f"confiança: {confianca}"))
    with linha2_col2:
        creator_response = audit_metrics.get("creator_response_rate") or {}
        if creator_response.get("status") == "ok":
            valor = f"{creator_response['value']:.1f}%"
            cobertura = f"{creator_response.get('total_count', 0)} comentário(s) avaliados"
        else:
            taxa = (analysis.get("antifraude") or {}).get("taxa_resposta_criadora", 0.0)
            valor = f"{taxa * 100:.1f}%"
            cobertura = "cobertura amostral indisponível"
        st.metric("Respostas da criadora", valor, help=_MICROCOPY_RESPOSTAS_CRIADORA)
        st.caption(_badge_caption("derived", cobertura))


_MICROCOPY_ENGAJAMENTO_VIEWS = (
    "Calculado somente para Reels com visualizações disponíveis. Quando a plataforma não "
    "fornece views, o resultado aparece como indisponível."
)


def _render_format_performance(analysis):
    """SPEC-001 §6.4: compara estático x Reels; card de views nunca mostra
    '0,00%' quando não há Reels na amostra — mostra o estado indisponível."""
    st.subheader("Formatos e Reels")
    audit_metrics = (analysis.get("audit_report") or {}).get("metrics") or {}
    by_followers = audit_metrics.get("engagement_rate_by_followers") or {}
    by_views = audit_metrics.get("engagement_rate_by_views") or {}

    col_geral, col_reels = st.columns(2, gap="large")
    with col_geral:
        if by_followers.get("status") == "ok":
            st.metric("Engajamento — todos os formatos (por seguidores)", f"{by_followers['value']:.2f}%")
        else:
            st.metric("Engajamento — todos os formatos (por seguidores)", "indisponível")
        st.caption(_badge_caption("derived", "inclui posts estáticos e Reels da amostra"))
    with col_reels:
        if by_views.get("status") == "ok":
            st.metric("Engajamento por visualizações", f"{by_views['value']:.2f}%", help=_MICROCOPY_ENGAJAMENTO_VIEWS)
            st.caption(_badge_caption("derived", f"{by_views.get('post_count', 0)} Reel(s) com views coletadas"))
        else:
            st.metric("Engajamento por visualizações", "indisponível", help=_MICROCOPY_ENGAJAMENTO_VIEWS)
            st.caption(_badge_caption("unavailable", "a fonte não forneceu views — indisponível não significa zero"))


_MICROCOPY_SINAL_INTERACAO_COORDENADA = (
    "Um pod é um grupo de contas que interage de forma repetida e concentrada para elevar "
    "artificialmente os sinais de engajamento. Este card mostra um alerta de padrão, não "
    "uma acusação."
)


def _render_audience_quality(analysis):
    """SPEC-001 §6.5: 'pod' só aparece no tooltip; nunca usa a linguagem de
    acusação de fraude. Itens brutos (lista completa de repetidores) ficam em
    Detalhes da auditoria (UI-09)."""
    st.subheader("Qualidade da audiência")
    audit_metrics = (analysis.get("audit_report") or {}).get("metrics") or {}
    pod_metric = audit_metrics.get("pod_index") or {}
    antifraude = analysis.get("antifraude") or {}
    top_repetidores = antifraude.get("top_repetidores") or {}

    if pod_metric.get("status") == "ok":
        valor = f"{pod_metric['value']:.1f}%"
        confianca = pod_metric.get("confidence") or "N/D"
    else:
        valor = f"{antifraude.get('pod_index', 0.0) * 100:.1f}%"
        confianca = "N/D"

    st.metric("Sinal de interação coordenada", valor, help=_MICROCOPY_SINAL_INTERACAO_COORDENADA)
    st.caption(
        _badge_caption("estimated", f"confiança: {confianca} · {len(top_repetidores)} conta(s) observada(s)")
    )
    for ressalva in pod_metric.get("ressalvas") or []:
        st.caption(f"Ressalva: {ressalva}")
    if not top_repetidores:
        st.caption("Nenhum repetidor relevante identificado nesta amostra.")


def _render_posts_maior_repercussao(analysis, campaign_insights):
    """SPEC-001 §6.6 (nomenclatura §4, ex-'Top 3 por alcance/volume' /
    ex-'Top 3 Posts'): usa o ranking do Gemini quando disponível; sem Gemini,
    cai para o ranking determinístico de engajamento absoluto do
    audit_report — nenhum dos dois é removido (SPEC-001 §2.2)."""
    st.markdown("**Posts de maior repercussão**")
    if campaign_insights and campaign_insights.get("top_3_content_ranking"):
        st.table(
            [
                {
                    "post": item.get("link") or item.get("post_id"),
                    "comentários": item.get("comments_count", 0),
                    "curtidas": item.get("likes_count", 0),
                }
                for item in campaign_insights["top_3_content_ranking"]
            ]
        )
        return
    metric = (analysis.get("audit_report") or {}).get("metrics", {}).get("top_posts") or {}
    posts = metric.get("posts") or []
    if metric.get("status") != "ok" or not posts:
        st.caption(exporter.TOP_POSTS_VAZIO_MSG)
        return
    st.table(
        [
            {
                "post": item.get("link") or item.get("post_id"),
                "tipo": item.get("media_type") or "N/D",
                "curtidas": item.get("likes_count", 0),
                "comentários": item.get("comments_count", 0),
                "engajamento (abs.)": item.get("engagement_absolute", 0),
                "engajamento (%)": (
                    f"{item['engagement_rate']:.2f}%" if item.get("engagement_rate") is not None else "N/D"
                ),
            }
            for item in posts
        ]
    )


def _render_posts_melhor_conversao(campaign_insights):
    """Ex-'Top 3 por qualidade/conversão' (SPEC-001 §4/§6.6)."""
    st.markdown("**Posts com melhor sinal de conversão**")
    st.caption(
        "Ranqueado pelo PostScore_i canônico: engajamento, qualidade do comentário, "
        "intenção de compra e sentimento, descontado risco de marca."
    )
    if not campaign_insights:
        st.caption(exporter.GEMINI_NAO_CONFIGURADO_MSG)
        return
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


def _render_temas_frequentes(campaign_insights):
    """Ex-'Top 3 pilares temáticos' (SPEC-001 §4/§6.6)."""
    st.markdown("**Temas que mais aparecem**")
    if not campaign_insights:
        st.caption(exporter.GEMINI_NAO_CONFIGURADO_MSG)
        return
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


def _render_hashtags_populares(analysis):
    st.markdown("**Hashtags populares**")
    metric = (analysis.get("audit_report") or {}).get("metrics", {}).get("popular_tags") or {}
    tags = metric.get("tags") or []
    if metric.get("status") != "ok" or not tags:
        st.caption(exporter.POPULAR_TAGS_VAZIO_MSG)
        return
    st.table([{"hashtag": item["tag"], "ocorrências": item["count"]} for item in tags])


def _render_parcerias_identificadas(analysis):
    """Ex-'Publis' (SPEC-001 §4, nomenclatura canônica). Publi confirmada e
    menção orgânica ficam separadas em duas listas (indícios de legenda e
    menções de @handle), preservando os dois conjuntos de dados já existentes."""
    st.markdown("**Parcerias identificadas**")
    publis = analysis.get("publis") or []
    if publis:
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
    else:
        st.caption(exporter.PUBLIS_VAZIO_MSG)

    metric = (analysis.get("audit_report") or {}).get("metrics", {}).get("brand_mentions") or {}
    mentions = metric.get("mentions") or []
    if metric.get("status") == "ok" and mentions:
        st.caption("Menções de marcas por @handle — publi confirmada x menção orgânica:")
        st.table(
            [
                {
                    "perfil": item["handle"],
                    "menções": item["count"],
                    "tipo": "Publi confirmada" if item["tipo"] == "publi_confirmada" else "Menção orgânica",
                }
                for item in mentions
            ]
        )
        for ressalva in metric.get("ressalvas") or []:
            st.caption(f"Ressalva: {ressalva}")
    elif not publis:
        st.caption(exporter.BRAND_MENTIONS_VAZIO_MSG)


def _render_content_quality(analysis, gemini_configurado):
    """SPEC-001 §6.6: duas colunas com papéis definidos — esquerda decide
    (posts), direita contextualiza (temas/hashtags/parcerias)."""
    st.subheader("Qualidade e conteúdo")
    campaign_insights = analysis.get("campaign_insights") if gemini_configurado else None
    col_esquerda, col_direita = st.columns([1.35, 1], gap="large")
    with col_esquerda:
        _render_posts_maior_repercussao(analysis, campaign_insights)
        _render_posts_melhor_conversao(campaign_insights)
    with col_direita:
        _render_temas_frequentes(campaign_insights)
        _render_hashtags_populares(analysis)
        _render_parcerias_identificadas(analysis)


def _render_audience_profile(analysis, gemini_configurado):
    """SPEC-001 §6.7 (ex-'Demografia da audiência'): gênero, região e faixa
    etária, sempre com cobertura amostral e o aviso de que a cobertura não
    representa automaticamente todos os seguidores."""
    st.subheader("Perfil da audiência (estimativa)")
    st.caption(
        "Estimativa a partir da amostra de comentários coletados. A cobertura não "
        "representa automaticamente todos os seguidores."
    )
    demografia = analysis.get("demografia") or {}
    pct_feminino = demografia.get("genero_pct", {}).get("feminino", 0.0) * 100
    st.write(
        f"**Gênero predominante:** {demografia.get('genero_predominante', 'indeterminado')} "
        f"({pct_feminino:.1f}% feminino na amostra)"
    )
    regioes = demografia.get("regioes") or []
    st.write(f"**Regiões detectadas:** {', '.join(regioes) if regioes else 'Nenhuma região detectada'}")

    audit_metrics = (analysis.get("audit_report") or {}).get("metrics") or {}
    gender_metric = audit_metrics.get("gender_distribution") or {}
    region_metric = audit_metrics.get("region_distribution") or {}
    if gender_metric.get("status") == "ok":
        st.caption(
            f"Cobertura amostral de gênero: {gender_metric['value']:.1f}% da amostra de "
            f"comentários ({gender_metric.get('total_identificados', 0)} nome(s) identificados)."
        )
    if region_metric.get("status") == "ok":
        st.caption(f"Cobertura amostral de região: {region_metric['value']:.1f}% da amostra de comentários.")
    for ressalva in gender_metric.get("ressalvas") or region_metric.get("ressalvas") or []:
        st.caption(f"Ressalva: {ressalva}")

    if gemini_configurado:
        parecer = (analysis.get("comentarios_analisados") or {}).get("parecer_comercial") or {}
        faixa = parecer.get("faixa_etaria_predominante")
        if faixa and faixa != "sem_dados":
            st.write(f"**Faixa etária predominante:** {faixa}")
        else:
            st.caption("Faixa etária predominante: sem dados suficientes para estimar.")


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


def _render_comment_reading(analysis, gemini_configurado):
    """SPEC-001 §6.8 (ex-'Comentários analisados'): primeira camada mostra só
    o resumo; tabela de itens Gemini/dados de depuração vão para Detalhes da
    auditoria (§6.8/UI-09)."""
    st.subheader("Comentários e intenção")
    comentarios = analysis.get("comentarios_analisados") or {}
    total = comentarios.get("total", 0)
    qualificados = comentarios.get("qualificados", 0)
    taxa_qualificados = (qualificados / total * 100) if total else 0.0
    st.write(
        f"Total coletado: **{total}** — Comentários com sinal útil: **{qualificados}** "
        f"({taxa_qualificados:.1f}%)"
    )
    st.caption("Comentários com conteúdo próprio, descontados emojis soltos, elogio genérico e spam/bot.")

    if not gemini_configurado:
        st.caption(exporter.GEMINI_NAO_CONFIGURADO_MSG)
        return

    parecer = comentarios.get("parecer_comercial")
    if parecer:
        _render_parecer_comercial(parecer)
        _render_intencao_compra_card(parecer)
        _render_sentimento_card(parecer)


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


def _render_brand_suitability_panel(campaign_insights):
    st.markdown("**Brand suitability**")
    veredito = campaign_insights.get("brand_suitability_verdict") or {}
    st.write(f"**Veredito:** {veredito.get('veredito', 'Sem dados suficientes para avaliar')}")
    if veredito.get("justificativa"):
        st.write(veredito["justificativa"])
    for alerta in veredito.get("alertas", []):
        st.warning(alerta)


_PROVENANCE_ROW_LABELS = {
    "engagement_rate_by_followers": "Por seguidores",
    "engagement_rate_by_reach": "Por alcance",
    "engagement_rate_by_views": "Por views de Reels",
}
_PROVENANCE_STATUS_LABELS = {"ok": "Disponível", "indisponivel": "Indisponível"}
_PROVENANCE_KIND_LABELS = {"derived": "Derivado", "estimated": "Estimado"}


def _render_provenance_card(analysis):
    # Sprint 002 Fase 3 (BENCHMARK-001.md §5.2): espelha na UI o mesmo
    # contrato canônico já exposto no exportador (src/exporter.py
    # _provenance_rows) — cada taxa de engajamento mostra se está disponível
    # nesta amostra, qual o denominador e o tipo de cálculo, para o usuário
    # nunca confundir "sem dado" com "engajamento zero".
    st.subheader("Proveniência e Escopo das Métricas")
    audit_report = analysis.get("audit_report") or {}
    metrics_map = audit_report.get("metrics") or {}
    if not metrics_map:
        st.caption("Nenhum dado de proveniência disponível para esta análise.")
        return

    for field, label in _PROVENANCE_ROW_LABELS.items():
        metric = metrics_map.get(field) or {}
        status = metric.get("status") or "indisponivel"
        status_label = _PROVENANCE_STATUS_LABELS.get(status, "Indisponível")
        valor = f"{metric['value']:.2f}%" if metric.get("value") is not None else "N/D"
        denominador = metric.get("denominator") or "N/D"
        tipo = _PROVENANCE_KIND_LABELS.get(metric.get("kind"), "N/D")
        fonte = metric.get("source") or "N/D"

        st.markdown(f"**{label}** — {status_label} — {valor}")
        st.caption(f"Denominador: {denominador} · Tipo: {tipo} · Fonte: {fonte}")
        for ressalva in metric.get("ressalvas") or []:
            st.caption(f"⚠️ {ressalva}")

    views_metric = metrics_map.get("engagement_rate_by_views") or {}
    if views_metric.get("status") == "ok":
        st.markdown("**Reels na amostra**")
        st.caption(
            f"{views_metric.get('post_count', 0)} vídeo(s)/Reels com views coletadas — "
            f"taxa de engajamento por views: {views_metric['value']:.2f}%."
        )


def _render_audit_details(analysis, state):
    """SPEC-001 §6.9/UI-09: números brutos, itens Gemini, fórmulas, IDs,
    warnings e metadados — tudo recolhido por padrão, nunca removido."""
    with st.expander("Detalhes da auditoria", expanded=False):
        st.caption(
            "Números brutos, itens classificados pelo Gemini, fórmulas e ressalvas "
            "técnicas desta auditoria."
        )
        st.write(f"Curtidas médias por post: **{analysis.get('average_likes', 0.0):.0f}**")
        st.write(f"Comentários médios por post: **{analysis.get('average_comments', 0.0):.0f}**")

        antifraude = analysis.get("antifraude") or {}
        top_repetidores = antifraude.get("top_repetidores") or {}
        st.markdown("**Contas com padrão de repetição (possíveis pods)**")
        if top_repetidores:
            st.table([{"conta": user, "comentários": count} for user, count in top_repetidores.items()])
        else:
            st.caption("Nenhum repetidor relevante identificado.")

        _render_provenance_card(analysis)

        comentarios = analysis.get("comentarios_analisados") or {}
        gemini_items = comentarios.get("gemini_items") or []
        if gemini_items:
            st.markdown("**Itens classificados pelo Gemini**")
            st.dataframe(gemini_items, width="stretch")

        campaign_insights = analysis.get("campaign_insights")
        if state.get("gemini_configurado") and campaign_insights:
            _render_campaign_insights_metric_cards(campaign_insights)
            _render_brand_suitability_panel(campaign_insights)


def _render_export_actions(analysis):
    st.subheader("Exportação")
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


def _render_report_page(analysis, state):
    """Composição de topo da tela de relatório (SPEC-001 §7): mesma ordem da
    arquitetura de informação da SPEC, §3. Em desktop, `_render_profile_header`
    e `_render_content_quality` usam st.columns([1.35, 1]); os pares de
    decisão dos KPIs usam st.columns(2) — nunca 3 ou 4 colunas (UI-01/UI-02).
    O Streamlit colapsa naturalmente para uma coluna em viewport estreito."""
    gemini_configurado = state.get("gemini_configurado", False)
    if state.get("demo_mode"):
        st.info("Resultado gerado em MODO DEMONSTRAÇÃO — dados fictícios, apenas para validar o pipeline fim-a-fim.")

    _render_profile_header(analysis, state)
    _render_decision_summary(analysis, gemini_configurado)
    _render_primary_kpis(analysis)
    _render_format_performance(analysis)
    _render_audience_quality(analysis)
    _render_content_quality(analysis, gemini_configurado)
    _render_audience_profile(analysis, gemini_configurado)
    _render_comment_reading(analysis, gemini_configurado)
    _render_audit_details(analysis, state)

    if not st.session_state.mostrar_relatorio:
        st.success("Relatório pronto! Clique abaixo para liberar a exportação em HTML/PDF.")
        if st.button("Ver Relatório"):
            st.session_state.mostrar_relatorio = True
            st.rerun()
    else:
        _render_export_actions(analysis)
        if st.button("Gerar novo relatório"):
            # Limpa só o estado da tela, nunca o cache global (FINDER-003 §2.4) —
            # quem quiser limpar o cache usa o botão "Limpar Cache e Re-analisar
            # Perfil" no formulário, de forma explícita.
            st.session_state.pipeline_state = {"status": "ocioso"}
            st.session_state.mostrar_relatorio = False
            st.rerun()


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
    _inject_design_system_css()

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
        _render_report_page(state["analysis"], state)


main()
