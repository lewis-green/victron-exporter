"""Load and validate the exporter configuration."""
from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class Feed:
    name: str
    host: str
    port: int = 1883


@dataclass(frozen=True)
class Config:
    feeds: tuple
    listen_port: int = 9105
    stale_seconds: float = 120.0
    keepalive_seconds: float = 30.0


def parse_config(raw):
    feeds = raw.get("feeds") if isinstance(raw, dict) else None
    if not isinstance(feeds, list) or not feeds:
        raise ValueError("config needs a non-empty 'feeds' list")
    parsed, seen = [], set()
    for item in feeds:
        if not isinstance(item, dict) or not item.get("name") or not item.get("host"):
            raise ValueError("each feed needs 'name' and 'host'")
        name = str(item["name"])
        if name in seen:
            raise ValueError(f"duplicate feed name: {name}")
        seen.add(name)
        parsed.append(Feed(name, str(item["host"]), int(item.get("port", 1883))))
    return Config(
        feeds=tuple(parsed),
        listen_port=int(raw.get("listen_port", 9105)),
        stale_seconds=float(raw.get("stale_seconds", 120.0)),
        keepalive_seconds=float(raw.get("keepalive_seconds", 30.0)),
    )


def load_config(path):
    with open(path, encoding="utf-8") as handle:
        return parse_config(yaml.safe_load(handle) or {})
