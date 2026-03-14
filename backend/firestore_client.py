"""
Firestore write helpers — the contract between PM agent and the rest of the system.

PM agent calls these to write state. UI/Voice watches Firestore for changes.
This is the single source of truth for all Firestore writes from the PM layer.
"""

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from firebase_admin import firestore
from config import session_ref


ActivityType = Literal[
    "event", "thinking", "tool_call", "call_outcome", "sms_sent", "success", "error"
]
AgentStatus = Literal["idle", "running", "complete", "failed"]
SlotStatus = Literal["open", "cancelled", "filling", "filled", "exhausted"]
ActionType = Literal["voice", "sms"]


def log_activity(activity_type: ActivityType, text: str) -> str:
    """Append an activity entry. UI sees this instantly via onSnapshot.

    Returns the activity ID.
    """
    activity_id = f"act_{uuid.uuid4().hex[:8]}"
    session_ref.update(
        {
            "activity": firestore.ArrayUnion(
                [
                    {
                        "id": activity_id,
                        "type": activity_type,
                        "text": text,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            )
        }
    )
    return activity_id


def set_agent_status(status: AgentStatus) -> None:
    """Update agent_status. UI shows this in the top bar."""
    session_ref.update({"agent_status": status})


def set_slot_status(status: SlotStatus, filled_by: Optional[str] = None) -> None:
    """Update slot status and optionally who filled it."""
    updates: dict = {"slot.status": status}
    if filled_by is not None:
        updates["slot.filled_by"] = filled_by
    session_ref.update(updates)


def update_candidates(candidates: list[dict]) -> None:
    """Replace the candidates array in Firestore."""
    session_ref.update({"candidates": candidates})


def write_pending_action(
    action_type: ActionType,
    phone: str,
    patient_name: str,
    message: str,
) -> str:
    """Write an outreach intent for the UI/Voice layer to execute.

    UI/Voice person's code watches `pending_action` via onSnapshot.
    When they see status="pending", they execute the call/SMS and write
    the outcome to `pending_outcome`.

    Returns the action ID.
    """
    action_id = f"action_{uuid.uuid4().hex[:8]}"
    session_ref.update(
        {
            "pending_action": {
                "id": action_id,
                "type": action_type,
                "phone": phone,
                "patient_name": patient_name,
                "message": message,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        }
    )
    return action_id


def read_and_clear_pending_outcome() -> Optional[dict]:
    """Read the pending_outcome written by UI/Voice layer, then clear it.

    Returns the outcome dict if present, None if not yet available.
    Outcome shape: {"type": "voice"|"sms", "result": "confirmed"|"declined"|"no_answer", "details": str}
    """
    doc = session_ref.get()
    data = doc.to_dict()
    outcome = data.get("pending_outcome")
    if outcome:
        session_ref.update({"pending_outcome": firestore.DELETE_FIELD})
        return outcome
    return None


def book_slot(candidate_name: str, value: int) -> None:
    """Finalize the booking — mark slot filled, record revenue."""
    session_ref.update(
        {
            "slot.status": "filled",
            "slot.filled_by": candidate_name,
            "recovered": value,
            "agent_status": "complete",
        }
    )


def get_session() -> dict:
    """Read the full session document."""
    doc = session_ref.get()
    return doc.to_dict()
