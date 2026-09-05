import requests

from config import API_BASE, CAMERA_ID


def send_detection(event_id, plate, conf, color="unknown"):
    try:
        response = requests.post(
            f"{API_BASE}/api/detection",
            json={
                "event_id": event_id,
                "plate_number": plate,
                "vehicle_type": "car",
                "color": color,
                "confidence": conf,
                "camera_id": CAMERA_ID,
            },
            timeout=3,
        )
        return response.json()
    except Exception as error:
        print(f"⚠️  Backend error: {error}")
        return None


def send_exit(event_id, plate):
    try:
        response = requests.put(
            f"{API_BASE}/api/exit",
            json={"event_id": event_id, "plate_number": plate, "camera_id": CAMERA_ID},
            timeout=3,
        )
        return response.json()
    except Exception as error:
        print(f"⚠️  Exit error: {error}")
        return None
