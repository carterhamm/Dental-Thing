"""
Firestore write helpers for the dental rescheduling agent.

These are thin wrappers around firebase-admin writes.
UI person will set up the Firebase project and share credentials.

Usage:
    from agent.firestore import init_firestore, add_activity, update_agent_status

    # Initialize once at startup
    init_firestore("path/to/serviceAccountKey.json")

    # Then use helpers
    add_activity("thinking", "Scoring 4 candidates...")
    update_agent_status("running")
"""

import uuid
from datetime import datetime, timezone

# Firebase admin SDK - will be initialized at runtime
_db = None
_session_ref = None


def init_firestore(service_account_path: str | None = None):
    """
    Initialize Firebase connection.

    Args:
        service_account_path: Path to service account JSON file.
            If None, uses GOOGLE_APPLICATION_CREDENTIALS env var.
    """
    global _db, _session_ref

    import firebase_admin
    from firebase_admin import credentials, firestore

    # Avoid re-initializing if already done
    if not firebase_admin._apps:
        if service_account_path:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
        else:
            # Use default credentials (GOOGLE_APPLICATION_CREDENTIALS env var)
            firebase_admin.initialize_app()

    _db = firestore.client()
    _session_ref = _db.collection("sessions").document("current")


def _get_session_ref():
    """Get the session document reference, initializing if needed."""
    if _session_ref is None:
        raise RuntimeError("Firestore not initialized. Call init_firestore() first.")
    return _session_ref


def add_activity(activity_type: str, text: str) -> None:
    """
    Add an activity log entry.

    UI will display this in the activity feed in real-time.

    Args:
        activity_type: One of "event", "thinking", "tool_call",
            "call_outcome", "sms_sent", "success", "error"
        text: Human-readable description of the activity
    """
    from firebase_admin import firestore

    session_ref = _get_session_ref()
    session_ref.update({
        "activity": firestore.ArrayUnion([{
            "id": f"act_{uuid.uuid4().hex[:8]}",
            "type": activity_type,
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }])
    })


def update_agent_status(status: str) -> None:
    """
    Update the agent_status field.

    UI shows this in the top bar (idle/running/complete/failed).

    Args:
        status: One of "idle", "running", "complete", "failed"
    """
    session_ref = _get_session_ref()
    session_ref.update({"agent_status": status})


def update_slot_status(status: str, filled_by: str | None = None) -> None:
    """
    Update the slot status and optionally who filled it.

    Args:
        status: One of "open", "cancelled", "filling", "filled", "exhausted"
        filled_by: Name of patient who filled the slot (if status is "filled")
    """
    session_ref = _get_session_ref()
    updates = {"slot.status": status}
    if filled_by is not None:
        updates["slot.filled_by"] = filled_by
    session_ref.update(updates)


def update_candidates(candidates: list[dict]) -> None:
    """
    Replace the candidates array.

    UI shows this in the candidate queue panel.

    Args:
        candidates: Full list of candidates with current statuses
    """
    session_ref = _get_session_ref()
    session_ref.update({"candidates": candidates})


def update_recovered(amount: int) -> None:
    """
    Update the recovered revenue amount.

    UI shows this in the revenue counter.

    Args:
        amount: Dollar amount recovered
    """
    session_ref = _get_session_ref()
    session_ref.update({"recovered": amount})


def reset_session() -> None:
    """
    Reset the session to initial demo state.

    Called by "Reset Demo" button in UI.
    """
    session_ref = _get_session_ref()
    session_ref.set({
        "slot": {
            "id": "slot_001",
            "time": "2:00 PM",
            "date": "Today",
            "treatment": "cleaning",
            "value": 200,
            "status": "open",
            "filled_by": None,
        },
        "activity": [],
        "candidates": [],
        "recovered": 0,
        "agent_status": "idle",
    })
