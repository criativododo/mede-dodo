# Pacing Seguro & Progresso Dinâmico — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar um rate controller conservador e observável (não um mecanismo de evasão/"anti-ban humanizado") para a coleta real do Instagram, e um painel de progresso dinâmico no Streamlit com mensagens contextuais, ETA calculado e um botão "Ver Relatório" que libera a exportação — sem quebrar nenhum dos 197 testes existentes, sem tocar `src/exporter.py`, e sem alterar `RealGeminiClient`/`DemoGeminiClient`/seus retries 429/503.

**Architecture:** Um novo módulo `src/rate_controller.py` expõe `RateController` (priors por tipo de operação, `next_wait`, `observe_response` que levanta `SafeStop` monotonicamente em 429/403/challenge, `pause_until_safe_signal`) e `NullRateController` (no-op, usado como default para não afetar os ~15 testes existentes de `instaloader_fetch_fn` que não injetam controller). `src/scraper.py` passa a aceitar injeção opcional de `rate_controller`/`on_progress` em `instaloader_fetch_fn` (pacing por post + detecção de 429/checkpoint durante a paginação) e deixa `SafeStop` propagar por `scrape_profile` sem cair no fallback de cache genérico (stop explícito, não degradação silenciosa). `app.py` liga esse controller apenas no caminho real (não-demo, que segue sem jitter), calcula ETA a partir de uma média móvel observada (não um valor fixo) e exibe mensagens humanizadas + ETA na barra de progresso existente; a exportação HTML/PDF/JSON passa a ficar atrás de um botão "Ver Relatório" (o resto do dashboard continua aparecendo imediatamente ao concluir, porque testes `AppTest` já existentes dependem disso).

**Tech Stack:** Python 3.14, Streamlit 1.61 (`streamlit.testing.v1.AppTest` para testes de UI), pytest, Instaloader 4.15.3 (sem libs de terceiros para pacing/retry — tudo implementado à mão, como já é o padrão do repo).

**Spec:** `/Users/danielperrut/0. PROJETO/mede-dodo/SPRINT-002/FINDER-003.md`

## Global Constraints

- Nunca implementar rotação de User-Agent, spoofing de `navigator.webdriver`, TLS fingerprint, proxies rotativos, pool de contas, ou qualquer "simulação humana" para evadir detecção (FINDER-003 §4.4/§14 — explicitamente não normativo/proibido).
- O controlador é conservador e monotônico: só reduz/pausa diante de sinal de bloqueio; nunca aumenta volume, muda identidade ou "fura" a barreira (FINDER-003 §4.1).
- Modo demonstração nunca tem rede nem jitter (FINDER-003 §2.2) — o novo `RateController` só é ligado no caminho real.
- `src/exporter.py` não pode ser modificado.
- `RealGeminiClient`, `DemoGeminiClient` e o retry 429/503 em `src/gemini_analyzer.py` (`_RETRYABLE_ERROR_CODES`, `_is_retryable_gemini_error`) não podem ser modificados.
- Ao final de cada task, `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && .venv/bin/python -m pytest tests/ -q` deve mostrar 0 falhas e um número de testes **maior ou igual** ao baseline de 197.
- Mensagem mínima de segurança obrigatória (texto exato, FINDER-003 §6): "A coleta foi pausada para proteger a sessão. Dados parciais foram salvos. Verifique a sessão/permissões e tente novamente mais tarde; nenhum mecanismo de contorno foi executado."
- Escopo deliberadamente EXCLUÍDO desta entrega (não pedido nos 3 itens do escopo, evita overengineering): persistência de checkpoint/resume (FINDER-003 §6.1, JSON com `audit_id`), API oficial Meta/OAuth (§3.3), observabilidade/métricas agregadas (§8). `pause_until_safe_signal` é implementado e testado como capacidade do controller, mas não é acionado automaticamente em nenhum fluxo — não há resume.

---

### Task 1: `RateController` — núcleo de pacing conservador

**Files:**
- Create: `src/rate_controller.py`
- Test: `tests/test_rate_controller.py`

**Interfaces:**
- Produces: `SafeStop(Exception)` com atributos `.reason` (str) e `.status` (str, default `"paused"`); `str(SafeStop(...))` é sempre igual a `rate_controller.SAFETY_MESSAGE`.
- Produces: `SAFETY_MESSAGE` (str) — texto exato do FINDER-003 §6.
- Produces: `OPERATION_PRIORS` (dict `str -> (float, float)`) com chaves `"resolucao_inicial"` (4.0, 7.0), `"secao_post_metadata"` (2.0, 5.0), `"lote_posts"` (3.0, 6.0), `"pausa_protecao"` (30.0, 60.0).
- Produces: `RateController(priors=None, sleep_fn=time.sleep, random_fn=random.uniform, on_pause=None)` com métodos `.next_wait(operation: str) -> float`, `.observe_response(status_code=None, challenge=False) -> None`, `.pause_until_safe_signal() -> float`, propriedade `.is_paused -> bool`.
- Produces: `NullRateController()` (mesmos métodos, sempre no-op, `next_wait`/`pause_until_safe_signal` retornam `0.0` sem chamar `sleep_fn`, `observe_response` nunca levanta) e a instância singleton `NULL_RATE_CONTROLLER`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_rate_controller.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from src import rate_controller


def test_next_wait_sleeps_within_secao_post_metadata_bounds():
    sleep_calls = []
    controller = rate_controller.RateController(
        sleep_fn=lambda s: sleep_calls.append(s), random_fn=lambda lo, hi: (lo + hi) / 2
    )

    delay = controller.next_wait("secao_post_metadata")

    assert sleep_calls == [delay]
    assert 2.0 <= delay <= 5.0


