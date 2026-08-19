"""View pura do métricaDODÔ (ISSUE-001/002) — Streamlit, Bento Grid, Paper Desktop 1:1."""

import base64
import re
import sys
import threading
import time
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

# View pura (DUMMY.md §5 / SPEC-001 §3.2): jamais importar sqlite3/requests/urllib3
# nem tocar disco ou rede diretamente aqui. A orquestração da auditoria real
# (ISSUE-007) chama exclusivamente serviços internos de `features/` — nunca
# SQL cru nem HTTP direto nesta camada.

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.features.analise import ai_gemini, demographics, metrics  # noqa: E402
from src.features.coleta import database, scraper  # noqa: E402
from src.features.coleta.auth import get_secret  # noqa: E402
from src.features.relatorios import csv_exporter, pdf_exporter  # noqa: E402

st.set_page_config(
    page_title="métricaDODÔ",
    page_icon=":material/monitoring:",
    layout="wide",
)

st.html('<meta name="robots" content="noindex, nofollow">')

# CSS sob medida (ISSUE-003, DUMMY.md §6 Risco 3: tokens centralizados e
# constantes). Cores/fontes de título/corpo/raio já são nativos via
# .streamlit/config.toml — este bloco cobre só o que o tema nativo não
# expõe: superfície do card diferenciada do fundo Cannoli, sombra sutil, a
# fonte técnica (IBM Plex Mono) nos números de st.metric (o `codeFont` nativo
# só se aplica a blocos de código) e o contraste dos inputs de texto/select
# (o `secondaryBackgroundColor` global do tema — Cannoli escurecido — deixa
# esses dois widgets com um fundo amarelado dissonante do resto da UI).
_CUSTOM_CSS = """
<style>
[class*="st-key-card_"] {
    background-color: #FAF9F5;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.5rem !important;
    line-height: 1.25;
    overflow-wrap: anywhere;
}
div[data-testid="stTextInputRootElement"],
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    border: 1px solid #E5E0D8 !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
div[data-testid="stTextInputRootElement"]:focus-within,
div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within > div {
    border-color: #810100 !important;
    box-shadow: 0 0 0 1px #810100 !important;
}
.st-key-btn_auditar_perfil,
.st-key-btn_demo,
.st-key-btn_export_pdf,
.st-key-btn_export_csv {
    margin-top: 0.5rem;
}
.st-key-btn_auditar_perfil button,
.st-key-btn_demo button,
.st-key-btn_export_pdf button,
.st-key-btn_export_csv button {
    transition: box-shadow 0.15s ease, transform 0.15s ease;
}
.st-key-btn_auditar_perfil button:hover,
.st-key-btn_demo button:hover,
.st-key-btn_export_pdf button:hover,
.st-key-btn_export_csv button:hover {
    box-shadow: 0 2px 10px rgba(129, 1, 0, 0.18);
    transform: translateY(-1px);
}
</style>
"""
st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)


def _render_login_gate(app_password: str) -> None:
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.space("large")
        with st.container(border=True, key="card_login"):
            st.subheader("métricaDODÔ")
            st.caption("Acesso restrito — informe a senha para continuar.")
            password_input = st.text_input("Senha", type="password", key="input_password")
            if st.button("Entrar", type="primary", key="btn_login", width="stretch"):
                if password_input == app_password:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Senha incorreta.", icon=":material/error:")


_app_password = get_secret("APP_PASSWORD")
if _app_password and not st.session_state.get("authenticated"):
    _render_login_gate(_app_password)
    st.stop()

MOCK_REPORT = {
    "perfil": {
        "username": "@perfilexemplo",
        "marca_contratante": "Jescri Lingerie",
        "iniciais_criadora": "PE",
        "iniciais_marca": "JL",
        "porte": "Micro",
        "seguidores": 42800,
    },
    "janela": {"dias": 90, "rotulo": "Janela trimestral (90 dias)"},
    "status_coleta": "Modo mock / visual",
    "metricas": {
        "er_branding": 4.8,
        "bqi": 82,
        "ci": 78,
        "sd": 18,
    },
    "formatos": [
        {"formato": "Reels", "posts": 14, "er": 5.6},
        {"formato": "Carrossel", "posts": 9, "er": 4.1},
        {"formato": "Foto", "posts": 6, "er": 3.2},
    ],
    "tipologia": {"A": 20, "B": 32, "C": 21, "D": 27},
    "parecer_ia": {
        "status": "Recomendada com Alta Afinidade",
        "pontos_fortes": [
            "Consistência editorial acima do saudável (CI 78%)",
            "Comentários com forte densidade de conexão e desejo (V_AB 52%)",
            "Saturação de publis dentro da faixa preferencial (SD 18%)",
        ],
        "bloqueadores": [],
        "ressalvas": [
            "Amostra de comentários ainda não coletada nesta sessão (dados mockados).",
        ],
    },
}

