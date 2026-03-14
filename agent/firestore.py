"""
Firestore write helpers for the dental rescheduling agent.

Adapted to Carter's frontend schema:
- slots/active          → slot info
- agent/status          → agent status doc
- patients/p0, p1, ...  → individual patient docs
- activity_log/         → activity collection with serverTimestamp

Usage:
    from agent.firestore import init_firestore, add_activity, update_agent_status

    # Initialize once at startup
    init_firestore("path/to/serviceAccountKey.json")

    # Then use helpers
    add_activity("thinking", "Scoring 4 candidates...")
    update_agent_status("running")
"""

import uuid

# Firebase admin SDK - will be initialized at runtime
_db = None


def init_firestore(service_account_path: str | None = None):
    """
    Initialize Firebase connection.

    Args:
        service_account_path: Path to service account JSON file.
            If None, uses GOOGLE_APPLICATION_CREDENTIALS env var.
    """
    global _db

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


def _get_db():
    """Get the Firestore client, raising if not initialized."""
    if _db is None:
        raise RuntimeError("Firestore not initialized. Call init_firestore() first.")
    return _db


def add_activity(activity_type: str, text: str) -> None:
    """
    Add an activity log entry to activity_log collection.

    UI will display this in the activity feed in real-time.

    Args:
        activity_type: One of "event", "thinking", "tool_call",
            "call_outcome", "sms_sent", "success", "error"
        text: Human-readable description of the activity
    """
    from firebase_admin import firestore

    db = _get_db()
    db.collection("activity_log").add({
        "id": f"act_{uuid.uuid4().hex[:8]}",
        "type": activity_type,
        "text": text,
        "timestamp": firestore.SERVER_TIMESTAMP,
    })


def update_agent_status(status: str) -> None:
    """
    Update the agent status document at agent/status.

    UI shows this in the top bar (idle/running/complete/failed).

    Args:
        status: One of "idle", "running", "complete", "failed"
    """
    db = _get_db()
    db.collection("agent").document("status").set({
        "status": status,
    }, merge=True)


def update_slot_status(status: str, filled_by: str | None = None) -> None:
    """
    Update the slot document at slots/active.

    Args:
        status: One of "open", "cancelled", "filling", "filled", "exhausted"
        filled_by: Name of patient who filled the slot (if status is "filled")
    """
    db = _get_db()
    updates = {"status": status}
    if filled_by is not None:
        updates["filled_by"] = filled_by
    db.collection("slots").document("active").set(updates, merge=True)


def update_candidates(candidates: list[dict]) -> None:
    """
    Write candidates to individual patient documents: patients/p0, p1, etc.

    UI shows this in the candidate queue panel.

    Args:
        candidates: Full list of candidates with current statuses
    """
    db = _get_db()
    patients_ref = db.collection("patients")

    # Write each candidate as patients/p0, patients/p1, etc.
    for i, candidate in enumerate(candidates):
        patients_ref.document(f"p{i}").set(candidate)


def update_recovered(amount: int) -> None:
    """
    Update the recovered revenue on the agent/status document.

    UI shows this in the revenue counter.

    Args:
        amount: Dollar amount recovered
    """
    db = _get_db()
    db.collection("agent").document("status").set({
        "recovered": amount,
    }, merge=True)


def initialize_session(slot: dict, recall_list: list[dict] | None = None) -> list[dict]:
    """
    Initialize a new session: score candidates and push everything to Firestore.

    This is the main entry point when a cancellation happens.
    Call this once, then use update_candidates() for status changes.

    Args:
        slot: The cancelled slot to fill (dict with treatment, time, date, value)
        recall_list: Optional patient list. If None, uses mock data.

    Returns:
        Scored and ranked candidates list (also written to Firestore)
    """
    from agent.brain import score_candidates
    from agent.mock_data import RECALL_LIST

    # Use mock data if no recall list provided
    if recall_list is None:
        recall_list = RECALL_LIST

    # Score and rank candidates using brain logic
    candidates = score_candidates(recall_list, slot)

    # Write everything to Firestore
    db = _get_db()

    # 1. Write the slot
    db.collection("slots").document("active").set({
        **slot,
        "status": "filling",
    })

    # 2. Set agent status to running
    db.collection("agent").document("status").set({
        "status": "running",
        "recovered": 0,
    })

    # 3. Write all candidates
    update_candidates(candidates)

    # 4. Log the activity
    add_activity("event", f"Scoring {len(candidates)} candidates for {slot.get('treatment', 'appointment')}")
    add_activity("thinking", f"Top candidate: {candidates[0]['name']} (score: {candidates[0]['score']})")

    return candidates


def reset_session() -> None:
    """
    Reset the session to initial demo state.

    Called by "Reset Demo" button in UI.
    Clears all collections and resets to initial state.
    """
    db = _get_db()

    # Reset slot
    db.collection("slots").document("active").set({
        "id": "slot_001",
        "time": "2:00 PM",
        "date": "Today",
        "treatment": "cleaning",
        "value": 200,
        "status": "open",
        "filled_by": None,
    })

    # Reset agent status
    db.collection("agent").document("status").set({
        "status": "idle",
        "recovered": 0,
    })

    # Clear patients collection (delete all p0, p1, etc.)
    patients_ref = db.collection("patients")
    for doc in patients_ref.stream():
        doc.reference.delete()

    # Clear activity log
    activity_ref = db.collection("activity_log")
    for doc in activity_ref.stream():
        doc.reference.delete()
