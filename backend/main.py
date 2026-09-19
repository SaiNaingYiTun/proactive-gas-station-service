from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID

import os

load_dotenv()

app = FastAPI()

# The frontend runs on its own origin/port (Vite dev server, or wherever it's
# hosted), so the browser needs this to call the API at all. Wide open for
# now since there's no auth on these endpoints yet either way (see the
# security review notes) -- tighten allow_origins to the real frontend
# origin(s) once this goes beyond local/exhibition use.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# This camera's entry view usually has no visible plate, so an open visit
# can only be matched to its eventual exit by colour/make. Bound that search
# to a reasonable dwell window so a visit that got stuck open (a bug, or a
# vehicle that never triggered an exit) can never be matched by accident
# hours or days later.
MATCH_MAX_DWELL_HOURS = 6


class Detection(BaseModel):
    event_id: UUID
    # Optional: this camera's entry view usually never shows a plate at all.
    plate_number: Optional[str] = None
    vehicle_type: str
    color: str = "unknown"
    make: str = "unknown"
    confidence: float
    camera_id: int


class ExitDetection(BaseModel):
    event_id: UUID
    plate_number: str
    # During single-camera testing this is the same camera ID used for entry.
    camera_id: int = 1
    confidence: Optional[float] = None
    # Colour/make of the exiting vehicle -- since entry has no plate, these
    # are what complete_active_visit matches against the open visits.
    color: str = "unknown"
    make: str = "unknown"


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


def _find_open_visit_candidates(data: ExitDetection):
    """Return open visits that could plausibly be this exiting vehicle.

    Entry never has a plate on this camera, so plate can't be the join key
    here -- match on colour/make instead, bounded to MATCH_MAX_DWELL_HOURS so
    a long-stuck-open visit can never be matched by accident. When colour or
    make itself is "unknown" (classification never resolved), that field is
    not used to filter -- an unknown is not evidence of a mismatch, just
    missing information.
    """
    cutoff = (datetime.utcnow() - timedelta(hours=MATCH_MAX_DWELL_HOURS)).isoformat()
    query = (
        supabase.table("vehicle_visits")
        .select("id")
        .is_("exit_time", "null")
        .gte("entry_time", cutoff)
        .order("entry_time")
    )
    if data.color != "unknown":
        query = query.eq("vehicle_color", data.color)
    if data.make != "unknown":
        query = query.eq("vehicle_make", data.make)
    return query.execute().data


def complete_active_visit(data: ExitDetection):
    """Close the best-matching open visit for an exiting vehicle and log its exit.

    The oldest matching open visit is assumed to be the one leaving (FIFO).
    When more than one open visit matches colour/make, the visit is still
    closed automatically -- but flagged "ambiguous" so staff can double check
    it later instead of trusting the guess silently. When nothing matches at
    all, the exit is still recorded (as an "exit_only" visit with no
    entry_time) rather than being discarded as an error -- a real detection
    happened and should stay reviewable, even if its entry was never seen.
    """
    candidates = _find_open_visit_candidates(data)

    if not candidates:
        orphan = (
            supabase.table("vehicle_visits")
            .insert({
                "plate_number": data.plate_number,
                "vehicle_color": data.color,
                "vehicle_make": data.make,
                "exit_time": datetime.utcnow().isoformat(),
                "visit_status": "completed",
                "match_status": "exit_only",
            })
            .execute()
        )
        visit_id = orphan.data[0]["id"]
    else:
        visit_id = candidates[0]["id"]
        match_status = "matched" if len(candidates) == 1 else "ambiguous"
        supabase.table("vehicle_visits").update({
            "plate_number": data.plate_number,
            "exit_time": datetime.utcnow().isoformat(),
            "visit_status": "completed",
            "match_status": match_status,
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

    #entry camera
    if data.camera_id == 1:
        # Entry never has a plate on this camera, so there is no reliable key
        # to dedupe against an already-open visit -- always insert a fresh
        # one. The AI side already guards against sending more than one
        # entry per tracked vehicle; the check above already protects
        # against a retried HTTP call for the same event.
        visit = (
            supabase.table("vehicle_visits")
            .insert({
                "plate_number": data.plate_number,
                "vehicle_type": data.vehicle_type,
                "vehicle_color": data.color,
                "vehicle_make": data.make,
                "entry_time": datetime.utcnow().isoformat(),
                "visit_status": "inside",
                "match_status": "pending",
            })
            .execute()
        )
        visit_id = visit.data[0]["id"]

        #exit camera
    elif data.camera_id == 2:
        visit_id = complete_active_visit(ExitDetection(
            event_id=data.event_id,
            plate_number=data.plate_number or "",
            camera_id=data.camera_id,
            confidence=data.confidence,
            color=data.color,
            make=data.make,
        ))

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
    return {"status": "saved", "visit_id": visit_id}

@app.get("/api/visits")
def list_visits(limit: int = 50, status: Optional[str] = None):
    """Recent vehicle visits for the dashboard, most recent entry first.

    `status` filters on visit_status ("inside" / "completed") when given.
    An "exit_only" visit (see complete_active_visit) has no entry_time, so
    it sorts as if it were the oldest -- acceptable here since these are rare
    and still show up in the list, just not necessarily at the very top.
    """
    query = supabase.table("vehicle_visits").select("*")
    if status:
        query = query.eq("visit_status", status)
    result = query.order("entry_time", desc=True).limit(limit).execute()
    return result.data


for route in app.routes:
    print(route.path)