# Amostra mockada de nomes/bios de comentaristas (Modo mock/visual) — usada só
# para exercitar de ponta a ponta o motor real de demografia (ISSUE-003), sem
# nenhuma coleta real nesta issue.
_MOCK_COMMENT_NAMES = [
    "Ana Paula", "Maria Clara", "Juliana Alves", "João Pedro", "Carlos Eduardo",
    "Fernanda Lima", "Beatriz Souza", "Rafael Costa", "Patrícia Nunes",
    "Marcos Vinícius", "Camila Rocha", "Bruno Teixeira", "Larissa Martins",
    "xX_zerocool_Xx", "usuario.instagram123",
]
_MOCK_TEXT_SAMPLES = [
    "Amei o look! sou de SP (11) 91234-5678",
    "Manda mais fotos, meu whats é 21 98888-7777",
    "Perfil lindo, moro no Rio",
    "(31) 99876-5432 quero comprar",
    "Sem contato aqui, só admirando",
]
MOCK_REPORT["demografia"] = {
    "genero": demographics.estimate_gender_distribution(_MOCK_COMMENT_NAMES),
    "localizacao": demographics.estimate_location_by_ddd(_MOCK_TEXT_SAMPLES),
}


# --- Dataset do Modo Demonstração (ISSUE-007 extensão) -----------------------------------------------------
# Dados 100% fictícios (nunca misturados com cache/coleta real — `source="demo"`
# tem sua própria label em `_STATUS_COLETA_LABELS`), usados só para exercitar o
# dashboard 100% preenchido com um clique quando a rede do Instagram oscila.
# A tipologia A/B/C/D já vem categorizada (`_DEMO_COMMENT_LABELS`) — pular a
# triagem via Gemini/heurística local é deliberado aqui: em modo convidado
# (sem chave), a heurística só reconhece ruído óbvio (D), deixando a maior
# parte da amostra sintética "incerta" e o card de Tipologia pobre. O restante
# do pipeline (demografia, motor de métricas, parecer) roda de verdade sobre
# este dataset, igual ao caminho de auditoria real.
_DEMO_PROFILE_DATA = {
    "username": "ana.estilodemo",
    "bio": "Moda autoral e styling do dia a dia ✨",
    "followers_count": 68_000,
}

_DEMO_CAPTIONS = [
    "Look do dia: alfaiataria + tênis",
    "5 formas de usar um blazer oversized",
    "Novo drop da coleção cápsula #publi",
    "Como usar cores neutras sem parecer sem graça",
    "Trend do momento: saia midi plissada",
    "Bastidores do editorial de verão",
    "Combo perfeito pro trabalho: camisa + calça pantalona",
    "Parceria com a Jescri Lingerie #publi",
    "Dica rápida: como amarrar um lenço no cabelo",
    "Look de festa em 3 variações",
    "O que eu uso pra viajar sem amassar a mala",
    "Acessórios que elevam qualquer produção",
    "Editorial inspirado nos anos 90",
    "Como montar um capsule wardrobe de inverno",
    "Resumo da semana de moda em looks",
]
_DEMO_FORMATS_CYCLE = ("Reel", "Carrossel", "Foto")
_DEMO_SPONSORED_INDEXES = {2, 7}
_DEMO_BASE_DATE = date(2026, 8, 15)

_DEMO_POSTS_DATA = [
    {
        "post_id": f"demo{indice + 1}",
        "format": _DEMO_FORMATS_CYCLE[indice % 3],
        "published_at": f"{(_DEMO_BASE_DATE - timedelta(days=indice * 5)).isoformat()}T12:00:00+00:00",
        "likes": 1800 + (indice % 5) * 350,
        "comments_count": 4 + (indice % 4),
        "caption": legenda,
        "is_sponsored": indice in _DEMO_SPONSORED_INDEXES,
        "reach_unique": 24_000 + (indice % 5) * 3_200,
        "shares": 60 + (indice % 5) * 25,
        "saves": 280 + (indice % 5) * 60,
    }
    for indice, legenda in enumerate(_DEMO_CAPTIONS)
]

