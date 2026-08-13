from utils import sharpness_score


class BurstTracker:
    def __init__(self, max_candidates=6, min_w=70, min_h=20):
        self.best_crop = None
        self.best_score = -1.0
        self.count = 0
        self.max = max_candidates
        self.min_w = min_w
        self.min_h = min_h

    def reset(self):
        self.best_crop = None
        self.best_score = -1.0
        self.count = 0

    def offer(self, tight, padded, yolo_conf):
        if tight.size == 0:
            return
        h, w = tight.shape[:2]
        if w < self.min_w or h < self.min_h:
            return
        score = sharpness_score(tight) * yolo_conf
        if score > self.best_score:
            self.best_score = score
            self.best_crop = padded
        self.count += 1

    def ready(self):
        return self.count >= self.max
