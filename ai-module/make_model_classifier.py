def infer_make_model(vehicle_crop):
    """Return (make, model, confidence) with a safe unknown fallback.

    This is a production scaffold stub. Replace this implementation with a
    real model inference step in phase 2.
    """
    if vehicle_crop is None or vehicle_crop.size == 0:
        return "unknown", "unknown", 0.0

    return "unknown", "unknown", 0.0