_DEMO_FEMALE_NAMES = [
    "Ana Paula", "Mariana Silva", "Juliana Costa", "Fernanda Lima", "Camila Rocha",
    "Beatriz Souza", "Larissa Martins", "Patrícia Nunes", "Carla Mendes", "Bruna Alves",
    "Débora Santos", "Rafaela Vieira", "Gabriela Torres", "Isabela Ramos", "Aline Ferreira",
]
_DEMO_MALE_NAMES = [
    "João Pedro", "Carlos Eduardo", "Marcos Vinícius", "Bruno Teixeira", "Rafael Costa",
    "Lucas Almeida", "Pedro Henrique", "Thiago Barros", "Diego Cardoso", "André Luiz",
]
_DEMO_NAMES_CYCLE = _DEMO_FEMALE_NAMES + _DEMO_MALE_NAMES

# Ordem deliberada (8 A / 6 B / 5 C / 4 D = 23 textos) — o ciclo de 80
# comentários sobre esta lista produz exatamente a contagem de
# `_DEMO_COMMENT_LABELS` abaixo (3 voltas completas + 11 primeiros itens).
_DEMO_TEXTS = [
    # A — Desejo / Estilo
    "Amei esse look, quero um igual!",
    "Que combinação linda de cores, inspiração total",
    "Esse estilo é tudo que eu queria pro meu guarda-roupa",
    "Virou referência pra mim, salvei tudo",
    "A alfaiataria ficou impecável em você",
    "Preciso desse blazer na minha vida",
    "Seu senso de moda é impecável",
    "Que produção linda, arrasou",
    # B — Conexão real
    "Te acompanho há anos, sempre inspira",
    "Sua energia nesse vídeo é contagiante",
    "Adoro como você fala sobre moda de um jeito tão real",
    "Comecei a usar mais cor por sua causa, obrigada",
    "Sempre aprendo muito com seus conteúdos",
    "Você é autêntica, isso que mais admiro",
    # C — Comercial
    "Onde compro essa peça? Qual o preço?",
    "Manda o link da loja, por favor",
    "Tem no meu tamanho? Preciso saber",
    "Qual marca é o blazer?",
    "Faz entrega pra fora de SP?",
    # D — Ruído
    "kkkkk",
    "🔥🔥🔥",
    "primeira",
    "😍😍",
]
_DEMO_CONTACT_SNIPPETS = (
    " meu whats é (11) 91234-5678",
    " me chama no (21) 98888-7777",
    " (31) 99876-5432 quero comprar",
    " sou de SP, (11) 90000-1111",
)
_DEMO_COMMENT_LABELS = {"A": 32, "B": 21, "C": 15, "D": 12, "spam": 0}

_DEMO_COMMENTS_DATA = []
for _indice in range(80):
    _nome = _DEMO_NAMES_CYCLE[_indice % len(_DEMO_NAMES_CYCLE)]
    _texto = _DEMO_TEXTS[_indice % len(_DEMO_TEXTS)]
    if _indice % 9 == 0:
        _texto += _DEMO_CONTACT_SNIPPETS[_indice % len(_DEMO_CONTACT_SNIPPETS)]
    _DEMO_COMMENTS_DATA.append(
        {
            "post_id": f"demo{(_indice % 15) + 1}",
            "username": _nome.lower().replace(" ", "."),
            "display_name": _nome,
            "texto": _texto,
        }
    )

# Pilar 2 (retenção visual) simulado dentro das faixas normativas de
# `metrics._P2_BOUNDS` — inexistente em auditorias reais (Instaloader não
# expõe esses sinais), aqui só para demonstrar o BQI/CI completos.
_DEMO_P2_INPUTS = {
    "save_rate": 0.035,
    "share_rate": 0.017,
    "vtr": 0.35,
    "qualified_reach_rate": 0.82,
}
_DEMO_WEEKLY_CONSISTENCY = {"values": [4, 5, 4, 5, 4, 5, 4], "floor": 3}


def _avatar_svg(initials: str, bg: str, fg: str = "#FFFFFF") -> str:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        f'<circle cx="32" cy="32" r="32" fill="{bg}"/>'
        f'<text x="32" y="39" font-family="Work Sans, sans-serif" font-size="22" '
        f'font-weight="600" fill="{fg}" text-anchor="middle">{initials}</text>'
        "</svg>"
    )
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _bqi_status(value: float | None) -> tuple[str, str]:
    if value is None:
        return "Indisponível", "gray"
    if value >= 80:
        return "Excelente", "green"
    if value >= 65:
        return "Saudável", "blue"
    if value >= 50:
        return "Alerta", "orange"
    return "Não recomendado", "red"


