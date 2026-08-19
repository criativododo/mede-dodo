"""métricaDODÔ — Dashboard Streamlit (ISSUE-0004).

Aplicação desktop local: audita perfis de influenciadoras do Instagram para
campanhas de marketing. 100% local, sem servidores/SDKs pagos de terceiros.

Regra inquebrável (DUMMY.md #1): a coleta/raspagem e o pipeline de análise
NUNCA rodam de forma síncrona na thread principal da UI. O botão "Gerar relatório"
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
# Raio de card não está fixado em SPEC-001 §8 — 12px é decisão editorial desta
# sprint (SPRINT-003), nomeado aqui para não virar literal solto pela CSS.
DS_RAIO_CARD = "12px"
DS_RAIO_SUPERFICIE_INTERNA = "8px"
# SPEC-004 §2.1 (contrato soberano desta tela): tokens funcionais exclusivos
# do relatório, escritos por cima de SPEC-001 onde os dois divergem — branco
# de contraste é texto/ícone sobre o vermelho haute, nunca superfície de
# card; borda de card é a medida própria da SPEC-004, não o cinza espuma
# herdado do protótipo do portal.
DS_BRANCO_CONTRASTE = "#FFFFFF"
DS_BORDA_CARD = "#E5E0D8"
DS_SOMBRA_ACAO = "0 6px 14px rgba(129,1,0,.18)"


def _inject_design_system_css():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {DS_CREME_CANNOLI};
        }}
        .stApp, .stApp p, .stApp label,
        .stApp span:not([data-testid="stIconMaterial"]) {{
            color: {DS_ONIX};
            font-family: "Elms Sans", sans-serif;
        }}
        /* stIconMaterial (setas de expander, ícones de status) usa a fonte de
        ligadura "Material Symbols Rounded" — herdar Elms Sans da regra acima
        (".stApp span" tem mais especificidade que o seletor de atributo do
        Streamlit) troca o glifo pelo nome cru do ícone ("keyboard_arrow_right"
        aparecendo como texto). A exclusão acima resolve; esta regra é reforço
        explícito para não depender só da ordem de especificidade. */
        .stApp [data-testid="stIconMaterial"] {{
            font-family: "Material Symbols Rounded" !important;
        }}
        /* SPEC-004 §2.2: display/título em Work Sans 700; corpo e microcopy em
        Elms Sans (regra acima). Mono (IBM Plex Mono) fica reservado a badges de
        procedência, IDs e valores técnicos de auditoria — nunca em título/corpo. */
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
        .stApp [data-testid="stMetricValue"] {{
            font-family: "Work Sans", sans-serif;
            font-weight: 700;
        }}
        /* _badge_caption() (badge de procedência: observado/derivado/estimado/...)
        usa markdown com crase simples, que o Streamlit renderiza como <code> —
        sem esta regra, o tema padrão do Streamlit pinta esse <code> de verde,
        uma cor fora da paleta Dodô e não documentada em nenhum token da
        SPEC-004. Vira pílula neutra com os mesmos tokens do `.dodo-badge`. */
        .stApp code {{
            color: {DS_ONIX} !important;
            background-color: {DS_CINZA_ESPUMA} !important;
            font-family: "IBM Plex Mono", monospace !important;
            border-radius: 999px !important;
            padding: 1px 10px !important;
        }}
        /* Sidebar e header do Streamlit usam cinza/branco cru por padrão — sem
        isso a moldura da aplicação não bate com o Design System Dodô, mesmo
        com o conteúdo já correto por dentro. */
        [data-testid="stSidebar"], header[data-testid="stHeader"] {{
            background-color: {DS_CREME_CANNOLI};
        }}
        /* Card editorial (SPEC-004 §4.1): superfície F5F4EC, borda 1px E5E0D8,
        raio 12px, sombra suave e padding generoso (24px horizontal / 20px
        vertical) — nunca branco puro como superfície. */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            background-color: {DS_BRANCO_BRILHANTE};
            border: 1px solid {DS_BORDA_CARD};
            border-radius: {DS_RAIO_CARD};
            box-shadow: {DS_SOMBRA_NEUTRA};
            padding: 20px 24px;
        }}
        [data-testid="stExpander"] summary {{
            background-color: {DS_BRANCO_BRILHANTE};
            border-radius: {DS_RAIO_CARD};
        }}
        [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
            background-color: {DS_BRANCO_BRILHANTE};
            border-radius: 0 0 {DS_RAIO_CARD} {DS_RAIO_CARD};
        }}
        /* Botão pílula (SPEC-004 §4.2): altura mínima 48px, padding horizontal
        28px, Work Sans 700, fundo vermelho haute, texto branco de contraste —
        nunca o creme cannoli, que é ilegível sobre o vinho. */
        .stButton button, .stFormSubmitButton button, .stDownloadButton button {{
            background-color: {DS_VERMELHO_HAUTE} !important;
            color: {DS_BRANCO_CONTRASTE} !important;
            border-radius: 999px !important;
            border: 1px solid {DS_VERMELHO_HAUTE} !important;
            min-height: 48px;
            height: 48px;
            padding: 0 28px;
            font-family: "Work Sans", sans-serif;
            font-weight: 700;
            box-shadow: {DS_SOMBRA_ACAO};
        }}
        .stButton button:hover, .stFormSubmitButton button:hover, .stDownloadButton button:hover {{
            background-color: {DS_BRANCO_BRILHANTE} !important;
            color: {DS_VERMELHO_HAUTE} !important;
        }}
        .stButton button:focus-visible, .stFormSubmitButton button:focus-visible {{
            outline: 2px solid {DS_VERMELHO_HAUTE} !important;
            outline-offset: 2px;
        }}
        .stButton button:disabled, .stFormSubmitButton button:disabled, .stDownloadButton button:disabled {{
            background-color: {DS_VERMELHO_HAUTE} !important;
            color: {DS_BRANCO_CONTRASTE} !important;
            opacity: .55;
            box-shadow: none;
        }}
        /* A regra ".stApp p/span/label" acima bate direto no <p> que o Streamlit
        usa para o rótulo do botão (<button><p>Texto</p></button>), vencendo por
        especificidade a cor herdada de .stButton/.stFormSubmitButton/.stDownloadButton
        button acima — sem isso o texto do botão fica quase preto sobre o fundo
        vinho. herdar a cor do botão pai resolve nos dois estados (normal/hover). */
        .stButton button p, .stButton button span,
        .stFormSubmitButton button p, .stFormSubmitButton button span,
        .stDownloadButton button p, .stDownloadButton button span {{
            color: inherit !important;
            font-family: inherit !important;
        }}
        /* Campos de formulário (texto e select) herdam o cinza cru padrão do
        Streamlit (rgb(240,242,246), sem token de Design System) — substitui
        pelo par creme/branco do Design System, com a mesma borda sutil dos
        cards. Streamlit 1.61 não usa mais BaseWeb nesses widgets (migrou para
        react-aria-components), por isso o alvo é o testid do wrapper, não
        [data-baseweb]. */
        [data-testid="stTextInputRootElement"],
        [data-testid="stSelectbox"] [role="group"] {{
            background-color: {DS_BRANCO_BRILHANTE} !important;
            border-color: {DS_BORDA_CARD} !important;
            border-radius: {DS_RAIO_SUPERFICIE_INTERNA} !important;
        }}
        /* st.container(key="dodo_decision_card") (SPRINT-003): key vira a classe
        `.st-key-dodo_decision_card` — troca o antigo `<div>` bruto aberto num
        st.markdown e fechado noutro, que o Streamlit não reconhece como um
        único bloco e renderizava como uma barra vazia acima do card real. */
        .st-key-dodo_decision_card {{
            background-color: {DS_BRANCO_BRILHANTE};
            border-left: 6px solid {DS_VERMELHO_HAUTE};
            border-radius: {DS_RAIO_CARD};
            padding: 20px 24px;
            margin-bottom: 16px;
        }}
        /* Pílula de procedência/hashtag (SPEC-004 §3.2, §4.1) — badge textual,
        nunca só cor: o rótulo (observado/derivado/estimado/#hashtag) é sempre
        legível por conta própria, a cor só reforça. */
        .dodo-badge {{
            display: inline-block;
            font-family: "IBM Plex Mono", monospace;
            font-size: 12px;
            padding: 3px 12px;
            margin: 0 6px 6px 0;
            border-radius: 999px;
            background-color: {DS_CINZA_ESPUMA};
            color: {DS_ONIX};
        }}
        .dodo-badge-estimado {{
            background-color: {DS_DALIA_VERMELHA};
            color: {DS_CREME_CANNOLI};
        }}
        /* st.info/st.success/st.warning/st.error nativos do Streamlit vêm com
        azul/verde/laranja de fábrica, fora da paleta Dodô — recolorido para o
        par creme/branco do Design System, com acento Vermelho Haute reservado
        para os estados que pedem atenção (warning/error). */
        [data-testid="stAlertContainer"] {{
            background-color: {DS_BRANCO_BRILHANTE} !important;
            border-radius: {DS_RAIO_CARD} !important;
            border-left: 4px solid {DS_BORDA_CARD};
        }}
        [data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]),
        [data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {{
            border-left-color: {DS_VERMELHO_HAUTE};
        }}
        [data-testid="stAlertContentSuccess"], [data-testid="stAlertContentSuccess"] p,
        [data-testid="stAlertContentInfo"], [data-testid="stAlertContentInfo"] p {{
            color: {DS_ONIX} !important;
        }}
        [data-testid="stAlertContentWarning"], [data-testid="stAlertContentWarning"] p,
        [data-testid="stAlertContentError"], [data-testid="stAlertContentError"] p {{
            color: {DS_VERMELHO_HAUTE} !important;
        }}
        /* Links ("Ver post ↗" em st.markdown e nas LinkColumn de st.dataframe)
        vêm azuis por padrão do tema do Streamlit — fora da paleta Dodô. O
        acento de ação da SPEC-004 é o vermelho haute, então links seguem o
        mesmo token do botão primário. */
        .stApp a, .stApp [data-testid="stDataFrameLinkCell"] a {{
            color: {DS_VERMELHO_HAUTE} !important;
        }}
        /* SPEC-006 §2.3: avatar circular de iniciais para mini-card de
        parceria — nunca uma foto/logo inventada (não existe URL de imagem no
        pipeline de coleta atual), só a inicial da marca real detectada na
        legenda sobre uma superfície neutra com borda sutil. */
        .dodo-avatar-circle {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            border-radius: 999px;
            background-color: {DS_CINZA_ESPUMA};
            border: 1px solid {DS_BORDA_CARD};
            font-family: "Work Sans", sans-serif;
            font-weight: 700;
            font-size: 15px;
            color: {DS_VERMELHO_HAUTE};
        }}
        /* SPEC-006 §2.3: pílula de ação "Ver post ↗" como link real (href do
        post), reaproveitando o par vermelho-haute/branco-contraste do botão
        primário — mesmo tratamento visual, elemento <a> em vez de <button>. */
        .dodo-pill-link {{
            display: inline-block;
            font-family: "Work Sans", sans-serif;
            font-weight: 700;
            font-size: 13px;
            color: {DS_BRANCO_CONTRASTE} !important;
            background-color: {DS_VERMELHO_HAUTE};
            border-radius: 999px;
            padding: 6px 16px;
            text-decoration: none;
        }}
        .dodo-pill-link:hover {{
            background-color: {DS_BRANCO_BRILHANTE};
            color: {DS_VERMELHO_HAUTE} !important;
        }}
        /* st.progress (barra do pipeline em andamento e barras de gênero da
        demografia) vem azul nativo do Streamlit (rgb(28,131,225)) por
        padrão, fora da paleta Dodô — trilho no cinza espuma, preenchimento
        no vermelho haute, mesmo par de tokens das barras do protótipo Paper. */
        [data-testid="stProgressBarTrack"] {{
            background-color: {DS_CINZA_ESPUMA} !important;
        }}
        [data-testid="stProgressBarTrack"] > div {{
            background-color: {DS_VERMELHO_HAUTE} !important;
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


_CONFIDENCE_LABELS = {
    "low": "baixa",
    "medium": "média",
    "high": "alta",
    "baixa": "baixa",
    "media": "média",
    "média": "média",
    "alta": "alta",
    None: "N/D",
}


def _confidence_label(value):
    """audit_report (src/metrics.py) devolve confidence em inglês
    (low/medium/high); o fallback legado antifraude já devolve em PT-BR
    (baixa/media) — normaliza os dois para nunca vazar inglês na tela
    (SPRINT-003, idioma PT-BR obrigatório)."""
    return _CONFIDENCE_LABELS.get(value, value or "N/D")


def _format_thousands(value):
    """Contagem absoluta com separador de milhar PT-BR (ex.: 2669 -> '2.669')
    — nunca compactado, usado em tabelas onde o valor exato importa mais que
    escaneabilidade (curtidas/comentários por post)."""
    try:
        return f"{int(round(value or 0)):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def _format_compact_number(value):
    """Número "de manchete" (seguidores/curtidas médias) compactado em K/M
    (ex.: 2219066 -> '2.2M', 150000 -> '150K') — mesma convenção usada por
    Instagram/X para KPIs de topo. Abaixo de 1.000, mostra o valor exato."""
    try:
        n = float(value or 0)
    except (TypeError, ValueError):
        return "0"
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n >= 1_000_000:
        texto = f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{sign}{texto}M"
    if n >= 1_000:
        texto = f"{n / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"{sign}{texto}K"
    return f"{sign}{int(round(n))}"


def _format_pct(value, casas=1):
    """Percentual limpo e consistente (1 casa decimal por padrão) — nunca
    misturar .1f/.2f/sem casas no mesmo relatório (SPRINT-003)."""
    if value is None:
        return "N/D"
    return f"{value:.{casas}f}%"


def _post_url(item):
    """Normaliza o campo 'link' numa URL clicável única — em content_posts
    (app.py, usado por campaign_insights) 'link' é o shortcode cru; em
    filters.detect_sponsored_posts/metrics.build_audit_report já vem como URL
    completa. Nunca deve sobrar shortcode/URL crua na tela (SPRINT-003)."""
    link = item.get("link") or item.get("post_id")
    if not link:
        return None
    link = str(link)
    return link if link.startswith("http") else f"https://www.instagram.com/p/{link}/"


_POST_LINK_COLUMN_CONFIG = {
    "post": st.column_config.LinkColumn("Post", display_text="Ver post ↗"),
}


def _render_empty_state(message, icon="—"):
    """Card de estado vazio (SPRINT-003) — substitui st.caption() solto por
    um container com a mesma hierarquia visual dos cards de dado, para "sem
    dado nesta amostra" nunca parecer um texto de erro perdido na tela."""
    with st.container(border=True):
        st.markdown(
            f"<div style='text-align:center; padding:4px 0;'>"
            f"<span style='font-size:20px;'>{icon}</span><br>"
            f"<span style='color:{DS_ONIX}; opacity:.65; font-size:14px;'>{message}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_pill_badges(labels):
    """Pílulas elegantes (SPEC-004 §3.2) para conjuntos curtos e homogêneos
    (hoje: hashtags que já passaram o piso de relevância em
    src.metrics.extract_popular_tags/POPULAR_TAGS_MIN_COUNT) — substitui a
    tabela crua de 2 colunas, que tratava cada hashtag como uma linha de
    dado tabular em vez de um rótulo curto e escaneável."""
    pills = "".join(f'<span class="dodo-badge">{html.escape(str(label))}</span>' for label in labels)
    st.markdown(f"<div>{pills}</div>", unsafe_allow_html=True)


WINDOW_OPTIONS = [30, 60, 90]

RASPAGEM_NAO_IMPLEMENTADA_MSG = (
    "Raspagem real do Instagram ainda não implementada nesta fase "
    "(dívida técnica conhecida — ver docs/issues/ISSUE-0001.md). "
    "Ative o \"Modo demonstração\" abaixo para rodar o pipeline completo "
    "com dados fictícios gerados localmente, sem rede."
)

COLETA_EM_RITMO_SEGURO_MSG = (
    "Análise em andamento: a coleta é realizada em ritmo seguro anti-bloqueio, com pausas "
    "propositais entre requisições (DUMMY.md #3). O tempo varia com o número de posts do "
    "perfil na janela selecionada, não com o tamanho da audiência — perfis muito ativos podem "
    "demorar mais que perfis grandes com poucos posts recentes."
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

# SPEC-006 §2.1: indicador de 3 estágios apresentacionais no estado de
# progresso — mapeia as etapas internas já escritas em `state["etapa"]` por
# `_run_pipeline`/`_make_coleta_progress_callback` (nenhuma etapa nova de
# pipeline é criada aqui, é só uma legenda mais compacta para a UI).
_PROGRESS_STAGE_LABELS = (
    "1. Coletando métricas",
    "2. Analisando comentários",
    "3. Consolidando formatos",
)
_PROGRESS_STAGE_BY_ETAPA = {
    "coleta": 0,
    "filtragem": 1,
    "demografia": 1,
    "pods_score": 1,
    "gemini": 1,
    "relatorio": 2,
}


def _render_progress_stage_indicator(etapa):
    estagio_ativo = _PROGRESS_STAGE_BY_ETAPA.get(etapa, 0)
    trechos = []
    for indice, label in enumerate(_PROGRESS_STAGE_LABELS):
        if indice == estagio_ativo:
            trechos.append(f'<span style="color:{DS_VERMELHO_HAUTE}; font-weight:700;">{label}</span>')
        else:
            trechos.append(f'<span style="opacity:.5;">{label}</span>')
    separador = '<span style="opacity:.35;"> &rarr; </span>'
    st.markdown(
        f'<div style="font-family:\'IBM Plex Mono\', monospace; font-size:13px; margin-top:8px;">'
        f"{separador.join(trechos)}</div>",
        unsafe_allow_html=True,
    )


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
        # SPEC-006: bio já é coletada por demo_fetch_fn/instaloader_fetch_fn e
        # persistida em database.profiles.bio (src/scraper.py:463) — só nunca
        # tinha sido propagada para `analysis`. Aditivo puro: nenhuma
        # heurística de coleta muda, só passa a usar um campo já existente.
        bio = cached.get("profile", {}).get("bio")

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
            "bio": bio,
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


def _render_quick_export_actions(analysis):
    """SPEC-006 §2.4: ações rápidas de exportação no header — Baixar PDF e
    Exportar CSV disponíveis assim que o relatório está `concluido`, sem
    depender do gate 'Ver Relatório' que continua controlando a seção
    'Exportação' completa (HTML/PDF/JSON) no rodapé. Chaves prefixadas com
    `header_` para não colidir com os botões homônimos de lá."""
    pdf_report = exporter.generate_pdf_report(analysis)
    csv_report = exporter.generate_csv_report(analysis)
    col_pdf, col_csv = st.columns(2)
    col_pdf.download_button(
        "Baixar PDF ↗",
        data=pdf_report,
        file_name=f"relatorio_{analysis['username']}.pdf",
        mime="application/pdf",
        key="header_download_pdf_button",
    )
    col_csv.download_button(
        "Exportar CSV ↗",
        data=csv_report,
        file_name=f"relatorio_{analysis['username']}.csv",
        mime="text/csv",
        key="header_download_csv_button",
    )


def _render_profile_header(analysis, state):
    """SPEC-001 §6.1: handle e identidade primeiro, nenhum número bruto antes
    dela; porte e janela ao lado; data de coleta e modo no rodapé. SPEC-006
    §2.4: ações rápidas de exportação acima do bloco de porte/janela.
    SPEC-006 (revisão de paridade visual com o protótipo Paper): avatar
    circular de inicial (nunca uma foto — não existe URL de avatar no
    pipeline) e bio só aparecem quando há dado real; bio já é coletada por
    demo_fetch_fn/instaloader_fetch_fn (src/scraper.py) e persistida em
    database.profiles.bio, só não era propagada para `analysis` até agora
    (campo aditivo, nenhuma heurística de coleta muda). Categoria/localização
    não aparecem aqui: não existe campo correspondente em nenhum ponto do
    pipeline — mostrar teria que inventar dado (SPEC-005 §1.2)."""
    username = analysis.get("username", "")
    bio = analysis.get("bio")
    porte = _classify_perfil_porte(analysis.get("followers_count"))
    window_days = analysis.get("window_days", "N/D")
    data_coleta = _format_data_coleta(analysis.get("data_coleta"))
    modo_label = "Demonstração" if state.get("demo_mode") else "Real"
    inicial = html.escape(username[:1].upper()) if username else "?"
    bio_html = (
        f'<span style="font-family:\'Elms Sans\', sans-serif; font-size:13px; '
        f'color:{DS_ONIX}; opacity:.65; max-width:480px; display:block;">{html.escape(bio)}</span>'
        if bio
        else ""
    )

    col_identidade, col_porte = st.columns([1.35, 1], gap="large")
    with col_identidade:
        st.markdown(
            '<div style="display:flex; flex-direction:row; gap:18px; align-items:center;">'
            f'<span class="dodo-avatar-circle" style="width:64px; height:64px; font-size:22px;">{inicial}</span>'
            '<div style="display:flex; flex-direction:column; gap:4px;">'
            f'<span style="font-family:\'Work Sans\', sans-serif; font-weight:700; font-size:24px; '
            f'color:{DS_ONIX};">@{html.escape(username)}</span>'
            f"{bio_html}</div></div>",
            unsafe_allow_html=True,
        )
    with col_porte:
        _render_quick_export_actions(analysis)
        st.write(f"**{porte}** · janela de {window_days} dias")
    st.caption(f"Coletado em {data_coleta} · Modo {modo_label}")


_LEITURA_CONTRATACAO_DISCLAIMER = (
    "Estimativas e alertas exigem revisão humana antes de qualquer decisão de contratação."
)


def _render_decision_summary(analysis, gemini_configurado):
    """SPEC-005 §3.1/§6.1 (ISSUE-0010): Score DODÔ e parecer de adequação
    comercial saem do primeiro viewport — o dataset/exportador continuam
    carregando os campos por compatibilidade, mas a UI só apresenta essa
    síntese aqui dentro, em 'Detalhes da auditoria', explicitamente rotulada
    como legada/derivada (nunca como a primeira conclusão do relatório).
    Nunca sugere aprovação automática (UI-10)."""
    score = analysis.get("score_dodo")
    parecer = (analysis.get("comentarios_analisados") or {}).get("parecer_comercial")

    with st.container(key="dodo_decision_card"):
        st.markdown("#### Score DODÔ (legado/derivado)")
        st.caption(
            "Síntese calculada localmente, preservada por compatibilidade — não é a "
            "primeira leitura do relatório."
        )
        st.metric(
            "Score DODÔ",
            f"{score:.2f}" if score is not None else "N/D",
            help=(
                "Índice de 0 a 10 que combina engajamento, qualidade de comentários, "
                "resposta da criadora e sinal de interação coordenada. Fórmula completa "
                "logo abaixo."
            ),
        )
        st.caption(_badge_caption("derived"))
        if gemini_configurado and parecer:
            label = ADERENCIA_INDICADOR_LABELS.get(parecer["indicador"], parecer["indicador"])
            st.markdown(f"**Parecer de adequação comercial (legado):** {label}")
            st.write(parecer.get("resumo", ""))
            for sinal in (parecer.get("alertas") or [])[:3]:
                st.markdown(f"- {sinal}")
        else:
            st.caption(exporter.GEMINI_NAO_CONFIGURADO_MSG)
        st.caption(_LEITURA_CONTRATACAO_DISCLAIMER)


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

    with st.container(border=True):
        linha1_col1, linha1_col2 = st.columns(2, gap="large")
        with linha1_col1:
            st.metric("Seguidores", _format_compact_number(analysis.get("followers_count", 0)))
            st.caption(_badge_caption("observed"))
        with linha1_col2:
            st.metric(
                "Engajamento por seguidores",
                _format_pct(analysis.get("engagement_rate", 0.0) * 100),
                help=_MICROCOPY_ENGAJAMENTO_SEGUIDORES,
            )
            st.caption(_badge_caption("derived", "denominador: seguidores"))

        linha2_col1, linha2_col2 = st.columns(2, gap="large")
        with linha2_col1:
            autenticidade = audit_metrics.get("audience_authenticity_signal") or {}
            if autenticidade.get("status") == "ok":
                valor = _format_pct(autenticidade["value"])
                confianca = _confidence_label(autenticidade.get("confidence"))
            else:
                fallback = analysis.get("fake_followers_estimate") or {}
                valor = _format_pct(fallback["value"]) if fallback.get("value") is not None else "indisponível"
                confianca = _confidence_label(fallback.get("confidence"))
            st.metric("Autenticidade da audiência (estimativa)", valor, help=_MICROCOPY_AUTENTICIDADE_AUDIENCIA)
            st.caption(_badge_caption("estimated", f"confiança: {confianca}"))
        with linha2_col2:
            creator_response = audit_metrics.get("creator_response_rate") or {}
            if creator_response.get("status") == "ok":
                valor = _format_pct(creator_response["value"])
                cobertura = f"{creator_response.get('total_count', 0)} comentário(s) avaliados"
            else:
                taxa = (analysis.get("antifraude") or {}).get("taxa_resposta_criadora", 0.0)
                valor = _format_pct(taxa * 100)
                cobertura = "cobertura amostral indisponível"
            st.metric("Respostas da criadora", valor, help=_MICROCOPY_RESPOSTAS_CRIADORA)
            st.caption(_badge_caption("derived", cobertura))


_MICROCOPY_ENGAJAMENTO_VIEWS = (
    "Calculado somente para Reels com visualizações disponíveis. Quando a plataforma não "
    "fornece views, o resultado aparece como indisponível."
)

_FORMAT_ORDER_UI = ("reels", "carrossel", "estatico")
_FORMAT_LABELS = {"reels": "Reels", "carrossel": "Carrossel", "estatico": "Estático"}
_MICROCOPY_FORMATO = (
    "Média de likes, média de comentários e ER calculados só sobre os posts deste "
    "formato na amostra coletada."
)


def _render_format_performance(analysis):
    """SPEC-005 §3.2/§4.3/§6.1 (ISSUE-0010): três cards comparáveis — Reels,
    Carrossel e Estático — cada um com n posts, likes médios, comentários
    médios e ER do próprio formato (metrics.calculate_format_metrics).
    Substitui o card genérico 'todos os formatos vs. views de Reels' da
    SPRINT-003. Categoria sem posts mostra 'sem posts suficientes', nunca
    três zeros."""
    st.subheader("Formatos")
    audit_metrics = (analysis.get("audit_report") or {}).get("metrics") or {}
    formats = (audit_metrics.get("format_metrics") or {}).get("formats") or {}

    columns = st.columns(3, gap="large")
    for coluna, formato in zip(columns, _FORMAT_ORDER_UI):
        with coluna:
            with st.container(border=True):
                st.markdown(f"**{_FORMAT_LABELS[formato]}**")
                dados = formats.get(formato) or {}
                if dados.get("status") == "ok":
                    st.metric("Likes médios", _format_compact_number(dados["average_likes"]), help=_MICROCOPY_FORMATO)
                    st.write(f"Comentários médios: **{_format_compact_number(dados['average_comments'])}**")
                    st.write(f"ER do formato: **{_format_pct(dados['engagement_rate'])}**")
                    st.caption(_badge_caption("derived", f"{dados.get('post_count', 0)} post(s) na amostra"))
                else:
                    st.caption("Sem posts suficientes nesta janela.")
                    st.caption(_badge_caption("unavailable", "indisponível não significa zero"))


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
        valor = _format_pct(pod_metric["value"])
        confianca = _confidence_label(pod_metric.get("confidence"))
    else:
        valor = _format_pct(antifraude.get("pod_index", 0.0) * 100)
        confianca = "N/D"

    with st.container(border=True):
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
        with st.container(border=True):
            st.dataframe(
                [
                    {
                        "post": _post_url(item),
                        "comentários": _format_thousands(item.get("comments_count", 0)),
                        "curtidas": _format_thousands(item.get("likes_count", 0)),
                    }
                    for item in campaign_insights["top_3_content_ranking"]
                ],
                width="stretch",
                hide_index=True,
                column_config=_POST_LINK_COLUMN_CONFIG,
            )
        return
    metric = (analysis.get("audit_report") or {}).get("metrics", {}).get("top_posts") or {}
    posts = metric.get("posts") or []
    if metric.get("status") != "ok" or not posts:
        _render_empty_state(exporter.TOP_POSTS_VAZIO_MSG)
        return
    with st.container(border=True):
        st.dataframe(
            [
                {
                    "post": _post_url(item),
                    "tipo": item.get("media_type") or "N/D",
                    "curtidas": _format_thousands(item.get("likes_count", 0)),
                    "comentários": _format_thousands(item.get("comments_count", 0)),
                    "engajamento (abs.)": _format_thousands(item.get("engagement_absolute", 0)),
                    "engajamento (%)": (
                        _format_pct(item["engagement_rate"]) if item.get("engagement_rate") is not None else "N/D"
                    ),
                }
                for item in posts
            ],
            width="stretch",
            hide_index=True,
            column_config=_POST_LINK_COLUMN_CONFIG,
        )


def _render_posts_melhor_conversao(campaign_insights):
    """Ex-'Top 3 por qualidade/conversão' (SPEC-001 §4/§6.6). Título revisado
    de "melhor sinal de conversão" para "maior potencial de conversão"
    (SPRINT-003 feedback editorial) — "sinal" é jargão técnico que não
    comunica o que a ordenação representa para quem vai contratar."""
    st.markdown("**Posts com maior potencial de conversão**")
    st.caption(
        "Ranqueado pelo PostScore_i canônico: engajamento, qualidade do comentário, "
        "intenção de compra e sentimento, descontado risco de marca."
    )
    if not campaign_insights:
        _render_empty_state(exporter.GEMINI_NAO_CONFIGURADO_MSG)
        return
    top_quality = campaign_insights.get("top_3_by_quality") or []
    if not top_quality:
        _render_empty_state("Sem posts na janela selecionada para ranquear.")
        return
    with st.container(border=True):
        st.dataframe(
            [
                {
                    "post": _post_url(item),
                    "PostScore": f"{item.get('post_score', 0.0):.2f}",
                    "comentários": _format_thousands(item.get("comments_count", 0)),
                    "curtidas": _format_thousands(item.get("likes_count", 0)),
                }
                for item in top_quality
            ],
            width="stretch",
            hide_index=True,
            column_config=_POST_LINK_COLUMN_CONFIG,
        )


def _render_temas_frequentes(campaign_insights):
    """Ex-'Top 3 pilares temáticos' (SPEC-001 §4/§6.6)."""
    st.markdown("**Temas que mais aparecem**")
    if not campaign_insights:
        _render_empty_state(exporter.GEMINI_NAO_CONFIGURADO_MSG)
        return
    top_pilares = campaign_insights.get("top_3_thematic_pillars") or []
    if not top_pilares:
        _render_empty_state("Sem pilares temáticos suficientes para ranquear nesta janela.")
        return
    with st.container(border=True):
        st.table(
            [
                {
                    "pilar": item["label"],
                    "comentários": item["count"],
                    "% dos comentários": _format_pct(item["pct"] * 100),
                }
                for item in top_pilares
            ]
        )


def _render_hashtags_populares(analysis):
    """SPEC-004 §3.2: hashtags como pílulas, não tabela — o piso de
    relevância (ocorrências ≥ 2) já é aplicado a montante em
    src.metrics.extract_popular_tags/POPULAR_TAGS_MIN_COUNT, então tudo que
    chega aqui em `tags` já passou do piso de ruído."""
    st.markdown("**Hashtags populares**")
    metric = (analysis.get("audit_report") or {}).get("metrics", {}).get("popular_tags") or {}
    tags = metric.get("tags") or []
    if metric.get("status") != "ok" or not tags:
        _render_empty_state(exporter.POPULAR_TAGS_VAZIO_MSG)
        return
    with st.container(border=True):
        _render_pill_badges(f"{item['tag']} · {item['count']}" for item in tags)


# SPEC-004 §3.2: resumo mostra no máximo cinco itens; o inventário integral
# fica em Detalhes da auditoria (ver _render_audit_details).
PARCERIAS_RESUMO_MAX = 5
# SPEC-006 §2.3: grade de mini-cards, não lista vertical — largura máxima em
# desktop comporta 4 cards por linha sem espremer o avatar/pílula.
PARCERIAS_COLUNAS_POR_LINHA = 4

_MICROCOPY_PARCERIAS_RESSALVA = (
    "Menção isolada não prova publicidade. `publi_confirmada` exige linguagem explícita de "
    "patrocínio na legenda, além da marcação."
)


def _render_parceria_mini_card(item):
    """SPEC-006 §2.3: avatar circular de iniciais — nunca uma foto/logo
    inventada, já que `filters.detect_sponsored_posts` não carrega URL de
    imagem nenhuma. A inicial vem da primeira marca real mencionada na
    legenda daquele post; sem marca identificada, mostra um glifo neutro em
    vez de fingir uma marca. O link é o mesmo `_post_url` já usado no resto
    da tela — sem `shortcode`, a pílula vira legenda muda, nunca um href
    fictício."""
    url = _post_url(item)
    termos = item.get("termos") or []
    marcas = item.get("marcas") or []
    # BRAND_MENTION_PATTERN (src/filters.py) captura o handle sem o "@" —
    # mesma convenção de exibição já usada em metrics.extract_brand_mentions
    # (`f"@{handle}"`), reaplicada aqui para o título do mini-card.
    marca_principal = marcas[0].lstrip("@") if marcas else None
    inicial = html.escape(marca_principal[:1].upper()) if marca_principal else "—"
    titulo = html.escape(f"@{marca_principal}") if marca_principal else "Publi sem marca identificada"
    indicios_texto = html.escape(" · ".join(termos)) if termos else "—"
    acao_html = (
        f'<a class="dodo-pill-link" href="{html.escape(url)}" target="_blank" rel="noopener">Ver post ↗</a>'
        if url
        else '<span style="font-size:12px; opacity:.5;">link indisponível</span>'
    )

    with st.container(border=True):
        st.markdown(
            '<div style="display:flex; flex-direction:column; gap:8px; align-items:flex-start;">'
            f'<span class="dodo-avatar-circle">{inicial}</span>'
            f"<strong>{titulo}</strong>"
            f'<span style="font-size:12px; opacity:.6;">Indícios: {indicios_texto}</span>'
            f"{acao_html}</div>",
            unsafe_allow_html=True,
        )


def _render_parcerias_identificadas(analysis):
    """Ex-'Publis' (SPEC-001 §4, nomenclatura canônica). Publi confirmada e
    menção orgânica ficam separadas em duas listas (indícios de legenda e
    menções de @handle), preservando os dois conjuntos de dados já existentes.
    SPEC-006 §2.3: grade de mini-cards com avatar circular de iniciais em vez
    de lista vertical de texto — cada card usa o link real daquele post
    específico (`analysis["publis"]`), não a métrica agregada por handle
    (`brand_mentions`, sem link de post único, que continua como tabela de
    resumo logo abaixo).
    SPEC-004 §3.2/§5.3: ressalva fixa junto do título e resumo limitado a
    PARCERIAS_RESUMO_MAX itens — o inventário completo não sai da tela, só
    migra para Detalhes da auditoria (_render_audit_details)."""
    st.markdown("**Parcerias identificadas**")
    st.caption(_MICROCOPY_PARCERIAS_RESSALVA)
    publis = analysis.get("publis") or []
    if publis:
        itens_resumo = publis[:PARCERIAS_RESUMO_MAX]
        for inicio in range(0, len(itens_resumo), PARCERIAS_COLUNAS_POR_LINHA):
            linha = itens_resumo[inicio : inicio + PARCERIAS_COLUNAS_POR_LINHA]
            colunas = st.columns(len(linha))
            for coluna, item in zip(colunas, linha):
                with coluna:
                    _render_parceria_mini_card(item)
        if len(publis) > PARCERIAS_RESUMO_MAX:
            st.caption(
                f"+{len(publis) - PARCERIAS_RESUMO_MAX} indício(s) adicional(is) — "
                "inventário completo em Detalhes da auditoria."
            )
    else:
        _render_empty_state(exporter.PUBLIS_VAZIO_MSG)

    metric = (analysis.get("audit_report") or {}).get("metrics", {}).get("brand_mentions") or {}
    mentions = metric.get("mentions") or []
    if metric.get("status") == "ok" and mentions:
        st.caption("Menções de marcas por @handle — publi confirmada x menção orgânica:")
        with st.container(border=True):
            st.dataframe(
                [
                    {
                        "perfil": item["handle"],
                        "menções": _format_thousands(item["count"]),
                        "tipo": "Publi confirmada" if item["tipo"] == "publi_confirmada" else "Menção orgânica",
                    }
                    for item in mentions[:PARCERIAS_RESUMO_MAX]
                ],
                width="stretch",
                hide_index=True,
            )
        if len(mentions) > PARCERIAS_RESUMO_MAX:
            st.caption(
                f"+{len(mentions) - PARCERIAS_RESUMO_MAX} menção(ões) adicional(is) — "
                "inventário completo em Detalhes da auditoria."
            )
        for ressalva in metric.get("ressalvas") or []:
            st.caption(f"Ressalva: {ressalva}")
    elif not publis:
        _render_empty_state(exporter.BRAND_MENTIONS_VAZIO_MSG)


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
    """SPEC-005 §4.1/§6.2 (ISSUE-0010): gênero como barras horizontais
    normalizadas pela amostra válida e reconhecida (feminino_validado +
    masculino_validado) — nunca pelo total bruto de comentários (o erro do
    '6.2%' corrigido pela SPEC-005). Região e faixa etária seguem com
    cobertura amostral e o aviso de que a cobertura não representa
    automaticamente todos os seguidores."""
    st.subheader("Perfil da audiência (estimativa)")
    st.caption(
        "Estimativa a partir da amostra de comentários coletados. A cobertura não "
        "representa automaticamente todos os seguidores."
    )
    demografia = analysis.get("demografia") or {}
    regioes = demografia.get("regioes") or []
    audit_metrics = (analysis.get("audit_report") or {}).get("metrics") or {}
    gender_metric = audit_metrics.get("gender_distribution") or {}
    region_metric = audit_metrics.get("region_distribution") or {}

    with st.container(border=True):
        genero_validado_n = gender_metric.get("genero_validado_n", 0)
        if gender_metric.get("status") == "ok" and genero_validado_n:
            st.write("**Gênero (amostra válida e reconhecida):**")
            st.progress(
                gender_metric["feminino_pct"] / 100,
                text=f"Feminino — {_format_pct(gender_metric['feminino_pct'])}",
            )
            st.progress(
                gender_metric["masculino_pct"] / 100,
                text=f"Masculino — {_format_pct(gender_metric['masculino_pct'])}",
            )
            st.caption(
                f"Cobertura amostral de gênero: {_format_pct(gender_metric.get('coverage_gender', 0.0) * 100)} "
                f"({genero_validado_n} nome(s) reconhecido(s) de gênero na amostra)."
            )
        else:
            st.caption("Amostra insuficiente para estimar composição de gênero nesta janela.")

        st.write(f"**Regiões detectadas:** {', '.join(regioes) if regioes else 'Nenhuma região detectada'}")
        if region_metric.get("status") == "ok":
            st.caption(f"Cobertura amostral de região: {_format_pct(region_metric['value'])} da amostra de comentários.")
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


# SPRINT-003 (feedback editorial): abaixo deste piso de comentários
# qualificados, os percentuais do Gemini são estatisticamente vazios (ex.: 1
# comentário "de interesse comercial" já mostra 100% numa tabela cheia de
# 0.0% nas outras linhas) — melhor um card de estado vazio explícito do que
# uma tabela que parece dado real.
MIN_COMENTARIOS_QUALIFICADOS_PARA_SENTIMENTO = 5


def _render_intencao_compra_card(parecer, qualificados):
    distribuicao = parecer.get("distribuicao_intencao_compra") or {}
    if not distribuicao:
        return
    st.markdown("**Distribuição de intenção de compra**")
    if qualificados < MIN_COMENTARIOS_QUALIFICADOS_PARA_SENTIMENTO:
        _render_empty_state(
            f"Amostra pequena demais ({qualificados} comentário(s) qualificado(s)) para uma "
            "distribuição de intenção de compra confiável."
        )
        return
    st.table(
        [
            {"Nível": INTENCAO_COMPRA_LABELS.get(nivel, nivel), "% dos comentários": _format_pct(pct * 100)}
            for nivel, pct in distribuicao.items()
        ]
    )


def _render_sentimento_card(parecer, qualificados):
    st.markdown("**Sentimento dos comentários (comercial x afetivo x crítica)**")
    if qualificados < MIN_COMENTARIOS_QUALIFICADOS_PARA_SENTIMENTO:
        _render_empty_state(
            f"Amostra pequena demais ({qualificados} comentário(s) qualificado(s)) para uma "
            "leitura de sentimento confiável."
        )
        return
    st.table(
        [
            {"Categoria": label, "% dos comentários": _format_pct(parecer.get(campo, 0.0) * 100)}
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
    with st.container(border=True):
        st.write(
            f"Total coletado: **{_format_thousands(total)}** — Comentários com sinal útil: "
            f"**{_format_thousands(qualificados)}** ({_format_pct(taxa_qualificados)})"
        )
        st.caption("Comentários com conteúdo próprio, descontados emojis soltos, elogio genérico e spam/bot.")

        if not gemini_configurado:
            _render_empty_state(exporter.GEMINI_NAO_CONFIGURADO_MSG)
            return

        parecer = comentarios.get("parecer_comercial")
        if parecer:
            _render_parecer_comercial(parecer)
            _render_intencao_compra_card(parecer, qualificados)
            _render_sentimento_card(parecer, qualificados)


def _render_campaign_insights_metric_cards(campaign_insights):
    st.subheader("Insights acionáveis de campanha")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        col1.metric(
            "Taxa de engajamento qualitativo",
            _format_pct(campaign_insights["qualitative_engagement_rate"]),
        )
        col1.caption(
            f"Benchmark editorial nano/micro: ~{BENCHMARK_ER_QUALITATIVO_MIN:.0f}%–"
            f"{BENCHMARK_ER_QUALITATIVO_MAX:.0f}% (ISSUE-001 §4.2). Pondera comentários por "
            "categoria de sentimento, não é a taxa de engajamento bruta."
        )
        col2.metric("Índice de intenção de compra", _format_pct(campaign_insights["purchase_intent_index"]))
        col2.caption("Média ponderada da intenção de compra classificada pelo Gemini nos comentários qualificados.")


def _render_brand_suitability_panel(campaign_insights):
    st.markdown("**Brand suitability**")
    veredito = campaign_insights.get("brand_suitability_verdict") or {}
    with st.container(border=True):
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
        valor = _format_pct(metric["value"]) if metric.get("value") is not None else "N/D"
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
            f"taxa de engajamento por views: {_format_pct(views_metric['value'])}."
        )


def _render_audit_details(analysis, state):
    """SPEC-002 §6.9/UI-09 + SPRINT-003 (FINDER-001 §4.3): números brutos,
    itens Gemini, fórmulas, IDs, warnings e metadados — tudo recolhido por
    padrão, nunca removido. Organizado em sub-blocos nomeados e escaneáveis
    (metodologia → procedência → itens do modelo → contas com padrão de
    repetição) em vez de uma lista única, já que Streamlit não tem um
    Accordion aninhado nativo — a subdivisão por `st.markdown`/`st.divider`
    dentro do único `st.expander` é o equivalente disponível neste stack."""
    with st.expander("Detalhes da auditoria", expanded=False):
        st.caption(
            "Números brutos, itens classificados pelo Gemini, fórmulas e ressalvas "
            "técnicas desta auditoria."
        )

        # SPEC-006 §1.1 item 6: o aviso de Modo Demonstração saiu do topo da
        # tela de relatório (primeiro viewport) e passou a viver aqui — mesmo
        # texto, só reposicionado, para não competir com os fatos concretos
        # do início do relatório.
        if state.get("demo_mode"):
            st.info(
                "Resultado gerado em MODO DEMONSTRAÇÃO — dados fictícios, apenas para validar o pipeline fim-a-fim."
            )

        # SPEC-005 §3.1/§6.1 (ISSUE-0010): Score DODÔ/parecer comercial saíram
        # do primeiro viewport — este é o único lugar onde ainda aparecem,
        # explicitamente rotulados como legado/derivado.
        _render_decision_summary(analysis, state.get("gemini_configurado", False))
        st.divider()

        st.markdown("#### Métricas brutas")
        st.write(f"Curtidas médias por post: **{_format_thousands(analysis.get('average_likes', 0.0))}**")
        st.write(f"Comentários médios por post: **{_format_thousands(analysis.get('average_comments', 0.0))}**")

        st.divider()
        st.markdown("#### Proveniência, janela e cobertura")
        _render_provenance_card(analysis)

        st.divider()
        st.markdown("#### Contas com padrão de repetição (possíveis pods)")
        antifraude = analysis.get("antifraude") or {}
        top_repetidores = antifraude.get("top_repetidores") or {}
        if top_repetidores:
            st.dataframe(
                [{"conta": user, "comentários": count} for user, count in top_repetidores.items()],
                width="stretch",
                hide_index=True,
            )
        else:
            st.caption("Nenhum repetidor relevante identificado.")

        # SPEC-004 §3.2: o resumo de "Parcerias identificadas" mostra no
        # máximo PARCERIAS_RESUMO_MAX itens — o inventário completo (sem
        # corte) vive aqui, não em outro lugar da tela.
        publis = analysis.get("publis") or []
        mentions = ((analysis.get("audit_report") or {}).get("metrics", {}).get("brand_mentions") or {}).get(
            "mentions"
        ) or []
        if publis or mentions:
            st.divider()
            st.markdown("#### Inventário completo de parcerias")
            if publis:
                st.dataframe(
                    [
                        {
                            "post": _post_url(item),
                            "indícios": ", ".join(item.get("termos") or []) or "—",
                            "marca(s)": ", ".join(item.get("marcas") or []) or "—",
                        }
                        for item in publis
                    ],
                    width="stretch",
                    hide_index=True,
                    column_config=_POST_LINK_COLUMN_CONFIG,
                )
            if mentions:
                st.dataframe(
                    [
                        {
                            "perfil": item["handle"],
                            "menções": _format_thousands(item["count"]),
                            "tipo": "Publi confirmada" if item["tipo"] == "publi_confirmada" else "Menção orgânica",
                        }
                        for item in mentions
                    ],
                    width="stretch",
                    hide_index=True,
                )

        comentarios = analysis.get("comentarios_analisados") or {}
        gemini_items = comentarios.get("gemini_items") or []
        if gemini_items:
            st.divider()
            st.markdown("#### Itens classificados pelo modelo (Gemini)")
            st.dataframe(gemini_items, width="stretch")

        campaign_insights = analysis.get("campaign_insights")
        if state.get("gemini_configurado") and campaign_insights:
            st.divider()
            st.markdown("#### Insights de campanha (Gemini)")
            _render_campaign_insights_metric_cards(campaign_insights)

        # SPEC-006 §1.1 item 6/§2.4: reanálise discreta dentro da auditoria —
        # mesmo reset de tela que "Gerar novo relatório" (nunca limpa cache,
        # ver comentário daquele botão), só posicionado perto de quem está
        # revisando o Score DODÔ/procedência e quer rodar de novo sem sair do
        # expander.
        st.divider()
        col_espaco, col_reanalisar = st.columns([3, 1])
        with col_reanalisar:
            if st.button("↻ Reanalisar perfil", key="reanalisar_perfil_button"):
                st.session_state.pipeline_state = {"status": "ocioso"}
                st.session_state.mostrar_relatorio = False
                st.rerun()


def _render_export_actions(analysis):
    """SPEC-002 §6.9/§9 previa HTML, PDF e JSON preservando a mesma
    proveniência — o JSON aqui é serialização direta do `analysis` já
    calculado pelo pipeline (mesmo dict usado pelos outros exportadores),
    sem recalcular nem alterar src/exporter.py."""
    st.subheader("Exportação")
    html_report = exporter.generate_html_report(analysis)
    pdf_report = exporter.generate_pdf_report(analysis)
    json_report = json.dumps(analysis, ensure_ascii=False, indent=2, default=str)
    col1, col2, col3 = st.columns(3)
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
    col3.download_button(
        "Baixar dados (JSON)",
        data=json_report,
        file_name=f"relatorio_{analysis['username']}.json",
        mime="application/json",
        key="download_json_button",
    )


def _render_report_page(analysis, state):
    """Composição de topo da tela de relatório (SPEC-002 §7 + SPRINT-003):
    mesma ordem da arquitetura de informação em 3 níveis (identidade → síntese
    → KPIs → evidência → detalhe). Em desktop, `_render_profile_header` e
    `_render_content_quality` usam st.columns([1.35, 1]); os pares de
    decisão (KPIs, qualidade/perfil de audiência, comentários/brand
    suitability) usam st.columns(2) — nunca 3 ou 4 colunas (UI-01/UI-02).
    O Streamlit colapsa naturalmente para uma coluna em viewport estreito."""
    gemini_configurado = state.get("gemini_configurado", False)

    _render_profile_header(analysis, state)
    _render_primary_kpis(analysis)
    _render_format_performance(analysis)

    # SPRINT-003: qualidade e perfil da audiência lado a lado, antes de
    # conteúdo — as duas perguntas ("o engajamento é limpo?" e "quem é essa
    # audiência?") pertencem ao mesmo par de decisão de evidência.
    col_qualidade_audiencia, col_perfil_audiencia = st.columns(2, gap="large")
    with col_qualidade_audiencia:
        _render_audience_quality(analysis)
    with col_perfil_audiencia:
        _render_audience_profile(analysis, gemini_configurado)

    _render_content_quality(analysis, gemini_configurado)

    # SPRINT-003: brand suitability sai do expander técnico e vira card de
    # Nível 2, ao lado de comentários e intenção — resumo de adequação
    # comercial não pode depender de abrir "Detalhes da auditoria".
    col_comentarios, col_brand_suitability = st.columns([1.35, 1], gap="large")
    with col_comentarios:
        _render_comment_reading(analysis, gemini_configurado)
    with col_brand_suitability:
        campaign_insights = analysis.get("campaign_insights") if gemini_configurado else None
        if campaign_insights:
            _render_brand_suitability_panel(campaign_insights)
        else:
            st.markdown("**Brand suitability**")
            st.caption(exporter.GEMINI_NAO_CONFIGURADO_MSG)

    _render_audit_details(analysis, state)

    if not st.session_state.mostrar_relatorio:
        st.success("Relatório pronto! Clique abaixo para liberar a exportação em HTML/PDF/JSON.")
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


def _render_hero_entrada():
    """SPEC-006 §1.1 item 1 / §2: moldura editorial acima do formulário de
    busca, visível só em `pipeline_state.status == "ocioso"` (antes de
    qualquer tentativa de análise) — não repete o wordmark de `st.title`, só
    adiciona a chamada de valor que estava no protótipo do Paper."""
    st.markdown(
        "<div style='text-align:center; padding:8px 0 4px 0;'>"
        "<span style='font-family:\"Work Sans\", sans-serif; font-weight:700; font-size:26px; "
        f"color:{DS_ONIX};'>Audite qualquer perfil do Instagram</span><br>"
        f"<span style='font-family:\"Elms Sans\", sans-serif; font-size:14px; color:{DS_ONIX}; opacity:.65;'>"
        "Cole o @perfil para gerar um relatório local — coleta e análise rodam neste computador, "
        "sem custos de API por consulta.</span></div>",
        unsafe_allow_html=True,
    )


def main():
    _init_state()
    _inject_design_system_css()

    st.title("métricaDODÔ")
    st.caption("Auditoria local de perfis do Instagram para campanhas de marketing — custo zero, 100% offline.")
    _render_session_status_sidebar()

    if st.session_state.pipeline_state.get("status", "ocioso") == "ocioso":
        _render_hero_entrada()

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
        analisar_clicked = col_analisar.form_submit_button("Gerar relatório", disabled=pipeline_running)
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
        if not demo_mode:
            st.info(COLETA_EM_RITMO_SEGURO_MSG)
        st.progress(progresso, text=label)
        _render_progress_stage_indicator(etapa)
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


if __name__ == "__main__":
    # Streamlit executa o script-alvo (via `streamlit run app.py` ou
    # `AppTest.from_file`) com `__name__ == "__main__"` (script_runner.py
    # instala um módulo fake `__main__` para isso). Este guard existe só para
    # que `import app` — usado por vários testes para chamar funções de
    # render isoladamente — NÃO rode `main()` como efeito colateral: antes
    # deste guard, isso deixava um `st.form` "aberto" no script-run em
    # execução, quebrando qualquer widget chamado depois no mesmo teste (ex.:
    # SPEC-006, botão "Reanalisar perfil" dentro de `_render_audit_details`).
    main()
