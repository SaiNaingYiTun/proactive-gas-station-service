# Make/Model Phase Architecture

## Goal
Add reliable vehicle make/model inference without reducing license-plate pipeline stability.

## Design Principles
- Keep plate OCR as the primary flow and isolate make/model as a secondary module.
- Fail safe: if make/model is uncertain, return unknown instead of wrong labels.
- Reuse existing vehicle detection crop to avoid extra detector cost.
- Record confidence for every predicted attribute (make, model, color).

## Pipeline Placement
1. Frame input
2. Plate detection and OCR (existing)
3. Vehicle detection and color (existing)
4. Make/model classifier (new, async worker)
5. Stabilization across frames
6. Backend event send

## Proposed Runtime Components
- vehicle_detector.py
  - Responsibility: detect vehicle bounding box once per frame.
  - Output: box, detector_conf.
- make_model_classifier.py (new)
  - Responsibility: infer make/model from vehicle crop.
  - Output: make, model, mm_conf.
- make_model_stabilizer.py (new)
  - Responsibility: smooth noisy predictions across short time windows.
  - Output: stable_make, stable_model, stable_mm_conf.
- main.py
  - Responsibility: orchestrate queues, merge OCR + color + make/model, send to backend.

## Data Contract (in-memory)
Use one shared object shape for stabilized results:

{
  "plate": "1234",
  "plate_conf": 0.91,
  "province": "กรุงเทพมหานคร",
  "province_conf": 0.78,
  "color": "white",
  "color_conf": 0.44,
  "make": "toyota",
  "model": "hilux",
  "mm_conf": 0.62,
  "updated": 1720000000.00
}

## Backend Contract (recommended)
Extend entry payload with optional fields:
- make: string
- model: string
- make_model_conf: float

If confidence is below threshold, send:
- make = "unknown"
- model = "unknown"
- make_model_conf = 0.0

## Confidence Policy
- plate/province: keep current thresholds.
- color: keep current conservative threshold.
- make/model (start point):
  - accept if mm_conf >= 0.55
  - else unknown
- stabilization requirement:
  - same make/model seen at least 2 times in last 5 samples.

## Model Strategy
Phase 1 (fast path)
- Use an off-the-shelf classifier baseline for coarse make classes.
- Keep model label set small (top frequent makes first).

Phase 2 (production path)
- Train custom classifier on Thai traffic domain images.
- Include night/rain/glare data and common CCTV camera angles.
- Add hard-negative examples (logos, occluded front grills, motion blur).

## Performance Budget
- Keep end-to-end latency bounded by current OCR loop.
- Run make/model every N frames (example: every 2 or 3 frames).
- Skip make/model if vehicle crop is too small or blurry.

## Observability
Add debug flags:
- DEBUG_MAKE_MODEL=1: log per-frame raw make/model/conf.
- DEBUG_PIPELINE=1: log stabilized single-line output.

Example log:
[PIPELINE] plate=1234 ocr_conf=0.89 province=กรุงเทพมหานคร color=white color_conf=0.42 make=toyota model=hilux mm_conf=0.61

## Rollout Plan
1. Add make_model_classifier.py with stub returning unknown.
2. Add queue + wiring in main.py behind feature flag ENABLE_MAKE_MODEL.
3. Add stabilizer and backend payload fields.
4. Run offline replay on recorded station footage.
5. Tune thresholds and only then enable in production.

## Minimal Interface (new module)
def infer_make_model(vehicle_crop):
    """Return (make, model, confidence) with unknown fallback."""
    return "unknown", "unknown", 0.0
