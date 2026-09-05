import torch
from ultralytics import YOLO


device = "cuda" if torch.cuda.is_available() else "cpu"
vehicle_model = YOLO("yolov8n.pt")  # or a car-specific model
vehicle_model.to(device)


def _safe_scalar(value, index=0):
    if value is None:
        return None
    if hasattr(value, "__len__") and not isinstance(value, (str, bytes)):
        if len(value) == 0:
            return None
        value = value[index]
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            return None
    return value


def find_vehicle_yolo(frame, min_conf=0.30, entry_roi=None):
    """Return the most confident vehicle whose centre is in the entry ROI.

    ``frame`` should be the complete camera frame.  Detecting on a cropped
    entry rectangle clips vehicles at its boundary and makes the resulting box
    unsuitable for colour classification.
    """
    results = vehicle_model(frame, conf=min_conf, iou=0.45, verbose=False)[0]

    candidates = []
    h, w = frame.shape[:2]

    for box in results.boxes:
        cls_value = _safe_scalar(box.cls, 0)
        conf_value = _safe_scalar(box.conf, 0)
        if cls_value is None or conf_value is None:
            continue

        try:
            cls = int(cls_value)
            conf = float(conf_value)
            # ``xyxy`` contains four coordinates, not a single scalar.
            # _safe_scalar() is suitable for class/confidence tensors only;
            # using it here discards every vehicle detection.
            x1, y1, x2, y2 = map(float, box.xyxy[0])
        except (TypeError, ValueError):
            continue

        label = vehicle_model.names[cls]
        if label.lower() not in {"car", "truck", "bus", "motorcycle"}:
            continue

        width = x2 - x1
        height = y2 - y1
        area = width * height

        if width <= 0 or height <= 0:
            continue
        # Distant vehicles at the top of the driveway are smaller than the
        # close-up van, but still large enough for a useful colour crop.
        if area < (w * h * 0.002):
            continue

        if entry_roi is not None:
            roi_x1, roi_y1, roi_x2, roi_y2 = entry_roi
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            if not (roi_x1 <= center_x <= roi_x2 and roi_y1 <= center_y <= roi_y2):
                continue

        if conf < min_conf:
            continue

        candidates.append((conf, area, int(x1), int(y1), int(x2), int(y2)))

    if not candidates:
        return None, 0.0

    # Confidence is primary; use area as a stable tie-breaker.
    conf, area, x1, y1, x2, y2 = max(candidates, key=lambda v: (v[0], v[1]))
    return (x1, y1, x2 - x1, y2 - y1), conf


def find_vehicle_tracks(frame, min_conf=0.30):
    """Return ByteTrack-identified vehicle detections for the current frame."""
    results = vehicle_model.track(
        frame,
        persist=True,
        tracker="bytetrack.yaml",
        conf=min_conf,
        iou=0.45,
        verbose=False,
    )[0]

    tracks = []
    h, w = frame.shape[:2]
    for box in results.boxes:
        if box.id is None:
            continue
        cls_value = _safe_scalar(box.cls, 0)
        conf_value = _safe_scalar(box.conf, 0)
        if cls_value is None or conf_value is None:
            continue

        try:
            cls = int(cls_value)
            conf = float(conf_value)
            x1, y1, x2, y2 = map(float, box.xyxy[0])
            track_id = int(box.id[0])
        except (TypeError, ValueError):
            continue

        if vehicle_model.names[cls].lower() not in {"car", "truck", "bus", "motorcycle"}:
            continue
        width, height = x2 - x1, y2 - y1
        if width <= 0 or height <= 0 or width * height < w * h * 0.002:
            continue

        tracks.append({
            "id": track_id,
            "box": (int(x1), int(y1), int(width), int(height)),
            "confidence": conf,
        })

    return tracks
