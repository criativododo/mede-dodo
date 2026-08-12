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

import os
import random
import re
import threading
import time

import streamlit as st

from src import data_loaders, database, demographics, exporter, filters, metrics, scoring, scraper
from src.gemini_analyzer import RealGeminiClient, analyze_comments

st.set_page_config(page_title="métricaDODÔ", page_icon="📊", layout="wide")

WINDOW_OPTIONS = [30, 60, 90]

RASPAGEM_NAO_IMPLEMENTADA_MSG = (
    "Raspagem real do Instagram ainda não implementada nesta fase "
    "(dívida técnica conhecida — ver docs/issues/ISSUE-0001.md). "
    "Ative o \"Modo demonstração\" abaixo para rodar o pipeline completo "
    "com dados fictícios gerados localmente, sem rede."
)

COLETA_INDISPONIVEL_MSG_TEMPLATE = (
    "Não foi possível coletar dados reais agora: {erro} Tente novamente mais "
    "tarde ou use o \"Modo demonstração\" para validar o pipeline sem "
    "depender de rede."
)

PIPELINE_STEPS = {
    "coleta": ("Coletando/consultando cache local...", 0.10),
    "filtragem": ("Filtrando comentários rasos...", 0.30),
    "demografia": ("Inferindo demografia da audiência...", 0.50),
    "pods_score": ("Calculando índice de pods e score DODÔ...", 0.70),
    "gemini": ("Análise de intenção (Gemini, se configurado)...", 0.85),
    "relatorio": ("Montando relatório final...", 0.97),
}

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
        try:
            cached = scraper.scrape_profile(
                username,
                window_days=window_days,
                fetch_fn=fetch_fn,
                throttle_fn=throttle_fn,
                cookies=cookies,
            )
        except NotImplementedError:
            state["status"] = "erro_scraping_nao_implementado"
            return
        except scraper.ScraperUnavailableError as exc:
            state["status"] = "erro_coleta_indisponivel"
            state["erro"] = str(exc)
            return

        posts = cached.get("posts", [])
        followers_count = cached.get("profile", {}).get("followers_count") or 0

        state["etapa"] = "filtragem"
        state["progresso"] = PIPELINE_STEPS["filtragem"][1]

        all_comments_flat = []
        metrics_posts = []
        engagement_posts = []
        for post in posts:
            raw_comments = (post.get("raw") or {}).get("comments", [])
            metrics_posts.append(
                {"post_id": post.get("post_id"), "commenters": [c.get("username") for c in raw_comments]}
            )
            engagement_posts.append(
                {"likes_count": post.get("likes_count") or 0, "comments_count": post.get("comments_count") or 0}
            )
            all_comments_flat.extend(raw_comments)

        qualified_comments = [c for c in all_comments_flat if not filters.is_shallow_comment(c.get("texto", ""))]
        total_comentarios = len(all_comments_flat)
        publis_detectadas = filters.detect_sponsored_posts(posts)

        state["etapa"] = "demografia"
        state["progresso"] = PIPELINE_STEPS["demografia"][1]

        names_db = data_loaders.load_names_db()
        ddd_to_uf = data_loaders.load_ddd_to_uf()

        genero_contagem = {"feminino": 0, "masculino": 0, "indeterminado": 0}
        regioes = []
        for c in all_comments_flat:
            nome = c.get("nome") or "desconhecido"
            genero = demographics.infer_gender(nome, names_db=names_db)
            genero_contagem[genero] = genero_contagem.get(genero, 0) + 1
            regiao_result = demographics.infer_region(c.get("texto", ""), ddd_to_uf=ddd_to_uf)
            for uf in regiao_result["por_ddd"] + regiao_result["por_mencao"]:
                if uf not in regioes:
                    regioes.append(uf)

        state["etapa"] = "pods_score"
        state["progresso"] = PIPELINE_STEPS["pods_score"][1]

        pod_result = metrics.calc_pod_index(metrics_posts)
        engagement_rate = scoring.calc_engagement_rate(engagement_posts, followers_count)
        qualified_ratio = (len(qualified_comments) / total_comentarios) if total_comentarios else 0.0
        response_rate = (
            sum(1 for c in all_comments_flat if c.get("respondido")) / total_comentarios
        ) if total_comentarios else 0.0
        score_dodo = scoring.calc_dodo_score(engagement_rate, qualified_ratio, response_rate, pod_result["pod_index"])

        state["etapa"] = "gemini"
        state["progresso"] = PIPELINE_STEPS["gemini"][1]

        # DUMMY.md #2: só comentários já filtrados localmente (qualified) vão ao Gemini.
        if gemini_client is not None:
            qualified_texts = [c.get("texto", "") for c in qualified_comments]
            gemini_result = analyze_comments(qualified_texts, gemini_client)
            gemini_items = gemini_result["items"]
        else:
            gemini_items = []

        state["etapa"] = "relatorio"
        state["progresso"] = PIPELINE_STEPS["relatorio"][1]

        analysis = {
            "username": username,
            "window_days": window_days,
            "score_dodo": score_dodo,
            "engagement_rate": engagement_rate,
            "demografia": {
                "genero_predominante": _genero_predominante(genero_contagem),
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
            },
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


def _render_metric_cards(analysis):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Score DODÔ (0-10)", f"{analysis['score_dodo']:.2f}")
    col2.metric("Taxa de engajamento", f"{analysis['engagement_rate'] * 100:.2f}%")
    col3.metric("Índice de pods", f"{analysis['antifraude']['pod_index'] * 100:.1f}%")
    col4.metric("Taxa de resposta da criadora", f"{analysis['antifraude']['taxa_resposta_criadora'] * 100:.1f}%")


def _render_demografia_card(analysis):
    st.subheader("Demografia da audiência")
    demografia = analysis["demografia"]
    st.write(f"**Gênero predominante:** {demografia['genero_predominante']}")
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


def _render_comentarios_card(analysis, gemini_configurado):
    st.subheader("Comentários analisados")
    comentarios = analysis["comentarios_analisados"]
    st.write(f"Total coletado: **{comentarios['total']}** — Qualificados (não rasos): **{comentarios['qualificados']}**")
    if not gemini_configurado:
        st.caption(exporter.GEMINI_NAO_CONFIGURADO_MSG)
    elif comentarios["gemini_items"]:
        st.dataframe(comentarios["gemini_items"], use_container_width=True)


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


def main():
    _init_state()

    st.title("métricaDODÔ")
    st.caption("Auditoria local de perfis do Instagram para campanhas de marketing — custo zero, 100% offline.")

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
        analisar_clicked = st.form_submit_button("Analisar", disabled=pipeline_running)

    if analisar_clicked:
        username = _normalize_username(username_input)
        if not username:
            st.warning("Informe um @perfil ou URL do Instagram válido antes de analisar.")
        else:
            gemini_client = None
            if not demo_mode:
                try:
                    gemini_client = RealGeminiClient()
                except RuntimeError:
                    # GEMINI_API_KEY ausente: segue sem Gemini, tratado graciosamente
                    # na UI via GEMINI_NAO_CONFIGURADO_MSG — nunca derruba o pipeline.
                    gemini_client = None
            st.session_state.pipeline_state = {"status": "rodando", "etapa": "coleta", "progresso": 0.0}
            thread = threading.Thread(
                target=_run_pipeline,
                args=(username, window_days, demo_mode, gemini_client, st.session_state.pipeline_state),
                daemon=True,
            )
            st.session_state.pipeline_thread = thread
            thread.start()
            st.rerun()

    state = st.session_state.pipeline_state
    status = state.get("status", "ocioso")

    if status == "rodando":
        etapa = state.get("etapa", "coleta")
        texto_etapa, progresso_padrao = PIPELINE_STEPS.get(etapa, ("Processando...", 0.0))
        progresso = state.get("progresso", progresso_padrao)
        st.progress(progresso, text=texto_etapa)
        time.sleep(0.3)
        st.rerun()
    elif status == "erro_scraping_nao_implementado":
        st.warning(RASPAGEM_NAO_IMPLEMENTADA_MSG)
    elif status == "erro_coleta_indisponivel":
        st.error(COLETA_INDISPONIVEL_MSG_TEMPLATE.format(erro=state.get("erro", "erro desconhecido")))
    elif status == "erro":
        st.error(f"Falha ao processar o pipeline: {state.get('erro', 'erro desconhecido')}")
    elif status == "concluido":
        analysis = state["analysis"]
        if state.get("demo_mode"):
            st.info("Resultado gerado em MODO DEMONSTRAÇÃO — dados fictícios, apenas para validar o pipeline fim-a-fim.")
        _render_metric_cards(analysis)
        col_left, col_right = st.columns(2)
        with col_left:
            _render_demografia_card(analysis)
            _render_publis_card(analysis)
        with col_right:
            _render_antifraude_card(analysis)
            _render_comentarios_card(analysis, state.get("gemini_configurado", False))
        _render_export_buttons(analysis)


main()
