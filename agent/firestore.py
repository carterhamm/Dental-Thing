"""
Firestore write helpers for the dental rescheduling agent.

When Firebase is initialized, writes go to Firestore (Carter's dashboard sees them).
When Firebase is NOT initialized, everything logs to the console instead.
This lets the agent run standalone without any infrastructure.

Carter's dashboard collections (when Firestore is active):
  - slots/active          → slot info
  - agent/status          → agent status doc
  - patients/p0, p1, ...  → individual patient docs
  - activity_log/         → activity collection with serverTimestamp
"""

import os
import uuid

_db = None
_firestore_available = False


def init_firestore(service_account: str | dict | None = None):
    """Initialize Firebase connection. Optional — agent works without it.

    Args:
        service_account: Path to service account JSON file, a dict of credentials,
            or None to use GOOGLE_APPLICATION_CREDENTIALS env var.
    """
    global _db, _firestore_available

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            if isinstance(service_account, dict):
                cred = credentials.Certificate(service_account)
                firebase_admin.initialize_app(cred)
            elif isinstance(service_account, str):
                cred = credentials.Certificate(service_account)
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

def add_activity(activity_type: str, text: str) -> None:
    """Add an activity log entry. Shows in dashboard feed or console."""
    if _firestore_available and _db:
        from firebase_admin import firestore
        _db.collection("activity_log").add({
            "id": f"act_{uuid.uuid4().hex[:8]}",
            "type": activity_type,
            "text": text,
            "timestamp": firestore.SERVER_TIMESTAMP,
        })
    else:
        print(f"  [{activity_type}] {text}")


# ---------------------------------------------------------------------------
# Agent Status
# ---------------------------------------------------------------------------

def update_agent_status(status: str) -> None:
    """Update the agent status document at agent/status."""
    if _firestore_available and _db:
        _db.collection("agent").document("status").set({"status": status}, merge=True)
    else:
        print(f"  [agent] status={status}")


# ---------------------------------------------------------------------------
# Slot
# ---------------------------------------------------------------------------

def update_slot_status(status: str, filled_by: str | None = None) -> None:
    """Update the slot document at slots/active."""
    if _firestore_available and _db:
        updates = {"status": status}
        if filled_by is not None:
            updates["filled_by"] = filled_by
        _db.collection("slots").document("active").set(updates, merge=True)
    else:
        msg = f"  [slot] → {status}"
        if filled_by:
            msg += f" (by {filled_by})"
        print(msg)


# ---------------------------------------------------------------------------
# Candidates / Patients
# ---------------------------------------------------------------------------

def update_candidates(candidates: list[dict]) -> None:
    """Write candidates to individual patient documents: patients/p0, p1, etc."""
    if _firestore_available and _db:
        patients_ref = _db.collection("patients")
        for i, candidate in enumerate(candidates):
            patients_ref.document(f"p{i}").set(candidate)
    else:
        for i, c in enumerate(candidates):
            print(f"  [p{i}] {c['name']} — {c.get('status', 'waiting')}")


def update_recovered(amount: int) -> None:
    """Update the recovered revenue on the agent/status document."""
    if _firestore_available and _db:
        _db.collection("agent").document("status").set({"recovered": amount}, merge=True)
    else:
        print(f"  [recovered] ${amount}")


def get_patient_by_phone(phone: str) -> dict | None:
    """Find a patient by phone number."""
    if _firestore_available and _db:
        docs = _db.collection("patients").where("phone", "==", phone).limit(1).get()
        for d in docs:
            return {"id": d.id, **d.to_dict()}
    return None


# ---------------------------------------------------------------------------
# Session Management
# ---------------------------------------------------------------------------

def initialize_session(slot: dict, recall_list: list[dict] | None = None) -> list[dict]:
    """Initialize a new session: score candidates and push everything to Firestore.

    Returns scored and ranked candidates list.
    """
    from agent.brain import score_candidates
    from agent.mock_data import RECALL_LIST

    if recall_list is None:
        recall_list = RECALL_LIST

    candidates = score_candidates(recall_list, slot)

    if _firestore_available and _db:
        _db.collection("slots").document("active").set({**slot, "status": "filling"})
        _db.collection("agent").document("status").set({"status": "running", "recovered": 0})
        update_candidates(candidates)

    add_activity("event", f"Scoring {len(candidates)} candidates for {slot.get('treatment', 'appointment')}")
    if candidates:
        add_activity("thinking", f"Top candidate: {candidates[0]['name']} (score: {candidates[0]['score']})")

    return candidates


def reset_session() -> None:
    """Reset everything to clean demo state."""
    if _firestore_available and _db:
        # Clear activity log
        for doc in _db.collection("activity_log").stream():
            doc.reference.delete()

        # Clear patients
        for doc in _db.collection("patients").stream():
            doc.reference.delete()

        # Reset slot
        _db.collection("slots").document("active").set({
            "id": "slot_001",
            "time": "2:00 PM",
            "date": "Today",
            "treatment": "cleaning",
            "value": 200,
            "status": "open",
            "filled_by": None,
        })

        # Reset agent status
        _db.collection("agent").document("status").set({
            "status": "idle",
            "recovered": 0,
        })
    else:
        print("  [reset] session cleared")
