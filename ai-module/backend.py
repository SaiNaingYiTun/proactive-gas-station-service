import requests

from config import API_BASE, CAMERA_ID


def send_detection(plate, conf):
    try:
        response = requests.post(
            f"{API_BASE}/api/detection",
            json={"plate_number": plate, "vehicle_type": "car", "confidence": conf, "camera_id": CAMERA_ID},
            timeout=3,
        )
        return response.json()
    except Exception as error:
        print(f"⚠️  Backend error: {error}")
        return None


def send_exit(plate):
    try:
        response = requests.put(f"{API_BASE}/api/exit", json={"plate_number": plate}, timeout=3)
        return response.json()
    except Exception as error:
        print(f"⚠️  Exit error: {error}")
        return None
