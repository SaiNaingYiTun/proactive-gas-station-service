from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, timezone
from collections import Counter
from uuid import UUID

import os

from auth import AuthDependency, create_token, hash_password, verify_password

load_dotenv()

app = FastAPI()

# The frontend runs on its own origin/port (Vite dev server, or wherever it's
# hosted), so the browser needs this to call the API at all. Wide open for
# now since the AI module's own detection endpoints below are still
# unauthenticated machine-to-machine calls either way (see the security
# review notes) -- tighten allow_origins to the real frontend origin(s) once
# this goes beyond local/exhibition use.
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

# Two dependencies: any logged-in staff account, or specifically the owner.
# Only dashboard-facing endpoints use these -- the AI module's own
# POST /api/detection, PUT /api/exit and PATCH /api/entry/{id} below are
# machine-to-machine calls, unrelated to a staff member being logged in, and
# are left exactly as they were.
require_auth = AuthDependency(require_owner=False).set_client(supabase)
require_owner = AuthDependency(require_owner=True).set_client(supabase)

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
    # The event_id of the entry this same tracked vehicle already sent, when it
    # sent one.  The AI knows exactly which entry an exit belongs to, so this is
    # a direct link -- colour/make matching is only the fallback for a vehicle
    # whose entry was never seen.
    entry_event_id: Optional[UUID] = None


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
    make itself is "unknown" on the EXIT side (classification never
    resolved), that field is not used to filter -- an unknown is not
    evidence of a mismatch, just missing information.

    The entry side can just as easily be "unknown" -- entry is sent as soon
    as colour is confident, often before make/model has resolved at all (see
    _queue_entry_if_ready in the AI module), and colour itself can stay
    unknown the same way. An open visit stored as unknown on either field is
    therefore also accepted as a candidate whenever the exit does have a
    real value for it, instead of being excluded by an exact-match filter
    that unknown could never satisfy.
    """
    cutoff = (datetime.utcnow() - timedelta(hours=MATCH_MAX_DWELL_HOURS)).isoformat()
    query = (
        supabase.table("vehicle_visits")
        .select("id, vehicle_color, vehicle_make")
        .is_("exit_time", "null")
        .gte("entry_time", cutoff)
        .order("entry_time")
    )
    if data.color != "unknown":
        query = query.or_(f"vehicle_color.eq.{data.color},vehicle_color.eq.unknown")
    if data.make != "unknown":
        query = query.or_(f"vehicle_make.eq.{data.make},vehicle_make.eq.unknown")
    rows = query.execute().data

    # A visit that actually agrees with the exit on colour/make is a better
    # guess than one that merely couldn't disagree because it was unknown, so
    # rank fewer-unknown-fields first. sort() is stable, so ties keep the
    # oldest-entry-first (FIFO) order the query already returned.
    def unknown_fields(row):
        return (
            (data.color != "unknown" and row["vehicle_color"] == "unknown")
            + (data.make != "unknown" and row["vehicle_make"] == "unknown")
        )

    rows.sort(key=unknown_fields)
    return rows


def _own_open_visit(data: ExitDetection):
    """The still-open visit this exiting vehicle's own entry event created, if any.

    Guessing by colour/make alone picks the OLDEST matching open visit, so with
    two similar cars open (or one stale visit from earlier) the exit closes the
    wrong one and the visit that really just ended stays "inside" forever."""
    if data.entry_event_id is None:
        return None
    visit_id = processed_visit_id(data.entry_event_id)
    if visit_id is None:
        return None
    rows = (
        supabase.table("vehicle_visits")
        .select("id, vehicle_color, vehicle_make")
        .eq("id", visit_id)
        .is_("exit_time", "null")
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def complete_active_visit(data: ExitDetection):
    """Close the open visit for an exiting vehicle and log its exit.

    A vehicle whose own entry was recorded closes exactly that visit.
    Otherwise the oldest matching open visit is assumed to be the one leaving (FIFO).
    When more than one open visit matches colour/make, the visit is still
    closed automatically -- but flagged "ambiguous" so staff can double check
    it later instead of trusting the guess silently. When nothing matches at
    all, the exit is still recorded (as an "exit_only" visit with no
    entry_time) rather than being discarded as an error -- a real detection
    happened and should stay reviewable, even if its entry was never seen.
    """
    own_visit = _own_open_visit(data)
    candidates = [own_visit] if own_visit else _find_open_visit_candidates(data)

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
        best = candidates[0]
        visit_id = best["id"]
        match_status = "matched" if len(candidates) == 1 else "ambiguous"
        updates = {
            "plate_number": data.plate_number,
            "exit_time": datetime.utcnow().isoformat(),
            "visit_status": "completed",
            "match_status": match_status,
        }
        # Entry is sent before colour/make necessarily resolves, so the
        # visit may have been stored as "unknown" for a value the exit camera
        # did read. Fill it in rather than leaving the completed visit
        # showing "Unknown vehicle" -- but never overwrite a value the entry
        # already had.
        if best["vehicle_color"] == "unknown" and data.color != "unknown":
            updates["vehicle_color"] = data.color
        if best["vehicle_make"] == "unknown" and data.make != "unknown":
            updates["vehicle_make"] = data.make
        supabase.table("vehicle_visits").update(updates).eq("id", visit_id).execute()

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

class EntryUpdate(BaseModel):
    color: str = "unknown"
    make: str = "unknown"


@app.patch("/api/entry/{event_id}")
def update_entry(event_id: UUID, data: EntryUpdate):
    """Fill in colour/make on an entry that was saved before they resolved.

    The AI sends an entry as soon as colour is confident, which is usually a
    moment before make has enough agreeing reads -- so the visit is stored
    with make "unknown" and, without this, stays that way until the exit
    fills it in. Same rule as complete_active_visit: only replace a value
    that is still unknown, never one the entry already had.
    """
    visit_id = processed_visit_id(event_id)
    if visit_id is None:
        return {"status": "not_found"}

    rows = (
        supabase.table("vehicle_visits")
        .select("vehicle_color, vehicle_make")
        .eq("id", visit_id)
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        return {"status": "not_found"}

    updates = {}
    if rows[0]["vehicle_color"] in (None, "unknown") and data.color != "unknown":
        updates["vehicle_color"] = data.color
    if rows[0]["vehicle_make"] in (None, "unknown") and data.make != "unknown":
        updates["vehicle_make"] = data.make
    if updates:
        supabase.table("vehicle_visits").update(updates).eq("id", visit_id).execute()
    return {"status": "updated" if updates else "unchanged", "visit_id": visit_id}


@app.get("/api/visits")
def list_visits(limit: int = 50, status: Optional[str] = None, account=Depends(require_auth)):
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


# =============================================================
# Health check
# =============================================================

@app.get("/api/health")
def health_check():
    """Whether the backend process AND its database connection are both up --
    not just "did some request succeed", which the dashboard's old status
    badges never actually checked at all (see the frontend review notes).
    Unauthenticated on purpose: a viewer needs to see the backend is down
    even when they cannot log in, and this exposes nothing sensitive."""
    try:
        supabase.table("vehicle_visits").select("id").limit(1).execute()
        return {"status": "ok", "database": "ok"}
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"database unreachable: {error}")


# =============================================================
# Authentication
# =============================================================

class LoginRequest(BaseModel):
    username: str
    password: str


def _account_out(row: dict):
    """The staff_accounts row shape the frontend receives -- never includes
    password_hash."""
    return {
        "id": row["id"], "username": row["username"], "display_name": row["display_name"],
        "is_owner": row["is_owner"], "active": row["active"],
    }


def _find_account_by_username(username: str):
    rows = (
        supabase.table("staff_accounts")
        .select("id, username, password_hash, display_name, is_owner, active, updated_at")
        .eq("username", username)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


@app.post("/api/auth/login")
def login(data: LoginRequest):
    account = _find_account_by_username(data.username)
    # Verify against a real (if irrelevant) hash even on a missing username,
    # so a wrong-username response takes about as long as a wrong-password
    # one -- a bit of defence against timing-based username enumeration.
    password_hash = account["password_hash"] if account else hash_password("")
    password_ok = verify_password(data.password, password_hash)
    if not account or not account["active"] or not password_ok:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return {"token": create_token(account), "account": _account_out(account)}


@app.get("/api/auth/me")
def whoami(account=Depends(require_auth)):
    return _account_out(account)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@app.post("/api/auth/change-password")
def change_own_password(data: ChangePasswordRequest, account=Depends(require_auth)):
    """Any logged-in account changing its OWN password -- proves identity by
    already being logged in plus re-entering its current password, same as
    changing a password on most ordinary systems. This is separate from the
    owner's staff-management endpoints below, which change ANOTHER
    account's credentials and so need the stronger owner-identifies-itself
    step described there."""
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    full = supabase.table("staff_accounts").select("password_hash").eq("id", account["id"]).limit(1).execute().data
    if not full or not verify_password(data.current_password, full[0]["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    supabase.table("staff_accounts").update({
        "password_hash": hash_password(data.new_password),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", account["id"]).execute()
    return {"status": "updated"}


# =============================================================
# Staff management (owner only)
# =============================================================
#
# Every account-modifying endpoint here takes owner_username/owner_password
# and re-verifies them against the CALLER's own account, on top of the
# require_owner dependency already checking the caller is logged in AS the
# owner. This is deliberately redundant with being logged in: it is the
# "the owner must identify themselves" step asked for, protecting against
# the moment an owner's already-open session is sitting unattended and
# someone else tries to use it to change a staff member's login.

def _verify_owner_reauth(account, owner_username: str, owner_password: str):
    if owner_username != account["username"]:
        raise HTTPException(status_code=401, detail="That is not the owner's own username")
    full = supabase.table("staff_accounts").select("password_hash").eq("id", account["id"]).limit(1).execute().data
    if not full or not verify_password(owner_password, full[0]["password_hash"]):
        raise HTTPException(status_code=401, detail="Owner password is incorrect")


@app.get("/api/auth/staff")
def list_staff(account=Depends(require_owner)):
    rows = (
        supabase.table("staff_accounts")
        .select("id, username, display_name, is_owner, active, created_at, updated_at")
        .order("created_at")
        .execute()
        .data
    )
    return rows


class CreateStaffRequest(BaseModel):
    username: str
    password: str
    display_name: str
    owner_username: str
    owner_password: str


@app.post("/api/auth/staff")
def create_staff(data: CreateStaffRequest, account=Depends(require_owner)):
    _verify_owner_reauth(account, data.owner_username, data.owner_password)
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if _find_account_by_username(data.username):
        raise HTTPException(status_code=409, detail="That username is already in use")
    row = supabase.table("staff_accounts").insert({
        "username": data.username,
        "password_hash": hash_password(data.password),
        "display_name": data.display_name,
        "is_owner": False,
    }).execute().data[0]
    return _account_out(row)


class UpdateStaffRequest(BaseModel):
    # All optional except the re-auth fields: send only what changes, e.g.
    # repurposing a former employee's row just sets username/password/
    # display_name for whoever replaces them.
    username: Optional[str] = None
    password: Optional[str] = None
    display_name: Optional[str] = None
    active: Optional[bool] = None
    owner_username: str
    owner_password: str


@app.patch("/api/auth/staff/{staff_id}")
def update_staff(staff_id: UUID, data: UpdateStaffRequest, account=Depends(require_owner)):
    _verify_owner_reauth(account, data.owner_username, data.owner_password)
    target = supabase.table("staff_accounts").select("id, is_owner").eq("id", str(staff_id)).limit(1).execute().data
    if not target:
        raise HTTPException(status_code=404, detail="No such staff account")
    if target[0]["is_owner"]:
        raise HTTPException(status_code=400, detail="Use /api/auth/change-password to change the owner's own password")

    updates = {}
    if data.username is not None:
        existing = _find_account_by_username(data.username)
        if existing and existing["id"] != str(staff_id):
            raise HTTPException(status_code=409, detail="That username is already in use")
        updates["username"] = data.username
    if data.password is not None:
        if len(data.password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        updates["password_hash"] = hash_password(data.password)
    if data.display_name is not None:
        updates["display_name"] = data.display_name
    if data.active is not None:
        updates["active"] = data.active
    if not updates:
        return {"status": "unchanged"}

    # Bumping updated_at is what makes this take effect immediately -- see
    # staff_accounts' own comment in the migration for why.
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    row = supabase.table("staff_accounts").update(updates).eq("id", str(staff_id)).execute().data[0]
    return _account_out(row)


# =============================================================
# Analytics
# =============================================================

@app.get("/api/analytics/summary")
def analytics_summary(days: int = 30, account=Depends(require_auth)):
    """Real aggregates computed from vehicle_visits -- replaces the frontend's
    previous hardcoded placeholder numbers entirely (see the frontend
    review notes: fuel type and customer-frequency segments are cut rather
    than faked, since this system does not and cannot track either)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = (
        supabase.table("vehicle_visits")
        .select("entry_time, exit_time, vehicle_make, vehicle_color, match_status")
        .gte("entry_time", cutoff)
        .limit(5000)
        .execute()
        .data
    )

    traffic_by_day = Counter()
    by_make = Counter()
    by_color = Counter()
    dwell_minutes = []
    needs_review = 0
    for row in rows:
        if row["entry_time"]:
            traffic_by_day[row["entry_time"][:10]] += 1
        if row["vehicle_make"] and row["vehicle_make"] != "unknown":
            by_make[row["vehicle_make"]] += 1
        if row["vehicle_color"] and row["vehicle_color"] != "unknown":
            by_color[row["vehicle_color"]] += 1
        if row["entry_time"] and row["exit_time"]:
            entry = datetime.fromisoformat(row["entry_time"].replace("Z", "+00:00"))
            exit_ = datetime.fromisoformat(row["exit_time"].replace("Z", "+00:00"))
            minutes = (exit_ - entry).total_seconds() / 60
            if minutes >= 0:  # a clock skew or bad data point must not silently corrupt the average
                dwell_minutes.append(minutes)
        if row["match_status"] in ("ambiguous", "exit_only"):
            needs_review += 1

    return {
        "range_days": days,
        "total_visits": len(rows),
        "needs_review": needs_review,
        "traffic_by_day": sorted(
            [{"date": date, "count": count} for date, count in traffic_by_day.items()],
            key=lambda item: item["date"],
        ),
        "by_make": sorted(
            [{"make": make, "count": count} for make, count in by_make.items()],
            key=lambda item: -item["count"],
        ),
        "by_color": sorted(
            [{"color": color, "count": count} for color, count in by_color.items()],
            key=lambda item: -item["count"],
        ),
        "avg_dwell_minutes": round(sum(dwell_minutes) / len(dwell_minutes), 1) if dwell_minutes else None,
        "completed_with_dwell": len(dwell_minutes),
    }


