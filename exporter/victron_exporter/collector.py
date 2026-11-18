"""Render the store as Prometheus metric families."""
from prometheus_client.core import GaugeMetricFamily

from .mapping import HELP


class VictronCollector:
    def __init__(self, store, feeds):
        self._store = store
        self._feeds = list(feeds)

    def describe(self):
        return []

    def collect(self):
        status = self._store.status()
        up = GaugeMetricFamily("victron_up", "1 if the exporter's MQTT connection to the GX is up.",
                               labels=["feed"])
        last = GaugeMetricFamily("victron_last_update_timestamp_seconds",
                                 "Unix time of the last MQTT message received from the GX.",
                                 labels=["feed"])
        for feed in self._feeds:
            is_up, last_update = status.get(feed, (False, None))
            up.add_metric([feed], 1.0 if is_up else 0.0)
            if last_update is not None:
                last.add_metric([feed], last_update)
        yield up
        yield last

        families = {}
        for feed, sample, value in self._store.snapshot():
            family = families.get(sample.metric)
            if family is None:
                names = ["feed"] + [name for name, _ in sample.labels]
                family = GaugeMetricFamily(sample.metric, HELP[sample.metric], labels=names)
                families[sample.metric] = family
            family.add_metric([feed] + [val for _, val in sample.labels], value)
        yield from families.values()