def _ci_status(value: float | None) -> tuple[str, str]:
    if value is None:
        return "Indisponível", "gray"
    if value >= 75:
        return "Consistente", "green"
    if value >= 60:
        return "Aceitável (volátil)", "orange"
    return "Instável", "red"


def _sd_status(value: float | None) -> tuple[str, str]:
    if value is None:
        return "Indisponível", "gray"
    if value <= 20:
        return "Saudável", "green"
    if value <= 25:
        return "Tolerável", "blue"
    if value <= 33:
        return "Alerta", "orange"
    return "Não recomendado", "red"


def _verdict_color(status: str) -> str:
    return {
        "Recomendada com Alta Afinidade": "green",
        "Recomendada com Ressalvas": "orange",
        "Não Recomendada": "red",
    }.get(status, "gray")


# --- Orquestração da auditoria real (ISSUE-007) -----------------------------------------------------------
# Taxonomia de porte já normativa (FINDER-001.md §3.3 / SPEC-001.md §4.3) — nunca inventa faixa nova aqui.
_PORTE_LABELS = (
    (10_000, "Nano"), (50_000, "Micro"), (100_000, "Midi"), (1_000_000, "Macro"),
)
_FORMAT_DISPLAY_LABELS = {"reel": "Reels", "carrossel": "Carrossel", "foto": "Foto"}
_TIPOLOGIA_LABELS = {
    "A": "Desejo / Estilo",
    "B": "Conexão real",
    "C": "Comercial",
    "D": "Ruído",
}
_VEREDITO_LABELS = {
    "recomendada": "Recomendada com Alta Afinidade",
    "recomendada_com_ressalvas": "Recomendada com Ressalvas",
    "nao_recomendada": "Não Recomendada",
    "indisponivel": "Indisponível",
}
_STATUS_COLETA_LABELS = {
    "real": "Coleta real (Instaloader)",
    "cache": "Cache (24h)",
    "cache_fallback": "Fallback de cache (coleta real falhou)",
    "demo": "Modo demonstração (dados fictícios)",
}
_JOB_ACTIVE_STATUSES = {"queued", "running", "coleta_concluida", "analisando"}
_JOB_FAILURE_STATUSES = {"falha_sessao", "falha"}


def _porte_from_followers(followers: int | None) -> str:
    if not followers:
        return "Indisponível"
    for limite, rotulo in _PORTE_LABELS:
        if followers < limite:
            return rotulo
    return "Mega"


def _aggregate_tipologia(classifications: list) -> dict:
    counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for item in classifications:
        label = (item or {}).get("label")
        if label in counts:
            counts[label] += 1
    total = sum(counts.values())
    if total == 0:
        return dict(counts)
    return {chave: round(100 * valor / total, 1) for chave, valor in counts.items()}


def _aggregate_formatos(posts_data: list, er_by_format: dict) -> list:
    counts = {chave: 0 for chave in _FORMAT_DISPLAY_LABELS}
    for post in posts_data:
        fmt = (post.get("format") or "").lower()
        if fmt in counts:
            counts[fmt] += 1
    formatos = []
    for chave, rotulo in _FORMAT_DISPLAY_LABELS.items():
        if counts[chave] == 0:
            continue
        er_valor = ((er_by_format or {}).get(chave) or {}).get("value")
        formatos.append({"formato": rotulo, "posts": counts[chave], "er": er_valor})
    return formatos


def _parecer_to_view_shape(parecer: dict) -> dict:
    status = _VEREDITO_LABELS.get(parecer.get("veredito"), "Indisponível")
    pontos_fortes = [item.get("texto", "") for item in parecer.get("pontos_fortes") or []]
    ressalvas = [item.get("texto", "") for item in parecer.get("alertas") or []]
    ressalvas.extend(parecer.get("lacunas_de_dados") or [])
    return {"status": status, "pontos_fortes": pontos_fortes, "bloqueadores": [], "ressalvas": ressalvas}