# =============================================================
# Reviewing / correcting a visit
# =============================================================

_VALID_VISIT_STATUS = {"inside", "completed"}
_VALID_MATCH_STATUS = {"pending", "matched", "ambiguous", "exit_only"}


class VisitCorrection(BaseModel):
    # Only fields actually sent are changed -- see exclude_unset below.
    plate_number: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_color: Optional[str] = None
    visit_status: Optional[str] = None
    match_status: Optional[str] = None


@app.patch("/api/visits/{visit_id}")
def correct_visit(visit_id: int, data: VisitCorrection, account=Depends(require_auth)):
    """Let staff fix a misread plate/make/colour, or clear the "needs
    review" flag once they have checked an ambiguous/exit_only visit by
    hand. Any logged-in account can do this -- correcting a wrong plate is
    routine staff work, not something that needs owner-level trust."""
    updates = data.dict(exclude_unset=True)
    if "visit_status" in updates and updates["visit_status"] not in _VALID_VISIT_STATUS:
        raise HTTPException(status_code=400, detail=f"visit_status must be one of {sorted(_VALID_VISIT_STATUS)}")
    if "match_status" in updates and updates["match_status"] not in _VALID_MATCH_STATUS:
        raise HTTPException(status_code=400, detail=f"match_status must be one of {sorted(_VALID_MATCH_STATUS)}")
    if not updates:
        return {"status": "unchanged"}

    existing = supabase.table("vehicle_visits").select("id").eq("id", visit_id).limit(1).execute().data
    if not existing:
        raise HTTPException(status_code=404, detail="No such visit")
    row = supabase.table("vehicle_visits").update(updates).eq("id", visit_id).execute().data[0]
    return row


@app.get("/api/visits/{visit_id}/events")
def visit_events(visit_id: int, account=Depends(require_auth)):
    """The detection_events rows behind one visit -- already stored on every
    entry/exit, but never surfaced anywhere in the dashboard until now."""
    existing = supabase.table("vehicle_visits").select("id").eq("id", visit_id).limit(1).execute().data
    if not existing:
        raise HTTPException(status_code=404, detail="No such visit")
    rows = (
        supabase.table("detection_events")
        .select("id, camera_id, confidence, event_type, created_at")
        .eq("visit_id", visit_id)
        .order("created_at")
        .execute()
        .data
    )
    return rows


for route in app.routes:
    print(route.path)