def test_next_wait_sleeps_within_lote_posts_bounds():
    controller = rate_controller.RateController(sleep_fn=lambda s: None, random_fn=lambda lo, hi: lo)

    delay = controller.next_wait("lote_posts")

    assert delay == 3.0


def test_next_wait_sleeps_within_resolucao_inicial_bounds():
    controller = rate_controller.RateController(sleep_fn=lambda s: None, random_fn=lambda lo, hi: hi)

    delay = controller.next_wait("resolucao_inicial")

    assert delay == 7.0


def test_next_wait_raises_key_error_for_unknown_operation():
    controller = rate_controller.RateController(sleep_fn=lambda s: None)

    with pytest.raises(KeyError):
        controller.next_wait("operacao_inexistente")


def test_pause_until_safe_signal_sleeps_within_pausa_protecao_bounds():
    sleep_calls = []
    controller = rate_controller.RateController(
        sleep_fn=lambda s: sleep_calls.append(s), random_fn=lambda lo, hi: lo
    )

    delay = controller.pause_until_safe_signal()

    assert sleep_calls == [30.0]
    assert delay == 30.0


def test_observe_response_does_not_raise_on_success_status():
    controller = rate_controller.RateController(sleep_fn=lambda s: None)

    controller.observe_response(status_code=200)

    assert controller.is_paused is False


def test_observe_response_raises_safe_stop_on_429_and_pauses():
    controller = rate_controller.RateController(sleep_fn=lambda s: None)

    with pytest.raises(rate_controller.SafeStop) as excinfo:
        controller.observe_response(status_code=429)

    assert excinfo.value.reason == "http_429"
    assert str(excinfo.value) == rate_controller.SAFETY_MESSAGE
    assert controller.is_paused is True


def test_observe_response_raises_safe_stop_on_challenge():
    controller = rate_controller.RateController(sleep_fn=lambda s: None)

    with pytest.raises(rate_controller.SafeStop) as excinfo:
        controller.observe_response(challenge=True)

    assert excinfo.value.reason == "challenge"


def test_observe_response_calls_on_pause_callback_exactly_once():
    calls = []
    controller = rate_controller.RateController(
        sleep_fn=lambda s: None, on_pause=lambda **kwargs: calls.append(kwargs)
    )

    with pytest.raises(rate_controller.SafeStop):
        controller.observe_response(status_code=403)

    assert calls == [{"status_code": 403, "challenge": False}]


def test_controller_stays_paused_monotonically_after_safe_stop():
    controller = rate_controller.RateController(sleep_fn=lambda s: None)
    with pytest.raises(rate_controller.SafeStop):
        controller.observe_response(status_code=429)

    with pytest.raises(rate_controller.SafeStop) as excinfo:
        controller.next_wait("lote_posts")

    assert excinfo.value.reason == "controller_paused"


def test_null_rate_controller_never_sleeps_and_never_raises():
    controller = rate_controller.NULL_RATE_CONTROLLER

    assert controller.next_wait("secao_post_metadata") == 0.0
    assert controller.pause_until_safe_signal() == 0.0
    controller.observe_response(status_code=429, challenge=True)
    assert controller.is_paused is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && .venv/bin/python -m pytest tests/test_rate_controller.py -v`
Expected: FAIL/ERROR — `ModuleNotFoundError: No module named 'src.rate_controller'`.

- [ ] **Step 3: Write the implementation**

```python
# src/rate_controller.py
import random
import time

SAFETY_MESSAGE = (
    "A coleta foi pausada para proteger a sessão. Dados parciais foram salvos. "
    "Verifique a sessão/permissões e tente novamente mais tarde; nenhum "
    "mecanismo de contorno foi executado."
)

# Priors iniciais do controlador de atraso (FINDER-003 §4.2). São ponto de
# partida conservador, não garantia da plataforma — não existem para simular
# comportamento humano, existem para respeitar capacidade/ToS (§4.1).
OPERATION_PRIORS = {
    "resolucao_inicial": (4.0, 7.0),
    "secao_post_metadata": (2.0, 5.0),
    "lote_posts": (3.0, 6.0),
    "pausa_protecao": (30.0, 60.0),
}


class SafeStop(Exception):
    """Levantada quando o controller detecta 429/403/challenge/checkpoint, ou
    quando é chamado de novo depois de já ter pausado (monotônico: nunca
    volta a liberar chamadas sozinho — FINDER-003 §4.1)."""

    def __init__(self, reason, status="paused"):
        self.reason = reason
        self.status = status
        super().__init__(SAFETY_MESSAGE)


class RateController:
    def __init__(self, priors=None, sleep_fn=time.sleep, random_fn=random.uniform, on_pause=None):
        self._priors = dict(priors or OPERATION_PRIORS)
        self._sleep_fn = sleep_fn
        self._random_fn = random_fn
        self._on_pause = on_pause
        self._paused = False

    @property
    def is_paused(self):
        return self._paused

    def next_wait(self, operation):
        if self._paused:
            raise SafeStop(reason="controller_paused")
        min_seconds, max_seconds = self._priors[operation]
        delay = self._random_fn(min_seconds, max_seconds)
        self._sleep_fn(delay)
        return delay

    def observe_response(self, status_code=None, challenge=False):
        if not challenge and status_code not in (429, 403):
            return
        self._paused = True
        reason = "challenge" if challenge else f"http_{status_code}"
        if self._on_pause is not None:
            self._on_pause(status_code=status_code, challenge=challenge)
        raise SafeStop(reason=reason)

    def pause_until_safe_signal(self):
        min_seconds, max_seconds = self._priors["pausa_protecao"]
        delay = self._random_fn(min_seconds, max_seconds)
        self._sleep_fn(delay)
        return delay