def _resolve_comment_labels_and_tipologia(comments_data: list, comment_labels_override: dict | None):
    """Resolve os rótulos A/B/C/D/spam e a tipologia agregada. Em Modo
    Demonstração, os rótulos já vêm categorizados (`comment_labels_override`)
    — pula a triagem via Gemini/heurística local, que em modo convidado só
    reconhece ruído óbvio e deixaria a amostra sintética majoritariamente
    "incerta"."""
    if comment_labels_override is not None:
        counts = dict(comment_labels_override)
        expandido = [
            {"label": rotulo}
            for rotulo, quantidade in counts.items()
            if rotulo in ("A", "B", "C", "D")
            for _ in range(quantidade)
        ]
        return counts, _aggregate_tipologia(expandido), []

    ai_comments = [
        {"comment_id": f"{c.get('post_id')}::{i}", "text": c.get("texto", "")}
        for i, c in enumerate(comments_data)
    ]
    gemini_client = ai_gemini.get_gemini_client(get_secret("GEMINI_API_KEY"))
    triagem = ai_gemini.triage_comments(ai_comments, client=gemini_client)
    tipologia = _aggregate_tipologia(triagem["classifications"])
    # `spam` não é rastreado separadamente pela triagem A/B/C/D (ISSUE-005) —
    # entra como 0 no Pilar 3 (redutor de ruído), nunca como zero silencioso
    # no resultado exibido (P3 só afeta BQI, que já fica indisponível abaixo).
    counts = {
        "A": sum(1 for c in triagem["classifications"] if (c or {}).get("label") == "A"),
        "B": sum(1 for c in triagem["classifications"] if (c or {}).get("label") == "B"),
        "C": sum(1 for c in triagem["classifications"] if (c or {}).get("label") == "C"),
        "D": sum(1 for c in triagem["classifications"] if (c or {}).get("label") == "D"),
        "spam": 0,
    }
    return counts, tipologia, triagem["warnings"]


def _build_report(
    username_display: str,
    marca_contratante: str,
    profile_data: dict,
    posts_data: list,
    comments_data: list,
    source: str,
    base_warnings: list | None = None,
    comment_labels_override: dict | None = None,
    p2_inputs: dict | None = None,
    weekly_consistency: dict | None = None,
    janela: dict | None = None,
) -> dict:
    """Corpo compartilhado do pipeline (Demografia -> AI/Tipologia -> Métricas
    -> payload de renderização/exportação), usado tanto pela auditoria real
    (`_run_audit`) quanto pelo Modo Demonstração (`_run_demo_audit`) — cada
    etapa delega ao módulo dono, esta função só conecta (SPEC-001 §3.2/§3.4)."""
    warnings = list(base_warnings or [])

    nomes_comentaristas = [c.get("display_name") or c.get("username") for c in comments_data]
    genero = demographics.estimate_gender_distribution([n for n in nomes_comentaristas if n])
    localizacao = demographics.estimate_location_by_ddd([c.get("texto", "") for c in comments_data])

    comment_labels, tipologia, triagem_warnings = _resolve_comment_labels_and_tipologia(
        comments_data, comment_labels_override
    )
    warnings.extend(triagem_warnings)

    metrics_payload = {
        "profile": {"followers_count": profile_data.get("followers_count")},
        "posts": [
            {
                "post_id": post.get("post_id"),
                "format": (post.get("format") or "").lower(),
                "reach_unique": post.get("reach_unique"),
                "comments": post.get("comments_count", 0),
                "likes": post.get("likes", 0),
                "shares": post.get("shares", 0),
                "saves": post.get("saves", 0),
                "is_sponsored": post.get("is_sponsored", False),
            }
            for post in posts_data
        ],
        "stories": [],
        "comment_labels": comment_labels,
    }
    if p2_inputs is not None:
        metrics_payload["p2_inputs"] = p2_inputs
    if weekly_consistency is not None:
        metrics_payload["weekly_consistency"] = weekly_consistency

    metrics_result = metrics.calculate_metrics(metrics_payload)
    warnings.extend(metrics_result["warnings"])
    if posts_data and p2_inputs is None:
        # p2_inputs/weekly_consistency ficam de fora deliberadamente em
        # auditorias reais: save_rate, share_rate, VTR e alcance_qualificado
        # não são expostos pela API pública do Instagram via Instaloader —
        # sem eles, BQI/CI permanecem `indisponivel` (nunca aproximados por
        # outro sinal, ISSUE-004 Rodada 2/3).
        warnings.append(
            "Compartilhamentos e Salvamentos não são expostos pela API pública do Instagram — "
            "ER Branding real considera apenas Comentários e Curtidas."
        )
        warnings.append(
            "BQI e CI seguem indisponíveis em auditorias reais: dependem de save_rate/share_rate/VTR/"
            "alcance qualificado (Pilar 2) e de séries semanais com piso aprovado (CI), que a coleta "
            "pública via Instaloader não expõe — ver ISSUE-004 Rodadas 2/3."
        )

    # O parecer escrito usa sempre o template local honesto (client=None):
    # BQI/CI seguem indisponíveis em auditorias reais (Pilar 2/CI sem dado
    # real), então pedir ao Gemini um veredito sobre métricas centrais
    # ausentes violaria a regra de não fabricar dado (issue-005 §6.2).
    parecer = ai_gemini.resolve_opinion(
        {
            "er_branding": metrics_result["er_branding"]["value"],
            "bqi": metrics_result["bqi"]["value"],
            "ci": metrics_result["ci"]["value"],
            "sd": metrics_result["sponsor_density"]["value"],
        },
        client=None,
    )

    followers_count = profile_data.get("followers_count")
    iniciais_marca = "".join(palavra[0] for palavra in marca_contratante.split()[:2]).upper() or "??"
    janela_resolvida = janela or {"dias": 90, "rotulo": "Janela trimestral (90 dias)"}

    return {
        "status": "ok",
        "perfil": {
            "username": f"@{username_display}",
            "marca_contratante": marca_contratante,
            "iniciais_criadora": username_display[:2].upper() or "??",
            "iniciais_marca": iniciais_marca,
            "porte": _porte_from_followers(followers_count),
            "seguidores": followers_count or 0,
        },
        "janela": janela_resolvida,
        "status_coleta": _STATUS_COLETA_LABELS.get(source, "Coleta"),
        "metricas": {
            "er_branding": metrics_result["er_branding"]["value"],
            "bqi": metrics_result["bqi"]["value"],
            "ci": metrics_result["ci"]["value"],
            "sd": metrics_result["sponsor_density"]["value"],
        },
        "formatos": _aggregate_formatos(posts_data, metrics_result["er_by_format"]),
        "tipologia": tipologia,
        "demografia": {"genero": genero, "localizacao": localizacao},
        "parecer_ia": _parecer_to_view_shape(parecer),
        "provenance": {
            "method_version": metrics.METHOD_VERSION,
            "window_days": janela_resolvida.get("dias"),
            "posts_n": len(posts_data),
        },
        "posts": [
            {
                "post_id": post.get("post_id"),
                "format": post.get("format"),
                "published_at": post.get("published_at"),
                "likes": post.get("likes"),
                "comments": post.get("comments_count"),
                "shares": post.get("shares"),
                "saves": post.get("saves"),
                "reach": post.get("reach_unique"),
                "is_sponsored": post.get("is_sponsored"),
            }
            for post in posts_data
        ],
        "warnings": warnings,
    }


