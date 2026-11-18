"""One MQTT connection to a Venus OS GX device. Read-only apart from the keepalive."""
import logging
import threading
import time

import paho.mqtt.client as mqtt

from .mapping import lookup, parse_value, subscriptions

log = logging.getLogger(__name__)

SUPPRESS = '{"keepalive-options": ["suppress-republish"]}'
DISCOVERY_TIMEOUT = 30.0


def _default_client(name):
    return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"victron-exporter-{name}")


class FeedClient:
    def __init__(self, feed, store, keepalive_seconds=30.0, full_refresh_seconds=600.0,
                 client=None, clock=time.monotonic):
        self.feed = feed
        self.store = store
        self.portal = None
        self._keepalive = keepalive_seconds
        self._full_refresh = full_refresh_seconds
        self._clock = clock
        self._connected = False
        self._connected_at = 0.0
        self._last_full = 0.0
        self._bad_topics = set()
        self._stop = threading.Event()
        self._client = client if client is not None else _default_client(feed.name)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def start(self):
        self._client.reconnect_delay_set(min_delay=1, max_delay=60)
        self._client.connect_async(self.feed.host, self.feed.port, keepalive=60)
        self._client.loop_start()
        threading.Thread(target=self._loop, daemon=True, name=f"keepalive-{self.feed.name}").start()

    def stop(self):
        self._stop.set()
        self._client.loop_stop()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if getattr(reason_code, "is_failure", False):
            log.warning("%s: connect refused: %s", self.feed.name, reason_code)
            return
        log.info("%s: connected to %s:%s", self.feed.name, self.feed.host, self.feed.port)
        self.portal = None
        self._connected = True
        self._connected_at = self._clock()
        self.store.set_up(self.feed.name, True)
        client.subscribe("N/+/system/0/Serial")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        log.warning("%s: disconnected: %s", self.feed.name, reason_code)
        self._connected = False
        self.store.set_up(self.feed.name, False)

    def _on_message(self, client, userdata, msg):
        self.handle(msg.topic, msg.payload)

    def handle(self, topic, payload):
        parts = topic.split("/", 2)
        if len(parts) < 3 or parts[0] != "N":
            return
        portal, suffix = parts[1], parts[2]
        if self.portal is None:
            self.portal = portal
            log.info("%s: portal id %s", self.feed.name, portal)
            self._client.subscribe([(t, 0) for t in subscriptions(portal)])
            self.send_keepalive(full=True)
        self.store.touch(self.feed.name)
        sample = lookup(suffix)
        if sample is None:
            return
        try:
            value = parse_value(payload)
        except ValueError as exc:
            if suffix not in self._bad_topics:
                self._bad_topics.add(suffix)
                log.warning("%s: skipping %s: %s", self.feed.name, suffix, exc)
            return
        self.store.set(self.feed.name, sample, value)

    def send_keepalive(self, full):
        if self.portal is None:
            return
        self._client.publish(f"R/{self.portal}/keepalive", None if full else SUPPRESS)
        if full:
            self._last_full = self._clock()

    def tick(self):
        if not self._connected:
            return
        if self.portal is None:
            if self._clock() - self._connected_at >= DISCOVERY_TIMEOUT:
                log.warning("%s: no portal id after %.0fs, reconnecting", self.feed.name, DISCOVERY_TIMEOUT)
                self._connected_at = self._clock()
                self._client.reconnect()
            return
        self.send_keepalive(full=self._clock() - self._last_full >= self._full_refresh)

    def _loop(self):
        while not self._stop.wait(self._keepalive):
            try:
                self.tick()
            except Exception:  # keep the keepalive thread alive
                log.exception("%s: keepalive tick failed", self.feed.name)
