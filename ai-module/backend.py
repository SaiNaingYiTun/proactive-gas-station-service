from datetime import datetime, timezone

import requests

from config import API_BASE as DEFAULT_API_BASE, CAMERA_ID

# Mutable so the desktop app (app.py) can point at another backend, or switch
# sending off for a rehearsal, without touching config.py.
api_base = DEFAULT_API_BASE
enabled = True


def set_api_base(url):
    global api_base
    api_base = url.rstrip("/")


def set_enabled(value):
    global enabled
    enabled = bool(value)


def _iso_utc(seen_at):
    """Capture time (a time.time() value taken when the frame was read) as an
    ISO-8601 UTC string, or None to let the backend use its own clock."""
    if seen_at is None:
        return None
    return datetime.fromtimestamp(seen_at, timezone.utc).isoformat()


def send_detection(event_id, plate, conf, color="unknown", make="unknown", seen_at=None):
    if not enabled:
        return None
    try:
        response = requests.post(
            f"{api_base}/api/detection",
            json={
                "event_id": event_id,
                # This camera's entry view usually has no visible plate; send
                # None rather than "" so the backend stores a real NULL and
                # matches this entry to its exit by colour/make instead.
                "plate_number": plate or None,
                "vehicle_type": "car",
                "color": color,
                "make": make,
                "confidence": conf,
                "camera_id": CAMERA_ID,
                "detected_at": _iso_utc(seen_at),
            },
            timeout=3,
        )
        return response.json()
    except Exception as error:
        print(f"⚠️  Backend error: {error}")
        return None


def send_entry_update(event_id, color="unknown", make="unknown"):
    """Fill in colour/make on an entry already sent with them still unknown."""
    if not enabled:
        return None
    try:
        response = requests.patch(
            f"{api_base}/api/entry/{event_id}",
            json={"color": color, "make": make},
            timeout=3,
        )
        return response.json()
    except Exception as error:
        print(f"⚠️  Entry update error: {error}")
        return None


def send_exit(event_id, plate, color="unknown", make="unknown", entry_event_id=None, seen_at=None):
    if not enabled:
        return None
    try:
        response = requests.put(
            f"{api_base}/api/exit",
            json={
                "event_id": event_id,
                "plate_number": plate,
                "camera_id": CAMERA_ID,
                "color": color,
                "make": make,
                "entry_event_id": entry_event_id,
                "detected_at": _iso_utc(seen_at),
            },
            timeout=3,
        )
        return response.json()
    except Exception as error:
        print(f"⚠️  Exit error: {error}")
        return None
