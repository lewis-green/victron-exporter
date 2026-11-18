"""Thread-safe store of the latest value per feed and sample."""
import threading
import time


class Store:
    def __init__(self, stale_seconds, clock=time.time):
        self._stale = stale_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._values = {}  # feed -> {Sample: float}
        self._up = {}      # feed -> bool
        self._last = {}    # feed -> time of last message

    def set(self, feed, sample, value):
        with self._lock:
            values = self._values.setdefault(feed, {})
            if value is None:
                values.pop(sample, None)
            else:
                values[sample] = value

    def touch(self, feed):
        with self._lock:
            self._last[feed] = self._clock()

    def set_up(self, feed, up):
        with self._lock:
            self._up[feed] = up

    def status(self):
        with self._lock:
            return {feed: (self._up.get(feed, False), self._last.get(feed))
                    for feed in set(self._up) | set(self._last)}

    def snapshot(self):
        """Return [(feed, sample, value)] for feeds heard from within stale_seconds."""
        with self._lock:
            now = self._clock()
            out = []
            for feed, values in self._values.items():
                last = self._last.get(feed)
                if last is None or now - last > self._stale:
                    continue
                out.extend((feed, sample, value) for sample, value in values.items())
            return out
