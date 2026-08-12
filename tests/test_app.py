import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def test_app_boots_without_exception():
    at = AppTest.from_file(APP_PATH)
    at.run()

    assert not at.exception


def test_app_has_main_input_widgets():
    at = AppTest.from_file(APP_PATH)
    at.run()

    assert not at.exception
    # RF-01: input de perfil/URL
    assert len(at.text_input) >= 1
    # RF-02: seletor de janela 30/60/90 dias
    assert len(at.selectbox) >= 1
    assert list(at.selectbox[0].options) == [30, 60, 90] or "30" in [
        str(o) for o in at.selectbox[0].options
    ]
    # botão de disparo do pipeline
    button_labels = [b.label for b in at.button]
    assert any("Analisar" in label for label in button_labels)


def test_app_has_demo_mode_toggle():
    at = AppTest.from_file(APP_PATH)
    at.run()

    assert not at.exception
    # Modo demonstração — coexiste com raspagem real ainda não implementada (ISSUE-0001)
    assert len(at.toggle) >= 1
    toggle_labels = [t.label for t in at.toggle]
    assert any("emonstra" in label for label in toggle_labels)


def test_app_idle_state_shows_no_analysis_yet():
    at = AppTest.from_file(APP_PATH)
    at.run()

    assert not at.exception
    # Sem clique em "Analisar", não deve haver botões de download de relatório
    download_button_labels = [b.label for b in at.download_button]
    assert download_button_labels == []


def test_app_has_limpar_cache_button():
    at = AppTest.from_file(APP_PATH)
    at.run()

    assert not at.exception
    button_labels = [b.label for b in at.button]
    assert any("Limpar Cache e Re-analisar Perfil" in label for label in button_labels)


def test_limpar_cache_button_clears_cached_profile_before_reanalyzing(monkeypatch):
    """O botão 'Limpar Cache e Re-analisar Perfil' deve apagar o cache do
    perfil antes de disparar o pipeline, garantindo que registros antigos ou
    corrompidos (ex.: fa_fiel_0) não sobrevivam à re-análise. A raspagem (mesmo
    em modo demo) reescreve o cache em thread de background logo em seguida,
    então o que a UI garante é a ORDEM (limpar antes de iniciar), verificada
    aqui via monkeypatch em vez de inspecionar o cache.db pós-clique (que teria
    corrida com a thread de background). Usa `src.database` diretamente (não
    `import app`): importar `app` executa `main()` em modo bare (fora de um
    ScriptRunContext real), o que deixa lixo de estado de formulário do
    Streamlit entre testes e quebra AppTest.from_file() chamado depois."""
    from src import database

    calls = []
    monkeypatch.setattr(database, "clear_profile_cache", lambda username: calls.append(username))

    username = f"perfil_limpar_cache_{uuid.uuid4().hex}"

    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input(key="username_input").set_value(username)
    at.toggle(key="demo_mode_toggle").set_value(True)
    limpar_button = next(b for b in at.button if b.label == "Limpar Cache e Re-analisar Perfil")
    limpar_button.click().run()

    assert not at.exception
    assert calls == [username]

    max_reruns = 50
    for _ in range(max_reruns):
        assert not at.exception
        status = at.session_state["pipeline_state"].get("status")
        if status != "rodando":
            break
        at.run()

    assert at.session_state["pipeline_state"]["status"] == "concluido"


