"""
Firestore write helpers — matched to Carter's frontend schema.

Carter's dashboard reads from these collections via onSnapshot:
  - slots/active        → CancellationSlot component
  - agent/status        → AgentStatus component
  - patients/p0..pN     → PatientQueue component
  - activity_log/       → ActivityLog component (ordered by timestamp desc)

All Python writes go through these helpers so the dashboard updates in real-time.
"""

import os
from datetime import datetime, timezone

_db = None


def init_firestore(service_account_path: str | None = None):
    """Initialize Firebase connection."""
    global _db

    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        if service_account_path and os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()

    _db = firestore.client()


def _get_db():
    if _db is None:
        raise RuntimeError("Firestore not initialized. Call init_firestore() first.")
    return _db


# --- Activity Log ---
# Frontend ActivityLog expects: { icon: str, message: str, type: str, timestamp }
# type values: 'call' | 'sms' | 'system' | 'success' | 'warning'

def add_activity(icon: str, message: str, log_type: str) -> None:
    """Add an activity log entry. Dashboard sees this instantly."""
    from firebase_admin import firestore
    db = _get_db()
    db.collection("activity_log").add({
        "icon": icon,
        "message": message,
        "type": log_type,
        "timestamp": firestore.SERVER_TIMESTAMP,
    })


# --- Agent Status ---
# Frontend AgentStatus expects: { phase, currentPatient, attempt, totalPatients }
# phase: 'idle' | 'calling' | 'no_answer' | 'sms_sent' | 'sms_reply' | 'booking' | 'filled'

def update_agent_status(
    phase: str,
    current_patient: str = "",
    attempt: int = 0,
    total_patients: int = 0,
) -> None:
    """Set the full agent status doc."""
    db = _get_db()
    db.document("agent/status").set({
        "phase": phase,
        "currentPatient": current_patient,
        "attempt": attempt,
        "totalPatients": total_patients,
    })


def update_agent_phase(phase: str, current_patient: str | None = None) -> None:
    """Update just the phase (and optionally currentPatient)."""
    db = _get_db()
    updates: dict = {"phase": phase}
    if current_patient is not None:
        updates["currentPatient"] = current_patient
    db.document("agent/status").update(updates)


def increment_attempt() -> None:
    """Increment the attempt counter."""
    from firebase_admin import firestore
    db = _get_db()
    db.document("agent/status").update({"attempt": firestore.Increment(1)})


# --- Slot ---
# Frontend CancellationSlot expects: { patientName, slotTime, slotDate, duration,
#   estimatedRevenue, status, bookedBy? }
# status: 'open' | 'booking' | 'filled'

def update_slot(status: str, booked_by: str | None = None) -> None:
    """Update the cancellation slot status."""
    db = _get_db()
    updates: dict = {"status": status}
    if booked_by is not None:
        updates["bookedBy"] = booked_by
    db.document("slots/active").update(updates)


# --- Patients ---
# Frontend PatientQueue expects: { name, phone, lastCleaning, status, order }
# status: 'queued' | 'calling' | 'no_answer' | 'sms_sent' | 'confirmed' | 'skipped'

def update_patient(patient_id: str, status: str) -> None:
    """Update a patient's status by doc ID (e.g., 'p0')."""
    db = _get_db()
    db.document(f"patients/{patient_id}").update({"status": status})


def get_queued_patients() -> list[dict]:
    """Get all queued patients ordered by priority."""
    db = _get_db()
    docs = (
        db.collection("patients")
        .where("status", "==", "queued")
        .order_by("order")
        .get()
    )
    return [{"id": d.id, **d.to_dict()} for d in docs]


def get_all_patients() -> list[dict]:
    """Get all patients."""
    db = _get_db()
    docs = db.collection("patients").order_by("order").get()
    return [{"id": d.id, **d.to_dict()} for d in docs]


def get_patient_by_phone(phone: str) -> dict | None:
    """Find a patient by phone number."""
    db = _get_db()
    docs = db.collection("patients").where("phone", "==", phone).limit(1).get()
    for d in docs:
        return {"id": d.id, **d.to_dict()}
    return None


# --- Reset ---

def reset_session() -> None:
    """Reset everything to clean demo state."""
    db = _get_db()

    # Clear activity log
    for log in db.collection("activity_log").get():
        log.reference.delete()

    # Reset patients
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
        db.document(f"patients/p{i}").set({**p, "status": "queued", "order": i})

    # Reset slot
    db.document("slots/active").set({
        "patientName": "Marcus Webb",
        "slotTime": "2:30 PM",
        "slotDate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "duration": 60,
        "estimatedRevenue": 185,
        "status": "open",
    })

    # Reset agent
    db.document("agent/status").set({
        "phase": "idle",
        "currentPatient": "",
        "attempt": 0,
        "totalPatients": len(patients),
    })
