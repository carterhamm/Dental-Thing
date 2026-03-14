"""
Firestore write helpers for the dental rescheduling agent.

When Firebase is initialized, writes go to Firestore (Carter's dashboard sees them).
When Firebase is NOT initialized, everything logs to the console instead.
This lets the agent run standalone without any infrastructure.

Carter's dashboard collections (when Firestore is active):
  - slots/active        → CancellationSlot component
  - agent/status        → AgentStatus component
  - patients/p0..pN     → PatientQueue component
  - activity_log/       → ActivityLog component
"""

import os
from datetime import datetime, timezone

_db = None
_firestore_available = False


def init_firestore(service_account_path: str | None = None):
    """Initialize Firebase connection. Optional — agent works without it."""
    global _db, _firestore_available

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            if service_account_path and os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
            else:
                firebase_admin.initialize_app()

        _db = firestore.client()
        _firestore_available = True
    except Exception as e:
        print(f"[firestore] Not available ({e}) — using console logging")
        _firestore_available = False


# ---------------------------------------------------------------------------
# Activity Log
# ---------------------------------------------------------------------------

def add_activity(icon: str, message: str, log_type: str) -> None:
    """Log an activity event. Shows in dashboard feed or console."""
    if _firestore_available and _db:
        from firebase_admin import firestore
        _db.collection("activity_log").add({
            "icon": icon,
            "message": message,
            "type": log_type,
            "timestamp": firestore.SERVER_TIMESTAMP,
        })
    else:
        print(f"  {icon}  {message}")


# ---------------------------------------------------------------------------
# Agent Status
# ---------------------------------------------------------------------------

def update_agent_status(
    phase: str,
    current_patient: str = "",
    attempt: int = 0,
    total_patients: int = 0,
) -> None:
    """Set the full agent status doc."""
    if _firestore_available and _db:
        _db.document("agent/status").set({
            "phase": phase,
            "currentPatient": current_patient,
            "attempt": attempt,
            "totalPatients": total_patients,
        })
    else:
        print(f"  [agent] phase={phase} patient={current_patient} attempt={attempt}/{total_patients}")


def update_agent_phase(phase: str, current_patient: str | None = None) -> None:
    """Update just the phase (and optionally currentPatient)."""
    if _firestore_available and _db:
        updates: dict = {"phase": phase}
        if current_patient is not None:
            updates["currentPatient"] = current_patient
        _db.document("agent/status").update(updates)
    else:
        msg = f"  [agent] → {phase}"
        if current_patient:
            msg += f" ({current_patient})"
        print(msg)


def increment_attempt() -> None:
    """Increment the attempt counter."""
    if _firestore_available and _db:
        from firebase_admin import firestore
        _db.document("agent/status").update({"attempt": firestore.Increment(1)})
    # No console output needed — the call/SMS activity log is enough


# ---------------------------------------------------------------------------
# Slot
# ---------------------------------------------------------------------------

def update_slot(status: str, booked_by: str | None = None) -> None:
    """Update the cancellation slot status."""
    if _firestore_available and _db:
        updates: dict = {"status": status}
        if booked_by is not None:
            updates["bookedBy"] = booked_by
        _db.document("slots/active").set(updates, merge=True)
    else:
        msg = f"  [slot] → {status}"
        if booked_by:
            msg += f" (by {booked_by})"
        print(msg)


# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------

def update_patient(patient_id: str, status: str) -> None:
    """Update a patient's status by doc ID (e.g., 'p0')."""
    if _firestore_available and _db:
        _db.document(f"patients/{patient_id}").update({"status": status})
    # No console output — the activity log already covers this


def get_queued_patients() -> list[dict]:
    """Get all queued patients ordered by priority.

    When Firestore isn't available, returns an empty list.
    The orchestrator falls back to mock data in that case.
    """
    if _firestore_available and _db:
        docs = (
            _db.collection("patients")
            .where("status", "==", "queued")
            .order_by("order")
            .get()
        )
        return [{"id": d.id, **d.to_dict()} for d in docs]
    return []


def get_all_patients() -> list[dict]:
    """Get all patients."""
    if _firestore_available and _db:
        docs = _db.collection("patients").order_by("order").get()
        return [{"id": d.id, **d.to_dict()} for d in docs]
    return []


def get_patient_by_phone(phone: str) -> dict | None:
    """Find a patient by phone number."""
    if _firestore_available and _db:
        docs = _db.collection("patients").where("phone", "==", phone).limit(1).get()
        for d in docs:
            return {"id": d.id, **d.to_dict()}
    return None


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

def reset_session() -> None:
    """Reset everything to clean demo state."""
    if _firestore_available and _db:
        for log in _db.collection("activity_log").get():
            log.reference.delete()

        patients = [
            {"name": "Sarah Chen", "lastCleaning": "8 months ago", "phone": "(555) 012-3456"},
            {"name": "James Patel", "lastCleaning": "7 months ago", "phone": "(555) 234-5678"},
            {"name": "Maria Santos", "lastCleaning": "7 months ago", "phone": "(555) 345-6789"},
            {"name": "Tom Bradley", "lastCleaning": "6 months ago", "phone": "(555) 456-7890"},
            {"name": "Emma Liu", "lastCleaning": "6 months ago", "phone": "(555) 567-8901"},
            {"name": "David Kim", "lastCleaning": "5 months ago", "phone": "(555) 678-9012"},
            {"name": "Lisa Thompson", "lastCleaning": "5 months ago", "phone": "(555) 789-0123"},
            {"name": "Ryan Garcia", "lastCleaning": "4 months ago", "phone": "(555) 890-1234"},
        ]
        for i, p in enumerate(patients):
            _db.document(f"patients/p{i}").set({**p, "status": "queued", "order": i})

        _db.document("slots/active").set({
            "patientName": "Marcus Webb",
            "slotTime": "2:30 PM",
            "slotDate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "duration": 60,
            "estimatedRevenue": 185,
            "status": "open",
        })

        _db.document("agent/status").set({
            "phase": "idle",
            "currentPatient": "",
            "attempt": 0,
            "totalPatients": len(patients),
        })
    else:
        print("  [reset] session cleared")