def test_app_demo_pipeline_runs_end_to_end_without_gemini_api_key(monkeypatch):
    """Sem GEMINI_API_KEY no ambiente, o Modo Demonstração continua funcionando
    fim-a-fim: RealGeminiClient() levanta RuntimeError, app.py deve capturar isso
    e seguir com gemini_client=None, sem exceção não tratada."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    at = AppTest.from_file(APP_PATH)
    at.run()
    assert not at.exception

    at.text_input(key="username_input").set_value("perfil_demo_teste")
    at.toggle(key="demo_mode_toggle").set_value(True)
    at.button[0].click().run()

    # Pipeline roda em thread de background; drena o polling síncrono do AppTest
    # até concluir (ou falhar), sem nunca bloquear além do necessário para o teste.
    max_reruns = 50
    for _ in range(max_reruns):
        assert not at.exception
        status = at.session_state["pipeline_state"].get("status")
        if status != "rodando":
            break
        at.run()

    assert not at.exception
    assert at.session_state["pipeline_state"]["status"] == "concluido"
    assert at.session_state["pipeline_state"]["gemini_configurado"] is False


def test_run_pipeline_detects_sponsored_posts_in_demo_mode():
    """RF-09: em Modo Demonstração, ao menos uma publi de exemplo deve ser
    detectada nas legendas geradas localmente (prova de que o pipeline real
    de detecção está conectado, não um placeholder fixo)."""
    import app

    # Username único: scrape_profile usa o cache SQLite compartilhado
    # (database.DB_PATH) por padrão, e um username fixo colidiria com cache
    # de execuções anteriores deste mesmo teste.
    username = f"perfil_demo_publis_{uuid.uuid4().hex}"
    state = {}
    app._run_pipeline(username, 90, True, None, state)

    assert state["status"] == "concluido"
    publis = state["analysis"]["publis"]
    assert len(publis) >= 1
    assert all("termos" in item and item["termos"] for item in publis)
    assert all(item["link"] is None or item["link"].startswith("https://www.instagram.com/p/") for item in publis)


def test_run_pipeline_exposes_genero_pct_in_demo_mode():
    import app

    username = f"perfil_demo_genero_{uuid.uuid4().hex}"
    state = {}
    app._run_pipeline(username, 90, True, None, state)

    assert state["status"] == "concluido"
    genero_pct = state["analysis"]["demografia"]["genero_pct"]
    assert set(genero_pct.keys()) == {"feminino", "masculino", "indeterminado"}
    assert abs(sum(genero_pct.values()) - 1.0) < 1e-9


def test_run_pipeline_returns_proportional_region_breakdown_and_handles_prefixed_gender_in_real_mode(monkeypatch):
    """RF: perfis femininos de moda/lifestyle devem classificar a amostragem
    como predominantemente feminina (>80%) mesmo com @handles prefixados
    ('style_by_...'), e a lista de regiões deve vir proporcional
    ('SP (40%), RJ (25%)...') em vez de um único estado ou lista sem peso."""
    import app

    def comentario(username, texto):
        return {"username": username, "texto": texto, "respondido": False}

    fake_cached = {
        "profile": {"followers_count": 20000},
        "posts": [
            {
                "post_id": "1",
                "likes_count": 100,
                "comments_count": 10,
                "raw": {
                    "shortcode": "sc1",
                    "caption": "look de hoje",
                    "comments": [
                        comentario("style_by_maria", "chama no (11) 91234-5678"),
                        comentario("its_ana_oficial", "chama no (11) 98765-4321"),
                        comentario("camila.moda92", "moro no Rio de Janeiro"),
                        comentario("eu_juliana_looks", "sou de Minas Gerais"),
                        comentario("look.by.patricia", "Lindo"),
                    ],
                },
            },
        ],
    }

    monkeypatch.setattr(app.scraper, "scrape_profile", lambda *args, **kwargs: fake_cached)

    state = {}
    app._run_pipeline("perfil_moda_teste", 90, False, None, state)

    assert state["status"] == "concluido"
    analysis = state["analysis"]
    demografia = analysis["demografia"]

    # >80% feminino mesmo com handles prefixados (style_by_, its_..._oficial, eu_..._looks, look.by.)
    assert demografia["genero_predominante"] == "feminino"
    assert demografia["genero_pct"]["feminino"] > 0.8

    # lista proporcional (não um único estado): 2 detecções de SP, 1 de RJ, 1 de MG
    assert demografia["regioes"] == ["SP (50%)", "RJ (25%)", "MG (25%)"]


def test_run_pipeline_filters_posts_outside_window_and_infers_gender_from_handle_in_real_mode(monkeypatch):
    """Prova de integração do reparo de ancoragem na realidade física: em modo
    real (demo_mode=False), posts fora da janela selecionada não devem
    contribuir para as métricas, e o gênero deve ser inferido a partir do
    @handle do comentarista quando não há 'nome' explícito — comentários
    reais (via instaloader_fetch_fn) só trazem 'username', nunca 'nome'."""
    import datetime as dt

    import app

    recent_date = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=5)).isoformat()
    old_date = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=200)).isoformat()

    fake_cached = {
        "profile": {"followers_count": 10000},
        "posts": [
            {
                "post_id": "1",
                "likes_count": 100,
                "comments_count": 1,
                "raw": {
                    "shortcode": "sc1",
                    "caption": "look de hoje",
                    "published_at": recent_date,
                    "comments": [{"username": "ana_silva92", "texto": "Quanto custa?", "respondido": False}],
                },
            },
            {
                "post_id": "2",
                "likes_count": 999,
                "comments_count": 5,
                "raw": {
                    "shortcode": "sc2",
                    "caption": "look antigo",
                    "published_at": old_date,
                    "comments": [{"username": "joao99", "texto": "Top", "respondido": False}],
                },
            },
        ],
    }

    monkeypatch.setattr(app.scraper, "scrape_profile", lambda *args, **kwargs: fake_cached)

    state = {}
    app._run_pipeline("perfil_real_teste", 90, False, None, state)

    assert state["status"] == "concluido"
    analysis = state["analysis"]
    # post de 200 dias atrás está fora da janela de 90 dias -> não conta nas métricas
    assert analysis["comentarios_analisados"]["total"] == 1
    # gênero inferido a partir do handle 'ana_silva92' -> 'ana' -> feminino
    assert analysis["demografia"]["genero_predominante"] == "feminino"


def test_run_pipeline_e2e_with_simulated_real_instagram_profile(monkeypatch):
    """E2E: simula a API real do Instaloader (sem rede) e roda o pipeline
    completo (demo_mode=False) fim-a-fim — instaloader_fetch_fn -> cache SQLite
    -> app._run_pipeline -> analysis. Prova que os dois reparos (comentários
    reais + janela por data de publicação) se conectam corretamente de ponta
    a ponta, não só isoladamente por módulo."""
    import datetime as dt

    import app
    from src import scraper

    class FakeOwner:
        def __init__(self, username):
            self.username = username

    class FakeComment:
        def __init__(self, owner_username, text):
            self.owner = FakeOwner(owner_username)
            self.text = text
            self.answers = []

    class FakePost:
        def __init__(self, mediaid, shortcode, caption, likes, comments_count, date_utc, comments):
            self.mediaid = mediaid
            self.shortcode = shortcode
            self.caption = caption
            self.likes = likes
            self.comments = comments_count
            self.date_utc = date_utc
            self._comments = comments

        def get_comments(self):
            return iter(self._comments)

    recent = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=5)
    old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=200)

    recent_comments = [
        FakeComment("camila_style23", "Qual o preço desse vestido?"),
        FakeComment("fernanda.looks", "Vocês têm no tamanho M?"),
        FakeComment("pedro99_", "Lindo"),
    ]
    old_comments = [FakeComment("joao_antigo", "Top")]

    class FakeProfile:
        username = "perfil_real_e2e"
        biography = "bio real"
        followers = 8000

        @staticmethod
        def get_posts():
            return iter(
                [
                    FakePost(1, "recente", "look novo #publi @marca_parceira", 300, 3, recent, recent_comments),
                    FakePost(2, "antigo", "look antigo", 50, 1, old, old_comments),
                ]
            )

    class FakeContext:
        pass

    class FakeInstaloader:
        def __init__(self):
            self.context = FakeContext()

        def load_session_from_file(self, username, filename):
            pass

    monkeypatch.setattr(scraper.instaloader, "Instaloader", FakeInstaloader)
    monkeypatch.setattr(
        scraper.instaloader.Profile,
        "from_username",
        staticmethod(lambda context, username: FakeProfile()),
    )

    username = f"perfil_real_e2e_{uuid.uuid4().hex}"
    state = {}
    app._run_pipeline(username, 90, False, None, state)

    assert state["status"] == "concluido"
    analysis = state["analysis"]

    # post de 200 dias atrás está fora da janela de 90 dias -> só o post recente conta
    assert analysis["comentarios_analisados"]["total"] == 3
    # 2 comentaristas femininas ("camila", "fernanda") vs 1 masculino ("pedro") -> feminino
    assert analysis["demografia"]["genero_predominante"] == "feminino"
    assert analysis["demografia"]["genero_pct"]["feminino"] > 0.5
    # TER calculada só sobre o post dentro da janela (300 likes + 3 comments / 8000 seguidores)
    assert analysis["engagement_rate"] == (300 + 3) / 8000
    # publi detectada na legenda do post recente (RF-09)
    assert len(analysis["publis"]) == 1
    assert analysis["publis"][0]["link"] == "https://www.instagram.com/p/recente/"


def test_erro_coleta_indisponivel_shows_exact_required_message():
    """A mensagem de erro de coleta real deve ser exatamente a exigida — nunca
    deve sugerir 'Modo demonstração' como alternativa a dados reais."""
    import app

    assert app.COLETA_INDISPONIVEL_MSG == (
        "Falha na coleta do Instagram. Verifique o arquivo de sessão local ou "
        "aguarde alguns minutos antes de tentar novamente."
    )
    assert "demonstra" not in app.COLETA_INDISPONIVEL_MSG.lower()


def test_run_pipeline_sets_erro_coleta_indisponivel_status(monkeypatch):
    """scraper.ScraperUnavailableError deve virar um status tratado na UI, nunca
    uma exceção crua propagada pela thread de background."""
    import app

    def fake_scrape_profile(*args, **kwargs):
        raise app.scraper.ScraperUnavailableError("sem rede e sem cache neste teste")

    monkeypatch.setattr(app.scraper, "scrape_profile", fake_scrape_profile)

    state = {}
    app._run_pipeline("perfil_sem_cache", 90, False, None, state)

    assert state["status"] == "erro_coleta_indisponivel"
    assert "erro" in state
