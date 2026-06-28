import requests

response = requests.post(
    "http://127.0.0.1:8000/api/detection",
    json={
        "plate_number": "TEST123",
        "vehicle_type": "car",
        "confidence": 0.95
    }
)

print(response.status_code)
print(response.json())