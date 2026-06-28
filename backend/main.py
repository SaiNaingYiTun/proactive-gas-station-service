from fastapi import FastAPI
from supabase import create_client
from dotenv import load_dotenv
from pydantic import BaseModel
from datetime import datetime

import os

load_dotenv()

#print("SUPABASE_URL =", os.getenv("SUPABASE_URL"))
#print("KEY EXISTS =", bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")))

app = FastAPI()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

class Detection(BaseModel):
    plate_number: str
    vehicle_type: str
    confidence: float

@app.post("/api/detection")
def save_detection(data: Detection):
    visit = supabase.table(
        "vehicle_visits"
    ).insert({
        "plate_number":
            data.plate_number,
        "vehicle_type":
            data.vehicle_type,
        "entry_time": 
            datetime.utcnow().isoformat()
    }).execute()

    visit_id = visit.data[0]["id"]

    supabase.table(
        "detection_events"
    ).insert({
        "visit_id":
            visit_id,
        
        "camera_id":
            1,
        
        "confidence":
            data.confidence
    }).execute()
    return {"status": "saved"}

for route in app.routes:
    print(route.path)



