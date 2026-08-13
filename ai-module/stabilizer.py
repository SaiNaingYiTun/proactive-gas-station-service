from collections import deque
from difflib import SequenceMatcher


class PlateStabilizer:
    def __init__(self, window_size=5, required_hits=3, stale_seconds=8, similarity_threshold=1.0):
        self.window_size = window_size
        self.required_hits = required_hits
        self.stale_seconds = stale_seconds
        self.similarity_threshold = similarity_threshold
        self._candidates = {}
        self._order = deque()

    def _prune(self, now):
        while self._order:
            text, seen_at = self._order[0]
            candidate = self._candidates.get(text)
            if candidate is None or now - candidate["last_seen"] > self.stale_seconds:
                self._order.popleft()
                self._candidates.pop(text, None)
                continue
            break

    def _match_candidate_key(self, text):
        if text in self._candidates:
            return text

        best_key = None
        best_score = 0.0
        for candidate_key in self._candidates:
            score = SequenceMatcher(None, text, candidate_key).ratio()
            if score > best_score:
                best_score = score
                best_key = candidate_key

        if best_key is not None and best_score >= self.similarity_threshold:
            return best_key

        return None

    def offer(self, text, conf, province, now):
        if not text:
            return None

        self._prune(now)

        matched_key = self._match_candidate_key(text)
        candidate = self._candidates.get(matched_key or text)
        if candidate is None:
            candidate = {
                "hits": 0,
                "best_conf": 0.0,
                "best_text": text,
                "province": province,
                "last_seen": now,
            }
            self._candidates[text] = candidate
            self._order.append((text, now))
        elif matched_key and matched_key != text:
            candidate = self._candidates[matched_key]

        candidate["hits"] += 1
        previous_best_conf = candidate["best_conf"]
        candidate["best_conf"] = max(candidate["best_conf"], conf)
        if conf >= previous_best_conf or len(text) > len(candidate["best_text"]):
            candidate["best_text"] = text
        candidate["province"] = province or candidate["province"]
        candidate["last_seen"] = now

        if candidate["hits"] >= self.required_hits:
            return {
                "text": candidate["best_text"],
                "province": candidate["province"],
                "conf": candidate["best_conf"],
                "hits": candidate["hits"],
            }

        return None
