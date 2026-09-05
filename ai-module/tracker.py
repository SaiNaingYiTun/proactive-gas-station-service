from utils import sharpness_score


class BurstTracker:
    def __init__(self, max_candidates=6, min_w=28, min_h=14):
        self.best_crop = None
        self.best_tight_crop = None
        self.best_score = -1.0
        self.count = 0
        self.max = max_candidates
        self.min_w = min_w
        self.min_h = min_h

    def reset(self):
        self.best_crop = None
        self.best_tight_crop = None
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
            # Both arguments are views into the frame.  The live loop draws
            # green rectangles onto that frame after this call; retaining the
            # view made those rectangles part of the image later sent to OCR.
            self.best_crop = padded.copy()
            self.best_tight_crop = tight.copy()
        self.count += 1

    def ready(self):
        return self.count >= self.max
