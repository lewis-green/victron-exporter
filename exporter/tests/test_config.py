import pytest

from victron_exporter.config import Config, Feed, parse_config


def test_parse_minimal_config_applies_defaults():
    cfg = parse_config({"feeds": [{"name": "a", "host": "10.0.0.1"}]})
    assert cfg == Config(feeds=(Feed("a", "10.0.0.1", 1883),), listen_port=9105,
                         stale_seconds=120.0, keepalive_seconds=30.0)


def test_parse_overrides():
    cfg = parse_config({"feeds": [{"name": "a", "host": "h", "port": 1884}],
                        "listen_port": 9200, "stale_seconds": 60, "keepalive_seconds": 20})
    assert cfg.feeds[0].port == 1884
    assert (cfg.listen_port, cfg.stale_seconds, cfg.keepalive_seconds) == (9200, 60.0, 20.0)


@pytest.mark.parametrize("raw", [
    {},
    {"feeds": []},
    {"feeds": [{"name": "a"}]},
    {"feeds": [{"host": "h"}]},
    {"feeds": [{"name": "a", "host": "h"}, {"name": "a", "host": "h2"}]},
])
def test_invalid_config_raises(raw):
    with pytest.raises(ValueError):
        parse_config(raw)
