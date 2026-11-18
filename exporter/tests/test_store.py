from victron_exporter.mapping import Sample
from victron_exporter.store import Store

SOC = Sample("victron_battery_soc_percent", ())


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_snapshot_returns_values_for_fresh_feed():
    clock = Clock()
    store = Store(stale_seconds=120, clock=clock)
    store.touch("a")
    store.set("a", SOC, 98.0)
    assert store.snapshot() == [("a", SOC, 98.0)]


def test_unchanged_value_stays_while_feed_keeps_talking():
    clock = Clock()
    store = Store(stale_seconds=120, clock=clock)
    store.touch("a")
    store.set("a", SOC, 98.0)
    clock.now += 500
    store.touch("a")  # heartbeat only
    assert store.snapshot() == [("a", SOC, 98.0)]


def test_silent_feed_is_dropped_from_snapshot():
    clock = Clock()
    store = Store(stale_seconds=120, clock=clock)
    store.touch("a")
    store.set("a", SOC, 98.0)
    clock.now += 121
    assert store.snapshot() == []


def test_none_removes_value():
    store = Store(stale_seconds=120, clock=Clock())
    store.touch("a")
    store.set("a", SOC, 98.0)
    store.set("a", SOC, None)
    assert store.snapshot() == []


def test_status_reports_up_and_last_update():
    clock = Clock()
    store = Store(stale_seconds=120, clock=clock)
    store.set_up("a", True)
    store.touch("a")
    store.set_up("b", False)
    assert store.status() == {"a": (True, 1000.0), "b": (False, None)}
