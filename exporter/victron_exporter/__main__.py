"""Victron GX to Prometheus exporter."""
import argparse
import logging
import os
import signal
import threading

from prometheus_client import CollectorRegistry, start_http_server

from .collector import VictronCollector
from .config import load_config
from .mqtt_client import FeedClient
from .store import Store


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=os.environ.get(
        "VICTRON_EXPORTER_CONFIG", "/etc/victron-exporter/config.yaml"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    config = load_config(args.config)
    store = Store(config.stale_seconds)
    registry = CollectorRegistry()
    registry.register(VictronCollector(store, [feed.name for feed in config.feeds]))
    clients = [FeedClient(feed, store, config.keepalive_seconds) for feed in config.feeds]
    for client in clients:
        client.start()
    start_http_server(config.listen_port, registry=registry)
    logging.info("serving /metrics on :%d for %d feeds", config.listen_port, len(clients))

    done = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: done.set())
    signal.signal(signal.SIGINT, lambda *_: done.set())
    done.wait()
    for client in clients:
        client.stop()


if __name__ == "__main__":
    main()
