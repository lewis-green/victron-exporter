from victron_exporter.config import Feed
from victron_exporter.mapping import Sample
from victron_exporter.mqtt_client import SUPPRESS, FeedClient
from victron_exporter.store import Store

SOC = Sample("victron_battery_soc_percent", ())


class FakeClient:
    def __init__(self):
        self.subscribed, self.published, self.reconnects = [], [], 0

    def subscribe(self, topic):
        self.subscribed.append(topic)

    def publish(self, topic, payload=None):
        self.published.append((topic, payload))

    def reconnect(self):
        self.reconnects += 1


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def make(clock=None):
    clock = clock or Clock()
    store = Store(stale_seconds=120, clock=lambda: 1000.0)
    fake = FakeClient()
    client = FeedClient(Feed("a", "h"), store, keepalive_seconds=30, full_refresh_seconds=600,
                        client=fake, clock=clock)
    return client, store, fake, clock


def test_connect_marks_up_and_subscribes_to_serial():
    client, store, fake, _ = make()
    client._on_connect(fake, None, None, 0, None)
    assert store.status()["a"][0] is True
    assert fake.subscribed == ["N/+/system/0/Serial"]


def test_first_message_discovers_portal_subscribes_and_requests_full_publish():
    client, store, fake, _ = make()
    client._on_connect(fake, None, None, 0, None)
    client.handle("N/abc123/system/0/Serial", b'{"value": "abc123"}')
    assert client.portal == "abc123"
    topics = [t for t, _qos in fake.subscribed[1]]
    assert "N/abc123/battery/+/Soc" in topics and "N/abc123/heartbeat" in topics
    assert fake.published == [("R/abc123/keepalive", None)]


def test_value_message_is_stored_and_null_clears_it():
    client, store, fake, _ = make()
    client._on_connect(fake, None, None, 0, None)
    client.handle("N/abc/battery/512/Soc", b'{"value": 98.0}')
    assert store.snapshot() == [("a", SOC, 98.0)]
    client.handle("N/abc/battery/512/Soc", b'{"value": null}')
    assert store.snapshot() == []


def test_malformed_and_unmapped_messages_are_ignored():
    client, store, fake, _ = make()
    client._on_connect(fake, None, None, 0, None)
    client.handle("N/abc/battery/512/Soc", b"garbage")
    client.handle("N/abc/battery/512/CustomName", b'{"value": "x"}')
    client.handle("bogus", b"")
    assert store.snapshot() == []


def test_tick_sends_suppressed_keepalive_then_periodic_full_refresh():
    client, store, fake, clock = make()
    client._on_connect(fake, None, None, 0, None)
    client.handle("N/abc/heartbeat", b'{"value": 1}')
    fake.published.clear()
    clock.now = 30
    client.tick()
    assert fake.published == [("R/abc/keepalive", SUPPRESS)]
    clock.now = 600
    client.tick()
    assert fake.published[-1] == ("R/abc/keepalive", None)


def test_tick_reconnects_when_portal_not_discovered():
    client, store, fake, clock = make()
    client._on_connect(fake, None, None, 0, None)
    clock.now = 29
    client.tick()
    assert fake.reconnects == 0
    clock.now = 31
    client.tick()
    assert fake.reconnects == 1


def test_disconnect_marks_down_and_stops_keepalives():
    client, store, fake, clock = make()
    client._on_connect(fake, None, None, 0, None)
    client.handle("N/abc/heartbeat", b'{"value": 1}')
    client._on_disconnect(fake, None, None, 0, None)
    fake.published.clear()
    client.tick()
    assert store.status()["a"][0] is False
    assert fake.published == []
