from core.metrics import Metrics


def test_metrics_incr_and_snapshot():
    m = Metrics()
    m.incr("a")
    m.incr("a", 2)
    m.timing("t", 10)
    m.timing("t", 20)
    m.error("x", "boom")
    snap = m.snapshot()
    assert snap["counters"]["a"] == 3
    assert snap["avg_timing_ms"]["t"] == 15.0
    assert len(snap["recent_errors"]) == 1
