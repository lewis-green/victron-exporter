from prometheus_client import CollectorRegistry, generate_latest

from victron_exporter.collector import VictronCollector
from victron_exporter.mapping import Sample
from victron_exporter.store import Store


def render(store, feeds):
    registry = CollectorRegistry()
    registry.register(VictronCollector(store, feeds))
    return generate_latest(registry).decode()


def test_renders_values_alarms_and_health():
    store = Store(stale_seconds=120, clock=lambda: 1000.0)
    store.set_up("a", True)
    store.touch("a")
    store.set("a", Sample("victron_battery_soc_percent", ()), 98.0)
    store.set("a", Sample("victron_alarm", (("source", "vebus"), ("alarm", "Overload"))), 1.0)
    text = render(store, ["a", "b"])
    assert 'victron_up{feed="a"} 1.0' in text
    assert 'victron_up{feed="b"} 0.0' in text
    assert 'victron_last_update_timestamp_seconds{feed="a"} 1000.0' in text
    assert 'victron_last_update_timestamp_seconds{feed="b"}' not in text
    assert 'victron_battery_soc_percent{feed="a"} 98.0' in text
    assert 'victron_alarm{alarm="Overload",feed="a",source="vebus"} 1.0' in text


def test_stale_feed_values_are_not_rendered():
    now = [1000.0]
    store = Store(stale_seconds=120, clock=lambda: now[0])
    store.set_up("a", True)
    store.touch("a")
    store.set("a", Sample("victron_battery_soc_percent", ()), 98.0)
    now[0] = 2000.0
    text = render(store, ["a"])
    assert "victron_battery_soc_percent{" not in text
    assert 'victron_up{feed="a"} 1.0' in text
