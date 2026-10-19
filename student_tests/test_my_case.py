"""AI-assisted case: an in-flight record reserves its whole original payload.

Before execution, derive: wire=[128,104,128], reserved=[200,0,200].
At tick 1 the 64-bit arrival is rejected before the old record completes.
At tick 2 the new 200-bit arrival is admitted but stays incomplete at cutoff.
Thus 464 generated = 200 delivered + 64 dropped + 200 backlog.
"""
import pytest

from src.metrics import summarize
from src.models import Arrival, Config
from src.utils import simulate


def test_inflight_payload_stays_reserved_until_completion():
    cfg = Config(users=2, ticks=3, buffer_payload_bits=200)
    arrivals = [Arrival(0, 1, 200), Arrival(1, 0, 64), Arrival(2, 0, 200)]
    raw = simulate(arrivals, cfg, 'packet')

    assert [t['wire_bits'] for t in raw['trace']] == [128, 104, 128]
    assert [t['buffer_payload_bits'] for t in raw['trace']] == [200, 0, 200]
    assert raw['completed'] == [dict(user=1, payload_bits=200, delay_ticks=2)]
    assert raw['generated_payload_bits'] == 464
    assert raw['delivered_payload_bits'] == 200
    assert raw['dropped_payload_bits'] == 64
    assert raw['backlog_payload_bits'] == 200
    metrics = summarize(raw, cfg)
    assert metrics['payload_utilization'] == pytest.approx(200 / 384)
    assert metrics['wire_utilization'] == pytest.approx(360 / 384)
    assert metrics['loss_ratio'] == pytest.approx(64 / 464)
    assert metrics['mean_delay_ms'] == metrics['max_delay_ms'] == 2
    assert metrics['backlog_payload_bits'] == 200
