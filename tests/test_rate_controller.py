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
