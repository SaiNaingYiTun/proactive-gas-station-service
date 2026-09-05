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

        # OCR commonly varies by one Thai letter or one serial digit on a
        # small, tilted plate (for example "บว1433" vs "ทว1430").  Treat
        # those as one candidate only when they have the same length, at
        # least three digits, and agree on at least 75% of the digit string.
        # This is intentionally narrower than lowering the general text
        # similarity threshold, which would also merge unrelated provinces.
        digits = "".join(char for char in text if char.isdigit())
        if len(digits) >= 3:
            for candidate_key in self._candidates:
                candidate_digits = "".join(char for char in candidate_key if char.isdigit())
                if len(text) != len(candidate_key) or len(digits) != len(candidate_digits):
                    continue
                digit_score = SequenceMatcher(None, digits, candidate_digits).ratio()
                if digit_score >= 0.75:
                    return candidate_key

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
        # OCR can read a real plate correctly once, then later drop a digit
        # with a slightly higher confidence.  Never replace a longer plate
        # reading with its shorter fragment merely because of confidence.
        if len(text) > len(candidate["best_text"]) or (
            len(text) == len(candidate["best_text"])
            and conf >= previous_best_conf
        ):
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
