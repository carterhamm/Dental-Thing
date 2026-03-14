"""
Core decision logic for the dental rescheduling agent.

This module is the "brain" that PM's Claude SDK agent will call.
It handles:
- Scoring candidates from the recall list
- Deciding the next action (call, SMS, next candidate, etc.)
- Updating candidate statuses
"""

from typing import Literal

from agent.state import is_terminal_status

# Type definitions
Action = Literal["call", "sms", "next_candidate", "wait", "give_up", "done"]
CandidateStatus = Literal[
    "waiting", "calling", "no_answer", "texting", "no_reply", "declined", "confirmed"
]

# Timeout configurations (in seconds)
# For demo, these can be shortened to keep things snappy
CALL_TIMEOUT = 30.0  # How long to wait for call outcome
SMS_TIMEOUT = 60.0   # How long to wait for SMS reply


def score_candidate(patient: dict, slot: dict) -> int:
    """
    Score a patient for a given slot.

    Higher score = higher priority to contact.

    Scoring factors:
    - days_overdue × 3: More overdue patients get higher priority
    - treatment_match: +50 if matches, -20 if doesn't
    - reliability_score × 20: More reliable patients get bonus

    Args:
        patient: Patient dict with keys:
            - treatment_needed: str
            - days_overdue: int
            - reliability_score: float (0-1)
        slot: Slot dict with keys:
            - treatment: str

    Returns:
        Integer score (higher = better candidate)
    """
    score = patient["days_overdue"] * 3

    # Treatment match bonus/penalty
    if patient["treatment_needed"] == slot["treatment"]:
        score += 50
    else:
        score -= 20

    # Reliability bonus
    score += int(patient["reliability_score"] * 20)

    return score


def score_candidates(recall_list: list[dict], slot: dict) -> list[dict]:
    """
    Score and rank all candidates for a slot.

    Args:
        recall_list: List of patients from recall list
        slot: The slot to fill

    Returns:
        List of candidates sorted by score (highest first), with added fields:
            - rank: int (1-indexed)
            - score: int
            - status: "waiting"
    """
    # Score each patient
    scored = []
    for patient in recall_list:
        candidate = {
            "name": patient["name"],
            "phone": patient["phone"],
            "treatment_needed": patient["treatment_needed"],
            "days_overdue": patient["days_overdue"],
            "score": score_candidate(patient, slot),
            "status": "waiting",
        }
        scored.append(candidate)

    # Sort by score descending
    scored.sort(key=lambda c: c["score"], reverse=True)

    # Add rank
    for i, candidate in enumerate(scored):
        candidate["rank"] = i + 1

    return scored


def get_next_action(
    candidates: list[dict],
    current_index: int,
    elapsed_time: float = 0.0,
) -> tuple[Action, int]:
    """
    Decide the next action based on current state.

    This is the core decision function. PM's agent loop calls this repeatedly
    to drive the flow.

    Args:
        candidates: Current ranked candidate list with statuses
        current_index: Index of candidate we're currently working on (-1 if none)
        elapsed_time: Seconds elapsed since current action started (for timeout checks)

    Returns:
        (action, candidate_index) tuple:
        - ("call", idx) → Trigger voice call to candidate at idx
        - ("sms", idx) → Send SMS to candidate at idx
        - ("next_candidate", idx) → Move to next candidate at idx
        - ("wait", idx) → Still waiting for response, check again later
        - ("give_up", -1) → All candidates exhausted, slot unfilled
        - ("done", idx) → Candidate confirmed, slot filled!
    """
    if not candidates:
        return ("give_up", -1)

    # Check if any candidate is confirmed (slot filled!)
    for i, c in enumerate(candidates):
        if c["status"] == "confirmed":
            return ("done", i)

    # If no current candidate, start with first one
    if current_index < 0:
        return ("call", 0)

    # Check if current index is valid
    if current_index >= len(candidates):
        return ("give_up", -1)

    current = candidates[current_index]
    status = current["status"]

    # Decision tree based on current candidate's status
    if status == "waiting":
        # Haven't contacted yet → call them
        return ("call", current_index)

    elif status == "calling":
        # Currently calling → check timeout
        if elapsed_time >= CALL_TIMEOUT:
            # Timeout → will need to mark as no_answer and try SMS
            return ("sms", current_index)
        else:
            # Still waiting for call outcome
            return ("wait", current_index)

    elif status == "no_answer":
        # Call failed → try SMS
        return ("sms", current_index)

    elif status == "texting":
        # Currently texting → check timeout
        if elapsed_time >= SMS_TIMEOUT:
            # Timeout → move to next candidate
            return _try_next_candidate(candidates, current_index)
        else:
            # Still waiting for SMS reply
            return ("wait", current_index)

    elif status in ("no_reply", "declined"):
        # Terminal failure → try next candidate
        return _try_next_candidate(candidates, current_index)

    elif status == "confirmed":
        # Should have been caught above, but just in case
        return ("done", current_index)

    else:
        # Unknown status → try next candidate to be safe
        return _try_next_candidate(candidates, current_index)


def _try_next_candidate(candidates: list[dict], current_index: int) -> tuple[Action, int]:
    """
    Find the next non-terminal candidate to try.

    Returns ("next_candidate", idx) if found, ("give_up", -1) if all exhausted.
    """
    for i in range(current_index + 1, len(candidates)):
        if not is_terminal_status(candidates[i]["status"]):
            return ("next_candidate", i)

    # All remaining candidates are terminal
    return ("give_up", -1)


def update_candidate_status(
    candidates: list[dict],
    candidate_index: int,
    new_status: CandidateStatus,
) -> list[dict]:
    """
    Update a candidate's status and return the updated list.

    Creates a new list (doesn't mutate in place) for cleaner state management.

    Args:
        candidates: Current candidate list
        candidate_index: Which candidate to update
        new_status: New status value

    Returns:
        New candidate list with updated status
    """
    # Create a copy to avoid mutating the original
    updated = [c.copy() for c in candidates]
    updated[candidate_index]["status"] = new_status
    return updated


def calculate_recovered_revenue(slot: dict) -> int:
    """
    Calculate recovered revenue when a slot is filled.

    Args:
        slot: The slot that was filled

    Returns:
        Dollar amount recovered (slot value)
    """
    return slot.get("value", 0)


# Re-export mock data for backwards compatibility (tests import from here)
from agent.mock_data import RECALL_LIST, DEMO_SLOT