def _run_audit(username: str, marca_contratante: str) -> dict:
    """Orquestra o fluxo completo (ISSUE-007): cache/coleta -> demografia ->
    triagem A/B/C/D + parecer -> métricas -> payload pronto para
    renderização/exportação, via `_build_report`."""
    clean_username = username.strip().lstrip("@")

    pre_cached = database.get_cached_profile(clean_username)
    if pre_cached is not None:
        source = "cache"
        profile_data = pre_cached["profile_data"]
        posts_data = pre_cached["posts_data"]
        comments_data = pre_cached["comments_data"]
        base_warnings = []
    else:
        try:
            collected = scraper.collect_profile(clean_username)
        except scraper.ScraperError as exc:
            return {"status": "coleta_indisponivel", "username": clean_username, "error_reason": exc.reason}
        source = collected.get("source", "real")
        profile_data = collected["profile_data"]
        posts_data = collected["posts_data"]
        comments_data = collected["comments_data"]
        base_warnings = list(collected.get("warnings", []))

    janela_estendida = any("Janela estendida" in aviso for aviso in base_warnings)
    janela = (
        {"dias": None, "rotulo": f"Janela estendida (últimos {len(posts_data)} posts)"}
        if janela_estendida
        else None
    )

    username_display = profile_data.get("username") or clean_username
    return _build_report(
        username_display, marca_contratante, profile_data, posts_data, comments_data,
        source, base_warnings=base_warnings, janela=janela,
    )


def _run_demo_audit(marca_contratante: str) -> dict:
    """Modo Demonstração: mesmo pipeline de `_run_audit` (Demografia ->
    AI/Métricas -> Render/Export), mas sobre um perfil 100% fictício — nunca
    grava nem lê cache real, nunca toca o Instaloader."""
    return _build_report(
        _DEMO_PROFILE_DATA["username"],
        marca_contratante,
        _DEMO_PROFILE_DATA,
        _DEMO_POSTS_DATA,
        _DEMO_COMMENTS_DATA,
        source="demo",
        base_warnings=[
            "Modo demonstração: perfil e métricas fictícios para visualizar o dashboard completo "
            "(inclui BQI/CI simulados — indisponíveis em auditorias reais)."
        ],
        comment_labels_override=_DEMO_COMMENT_LABELS,
        p2_inputs=_DEMO_P2_INPUTS,
        weekly_consistency=_DEMO_WEEKLY_CONSISTENCY,
    )


