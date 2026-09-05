from fastapi import FastAPI
from supabase import create_client
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

import os

load_dotenv()

app = FastAPI()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

class Detection(BaseModel):
    event_id: UUID
    plate_number: str
    vehicle_type: str
    color: str = "unknown"
    confidence: float
    camera_id: int


class ExitDetection(BaseModel):
    event_id: UUID
    plate_number: str
    # During single-camera testing this is the same camera ID used for entry.
    camera_id: int = 1
    confidence: Optional[float] = None


def processed_visit_id(event_id: UUID):
    """Return the visit for an already handled AI event, if any."""
    result = (
        supabase.table("detection_events")
        .select("visit_id")
        .eq("source_event_id", str(event_id))
        .limit(1)
        .execute()
    )
    return result.data[0]["visit_id"] if result.data else None


def complete_active_visit(data: ExitDetection):
    """Close the latest active visit for a detected plate and log its exit."""
    existing = (
        supabase.table("vehicle_visits")
        .select("id")
        .eq("plate_number", data.plate_number)
        .is_("exit_time", "null")
        .order("entry_time", desc=True)
        .limit(1)
        .execute()
    )

    if not existing.data:
        return None

    visit_id = existing.data[0]["id"]
    supabase.table("vehicle_visits").update({
        "exit_time": datetime.utcnow().isoformat(),
        "visit_status": "completed",
    }).eq("id", visit_id).execute()

    supabase.table("detection_events").insert({
        "visit_id": visit_id,
        "camera_id": data.camera_id,
        "confidence": data.confidence,
        "event_type": "exit",
        "source_event_id": str(data.event_id),
    }).execute()
    return visit_id

@app.post("/api/detection")
def save_detection(data: Detection):
    duplicate_visit_id = processed_visit_id(data.event_id)
    if duplicate_visit_id is not None:
        return {"status": "duplicate", "visit_id": duplicate_visit_id}

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
            # Keep the latest usable colour classification without replacing a
            # previous result with the classifier's "unknown" fallback.
            if data.color != "unknown":
                supabase.table("vehicle_visits").update({
                    "vehicle_color": data.color,
                }).eq("id", visit_id).execute()
        
        else:

            visit = (
                supabase.table("vehicle_visits")
                .insert({
                    "plate_number":data.plate_number,
                    "vehicle_type":data.vehicle_type,
                    "vehicle_color":data.color,
                    "entry_time": datetime.utcnow().isoformat(),
                    "visit_status" : "inside"
            })
            .execute()
        )
            visit_id = visit.data[0]["id"]

        #exit camera
    elif data.camera_id == 2:
        visit_id = complete_active_visit(ExitDetection(
            event_id=data.event_id,
            plate_number=data.plate_number,
            camera_id=data.camera_id,
            confidence=data.confidence,
        ))
        if visit_id is None:
            return{
                "status":"error",
                "message":"No active visit found"
            }

    else:
        return {
            "status":"error",
            "message":"Invalid camera_id"
        }
    
    # The camera-ID 2 path already logged its exit in complete_active_visit.
    if data.camera_id == 2:
        return {"status": "saved", "visit_id": visit_id}

    # Save entry detection event.

    supabase.table(
        "detection_events"
    ).insert({
        "visit_id":
            visit_id,
        
        "camera_id":
            data.camera_id,
        
        "confidence":
            data.confidence,
        "vehicle_color": data.color,
        "event_type":"entry",
        "source_event_id": str(data.event_id),
    }).execute()
    return {"status": "saved",
            "visit_id": visit_id}


@app.put("/api/exit")
def save_exit(data: ExitDetection):
    """Exit endpoint used by the AI for both one- and two-camera setups."""
    duplicate_visit_id = processed_visit_id(data.event_id)
    if duplicate_visit_id is not None:
        return {"status": "duplicate", "visit_id": duplicate_visit_id}

    visit_id = complete_active_visit(data)
    if visit_id is None:
        return {
            "status": "error",
            "message": "No active visit found",
        }
    return {"status": "saved", "visit_id": visit_id}

for route in app.routes:
    print(route.path)



