import time
from collections import defaultdict, deque


class MakeModelStabilizer:
    def __init__(self, window_size=5, required_hits=2, stale_seconds=8):
        self.window_size = window_size
        self.required_hits = required_hits
        self.stale_seconds = stale_seconds
        self._samples = deque()

    def _prune(self, now):
        while self._samples and now - self._samples[0]["ts"] > self.stale_seconds:
            self._samples.popleft()
        while len(self._samples) > self.window_size:
            self._samples.popleft()

    def offer(self, make, model, conf, now=None):
        if not make or not model:
            return None

        now = now if now is not None else time.time()
        self._samples.append(
            {
                "make": make,
                "model": model,
                "conf": float(conf),
                "ts": float(now),
            }
        )
        self._prune(now)

        grouped = defaultdict(list)
        for sample in self._samples:
            key = (sample["make"], sample["model"])
            grouped[key].append(sample["conf"])

        best_key = None
        best_hits = 0
        best_conf = 0.0
        for key, confs in grouped.items():
            hits = len(confs)
            max_conf = max(confs)
            if hits > best_hits or (hits == best_hits and max_conf > best_conf):
                best_key = key
                best_hits = hits
                best_conf = max_conf

        if best_key is None or best_hits < self.required_hits:
            return None

        return {
            "make": best_key[0],
            "model": best_key[1],
            "conf": best_conf,
            "hits": best_hits,
        }