if "report" not in st.session_state:
    st.session_state.report = MOCK_REPORT

report = st.session_state.report
perfil = report["perfil"]
janela = report["janela"]
metricas = report["metricas"]

st.title("métricaDODÔ")
st.caption("Auditoria editorial de criadoras para marcas de moda — relatório trimestral")

# 1. Header de identidade
with st.container(border=True, key="card_header"):
    header = st.columns([1, 3, 3, 1], vertical_alignment="center")
    with header[0]:
        st.image(_avatar_svg(perfil["iniciais_criadora"], bg="#810100"), width=64)
    with header[1]:
        st.text_input("Perfil do Instagram", value=perfil["username"], key="input_username")
        st.caption(f"{perfil['porte']} · {perfil['seguidores']:,} seguidores".replace(",", "."))
    with header[2]:
        st.selectbox(
            "Marca contratante",
            options=["Jescri Lingerie", "Ela Fashion Mkt", "Marca genérica Dodô"],
            key="input_marca",
        )
        st.caption("Contextualiza o parecer editorial da IA para o briefing.")
    with header[3]:
        st.image(_avatar_svg(perfil["iniciais_marca"], bg="#3F3229"), width=64)
    st.badge(f"{janela['rotulo']} · {report['status_coleta']}", icon=":material/schedule:", color="primary")

    with st.container(horizontal=True):
        auditar_clicado = st.button(
            "Auditar Perfil", icon=":material/search:", type="primary", key="btn_auditar_perfil"
        )
        demo_clicado = st.button(
            "Carregar Exemplo (Demo)", icon=":material/play_circle:", key="btn_demo"
        )

    if auditar_clicado:
        with st.spinner("Coletando cache/perfil, analisando comentários e calculando métricas..."):
            resultado = _run_audit(
                st.session_state.get("input_username", perfil["username"]),
                st.session_state.get("input_marca", perfil["marca_contratante"]),
            )
        if resultado.get("status") == "coleta_indisponivel":
            st.error(
                f"Coleta indisponível para {resultado['username']} ({resultado['error_reason']}) "
                "e nenhum cache válido foi encontrado.",
                icon=":material/error:",
            )
        else:
            st.session_state.report = resultado
            st.rerun()
    elif demo_clicado:
        with st.spinner("Carregando dados de demonstração..."):
            resultado = _run_demo_audit(st.session_state.get("input_marca", perfil["marca_contratante"]))
        st.session_state.report = resultado
        st.rerun()

st.space("small")

# 2. Cards de métricas principais (Bento Grid topo) — "Indisponível" explícito
# em vez de zero silencioso quando a métrica ainda não foi resolvida (ex.:
# BQI/CI dependem de sinais que a coleta pública via Instaloader não expõe,
# exceto em Modo Demonstração).
with st.container(horizontal=True):
    with st.container(border=True, width="stretch", key="card_metric_er"):
        er_valor = metricas.get("er_branding")
        st.metric("ER Branding", f"{er_valor}%" if er_valor is not None else "Indisponível")
        st.caption(f"Contextualizado por porte {perfil['porte']}")

    with st.container(border=True, width="stretch", key="card_metric_bqi"):
        bqi_valor = metricas.get("bqi")
        st.metric("BQI", f"{bqi_valor}/100" if bqi_valor is not None else "Indisponível")
        label, color = _bqi_status(bqi_valor)
        st.badge(label, color=color)

    with st.container(border=True, width="stretch", key="card_metric_ci"):
        ci_valor = metricas.get("ci")
        st.metric("Consistência (CI)", f"{ci_valor}%" if ci_valor is not None else "Indisponível")
        label, color = _ci_status(ci_valor)
        st.badge(label, color=color)

    with st.container(border=True, width="stretch", key="card_metric_sd"):
        sd_valor = metricas.get("sd")
        st.metric("Saturação de publis (SD)", f"{sd_valor}%" if sd_valor is not None else "Indisponível")
        label, color = _sd_status(sd_valor)
        st.badge(label, color=color)

st.space("small")

