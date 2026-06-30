from fastapi import FastAPI
from supabase import create_client
from dotenv import load_dotenv
from pydantic import BaseModel
from datetime import datetime

import os

load_dotenv()

app = FastAPI()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

class Detection(BaseModel):
    plate_number: str
    vehicle_type: str
    confidence: float
    camera_id: int

@app.post("/api/detection")
def save_detection(data: Detection):
    #check there is active visit or not
    existing = (
        supabase.table("vehicle_visits")
        .select("*")
        .eq("plate_number",data.plate_number)
        .is_("exit_time","null")
        .execute()
    )

    #entry camera

    if data.camera_id == 1 :

        if existing.data:
            #vehicle already inside
            visit_id = existing.data[0]["id"]
        
        else:

            visit = (
                supabase.table("vehicle_visits")
                .insert({
                    "plate_number":data.plate_number,
                    "vehicle_type":data.vehicle_type,
                    "entry_time": datetime.utcnow().isoformat(),
                    "visit_status" : "inside"
            })
            .execute()
        )
            visit_id = visit.data[0]["id"]

        #exit camera
    elif data.camera_id == 2:

        if not existing.data:
            return{
                "status":"error",
                "message":"No active visit found"
            }
            

        visit_id = existing.data[0]["id"]

        #update exit  time
        supabase.table("vehicle_visits").update({
            "exit_time" : datetime.utcnow().isoformat(),
            "visit_status" : "completed"
        }).eq("id",visit_id).execute()

    else:
        return {
            "status":"error",
            "message":"Invalid camera_id"
        }
    
    #save detection event

    supabase.table(
        "detection_events"
    ).insert({
        "visit_id":
            visit_id,
        
        "camera_id":
            data.camera_id,
        
        "confidence":
            data.confidence,
            "event_type":"entry" if data.camera_id == 1 else "exit"
    }).execute()
    return {"status": "saved",
            "visit_id": visit_id}

for route in app.routes:
    print(route.path)



