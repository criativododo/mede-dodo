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