class NullRateController:
    """No-op: usado como default em código que não recebeu um RateController
    explícito (ex.: os testes existentes de instaloader_fetch_fn, que não
    devem ganhar nenhum sleep real ao herdar este parâmetro novo)."""

    is_paused = False

    def next_wait(self, operation):
        return 0.0

    def observe_response(self, status_code=None, challenge=False):
        return None

    def pause_until_safe_signal(self):
        return 0.0


NULL_RATE_CONTROLLER = NullRateController()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && .venv/bin/python -m pytest tests/test_rate_controller.py -v`
Expected: PASS — 12 testes verdes.

- [ ] **Step 5: Commit**

```bash
cd "/Users/danielperrut/0. PROJETO/mede-dodo"
git add src/rate_controller.py tests/test_rate_controller.py
git commit -m "feat(rate-controller): controlador de pacing conservador com SafeStop em 429/403/challenge"
```

---

### Task 2: `SafeStop` propaga por `scrape_profile` sem cair no fallback de cache genérico

**Files:**
- Modify: `src/scraper.py:1-11` (imports), `src/scraper.py:338-347` (bloco `try/except` de `fetch_fn`)
- Test: `tests/test_scraper.py`

**Interfaces:**
- Consumes: `rate_controller.SafeStop` (Task 1).
- Produces: nenhuma interface nova — comportamento de `scrape_profile` para exceções que NÃO são `SafeStop` continua idêntico.

- [ ] **Step 1: Write the failing test**

Adicionar ao final de `tests/test_scraper.py` (o arquivo já importa `os`, `sys`, `tempfile`, `datetime`, `instaloader`, `database`, `scraper` no topo — adicionar também `from src import rate_controller`):

```python
def test_scrape_profile_reraises_safe_stop_without_falling_back_to_cache_even_when_cache_exists():
    db_path = make_temp_db()
    try:
        database.save_profile_data(
            "perfil_com_cache_mas_safe_stop",
            posts=[{"post_id": "1", "raw": {}, "likes_count": 5, "comments_count": 1}],
            bio="bio antiga",
            followers_count=300,
            db_path=db_path,
        )

        def fetch_fn_safe_stop(username, cookies):
            raise rate_controller.SafeStop(reason="http_429")

        try:
            scraper.scrape_profile(
                "perfil_com_cache_mas_safe_stop",
                window_days=0,
                fetch_fn=fetch_fn_safe_stop,
                throttle_fn=lambda: None,
                db_path=db_path,
            )
            assert False, "esperava SafeStop"
        except rate_controller.SafeStop as exc:
            assert exc.reason == "http_429"
    finally:
        os.unlink(db_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && .venv/bin/python -m pytest tests/test_scraper.py::test_scrape_profile_reraises_safe_stop_without_falling_back_to_cache_even_when_cache_exists -v`
Expected: FAIL — o `except Exception` genérico engole o `SafeStop` e devolve o cache antigo silenciosamente (o teste falha no `assert False, "esperava SafeStop"`).

- [ ] **Step 3: Implement**

Em `src/scraper.py`, trocar `from src import database` (topo do arquivo) por:

```python
from src import database
from src import rate_controller as rate_controller_module
```

(usa alias porque o Task 3 introduz um parâmetro também chamado `rate_controller` em `instaloader_fetch_fn`, que colidiria com o nome do módulo).

E em `scrape_profile`, adicionar um `except` específico ANTES do genérico existente:

```python
    throttle_fn()
    try:
        raw = fetch_fn(username, cookies)
    except rate_controller_module.SafeStop:
        # 429/403/challenge: parar de forma explícita, não degradar
        # silenciosamente para um cache que pode estar desatualizado
        # (FINDER-003 §4.1/§6 — comportamento observável, não evasivo).
        raise
    except Exception as exc:
        fallback = database.get_cached_data(username, window_days=None, source=source, db_path=db_path)
        if fallback is not None:
            return fallback
        raise ScraperUnavailableError(
            f"Falha ao coletar dados de '{username}' e nenhum cache disponível: {exc}"
        ) from exc
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && .venv/bin/python -m pytest tests/test_scraper.py -v`
Expected: PASS — todos os testes de `test_scraper.py`, incluindo os ~19 pré-existentes e o novo.

- [ ] **Step 5: Commit**

```bash
cd "/Users/danielperrut/0. PROJETO/mede-dodo"
git add src/scraper.py tests/test_scraper.py
git commit -m "fix(scraper): SafeStop propaga sem cair no fallback de cache genérico"
```

---

### Task 3: Pacing por post + detecção de 429/checkpoint em `instaloader_fetch_fn`

**Files:**
- Modify: `src/scraper.py:20` (novas constantes de assinatura), `src/scraper.py:215-312` (`instaloader_fetch_fn`)
- Test: `tests/test_scraper.py`

**Interfaces:**
- Consumes: `rate_controller_module.RateController`, `rate_controller_module.NULL_RATE_CONTROLLER`, `rate_controller_module.SafeStop` (Task 1, via o alias criado no Task 2); `instaloader.exceptions.TooManyRequestsException`, `instaloader.exceptions.ConnectionException` (já usadas no arquivo).
- Produces: nova assinatura pública `instaloader_fetch_fn(username, cookies=None, rate_controller=None, on_progress=None)`. `on_progress`, quando fornecido, é chamado como `on_progress(processed: int, total: int)` uma vez por post efetivamente coletado (`processed` cumulativo, `total` = `min(profile.mediacount or MAX_POSTS_SAFETY_CAP, MAX_POSTS_SAFETY_CAP)`, estável durante toda a chamada).

- [ ] **Step 1: Write the failing tests**

Adicionar a `tests/test_scraper.py` (usa as classes `FakePost`/`FakeProfile`/`_patch_fake_profile`/`FakeInstaloader` já existentes no arquivo, e `from src import rate_controller` já importado no Task 2 — adicionar também `import pytest` no topo se ainda não existir):

```python
def test_instaloader_fetch_fn_calls_rate_controller_and_progress_callback_per_post(monkeypatch):
    class FakeProfile:
        username = "perfil_fake"
        biography = "bio fake"
        followers = 1234
        mediacount = 2

        @staticmethod
        def get_posts():
            recent = datetime.now(timezone.utc) - timedelta(days=1)
            return iter(
                [
                    FakePost(1, "a", "legenda1", 10, 0, recent),
                    FakePost(2, "b", "legenda2", 20, 0, recent),
                ]
            )

    _patch_fake_profile(monkeypatch, FakeProfile())

    wait_calls = []

    class TrackingController:
        def next_wait(self, operation):
            wait_calls.append(operation)

        def observe_response(self, status_code=None, challenge=False):
            pass

    progress_calls = []

    result = scraper.instaloader_fetch_fn(
        "perfil_fake",
        cookies=None,
        rate_controller=TrackingController(),
        on_progress=lambda processed, total: progress_calls.append((processed, total)),
    )

    assert wait_calls == ["resolucao_inicial", "secao_post_metadata", "secao_post_metadata"]
    assert progress_calls == [(1, 2), (2, 2)]
    assert len(result["posts"]) == 2


def test_instaloader_fetch_fn_defaults_to_null_rate_controller_without_slowing_down(monkeypatch):
    class FakeProfile:
        username = "perfil_fake"
        biography = "bio fake"
        followers = 1234

        @staticmethod
        def get_posts():
            recent = datetime.now(timezone.utc) - timedelta(days=1)
            return iter([FakePost(1, "a", "legenda1", 10, 0, recent)])

    _patch_fake_profile(monkeypatch, FakeProfile())

    result = scraper.instaloader_fetch_fn("perfil_fake", cookies=None)

    assert len(result["posts"]) == 1


def test_instaloader_fetch_fn_raises_safe_stop_on_too_many_requests_during_pagination(monkeypatch):
    class FakeProfile:
        username = "perfil_fake"
        biography = "bio fake"
        followers = 1234

        @staticmethod
        def get_posts():
            recent = datetime.now(timezone.utc) - timedelta(days=1)

            def _gen():
                yield FakePost(1, "a", "legenda1", 10, 0, recent)
                raise instaloader.exceptions.TooManyRequestsException("429 Too Many Requests")

            return _gen()

    _patch_fake_profile(monkeypatch, FakeProfile())
    controller = rate_controller.RateController(sleep_fn=lambda s: None)

    with pytest.raises(rate_controller.SafeStop) as excinfo:
        scraper.instaloader_fetch_fn("perfil_fake", cookies=None, rate_controller=controller)

    assert excinfo.value.reason == "http_429"
    assert controller.is_paused is True


def test_instaloader_fetch_fn_raises_safe_stop_on_checkpoint_signal_during_pagination(monkeypatch):
    class FakeProfile:
        username = "perfil_fake"
        biography = "bio fake"
        followers = 1234

        @staticmethod
        def get_posts():
            def _gen():
                if False:
                    yield None
                raise instaloader.exceptions.ConnectionException("checkpoint_required")

            return _gen()

    _patch_fake_profile(monkeypatch, FakeProfile())
    controller = rate_controller.RateController(sleep_fn=lambda s: None)

    with pytest.raises(rate_controller.SafeStop) as excinfo:
        scraper.instaloader_fetch_fn("perfil_fake", cookies=None, rate_controller=controller)

    assert excinfo.value.reason == "challenge"


def test_instaloader_fetch_fn_raises_safe_stop_on_too_many_requests_resolving_profile(monkeypatch):
    monkeypatch.setattr(scraper.instaloader, "Instaloader", FakeInstaloader)

    def _raise_too_many_requests(context, username):
        raise instaloader.exceptions.TooManyRequestsException("429 Too Many Requests")

    monkeypatch.setattr(
        scraper.instaloader.Profile, "from_username", staticmethod(_raise_too_many_requests)
    )
    controller = rate_controller.RateController(sleep_fn=lambda s: None)

    with pytest.raises(rate_controller.SafeStop) as excinfo:
        scraper.instaloader_fetch_fn("perfil_fake", cookies=None, rate_controller=controller)

    assert excinfo.value.reason == "http_429"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && .venv/bin/python -m pytest tests/test_scraper.py -k "rate_controller_and_progress or safe_stop or null_rate_controller" -v`
Expected: FAIL — `instaloader_fetch_fn() got an unexpected keyword argument 'rate_controller'`.

- [ ] **Step 3: Implement**

Em `src/scraper.py`, adicionar perto de `_DELETED_SCHEMA_SIGNATURE` (linha ~20):

```python
# Sinais textuais de checkpoint/challenge do Instagram (Instaloader não expõe
# uma exceção dedicada para isso — surge como ConnectionException com uma
# dessas strings na mensagem, conforme troubleshooting.html da lib, ref. [1]
# no FINDER-003). Pausa e pede ação humana — nunca contorna (FINDER-003 §4.4).
_CHECKPOINT_SIGNATURES = ("checkpoint_required", "challenge_required")


def _is_checkpoint_signal(exc_text):
    lowered = exc_text.lower()
    return any(signature in lowered for signature in _CHECKPOINT_SIGNATURES)
```

Substituir a função `instaloader_fetch_fn` inteira (linhas 215-312) por:

```python
def instaloader_fetch_fn(username, cookies=None, rate_controller=None, on_progress=None):
    # cookies, se fornecido, é o caminho de um arquivo de sessão local salvo
    # previamente via Instaloader.save_session_to_file (login manual único, fora
    # deste código) — evita reautenticar a cada coleta. Quando não fornecido,
    # tenta autodetectar qualquer sessão salva em SESSION_DIR.
    active_controller = rate_controller or rate_controller_module.NULL_RATE_CONTROLLER

    loader = instaloader.Instaloader()
    if cookies:
        session_username = _session_username_from_path(cookies) or username
        loader.load_session_from_file(session_username, filename=cookies)
    else:
        load_any_available_session(loader)

    active_controller.next_wait("resolucao_inicial")

    try:
        profile = instaloader.Profile.from_username(loader.context, username)
    except instaloader.exceptions.TooManyRequestsException as exc:
        _logger.error(
            "Coleta de '%s' interrompida: Instagram sinalizou 429 (rate limit) ao "
            "resolver o perfil.", username,
        )
        active_controller.observe_response(status_code=429)
        raise
    except (
        instaloader.exceptions.ConnectionException,
        instaloader.exceptions.QueryReturnedBadRequestException,
    ) as exc:
        # QueryReturnedBadRequestException (HTTP 400) é levantada direto por
        # InstaloaderContext.get_json() e NÃO é subclasse de ConnectionException
        # (confirmado lendo instaloadercontext.py: o except que faz retry/wrap só
        # cobre ConnectionException) — é essa a exceção real que o bug de schema
        # removido do Instagram produz. Reproduzido ao vivo contra @silviabraz em
        # 2026-08-12: um `except ConnectionException` sozinho nunca capturava esse
        # erro, e a coleta caía no `except Exception` genérico logo abaixo, pulando
        # o fallback via topsearch por completo.
        if _DELETED_SCHEMA_SIGNATURE in str(exc).lower():
            fallback_profile = _resolve_profile_via_topsearch(loader, username)
            if fallback_profile is None:
                _logger.error(
                    "Coleta de '%s' falhou: Instagram devolveu um erro de schema removido "
                    "no endpoint web_profile_info — bug atual no backend do Instagram, não "
                    "é falha de sessão/autenticação local. Fallback via topsearch também "
                    "não resolveu o perfil. Detalhe: %s", username, exc,
                )
                raise ScraperUnavailableError(
                    f"Instagram recusou a resolução do perfil '{username}' com um erro de "
                    f"schema removido no endpoint web_profile_info (bug atual no backend "
                    f"do Instagram, não é falha de sessão local), e o fallback via "
                    f"topsearch também não conseguiu resolver o perfil: {exc}"
                ) from exc
            _logger.warning(
                "Coleta de '%s': web_profile_info devolveu o bug de schema removido do "
                "Instagram, mas o fallback via topsearch resolveu o perfil normalmente.",
                username,
            )
            profile = fallback_profile
        elif _is_checkpoint_signal(str(exc)):
            _logger.error(
                "Coleta de '%s' interrompida: sinal de checkpoint/challenge do Instagram "
                "ao resolver o perfil.", username,
            )
            active_controller.observe_response(challenge=True)
            raise
        else:
            _logger.error("Coleta de '%s' falhou ao resolver o perfil (conexão): %s", username, exc)
            raise
    except Exception as exc:
        _logger.error("Coleta de '%s' falhou de forma inesperada ao resolver o perfil: %s", username, exc)
        raise
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_WINDOW_DAYS)
    total_hint = min(getattr(profile, "mediacount", None) or MAX_POSTS_SAFETY_CAP, MAX_POSTS_SAFETY_CAP)

    posts = []
    # get_posts() geralmente retorna do mais recente para o mais antigo, mas o
    # Instagram permite fixar até 3 posts no topo do grid fora dessa ordem —
    # inclusive posts bem antigos (reproduzido ao vivo em @silviabraz: os 3
    # primeiros posts vinham de 2021/2024/2025, escondendo posts reais de agosto de
    # 2026 logo em seguida). Por isso só passamos a "confiar" na ordem cronológica
    # (e parar no primeiro post fora da janela) depois do primeiro post que já caiu
    # dentro da janela — antes disso, um post antigo pode ser só um fixado, não o
    # fim do conteúdo recente. Sem posts fixados, o comportamento é idêntico ao
    # anterior (para no primeiro post fora da janela). O teto de segurança
    # (MAX_POSTS_SAFETY_CAP) segue limitando o pior caso (perfil sem nenhum post
    # dentro da janela).
    past_pinned_zone = False
    posts_iterator = iter(profile.get_posts())
    while True:
        try:
            post = next(posts_iterator)
        except StopIteration:
            break
        except instaloader.exceptions.TooManyRequestsException:
            _logger.error(
                "Coleta de '%s' interrompida durante a paginação de posts: 429 "
                "(rate limit).", username,
            )
            active_controller.observe_response(status_code=429)
            raise
        except instaloader.exceptions.ConnectionException as exc:
            if _is_checkpoint_signal(str(exc)):
                _logger.error(
                    "Coleta de '%s' interrompida durante a paginação de posts: sinal "
                    "de checkpoint/challenge do Instagram.", username,
                )
                active_controller.observe_response(challenge=True)
                raise
            raise

        if len(posts) >= MAX_POSTS_SAFETY_CAP:
            break

        post_date = _post_date_utc(post)
        if past_pinned_zone and post_date < cutoff:
            break
        if post_date < cutoff:
            continue
        past_pinned_zone = True

        active_controller.next_wait("secao_post_metadata")
        posts.append(
            {
                "post_id": str(post.mediaid),
                "raw": {
                    "shortcode": post.shortcode,
                    "caption": post.caption,
                    "published_at": post_date.isoformat(),
                    "comments": _fetch_real_comments(post, profile.username),
                },
                "likes_count": post.likes,
                "comments_count": post.comments,
            }
        )
        if on_progress is not None:
            on_progress(len(posts), total_hint)

    return {
        "bio": profile.biography,
        "followers_count": profile.followers,
        "posts": posts,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && .venv/bin/python -m pytest tests/test_scraper.py -v`
Expected: PASS — todos os testes de `test_scraper.py` (pré-existentes + novos desta task).

- [ ] **Step 5: Commit**

```bash
cd "/Users/danielperrut/0. PROJETO/mede-dodo"
git add src/scraper.py tests/test_scraper.py
git commit -m "feat(scraper): pacing por post e SafeStop em 429/checkpoint durante a coleta real"
```

---

### Task 4: Helpers puros de ETA/mensagem humanizada (`app.py`)

**Files:**
- Modify: `app.py` (novas funções privadas, perto de `_run_pipeline`)
- Test: `tests/test_app.py`

**Interfaces:**
- Produces: `_compute_eta_seconds(remaining_items, mean_seconds_per_item, max_runtime_budget=300.0) -> float | None`; `_format_eta(seconds) -> str`; `_make_coleta_progress_callback(state) -> callable(processed, total)`.
- Consumes: nenhuma dependência nova de outros módulos.

- [ ] **Step 1: Write the failing tests**

Adicionar a `tests/test_app.py`:

```python
def test_compute_eta_seconds_returns_none_when_mean_unknown():
    import app

    assert app._compute_eta_seconds(10, None) is None


def test_compute_eta_seconds_returns_none_when_nothing_remaining():
    import app

    assert app._compute_eta_seconds(0, 3.5) is None


def test_compute_eta_seconds_multiplies_remaining_by_mean():
    import app

    assert app._compute_eta_seconds(4, 3.5) == 14.0


def test_compute_eta_seconds_clamps_to_max_runtime_budget():
    import app

    assert app._compute_eta_seconds(1000, 3.5, max_runtime_budget=60.0) == 60.0


def test_format_eta_formats_seconds_only():
    import app

    assert app._format_eta(0) == "0s"
    assert app._format_eta(45) == "45s"


def test_format_eta_formats_minutes_and_seconds():
    import app

    assert app._format_eta(60) == "1min"
    assert app._format_eta(75) == "1min 15s"
    assert app._format_eta(125.6) == "2min 6s"


def test_make_coleta_progress_callback_updates_state_progressively():
    import app

    state = {}
    callback = app._make_coleta_progress_callback(state)

    callback(1, 4)
    assert state["etapa"] == "coleta"
    assert 0.05 <= state["progresso"] <= 0.30
    primeiro_progresso = state["progresso"]
    assert "1/4" in state["mensagem"]

    callback(2, 4)
    assert state["progresso"] > primeiro_progresso
    assert "2/4" in state["mensagem"]
    assert state["eta_seconds"] is not None
    assert state["eta_seconds"] >= 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && .venv/bin/python -m pytest tests/test_app.py -k "eta or progress_callback" -v`
Expected: FAIL — `AttributeError: module 'app' has no attribute '_compute_eta_seconds'`.

- [ ] **Step 3: Implement**

Em `app.py`, adicionar logo após a definição de `PIPELINE_STEPS` (linha ~67):

```python
# Banda de progresso reservada para a extração dinâmica (post a post) dentro
# da fase "coleta" — FINDER-003 §2.3 (banda 30-85% na tabela de referência;
# aqui usamos a banda já reservada para "coleta" nesta implementação, já que
# renomear a fase quebraria nenhuma asserção de teste existente, mas manter o
# nome reduz o diff sem necessidade).
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && .venv/bin/python -m pytest tests/test_app.py -v`
Expected: PASS — todos os testes de `test_app.py` (pré-existentes + novos).

- [ ] **Step 5: Commit**

```bash
cd "/Users/danielperrut/0. PROJETO/mede-dodo"
git add app.py tests/test_app.py
git commit -m "feat(app): ETA dinâmico por média móvel e mensagem contextual de progresso"
```

---

### Task 5: Ligar o `RateController` real no pipeline + status `pausado_seguranca`

**Files:**
- Modify: `app.py:14-39` (imports), `app.py:55-58` (nova mensagem), `app.py:230-261` (`_run_pipeline`), `app.py:767-780` (render loop de `main()`)
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `rate_controller.RateController`, `rate_controller.SafeStop`, `rate_controller.SAFETY_MESSAGE` (Task 1, importado direto — sem alias — em `app.py`); `_make_coleta_progress_callback` (Task 4).
- Produces: novo valor possível para `state["status"]`: `"pausado_seguranca"`.

- [ ] **Step 1: Write the failing tests**

Adicionar a `tests/test_app.py`:

```python
def test_run_pipeline_sets_pausado_seguranca_status_when_scrape_profile_raises_safe_stop(monkeypatch):
    import app
    from src import rate_controller, scraper

    def _raise_safe_stop(*args, **kwargs):
        raise rate_controller.SafeStop(reason="http_429")

    monkeypatch.setattr(scraper, "scrape_profile", _raise_safe_stop)

    state = {}
    app._run_pipeline("perfil_qualquer", 90, False, None, state)

    assert state["status"] == "pausado_seguranca"
    assert state["erro"] == rate_controller.SAFETY_MESSAGE


def test_app_shows_safety_message_when_pipeline_reports_pausado_seguranca(monkeypatch):
    from src import rate_controller, scraper

    def _raise_safe_stop(*args, **kwargs):
        raise rate_controller.SafeStop(reason="http_429")

    monkeypatch.setattr(scraper, "scrape_profile", _raise_safe_stop)

    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input(key="username_input").set_value(f"perfil_safe_stop_{uuid.uuid4().hex}")
    at.toggle(key="demo_mode_toggle").set_value(False)
    at.button[0].click().run()

    max_reruns = 50
    for _ in range(max_reruns):
        assert not at.exception
        status = at.session_state["pipeline_state"].get("status")
        if status != "rodando":
            break
        at.run()

    assert not at.exception
    assert at.session_state["pipeline_state"]["status"] == "pausado_seguranca"
    warning_values = [w.value for w in at.warning]
    assert any(rate_controller.SAFETY_MESSAGE in value for value in warning_values)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && .venv/bin/python -m pytest tests/test_app.py -k "pausado_seguranca or safety_message" -v`
Expected: FAIL — `state["status"] == "erro"` (cai no `except Exception` genérico existente) em vez de `"pausado_seguranca"`.

- [ ] **Step 3: Implement**

Em `app.py`, no bloco de imports (linha ~28), adicionar `rate_controller` e `functools`:

```python
import functools
...
from src import data_loaders, database, demographics, exporter, filters, metrics, scoring, scraper
from src import rate_controller
```

Perto de `COLETA_INDISPONIVEL_MSG` (linha ~58), adicionar:

```python
# FINDER-003 §6: mensagem mínima obrigatória quando o rate controller para a
# coleta por 429/403/challenge/checkpoint — texto vem de rate_controller para
# não duplicar a string em dois lugares.
SAFE_STOP_MSG = rate_controller.SAFETY_MESSAGE
```

Dentro de `_run_pipeline`, no início (linhas ~236-245), trocar:

```python
        fetch_fn = demo_fetch_fn if demo_mode else scraper.instaloader_fetch_fn
        # DUMMY.md #3 (throttling 2-5s) só faz sentido para requisições de rede reais.
        # Em modo demonstração não há nenhuma requisição a proteger, então usamos um
        # throttle_fn instantâneo; a raspagem real usa o jitter padrão de src/scraper.py.
        throttle_fn = scraper.throttle if not demo_mode else (lambda: None)
        # Caminho de um arquivo de sessão local salvo via Instaloader (login manual
        # único, fora deste código) — sem isso, a coleta real ainda tenta rodar sem
        # sessão e cai no fallback de cache/erro tratado abaixo se falhar.
        cookies = None if demo_mode else os.environ.get("INSTAGRAM_SESSION_FILE")
```

por:

```python
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
```

E o `try/except` logo abaixo (linhas ~246-261), trocar:

```python
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
        except scraper.ScraperUnavailableError as exc:
            state["status"] = "erro_coleta_indisponivel"
            state["erro"] = str(exc)
            return
```

por:

```python
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
```

Por fim, no loop de render de `main()` (linhas ~767-780), trocar:

```python
    if status == "rodando":
        etapa = state.get("etapa", "coleta")
        texto_etapa, progresso_padrao = PIPELINE_STEPS.get(etapa, ("Processando...", 0.0))
        progresso = state.get("progresso", progresso_padrao)
        st.progress(progresso, text=texto_etapa)
        time.sleep(0.3)
        st.rerun()
    elif status == "erro_scraping_nao_implementado":
```

por:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && .venv/bin/python -m pytest tests/test_app.py tests/test_scraper.py -v`
Expected: PASS — todos verdes.

- [ ] **Step 5: Commit**

```bash
cd "/Users/danielperrut/0. PROJETO/mede-dodo"
git add app.py tests/test_app.py
git commit -m "feat(app): liga RateController real no pipeline e adiciona status pausado_seguranca"
```

---

### Task 6: Botão "Ver Relatório" — libera exportação HTML/PDF/JSON

**Files:**
- Modify: `app.py:419-424` (`_init_state`), `app.py:684-706` (`_start_pipeline_thread`), `app.py:781-794` (bloco `concluido` em `main()`)
- Test: `tests/test_app.py`

**Interfaces:**
- Produces: `st.session_state.mostrar_relatorio` (bool). Nenhuma função nova exportada — comportamento inteiramente dentro de `main()`.
- Nota de design (registrar no PR): os cards do dashboard (`_render_metric_cards`, `_render_campaign_insights_section`, demografia/antifraude/publis/comentários) continuam renderizando imediatamente ao concluir — testes `AppTest` pré-existentes (`test_app_demo_mode_renders_campaign_insights_section_without_gemini_api_key`, `test_app_renders_new_audience_metric_cards_when_gemini_configured`) já afirmam isso sem clicar em nada extra. Só a exportação (`_render_export_buttons`, os únicos `download_button`) fica atrás do clique — nenhum teste existente afirma a presença de `download_button` logo após "concluido" (conferido: `test_app_idle_state_shows_no_analysis_yet` só afirma ausência no estado ocioso).

- [ ] **Step 1: Write the failing tests**

Adicionar a `tests/test_app.py`:

```python
def test_app_hides_export_buttons_until_ver_relatorio_clicked():
    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input(key="username_input").set_value(f"perfil_ver_relatorio_{uuid.uuid4().hex}")
    at.toggle(key="demo_mode_toggle").set_value(True)
    at.button[0].click().run()

    max_reruns = 50
    for _ in range(max_reruns):
        assert not at.exception
        status = at.session_state["pipeline_state"].get("status")
        if status != "rodando":
            break
        at.run()

    assert at.session_state["pipeline_state"]["status"] == "concluido"
    assert at.download_button == []
    ver_relatorio_button = next(b for b in at.button if b.label == "Ver Relatório")

    ver_relatorio_button.click().run()

    assert not at.exception
    assert len(at.download_button) >= 1


def test_app_gerar_novo_relatorio_resets_screen_without_clearing_cache(monkeypatch):
    from src import database

    clear_cache_calls = []
    monkeypatch.setattr(database, "clear_profile_cache", lambda username: clear_cache_calls.append(username))

    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input(key="username_input").set_value(f"perfil_gerar_novo_{uuid.uuid4().hex}")
    at.toggle(key="demo_mode_toggle").set_value(True)
    at.button[0].click().run()

    max_reruns = 50
    for _ in range(max_reruns):
        assert not at.exception
        status = at.session_state["pipeline_state"].get("status")
        if status != "rodando":
            break
        at.run()

    next(b for b in at.button if b.label == "Ver Relatório").click().run()
    next(b for b in at.button if b.label == "Gerar novo relatório").click().run()

    assert not at.exception
    assert at.session_state["pipeline_state"]["status"] == "ocioso"
    assert at.session_state["mostrar_relatorio"] is False
    assert clear_cache_calls == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && .venv/bin/python -m pytest tests/test_app.py -k "ver_relatorio or gerar_novo" -v`
Expected: FAIL — `StopIteration` em `next(b for b in at.button if b.label == "Ver Relatório")` (botão ainda não existe) / `download_button` já aparece sem gate.

- [ ] **Step 3: Implement**

Em `_init_state` (linha ~419):

```python
def _init_state():
    if "pipeline_state" not in st.session_state:
        st.session_state.pipeline_state = {"status": "ocioso"}
    if "pipeline_thread" not in st.session_state:
        st.session_state.pipeline_thread = None
    if "mostrar_relatorio" not in st.session_state:
        st.session_state.mostrar_relatorio = False
```

Em `_start_pipeline_thread` (linha ~698), logo antes de criar a thread:

```python
    st.session_state.pipeline_state = {"status": "rodando", "etapa": "coleta", "progresso": 0.0}
    st.session_state.mostrar_relatorio = False
```

No bloco `elif status == "concluido":` de `main()` (linhas ~781-794), trocar o final (a partir de `_render_export_buttons(analysis)`):

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && .venv/bin/python -m pytest tests/test_app.py -v`
Expected: PASS — todos os testes de `test_app.py`.

- [ ] **Step 5: Commit**

```bash
cd "/Users/danielperrut/0. PROJETO/mede-dodo"
git add app.py tests/test_app.py
git commit -m "feat(app): botão Ver Relatório libera exportação HTML/PDF/JSON ao concluir"
```

---

### Task 7: Regressão completa e verificação das muralhas

**Files:** nenhum arquivo novo — só verificação.

- [ ] **Step 1: Rodar a suíte inteira**

Run: `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && .venv/bin/python -m pytest tests/ -q`
Expected: `N passed` com `N >= 197` e 0 falhas/erros.

- [ ] **Step 2: Confirmar que `src/exporter.py` não foi tocado**

Run: `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && git diff --stat main -- src/exporter.py`
Expected: saída vazia (nenhuma diferença).

- [ ] **Step 3: Confirmar que os clientes Gemini/retries não foram tocados**

Run: `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && git diff --stat main -- src/gemini_analyzer.py`
Expected: saída vazia. (`DemoGeminiClient`, em `app.py`, não deve aparecer nos diffs das tasks 1-3/6 — só as tasks 4/5 tocam `app.py`, e nenhuma delas mexe em `DemoGeminiClient`, `_make_demo_comment`, `_classify_demo_comment` ou `demo_fetch_fn`; conferir manualmente com `git diff main -- app.py` se houver dúvida.)

- [ ] **Step 4: Rodar o app manualmente em modo demonstração**

Run: `cd "/Users/danielperrut/0. PROJETO/mede-dodo" && ./iniciar_app.command` (ou `.venv/bin/python -m streamlit run app.py`), abrir no navegador, marcar "Modo demonstração", clicar "Analisar", confirmar que a barra de progresso aparece com mensagens e some ao concluir, que o dashboard aparece imediatamente, que "Ver Relatório" libera os botões de download, e que "Gerar novo relatório" volta ao formulário sem apagar o cache.

- [ ] **Step 5: Commit final (se houver qualquer ajuste residual das verificações acima)**

```bash
cd "/Users/danielperrut/0. PROJETO/mede-dodo"
git status --short
# só commitar se houver mudança pendente das correções do Step 4
```

---

## Self-Review (preenchido durante a escrita do plano)

**Cobertura da spec (escopo dos 3 itens pedidos):**
1. Pacing dinâmico & anti-ban → Tasks 1-3 (RateController conservador/monotônico, não humanizado; SafeStop em 429/403/challenge; pacing por post).
2. Fluxo visual de progresso (mensagens humanizadas + ETA + "Ver Relatório") → Tasks 4-6.
3. Muros de contenção → Global Constraints + verificação explícita na Task 7.

**Divergência disclosed vs. pedido original:** o pedido usa "anti-ban"/"simular comportamento humano" — implementado como rate limiting conservador e observável (FINDER-003 §4.1/§14), não evasão. O "Ver Relatório" gateia a exportação (HTML/PDF/JSON), não o dashboard inteiro, porque testes `AppTest` pré-existentes já afirmam que os cards aparecem imediatamente ao concluir — gatear tudo quebraria a muralha dos 197 testes.

**Fora de escopo (deliberado):** checkpoint/resume persistente (§6.1), API oficial Meta/OAuth (§3.3), métricas agregadas (§8), progresso dinâmico em modo demonstração (spec pede explicitamente sem jitter/rede em demo).
