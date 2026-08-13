from ultralytics import YOLO

from config import CONF_THRESHOLD, MODEL_PATH


plate_model = YOLO(MODEL_PATH)


def find_plate_yolo(frame):
    results = plate_model(frame, conf=CONF_THRESHOLD, verbose=False)[0]
    best_box, best_conf = None, 0.0
    for box in results.boxes:
        c = float(box.conf[0])
        if c > best_conf:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            best_box = (x1, y1, x2 - x1, y2 - y1)
            best_conf = c
    return best_box, best_conf
