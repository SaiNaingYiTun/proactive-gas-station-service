import requests

payload = {
    "plate_number": "1กก1234",
    "vehicle_type": "car",
    "confidence": 0.96
}

response = requests.post(
    "http://127.0.0.1:8000/api/detection",
    json=payload
)

print(response.json())