# 3. Bloco central: distribuições e demografia
with st.container(horizontal=True):
    with st.container(border=True, width="stretch", key="card_formatos"):
        st.subheader("Distribuição de formatos")
        if not report["formatos"]:
            st.caption("Indisponível — nenhum post no período analisado.")
        else:
            total_posts_formatos = sum(linha["posts"] for linha in report["formatos"]) or 1
            for linha in report["formatos"]:
                proporcao = linha["posts"] / total_posts_formatos
                er_rotulo = f"{linha['er']}%" if linha["er"] is not None else "indisponível"
                st.progress(
                    proporcao,
                    text=f"{linha['formato']} · {linha['posts']} posts ({proporcao * 100:.0f}%) · ER {er_rotulo}",
                )

    with st.container(border=True, width="stretch", key="card_tipologia"):
        st.subheader("Tipologia de comentários")
        tipologia = report["tipologia"]
        if not any(tipologia.values()):
            st.caption("Indisponível — nenhum comentário classificado nesta amostra.")
        else:
            v_ab = round(tipologia["A"] + tipologia["B"], 1)
            st.badge(
                f"V_AB (valor de marca): {v_ab}% — patamar saudável ≥ 40%",
                icon=":material/favorite:",
                color="green" if v_ab >= 40 else "orange",
            )
            for chave, rotulo in _TIPOLOGIA_LABELS.items():
                st.progress(tipologia[chave] / 100, text=f"{rotulo} ({chave}) · {tipologia[chave]}%")

    with st.container(border=True, width="stretch", key="card_demografia"):
        st.subheader("Demografia estimada")
        genero = report["demografia"]["genero"]
        st.caption(f"Gênero (estimativa por nome · cobertura {genero['coverage_pct']}%)")
        if genero["coverage_pct"] == 0:
            st.caption("Indisponível / Cobertura insuficiente — nenhum nome reconhecido na amostra.")
        else:
            st.progress(genero["female_pct"] / 100, text=f"Feminino {genero['female_pct']}%")
            st.progress(genero["male_pct"] / 100, text=f"Masculino {genero['male_pct']}%")
            if genero["unknown_pct"] > 0:
                st.caption(f"Indeterminado: {genero['unknown_pct']}%")

        localizacao = report["demografia"]["localizacao"]
        st.caption(f"Top 3 estados por DDD (cobertura {localizacao['coverage_pct']}%)")
        top_estados = localizacao["top_estados"]
        if not top_estados:
            st.caption("Indisponível / Cobertura insuficiente — nenhum DDD reconhecido na amostra.")
        else:
            total_mencoes = sum(estado["mencoes"] for estado in top_estados) or 1
            chips = " ".join(
                f":primary-badge[{posicao}. {estado['uf']} "
                f"({round(100 * estado['mencoes'] / total_mencoes)}%)]"
                for posicao, estado in enumerate(top_estados, start=1)
            )
            st.markdown(chips)

st.space("small")

# 4. Card de parecer editorial da IA
parecer = report["parecer_ia"]
with st.container(border=True, key="card_parecer"):
    st.badge(parecer["status"], icon=":material/auto_awesome:", color=_verdict_color(parecer["status"]))
    st.subheader("Parecer editorial da IA")
    st.markdown("**Pontos fortes**")
    for ponto in parecer["pontos_fortes"]:
        st.markdown(f"- {ponto}")
    if parecer["bloqueadores"]:
        st.markdown("**Bloqueadores**")
        for bloqueador in parecer["bloqueadores"]:
            st.markdown(f"- {bloqueador}")
    if parecer["ressalvas"]:
        st.markdown("**Ressalvas para o briefing**")
        for ressalva in parecer["ressalvas"]:
            st.markdown(f"- {ressalva}")

st.space("small")

# 5. Barra de ações (rodapé) — ISSUE-006: os exportadores recebem o `report`
# já resolvido em `st.session_state` e apenas retornam bytes; a View apenas
# conecta esses bytes ao controle de download (nenhuma composição aqui).
_username_slug = re.sub(r"[^A-Za-z0-9]+", "", perfil.get("username", "perfil"))
_export_date = date.today().isoformat()

with st.container(horizontal=True):
    st.download_button(
        "Exportar relatório em PDF",
        data=pdf_exporter.generate_pdf_report(report),
        file_name=f"metricaDODO_{_username_slug}_{_export_date}.pdf",
        mime="application/pdf",
        icon=":material/picture_as_pdf:",
        type="primary",
        key="btn_export_pdf",
    )
    st.download_button(
        "Baixar CSV",
        data=csv_exporter.generate_csv_report(report),
        file_name=f"metricaDODO_{_username_slug}_{_export_date}.csv",
        mime="text/csv",
        icon=":material/download:",
        key="btn_export_csv",
    )
